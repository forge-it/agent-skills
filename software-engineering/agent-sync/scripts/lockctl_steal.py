"""When a lock may be taken from its holder."""

import time
from dataclasses import dataclass
from pathlib import Path

from agent_sync_common import PaneReading, describe_herdr_session_mismatch, format_duration, read_pane_reading

from lockctl_records import LockRecord
from lockctl_store import LockStore, run_git

INTEGRATE_LOCK_NAME = "integrate"
IN_PROGRESS_MARKERS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply")


@dataclass(frozen=True)
class StealAssessment:
    allowed: bool
    reason: str
    reading: PaneReading | None = None


class StealPolicy:
    def __init__(self, store: LockStore):
        self._store = store

    def assess(self, record: LockRecord) -> StealAssessment:
        """Stealable only when nothing runs under the lock, herdr itself shows the holder pane
        idle or done and has not moved since the holder first saw it idle, that has lasted the
        idle threshold the holder recorded when it took the lock, and (for `integrate`) the
        worktree the hold was taken from is clean. herdr shows a pane idle while its session waits
        on a background command, hence the first condition. Anything that cannot be verified
        counts as not stealable."""
        running_commands = self._describe_running_commands(record.lock)
        if running_commands:
            return StealAssessment(False, running_commands)

        refusal, reading = self._verify_pane_stayed_resting(record)
        if refusal:
            return StealAssessment(False, refusal, reading)
        assert record.idle_since, "a pane that stayed resting was seen idle by its holder"
        idle_for_seconds = time.time() - record.idle_since
        if idle_for_seconds < record.idle_threshold_seconds:
            required = format_duration(record.idle_threshold_seconds)
            reason = f"idle for {format_duration(idle_for_seconds)}, {required} required"
            return StealAssessment(False, reason, reading)

        if record.lock == INTEGRATE_LOCK_NAME:
            checkout_problem = self._describe_checkout_problem(record)
            if checkout_problem:
                return StealAssessment(False, checkout_problem, reading)

        refusal, reading = self._verify_pane_stayed_resting(record)
        if refusal:
            return StealAssessment(False, refusal, reading)
        running_commands = self._describe_running_commands(record.lock)
        if running_commands:
            return StealAssessment(False, running_commands, reading)
        return StealAssessment(True, f"idle for {format_duration(idle_for_seconds)}", reading)

    def _describe_running_commands(self, lock_name: str) -> str:
        activities = self._store.live_activities(lock_name)
        if not activities:
            return ""
        commands = ", ".join(
            f"`{activity.command}` (run pid {activity.run_pid}{', gone' if activity.is_orphaned else ''})"
            for activity in activities
        )
        return f"{len(activities)} command(s) still running under the lock: {commands}"

    @staticmethod
    def _verify_pane_stayed_resting(record: LockRecord) -> tuple[str, PaneReading | None]:
        """A fresh herdr reading against what the holder recorded when it first saw the pane idle;
        the first element is the reason it cannot be stolen, empty when it can."""
        if not record.pane_id:
            return "the holder has no herdr pane id, so its state cannot be verified", None
        session_mismatch = describe_herdr_session_mismatch(record.herdr_session)
        if session_mismatch:
            return f"the holder's state cannot be verified: {session_mismatch}", None

        reading = read_pane_reading(record.pane_id, record.herdr_session)
        if not reading:
            return "herdr is unavailable, so the holder's state cannot be verified", None
        if not reading.status.is_resting:
            return f"the holder pane is {reading.status}", reading
        if not record.idle_since:
            return "the holder has not been seen idle yet", reading
        if reading.state_change_sequence is None:
            return "herdr reports no state change sequence, so the holder's idleness cannot be verified", reading
        if reading.state_change_sequence != record.idle_state_change_sequence:
            return "the holder pane changed state since the holder first saw it idle", reading
        return "", reading

    @staticmethod
    def _describe_checkout_problem(record: LockRecord) -> str:
        """Judges the worktree the hold was taken from (its recorded scope), not the repository's
        main worktree: with linked worktrees, or a bare repository with worktrees, they are
        different places, and the one with a merge half done is the one that matters."""
        if not record.scope:
            return "the hold recorded no worktree, so the checkout it works in cannot be judged"
        worktree = Path(record.scope)
        if not worktree.is_dir():
            return f"the worktree the hold was taken from ({record.scope}) no longer exists"

        toplevel = (run_git(["rev-parse", "--show-toplevel"], worktree) or "").strip()
        if not toplevel or Path(toplevel).resolve() != worktree.resolve():
            return f"{record.scope} is not the top of a git work tree, so its state cannot be judged"
        status_output = run_git(["status", "--porcelain", "--untracked-files=no"], worktree)
        if status_output is None:
            return f"cannot read the status of the worktree {record.scope}"
        if status_output.strip():
            return f"the worktree {record.scope} has uncommitted changes"

        git_directory = (run_git(["rev-parse", "--absolute-git-dir"], worktree) or "").strip()
        if not git_directory:
            return f"cannot locate the git directory of the worktree {record.scope}"
        for marker in IN_PROGRESS_MARKERS:
            if (Path(git_directory) / marker).exists():
                return f"the worktree {record.scope} has a {marker} in progress"
        return ""
