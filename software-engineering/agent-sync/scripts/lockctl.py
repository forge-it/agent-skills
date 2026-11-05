#!/usr/bin/env python3
"""Named locks per repository for sessions that share one checkout.

A lock is an flock on <git-common-dir>/agent-sync/<name>.lock. `acquire` hands it to a detached
holder process that watches the owning `claude` process and frees the lock when it dies; `run`
holds it itself while its command runs. The holder also writes its own and its owner's identity
into the .lock file, which is never deleted, so a lock whose record went missing can still be
found and freed. <name>.json is the holder's record (who, where, why, and the owner pane's herdr
state), <name>.activities/ has one file per `run` command that is executing under the lock, and
events.log is the history.

A hold belongs to its owner (the `claude` process) and to its scope, the git toplevel of the
directory it was taken from: subagents run inside their orchestrator's process, so the owner
alone cannot tell them apart.
"""

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import assert_never

from agent_sync_common import (
    DEFAULT_POLL_SECONDS,
    ERROR_REPLY_PREFIX,
    POLL_SECONDS_ENVIRONMENT_VARIABLE,
    READY_MESSAGE,
    EnvironmentProblem,
    ExitCode,
    ProcessIdentity,
    format_timestamp,
    install_stop_signal_handlers,
    read_seconds_setting,
    signal_readiness,
    terminate_process,
)

from lockctl_arguments import parse_arguments
from lockctl_context import CommandContext, build_context, describe_busy, describe_holder, describe_other_hold
from lockctl_hold import (
    AcquireOutcome,
    AcquireResult,
    attempt_acquire,
    run_holding_lock,
    run_inside_hold,
)
from lockctl_holder import HolderSession, HoldRequest
from lockctl_records import HoldKind, LockEvent, LockRecord, TheftNote
from lockctl_report import build_report, render_report
from lockctl_steal import StealPolicy
from lockctl_store import LockInspection, LockStore
from lockctl_supervisor import RELEASE_GRACE_SECONDS, stop_running_commands

EXIT_INTERRUPTED = 130


def command_acquire(arguments: argparse.Namespace) -> ExitCode:
    context = build_context(owner_required=True)
    result = attempt_acquire(context, arguments.lock, arguments.purpose, arguments.wait)
    return report_acquire(context, arguments.lock, result, arguments.wait)


def report_acquire(
    context: CommandContext,
    name: str,
    result: AcquireResult,
    wait_seconds: float,
    stolen_from: LockRecord | None = None,
) -> ExitCode:
    """Success is announced only once this session holds the lock, so a `steal` that loses the
    race to a waiter does not claim a theft it did not complete."""
    owner = context.require_owner()
    match result.outcome:
        case AcquireOutcome.ACQUIRED:
            if stolen_from:
                print(f"stole lock {name} from pane {stolen_from.pane_id or '-'} (owner pid {stolen_from.owner_pid})")
            print(
                f"acquired {name} (owner pid {owner.pid}, pane {context.pane_id or '-'}, "
                f"holder pid {result.holder_pid})"
            )
            return ExitCode.OK
        case AcquireOutcome.ALREADY_HELD:
            print(f"lock {name} is already held by you (holder pid {result.holder_pid})")
            return ExitCode.OK
        case AcquireOutcome.BUSY:
            message = describe_busy(context, name, result.blocking_record, wait_seconds)
            if stolen_from:
                message = f"steal lost the race: {message}"
            print(message, file=sys.stderr)
            return ExitCode.BUSY
        case _:
            assert_never(result.outcome)


def command_release(arguments: argparse.Namespace) -> ExitCode:
    context = build_context(owner_required=True)
    name = arguments.lock
    inspection = context.store.inspect(name)
    record = inspection.record

    if not inspection.held:
        print(f"lock {name} is free: you do not hold it", file=sys.stderr)
        return ExitCode.REFUSED
    if not record or not context.owns(record):
        holder = describe_other_hold(context, record) if record else "a holder whose record is not readable"
        print(f"lock {name} is not held by you, it is held by {holder}", file=sys.stderr)
        return ExitCode.REFUSED

    stop_running_commands(context.store, name)
    if not terminate_process(record.holder, RELEASE_GRACE_SECONDS):
        raise EnvironmentProblem(f"the holder of lock {name} (pid {record.holder_pid}) did not exit")

    context.store.append_event(
        LockEvent.RELEASE, name, record.owner_pid, record.pane_id, f"holder_pid={record.holder_pid}"
    )
    print(f"released {name}")
    return ExitCode.OK


