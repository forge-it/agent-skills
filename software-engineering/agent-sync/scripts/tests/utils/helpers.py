import fcntl
import json
import os
import resource
import select
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from tests.utils.constants import (
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    FAST_POLL_ENVIRONMENT,
    GRANDCHILD_COMMAND,
    HERDR_SESSION_NAME,
    INHERITED_ENVIRONMENT_PREFIXES,
    NO_DESCRIPTORS_LEFT,
    WAIT_INTERVAL_SECONDS,
    WAIT_TIMEOUT_SECONDS,
)
from tests.utils.samples import FAKE_HERDR_SCRIPT, GIT_SPY_SCRIPT, HELD_RECORD_TEMPLATE

STAT_START_TICKS_INDEX = 19
POACHER_JOIN_SECONDS = 2.0


@dataclass(frozen=True)
class CliResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


class FakeHerdr:
    """A herdr stand-in whose `agent get` status is a file per pane and whose notifications are
    appended to a log, so no test can ever reach the operator's real herdr. Like the real one it
    moves a pane's `state_change_seq` whenever the pane's status changes."""

    def __init__(self, directory: Path):
        self._state_directory = directory / "herdr-state"
        self._state_directory.mkdir(parents=True)
        self.binary = directory / "herdr"
        self.binary.write_text(FAKE_HERDR_SCRIPT)
        self.binary.chmod(0o755)

    def set_status(self, pane_id: str, status: str):
        status_file = self._state_directory / f"status.{pane_id}"
        if not status_file.exists() or status_file.read_text() != status:
            self._advance_sequence(pane_id)
        status_file.write_text(status)

    def simulate_unobserved_work(self, pane_id: str):
        """The pane worked and went idle again between two samples: the status reads the same,
        only the sequence moved."""
        self._advance_sequence(pane_id)
        self._advance_sequence(pane_id)

    def stop_reporting_sequences(self):
        (self._state_directory / "sequence.hidden").write_text("")

    def reply_with(self, raw_reply: bytes):
        """Every `agent get` from now on prints these bytes, whatever they are."""
        (self._state_directory / "reply.raw").write_bytes(raw_reply)

    def fail_notifications(self):
        (self._state_directory / "notifications.fail").write_text("")

    def recover_notifications(self):
        (self._state_directory / "notifications.fail").unlink(missing_ok=True)

    def read_count(self, pane_id: str) -> int:
        reads_log = self._state_directory / "reads.log"
        if not reads_log.exists():
            return 0
        return reads_log.read_text().split().count(pane_id)

    def notifications(self) -> list[list[str]]:
        log_file = self._state_directory / "notifications.log"
        if not log_file.exists():
            return []
        complete_lines = log_file.read_text().split("\n")[:-1]
        return [line.split("\t")[:-1] for line in complete_lines]

    def _advance_sequence(self, pane_id: str):
        sequence_file = self._state_directory / f"sequence.{pane_id}"
        current = int(sequence_file.read_text()) if sequence_file.exists() else 0
        sequence_file.write_text(str(current + 1))


class GitSpy:
    """A `git` stand-in that goes first on PATH: it logs the arguments of every call, then runs the
    real git."""

    def __init__(self, directory: Path):
        directory.mkdir(parents=True)
        self._directory = directory
        self._calls_log = directory / "git-calls.log"
        wrapper = directory / "git"
        wrapper.write_text(GIT_SPY_SCRIPT.format(calls_log=self._calls_log, real_git=shutil.which("git")))
        wrapper.chmod(0o755)

    @property
    def path_environment(self) -> dict[str, str]:
        return {"PATH": os.pathsep.join([str(self._directory), os.environ["PATH"]])}

    def calls(self) -> list[str]:
        return self._calls_log.read_text().splitlines() if self._calls_log.exists() else []


