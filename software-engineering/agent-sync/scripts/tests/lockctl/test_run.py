import os
import signal
import time
from pathlib import Path

from tests.utils.constants import (
    BUSY_EXIT_CODE,
    FIRST_PANE_ID,
    GRANDCHILD_COMMAND,
    INTEGRATE_LOCK,
    LONG_WAIT_ARGUMENT,
    POLLS_TO_SURVIVE,
    SIGTERM_EXIT_CODE,
    SIGTERM_IGNORING_GRANDCHILD_COMMAND,
    STACK_LOCK,
    SURVIVAL_WINDOW_SECONDS,
    WAIT_FOR_MARKER_COMMAND,
)
from tests.utils.helpers import (
    FakeHerdr,
    Session,
    collect_output,
    file_descriptors_exhausted,
    process_is_running,
    read_pid_file,
    read_stderr_line,
    wait_for_command_to_run_under,
    wait_until,
)


class TestRun:
    def test_run_exits_with_the_exit_code_of_the_command(self, first_session: Session):
        result = first_session.run("run", STACK_LOCK, "--", "sh", "-c", "exit 7")

        assert result.returncode == 7

    def test_run_passes_the_command_output_through(self, first_session: Session):
        result = first_session.run("run", STACK_LOCK, "--", "echo", "hello from the stack")

        assert result.returncode == 0
        assert "hello from the stack" in result.stdout

    def test_run_holds_the_lock_only_while_the_command_runs(
        self, first_session: Session, second_session: Session, tmp_path: Path
    ):
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")

        refused = second_session.run("acquire", STACK_LOCK)
        marker.touch()
        collect_output(running)

        assert refused.returncode == BUSY_EXIT_CODE
        assert first_session.record(STACK_LOCK) is None
        assert second_session.run("acquire", STACK_LOCK).returncode == 0

    def test_run_records_its_own_process_as_the_holder(self, first_session: Session, tmp_path: Path):
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )

        record = wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")
        marker.touch()
        collect_output(running)

        assert record["holder_pid"] == running.pid
        assert record["hold_kind"] == "run"
        assert record["purpose"].startswith("run: sh -c")

    def test_run_refuses_a_busy_lock_without_running_the_command(
        self, first_session: Session, second_session: Session, tmp_path: Path
    ):
        first_session.run("acquire", STACK_LOCK)
        side_effect = tmp_path / "side-effect"

        refused = second_session.run("run", STACK_LOCK, "--", "touch", str(side_effect))

        assert refused.returncode == BUSY_EXIT_CODE
        assert not side_effect.exists()

    def test_run_with_wait_runs_the_command_once_the_lock_is_released(
        self, first_session: Session, second_session: Session, tmp_path: Path
    ):
        first_session.run("acquire", STACK_LOCK)
        side_effect = tmp_path / "side-effect"
        waiting = second_session.popen("run", STACK_LOCK, "--wait", LONG_WAIT_ARGUMENT, "--", "touch", str(side_effect))
        assert "waiting up to" in read_stderr_line(waiting)

        first_session.run("release", STACK_LOCK)

        assert collect_output(waiting).returncode == 0
        assert side_effect.exists()

    def test_run_reports_a_missing_command_with_exit_code_127(self, first_session: Session):
        result = first_session.run("run", STACK_LOCK, "--", "no-such-command-anywhere")

        assert result.returncode == 127
        assert "command not found" in result.output
        assert first_session.record(STACK_LOCK) is None

    def test_run_without_a_command_is_a_usage_error(self, first_session: Session):
        result = first_session.run("run", STACK_LOCK)

        assert result.returncode == 2
        assert "needs a command" in result.output

    def test_run_stops_the_command_and_frees_the_lock_when_the_owner_dies(
        self, first_session: Session, tmp_path: Path, owner_process
    ):
        command_pid_file = tmp_path / "command-pid"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", f"echo $$ > {command_pid_file}; exec sleep 600"
        )
        command_pid = read_pid_file(command_pid_file)

        owner_process.kill()
        owner_process.wait()

        wait_until(lambda: running.poll() is not None, "run to exit after its owner died")
        assert not process_is_running(command_pid)
        assert first_session.record(STACK_LOCK) is None

    def test_run_keeps_the_command_running_when_the_record_cannot_be_written(
        self, first_session: Session, fake_herdr: FakeHerdr, tmp_path: Path
    ):
        marker = tmp_path / "finish-marker"
        finished = tmp_path / "finished"
        command = f"{WAIT_FOR_MARKER_COMMAND.format(marker=marker)}; touch {finished}"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", command)
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")
        first_session.block_record_writes(STACK_LOCK)
        reads_before = fake_herdr.read_count(FIRST_PANE_ID)

        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_until(
            lambda: fake_herdr.read_count(FIRST_PANE_ID) >= reads_before + POLLS_TO_SURVIVE,
            "the run process to try and fail to rewrite its record",
        )
        marker.touch()

        assert collect_output(running).returncode == 0
        assert finished.exists()

    def test_run_does_not_stop_its_command_when_it_cannot_open_the_files_it_needs_to_check_on_its_owner(
        self, first_session: Session, tmp_path: Path
    ):
        marker = tmp_path / "finish-marker"
        finished = tmp_path / "finished"
        command = f"{WAIT_FOR_MARKER_COMMAND.format(marker=marker)}; touch {finished}"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", command)
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")

        with file_descriptors_exhausted(running.pid):
            time.sleep(SURVIVAL_WINDOW_SECONDS)
        marker.touch()

        result = collect_output(running)
        assert result.returncode == 0
        assert "stopping the command" not in result.stderr
        assert finished.exists()


