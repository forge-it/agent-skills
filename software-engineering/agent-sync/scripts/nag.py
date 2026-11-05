#!/usr/bin/env python3
"""Repeated herdr notification until it is stopped or the owning `claude` session dies.

`start` spawns a detached loop that notifies at once and then every interval; `stop` ends it; `list`
shows the running ones. The owner is the nearest ancestor process named `claude`
(override: AGENT_SYNC_OWNER_PID).
"""

import argparse
import fcntl
import json
import os
import re
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Self

from agent_sync_common import (
    DEFAULT_POLL_SECONDS,
    ERROR_REPLY_PREFIX,
    POLL_SECONDS_ENVIRONMENT_VARIABLE,
    READY_MESSAGE,
    EnvironmentProblem,
    ExitCode,
    HerdrError,
    ProcessIdentity,
    atomic_write_json,
    find_owner_process,
    format_duration,
    install_stop_signal_handlers,
    is_same_process_alive,
    launch_detached,
    parse_duration,
    read_own_identity,
    read_seconds_setting,
    send_notification,
    signal_readiness,
    terminate_process,
)

NAG_ID_PATTERN = re.compile(r"[a-z0-9-]+")
STATE_HOME_ENVIRONMENT_VARIABLE = "XDG_STATE_HOME"
STATE_SUBDIRECTORY = Path("agent-sync") / "nag"
RECORD_SUFFIX = ".json"
LOCK_SUFFIX = ".lock"
DEFAULT_EVERY_SECONDS = 300.0
MIN_EVERY_SECONDS_ENVIRONMENT_VARIABLE = "AGENT_SYNC_NAG_MIN_SECONDS"
DEFAULT_MIN_EVERY_SECONDS = 30.0

DESCRIPTION = """\
Repeated herdr notification (sound: request) until stopped or the owning `claude` session dies.

State lives in ${XDG_STATE_HOME:-~/.local/state}/agent-sync/nag/. Nag ids are shared by every
session on the machine, so one session never replaces or stops another's nag without --force.

Exit codes:
  0   success
  1   stop: no such nag, or it belongs to another session
  2   usage or environment error, including a first notification herdr could not show
  75  busy, from start only: the id is already running for another live session, so nothing
      was started or replaced (--force overrides, on the operator's instruction only)

Each subcommand's --help says what it prints.
"""

START_DESCRIPTION = """\
Notify now and then every interval, until stopped or the owner session dies.

Prints on stdout, exit 0, once the first notification was shown:
  nag <id> started|replaced: every D, until stopped or owner pid N exits (loop pid P)
Prints on stderr, exit 75, when the id belongs to another live session:
  nag <id> belongs to another session (owner pid N), not replacing it; ...
Prints on stderr, exit 2, when herdr is missing or fails the first notification, or --every is
below the minimum; no loop is left running then.
"""

START_EPILOG = """\
Starting an id that is already running replaces it: the old loop is stopped and the new
title, body and interval take over, notifying immediately. A nag of another live session is
left alone unless --force is given. `start` succeeds only once the first notification was shown;
if herdr is missing or fails, it exits 2 and no loop is left running. The interval is at least
30s (override for tests: AGENT_SYNC_NAG_MIN_SECONDS). Two `start` or `stop` calls for the same id
take turns, so one id never has two loops.
"""

STOP_DESCRIPTION = """\
Stop a running nag.

Prints `nag <id> stopped` on stdout, exit 0. Prints on stderr, exit 1, `no running nag with id <id>`,
or `nag <id> belongs to another session ...` when its owner is another live session (--force
overrides, on the operator's instruction only).
"""

LIST_DESCRIPTION = """\
Show the running nags, oldest first. Always exit 0.

Prints on stdout one line per nag:
  <id>  "<title>"  started D ago  last sent D ago|never  every D  owner pid N  [last error: ...]
or `no running nags`.
"""


