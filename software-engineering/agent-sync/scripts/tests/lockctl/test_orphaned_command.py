import subprocess
from pathlib import Path

from tests.utils.constants import BUSY_EXIT_CODE, FIRST_PANE_ID, NO_IDLE_REQUIRED, STACK_LOCK
from tests.utils.helpers import (
    FakeHerdr,
    OrphanedCommand,
    Session,
    plant_activity_of_a_dead_run,
    process_is_running,
    wait_for_idle_observation,
    wait_until,
)


class TestOrphanedCommandStaysAnActivity:
    def test_status_lists_the_command_of_a_killed_run_process_as_still_running(
        self, first_session: Session, orphan_in_an_acquired_lock: OrphanedCommand
    ):
        report = first_session.lock_report(STACK_LOCK)

        assert orphan_in_an_acquired_lock.is_running
        assert len(report["activities"]) == 1
        assert report["activities"][0]["orphaned"] is True
        assert "the run process is gone" in first_session.run("status", STACK_LOCK).output

    def test_status_lists_the_command_of_a_killed_run_process_under_the_lock_it_held_which_is_free(
        self, first_session: Session, orphan_of_a_killed_run_holding_the_lock: OrphanedCommand
    ):
        status = first_session.run("status", STACK_LOCK)

        assert orphan_of_a_killed_run_holding_the_lock.is_running
        assert f"{STACK_LOCK}  free, but 1 command(s) still running on it" in status.output
        assert "the run process is gone" in status.output
        assert "the next `acquire`, `run` or `steal` of this lock stops these commands" in status.output

    def test_status_json_lists_the_command_of_a_killed_run_process_under_the_lock_it_held_which_is_free(
        self, first_session: Session, orphan_of_a_killed_run_holding_the_lock: OrphanedCommand
    ):
        report = first_session.lock_report(STACK_LOCK)

        assert report["state"] == "free"
        assert [activity["orphaned"] for activity in report["activities"]] == [True]
        assert report["activities"][0]["process_group_id"] == orphan_of_a_killed_run_holding_the_lock.process_group_id
        assert "the next `acquire`, `run` or `steal` of this lock stops these commands" in report["reason"]

    def test_status_stops_listing_the_command_of_a_killed_run_process_under_a_free_lock_once_it_ended(
        self, first_session: Session, orphan_of_a_killed_run_holding_the_lock: OrphanedCommand
    ):
        orphan_of_a_killed_run_holding_the_lock.kill()
        wait_until(lambda: not orphan_of_a_killed_run_holding_the_lock.is_running, "the orphaned command to end")

        report = first_session.lock_report(STACK_LOCK)

        assert report["state"] == "free"
        assert report["activities"] == []
        assert report["reason"] == ""

    def test_status_json_lists_no_command_under_a_free_lock_that_nothing_ran_on(self, first_session: Session):
        first_session.run("acquire", STACK_LOCK)
        first_session.run("release", STACK_LOCK)

        report = first_session.lock_report(STACK_LOCK)

        assert report["state"] == "free"
        assert report["activities"] == []

    def test_steal_is_refused_while_the_command_of_a_killed_run_process_still_runs(
        self,
        first_session: Session,
        second_session: Session,
        fake_herdr: FakeHerdr,
        orphan_in_an_acquired_lock: OrphanedCommand,
    ):
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, STACK_LOCK)

        refused = second_session.run("steal", STACK_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "still running" in refused.output
        assert orphan_in_an_acquired_lock.is_running
        assert first_session.run("check", STACK_LOCK).returncode == 0

    def test_steal_is_allowed_once_the_orphaned_command_ended_by_itself(
        self,
        first_session: Session,
        second_session: Session,
        fake_herdr: FakeHerdr,
        orphan_in_an_acquired_lock: OrphanedCommand,
    ):
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, STACK_LOCK)
        orphan_in_an_acquired_lock.kill()
        wait_until(lambda: not orphan_in_an_acquired_lock.is_running, "the orphaned command to end")

        stolen = second_session.run("steal", STACK_LOCK)

        assert stolen.returncode == 0

    def test_a_reused_process_group_id_is_not_mistaken_for_the_orphaned_command(
        self,
        first_session: Session,
        second_session: Session,
        fake_herdr: FakeHerdr,
        unrelated_process_group: subprocess.Popen[bytes],
    ):
        first_session.run("acquire", STACK_LOCK, environment=NO_IDLE_REQUIRED)
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, STACK_LOCK)
        plant_activity_of_a_dead_run(first_session, STACK_LOCK, unrelated_process_group.pid, leader_start_ticks=1)

        stolen = second_session.run("steal", STACK_LOCK)

        assert stolen.returncode == 0
        assert process_is_running(unrelated_process_group.pid)


class TestOrphanedCommandIsStoppedBeforeHandover:
    def test_release_stops_the_command_of_a_killed_run_process(
        self, first_session: Session, orphan_in_an_acquired_lock: OrphanedCommand
    ):
        released = first_session.run("release", STACK_LOCK)

        assert released.returncode == 0
        assert not orphan_in_an_acquired_lock.is_running

    def test_steal_force_stops_the_command_of_a_killed_run_process(
        self, second_session: Session, orphan_in_an_acquired_lock: OrphanedCommand
    ):
        forced = second_session.run("steal", STACK_LOCK, "--force")

        assert forced.returncode == 0
        assert not orphan_in_an_acquired_lock.is_running
        assert second_session.run("check", STACK_LOCK).returncode == 0

    def test_holder_stops_the_command_of_a_killed_run_process_when_its_owner_dies(
        self, owner_process: subprocess.Popen[bytes], orphan_in_an_acquired_lock: OrphanedCommand
    ):
        owner_process.kill()
        owner_process.wait()

        wait_until(lambda: not orphan_in_an_acquired_lock.is_running, "the holder to stop the orphaned command")

    def test_acquire_stops_the_command_left_by_a_run_process_that_held_the_lock_when_it_was_killed(
        self, second_session: Session, orphan_of_a_killed_run_holding_the_lock: OrphanedCommand
    ):
        acquired = second_session.run("acquire", STACK_LOCK)

        assert acquired.returncode == 0
        assert not orphan_of_a_killed_run_holding_the_lock.is_running
        assert second_session.run("check", STACK_LOCK).returncode == 0

    def test_run_stops_the_command_left_by_a_run_process_that_held_the_lock_when_it_was_killed(
        self, second_session: Session, orphan_of_a_killed_run_holding_the_lock: OrphanedCommand, tmp_path: Path
    ):
        side_effect = tmp_path / "side-effect"

        result = second_session.run("run", STACK_LOCK, "--", "touch", str(side_effect))

        assert result.returncode == 0
        assert side_effect.exists()
        assert not orphan_of_a_killed_run_holding_the_lock.is_running

    def test_steal_of_the_lock_of_a_killed_run_process_stops_its_command_before_taking_over(
        self, second_session: Session, orphan_of_a_killed_run_holding_the_lock: OrphanedCommand
    ):
        stolen = second_session.run("steal", STACK_LOCK)

        assert stolen.returncode == 0
        assert not orphan_of_a_killed_run_holding_the_lock.is_running
