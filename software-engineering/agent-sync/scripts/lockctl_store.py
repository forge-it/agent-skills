"""The files of <git-common-dir>/agent-sync/ and the git questions that locate them: lock files,
holder records, activities, theft notes and the event log."""

import fcntl
import json
import os
import subprocess
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from agent_sync_common import (
    EnvironmentProblem,
    ProcessIdentity,
    atomic_write_json,
    format_timestamp,
    is_same_process_alive,
)

from lockctl_records import ActivityRecord, HolderStamp, LockEvent, LockRecord, TheftNote

STATE_SUBDIRECTORY = "agent-sync"
EVENTS_LOG_NAME = "events.log"
LOCK_SUFFIX = ".lock"
RECORD_SUFFIX = ".json"
THEFT_NOTE_SUFFIX = ".stolen.json"
ACTIVITIES_SUFFIX = ".activities"
ACTIVITY_FILE_PATTERN = "*.json"
GIT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class LockPaths:
    state_directory: Path
    name: str

    @property
    def lock_file(self) -> Path:
        return self.state_directory / f"{self.name}{LOCK_SUFFIX}"

    @property
    def record_file(self) -> Path:
        return self.state_directory / f"{self.name}{RECORD_SUFFIX}"

    @property
    def theft_note_file(self) -> Path:
        return self.state_directory / f"{self.name}{THEFT_NOTE_SUFFIX}"

    @property
    def activities_directory(self) -> Path:
        return self.state_directory / f"{self.name}{ACTIVITIES_SUFFIX}"


@dataclass(frozen=True)
class LockInspection:
    """`record` is set only for a held lock whose holder process is alive; a held lock without one
    is being acquired or probed by someone right now. When the holder's JSON record is missing but
    the stamp in the lock file names a live holder, `record` is rebuilt from the stamp and
    `record_missing` is set."""

    name: str
    held: bool
    record: LockRecord | None
    record_missing: bool = False


def run_git(arguments: Sequence[str], working_directory: Path) -> str | None:
    """Stdout of the git command, or None when git is missing or the command fails; an empty
    string is a successful command with no output. Git never takes an optional lock here
    (`.git/index.lock` for a status refresh): the checkout belongs to other sessions, and a lock
    of ours would make their `git merge` or `git commit` fail with "index.lock exists"."""
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(working_directory), *arguments],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode:
        return None
    return completed.stdout


def locate_state_directory(working_directory: Path) -> Path:
    common_directory = (
        run_git(["rev-parse", "--path-format=absolute", "--git-common-dir"], working_directory) or ""
    ).strip()
    if not common_directory:
        raise EnvironmentProblem(f"{working_directory} is not inside a git repository")
    return Path(common_directory) / STATE_SUBDIRECTORY


def locate_scope(working_directory: Path) -> str:
    """The git toplevel of the directory, or the directory itself where git names none (a bare
    repository, the inside of .git)."""
    toplevel = (run_git(["rev-parse", "--show-toplevel"], working_directory) or "").strip()
    return toplevel or str(working_directory)