class TestRunProcessGroup:
    def test_run_stops_the_grandchildren_of_a_shell_command_when_the_lock_is_released(
        self, first_session: Session, tmp_path: Path
    ):
        pid_file = tmp_path / "grandchild-pid"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", GRANDCHILD_COMMAND.format(pid_file=pid_file))
        grandchild_pid = read_pid_file(pid_file)

        released = first_session.run("release", STACK_LOCK)

        collect_output(running)
        assert released.returncode == 0
        assert not process_is_running(grandchild_pid)

    def test_run_stops_the_grandchildren_of_a_shell_command_when_the_lock_is_stolen_with_force(
        self, first_session: Session, second_session: Session, tmp_path: Path
    ):
        pid_file = tmp_path / "grandchild-pid"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", GRANDCHILD_COMMAND.format(pid_file=pid_file))
        grandchild_pid = read_pid_file(pid_file)

        stolen = second_session.run("steal", STACK_LOCK, "--force")

        collect_output(running)
        assert stolen.returncode == 0
        assert not process_is_running(grandchild_pid)

    def test_run_stops_the_grandchildren_of_a_shell_command_when_the_owner_dies(
        self, first_session: Session, tmp_path: Path, owner_process
    ):
        pid_file = tmp_path / "grandchild-pid"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", GRANDCHILD_COMMAND.format(pid_file=pid_file))
        grandchild_pid = read_pid_file(pid_file)

        owner_process.kill()
        owner_process.wait()

        wait_until(lambda: running.poll() is not None, "run to exit after its owner died")
        assert not process_is_running(grandchild_pid)

    def test_run_stops_what_the_command_left_running_in_the_background_when_it_ends(
        self, first_session: Session, tmp_path: Path
    ):
        pid_file = tmp_path / "leftover-pid"

        result = first_session.run("run", STACK_LOCK, "--", "sh", "-c", f"sleep 600 & echo $! > {pid_file}")

        assert result.returncode == 0
        assert not process_is_running(read_pid_file(pid_file))

    def test_run_kills_a_command_that_ignores_sigterm_after_the_grace_period(
        self, first_session: Session, tmp_path: Path
    ):
        pid_file = tmp_path / "grandchild-pid"
        command = SIGTERM_IGNORING_GRANDCHILD_COMMAND.format(pid_file=pid_file)
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", command)
        grandchild_pid = read_pid_file(pid_file)

        first_session.run("release", STACK_LOCK)

        collect_output(running)
        assert not process_is_running(grandchild_pid)


