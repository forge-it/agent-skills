"""Taking a lock and holding it: the acquire protocol, and `run`, which holds the lock itself or
slips into a hold its caller already has."""

import os
import shlex
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from agent_sync_common import (
    ExitCode,
    format_duration,
    install_stop_signal_handlers,
    is_same_process_alive,
    launch_detached,
)

from lockctl_context import CommandContext, describe_busy, describe_holder
from lockctl_holder import HolderSession, HoldRequest
from lockctl_records import HoldKind, LockRecord
from lockctl_store import LockStore
from lockctl_supervisor import CommandActivity, CommandSupervisor, stop_running_commands

ENTRY_SCRIPT_NAME = "lockctl.py"
BUSY_GRACE_SECONDS = 0.25
WAIT_POLL_SECONDS = 0.1


class AcquireOutcome(StrEnum):
    ACQUIRED = "acquired"
    ALREADY_HELD = "already_held"
    BUSY = "busy"


@dataclass(frozen=True)
class AcquireResult:
    outcome: AcquireOutcome
    holder_pid: int = 0
    blocking_record: LockRecord | None = None


def wait_for_lock(store: LockStore, lock_file_descriptor: int, wait_seconds: float) -> bool:
    """Polls rather than blocking, so the wait can end by a deadline; at least BUSY_GRACE_SECONDS
    even for a no-wait acquire, because a concurrent `status` probes the flock for a moment."""
    deadline = time.monotonic() + max(wait_seconds, BUSY_GRACE_SECONDS)
    while not store.try_lock(lock_file_descriptor):
        if time.monotonic() >= deadline:
            return False
        time.sleep(WAIT_POLL_SECONDS)
    return True


def announce_wait(name: str, record: LockRecord | None, wait_seconds: float):
    if wait_seconds and record:
        print(
            f"waiting up to {format_duration(wait_seconds)} for lock {name}, held by {describe_holder(record)}",
            file=sys.stderr,
        )


def take_over_lock(context: CommandContext, name: str):
    """Runs right after the flock was won and before anything is published. Commands that the
    previous hold left running (a `run` process that was killed leaves its command behind) are
    stopped now, while this process owns the flock, so the new hold never shares the resource
    with them. The other way out, keeping the lock busy until such a command ends, could leave it
    unusable for as long as the command lives."""
    stop_running_commands(context.store, name)
    context.store.discard_record(name)
    context.store.clear_theft_note_of(name, context.require_owner())


def attempt_acquire(context: CommandContext, name: str, purpose: str, wait_seconds: float) -> AcquireResult:
    """Only a hold taken with `acquire` is entered again, and only by its owner from the scope it
    was taken from; a `run` hold lasts as long as its command, so no second hold can be built on
    it."""
    owner = context.require_owner()
    existing = context.store.inspect(name)
    if existing.record and context.owns(existing.record) and existing.record.hold_kind == HoldKind.ACQUIRE:
        return AcquireResult(AcquireOutcome.ALREADY_HELD, holder_pid=existing.record.holder_pid)
    if existing.held:
        announce_wait(name, existing.record, wait_seconds)

    lock_file_descriptor = context.store.open_lock_file(name)
    try:
        if not wait_for_lock(context.store, lock_file_descriptor, wait_seconds):
            return AcquireResult(AcquireOutcome.BUSY, blocking_record=context.store.inspect(name).record)

        take_over_lock(context, name)
        holder_pid = launch_detached(
            [
                sys.executable,
                str(Path(__file__).resolve().with_name(ENTRY_SCRIPT_NAME)),
                "_hold",
                name,
                f"--state-directory={context.store.state_directory}",
                f"--owner-pid={owner.pid}",
                f"--owner-start-ticks={owner.start_ticks}",
                f"--scope={context.scope}",
                f"--lock-file-descriptor={lock_file_descriptor}",
                f"--purpose={purpose}",
            ],
            inherited_file_descriptors=(lock_file_descriptor,),
        )
    finally:
        os.close(lock_file_descriptor)
    return AcquireResult(AcquireOutcome.ACQUIRED, holder_pid=holder_pid)


def run_inside_hold(context: CommandContext, hold: LockRecord, command: Sequence[str]) -> int | None:
    """Runs the command under a lock this session took with `acquire`, registered as an activity
    so the lock cannot be stolen meanwhile. None when the hold ended before the command could
    start, and the caller takes the lock itself."""
    owner = context.require_owner()
    stop_requested = install_stop_signal_handlers()
    activity = CommandActivity(context.store, hold.lock, command)
    try:
        activity.register()
        if not is_same_process_alive(hold.holder):
            return None
        supervisor = CommandSupervisor(activity, stop_requested, owner, watched_holder=hold.holder)
        return supervisor.run(command).exit_code
    finally:
        activity.deregister()


def run_holding_lock(
    context: CommandContext, name: str, command: Sequence[str], purpose: str, wait_seconds: float
) -> int:
    owner = context.require_owner()
    existing = context.store.inspect(name)
    if existing.held:
        announce_wait(name, existing.record, wait_seconds)

    lock_file_descriptor = context.store.open_lock_file(name)
    try:
        if not wait_for_lock(context.store, lock_file_descriptor, wait_seconds):
            blocking_record = context.store.inspect(name).record
            print(describe_busy(context, name, blocking_record, wait_seconds), file=sys.stderr)
            return ExitCode.BUSY

        take_over_lock(context, name)
        stop_requested = install_stop_signal_handlers()
        session = HolderSession(
            context.store,
            HoldRequest(name, owner, context.scope, purpose or f"run: {shlex.join(command)}", HoldKind.RUN),
        )
        activity = CommandActivity(context.store, name, command)
        end_event = None
        try:
            activity.register()
            session.publish()
            outcome = CommandSupervisor(activity, stop_requested, owner, session=session).run(command)
            end_event = outcome.end_event
        finally:
            session.withdraw(end_event)
            activity.deregister()
        return outcome.exit_code
    finally:
        os.close(lock_file_descriptor)
