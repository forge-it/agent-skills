"""The command line of lockctl.py: help texts, the parser, and the split of `run`'s command."""

import argparse
import re
from collections.abc import Sequence

from agent_sync_common import parse_duration

LOCK_NAME_PATTERN = re.compile(r"[a-z0-9-]+")

DESCRIPTION = """\
Named locks per repository, held by a detached process that frees them when the owning
`claude` session dies.

The owner is the nearest ancestor process named `claude` (override: AGENT_SYNC_OWNER_PID). A hold
belongs to its owner and to the worktree it was taken from (the git toplevel of the current
directory), because subagents run inside their orchestrator's process and the owner cannot tell
them apart: only that worktree re-enters, checks or releases the hold.

Exit codes:
  0   success
  1   the lock is not held by you (check, release)
  2   usage or environment error
  75  busy: acquire, run or steal found the lock held by someone else, the --wait ran out,
      or the steal was refused (read `status` before doing anything else)
`run` passes its command's own exit code through (127 when it cannot be found, 126 when not
executable), so a 75 from `run` can come from the command itself. lockctl's own busy refusal is the
75 with a `lock <name> is held by ...` message on stderr and no output from the command.

Each subcommand's --help says what it prints.
"""

EPILOG = """\
Environment:
  AGENT_SYNC_OWNER_PID          owner process, instead of the nearest `claude` ancestor
  AGENT_SYNC_HERDR              herdr binary (else HERDR_BIN_PATH, else `herdr` on PATH)
  AGENT_SYNC_POLL_SECONDS       how often a holder checks its owner (default 2)
  AGENT_SYNC_REFRESH_SECONDS    how often a holder re-reads its pane's herdr state (default 30)
"""

ACQUIRE_DESCRIPTION = """\
Take the lock for this session and this worktree. The hold survives across tool calls and ends
with `release`, a steal, or the exit of the owning session.

Prints on stdout, exit 0:
  acquired <lock> (owner pid N, pane P, holder pid H)
  lock <lock> is already held by you (holder pid H)     (same owner, same worktree)
Prints on stderr, exit 75, when the lock is held by someone else, or by your own session from
another worktree: `lock <lock> is held by <pane, owner, branch, worktree, purpose, held for>`.
With --wait it first prints `waiting up to D for lock <lock>, held by ...`, and `gave up after D`
when the wait runs out.
"""

RELEASE_DESCRIPTION = """\
Release a lock this session holds from this worktree: the commands running under it are stopped,
then the holder.

Prints `released <lock>` on stdout, exit 0. Exit 1, with the reason on stderr, when the lock is
free or held by someone else (including your own session from another worktree).
"""

CHECK_DESCRIPTION = """\
Exit 0 only if this session holds the lock from this worktree. Always prints one line on stdout:
  lock <lock> is held by you since <time> (pane P)                           exit 0
  lock <lock> is free: you do not hold it                                    exit 1
  lock <lock> is held by someone else: <holder>                              exit 1
  lock <lock> is held by your own session from another worktree, not by this one: <holder>
                                                                             exit 1
A lock stolen from you is reported as `; it was stolen from you at <time> by pane P`.
"""

STATUS_DESCRIPTION = """\
Show who holds which lock, what runs under it, and whether it can be stolen. Always exit 0.

Prints on stdout one block per lock (every lock of the repository, or the one named):
  <lock>  free
  <lock>  HELD [(by you)], then lines for holder (pane, owner pid, holder pid), where (branch,
  worktree, directory), purpose, held for, herdr (state of the holder's pane, idle time), one
  `run pid` line per command running under the lock, and `stealable yes|no: <reason>`.
`no locks yet` when there are none. --json prints the same facts as a JSON array, one object per lock.
A free lock that commands still run on (a killed `run` leaves its command behind) lists them too, with
a note that the next `acquire`, `run` or `steal` stops them before it takes over.
"""

RUN_DESCRIPTION = """\
Hold the lock only while a command runs: lockctl.py run <lock> [--wait D] [--purpose P] -- <command...>

The command's own stdout and stderr pass through, and so does its exit code (128+N when it was
killed by signal N, 127 when it cannot be found, 126 when it is not executable): a 75 from `run`
can therefore come from the command. lockctl's own busy refusal is the 75 that comes with
`lock <lock> is held by ...` on stderr and no output from the command, which never started.
Other lockctl messages (`waiting up to ...`, `stopping the command: ...`) go to stderr; nothing
lockctl prints goes to stdout.

Inside a lock this session took with `acquire` from the same worktree, `run` does not lock again:
it registers the command as an activity of that lock, and a lock with a running activity is never
stolen without --force. Inside any other hold, including your own session's from another worktree,
`run` waits like any contender.
"""

RUN_EPILOG = """\
The command runs in its own process group, which is stopped as a whole (SIGTERM, then SIGKILL)
when the lock is released or stolen, when the owner exits, and when the command ends while
something it started is still running: nothing started under a lock outlives it.

If the `run` process itself is killed, its command keeps running with no lock. It still counts as
running under the lock: `status` lists it, even where the lock shows as free, and the lock cannot be
stolen without --force; `release`, `steal --force` and the holder's exit stop it, and so does the
next `acquire`, `run` or `steal` of a lock that `run` held, before that takes over: two users never
share the resource.
"""

