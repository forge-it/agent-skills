import os
import signal
from pathlib import Path

from tests.utils.constants import FIRST_PANE_ID, INTEGRATE_LOCK
from tests.utils.helpers import Session, process_is_running, wait_for_first_observation, wait_until


class TestCheck:
    def test_check_exits_zero_when_the_caller_holds_the_lock(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)

        checked = first_session.run("check", INTEGRATE_LOCK)

        assert checked.returncode == 0
        assert "held by you" in checked.output

    def test_check_exits_one_when_the_lock_is_free(self, first_session: Session):
        checked = first_session.run("check", INTEGRATE_LOCK)

        assert checked.returncode == 1
        assert "free" in checked.output

    def test_check_exits_one_when_someone_else_holds_the_lock(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)

        checked = second_session.run("check", INTEGRATE_LOCK)

        assert checked.returncode == 1
        assert "held by someone else" in checked.output
        assert FIRST_PANE_ID in checked.output

    def test_check_exits_one_after_the_holder_was_killed_without_cleanup(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        os.kill(holder_pid, signal.SIGKILL)
        wait_until(lambda: not process_is_running(holder_pid), "the killed holder to disappear")

        checked = first_session.run("check", INTEGRATE_LOCK)
        assert checked.returncode == 1
        assert "free" in checked.output

    def test_check_exits_one_when_the_recorded_holder_pid_belongs_to_a_newer_process(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        wait_for_first_observation(first_session, INTEGRATE_LOCK)
        first_session.simulate_holder_pid_reuse(INTEGRATE_LOCK)

        checked = first_session.run("check", INTEGRATE_LOCK)

        assert checked.returncode == 1
        assert "held by someone else" in checked.output

    def test_check_exits_one_for_the_same_owner_from_another_worktree_and_names_the_holding_worktree(
        self, first_session: Session, linked_worktree: Path, git_repository: Path
    ):
        first_session.run("acquire", INTEGRATE_LOCK)

        checked = first_session.run("check", INTEGRATE_LOCK, working_directory=linked_worktree)

        assert checked.returncode == 1
        assert "your own session from another worktree" in checked.output
        assert str(git_repository) in checked.output

    def test_check_exits_zero_from_a_subdirectory_of_the_worktree_that_holds_the_lock(
        self, first_session: Session, git_repository: Path
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        subdirectory = git_repository / "nested"
        subdirectory.mkdir()

        checked = first_session.run("check", INTEGRATE_LOCK, working_directory=subdirectory)

        assert checked.returncode == 0

    def test_check_exits_zero_in_the_linked_worktree_that_took_the_lock(
        self, first_session: Session, linked_worktree: Path
    ):
        first_session.run("acquire", INTEGRATE_LOCK, working_directory=linked_worktree)

        assert first_session.run("check", INTEGRATE_LOCK, working_directory=linked_worktree).returncode == 0
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 1
