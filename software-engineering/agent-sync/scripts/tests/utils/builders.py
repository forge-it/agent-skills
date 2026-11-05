import json
import shutil
from pathlib import Path

from agent_sync_common import ProcessIdentity
from lockctl_context import CommandContext
from lockctl_records import LockRecord
from lockctl_store import LockStore

from tests.utils.constants import (
    FIRST_PANE_ID,
    SAMPLE_HOLDER_PID,
    SAMPLE_OWNER_PID,
    SAMPLE_WORKTREE,
    STACK_LOCK,
    TRACKED_FILE_NAME,
)
from tests.utils.helpers import run_git_command
from tests.utils.samples import HELD_RECORD_TEMPLATE

STAT_FIELDS_AFTER_NAME = 50
STAT_START_TICKS_FIELD_INDEX = 19
BASH_BINARY = Path("/bin/bash")
GIT_IDENTITY_ARGUMENTS = ("-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false")


def build_git_repository(path: Path) -> Path:
    path.mkdir(parents=True)
    run_git_command(path, "init", "-q", "-b", "main")
    (path / TRACKED_FILE_NAME).write_text("committed content\n")
    run_git_command(path, "add", TRACKED_FILE_NAME)
    run_git_command(path, *GIT_IDENTITY_ARGUMENTS, "commit", "-q", "-m", "initial commit")
    return path


def add_linked_worktree(repository: Path, name: str) -> Path:
    worktree = repository.parent / name
    run_git_command(repository, "worktree", "add", "-q", str(worktree), "-b", name)
    return worktree


def build_bare_repository(source_repository: Path, bare_repository: Path) -> Path:
    run_git_command(source_repository, "clone", "-q", "--bare", str(source_repository), str(bare_repository))
    return bare_repository


def add_worktree_of_bare_repository(bare_repository: Path, worktree: Path) -> Path:
    run_git_command(bare_repository, "worktree", "add", "-q", str(worktree), "main")
    return worktree


def leave_a_merge_with_conflicts(repository: Path, worktree: Path):
    """Both branches changed the tracked file, so merging `main` into the worktree's branch stops
    half done: the file is unmerged and MERGE_HEAD exists in the worktree's git directory, while
    the repository's own worktree stays clean."""
    (repository / TRACKED_FILE_NAME).write_text("changed on main\n")
    run_git_command(repository, *GIT_IDENTITY_ARGUMENTS, "commit", "-q", "-a", "-m", "change on main")
    (worktree / TRACKED_FILE_NAME).write_text("changed on the worktree branch\n")
    run_git_command(worktree, *GIT_IDENTITY_ARGUMENTS, "commit", "-q", "-a", "-m", "change on the worktree branch")
    run_git_command(worktree, *GIT_IDENTITY_ARGUMENTS, "merge", "main", check=False)


def write_stat_of_a_process_named_in_invalid_utf8(process_directory: Path, pid: int, start_ticks: int):
    """A /proc/<pid>/stat whose process name is not UTF-8, which the kernel allows."""
    fields_after_name = ["S"] + ["0"] * (STAT_FIELDS_AFTER_NAME - 1)
    fields_after_name[STAT_START_TICKS_FIELD_INDEX] = str(start_ticks)
    entry = process_directory / str(pid)
    entry.mkdir(parents=True)
    (entry / "stat").write_bytes(f"{pid} (".encode() + b"\xff\xfe" + f") {' '.join(fields_after_name)}\n".encode())


def build_claude_named_shell(directory: Path) -> Path:
    directory.mkdir(parents=True)
    claude_binary = directory / "claude"
    shutil.copy2(BASH_BINARY, claude_binary)
    return claude_binary


def build_command_context(scope: str = SAMPLE_WORKTREE) -> CommandContext:
    return CommandContext(
        store=LockStore(Path("/unused-state-directory")),
        owner=ProcessIdentity(SAMPLE_OWNER_PID, 1),
        scope=scope,
        pane_id=FIRST_PANE_ID,
    )


def build_lock_record(**overrides: object) -> LockRecord:
    """A hold of the sample owner, taken from the sample worktree; the overrides say what differs."""
    payload = {
        **HELD_RECORD_TEMPLATE,
        "lock": STACK_LOCK,
        "owner_pid": SAMPLE_OWNER_PID,
        "owner_start_ticks": 1,
        "holder_pid": SAMPLE_HOLDER_PID,
        "holder_start_ticks": 1,
        "pane_id": FIRST_PANE_ID,
        "scope": SAMPLE_WORKTREE,
        "acquired_at": 0.0,
        **overrides,
    }
    record = LockRecord.from_json(json.dumps(payload))
    assert record, f"the sample record is not a valid lock record: {payload}"
    return record
