"""Prepare the run directory for reviewing one merge request.

Writes meta.json and mr-description.md, and puts a detached worktree on the MR head at
<run>/wt, after fetching both branches. Rerunning it after the author pushes moves the
worktree to the new head and keeps notes/ and posted.json.

Usage: python3 -B setup_review.py <merge request URL> [--repository <local clone>]
"""

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from urllib.parse import quote

from gitlab_api import call_gitlab_api
from review_run import META_FILE_NAME, RUNS_ROOT, WORKTREE_DIRECTORY_NAME, ReviewRun, run_git

MERGE_REQUEST_URL_PATTERN = re.compile(
    r"^https?://(?P<hostname>[^/]+)/(?P<project_path>.+?)/-/merge_requests/(?P<iid>\d+)"
)
TICKET_KEY_PATTERN = re.compile(r"\bSYN-\d+\b")
PROJECTS_ROOT = Path.home() / "Projects"
MR_DESCRIPTION_FILE_NAME = "mr-description.md"
VIRTUALENV_DIRECTORY_NAME = ".venv"


def main():
    argument_parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argument_parser.add_argument("merge_request_url")
    argument_parser.add_argument("--repository", type=Path, help="local clone (default: ~/Projects/<project name>)")
    arguments = argument_parser.parse_args()

    url_match = MERGE_REQUEST_URL_PATTERN.match(arguments.merge_request_url)
    if not url_match:
        sys.exit(f"not a merge request URL: {arguments.merge_request_url}")
    hostname = url_match["hostname"]
    project_path = url_match["project_path"]
    merge_request_iid = int(url_match["iid"])

    merge_request = call_gitlab_api(
        hostname, f"projects/{quote(project_path, safe='')}/merge_requests/{merge_request_iid}"
    )
    repository = arguments.repository or PROJECTS_ROOT / project_path.rsplit("/", 1)[-1]
    origin_url = run_git(repository, "remote", "get-url", "origin").strip()
    if project_path not in origin_url:
        sys.exit(f"{repository} has origin {origin_url}, not {project_path}: pass --repository")

    source_branch = merge_request["source_branch"]
    target_branch = merge_request["target_branch"]
    run_git(repository, "fetch", "origin", target_branch, source_branch)
    head_commit = merge_request["diff_refs"]["head_sha"]
    fetched_head = run_git(repository, "rev-parse", f"origin/{source_branch}").strip()
    if fetched_head != head_commit:
        sys.exit(
            f"origin/{source_branch} is {fetched_head[:12]} but the MR head is {head_commit[:12]}: "
            "a push is still being processed, rerun in a minute"
        )

    run_directory = RUNS_ROOT / f"{repository.name}-{merge_request_iid}"
    run_directory.mkdir(parents=True, exist_ok=True)
    worktree = run_directory / WORKTREE_DIRECTORY_NAME
    if worktree.exists():
        if run_git(worktree, "status", "--porcelain").strip():
            sys.exit(f"{worktree} has local changes; reviewers must never edit it. Inspect it before rerunning.")
        run_git(worktree, "checkout", "--quiet", "--detach", head_commit)
    else:
        run_git(repository, "worktree", "prune")
        run_git(repository, "worktree", "add", "--quiet", "--detach", str(worktree), head_commit)

    description = merge_request.get("description") or ""
    ticket_match = TICKET_KEY_PATTERN.search(f"{merge_request['title']}\n{description}\n{source_branch}")
    review_run = ReviewRun(
        hostname=hostname,
        project_path=project_path,
        project_id=merge_request["project_id"],
        merge_request_iid=merge_request_iid,
        title=merge_request["title"],
        web_url=merge_request["web_url"],
        author_username=merge_request["author"]["username"],
        author_name=merge_request["author"]["name"],
        source_branch=source_branch,
        target_branch=target_branch,
        base_commit=merge_request["diff_refs"]["base_sha"],
        start_commit=merge_request["diff_refs"]["start_sha"],
        head_commit=head_commit,
        repository_path=str(repository),
        ticket_key=ticket_match.group(0) if ticket_match else "",
        has_virtualenv=(repository / VIRTUALENV_DIRECTORY_NAME).exists(),
    )
    (run_directory / META_FILE_NAME).write_text(json.dumps(asdict(review_run), indent=2) + "\n")
    (run_directory / MR_DESCRIPTION_FILE_NAME).write_text(f"# {review_run.title}\n\n{description}\n")

    changed_files = run_git(worktree, "diff", "--name-only", review_run.base_commit, head_commit).splitlines()
    print(f"run directory : {run_directory}")
    print(f"worktree      : {worktree} (detached at {head_commit[:12]})")
    print(f"base          : {review_run.base_commit}  ({target_branch})")
    print(f"author        : {review_run.author_name} ({review_run.author_username})")
    print(f"ticket        : {review_run.ticket_key or 'none found: ask the operator for the spec'}")
    print(f"virtualenv    : {repository / VIRTUALENV_DIRECTORY_NAME if review_run.has_virtualenv else 'none: static review only'}")
    print(f"changed files : {len(changed_files)}")


if __name__ == "__main__":
    main()
