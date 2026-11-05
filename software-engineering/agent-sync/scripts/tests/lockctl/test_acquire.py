from collections.abc import Callable
from pathlib import Path

from tests.utils.constants import BUSY_EXIT_CODE, FIRST_PANE_ID, INTEGRATE_LOCK, LONG_WAIT_ARGUMENT, PROBE_HOLD_SECONDS
from tests.utils.helpers import Session, collect_output, hold_flock_briefly, process_is_running, read_stderr_line


class TestAcquire:
    def test_acquire_succeeds_and_check_confirms_the_hold(self, first_session: Session):
        acquired = first_session.run("acquire", INTEGRATE_LOCK)

        assert acquired.returncode == 0
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_acquire_writes_the_holder_record(self, first_session: Session, owner_process):
        first_session.run("acquire", INTEGRATE_LOCK, "--purpose", "merge feature-x")

        record = first_session.record(INTEGRATE_LOCK)
        assert record["owner_pid"] == owner_process.pid
        assert record["pane_id"] == FIRST_PANE_ID
        assert record["purpose"] == "merge feature-x"
        assert record["branch"] == "main"
        assert process_is_running(record["holder_pid"])

    def test_acquire_by_the_same_owner_from_the_same_worktree_again_keeps_the_single_holder(
        self, first_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        first_holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        repeated = first_session.run("acquire", INTEGRATE_LOCK)

        assert repeated.returncode == 0
        assert f"already held by you (holder pid {first_holder_pid})" in repeated.output
        assert first_session.record(INTEGRATE_LOCK)["holder_pid"] == first_holder_pid

    def test_acquire_by_the_same_owner_from_a_subdirectory_of_the_same_worktree_keeps_the_single_holder(
        self, first_session: Session, git_repository: Path
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        first_holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        subdirectory = git_repository / "nested"
        subdirectory.mkdir()

        repeated = first_session.run("acquire", INTEGRATE_LOCK, working_directory=subdirectory)

        assert repeated.returncode == 0
        assert f"already held by you (holder pid {first_holder_pid})" in repeated.output

    def test_acquire_by_the_same_owner_from_another_worktree_is_busy_and_names_the_holding_worktree(
        self, first_session: Session, linked_worktree: Path, git_repository: Path
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        first_holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        refused = first_session.run("acquire", INTEGRATE_LOCK, working_directory=linked_worktree)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "your own session" in refused.output
        assert f"worktree {git_repository}" in refused.output
        assert first_session.record(INTEGRATE_LOCK)["holder_pid"] == first_holder_pid

    def test_acquire_with_wait_from_another_worktree_of_the_same_owner_gets_the_lock_once_the_holder_releases(
        self, first_session: Session, linked_worktree: Path
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        waiting = first_session.popen(
            "acquire", INTEGRATE_LOCK, "--wait", LONG_WAIT_ARGUMENT, working_directory=linked_worktree
        )
        assert "waiting up to" in read_stderr_line(waiting)

        first_session.run("release", INTEGRATE_LOCK)

        assert collect_output(waiting).returncode == 0
        assert first_session.run("check", INTEGRATE_LOCK, working_directory=linked_worktree).returncode == 0
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 1

    def test_acquire_by_another_owner_is_refused_while_the_lock_is_held(
        self, first_session: Session, second_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK, "--purpose", "merge feature-x")

        refused = second_session.run("acquire", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert FIRST_PANE_ID in refused.output
        assert "merge feature-x" in refused.output
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_acquire_with_wait_gives_up_when_the_lock_stays_busy(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)

        gave_up = second_session.run("acquire", INTEGRATE_LOCK, "--wait", "1s")

        assert gave_up.returncode == BUSY_EXIT_CODE
        assert "gave up" in gave_up.output

    def test_acquire_with_wait_succeeds_once_the_holder_releases(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        waiting = second_session.popen("acquire", INTEGRATE_LOCK, "--wait", LONG_WAIT_ARGUMENT)
        assert "waiting up to" in read_stderr_line(waiting)

        first_session.run("release", INTEGRATE_LOCK)

        assert collect_output(waiting).returncode == 0
        assert second_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_acquire_rejects_an_invalid_lock_name(self, first_session: Session):
        rejected = first_session.run("acquire", "Not_A_Valid_Name")

        assert rejected.returncode == 2
        assert "invalid lock name" in rejected.output

    def test_acquire_accepts_any_valid_lock_name(self, first_session: Session):
        assert first_session.run("acquire", "release-train-2").returncode == 0

    def test_acquire_outside_a_git_repository_fails_with_an_environment_error(
        self, first_session: Session, plain_directory: Path
    ):
        failed = first_session.run("acquire", INTEGRATE_LOCK, working_directory=plain_directory)

        assert failed.returncode == 2
        assert "not inside a git repository" in failed.output

    def test_acquire_fails_when_the_owner_override_is_not_a_running_process(self, first_session: Session):
        failed = first_session.run("acquire", INTEGRATE_LOCK, environment={"AGENT_SYNC_OWNER_PID": "99999999"})

        assert failed.returncode == 2
        assert "not a running process" in failed.output

    def test_acquire_logs_an_acquire_event(self, first_session: Session, owner_process):
        first_session.run("acquire", INTEGRATE_LOCK)

        assert f"acquire lock={INTEGRATE_LOCK} owner_pid={owner_process.pid} pane={FIRST_PANE_ID}" in (
            first_session.events()
        )

    def test_acquire_from_a_linked_worktree_shares_the_lock_with_the_main_checkout(
        self, first_session: Session, second_session: Session, linked_worktree: Path
    ):
        first_session.run("acquire", INTEGRATE_LOCK)

        refused = second_session.run("acquire", INTEGRATE_LOCK, working_directory=linked_worktree)

        assert refused.returncode == BUSY_EXIT_CODE

    def test_acquire_by_many_owners_at_once_grants_the_lock_to_exactly_one(
        self, lockctl_session_factory: Callable[[int], Session]
    ):
        sessions = [lockctl_session_factory(index) for index in range(1, 6)]
        racing = [session.popen("acquire", INTEGRATE_LOCK) for session in sessions]

        returncodes = [collect_output(process).returncode for process in racing]

        assert sorted(returncodes) == [0, BUSY_EXIT_CODE, BUSY_EXIT_CODE, BUSY_EXIT_CODE, BUSY_EXIT_CODE]
        winner = sessions[returncodes.index(0)]
        assert winner.run("check", INTEGRATE_LOCK).returncode == 0

    def test_acquire_succeeds_although_a_status_probe_holds_the_flock_for_a_moment(self, first_session: Session):
        probe = hold_flock_briefly(first_session.state_directory / f"{INTEGRATE_LOCK}.lock", PROBE_HOLD_SECONDS)

        acquired = first_session.run("acquire", INTEGRATE_LOCK)

        probe.join()
        assert acquired.returncode == 0
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0
