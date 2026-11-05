"""Who the caller is (owner, scope, pane) and how a hold is described relative to the caller."""

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

from agent_sync_common import (
    HERDR_PANE_ENVIRONMENT_VARIABLE,
    EnvironmentProblem,
    ProcessIdentity,
    find_owner_process,
    format_duration,
)

from lockctl_records import HoldKind, LockRecord
from lockctl_store import LockStore, locate_scope, locate_state_directory


@dataclass(frozen=True)
class CommandContext:
    store: LockStore
    owner: ProcessIdentity | None
    scope: str
    pane_id: str

    def require_owner(self) -> ProcessIdentity:
        assert self.owner, "this command needs an owner process"
        return self.owner

    def shares_owner_with(self, record: LockRecord) -> bool:
        return bool(self.owner) and record.owner == self.owner

    def owns(self, record: LockRecord) -> bool:
        """Subagents run inside their orchestrator's process, so the owner alone does not make a
        hold yours: it must also have been taken from this scope."""
        return self.shares_owner_with(record) and record.scope == self.scope


def build_context(owner_required: bool) -> CommandContext:
    working_directory = Path.cwd()
    store = LockStore(locate_state_directory(working_directory))
    try:
        owner = find_owner_process()
    except EnvironmentProblem:
        if owner_required:
            raise
        owner = None
    return CommandContext(
        store,
        owner,
        locate_scope(working_directory),
        os.environ.get(HERDR_PANE_ENVIRONMENT_VARIABLE, ""),
    )


def describe_holder(record: LockRecord) -> str:
    title = f' "{record.herdr_title}"' if record.herdr_title else ""
    branch = f", branch {record.branch}" if record.branch else ""
    worktree = f", worktree {record.scope}" if record.scope else ""
    purpose = f", purpose: {record.purpose}" if record.purpose else ""
    run_process = f", run pid {record.holder_pid}" if record.hold_kind == HoldKind.RUN else ""
    held_for = format_duration(time.time() - record.acquired_at)
    return (
        f"pane {record.pane_id or '-'}{title} (owner pid {record.owner_pid}{run_process})"
        f"{branch}{worktree}{purpose}, held for {held_for}"
    )


def describe_other_hold(context: CommandContext, record: LockRecord) -> str:
    """A hold of the caller's own session that was taken from another worktree is named as such:
    the owner process cannot tell the subagents inside it apart, so the worktree decides."""
    holder = describe_holder(record)
    if not context.shares_owner_with(record):
        return holder
    return (
        f"{holder}; that is your own session, but the hold was taken from another worktree, "
        "so only that worktree can use or release it"
    )


def describe_own_hold(record: LockRecord) -> str:
    """Why a lock the caller already holds still answered busy: the caller's own `run` is the
    holder, or another of the caller's commands took the lock at the same moment."""
    purpose = record.purpose or "no purpose"
    match record.hold_kind:
        case HoldKind.RUN:
            return (
                f"lock {record.lock} is held by your own `run` (pid {record.holder_pid}, {purpose}), "
                "which holds it only while its command runs; wait for it to finish, or `release` it to stop the command"
            )
        case HoldKind.ACQUIRE:
            return (
                f"lock {record.lock} is held by you through `acquire` (holder pid {record.holder_pid}, {purpose}): "
                "another of your commands took it at the same moment; `check` confirms it, `release` frees it"
            )
        case _:
            assert_never(record.hold_kind)


def describe_busy(context: CommandContext, name: str, blocking_record: LockRecord | None, wait_seconds: float) -> str:
    prefix = f"gave up after {format_duration(wait_seconds)}: " if wait_seconds else ""
    if blocking_record and context.owns(blocking_record):
        return f"{prefix}{describe_own_hold(blocking_record)}"
    holder = (
        describe_other_hold(context, blocking_record)
        if blocking_record
        else "a holder whose record is not readable yet"
    )
    return f"{prefix}lock {name} is held by {holder}; see `lockctl.py status {name}`"
