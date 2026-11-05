from tests.utils.helpers import Session


class TestHelp:
    def test_help_states_that_75_means_the_id_is_taken_by_another_live_session(self, nag_session: Session):
        helped = nag_session.run("--help")

        assert helped.returncode == 0
        assert "75  busy, from start only" in helped.stdout
        assert "already running for another live session" in helped.stdout

    def test_start_help_says_what_start_prints_on_success_and_on_a_taken_id(self, nag_session: Session):
        helped = nag_session.run("start", "--help")

        assert "nag <id> started|replaced" in helped.stdout
        assert "exit 75" in helped.stdout
        assert "belongs to another session" in helped.stdout

    def test_stop_help_says_what_stop_prints(self, nag_session: Session):
        helped = nag_session.run("stop", "--help")

        assert "nag <id> stopped" in helped.stdout
        assert "no running nag with id" in helped.stdout

    def test_list_help_says_what_list_prints(self, nag_session: Session):
        helped = nag_session.run("list", "--help")

        assert "no running nags" in helped.stdout
        assert "last sent" in helped.stdout