@dataclass
class NagRecord:
    nag_id: str
    title: str
    body: str
    every_seconds: float
    started_at: float
    owner_pid: int
    owner_start_ticks: int
    nagger_pid: int
    nagger_start_ticks: int
    last_sent_at: float | None = None
    last_error: str = ""

    @classmethod
    def from_json(cls, text: str) -> Self | None:
        try:
            return cls(**json.loads(text))
        except (ValueError, TypeError):
            return None

    @property
    def nagger(self) -> ProcessIdentity:
        return ProcessIdentity(self.nagger_pid, self.nagger_start_ticks)

    @property
    def owner(self) -> ProcessIdentity:
        return ProcessIdentity(self.owner_pid, self.owner_start_ticks)


class NagStore:
    def __init__(self, directory: Path):
        self._directory = directory

    @property
    def directory(self) -> Path:
        return self._directory

    def record_file(self, nag_id: str) -> Path:
        return self._directory / f"{nag_id}{RECORD_SUFFIX}"

    def read(self, nag_id: str) -> NagRecord | None:
        try:
            return NagRecord.from_json(self.record_file(nag_id).read_text())
        except OSError:
            return None

    def write(self, record: NagRecord):
        self._directory.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.record_file(record.nag_id), asdict(record))

    def remove_if_written_by(self, nag_id: str, nagger: ProcessIdentity):
        record = self.read(nag_id)
        if record and record.nagger == nagger:
            self.record_file(nag_id).unlink(missing_ok=True)

    @contextmanager
    def exclusive(self, nag_id: str) -> Iterator[None]:
        """Start and stop of one id take turns across processes: two concurrent `start` calls would
        each see no loop, launch one, and leave the first one running with no record, invisible
        to `list` and unreachable by `stop`."""
        self._directory.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self._directory / f"{nag_id}{LOCK_SUFFIX}", os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

    def running(self) -> list[NagRecord]:
        """Records whose loop is alive, oldest first; records of dead loops are removed."""
        running_records = []
        for record_file in sorted(self._directory.glob(f"*{RECORD_SUFFIX}")):
            nag_id = record_file.name.removesuffix(RECORD_SUFFIX)
            record = self.read(nag_id)
            if record and is_same_process_alive(record.nagger):
                running_records.append(record)
            else:
                record_file.unlink(missing_ok=True)
        return sorted(running_records, key=lambda record: record.started_at)


def resolve_state_directory() -> Path:
    state_home = os.environ.get(STATE_HOME_ENVIRONMENT_VARIABLE)
    return (Path(state_home) if state_home else Path.home() / ".local" / "state") / STATE_SUBDIRECTORY


def nag_id_argument(text: str) -> str:
    if not NAG_ID_PATTERN.fullmatch(text):
        raise argparse.ArgumentTypeError(f"invalid nag id {text!r}: use lowercase letters, digits and dashes")
    return text


def find_owner_process_if_any() -> ProcessIdentity | None:
    try:
        return find_owner_process()
    except EnvironmentProblem:
        return None


def find_other_sessions_nag(store: NagStore, nag_id: str, owner: ProcessIdentity | None) -> NagRecord | None:
    """The running nag with this id when its owner is another session that is still alive; the nag
    of a dead owner is an orphan that any session may replace or stop."""
    record = store.read(nag_id)
    if not record or not is_same_process_alive(record.nagger):
        return None
    if record.owner == owner or not is_same_process_alive(record.owner):
        return None
    return record


def refuse_other_sessions_nag(record: NagRecord, action: str):
    print(
        f"nag {record.nag_id} belongs to another session (owner pid {record.owner_pid}), not {action} it; "
        "pass --force only on the operator's instruction",
        file=sys.stderr,
    )


def stop_nag(store: NagStore, nag_id: str) -> bool:
    """True when a running loop was stopped; a record left by a dead loop is removed either way."""
    record = store.read(nag_id)
    if not record or not is_same_process_alive(record.nagger):
        store.record_file(nag_id).unlink(missing_ok=True)
        return False
    if not terminate_process(record.nagger):
        raise EnvironmentProblem(f"the loop of nag {nag_id} (pid {record.nagger_pid}) did not exit")
    store.record_file(nag_id).unlink(missing_ok=True)
    return True


