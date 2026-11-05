import os
import signal

from tests.utils.helpers import Session, process_is_running, wait_until


class TestList:
    def test_list_with_no_nags_says_so(self, nag_session: Session):
        listed = nag_session.run("list")

        assert listed.returncode == 0
        assert "no running nags" in listed.output

    def test_list_shows_id_title_last_sent_and_owner(self, nag_session: Session, owner_process):
        nag_session.run("start", "design", "--title", "which design?", "--every", "60s")
        wait_until(
            lambda: (nag_session.nag_record("design") or {}).get("last_sent_at"), "the first send to be recorded"
        )

        listed = nag_session.run("list").stdout

        assert 'design  "which design?"' in listed
        assert "last sent" in listed
        assert "last sent never" not in listed
        assert f"owner pid {owner_process.pid}" in listed

    def test_list_drops_a_nag_whose_loop_was_killed(self, nag_session: Session):
        nag_session.run("start", "design", "--title", "which design?", "--every", "60s")
        loop_pid = nag_session.nag_record("design")["nagger_pid"]
        os.kill(loop_pid, signal.SIGKILL)
        wait_until(lambda: not process_is_running(loop_pid), "the killed loop to disappear")

        listed = nag_session.run("list")

        assert "no running nags" in listed.output
        assert nag_session.nag_record("design") is None
