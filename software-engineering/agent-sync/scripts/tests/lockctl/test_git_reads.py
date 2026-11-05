from tests.utils.constants import FIRST_PANE_ID, INTEGRATE_LOCK, NO_IDLE_REQUIRED, NO_OPTIONAL_LOCKS_FLAG
from tests.utils.helpers import FakeHerdr, GitSpy, Session, wait_for_idle_observation


class TestGitReadsTakeNoOptionalLocks:
    def test_every_git_command_lockctl_runs_leaves_out_the_optional_locks_that_could_block_other_sessions(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr, git_spy: GitSpy
    ):
        first_session.run("acquire", INTEGRATE_LOCK, environment={**NO_IDLE_REQUIRED, **git_spy.path_environment})
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, INTEGRATE_LOCK)

        second_session.run("status", INTEGRATE_LOCK, environment=git_spy.path_environment)
        stolen = second_session.run("steal", INTEGRATE_LOCK, environment=git_spy.path_environment)

        calls = git_spy.calls()
        assert stolen.returncode == 0
        assert any(" status " in call for call in calls), f"the checkout's status was never read: {calls}"
        assert any(" branch " in call for call in calls), f"the holder's branch was never read: {calls}"
        assert all(call.startswith(f"{NO_OPTIONAL_LOCKS_FLAG} ") for call in calls), calls
