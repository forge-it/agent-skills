import json
import os
import signal
from pathlib import Path

from tests.utils.constants import (
    FIRST_PANE_ID,
    INTEGRATE_LOCK,
    OTHER_HERDR_SESSION,
    OTHER_HERDR_SESSION_NAME,
    STACK_LOCK,
    WAIT_FOR_MARKER_COMMAND,
)
from tests.utils.helpers import (
    Session,
    collect_output,
    process_is_running,
    wait_for_command_to_run_under,
    wait_for_first_observation,
    wait_for_idle_observation,
    wait_until,
)


class TestStatus:
    def test_status_with_no_locks_says_so(self, first_session: Session):
        status = first_session.run("status")

        assert status.returncode == 0
        assert "no locks yet" in status.output

    def test_status_reports_a_lock_that_was_never_used_as_free(self, first_session: Session):
        status = first_session.run("status", INTEGRATE_LOCK)

        assert status.returncode == 0
        assert f"{INTEGRATE_LOCK}  free" in status.output

    def test_status_shows_the_holder_details(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK, "--purpose", "merge feature-x")

        status = second_session.run("status", INTEGRATE_LOCK)

        assert "HELD" in status.output
        assert f"pane {FIRST_PANE_ID}" in status.output
        assert "branch main" in status.output
        assert "merge feature-x" in status.output
        assert "working" in status.output
        assert "stealable  no" in status.output

    def test_status_marks_the_lock_as_held_by_you_for_its_holder(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)

        status = first_session.run("status", INTEGRATE_LOCK)

        assert "HELD (by you)" in status.output

    def test_status_lists_every_lock_in_the_repository(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        first_session.run("acquire", STACK_LOCK)
        first_session.run("release", STACK_LOCK)

        status = first_session.run("status")

        assert f"{INTEGRATE_LOCK}  HELD" in status.output
        assert f"{STACK_LOCK}  free" in status.output

    def test_status_json_describes_the_holder(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK, "--purpose", "merge feature-x")

        reports = json.loads(second_session.run("status", "--json").stdout)

        assert len(reports) == 1
        assert reports[0]["lock"] == INTEGRATE_LOCK
        assert reports[0]["state"] == "held"
        assert reports[0]["pane_id"] == FIRST_PANE_ID
        assert reports[0]["purpose"] == "merge feature-x"
        assert reports[0]["stealable"] is False

    def test_status_reports_a_killed_holder_as_free_and_removes_its_stale_record(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        os.kill(holder_pid, signal.SIGKILL)
        wait_until(lambda: not process_is_running(holder_pid), "the killed holder to disappear")
        assert first_session.record(INTEGRATE_LOCK) is not None

        status = first_session.run("status", INTEGRATE_LOCK)

        assert f"{INTEGRATE_LOCK}  free" in status.output
        assert first_session.record(INTEGRATE_LOCK) is None
        assert f"expire lock={INTEGRATE_LOCK}" in first_session.events()

    def test_status_shows_how_long_the_holder_pane_has_been_idle(
        self, idle_integrate_holder_with_default_threshold: Session, second_session: Session
    ):
        wait_for_idle_observation(idle_integrate_holder_with_default_threshold, INTEGRATE_LOCK)

        status = second_session.run("status", INTEGRATE_LOCK)

        assert "idle, idle for" in status.output
        assert "required" in status.output

    def test_status_marks_an_idle_holder_stealable_once_the_threshold_passed(
        self, idle_integrate_holder: Session, second_session: Session
    ):
        status = second_session.run("status", INTEGRATE_LOCK)

        assert "stealable  yes" in status.output

    def test_status_does_not_credit_the_recorded_owner_when_the_recorded_holder_process_is_not_alive(
        self, first_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        wait_for_first_observation(first_session, INTEGRATE_LOCK)
        first_session.simulate_holder_pid_reuse(INTEGRATE_LOCK)

        report = first_session.lock_report(INTEGRATE_LOCK)

        assert report["state"] == "held"
        assert report["held_by_you"] is False
        assert report["stealable"] is False

    def test_status_lists_the_commands_running_under_a_lock(self, first_session: Session, tmp_path: Path):
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )
        wait_for_command_to_run_under(first_session, STACK_LOCK)

        status = first_session.run("status", STACK_LOCK)
        marker.touch()
        collect_output(running)

        assert f"run pid {running.pid}: sh -c" in status.output

    def test_status_drops_the_command_of_a_run_process_that_was_killed(self, first_session: Session, tmp_path: Path):
        first_session.run("acquire", STACK_LOCK)
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )
        wait_for_command_to_run_under(first_session, STACK_LOCK)

        os.kill(running.pid, signal.SIGKILL)
        running.wait()
        marker.touch()

        wait_until(
            lambda: first_session.lock_report(STACK_LOCK)["activities"] == [],
            "the command of the killed run process to end and its activity to be dropped",
        )

    def test_status_shows_the_worktree_that_took_the_lock(self, first_session: Session, git_repository: Path):
        first_session.run("acquire", INTEGRATE_LOCK)

        status = first_session.run("status", INTEGRATE_LOCK)

        assert f"worktree {git_repository}" in status.output
        assert first_session.lock_report(INTEGRATE_LOCK)["scope"] == str(git_repository)

    def test_status_shows_the_holder_of_a_lock_whose_record_is_missing(
        self, first_session: Session, second_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        wait_for_first_observation(first_session, INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        first_session.delete_record(INTEGRATE_LOCK)

        report = second_session.lock_report(INTEGRATE_LOCK)
        status = second_session.run("status", INTEGRATE_LOCK)

        assert report["state"] == "held"
        assert report["holder_pid"] == holder_pid
        assert report["stealable"] is False
        assert "record is missing" in report["reason"]
        assert f"holder pid {holder_pid}" in status.output

    def test_status_marks_a_lock_whose_record_is_missing_as_held_by_you_for_its_owner(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        wait_for_first_observation(first_session, INTEGRATE_LOCK)
        first_session.delete_record(INTEGRATE_LOCK)

        assert first_session.lock_report(INTEGRATE_LOCK)["held_by_you"] is True


class TestStatusAcrossHerdrSessions:
    def test_status_says_why_a_holder_in_another_herdr_session_cannot_be_judged(
        self, idle_integrate_holder: Session, second_session: Session
    ):
        status = second_session.run("status", INTEGRATE_LOCK, environment=OTHER_HERDR_SESSION)

        assert "stealable  no" in status.output
        assert f"herdr session '{OTHER_HERDR_SESSION_NAME}'" in status.output
        assert "cannot be verified" in status.output