class Session:
    """One orchestrator: a script run as a given owner process, in a given herdr pane."""

    def __init__(
        self,
        *,
        script: Path,
        repository: Path,
        owner_pid: int,
        pane_id: str,
        herdr: FakeHerdr,
        state_home: Path,
    ):
        self._script = script
        self._repository = repository
        self._owner_pid = owner_pid
        self._pane_id = pane_id
        self._herdr = herdr
        self._state_home = state_home

    @property
    def owner_pid(self) -> int:
        return self._owner_pid

    @property
    def pane_id(self) -> str:
        return self._pane_id

    @property
    def repository(self) -> Path:
        return self._repository

    @cached_property
    def state_directory(self) -> Path:
        git_common_directory = run_git_command(
            self._repository, "rev-parse", "--path-format=absolute", "--git-common-dir"
        )
        return Path(git_common_directory.strip()) / "agent-sync"

    @property
    def nag_directory(self) -> Path:
        return self._state_home / "agent-sync" / "nag"

    def build_environment(self, overrides: Mapping[str, str | None] | None = None) -> dict[str, str]:
        """The fake herdr comes first on PATH and in HERDR_BIN_PATH, so even a script that ignores
        AGENT_SYNC_HERDR cannot reach the real one. An override value of None removes the variable."""
        environment = {
            name: value for name, value in os.environ.items() if not name.startswith(INHERITED_ENVIRONMENT_PREFIXES)
        }
        environment.update(FAST_POLL_ENVIRONMENT)
        environment.update(
            {
                "PATH": os.pathsep.join([str(self._herdr.binary.parent), environment.get("PATH", "")]),
                "AGENT_SYNC_OWNER_PID": str(self._owner_pid),
                "AGENT_SYNC_HERDR": str(self._herdr.binary),
                "HERDR_BIN_PATH": str(self._herdr.binary),
                "HERDR_PANE_ID": self._pane_id,
                "HERDR_SESSION": HERDR_SESSION_NAME,
                "XDG_STATE_HOME": str(self._state_home),
            }
        )
        for name, value in (overrides or {}).items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = value
        return environment

    def run(
        self,
        *arguments: str,
        environment: Mapping[str, str | None] | None = None,
        working_directory: Path | None = None,
        timeout: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    ) -> CliResult:
        completed = subprocess.run(
            [sys.executable, str(self._script), *arguments],
            capture_output=True,
            text=True,
            env=self.build_environment(environment),
            cwd=working_directory or self._repository,
            timeout=timeout,
            check=False,
        )
        return CliResult(completed.returncode, completed.stdout, completed.stderr)

    def popen(
        self,
        *arguments: str,
        environment: Mapping[str, str | None] | None = None,
        working_directory: Path | None = None,
        pass_file_descriptors: Sequence[int] = (),
    ) -> subprocess.Popen[str]:
        return self.spawn(
            sys.executable,
            str(self._script),
            *arguments,
            environment=environment,
            working_directory=working_directory,
            pass_file_descriptors=pass_file_descriptors,
        )

    def spawn(
        self,
        *command: str,
        environment: Mapping[str, str | None] | None = None,
        working_directory: Path | None = None,
        pass_file_descriptors: Sequence[int] = (),
    ) -> subprocess.Popen[str]:
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.build_environment(environment),
            cwd=working_directory or self._repository,
            pass_fds=pass_file_descriptors,
        )

    def record(self, lock: str) -> dict | None:
        return read_json(self.state_directory / f"{lock}.json")

    def rewrite_record(self, lock: str, **changes: object):
        record_file = self.state_directory / f"{lock}.json"
        record_file.write_text(json.dumps({**json.loads(record_file.read_text()), **changes}))

    def stamp(self, lock: str) -> dict | None:
        """What the holder wrote into the lock file itself."""
        return read_json(self.state_directory / f"{lock}.lock")

    def delete_record(self, lock: str):
        (self.state_directory / f"{lock}.json").unlink()

    def simulate_holder_pid_reuse(self, lock: str):
        """The holder is gone and its pid now belongs to a newer process: record and stamp both name
        a start time that the live process at that pid does not have."""
        stamp_file = self.state_directory / f"{lock}.lock"
        stamp = json.loads(stamp_file.read_text())
        self.rewrite_record(lock, holder_start_ticks=stamp["holder_start_ticks"] + 1)
        stamp_file.write_text(json.dumps({**stamp, "holder_start_ticks": stamp["holder_start_ticks"] + 1}))

    def block_record_writes(self, lock: str):
        """Puts a non-empty directory where the record file belongs, so every rewrite of the record
        fails with an OSError, whoever the test runs as."""
        record_file = self.state_directory / f"{lock}.json"
        record_file.unlink()
        record_file.mkdir()
        (record_file / "blocker").write_text("")

    def unblock_record_writes(self, lock: str):
        shutil.rmtree(self.state_directory / f"{lock}.json")

    def events(self) -> str:
        events_log = self.state_directory / "events.log"
        return events_log.read_text() if events_log.exists() else ""

    def nag_record(self, nag_id: str) -> dict | None:
        return read_json(self.nag_directory / f"{nag_id}.json")

    def lock_report(self, lock: str) -> dict:
        return json.loads(self.run("status", lock, "--json").stdout)[0]


