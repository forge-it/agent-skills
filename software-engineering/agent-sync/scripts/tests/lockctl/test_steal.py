from collections.abc import Callable
from pathlib import Path

from tests.utils.builders import leave_a_merge_with_conflicts
from tests.utils.constants import (
    BUSY_EXIT_CODE,
    FIRST_PANE_ID,
    HERDR_UNAVAILABLE,
    INTEGRATE_LOCK,
    NO_HERDR_SESSION,
    NO_IDLE_REQUIRED,
    NO_IDLE_REQUIRED_NO_HERDR_SESSION,
    NO_IDLE_REQUIRED_NO_PANE,
    NO_IDLE_REQUIRED_SAMPLED_ONCE,
    NO_PANE,
    OTHER_HERDR_SESSION,
    OTHER_HERDR_SESSION_NAME,
    SECOND_PANE_ID,
    STACK_LOCK,
    TRACKED_FILE_NAME,
    WAIT_FOR_MARKER_COMMAND,
)
from tests.utils.helpers import (
    FakeHerdr,
    LockPoacher,
    Session,
    collect_output,
    process_is_running,
    run_git_command,
    wait_for_command_to_run_under,
    wait_for_first_observation,
    wait_for_idle_observation,
    wait_until,
)


class TestStealRefusals:
    def test_steal_is_refused_while_the_holder_is_working(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED)

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "working" in refused.output
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_steal_is_refused_while_the_holder_is_blocked(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr
    ):
        fake_herdr.set_status(FIRST_PANE_ID, "blocked")
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED)

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "blocked" in refused.output

    def test_steal_is_refused_when_the_holder_has_been_idle_for_less_than_the_threshold(
        self, idle_integrate_holder_with_default_threshold: Session, second_session: Session
    ):
        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "required" in refused.output
        assert idle_integrate_holder_with_default_threshold.run("check", INTEGRATE_LOCK).returncode == 0

    def test_steal_is_refused_although_the_thief_asks_for_no_idle_time_in_its_own_environment(
        self, idle_integrate_holder_with_default_threshold: Session, second_session: Session
    ):
        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "10m 00s required" in refused.output
        assert idle_integrate_holder_with_default_threshold.run("check", INTEGRATE_LOCK).returncode == 0

    def test_steal_applies_the_idle_threshold_the_holder_recorded_when_it_took_the_lock(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr
    ):
        first_session.run("acquire", INTEGRATE_LOCK, environment={"AGENT_SYNC_IDLE_SECONDS": "90"})
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, INTEGRATE_LOCK)

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert first_session.record(INTEGRATE_LOCK)["idle_threshold_seconds"] == 90.0
        assert "1m 30s required" in refused.output

    def test_steal_is_refused_when_a_tracked_file_of_the_shared_checkout_has_uncommitted_changes(
        self, idle_integrate_holder: Session, second_session: Session, git_repository: Path
    ):
        (git_repository / TRACKED_FILE_NAME).write_text("work in progress")

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "uncommitted changes" in refused.output

    def test_steal_is_refused_while_a_merge_is_in_progress(
        self, idle_integrate_holder: Session, second_session: Session, git_repository: Path
    ):
        head_commit = run_git_command(git_repository, "rev-parse", "HEAD").strip()
        (git_repository / ".git" / "MERGE_HEAD").write_text(f"{head_commit}\n")

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "MERGE_HEAD" in refused.output

    def test_steal_is_refused_while_a_rebase_is_in_progress(
        self, idle_integrate_holder: Session, second_session: Session, git_repository: Path
    ):
        (git_repository / ".git" / "rebase-merge").mkdir()

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "rebase-merge" in refused.output

    def test_steal_is_refused_when_herdr_is_unavailable(self, idle_integrate_holder: Session, second_session: Session):
        refused = second_session.run("steal", INTEGRATE_LOCK, environment=HERDR_UNAVAILABLE)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "herdr is unavailable" in refused.output

    def test_steal_is_refused_when_the_holder_has_no_herdr_pane(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED_NO_PANE)

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "no herdr pane id" in refused.output

    def test_steal_from_yourself_is_refused(self, idle_integrate_holder: Session):
        refused = idle_integrate_holder.run("steal", INTEGRATE_LOCK, "--force")

        assert refused.returncode == BUSY_EXIT_CODE
        assert "you already hold" in refused.output


