"""The run directory of one merge request review: its metadata, its review notes, and its worktree."""

import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

RUNS_ROOT = Path.home() / ".cache" / "mr-review"
META_FILE_NAME = "meta.json"
WORKTREE_DIRECTORY_NAME = "wt"
NOTES_DIRECTORY_NAME = "notes"
POSTED_STATE_FILE_NAME = "posted.json"
SYNTHESIZED_LEDGER_FILE_NAME = "ledger-synthesized.md"
FRONT_MATTER_DELIMITER = "---"
NOTE_FRONT_MATTER_KEYS = {"finding", "path", "line"}


@dataclass
class ReviewRun:
    hostname: str
    project_path: str
    project_id: int
    merge_request_iid: int
    title: str
    web_url: str
    author_username: str
    author_name: str
    source_branch: str
    target_branch: str
    base_commit: str
    start_commit: str
    head_commit: str
    repository_path: str
    ticket_key: str
    has_virtualenv: bool


@dataclass
class ReviewNote:
    finding: int
    path: str
    line: int
    body: str
    source_file: Path


def load_review_run(run_directory: Path) -> ReviewRun:
    meta_file = run_directory / META_FILE_NAME
    if not meta_file.exists():
        sys.exit(f"{meta_file} not found: run setup_review.py for this merge request first")
    return ReviewRun(**json.loads(meta_file.read_text()))


def run_git(repository: Path, *git_arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *git_arguments], capture_output=True, text=True
    )
    if completed.returncode:
        sys.exit(f"git {' '.join(git_arguments)} failed in {repository}: {completed.stderr.strip()}")
    return completed.stdout


def load_review_notes(run_directory: Path) -> tuple[ReviewNote, ...]:
    """Reads every notes/NN.md file.

    Each file starts with a front matter block naming the ledger finding and, for an
    inline note, the anchor in the MR head; without `path` and `line` it is a general note:

        ---
        finding: 4
        path: src/central_rest_api/api/hardware.py
        line: 285
        ---
        **Important — pagination links drop the filters**
        ...
    """
    notes_directory = run_directory / NOTES_DIRECTORY_NAME
    review_notes = []
    for note_file in sorted(notes_directory.glob("*.md")):
        front_matter_lines, body = _split_front_matter(note_file)
        fields = {}
        for front_matter_line in front_matter_lines:
            key, _, value = front_matter_line.partition(":")
            fields[key.strip()] = value.strip()
        unknown_keys = set(fields) - NOTE_FRONT_MATTER_KEYS
        if unknown_keys:
            sys.exit(f"{note_file}: unknown front matter keys {sorted(unknown_keys)}")
        if not fields.get("finding", "").isdigit():
            sys.exit(f"{note_file}: the front matter needs 'finding: <ledger number>'")
        if bool(fields.get("path")) != bool(fields.get("line")):
            sys.exit(f"{note_file}: give both 'path' and 'line', or neither")
        if fields.get("line") and not fields["line"].isdigit():
            sys.exit(f"{note_file}: 'line' must be a line number")
        if not body:
            sys.exit(f"{note_file}: the note body is empty")
        review_notes.append(
            ReviewNote(
                finding=int(fields["finding"]),
                path=fields.get("path", ""),
                line=int(fields.get("line") or 0),
                body=body,
                source_file=note_file,
            )
        )

    note_counts_by_finding = Counter(review_note.finding for review_note in review_notes)
    duplicated_findings = sorted(finding for finding, note_count in note_counts_by_finding.items() if note_count > 1)
    if duplicated_findings:
        sys.exit(f"more than one note file for findings {duplicated_findings}")
    return tuple(review_notes)


def _split_front_matter(note_file: Path) -> tuple[list[str], str]:
    lines = note_file.read_text().splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_DELIMITER:
        sys.exit(f"{note_file}: must start with a '---' front matter block")
    closing_index = next(
        (index for index in range(1, len(lines)) if lines[index].strip() == FRONT_MATTER_DELIMITER), 0
    )
    if not closing_index:
        sys.exit(f"{note_file}: the front matter block is never closed with '---'")
    return lines[1:closing_index], "\n".join(lines[closing_index + 1 :]).strip()