def command_start(arguments: argparse.Namespace) -> ExitCode:
    owner = find_owner_process()
    minimum_every_seconds = read_seconds_setting(MIN_EVERY_SECONDS_ENVIRONMENT_VARIABLE, DEFAULT_MIN_EVERY_SECONDS)
    if arguments.every < minimum_every_seconds:
        raise EnvironmentProblem(
            f"--every must be at least {minimum_every_seconds:g}s, got {arguments.every:g}s: "
            "a shorter interval would flood the operator"
        )

    store = NagStore(resolve_state_directory())
    with store.exclusive(arguments.id):
        other_sessions_nag = find_other_sessions_nag(store, arguments.id, owner)
        if other_sessions_nag and not arguments.force:
            refuse_other_sessions_nag(other_sessions_nag, "replacing")
            return ExitCode.BUSY
        replaced = stop_nag(store, arguments.id)

        nagger_pid = launch_detached(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "_loop",
                arguments.id,
                f"--state-directory={store.directory}",
                f"--title={arguments.title}",
                f"--body={arguments.body}",
                f"--every-seconds={arguments.every}",
                f"--owner-pid={owner.pid}",
                f"--owner-start-ticks={owner.start_ticks}",
            ]
        )
    verb = "replaced" if replaced else "started"
    print(
        f"nag {arguments.id} {verb}: every {format_duration(arguments.every)}, "
        f"until stopped or owner pid {owner.pid} exits (loop pid {nagger_pid})"
    )
    return ExitCode.OK


def command_stop(arguments: argparse.Namespace) -> ExitCode:
    store = NagStore(resolve_state_directory())
    with store.exclusive(arguments.id):
        other_sessions_nag = find_other_sessions_nag(store, arguments.id, find_owner_process_if_any())
        if other_sessions_nag and not arguments.force:
            refuse_other_sessions_nag(other_sessions_nag, "stopping")
            return ExitCode.REFUSED

        if not stop_nag(store, arguments.id):
            print(f"no running nag with id {arguments.id}", file=sys.stderr)
            return ExitCode.REFUSED
    print(f"nag {arguments.id} stopped")
    return ExitCode.OK


def command_list(arguments: argparse.Namespace) -> ExitCode:
    records = NagStore(resolve_state_directory()).running()
    if not records:
        print("no running nags")
        return ExitCode.OK

    now = time.time()
    for record in records:
        last_sent = f"{format_duration(now - record.last_sent_at)} ago" if record.last_sent_at else "never"
        last_error = f"  last error: {record.last_error}" if record.last_error else ""
        print(
            f'{record.nag_id}  "{record.title}"  started {format_duration(now - record.started_at)} ago'
            f"  last sent {last_sent}  every {format_duration(record.every_seconds)}  owner pid {record.owner_pid}"
            f"{last_error}"
        )
    return ExitCode.OK


def deliver_repeat(store: NagStore, record: NagRecord):
    """A failing herdr does not end a loop that already started, so the operator is still reached
    once herdr is back; the failure is kept in the record for `list` to show."""
    try:
        send_notification(record.title, record.body)
    except HerdrError as failure:
        record.last_error = str(failure)
    else:
        record.last_sent_at = time.time()
        record.last_error = ""
    try:
        store.write(record)
    except OSError:
        return


