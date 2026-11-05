"""What lockctl keeps on disk about a hold: the stamp the holder writes into the lock file, the
holder's JSON record, the commands running under the lock, and the note a theft leaves for its
victim."""

import json
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Self

from agent_sync_common import (
    HerdrStatus,
    ProcessGroupIdentity,
    ProcessIdentity,
    find_group_members_of,
    is_same_process_alive,
)

DEFAULT_IDLE_SECONDS = 600.0


class LockEvent(StrEnum):
    ACQUIRE = "acquire"
    RELEASE = "release"
    STEAL = "steal"
    EXPIRE = "expire"


class HoldKind(StrEnum):
    ACQUIRE = "acquire"
    RUN = "run"

    @classmethod
    def parse(cls, raw_kind: object) -> "HoldKind":
        """An unknown kind is treated as a `run` hold, the one nobody can enter."""
        try:
            return cls(raw_kind)
        except ValueError:
            return cls.RUN


@dataclass(frozen=True)
class HolderStamp:
    """What the holder writes into the lock file itself, which is never deleted: enough to find and
    stop the holder, and to tell its owner from anyone else, when the JSON record is missing. It
    is emptied when the holder lets go, so a stamp naming a live process means that process holds
    the flock."""

    holder_pid: int
    holder_start_ticks: int
    owner_pid: int
    owner_start_ticks: int
    scope: str
    hold_kind: HoldKind

    @classmethod
    def from_json(cls, text: str) -> Self | None:
        try:
            payload = json.loads(text)
            return cls(**{**payload, "hold_kind": HoldKind.parse(payload.get("hold_kind"))})
        except (ValueError, TypeError, AttributeError):
            return None

    @property
    def holder(self) -> ProcessIdentity:
        return ProcessIdentity(self.holder_pid, self.holder_start_ticks)


@dataclass
class LockRecord:
    lock: str
    owner_pid: int
    owner_start_ticks: int
    holder_pid: int
    holder_start_ticks: int
    pane_id: str
    herdr_session: str
    working_directory: str
    branch: str
    purpose: str
    acquired_at: float
    hold_kind: HoldKind = HoldKind.ACQUIRE
    scope: str = ""
    idle_threshold_seconds: float = DEFAULT_IDLE_SECONDS
    herdr_status: HerdrStatus = HerdrStatus.UNKNOWN
    herdr_title: str = ""
    idle_since: float | None = None
    idle_state_change_sequence: int | None = None

    @classmethod
    def from_json(cls, text: str) -> Self | None:
        try:
            payload = json.loads(text)
            known_names = {record_field.name for record_field in fields(cls)}
            record = cls(**{key: value for key, value in payload.items() if key in known_names})
        except (ValueError, TypeError, AttributeError):
            return None
        record.herdr_status = HerdrStatus.parse(record.herdr_status)
        record.hold_kind = HoldKind.parse(record.hold_kind)
        return record

    @classmethod
    def reconstruct(cls, lock: str, stamp: HolderStamp, acquired_at: float) -> Self:
        """What can be said about a hold from its stamp alone: who holds it, for whom, from where.
        The pane, branch and purpose stay empty, so nothing about its state can be verified."""
        return cls(
            lock=lock,
            owner_pid=stamp.owner_pid,
            owner_start_ticks=stamp.owner_start_ticks,
            holder_pid=stamp.holder_pid,
            holder_start_ticks=stamp.holder_start_ticks,
            pane_id="",
            herdr_session="",
            working_directory="",
            branch="",
            purpose="",
            acquired_at=acquired_at,
            hold_kind=stamp.hold_kind,
            scope=stamp.scope,
        )

    @property
    def holder(self) -> ProcessIdentity:
        return ProcessIdentity(self.holder_pid, self.holder_start_ticks)

    @property
    def owner(self) -> ProcessIdentity:
        return ProcessIdentity(self.owner_pid, self.owner_start_ticks)


@dataclass
class ActivityRecord:
    """A `run` command executing under a lock. It lives as long as its `run` process does or its
    command's process group has live members: a `run` process that was killed leaves its command
    running with no lock, and that command is still an activity of the lock, to be stopped before
    the lock changes hands. A record with neither is dead and gets pruned."""

    lock: str
    run_pid: int
    run_start_ticks: int
    command: str
    started_at: float
    process_group_id: int = 0
    process_group_leader_start_ticks: int = 0

    @classmethod
    def from_json(cls, text: str) -> Self | None:
        try:
            payload = json.loads(text)
            known_names = {record_field.name for record_field in fields(cls)}
            return cls(**{key: value for key, value in payload.items() if key in known_names})
        except (ValueError, TypeError, AttributeError):
            return None

    @property
    def run_process(self) -> ProcessIdentity:
        return ProcessIdentity(self.run_pid, self.run_start_ticks)

    @property
    def command_group(self) -> ProcessGroupIdentity:
        return ProcessGroupIdentity(self.process_group_id, self.process_group_leader_start_ticks)

    @property
    def is_orphaned(self) -> bool:
        """Its `run` process is gone; whether the command still runs is `is_running`."""
        return not is_same_process_alive(self.run_process)

    @property
    def is_running(self) -> bool:
        return not self.is_orphaned or bool(find_group_members_of(self.command_group))


@dataclass(frozen=True)
class TheftNote:
    lock: str
    stolen_at: float
    thief_pane_id: str
    thief_owner_pid: int
    victim_owner_pid: int
    victim_owner_start_ticks: int
    victim_pane_id: str
    forced: bool