class TestRunInsideAcquiredLock:
    def test_run_inside_an_acquired_lock_runs_the_command_without_relocking(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        result = first_session.run("run", INTEGRATE_LOCK, "--", "sh", "-c", "exit 3")

        assert result.returncode == 3
        assert first_session.record(INTEGRATE_LOCK)["holder_pid"] == holder_pid
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_run_inside_an_acquired_lock_is_listed_as_a_running_command_until_it_ends(
        self, first_session: Session, tmp_path: Path
    ):
        first_session.run("acquire", STACK_LOCK)
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )
        wait_for_command_to_run_under(first_session, STACK_LOCK)

        activities_while_running = first_session.lock_report(STACK_LOCK)["activities"]
        marker.touch()
        collect_output(running)

        assert [activity["run_pid"] for activity in activities_while_running] == [running.pid]
        assert "sh -c" in activities_while_running[0]["command"]
        assert first_session.lock_report(STACK_LOCK)["activities"] == []

    def test_run_inside_an_acquired_lock_stops_the_grandchildren_when_the_lock_is_released(
        self, first_session: Session, tmp_path: Path
    ):
        first_session.run("acquire", STACK_LOCK)
        pid_file = tmp_path / "grandchild-pid"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", GRANDCHILD_COMMAND.format(pid_file=pid_file))
        grandchild_pid = read_pid_file(pid_file)

        released = first_session.run("release", STACK_LOCK)

        collect_output(running)
        assert released.returncode == 0
        assert not process_is_running(grandchild_pid)

    def test_run_inside_an_acquired_lock_stops_the_grandchildren_when_the_lock_is_stolen_with_force(
        self, first_session: Session, second_session: Session, tmp_path: Path
    ):
        first_session.run("acquire", STACK_LOCK)
        pid_file = tmp_path / "grandchild-pid"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", GRANDCHILD_COMMAND.format(pid_file=pid_file))
        grandchild_pid = read_pid_file(pid_file)

        stolen = second_session.run("steal", STACK_LOCK, "--force")

        collect_output(running)
        assert stolen.returncode == 0
        assert not process_is_running(grandchild_pid)

    def test_run_inside_an_acquired_lock_stops_the_command_and_exits_143_when_the_holder_is_killed(
        self, first_session: Session, tmp_path: Path
    ):
        first_session.run("acquire", STACK_LOCK)
        holder_pid = first_session.record(STACK_LOCK)["holder_pid"]
        pid_file = tmp_path / "grandchild-pid"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", GRANDCHILD_COMMAND.format(pid_file=pid_file))
        grandchild_pid = read_pid_file(pid_file)
        wait_for_command_to_run_under(first_session, STACK_LOCK)

        os.kill(holder_pid, signal.SIGKILL)

        result = collect_output(running)
        assert result.returncode == SIGTERM_EXIT_CODE
        assert "the acquired lock it ran inside ended" in result.stderr
        assert not process_is_running(grandchild_pid)

    def test_run_inside_an_acquired_lock_stops_the_grandchildren_when_the_owner_dies(
        self, first_session: Session, tmp_path: Path, owner_process
    ):
        first_session.run("acquire", STACK_LOCK)
        pid_file = tmp_path / "grandchild-pid"
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", GRANDCHILD_COMMAND.format(pid_file=pid_file))
        grandchild_pid = read_pid_file(pid_file)

        owner_process.kill()
        owner_process.wait()

        wait_until(lambda: running.poll() is not None, "run to exit after its owner died")
        assert not process_is_running(grandchild_pid)