def command_loop(arguments: argparse.Namespace) -> ExitCode:
    """The detached loop; started by `start`, never by a person. The first notification is part of
    being ready, so a `start` that reports success has already reached the operator once."""
    store = NagStore(Path(arguments.state_directory))
    owner = ProcessIdentity(arguments.owner_pid, arguments.owner_start_ticks)
    stop_requested = install_stop_signal_handlers()

    try:
        poll_seconds = read_seconds_setting(POLL_SECONDS_ENVIRONMENT_VARIABLE, DEFAULT_POLL_SECONDS)
        nagger = read_own_identity()
        record = NagRecord(
            nag_id=arguments.id,
            title=arguments.title,
            body=arguments.body,
            every_seconds=arguments.every_seconds,
            started_at=time.time(),
            owner_pid=owner.pid,
            owner_start_ticks=owner.start_ticks,
            nagger_pid=nagger.pid,
            nagger_start_ticks=nagger.start_ticks,
        )
        send_notification(record.title, record.body)
        record.last_sent_at = time.time()
        store.write(record)
    except HerdrError as failure:
        signal_readiness(
            arguments.readiness_file_descriptor, f"{ERROR_REPLY_PREFIX}the first notification failed: {failure}"
        )
        return ExitCode.ENVIRONMENT
    except (EnvironmentProblem, OSError) as failure:
        signal_readiness(
            arguments.readiness_file_descriptor, f"{ERROR_REPLY_PREFIX}the nag loop could not start: {failure}"
        )
        return ExitCode.ENVIRONMENT
    if not signal_readiness(arguments.readiness_file_descriptor, READY_MESSAGE):
        store.remove_if_written_by(arguments.id, nagger)
        return ExitCode.OK

    next_send = time.monotonic() + record.every_seconds
    try:
        while not stop_requested.is_set() and is_same_process_alive(owner):
            if time.monotonic() >= next_send:
                deliver_repeat(store, record)
                next_send = time.monotonic() + record.every_seconds
            stop_requested.wait(min(poll_seconds, max(next_send - time.monotonic(), 0.0)))
    finally:
        store.remove_if_written_by(arguments.id, nagger)
    return ExitCode.OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nag.py", description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subcommands = parser.add_subparsers(dest="command_name", metavar="COMMAND", required=True)

    start = subcommands.add_parser(
        "start",
        help="notify now and then every interval; exit 2 if the first notification fails, 75 if the id is taken",
        description=START_DESCRIPTION,
        epilog=START_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    start.add_argument("id", type=nag_id_argument)
    start.add_argument("--title", required=True, help="notification title, e.g. '<pane>: <question>'")
    start.add_argument("--body", default="", help="notification body")
    start.add_argument(
        "--every",
        type=parse_duration,
        default=DEFAULT_EVERY_SECONDS,
        metavar="DURATION",
        help="repeat interval, at least 30s (default 5m)",
    )
    start.add_argument(
        "--force", action="store_true", help="replace the nag of another live session (operator instruction only)"
    )

    stop = subcommands.add_parser(
        "stop",
        help="stop a running nag; exit 1 if there is none or it belongs to another session",
        description=STOP_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    stop.add_argument("id", type=nag_id_argument)
    stop.add_argument(
        "--force", action="store_true", help="stop the nag of another live session (operator instruction only)"
    )

    subcommands.add_parser(
        "list",
        help="running nags: id, title, started, last sent, owner, last error",
        description=LIST_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    loop = subcommands.add_parser("_loop")
    loop.add_argument("id", type=nag_id_argument)
    loop.add_argument("--state-directory", required=True)
    loop.add_argument("--title", required=True)
    loop.add_argument("--body", default="")
    loop.add_argument("--every-seconds", type=float, required=True)
    loop.add_argument("--owner-pid", type=int, required=True)
    loop.add_argument("--owner-start-ticks", type=int, required=True)
    loop.add_argument("--readiness-file-descriptor", type=int, required=True)
    return parser


def main(command_line_arguments: Sequence[str]) -> int:
    handlers: dict[str, Callable[[argparse.Namespace], ExitCode]] = {
        "start": command_start,
        "stop": command_stop,
        "list": command_list,
        "_loop": command_loop,
    }
    arguments = build_parser().parse_args(command_line_arguments)
    try:
        return int(handlers[arguments.command_name](arguments))
    except EnvironmentProblem as problem:
        print(f"nag: error: {problem}", file=sys.stderr)
        return ExitCode.ENVIRONMENT
    except OSError as failure:
        print(f"nag: error: {failure}", file=sys.stderr)
        return ExitCode.ENVIRONMENT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
