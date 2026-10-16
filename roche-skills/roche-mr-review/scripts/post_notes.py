"""Plan, preflight, and post the review notes in <run>/notes/ on the merge request.

Without --post it is a dry run: it prints where every note would land and checks every
body against the GitLab firewall through the markdown preview endpoint, which creates
nothing. With --post it creates new notes and updates edited ones in place; posted.json
records what is live, so a rerun skips unchanged notes.

Usage: python3 -B post_notes.py <run directory> [--post]
"""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import assert_never

from gitlab_api import FirewallBlockedError, GitLabApiError, call_gitlab_api
from review_run import (
    NOTES_DIRECTORY_NAME,
    POSTED_STATE_FILE_NAME,
    ReviewNote,
    ReviewRun,
    load_review_notes,
    load_review_run,
    run_git,
)

FULL_FILE_CONTEXT_OPTION = "--unified=1000000"
HUNK_HEADER_PATTERN = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
GENERAL_NOTE_PREFIX_TEMPLATE = "`{path}:{line}` (not changed in this MR, so posted as a general note):\n\n"
SOURCE_PREVIEW_LENGTH = 70
COMBINATION_BLOCKED_MESSAGE = "no single line is blocked, only their combination: split the note or reword it"


class LineKind(StrEnum):
    ADDED = "added"
    UNCHANGED = "unchanged"
    OUTSIDE_DIFF = "outside the diff"
    GENERAL = "general"

    @property
    def is_anchored(self) -> bool:
        return self in (LineKind.ADDED, LineKind.UNCHANGED)


class NoteAction(StrEnum):
    POST = "post"
    UPDATE = "update"
    SKIP = "skip"


@dataclass
class LinePosition:
    kind: LineKind
    old_path: str
    old_line: int


@dataclass
class PostedNote:
    discussion_id: str
    note_id: int
    path: str
    line: int
    body_digest: str
    posted_inline: bool


@dataclass
class NotePlan:
    review_note: ReviewNote
    line_position: LinePosition | None
    posts_inline: bool
    lands_as: str
    body: str
    body_digest: str
    action: NoteAction
    source_line: str


def main():
    argument_parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argument_parser.add_argument("run_directory", type=Path)
    argument_parser.add_argument("--post", action="store_true", help="publish; without it nothing is created")
    arguments = argument_parser.parse_args()

    review_run = load_review_run(arguments.run_directory)
    review_notes = load_review_notes(arguments.run_directory)
    if not review_notes:
        sys.exit(f"no note files in {arguments.run_directory / NOTES_DIRECTORY_NAME}")
    state_file = arguments.run_directory / POSTED_STATE_FILE_NAME
    posted_state = {}
    if state_file.exists():
        posted_state = {
            finding: PostedNote(**posted_fields) for finding, posted_fields in json.loads(state_file.read_text()).items()
        }
    repository = Path(review_run.repository_path)

    note_plans = [plan_note(review_run, repository, review_note, posted_state) for review_note in review_notes]
    print_plan(note_plans)

    merge_request = call_gitlab_api(
        review_run.hostname, f"projects/{review_run.project_id}/merge_requests/{review_run.merge_request_iid}"
    )
    has_new_anchored_notes = any(
        note_plan.action == NoteAction.POST and note_plan.posts_inline for note_plan in note_plans
    )
    if merge_request["diff_refs"]["head_sha"] != review_run.head_commit and has_new_anchored_notes:
        sys.exit(
            "the MR head moved since the review: rerun setup_review.py, re-check every anchor line "
            "against the new head, then rerun this script"
        )

    blocked_notes = preflight_bodies(review_run.hostname, note_plans)
    if blocked_notes:
        for note_plan, blocked_lines in blocked_notes:
            print(f"\nfirewall blocks finding {note_plan.review_note.finding} ({note_plan.review_note.source_file.name}):")
            for blocked_line in blocked_lines:
                print(f"    {blocked_line}")
        sys.exit("\nreword the blocked lines (known trigger: `time (`) and rerun; nothing was posted")

    if not arguments.post:
        print("\ndry run: nothing was posted. Rerun with --post to publish.")
        return
    publish(review_run, note_plans, posted_state, state_file)


