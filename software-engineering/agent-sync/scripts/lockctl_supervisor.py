"""Running a command under a lock: its activity record, the supervisor that stops its whole process
group when the run must end early, and the helper that stops every command under a lock."""

import shlex
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from agent_sync_common import (
    DEFAULT_POLL_SECONDS,
    POLL_SECONDS_ENVIRONMENT_VARIABLE,
    UNREADABLE_STAT_ERRORS,
    EnvironmentProblem,
    ProcessIdentity,
    is_same_process_alive,
    read_own_identity,
    read_process_stat,
    read_seconds_setting,
    terminate_group_of,
    terminate_process,
    terminate_process_group,
)

from lockctl_holder import HolderSession
from lockctl_records import ActivityRecord, LockEvent
from lockctl_store import LockStore

RELEASE_GRACE_SECONDS = 10.0
RUN_POLL_CEILING_SECONDS = 0.5
COMMAND_TERMINATION_GRACE_SECONDS = 2.0
COMMAND_SUMMARY_LIMIT = 120
EXIT_COMMAND_NOT_EXECUTABLE = 126
EXIT_COMMAND_NOT_FOUND = 127
EXIT_SIGNAL_OFFSET = 128


class StopReason(StrEnum):
    REQUESTED = "it was asked to stop (lock released or stolen, or a signal)"
    OWNER_GONE = "the owning session exited"
    HOLD_LOST = "the acquired lock it ran inside ended"

    @property
    def end_event(self) -> LockEvent | None:
        """Release and steal log their own event; only the owner's death is logged by the holder."""
        return LockEvent.EXPIRE if self is StopReason.OWNER_GONE else None


@dataclass(frozen=True)
class CommandOutcome:
    exit_code: int
    end_event: LockEvent | None


class CommandActivity:
    """One `run` command, registered as an activity of the lock for as long as it executes."""

    def __init__(self, store: LockStore, lock_name: str, command: Sequence[str]):
        identity = read_own_identity()
        self._store = store
        self._record = ActivityRecord(
            lock=lock_name,
            run_pid=identity.pid,
            run_start_ticks=identity.start_ticks,
            command=self._summarize_command(command),
            started_at=time.time(),
        )

    @staticmethod
    def _summarize_command(command: Sequence[str]) -> str:
        joined = shlex.join(command)
        if len(joined) <= COMMAND_SUMMARY_LIMIT:
            return joined
        return f"{joined[: COMMAND_SUMMARY_LIMIT - 3]}..."

    def register(self):
        self._store.write_activity(self._record)

    def attach_group(self, process_group_id: int):
        """The group only matters to whoever has to finish off a command whose `run` process was
        killed; failing to record it must not take the running command down."""
        try:
            leader_stat = read_process_stat(process_group_id)
        except UNREADABLE_STAT_ERRORS:
            return
        if not leader_stat:
            return
        self._record.process_group_id = process_group_id
        self._record.process_group_leader_start_ticks = leader_stat.start_ticks
        try:
            self._store.write_activity(self._record)
        except OSError:
            return

    def deregister(self):
        try:
            self._store.remove_activity(self._record.lock, self._record.run_process)
        except OSError:
            return


class CommandSupervisor:
    """Runs a command in its own process group and stops that whole group, so the grandchildren
    of a shell command go with it, when the run must end early: it was told to stop, its owner
    exited, or the acquired lock it ran inside ended."""

    def __init__(
        self,
        activity: CommandActivity,
        stop_requested: threading.Event,
        owner: ProcessIdentity,
        session: HolderSession | None = None,
        watched_holder: ProcessIdentity | None = None,
    ):
        self._activity = activity
        self._stop_requested = stop_requested
        self._owner = owner
        self._session = session
        self._watched_holder = watched_holder

    def run(self, command: Sequence[str]) -> CommandOutcome:
        try:
            child = subprocess.Popen(command, process_group=0)
        except FileNotFoundError:
            print(f"lockctl: command not found: {command[0]}", file=sys.stderr)
            return CommandOutcome(EXIT_COMMAND_NOT_FOUND, LockEvent.RELEASE)
        except PermissionError:
            print(f"lockctl: command not executable: {command[0]}", file=sys.stderr)
            return CommandOutcome(EXIT_COMMAND_NOT_EXECUTABLE, LockEvent.RELEASE)

        try:
            self._activity.attach_group(child.pid)
            return self._wait_for(child)
        finally:
            terminate_process_group(child.pid, COMMAND_TERMINATION_GRACE_SECONDS)
            child.wait()

    def _wait_for(self, child: subprocess.Popen[bytes]) -> CommandOutcome:
        poll_seconds = min(
            read_seconds_setting(POLL_SECONDS_ENVIRONMENT_VARIABLE, DEFAULT_POLL_SECONDS), RUN_POLL_CEILING_SECONDS
        )
        while True:
            try:
                return CommandOutcome(self._exit_code(child.wait(timeout=poll_seconds)), LockEvent.RELEASE)
            except subprocess.TimeoutExpired:
                pass

            if self._session:
                self._session.refresh_if_due()
            stop_reason = self._find_stop_reason()
            if stop_reason:
                print(f"lockctl: stopping the command: {stop_reason}", file=sys.stderr)
                terminate_process_group(child.pid, COMMAND_TERMINATION_GRACE_SECONDS)
                return CommandOutcome(self._exit_code(child.wait()), stop_reason.end_event)

    def _find_stop_reason(self) -> StopReason | None:
        if not is_same_process_alive(self._owner):
            return StopReason.OWNER_GONE
        if self._stop_requested.is_set():
            return StopReason.REQUESTED
        if self._watched_holder and not is_same_process_alive(self._watched_holder):
            return StopReason.HOLD_LOST
        return None

    @staticmethod
    def _exit_code(return_code: int) -> int:
        return EXIT_SIGNAL_OFFSET + abs(return_code) if return_code < 0 else return_code


def stop_running_commands(store: LockStore, name: str):
    """Ends every command that runs under the lock, and is called while the flock is still held by
    whoever is ending the hold, so no waiter can take the lock before the commands are gone. The
    `run` process goes first: it stops its own command and exits, so a `run` that holds the flock
    lets go of it only once its command is gone. The recorded process group goes second: it is all
    that is left of a command whose `run` process was killed."""
    for activity in store.live_activities(name):
        if not terminate_process(activity.run_process, RELEASE_GRACE_SECONDS):
            raise EnvironmentProblem(f"a command under lock {name} (run pid {activity.run_pid}) did not exit")
        if not terminate_group_of(activity.command_group):
            raise EnvironmentProblem(
                f"a command under lock {name} (process group {activity.process_group_id}) did not exit"
            )
        store.remove_activity(name, activity.run_process)