def command_check(arguments: argparse.Namespace) -> ExitCode:
    context = build_context(owner_required=True)
    name = arguments.lock
    inspection = context.store.inspect(name)
    record = inspection.record

    if inspection.held and record and context.owns(record):
        print(f"lock {name} is held by you since {format_timestamp(record.acquired_at)} (pane {record.pane_id or '-'})")
        return ExitCode.OK

    theft_note = context.store.read_theft_note(name)
    theft_remark = ""
    if (
        theft_note
        and ProcessIdentity(theft_note.victim_owner_pid, theft_note.victim_owner_start_ticks) == context.owner
    ):
        stolen_at = format_timestamp(theft_note.stolen_at)
        theft_remark = f"; it was stolen from you at {stolen_at} by pane {theft_note.thief_pane_id or '-'}"

    if not inspection.held:
        print(f"lock {name} is free: you do not hold it{theft_remark}")
    elif record and context.shares_owner_with(record):
        print(
            f"lock {name} is held by your own session from another worktree, not by this one: "
            f"{describe_holder(record)}{theft_remark}"
        )
    else:
        holder = describe_holder(record) if record else "a holder whose record is not readable"
        print(f"lock {name} is held by someone else: {holder}{theft_remark}")
    return ExitCode.REFUSED


def command_status(arguments: argparse.Namespace) -> ExitCode:
    context = build_context(owner_required=False)
    policy = StealPolicy(context.store)
    names = [arguments.lock] if arguments.lock else context.store.lock_names()
    reports = [build_report(context, context.store.inspect(name), policy) for name in names]

    if arguments.json:
        print(json.dumps([asdict(report) for report in reports], indent=2))
    elif reports:
        print("\n".join(render_report(report) for report in reports))
    else:
        print("no locks yet")
    return ExitCode.OK


def command_steal(arguments: argparse.Namespace) -> ExitCode:
    context = build_context(owner_required=True)
    name = arguments.lock
    inspection = context.store.inspect(name)

    if not inspection.held:
        result = attempt_acquire(context, name, arguments.purpose, wait_seconds=0.0)
        return report_acquire(context, name, result, wait_seconds=0.0)
    record = inspection.record
    if not record:
        print(
            f"steal refused: lock {name} is held but its holder record is not readable (it may be starting up)",
            file=sys.stderr,
        )
        return ExitCode.BUSY
    if context.owns(record):
        print(f"steal refused: you already hold lock {name}", file=sys.stderr)
        return ExitCode.BUSY

    if not arguments.force:
        refusal = describe_steal_refusal(context, inspection)
        if refusal:
            print(
                f"steal refused: lock {name} is held by {describe_other_hold(context, record)}: {refusal}",
                file=sys.stderr,
            )
            return ExitCode.BUSY

    current_record = context.store.inspect(name).record
    if not current_record or current_record.holder != record.holder:
        print(
            f"steal refused: lock {name} changed hands while it was being assessed; read `status` again",
            file=sys.stderr,
        )
        return ExitCode.BUSY
    stop_running_commands(context.store, name)
    if not terminate_process(record.holder):
        raise EnvironmentProblem(f"could not stop the holder of lock {name} (pid {record.holder_pid})")

    result = attempt_acquire(context, name, arguments.purpose, wait_seconds=0.0)
    record_theft(context, record, result, forced=arguments.force)
    return report_acquire(context, name, result, wait_seconds=0.0, stolen_from=record)


def describe_steal_refusal(context: CommandContext, inspection: LockInspection) -> str:
    """Empty when the holder may be stolen from."""
    assert inspection.record, "a steal is only assessed for a hold with a record"
    if inspection.record_missing:
        return "its record is missing, so the holder's state cannot be verified"
    assessment = StealPolicy(context.store).assess(inspection.record)
    return "" if assessment.allowed else assessment.reason