class TestRunAndAcquireTogether:
    def test_run_inside_your_own_run_is_refused_instead_of_nesting(self, first_session: Session, tmp_path: Path):
        marker = tmp_path / "finish-marker"
        side_effect = tmp_path / "side-effect"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")

        refused = first_session.run("run", STACK_LOCK, "--", "touch", str(side_effect))
        marker.touch()
        collect_output(running)

        assert refused.returncode == BUSY_EXIT_CODE
        assert f"your own `run` (pid {running.pid}" in refused.output
        assert not side_effect.exists()

    def test_run_is_refused_while_another_sessions_run_holds_the_lock(
        self, first_session: Session, second_session: Session, tmp_path: Path
    ):
        marker = tmp_path / "finish-marker"
        side_effect = tmp_path / "side-effect"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")

        refused = second_session.run("run", STACK_LOCK, "--", "touch", str(side_effect))
        marker.touch()
        collect_output(running)

        assert refused.returncode == BUSY_EXIT_CODE
        assert f"run pid {running.pid}" in refused.output
        assert not side_effect.exists()

    def test_acquire_is_busy_while_your_own_run_holds_the_lock_and_names_the_run_process(
        self, first_session: Session, tmp_path: Path
    ):
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")

        refused = first_session.run("acquire", STACK_LOCK)
        marker.touch()
        collect_output(running)

        assert refused.returncode == BUSY_EXIT_CODE
        assert f"your own `run` (pid {running.pid}" in refused.output


class TestRunScope:
    def test_run_from_another_worktree_of_the_same_owner_does_not_slip_into_an_acquired_lock(
        self, first_session: Session, linked_worktree: Path, git_repository: Path, tmp_path: Path
    ):
        first_session.run("acquire", STACK_LOCK)
        side_effect = tmp_path / "side-effect"

        refused = first_session.run(
            "run", STACK_LOCK, "--", "touch", str(side_effect), working_directory=linked_worktree
        )

        assert refused.returncode == BUSY_EXIT_CODE
        assert not side_effect.exists()
        assert f"worktree {git_repository}" in refused.output
        assert first_session.lock_report(STACK_LOCK)["activities"] == []

    def test_run_from_another_worktree_of_the_same_owner_waits_for_the_acquired_lock_to_be_released(
        self, first_session: Session, linked_worktree: Path, tmp_path: Path
    ):
        first_session.run("acquire", STACK_LOCK)
        side_effect = tmp_path / "side-effect"
        waiting = first_session.popen(
            "run",
            STACK_LOCK,
            "--wait",
            LONG_WAIT_ARGUMENT,
            "--",
            "touch",
            str(side_effect),
            working_directory=linked_worktree,
        )
        assert "waiting up to" in read_stderr_line(waiting)

        first_session.run("release", STACK_LOCK)

        assert collect_output(waiting).returncode == 0
        assert side_effect.exists()

    def test_run_from_a_subdirectory_of_the_acquiring_worktree_runs_inside_the_acquired_lock(
        self, first_session: Session, git_repository: Path
    ):
        first_session.run("acquire", STACK_LOCK)
        holder_pid = first_session.record(STACK_LOCK)["holder_pid"]
        subdirectory = git_repository / "nested"
        subdirectory.mkdir()

        result = first_session.run("run", STACK_LOCK, "--", "sh", "-c", "exit 4", working_directory=subdirectory)

        assert result.returncode == 4
        assert first_session.record(STACK_LOCK)["holder_pid"] == holder_pid

    def test_run_records_the_worktree_it_runs_from_as_the_scope_of_its_hold(
        self, first_session: Session, linked_worktree: Path, tmp_path: Path
    ):
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run",
            STACK_LOCK,
            "--",
            "sh",
            "-c",
            WAIT_FOR_MARKER_COMMAND.format(marker=marker),
            working_directory=linked_worktree,
        )

        record = wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")
        marker.touch()
        collect_output(running)

        assert record["scope"] == str(linked_worktree)
