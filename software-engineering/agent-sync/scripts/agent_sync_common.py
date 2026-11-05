"""Primitives shared by lockctl.py and nag.py, which import this module from their own directory:
owner-process detection, herdr calls, and detached background processes."""

import argparse
import json
import os
import re
import select
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from pathlib import Path

OWNER_PROCESS_NAME = "claude"
OWNER_PID_ENVIRONMENT_VARIABLE = "AGENT_SYNC_OWNER_PID"
HERDR_BINARY_ENVIRONMENT_VARIABLES = ("AGENT_SYNC_HERDR", "HERDR_BIN_PATH")
HERDR_PANE_ENVIRONMENT_VARIABLE = "HERDR_PANE_ID"
HERDR_SESSION_ENVIRONMENT_VARIABLE = "HERDR_SESSION"
HERDR_COMMAND_TIMEOUT_SECONDS = 4.0
HERDR_ERROR_EXCERPT_LIMIT = 200
POLL_SECONDS_ENVIRONMENT_VARIABLE = "AGENT_SYNC_POLL_SECONDS"
DEFAULT_POLL_SECONDS = 2.0
TERMINATION_GRACE_SECONDS = 5.0
KILL_WAIT_SECONDS = 2.0
PROCESS_EXIT_POLL_SECONDS = 0.02
READINESS_TIMEOUT_SECONDS = 15.0
READY_MESSAGE = "ready"
ERROR_REPLY_PREFIX = "error: "
STAT_START_TICKS_INDEX = 19
STAT_PROCESS_GROUP_INDEX = 2
ZOMBIE_STATE = "Z"
UNREADABLE_STAT_ERRORS = (OSError, ValueError, IndexError)
PROCESS_DIRECTORY = Path("/proc")
LOWEST_SIGNALLABLE_GROUP_ID = 2
STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
DURATION_PATTERN = re.compile(r"(\d+(?:\.\d+)?)([smh])")
DURATION_UNIT_SECONDS = {"s": 1.0, "m": 60.0, "h": 3600.0}
SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60


class ExitCode(IntEnum):
    OK = 0
    REFUSED = 1
    ENVIRONMENT = 2
    BUSY = 75


class EnvironmentProblem(Exception):
    """The caller's setup, not the requested operation, is wrong: the script exits with 2."""


class HerdrError(Exception):
    """herdr is missing, did not answer in time, or refused the request."""


class HerdrStatus(StrEnum):
    WORKING = "working"
    IDLE = "idle"
    DONE = "done"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"

    @classmethod
    def parse(cls, raw_status: object) -> "HerdrStatus":
        try:
            return cls(raw_status)
        except ValueError:
            return cls.UNKNOWN

    @property
    def is_resting(self) -> bool:
        return self in (HerdrStatus.IDLE, HerdrStatus.DONE)


@dataclass(frozen=True)
class ProcessIdentity:
    """A pid plus its start time, so a recycled pid is never mistaken for the original process."""

    pid: int
    start_ticks: int


@dataclass(frozen=True)
class ProcessGroupIdentity:
    """A process group id plus the start time of the process that leads it. Linux never reuses a pid
    while a group still has members, so a leader pid that now belongs to a different process proves
    the group is gone and its id was reused by an unrelated one."""

    group_id: int
    leader_start_ticks: int


@dataclass(frozen=True)
class ProcessStat:
    name: str
    state: str
    parent_pid: int
    process_group_id: int
    start_ticks: int


@dataclass(frozen=True)
class PaneReading:
    """`state_change_sequence` is herdr's `state_change_seq`: it moves on every status change, so
    an unchanged value proves the pane did not work in between two readings that both show it idle."""

    status: HerdrStatus
    title: str
    state_change_sequence: int | None = None


def parse_process_stat(raw_stat: str) -> ProcessStat:
    name_end = raw_stat.rfind(")")
    fields_after_name = raw_stat[name_end + 2 :].split()
    return ProcessStat(
        name=raw_stat[raw_stat.find("(") + 1 : name_end],
        state=fields_after_name[0],
        parent_pid=int(fields_after_name[1]),
        process_group_id=int(fields_after_name[STAT_PROCESS_GROUP_INDEX]),
        start_ticks=int(fields_after_name[STAT_START_TICKS_INDEX]),
    )