class LockPoacher:
    """Blocks on a lock's flock from the test process, so it wins the instant the holder lets go,
    as a waiting `acquire` would, and then publishes a record that names it as the holder."""

    def __init__(self, session: Session, lock: str, watched_file: Path | None = None):
        self._record_file = session.state_directory / f"{lock}.json"
        self._lock = lock
        self._owner_pid = session.owner_pid
        self._pane_id = session.pane_id
        self._scope = str(session.repository)
        self._watched_file = watched_file
        self._descriptor = os.open(session.state_directory / f"{lock}.lock", os.O_RDWR)
        self._thread = threading.Thread(target=self._take_the_lock, daemon=True)
        self._has_the_lock = threading.Event()
        self.watched_file_existed_when_it_won = False

    def start(self):
        self._thread.start()

    def won_the_lock(self, timeout_seconds: float = WAIT_TIMEOUT_SECONDS) -> bool:
        return self._has_the_lock.wait(timeout_seconds)

    def stop(self):
        os.close(self._descriptor)
        self._thread.join(POACHER_JOIN_SECONDS)

    def _take_the_lock(self):
        fcntl.flock(self._descriptor, fcntl.LOCK_EX)
        self.watched_file_existed_when_it_won = bool(self._watched_file) and self._watched_file.exists()
        own_ticks = read_start_ticks(os.getpid())
        record = {
            **HELD_RECORD_TEMPLATE,
            "lock": self._lock,
            "owner_pid": self._owner_pid,
            "owner_start_ticks": read_start_ticks(self._owner_pid),
            "holder_pid": os.getpid(),
            "holder_start_ticks": own_ticks,
            "pane_id": self._pane_id,
            "scope": self._scope,
            "acquired_at": time.time(),
        }
        self._record_file.write_text(json.dumps(record))
        self._has_the_lock.set()


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def read_start_ticks(pid: int) -> int:
    raw_stat = Path(f"/proc/{pid}/stat").read_text()
    return int(raw_stat.rsplit(")", 1)[1].split()[STAT_START_TICKS_INDEX])


def process_is_running(pid: int) -> bool:
    try:
        raw_stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return raw_stat.rsplit(")", 1)[1].split()[0] != "Z"


@contextmanager
def file_descriptors_exhausted(pid: int) -> Iterator[None]:
    """The process can open nothing new until the block ends: every `open()` and `pipe()` it makes
    fails with EMFILE, as when a machine runs out of descriptors."""
    previous_limits = resource.prlimit(pid, resource.RLIMIT_NOFILE)
    resource.prlimit(pid, resource.RLIMIT_NOFILE, (NO_DESCRIPTORS_LEFT, previous_limits[1]))
    try:
        yield
    finally:
        with suppress(ProcessLookupError):
            resource.prlimit(pid, resource.RLIMIT_NOFILE, previous_limits)


def wait_until(
    condition: Callable[[], object],
    description: str,
    timeout_seconds: float = WAIT_TIMEOUT_SECONDS,
) -> object:
    deadline = time.monotonic() + timeout_seconds
    while True:
        value = condition()
        if value:
            return value
        assert time.monotonic() < deadline, f"timed out waiting for {description}"
        time.sleep(WAIT_INTERVAL_SECONDS)


def read_stderr_line(process: subprocess.Popen[str], timeout_seconds: float = WAIT_TIMEOUT_SECONDS) -> str:
    readable, _, _ = select.select([process.stderr], [], [], timeout_seconds)
    assert readable, f"timed out after {timeout_seconds}s waiting for a line on the process's stderr"
    return process.stderr.readline()


def read_pid_file(pid_file: Path) -> int:
    return int(wait_until(lambda: pid_file.exists() and pid_file.read_text().strip(), f"{pid_file.name} to be written"))


def hold_flock_briefly(lock_file: Path, seconds: float) -> threading.Thread:
    """Takes the flock before returning and drops it `seconds` later, like the moment a concurrent
    `status` spends probing it."""
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_file, os.O_RDWR | os.O_CREAT, 0o644)
    fcntl.flock(descriptor, fcntl.LOCK_EX)

    def release_later():
        time.sleep(seconds)
        os.close(descriptor)

    thread = threading.Thread(target=release_later)
    thread.start()
    return thread


