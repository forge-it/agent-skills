from tests.utils.helpers import Session


class TestHelp:
    def test_help_states_that_run_passes_the_command_exit_code_through_so_a_75_can_come_from_the_command(
        self, first_session: Session
    ):
        helped = first_session.run("--help")

        assert helped.returncode == 0
        assert "passes its command's own exit code through" in helped.stdout
        assert "a 75 from `run` can come from the command itself" in helped.stdout

    def test_help_does_not_document_the_idle_seconds_variable(self, first_session: Session):
        for arguments in (("--help",), ("steal", "--help"), ("status", "--help"), ("acquire", "--help")):
            assert "AGENT_SYNC_IDLE_SECONDS" not in first_session.run(*arguments).stdout

    def test_run_help_states_that_a_75_can_come_from_the_command(self, first_session: Session):
        helped = first_session.run("run", "--help")

        assert "a 75 from `run`" in helped.stdout
        assert "can therefore come from the command" in helped.stdout
        assert "nothing\nlockctl prints goes to stdout" in helped.stdout

    def test_acquire_help_says_what_acquire_prints(self, first_session: Session):
        helped = first_session.run("acquire", "--help")

        assert "acquired <lock> (owner pid N, pane P, holder pid H)" in helped.stdout
        assert "already held by you" in helped.stdout
        assert "another worktree" in helped.stdout

    def test_release_help_says_what_release_prints(self, first_session: Session):
        helped = first_session.run("release", "--help")

        assert "released <lock>" in helped.stdout
        assert "Exit 1" in helped.stdout

    def test_check_help_says_what_check_prints(self, first_session: Session):
        helped = first_session.run("check", "--help")

        assert "lock <lock> is held by you since <time>" in helped.stdout
        assert "is held by someone else" in helped.stdout

    def test_status_help_says_what_status_prints(self, first_session: Session):
        helped = first_session.run("status", "--help")

        assert "<lock>  free" in helped.stdout
        assert "stealable yes|no" in helped.stdout
        assert "no locks yet" in helped.stdout

    def test_steal_help_says_what_steal_prints_and_that_the_holder_sets_the_idle_time(self, first_session: Session):
        helped = first_session.run("steal", "--help")

        assert "stole lock <lock> from pane P" in helped.stdout
        assert "steal refused" in helped.stdout
        assert "the thief\ncannot shorten it" in helped.stdout