def read_process_stat(pid: int) -> ProcessStat | None:
    """None when the process is gone. A read that fails for any other reason (descriptors or memory
    exhausted, access denied) raises: it says nothing about whether the process lives."""
    try:
        return parse_process_stat((PROCESS_DIRECTORY / str(pid) / "stat").read_text(errors="replace"))
    except (FileNotFoundError, ProcessLookupError):
        return None


def read_own_identity() -> ProcessIdentity:
    stat = read_process_stat(os.getpid())
    if not stat:
        raise EnvironmentProblem("cannot read /proc/self/stat: agent-sync needs Linux procfs")
    return ProcessIdentity(os.getpid(), stat.start_ticks)


def is_same_process_alive(identity: ProcessIdentity) -> bool:
    """A process whose /proc entry cannot be read, for any reason but its absence, counts as alive:
    callers act on "gone" by freeing a lock or stopping a command, and a shortage of descriptors
    must not do that while the owner lives. They ask again at their next poll."""
    try:
        stat = read_process_stat(identity.pid)
    except UNREADABLE_STAT_ERRORS:
        return True
    if not stat:
        return False
    return stat.state != ZOMBIE_STATE and stat.start_ticks == identity.start_ticks


def find_owner_process() -> ProcessIdentity:
    """The session a lock or nag belongs to: the nearest ancestor named `claude`, or the process
    named by AGENT_SYNC_OWNER_PID for tests and non-Claude callers."""
    override = os.environ.get(OWNER_PID_ENVIRONMENT_VARIABLE)
    if override:
        if not override.isdigit():
            raise EnvironmentProblem(f"{OWNER_PID_ENVIRONMENT_VARIABLE} must be a process id, got {override!r}")
        override_stat = read_process_stat(int(override))
        if not override_stat or override_stat.state == ZOMBIE_STATE:
            raise EnvironmentProblem(f"{OWNER_PID_ENVIRONMENT_VARIABLE}={override} is not a running process")
        return ProcessIdentity(int(override), override_stat.start_ticks)

    process_id = os.getpid()
    while True:
        stat = read_process_stat(process_id)
        if not stat or stat.parent_pid <= 1:
            break
        parent_stat = read_process_stat(stat.parent_pid)
        if not parent_stat:
            break
        if parent_stat.name == OWNER_PROCESS_NAME:
            return ProcessIdentity(stat.parent_pid, parent_stat.start_ticks)
        process_id = stat.parent_pid

    raise EnvironmentProblem(
        f"no `{OWNER_PROCESS_NAME}` process among the ancestors of this command; "
        f"set {OWNER_PID_ENVIRONMENT_VARIABLE} to name the owning process"
    )