class TestStealIdleContinuity:
    def test_steal_is_refused_when_the_holder_pane_worked_unobserved_between_two_samples(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr
    ):
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED_SAMPLED_ONCE)
        wait_for_idle_observation(first_session, INTEGRATE_LOCK)
        fake_herdr.simulate_unobserved_work(FIRST_PANE_ID)

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "changed state" in refused.output
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_steal_is_refused_when_herdr_reports_no_state_change_sequence(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr
    ):
        fake_herdr.stop_reporting_sequences()
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED)
        wait_for_idle_observation(first_session, INTEGRATE_LOCK)

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "no state change sequence" in refused.output

    def test_holder_restarts_the_idle_time_when_the_pane_worked_between_two_of_its_samples(
        self, idle_integrate_holder: Session, fake_herdr: FakeHerdr
    ):
        first_idle_since = idle_integrate_holder.record(INTEGRATE_LOCK)["idle_since"]

        fake_herdr.simulate_unobserved_work(FIRST_PANE_ID)

        wait_until(
            lambda: idle_integrate_holder.record(INTEGRATE_LOCK)["idle_since"] > first_idle_since,
            "the holder to restart its idle time",
        )

    def test_steal_reads_herdr_again_after_judging_the_shared_checkout(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr
    ):
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED_SAMPLED_ONCE)
        wait_for_idle_observation(first_session, INTEGRATE_LOCK)
        reads_before = fake_herdr.read_count(FIRST_PANE_ID)

        stolen = second_session.run("steal", INTEGRATE_LOCK)

        assert stolen.returncode == 0
        assert fake_herdr.read_count(FIRST_PANE_ID) - reads_before == 2


class TestStealWhileACommandRuns:
    def test_steal_is_refused_while_a_run_command_holds_the_lock_even_though_herdr_shows_the_pane_idle(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr, tmp_path: Path
    ):
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run",
            STACK_LOCK,
            "--",
            "sh",
            "-c",
            WAIT_FOR_MARKER_COMMAND.format(marker=marker),
            environment=NO_IDLE_REQUIRED,
        )
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, STACK_LOCK)

        refused = second_session.run("steal", STACK_LOCK)
        still_running = running.poll() is None
        marker.touch()
        collect_output(running)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "still running" in refused.output
        assert still_running

    def test_steal_force_takes_the_lock_from_a_run_command_and_stops_it(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr, tmp_path: Path
    ):
        marker = tmp_path / "finish-marker"
        finished = tmp_path / "finished"
        command = f"{WAIT_FOR_MARKER_COMMAND.format(marker=marker)}; touch {finished}"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", command)
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, STACK_LOCK)

        forced = second_session.run("steal", STACK_LOCK, "--force")

        marker.touch()
        collect_output(running)
        assert forced.returncode == 0
        assert not finished.exists()
        assert second_session.run("check", STACK_LOCK).returncode == 0

    def test_steal_is_refused_while_a_command_runs_inside_an_acquired_lock_and_allowed_once_it_ends(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr, tmp_path: Path
    ):
        first_session.run("acquire", STACK_LOCK, environment=NO_IDLE_REQUIRED)
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, STACK_LOCK)
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )
        wait_for_command_to_run_under(first_session, STACK_LOCK)

        refused = second_session.run("steal", STACK_LOCK)
        marker.touch()
        collect_output(running)
        stolen = second_session.run("steal", STACK_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "still running" in refused.output
        assert stolen.returncode == 0


class TestStealAllowed:
    def test_steal_of_a_free_lock_acts_like_acquire(self, second_session: Session):
        stolen = second_session.run("steal", INTEGRATE_LOCK)

        assert stolen.returncode == 0
        assert second_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_steal_succeeds_when_the_holder_has_been_idle_past_the_threshold(
        self, idle_integrate_holder: Session, second_session: Session
    ):
        old_holder_pid = idle_integrate_holder.record(INTEGRATE_LOCK)["holder_pid"]

        stolen = second_session.run("steal", INTEGRATE_LOCK, "--purpose", "merge after steal")

        assert stolen.returncode == 0
        assert "stole lock" in stolen.stdout
        assert not process_is_running(old_holder_pid)
        assert second_session.run("check", INTEGRATE_LOCK).returncode == 0
        assert second_session.record(INTEGRATE_LOCK)["purpose"] == "merge after steal"

    def test_steal_succeeds_when_the_holder_pane_is_done(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr
    ):
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED)
        fake_herdr.set_status(FIRST_PANE_ID, "done")
        wait_for_idle_observation(first_session, INTEGRATE_LOCK)

        stolen = second_session.run("steal", INTEGRATE_LOCK)

        assert stolen.returncode == 0

    def test_steal_reports_the_theft_to_the_victim_check(self, idle_integrate_holder: Session, second_session: Session):
        second_session.run("steal", INTEGRATE_LOCK)

        victim_check = idle_integrate_holder.run("check", INTEGRATE_LOCK)

        assert victim_check.returncode == 1
        assert "stolen from you" in victim_check.output
        assert SECOND_PANE_ID in victim_check.output

    def test_steal_note_is_cleared_when_the_victim_acquires_again(
        self, idle_integrate_holder: Session, second_session: Session
    ):
        second_session.run("steal", INTEGRATE_LOCK)
        second_session.run("release", INTEGRATE_LOCK)

        idle_integrate_holder.run("acquire", INTEGRATE_LOCK)
        idle_integrate_holder.run("release", INTEGRATE_LOCK)

        assert "stolen from you" not in idle_integrate_holder.run("check", INTEGRATE_LOCK).output

    def test_steal_logs_a_steal_event(self, idle_integrate_holder: Session, second_session: Session):
        second_session.run("steal", INTEGRATE_LOCK)

        assert f"steal lock={INTEGRATE_LOCK}" in second_session.events()
        assert f"from_pane={FIRST_PANE_ID}" in second_session.events()

    def test_steal_does_not_check_the_shared_checkout_for_other_locks(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr, git_repository: Path
    ):
        first_session.run("acquire", STACK_LOCK, environment=NO_IDLE_REQUIRED)
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, STACK_LOCK)
        (git_repository / TRACKED_FILE_NAME).write_text("work in progress")

        stolen = second_session.run("steal", STACK_LOCK)

        assert stolen.returncode == 0

    def test_steal_ignores_untracked_files_in_the_shared_checkout(
        self, idle_integrate_holder: Session, second_session: Session, git_repository: Path
    ):
        (git_repository / "scratch-notes.txt").write_text("not part of any commit")

        stolen = second_session.run("steal", INTEGRATE_LOCK)

        assert stolen.returncode == 0


