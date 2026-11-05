from pathlib import Path

from tests.utils.constants import INTEGRATE_LOCK
from tests.utils.helpers import Session, process_is_running, wait_for_first_observation


class TestRelease:
    def test_release_frees_the_lock_for_another_owner(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)

        released = first_session.run("release", INTEGRATE_LOCK)

        assert released.returncode == 0
        assert second_session.run("acquire", INTEGRATE_LOCK).returncode == 0

    def test_release_stops_the_holder_process_and_removes_its_record(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        first_session.run("release", INTEGRATE_LOCK)

        assert not process_is_running(holder_pid)
        assert first_session.record(INTEGRATE_LOCK) is None

    def test_release_by_another_owner_is_refused_and_the_lock_stays_held(
        self, first_session: Session, second_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK)

        refused = second_session.run("release", INTEGRATE_LOCK)

        assert refused.returncode == 1
        assert "not held by you" in refused.output
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_release_of_a_free_lock_exits_one(self, first_session: Session):
        refused = first_session.run("release", INTEGRATE_LOCK)

        assert refused.returncode == 1
        assert "free" in refused.output

    def test_release_logs_a_release_event(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)

        first_session.run("release", INTEGRATE_LOCK)

        assert f"release lock={INTEGRATE_LOCK}" in first_session.events()

    def test_release_then_acquire_again_starts_a_fresh_hold(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        first_holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        first_session.run("release", INTEGRATE_LOCK)

        first_session.run("acquire", INTEGRATE_LOCK)

        assert first_session.record(INTEGRATE_LOCK)["holder_pid"] != first_holder_pid
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_release_leaves_alone_a_process_that_reuses_the_recorded_holder_pid(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        wait_for_first_observation(first_session, INTEGRATE_LOCK)
        record = first_session.record(INTEGRATE_LOCK)
        first_session.simulate_holder_pid_reuse(INTEGRATE_LOCK)

        refused = first_session.run("release", INTEGRATE_LOCK)

        assert refused.returncode == 1
        assert process_is_running(record["holder_pid"])

    def test_release_from_another_worktree_of_the_same_owner_is_refused_and_the_lock_stays_held(
        self, first_session: Session, linked_worktree: Path, git_repository: Path
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        refused = first_session.run("release", INTEGRATE_LOCK, working_directory=linked_worktree)

        assert refused.returncode == 1
        assert "not held by you" in refused.output
        assert str(git_repository) in refused.output
        assert process_is_running(holder_pid)
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_release_by_the_owner_frees_a_lock_whose_record_is_missing(
        self, first_session: Session, second_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        wait_for_first_observation(first_session, INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        first_session.delete_record(INTEGRATE_LOCK)

        released = first_session.run("release", INTEGRATE_LOCK)

        assert released.returncode == 0
        assert not process_is_running(holder_pid)
        assert second_session.run("acquire", INTEGRATE_LOCK).returncode == 0

    def test_release_of_a_lock_whose_record_is_missing_is_refused_for_another_owner(
        self, first_session: Session, second_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        wait_for_first_observation(first_session, INTEGRATE_LOCK)
        first_session.delete_record(INTEGRATE_LOCK)

        refused = second_session.run("release", INTEGRATE_LOCK)

        assert refused.returncode == 1
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0