def plan_note(
    review_run: ReviewRun, repository: Path, review_note: ReviewNote, posted_state: dict[str, PostedNote]
) -> NotePlan:
    posted_note = posted_state.get(str(review_note.finding))
    if posted_note:
        if (posted_note.path, posted_note.line) != (review_note.path, review_note.line):
            posted_anchor = f"{posted_note.path}:{posted_note.line}" if posted_note.path else "a general note"
            sys.exit(
                f"{review_note.source_file.name}: finding {review_note.finding} is already posted as "
                f"{posted_anchor}, and GitLab cannot move a note. Restore that anchor, or withdraw the "
                "note (SKILL.md stage 6) and post it again."
            )
        line_position = None
        posts_inline = posted_note.posted_inline
        lands_as = "inline (posted)" if posts_inline else "general note (posted)"
        source_line = ""
    else:
        line_position, source_line = locate_line(review_run, repository, review_note)
        posts_inline = line_position.kind.is_anchored
        match line_position.kind:
            case LineKind.ADDED:
                lands_as = "inline, added line"
            case LineKind.UNCHANGED:
                lands_as = f"inline, unchanged (old line {line_position.old_line})"
            case LineKind.OUTSIDE_DIFF:
                lands_as = "general note (file not in the diff)"
            case LineKind.GENERAL:
                lands_as = "general note"
            case _:
                assert_never(line_position.kind)

    body = review_note.body
    if review_note.path and not posts_inline:
        body = GENERAL_NOTE_PREFIX_TEMPLATE.format(path=review_note.path, line=review_note.line) + body
    body_digest = hashlib.sha256(body.encode()).hexdigest()

    if not posted_note:
        action = NoteAction.POST
    elif posted_note.body_digest == body_digest:
        action = NoteAction.SKIP
    else:
        action = NoteAction.UPDATE
    return NotePlan(review_note, line_position, posts_inline, lands_as, body, body_digest, action, source_line)


def locate_line(review_run: ReviewRun, repository: Path, review_note: ReviewNote) -> tuple[LinePosition, str]:
    if not review_note.path:
        return LinePosition(LineKind.GENERAL, "", 0), ""

    file_lines = run_git(repository, "show", f"{review_run.head_commit}:{review_note.path}").splitlines()
    if not 0 < review_note.line <= len(file_lines):
        sys.exit(
            f"{review_note.source_file.name}: {review_note.path} has {len(file_lines)} lines at the MR head, "
            f"not {review_note.line}"
        )
    source_line = file_lines[review_note.line - 1].strip()

    renamed_from = {}
    changed_paths = set()
    name_status = run_git(repository, "diff", "--find-renames", "--name-status", review_run.base_commit, review_run.head_commit)
    for status_line in name_status.splitlines():
        status, *paths = status_line.split("\t")
        changed_paths.add(paths[-1])
        if status.startswith("R"):
            renamed_from[paths[-1]] = paths[0]
    if review_note.path not in changed_paths:
        return LinePosition(LineKind.OUTSIDE_DIFF, review_note.path, review_note.line), source_line

    old_path = renamed_from.get(review_note.path, review_note.path)
    file_diff = run_git(
        repository,
        "diff",
        "--find-renames",
        FULL_FILE_CONTEXT_OPTION,
        review_run.base_commit,
        review_run.head_commit,
        "--",
        old_path,
        review_note.path,
    )
    old_line_number = new_line_number = 0
    inside_hunk = False
    for diff_line in file_diff.splitlines():
        hunk_header = HUNK_HEADER_PATTERN.match(diff_line)
        if hunk_header:
            old_start, old_count, new_start, new_count = hunk_header.groups()
            old_line_number = int(old_start) - 1 if old_count != "0" else int(old_start)
            new_line_number = int(new_start) - 1 if new_count != "0" else int(new_start)
            inside_hunk = True
            continue
        if not inside_hunk or diff_line.startswith("\\"):
            continue
        if diff_line.startswith("-"):
            old_line_number += 1
            continue
        new_line_number += 1
        if diff_line.startswith("+"):
            if new_line_number == review_note.line:
                return LinePosition(LineKind.ADDED, old_path, 0), source_line
            continue
        old_line_number += 1
        if new_line_number == review_note.line:
            return LinePosition(LineKind.UNCHANGED, old_path, old_line_number), source_line

    # A pure rename has no hunks: every line is unchanged and keeps its number.
    return LinePosition(LineKind.UNCHANGED, old_path, review_note.line), source_line


def print_plan(note_plans: list[NotePlan]):
    print(f"{'finding':>7}  {'action':<6}  {'lands as':<38}  anchor")
    for note_plan in note_plans:
        review_note = note_plan.review_note
        anchor = f"{review_note.path}:{review_note.line}" if review_note.path else "-"
        print(f"{review_note.finding:>7}  {note_plan.action:<6}  {note_plan.lands_as:<38}  {anchor}")
        if note_plan.source_line:
            print(f"{'':>7}  {'':<6}  {'':<38}  | {note_plan.source_line[:SOURCE_PREVIEW_LENGTH]}")