class TestStealJudgesTheWorktreeTheHoldWasTakenFrom:
    def test_steal_ignores_uncommitted_changes_of_a_worktree_the_hold_was_not_taken_from(
        self, idle_integrate_holder: Session, second_session: Session, linked_worktree: Path
    ):
        (linked_worktree / TRACKED_FILE_NAME).write_text("work in a worker worktree")

        stolen = second_session.run("steal", INTEGRATE_LOCK, working_directory=linked_worktree)

        assert stolen.returncode == 0

    def test_steal_is_refused_when_the_worktree_of_the_hold_is_dirty_even_from_a_clean_linked_worktree(
        self, idle_integrate_holder: Session, second_session: Session, linked_worktree: Path, git_repository: Path
    ):
        (git_repository / TRACKED_FILE_NAME).write_text("work in progress")

        refused = second_session.run("steal", INTEGRATE_LOCK, working_directory=linked_worktree)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "uncommitted changes" in refused.output

    def test_steal_is_refused_when_the_hold_was_taken_in_a_linked_worktree_that_is_in_the_middle_of_a_merge(
        self,
        idle_holder_in_linked_worktree: Session,
        second_session: Session,
        linked_worktree: Path,
        git_repository: Path,
    ):
        leave_a_merge_with_conflicts(git_repository, linked_worktree)

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "uncommitted changes" in refused.output
        assert str(linked_worktree) in refused.output
        assert (
            idle_holder_in_linked_worktree.run("check", INTEGRATE_LOCK, working_directory=linked_worktree).returncode
            == 0
        )

    def test_steal_is_refused_when_a_merge_is_in_progress_in_the_linked_worktree_of_the_hold(
        self, idle_holder_in_linked_worktree: Session, second_session: Session, linked_worktree: Path
    ):
        head_commit = run_git_command(linked_worktree, "rev-parse", "HEAD").strip()
        git_directory = Path(run_git_command(linked_worktree, "rev-parse", "--absolute-git-dir").strip())
        (git_directory / "MERGE_HEAD").write_text(f"{head_commit}\n")

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "MERGE_HEAD" in refused.output

    def test_steal_succeeds_when_the_linked_worktree_of_the_hold_is_clean_although_the_main_worktree_is_not(
        self, idle_holder_in_linked_worktree: Session, second_session: Session, git_repository: Path
    ):
        (git_repository / TRACKED_FILE_NAME).write_text("work in progress")

        stolen = second_session.run("steal", INTEGRATE_LOCK)

        assert stolen.returncode == 0

    def test_steal_succeeds_in_a_bare_repository_with_worktrees_when_the_worktree_of_the_hold_is_clean(
        self, bare_layout_holder: Session, bare_layout_thief: Session
    ):
        stolen = bare_layout_thief.run("steal", INTEGRATE_LOCK)

        assert stolen.returncode == 0
        assert bare_layout_thief.run("check", INTEGRATE_LOCK).returncode == 0

    def test_steal_is_refused_in_a_bare_repository_with_worktrees_when_the_worktree_of_the_hold_is_dirty(
        self, bare_layout_holder: Session, bare_layout_thief: Session, bare_repository_worktree: Path
    ):
        (bare_repository_worktree / TRACKED_FILE_NAME).write_text("work in progress")

        refused = bare_layout_thief.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "uncommitted changes" in refused.output

    def test_steal_is_refused_when_the_hold_was_taken_in_a_bare_repository_itself(
        self,
        lockctl_session_factory: Callable[..., Session],
        fake_herdr: FakeHerdr,
        bare_repository: Path,
        bare_repository_worktree: Path,
    ):
        holder = lockctl_session_factory(1, bare_repository_worktree)
        thief = lockctl_session_factory(2, bare_repository_worktree)
        holder.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED, working_directory=bare_repository)
        fake_herdr.set_status(holder.pane_id, "idle")
        wait_for_idle_observation(holder, INTEGRATE_LOCK)

        refused = thief.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "not the top of a git work tree" in refused.output

    def test_steal_is_refused_when_the_worktree_of_the_hold_no_longer_exists(
        self,
        idle_holder_in_linked_worktree: Session,
        second_session: Session,
        linked_worktree: Path,
        git_repository: Path,
    ):
        run_git_command(git_repository, "worktree", "remove", "--force", str(linked_worktree))

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "no longer exists" in refused.output

    def test_steal_is_refused_when_the_record_names_no_worktree(
        self, idle_integrate_holder: Session, second_session: Session
    ):
        idle_integrate_holder.rewrite_record(INTEGRATE_LOCK, scope="")

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "recorded no worktree" in refused.output

    def test_steal_force_takes_the_lock_although_the_worktree_of_the_hold_no_longer_exists(
        self,
        idle_holder_in_linked_worktree: Session,
        second_session: Session,
        linked_worktree: Path,
        git_repository: Path,
    ):
        run_git_command(git_repository, "worktree", "remove", "--force", str(linked_worktree))

        forced = second_session.run("steal", INTEGRATE_LOCK, "--force")

        assert forced.returncode == 0