def wait_until_gone(identity: ProcessIdentity, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while is_same_process_alive(identity):
        if time.monotonic() >= deadline:
            return False
        time.sleep(PROCESS_EXIT_POLL_SECONDS)
    return True


def terminate_process(identity: ProcessIdentity, grace_seconds: float = TERMINATION_GRACE_SECONDS) -> bool:
    """SIGTERM, then SIGKILL once the grace period passes; False when the process survives both.
    A pid whose start time differs from `identity` belongs to some other process and is left alone."""
    if not is_same_process_alive(identity):
        return True

    try:
        os.kill(identity.pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    if wait_until_gone(identity, grace_seconds):
        return True

    try:
        os.kill(identity.pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    return wait_until_gone(identity, KILL_WAIT_SECONDS)


def find_process_group_members(group_id: int) -> list[int]:
    """Pids of the live processes of a process group. Found by scanning procfs, because
    `killpg(group, 0)` also succeeds for zombies that nobody has reaped yet."""
    members = []
    for stat_file in PROCESS_DIRECTORY.glob("[0-9]*/stat"):
        try:
            stat = parse_process_stat(stat_file.read_text(errors="replace"))
        except UNREADABLE_STAT_ERRORS:
            continue
        if stat.process_group_id == group_id and stat.state != ZOMBIE_STATE:
            members.append(int(stat_file.parent.name))
    return members


def find_group_members_of(group: ProcessGroupIdentity) -> list[int]:
    """Live pids of exactly this group; empty when its id now belongs to an unrelated process group
    or is not a real group (0 means "unknown", and the kernel threads sit in group 0)."""
    if group.group_id < LOWEST_SIGNALLABLE_GROUP_ID:
        return []
    try:
        leader_stat = read_process_stat(group.group_id)
    except UNREADABLE_STAT_ERRORS:
        leader_stat = None
    if leader_stat and leader_stat.start_ticks != group.leader_start_ticks:
        return []
    return find_process_group_members(group.group_id)


def wait_until_group_is_empty(group_id: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while find_process_group_members(group_id):
        if time.monotonic() >= deadline:
            return False
        time.sleep(PROCESS_EXIT_POLL_SECONDS)
    return True


def terminate_process_group(group_id: int, grace_seconds: float = TERMINATION_GRACE_SECONDS) -> bool:
    """SIGTERM to the whole group, then SIGKILL to what is left once the grace period passes, so
    the grandchildren of a shell command go with it. False when a member survives both. Ids that
    are not a real group of someone else (0 means "unknown", 1 is init) are never signalled."""
    if group_id < LOWEST_SIGNALLABLE_GROUP_ID or group_id == os.getpgrp():
        return True
    if not find_process_group_members(group_id):
        return True

    try:
        os.killpg(group_id, signal.SIGTERM)
    except ProcessLookupError:
        return True
    if wait_until_group_is_empty(group_id, grace_seconds):
        return True

    try:
        os.killpg(group_id, signal.SIGKILL)
    except ProcessLookupError:
        return True
    return wait_until_group_is_empty(group_id, KILL_WAIT_SECONDS)


def terminate_group_of(group: ProcessGroupIdentity, grace_seconds: float = TERMINATION_GRACE_SECONDS) -> bool:
    """terminate_process_group for a group recorded earlier, left alone when its id was reused."""
    if not find_group_members_of(group):
        return True
    return terminate_process_group(group.group_id, grace_seconds)


def install_stop_signal_handlers() -> threading.Event:
    stop_requested = threading.Event()

    def request_stop(signal_number: int, frame: object):
        stop_requested.set()

    for stop_signal in STOP_SIGNALS:
        signal.signal(stop_signal, request_stop)
    return stop_requested


def signal_readiness(readiness_file_descriptor: int, message: str) -> bool:
    """False when the launching command is already gone, so nobody will learn of this process."""
    try:
        os.write(readiness_file_descriptor, f"{message}\n".encode())
    except OSError:
        return False
    finally:
        os.close(readiness_file_descriptor)
    return True


def launch_detached(command: Sequence[str], inherited_file_descriptors: Sequence[int] = ()) -> int:
    """Starts `command` in its own session with no stdio, so the calling tool call can end without
    killing it or waiting for its pipes. Returns its pid once it has written the readiness line to
    the `--readiness-file-descriptor` that is appended to the command."""
    reply_read_descriptor, reply_write_descriptor = os.pipe()
    child = subprocess.Popen(
        [*command, f"--readiness-file-descriptor={reply_write_descriptor}"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        pass_fds=(*inherited_file_descriptors, reply_write_descriptor),
        start_new_session=True,
    )
    os.close(reply_write_descriptor)

    try:
        readable, _, _ = select.select([reply_read_descriptor], [], [], READINESS_TIMEOUT_SECONDS)
        reply = os.read(reply_read_descriptor, 4096).decode().strip() if readable else ""
    finally:
        os.close(reply_read_descriptor)

    if reply == READY_MESSAGE:
        return child.pid
    if child.poll() is None:
        child.kill()
    child.wait()
    raise EnvironmentProblem(
        reply.removeprefix(ERROR_REPLY_PREFIX) or "the background process exited before it was ready"
    )


def resolve_herdr_binary() -> str | None:
    for variable in HERDR_BINARY_ENVIRONMENT_VARIABLES:
        configured = os.environ.get(variable)
        if configured:
            return configured
    return shutil.which("herdr")


def run_herdr(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    binary = resolve_herdr_binary()
    if not binary:
        raise HerdrError("herdr is not available: set AGENT_SYNC_HERDR or put herdr on PATH")
    try:
        completed = subprocess.run(
            [binary, *arguments],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=HERDR_COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, ValueError) as failure:
        # ValueError: herdr's output was not text (UnicodeDecodeError), or an argument cannot be passed on
        raise HerdrError(f"herdr could not be run: {failure}") from failure
    if completed.returncode:
        reason = (completed.stderr or completed.stdout).strip()[:HERDR_ERROR_EXCERPT_LIMIT]
        raise HerdrError(f"herdr {' '.join(arguments[:2])} exited with {completed.returncode}: {reason}")
    return completed


def describe_herdr_session_mismatch(pane_session: str) -> str:
    """Pane ids are numbered per herdr server, and HERDR_SESSION picks the server a command talks
    to: read through another session, a pane id names some other pane or none. Empty when this
    process talks to the server the pane id belongs to; a session missing on one side only is a
    different session."""
    current_session = os.environ.get(HERDR_SESSION_ENVIRONMENT_VARIABLE, "")
    if current_session == pane_session:
        return ""
    pane_session_name = f"herdr session {pane_session!r}" if pane_session else "no herdr session"
    current_session_name = f"herdr session {current_session!r}" if current_session else "no herdr session"
    return (
        f"the pane was recorded in {pane_session_name} but this command runs in {current_session_name}, "
        "and pane ids belong to one herdr session"
    )


def read_pane_reading(pane_id: str, pane_session: str) -> PaneReading | None:
    """None when the pane cannot be read, including when it was recorded in another herdr session
    than the one this process talks to."""
    if not pane_id or describe_herdr_session_mismatch(pane_session):
        return None
    try:
        completed = run_herdr(["agent", "get", pane_id])
    except HerdrError:
        return None
    try:
        agent = json.loads(completed.stdout)["result"]["agent"]
        state_change_sequence = agent.get("state_change_seq")
        return PaneReading(
            status=HerdrStatus.parse(agent.get("agent_status")),
            title=str(agent.get("terminal_title_stripped") or ""),
            state_change_sequence=state_change_sequence if isinstance(state_change_sequence, int) else None,
        )
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def send_notification(title: str, body: str):
    """Raises HerdrError when the notification could not be shown."""
    arguments = ["notification", "show", title, "--sound", "request"]
    if body:
        arguments += ["--body", body]
    run_herdr(arguments)


def parse_duration(text: str) -> float:
    match = DURATION_PATTERN.fullmatch(text.strip())
    if not match:
        raise argparse.ArgumentTypeError(f"invalid duration {text!r}: use a number and a unit, like 90s, 15m or 1h")
    return float(match.group(1)) * DURATION_UNIT_SECONDS[match.group(2)]


def read_seconds_setting(variable: str, default: float) -> float:
    raw_value = os.environ.get(variable)
    if not raw_value:
        return default
    try:
        seconds = float(raw_value)
    except ValueError:
        raise EnvironmentProblem(f"{variable} must be a number of seconds, got {raw_value!r}") from None
    if seconds < 0:
        raise EnvironmentProblem(f"{variable} must not be negative, got {raw_value!r}")
    return seconds


def format_duration(seconds: float) -> str:
    whole_seconds = int(max(seconds, 0))
    hours, remainder = divmod(whole_seconds, SECONDS_PER_HOUR)
    minutes, remaining_seconds = divmod(remainder, SECONDS_PER_MINUTE)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {remaining_seconds:02d}s"
    return f"{remaining_seconds}s"


def format_timestamp(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_json(path: Path, payload: Mapping[str, object]):
    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary_path.write_text(json.dumps(payload, indent=2))
        temporary_path.replace(path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
