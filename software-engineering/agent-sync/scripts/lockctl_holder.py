"""What a holder process does while it holds a lock: stamp the lock file, publish the record, and
keep the owner pane's herdr state current."""

import os
import time
from dataclasses import dataclass
from pathlib import Path

from agent_sync_common import (
    HERDR_PANE_ENVIRONMENT_VARIABLE,
    HERDR_SESSION_ENVIRONMENT_VARIABLE,
    HerdrStatus,
    PaneReading,
    ProcessIdentity,
    is_same_process_alive,
    read_own_identity,
    read_pane_reading,
    read_seconds_setting,
)

from lockctl_records import DEFAULT_IDLE_SECONDS, HolderStamp, HoldKind, LockEvent, LockRecord
from lockctl_store import LockStore, run_git

IDLE_SECONDS_ENVIRONMENT_VARIABLE = "AGENT_SYNC_IDLE_SECONDS"
REFRESH_SECONDS_ENVIRONMENT_VARIABLE = "AGENT_SYNC_REFRESH_SECONDS"
DEFAULT_REFRESH_SECONDS = 30.0


@dataclass(frozen=True)
class PaneState:
    """What a record says about the owner pane; the record is rewritten only when this changes."""

    herdr_status: HerdrStatus
    herdr_title: str
    idle_since: float | None
    idle_state_change_sequence: int | None


@dataclass(frozen=True)
class HoldRequest:
    lock_name: str
    owner: ProcessIdentity
    scope: str
    purpose: str
    hold_kind: HoldKind


class HolderSession:
    """What a holder process (the detached one, or `run` itself) does while it holds a lock:
    stamp the lock file, publish the record, keep the owner pane's herdr state current, and take
    both away at the end. The idle threshold is read once, here, and recorded: a thief cannot
    shorten it with its own environment."""

    def __init__(self, store: LockStore, request: HoldRequest):
        self._store = store
        self._lock_name = request.lock_name
        self._owner = request.owner
        self._scope = request.scope
        self._purpose = request.purpose
        self._hold_kind = request.hold_kind
        self._identity = read_own_identity()
        self._idle_threshold_seconds = read_seconds_setting(IDLE_SECONDS_ENVIRONMENT_VARIABLE, DEFAULT_IDLE_SECONDS)
        self._refresh_seconds = read_seconds_setting(REFRESH_SECONDS_ENVIRONMENT_VARIABLE, DEFAULT_REFRESH_SECONDS)
        self._last_refresh = float("-inf")
        self._record: LockRecord | None = None
        self._written_state: PaneState | None = None

    def publish(self):
        working_directory = Path.cwd()
        self._store.write_holder_stamp(
            self._lock_name,
            HolderStamp(
                holder_pid=self._identity.pid,
                holder_start_ticks=self._identity.start_ticks,
                owner_pid=self._owner.pid,
                owner_start_ticks=self._owner.start_ticks,
                scope=self._scope,
                hold_kind=self._hold_kind,
            ),
        )
        self._record = LockRecord(
            lock=self._lock_name,
            owner_pid=self._owner.pid,
            owner_start_ticks=self._owner.start_ticks,
            holder_pid=self._identity.pid,
            holder_start_ticks=self._identity.start_ticks,
            pane_id=os.environ.get(HERDR_PANE_ENVIRONMENT_VARIABLE, ""),
            herdr_session=os.environ.get(HERDR_SESSION_ENVIRONMENT_VARIABLE, ""),
            working_directory=str(working_directory),
            branch=(run_git(["branch", "--show-current"], working_directory) or "").strip(),
            purpose=self._purpose,
            acquired_at=time.time(),
            hold_kind=self._hold_kind,
            scope=self._scope,
            idle_threshold_seconds=self._idle_threshold_seconds,
        )
        self._store.write_record(self._record)
        self._written_state = self._observed_state()
        self._store.append_event(
            LockEvent.ACQUIRE,
            self._lock_name,
            self._owner.pid,
            self._record.pane_id,
            f"holder_pid={self._identity.pid}",
        )

    def refresh_if_due(self):
        """The record is rewritten only when what herdr shows changed. Nothing that goes wrong here
        ends the hold: the lock is the flock, not the record, so whatever fails (herdr, the write)
        is left for the next refresh, while the holder keeps holding."""
        assert self._record, "publish() must run before refresh_if_due()"
        if time.monotonic() - self._last_refresh < self._refresh_seconds:
            return
        self._last_refresh = time.monotonic()

        try:
            self._apply_reading(read_pane_reading(self._record.pane_id, self._record.herdr_session), time.time())
            if self._observed_state() == self._written_state:
                return
            self._store.write_record(self._record)
            self._written_state = self._observed_state()
        except Exception:
            return

    def _observed_state(self) -> PaneState:
        assert self._record, "publish() must run before the record is observed"
        return PaneState(
            herdr_status=self._record.herdr_status,
            herdr_title=self._record.herdr_title,
            idle_since=self._record.idle_since,
            idle_state_change_sequence=self._record.idle_state_change_sequence,
        )

    def _apply_reading(self, reading: PaneReading | None, now: float):
        """Idle time restarts whenever herdr's state change sequence moves, even if the status
        reads idle again: a pane that worked between two samples was not idle throughout."""
        assert self._record, "publish() must run before a reading is applied"
        if not reading:
            self._record.herdr_status = HerdrStatus.UNKNOWN
            self._record.idle_since = None
            self._record.idle_state_change_sequence = None
            return

        self._record.herdr_status = reading.status
        self._record.herdr_title = reading.title
        if not reading.status.is_resting:
            self._record.idle_since = None
            self._record.idle_state_change_sequence = None
            return
        continues_same_idle_spell = (
            bool(self._record.idle_since) and reading.state_change_sequence == self._record.idle_state_change_sequence
        )
        if not continues_same_idle_spell:
            self._record.idle_since = now
            self._record.idle_state_change_sequence = reading.state_change_sequence

    def owner_is_gone(self) -> bool:
        return not is_same_process_alive(self._owner)

    def withdraw(self, event: LockEvent | None):
        """Removes the record and the stamp this process published (the flock is still held, so
        nobody else's can be in their place) and logs `event`; the kernel frees the flock at exit."""
        if not self._record:
            return
        try:
            self._store.remove_record_held_by(self._lock_name, self._identity)
            self._store.clear_holder_stamp(self._lock_name, self._identity)
            if event:
                self._store.append_event(
                    event, self._lock_name, self._owner.pid, self._record.pane_id, f"holder_pid={self._identity.pid}"
                )
        except OSError:
            return