class TestStealAcrossHerdrSessions:
    def test_steal_is_refused_when_the_thief_runs_in_another_herdr_session_than_the_holder(
        self, idle_integrate_holder: Session, second_session: Session
    ):
        refused = second_session.run("steal", INTEGRATE_LOCK, environment=OTHER_HERDR_SESSION)

        assert refused.returncode == BUSY_EXIT_CODE
        assert f"herdr session '{OTHER_HERDR_SESSION_NAME}'" in refused.output
        assert idle_integrate_holder.run("check", INTEGRATE_LOCK).returncode == 0

    def test_steal_is_refused_when_the_thief_has_no_herdr_session_but_the_holder_has_one(
        self, idle_integrate_holder: Session, second_session: Session
    ):
        refused = second_session.run("steal", INTEGRATE_LOCK, environment=NO_HERDR_SESSION)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "no herdr session" in refused.output

    def test_steal_is_refused_when_the_holder_had_no_herdr_session_but_the_thief_has_one(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr
    ):
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED_NO_HERDR_SESSION)
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, INTEGRATE_LOCK)

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "no herdr session" in refused.output

    def test_steal_is_allowed_when_both_run_without_a_herdr_session(
        self, first_session: Session, second_session: Session, fake_herdr: FakeHerdr
    ):
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED_NO_HERDR_SESSION)
        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_for_idle_observation(first_session, INTEGRATE_LOCK)

        stolen = second_session.run("steal", INTEGRATE_LOCK, environment=NO_HERDR_SESSION)

        assert stolen.returncode == 0

    def test_steal_force_takes_the_lock_across_herdr_sessions(
        self, idle_integrate_holder: Session, second_session: Session
    ):
        forced = second_session.run("steal", INTEGRATE_LOCK, "--force", environment=OTHER_HERDR_SESSION)

        assert forced.returncode == 0