def start_holder_whose_acquirer_is_gone(session: Session, lock: str) -> subprocess.Popen[str]:
    """Runs the detached holder the way `acquire` starts it, but with the acquirer already gone:
    nobody listens on the readiness pipe and the acquirer's copy of the flock is closed."""
    session.state_directory.mkdir(parents=True, exist_ok=True)
    lock_descriptor = os.open(session.state_directory / f"{lock}.lock", os.O_RDWR | os.O_CREAT, 0o644)
    fcntl.flock(lock_descriptor, fcntl.LOCK_EX)
    reply_read_descriptor, reply_write_descriptor = os.pipe()
    os.close(reply_read_descriptor)
    holder = session.popen(
        "_hold",
        lock,
        f"--state-directory={session.state_directory}",
        f"--owner-pid={session.owner_pid}",
        f"--owner-start-ticks={read_start_ticks(session.owner_pid)}",
        f"--scope={session.repository}",
        f"--lock-file-descriptor={lock_descriptor}",
        f"--readiness-file-descriptor={reply_write_descriptor}",
        pass_file_descriptors=(lock_descriptor, reply_write_descriptor),
    )
    os.close(reply_write_descriptor)
    os.close(lock_descriptor)
    return holder


def run_git_command(directory: Path, *arguments: str, check: bool = True) -> str:
    environment = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    completed = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        capture_output=True,
        text=True,
        env=environment,
        check=check,
    )
    return completed.stdout


def collect_output(
    process: subprocess.Popen[str], timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS
) -> CliResult:
    stdout, stderr = process.communicate(timeout=timeout_seconds)
    return CliResult(process.returncode, stdout, stderr)


def wait_for_idle_observation(session: Session, lock: str):
    wait_until(
        lambda: (session.record(lock) or {}).get("idle_since"),
        f"the holder of {lock} to observe its pane idle",
    )


def wait_for_first_observation(session: Session, lock: str):
    """The holder rewrites its record once, after its first look at the pane; tests that tamper with
    the record must wait for that, or the holder overwrites the tampering."""
    wait_until(
        lambda: (session.record(lock) or {}).get("herdr_status") != "unknown",
        f"the holder of {lock} to look at its pane",
    )


def wait_for_recorded_herdr_status(session: Session, lock: str, status: str) -> dict:
    return wait_until(
        lambda: (session.record(lock) or {}).get("herdr_status") == status and session.record(lock),
        f"the record of {lock} to show the pane as {status}",
    )


def wait_for_command_to_run_under(session: Session, lock: str):
    """Until the activity names its command's process group, which is what outlives a killed `run`."""
    wait_until(
        lambda: any(activity["process_group_id"] for activity in session.lock_report(lock)["activities"]),
        f"a command to be registered under lock {lock}",
    )


@dataclass(frozen=True)
class OrphanedCommand:
    """What a `run` command left behind when its `run` process was killed: a shell and its
    background `sleep`, in a process group of their own, holding no lock."""

    grandchild_pid: int
    process_group_id: int

    @property
    def is_running(self) -> bool:
        return process_is_running(self.grandchild_pid)

    def kill(self):
        try:
            os.killpg(self.process_group_id, signal.SIGKILL)
        except ProcessLookupError:
            return


def leave_an_orphaned_command(session: Session, lock: str, pid_file: Path) -> OrphanedCommand:
    running = session.popen("run", lock, "--", "sh", "-c", GRANDCHILD_COMMAND.format(pid_file=pid_file))
    grandchild_pid = read_pid_file(pid_file)
    wait_for_command_to_run_under(session, lock)
    orphan = OrphanedCommand(grandchild_pid, os.getpgid(grandchild_pid))
    os.kill(running.pid, signal.SIGKILL)
    running.wait()
    return orphan


def plant_activity_of_a_dead_run(session: Session, lock: str, process_group_id: int, leader_start_ticks: int):
    """An activity record of a `run` process that no longer exists, naming a process group."""
    activities_directory = session.state_directory / f"{lock}.activities"
    activities_directory.mkdir(exist_ok=True)
    activity = {
        "lock": lock,
        "run_pid": 1,
        "run_start_ticks": 1,
        "command": "a command whose group id was reused",
        "started_at": 0,
        "process_group_id": process_group_id,
        "process_group_leader_start_ticks": leader_start_ticks,
    }
    (activities_directory / "1-1.json").write_text(json.dumps(activity))