def record_theft(context: CommandContext, victim: LockRecord, result: AcquireResult, forced: bool):
    """Written once the outcome is known, and naming whoever holds the lock now: the thief, or the
    waiter that took the freed lock before the thief could. Without a known holder there is nothing
    true to tell the victim."""
    owner = context.require_owner()
    match result.outcome:
        case AcquireOutcome.ACQUIRED | AcquireOutcome.ALREADY_HELD:
            new_holder_pane, new_holder_owner_pid = context.pane_id, owner.pid
        case AcquireOutcome.BUSY:
            winner = result.blocking_record
            new_holder_pane = winner.pane_id if winner else ""
            new_holder_owner_pid = winner.owner_pid if winner else 0
        case _:
            assert_never(result.outcome)

    if new_holder_owner_pid:
        context.store.write_theft_note(
            TheftNote(
                lock=victim.lock,
                stolen_at=time.time(),
                thief_pane_id=new_holder_pane,
                thief_owner_pid=new_holder_owner_pid,
                victim_owner_pid=victim.owner_pid,
                victim_owner_start_ticks=victim.owner_start_ticks,
                victim_pane_id=victim.pane_id,
                forced=forced,
            )
        )
    forced_remark = " forced=yes" if forced else ""
    lost_remark = f" lost_race_by_owner_pid={owner.pid}" if result.outcome == AcquireOutcome.BUSY else ""
    context.store.append_event(
        LockEvent.STEAL,
        victim.lock,
        new_holder_owner_pid,
        new_holder_pane,
        f"from_owner_pid={victim.owner_pid} from_pane={victim.pane_id or '-'}{forced_remark}{lost_remark}",
    )


def command_run(arguments: argparse.Namespace) -> int:
    context = build_context(owner_required=True)
    name = arguments.lock
    command = arguments.command

    existing = context.store.inspect(name)
    if existing.record and context.owns(existing.record) and existing.record.hold_kind == HoldKind.ACQUIRE:
        exit_code = run_inside_hold(context, existing.record, command)
        if exit_code is not None:
            return exit_code
    return run_holding_lock(context, name, command, arguments.purpose, arguments.wait)


def command_hold(arguments: argparse.Namespace) -> ExitCode:
    """The detached holder process; started by `acquire`, never by a person. It inherits the flock
    that `acquire` took, so the lock never has an unowned moment between the two."""
    store = LockStore(Path(arguments.state_directory))
    owner = ProcessIdentity(arguments.owner_pid, arguments.owner_start_ticks)
    os.set_inheritable(arguments.lock_file_descriptor, False)
    stop_requested = install_stop_signal_handlers()

    try:
        poll_seconds = read_seconds_setting(POLL_SECONDS_ENVIRONMENT_VARIABLE, DEFAULT_POLL_SECONDS)
        session = HolderSession(
            store, HoldRequest(arguments.lock, owner, arguments.scope, arguments.purpose, HoldKind.ACQUIRE)
        )
        session.publish()
    except (EnvironmentProblem, OSError) as failure:
        signal_readiness(arguments.readiness_file_descriptor, f"{ERROR_REPLY_PREFIX}holder could not start: {failure}")
        return ExitCode.ENVIRONMENT
    if not signal_readiness(arguments.readiness_file_descriptor, READY_MESSAGE):
        session.withdraw(LockEvent.RELEASE)
        return ExitCode.OK

    end_event = None
    try:
        while not stop_requested.is_set():
            if session.owner_is_gone():
                end_event = LockEvent.EXPIRE
                break
            session.refresh_if_due()
            stop_requested.wait(poll_seconds)
    finally:
        try:
            stop_running_commands(store, arguments.lock)
        finally:
            session.withdraw(end_event)
    return ExitCode.OK


def main(command_line_arguments: Sequence[str]) -> int:
    handlers: dict[str, Callable[[argparse.Namespace], int]] = {
        "acquire": command_acquire,
        "release": command_release,
        "check": command_check,
        "status": command_status,
        "run": command_run,
        "steal": command_steal,
        "_hold": command_hold,
    }
    arguments = parse_arguments(command_line_arguments)
    try:
        return int(handlers[arguments.command_name](arguments))
    except EnvironmentProblem as problem:
        print(f"lockctl: error: {problem}", file=sys.stderr)
        return ExitCode.ENVIRONMENT
    except OSError as failure:
        print(f"lockctl: error: {failure}", file=sys.stderr)
        return ExitCode.ENVIRONMENT
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