class TestStealRace:
    def test_steal_reports_who_won_when_a_waiter_takes_the_freed_lock_first(
        self,
        idle_integrate_holder: Session,
        second_session: Session,
        lockctl_session_factory: Callable[[int], Session],
        lock_poacher_factory: Callable[..., LockPoacher],
    ):
        waiter_session = lockctl_session_factory(3)
        poacher = lock_poacher_factory(waiter_session, INTEGRATE_LOCK)
        poacher.start()

        lost = second_session.run("steal", INTEGRATE_LOCK)

        assert poacher.won_the_lock()
        assert lost.returncode == BUSY_EXIT_CODE
        assert "stole lock" not in lost.output
        assert "steal lost the race" in lost.output
        assert waiter_session.pane_id in lost.output

    def test_steal_that_lost_the_race_tells_the_victim_who_holds_the_lock_now(
        self,
        idle_integrate_holder: Session,
        second_session: Session,
        lockctl_session_factory: Callable[[int], Session],
        lock_poacher_factory: Callable[..., LockPoacher],
    ):
        waiter_session = lockctl_session_factory(3)
        poacher = lock_poacher_factory(waiter_session, INTEGRATE_LOCK)
        poacher.start()
        second_session.run("steal", INTEGRATE_LOCK)
        assert poacher.won_the_lock()

        victim_check = idle_integrate_holder.run("check", INTEGRATE_LOCK)

        assert victim_check.returncode == 1
        assert "stolen from you at" in victim_check.output
        assert f"by pane {waiter_session.pane_id}" in victim_check.output
        assert f"by pane {SECOND_PANE_ID}" not in victim_check.output


class TestStealForce:
    def test_steal_force_takes_the_lock_from_a_working_holder(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        old_holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        stolen = second_session.run("steal", INTEGRATE_LOCK, "--force")

        assert stolen.returncode == 0
        assert not process_is_running(old_holder_pid)
        assert second_session.run("check", INTEGRATE_LOCK).returncode == 0
        assert "stolen from you" in first_session.run("check", INTEGRATE_LOCK).output

    def test_steal_force_marks_the_event_as_forced(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)

        second_session.run("steal", INTEGRATE_LOCK, "--force")

        assert "forced=yes" in second_session.events()

    def test_steal_force_works_without_herdr(self, first_session: Session, second_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_PANE)

        stolen = second_session.run("steal", INTEGRATE_LOCK, "--force", environment=HERDR_UNAVAILABLE)

        assert stolen.returncode == 0
        wait_until(lambda: second_session.record(INTEGRATE_LOCK), "the thief's holder record")


class TestStealWhenTheRecordIsMissing:
    def test_steal_without_force_is_refused_because_the_holder_cannot_be_verified(
        self, first_session: Session, second_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED)
        wait_for_first_observation(first_session, INTEGRATE_LOCK)
        first_session.delete_record(INTEGRATE_LOCK)

        refused = second_session.run("steal", INTEGRATE_LOCK)

        assert refused.returncode == BUSY_EXIT_CODE
        assert "its record is missing" in refused.output
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_steal_force_frees_a_lock_whose_record_is_missing_while_its_owner_lives(
        self, first_session: Session, second_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        wait_for_first_observation(first_session, INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        first_session.delete_record(INTEGRATE_LOCK)

        stolen = second_session.run("steal", INTEGRATE_LOCK, "--force")

        assert stolen.returncode == 0
        assert not process_is_running(holder_pid)
        assert second_session.run("check", INTEGRATE_LOCK).returncode == 0