class LockStore:
    """The files of <git-common-dir>/agent-sync/: lock files, holder records, activities, theft
    notes, events."""

    def __init__(self, state_directory: Path):
        self._state_directory = state_directory

    @property
    def state_directory(self) -> Path:
        return self._state_directory

    def paths(self, name: str) -> LockPaths:
        return LockPaths(self._state_directory, name)

    def lock_names(self) -> list[str]:
        return sorted(
            lock_file.name.removesuffix(LOCK_SUFFIX) for lock_file in self._state_directory.glob(f"*{LOCK_SUFFIX}")
        )

    def open_lock_file(self, name: str) -> int:
        self._state_directory.mkdir(parents=True, exist_ok=True)
        return os.open(self.paths(name).lock_file, os.O_RDWR | os.O_CREAT, 0o644)

    @staticmethod
    def try_lock(lock_file_descriptor: int) -> bool:
        try:
            fcntl.flock(lock_file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True

    def inspect(self, name: str) -> LockInspection:
        """Held or free by probing the flock itself, never by trusting a record. A busy flock
        counts as held by the recorded owner only while the recorded holder process is alive: a
        busy flock whose recorded holder is gone is somebody mid-acquire or mid-probe, unless the
        stamp in the lock file names a live holder, whose record is then missing. A record found
        while the flock is free is removed under that flock, so a concurrent acquirer's fresh
        record cannot be deleted by mistake."""
        paths = self.paths(name)
        if not paths.lock_file.exists():
            return LockInspection(name, held=False, record=None)

        probe_file_descriptor = os.open(paths.lock_file, os.O_RDWR)
        try:
            if not self.try_lock(probe_file_descriptor):
                record = self.read_record(name)
                if record and is_same_process_alive(record.holder):
                    return LockInspection(name, held=True, record=record)
                stamp = self.read_holder_stamp(name)
                if stamp and is_same_process_alive(stamp.holder):
                    acquired_at = paths.lock_file.stat().st_mtime
                    return LockInspection(
                        name, held=True, record=LockRecord.reconstruct(name, stamp, acquired_at), record_missing=True
                    )
                return LockInspection(name, held=True, record=None)
            stale_record = self.read_record(name)
            paths.record_file.unlink(missing_ok=True)
            if stale_record:
                self.append_event(
                    LockEvent.EXPIRE,
                    name,
                    stale_record.owner_pid,
                    stale_record.pane_id,
                    f"stale_holder_pid={stale_record.holder_pid}",
                )
            return LockInspection(name, held=False, record=None)
        finally:
            os.close(probe_file_descriptor)

    def read_record(self, name: str) -> LockRecord | None:
        try:
            return LockRecord.from_json(self.paths(name).record_file.read_text())
        except OSError:
            return None

    def write_record(self, record: LockRecord):
        atomic_write_json(self.paths(record.lock).record_file, asdict(record))

    def discard_record(self, name: str):
        self.paths(name).record_file.unlink(missing_ok=True)

    def remove_record_held_by(self, name: str, holder: ProcessIdentity):
        record = self.read_record(name)
        if record and record.holder == holder:
            self.discard_record(name)

    def write_holder_stamp(self, name: str, stamp: HolderStamp):
        """Rewritten in place: the flock belongs to the file, so the file is never replaced."""
        self.paths(name).lock_file.write_text(json.dumps(asdict(stamp)))

    def read_holder_stamp(self, name: str) -> HolderStamp | None:
        try:
            return HolderStamp.from_json(self.paths(name).lock_file.read_text())
        except OSError:
            return None

    def clear_holder_stamp(self, name: str, holder: ProcessIdentity):
        stamp = self.read_holder_stamp(name)
        if stamp and stamp.holder == holder:
            self.paths(name).lock_file.write_text("")

    def activity_file(self, name: str, run_process: ProcessIdentity) -> Path:
        return self.paths(name).activities_directory / f"{run_process.pid}-{run_process.start_ticks}.json"

    def write_activity(self, activity: ActivityRecord):
        self.paths(activity.lock).activities_directory.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.activity_file(activity.lock, activity.run_process), asdict(activity))

    def remove_activity(self, name: str, run_process: ProcessIdentity):
        self.activity_file(name, run_process).unlink(missing_ok=True)

    def live_activities(self, name: str) -> list[ActivityRecord]:
        """The commands running under the lock, oldest first, including those whose `run` process
        died but whose process group still lives; records with neither are removed."""
        live = []
        for activity_file in sorted(self.paths(name).activities_directory.glob(ACTIVITY_FILE_PATTERN)):
            try:
                activity = ActivityRecord.from_json(activity_file.read_text())
            except OSError:
                continue
            if activity and activity.is_running:
                live.append(activity)
            else:
                activity_file.unlink(missing_ok=True)
        return sorted(live, key=lambda activity: activity.started_at)

    def read_theft_note(self, name: str) -> TheftNote | None:
        try:
            return TheftNote(**json.loads(self.paths(name).theft_note_file.read_text()))
        except (OSError, ValueError, TypeError):
            return None

    def write_theft_note(self, note: TheftNote):
        atomic_write_json(self.paths(note.lock).theft_note_file, asdict(note))

    def clear_theft_note_of(self, name: str, victim: ProcessIdentity):
        note = self.read_theft_note(name)
        if note and ProcessIdentity(note.victim_owner_pid, note.victim_owner_start_ticks) == victim:
            self.paths(name).theft_note_file.unlink(missing_ok=True)

    def append_event(self, event: LockEvent, name: str, owner_pid: int, pane_id: str, details: str = ""):
        self._state_directory.mkdir(parents=True, exist_ok=True)
        line = f"{format_timestamp(time.time())} {event} lock={name} owner_pid={owner_pid} pane={pane_id or '-'}"
        if details:
            line += f" {details}"
        with (self._state_directory / EVENTS_LOG_NAME).open("a", encoding="utf-8") as events_log:
            events_log.write(f"{line}\n")
