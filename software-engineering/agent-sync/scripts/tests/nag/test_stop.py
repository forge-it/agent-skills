from tests.utils.constants import FIRST_PANE_ID
from tests.utils.helpers import FakeHerdr, Session, process_is_running, wait_until


class TestStop:
    def test_stop_ends_the_loop_and_removes_the_nag(self, nag_session: Session, fake_herdr: FakeHerdr):
        nag_session.run("start", "design", "--title", FIRST_PANE_ID, "--every", "0.3s")
        wait_until(lambda: len(fake_herdr.notifications()) >= 2, "two notifications")
        loop_pid = nag_session.nag_record("design")["nagger_pid"]

        stopped = nag_session.run("stop", "design")

        assert stopped.returncode == 0
        assert not process_is_running(loop_pid)
        assert nag_session.nag_record("design") is None
        assert "no running nags" in nag_session.run("list").stdout

    def test_stop_of_an_unknown_id_exits_one(self, nag_session: Session):
        stopped = nag_session.run("stop", "never-started")

        assert stopped.returncode == 1
        assert "no running nag" in stopped.output

    def test_stop_only_ends_the_named_nag(self, nag_session: Session):
        nag_session.run("start", "design", "--title", "design question", "--every", "60s")
        nag_session.run("start", "deploy", "--title", "deploy question", "--every", "60s")

        nag_session.run("stop", "design")

        listed = nag_session.run("list").stdout
        assert "deploy question" in listed
        assert "design question" not in listed

    def test_stop_refuses_to_stop_the_nag_of_another_session(self, nag_session: Session, second_nag_session: Session):
        nag_session.run("start", "design", "--title", "design question", "--every", "60s")
        loop_pid = nag_session.nag_record("design")["nagger_pid"]

        refused = second_nag_session.run("stop", "design")

        assert refused.returncode == 1
        assert "belongs to another session" in refused.output
        assert process_is_running(loop_pid)

    def test_stop_with_force_stops_the_nag_of_another_session(self, nag_session: Session, second_nag_session: Session):
        nag_session.run("start", "design", "--title", "design question", "--every", "60s")
        loop_pid = nag_session.nag_record("design")["nagger_pid"]

        stopped = second_nag_session.run("stop", "design", "--force")

        assert stopped.returncode == 0
        assert not process_is_running(loop_pid)
        assert nag_session.nag_record("design") is None