STEAL_DESCRIPTION = """\
Take a lock from a holder that forgot it, when that is safe; a free lock is simply acquired.
Allowed only when no command runs under the lock, herdr shows the holder's pane idle or done and
unchanged for as long as the holder asked when it took the lock (10 minutes by default; the thief
cannot shorten it), and, for `integrate`, the worktree the hold was taken from (the git toplevel
`acquire` ran in, which must still exist) has no tracked changes and no merge or rebase in
progress. Pane ids belong to one herdr session, so the thief's HERDR_SESSION must be the one the
holder ran in. Whatever cannot be verified counts as not stealable.

Prints on stdout, exit 0: `stole lock <lock> from pane P (owner pid N)`, then
`acquired <lock> (...)`. Prints on stderr, exit 75, `steal refused: lock <lock> is held by
<holder>: <reason>`, or `steal lost the race: ...` when a waiting acquirer took the freed lock
first. The victim learns of the theft from `check`.
"""

STEAL_EPILOG = """\
--force skips the eligibility check and stops the commands running under the lock and the holder
itself. It also frees a lock whose record is missing. Use it only on the operator's instruction.
"""


def lock_name_argument(text: str) -> str:
    if not LOCK_NAME_PATTERN.fullmatch(text):
        raise argparse.ArgumentTypeError(f"invalid lock name {text!r}: use lowercase letters, digits and dashes")
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lockctl.py", description=DESCRIPTION, epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subcommands = parser.add_subparsers(dest="command_name", metavar="COMMAND", required=True)

    acquire = subcommands.add_parser(
        "acquire",
        help="take a lock for this session; survives across tool calls",
        description=ACQUIRE_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    acquire.add_argument("lock", type=lock_name_argument)
    acquire.add_argument(
        "--wait",
        type=parse_duration,
        default=0.0,
        metavar="DURATION",
        help="wait this long for a busy lock (90s, 15m, 1h); exit 75 when it runs out",
    )
    acquire.add_argument("--purpose", default="", help="what the lock is for, shown to the others")

    release = subcommands.add_parser(
        "release",
        help="release a lock this session holds",
        description=RELEASE_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    release.add_argument("lock", type=lock_name_argument)

    check = subcommands.add_parser(
        "check",
        help="exit 0 only if this session holds the lock",
        description=CHECK_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    check.add_argument("lock", type=lock_name_argument)

    status = subcommands.add_parser(
        "status",
        help="who holds which lock, what runs under it, whether it can be stolen",
        description=STATUS_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    status.add_argument("lock", nargs="?", type=lock_name_argument)
    status.add_argument("--json", action="store_true", help="machine-readable output")

    run = subcommands.add_parser(
        "run",
        help="run <lock> -- <command...>: hold a lock only while a command runs; exits with the command's own "
        "code, and 75 when the lock is busy",
        description=RUN_DESCRIPTION,
        epilog=RUN_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run.add_argument("lock", type=lock_name_argument)
    run.add_argument(
        "--wait",
        type=parse_duration,
        default=0.0,
        metavar="DURATION",
        help="wait this long for a busy lock (90s, 15m, 1h); exit 75 when it runs out",
    )
    run.add_argument("--purpose", default="", help="what the lock is for, shown to the others")

    steal = subcommands.add_parser(
        "steal",
        help="take a lock from an idle holder, when that is safe; exit 75 when it is refused",
        description=STEAL_DESCRIPTION,
        epilog=STEAL_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    steal.add_argument("lock", type=lock_name_argument)
    steal.add_argument("--force", action="store_true", help="skip the eligibility check (operator instruction only)")
    steal.add_argument("--purpose", default="", help="what the lock is for, shown to the others")

    hold = subcommands.add_parser("_hold")
    hold.add_argument("lock", type=lock_name_argument)
    hold.add_argument("--state-directory", required=True)
    hold.add_argument("--owner-pid", type=int, required=True)
    hold.add_argument("--owner-start-ticks", type=int, required=True)
    hold.add_argument("--scope", required=True)
    hold.add_argument("--lock-file-descriptor", type=int, required=True)
    hold.add_argument("--readiness-file-descriptor", type=int, required=True)
    hold.add_argument("--purpose", default="")
    return parser


def parse_arguments(command_line_arguments: Sequence[str]) -> argparse.Namespace:
    parser = build_parser()
    command_tokens: list[str] = []
    lockctl_tokens = list(command_line_arguments)
    if lockctl_tokens[:1] == ["run"] and "--" in lockctl_tokens:
        separator_index = lockctl_tokens.index("--")
        command_tokens = lockctl_tokens[separator_index + 1 :]
        lockctl_tokens = lockctl_tokens[:separator_index]

    arguments = parser.parse_args(lockctl_tokens)
    if arguments.command_name == "run":
        if not command_tokens:
            parser.error("run needs a command after `--`: lockctl.py run <lock> -- <command...>")
        arguments.command = command_tokens
    return arguments
