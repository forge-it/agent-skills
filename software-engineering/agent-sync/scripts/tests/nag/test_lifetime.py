import os
from pathlib import Path

from tests.utils.helpers import Session, process_is_running, wait_until


class TestNagLifetime:
    def test_nag_ends_and_cleans_up_when_the_owner_process_dies(self, nag_session: Session, owner_process):
        nag_session.run("start", "design", "--title", "which design?", "--every", "60s")
        loop_pid = nag_session.nag_record("design")["nagger_pid"]

        owner_process.kill()
        owner_process.wait()

        wait_until(lambda: not process_is_running(loop_pid), "the nag loop to exit after its owner died")
        assert nag_session.nag_record("design") is None

    def test_nag_loop_runs_in_its_own_session_without_inherited_output(self, nag_session: Session):
        nag_session.run("start", "design", "--title", "which design?", "--every", "60s", timeout=15)

        loop_pid = nag_session.nag_record("design")["nagger_pid"]
        assert os.getsid(loop_pid) == loop_pid
        assert Path(f"/proc/{loop_pid}/fd/1").resolve() == Path(os.devnull)

    def test_nag_without_an_owner_process_is_an_environment_error(self, nag_session: Session):
        failed = nag_session.run(
            "start", "design", "--title", "which design?", environment={"AGENT_SYNC_OWNER_PID": "99999999"}
        )

        assert failed.returncode == 2
        assert "not a running process" in failed.output