def preflight_bodies(hostname: str, note_plans: list[NotePlan]) -> list[tuple[NotePlan, list[str]]]:
    blocked_notes = []
    for note_plan in note_plans:
        if note_plan.action == NoteAction.SKIP:
            continue
        try:
            call_gitlab_api(hostname, "markdown", method="POST", payload={"text": note_plan.body, "gfm": True})
        except FirewallBlockedError:
            blocked_lines = []
            for body_line in note_plan.body.splitlines():
                if not body_line.strip():
                    continue
                try:
                    call_gitlab_api(hostname, "markdown", method="POST", payload={"text": body_line, "gfm": True})
                except FirewallBlockedError:
                    blocked_lines.append(body_line)
            blocked_notes.append((note_plan, blocked_lines or [COMBINATION_BLOCKED_MESSAGE]))
    print(f"\nfirewall preflight: {len(blocked_notes)} blocked")
    return blocked_notes


def publish(review_run: ReviewRun, note_plans: list[NotePlan], posted_state: dict[str, PostedNote], state_file: Path):
    discussions_endpoint = f"projects/{review_run.project_id}/merge_requests/{review_run.merge_request_iid}/discussions"
    for note_plan in note_plans:
        review_note = note_plan.review_note
        state_key = str(review_note.finding)
        try:
            match note_plan.action:
                case NoteAction.SKIP:
                    continue
                case NoteAction.UPDATE:
                    posted_note = posted_state[state_key]
                    call_gitlab_api(
                        review_run.hostname,
                        f"{discussions_endpoint}/{posted_note.discussion_id}/notes/{posted_note.note_id}",
                        method="PUT",
                        payload={"body": note_plan.body},
                    )
                    posted_note.body_digest = note_plan.body_digest
                    print(f"finding {review_note.finding}: updated in place")
                case NoteAction.POST:
                    discussion = create_discussion(review_run, discussions_endpoint, note_plan)
                    first_note = discussion["notes"][0]
                    posted_state[state_key] = PostedNote(
                        discussion_id=discussion["id"],
                        note_id=first_note["id"],
                        path=review_note.path,
                        line=review_note.line,
                        body_digest=note_plan.body_digest,
                        posted_inline=bool(first_note.get("position")),
                    )
                    lands_as = "inline" if first_note.get("position") else "general note"
                    print(f"finding {review_note.finding}: posted ({lands_as})")
                case _:
                    assert_never(note_plan.action)
        except FirewallBlockedError:
            sys.exit(
                f"finding {review_note.finding}: blocked by the firewall although the preflight passed. "
                "Reword it and rerun; notes already posted are skipped."
            )
        except GitLabApiError as error:
            sys.exit(f"finding {review_note.finding}: {error}\nFix it and rerun; notes already posted are skipped.")
        finally:
            state_file.write_text(
                json.dumps({finding: asdict(posted_note) for finding, posted_note in posted_state.items()}, indent=2)
                + "\n"
            )
    print(f"\nall notes live on {review_run.web_url}")


def create_discussion(review_run: ReviewRun, discussions_endpoint: str, note_plan: NotePlan) -> dict:
    review_note = note_plan.review_note
    line_position = note_plan.line_position
    if not note_plan.posts_inline or not line_position:
        return call_gitlab_api(review_run.hostname, discussions_endpoint, method="POST", payload={"body": note_plan.body})

    position = {
        "position_type": "text",
        "base_sha": review_run.base_commit,
        "start_sha": review_run.start_commit,
        "head_sha": review_run.head_commit,
        "old_path": line_position.old_path,
        "new_path": review_note.path,
        "new_line": review_note.line,
    }
    if line_position.kind == LineKind.UNCHANGED:
        position["old_line"] = line_position.old_line
    try:
        return call_gitlab_api(
            review_run.hostname, discussions_endpoint, method="POST", payload={"body": note_plan.body, "position": position}
        )
    except FirewallBlockedError:
        raise
    except GitLabApiError as error:
        if line_position.kind == LineKind.ADDED:
            raise
        print(f"finding {review_note.finding}: GitLab refused the unchanged-line anchor ({error}); posting it as a general note")
        note_plan.posts_inline = False
        note_plan.body = GENERAL_NOTE_PREFIX_TEMPLATE.format(path=review_note.path, line=review_note.line) + review_note.body
        note_plan.body_digest = hashlib.sha256(note_plan.body.encode()).hexdigest()
        return call_gitlab_api(review_run.hostname, discussions_endpoint, method="POST", payload={"body": note_plan.body})


if __name__ == "__main__":
    main()
