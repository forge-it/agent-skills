import os
import sys
import time
from pathlib import Path

from tests.utils.constants import (
    FIRST_PANE_ID,
    INTEGRATE_LOCK,
    LOCKCTL_SCRIPT,
    POLLS_TO_SURVIVE,
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
    start_holder_whose_acquirer_is_gone,
    wait_for_recorded_herdr_status,
    wait_until,
)
from tests.utils.samples import DEEPLY_NESTED_HERDR_REPLY, NOT_TEXT_HERDR_REPLY


class TestHolderLifetime:
    def test_holder_keeps_running_after_the_acquire_command_exits(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK, timeout=15)

        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        assert process_is_running(holder_pid)
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_holder_runs_in_its_own_session_without_inherited_output(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)

        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        assert os.getsid(holder_pid) == holder_pid
        assert Path(f"/proc/{holder_pid}/fd/1").resolve() == Path(os.devnull)
        assert Path(f"/proc/{holder_pid}/fd/2").resolve() == Path(os.devnull)

    def test_lock_is_freed_when_the_owner_process_dies(
        self, first_session: Session, second_session: Session, owner_process
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        owner_process.kill()
        owner_process.wait()

        wait_until(lambda: not process_is_running(holder_pid), "the holder to exit after its owner died")
        assert second_session.run("acquire", INTEGRATE_LOCK).returncode == 0

    def test_owner_death_is_logged_as_an_expire_event(self, first_session: Session, owner_process):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        owner_process.kill()
        owner_process.wait()

        wait_until(lambda: not process_is_running(holder_pid), "the holder to exit after its owner died")
        assert f"expire lock={INTEGRATE_LOCK}" in first_session.events()
        assert first_session.record(INTEGRATE_LOCK) is None


class TestHolderStamp:
    def test_holder_writes_its_own_and_its_owners_identity_into_the_lock_file(
        self, first_session: Session, owner_process, git_repository: Path
    ):
        first_session.run("acquire", INTEGRATE_LOCK)

        stamp = first_session.stamp(INTEGRATE_LOCK)

        assert stamp["holder_pid"] == first_session.record(INTEGRATE_LOCK)["holder_pid"]
        assert stamp["owner_pid"] == owner_process.pid
        assert stamp["scope"] == str(git_repository)
        assert stamp["hold_kind"] == "acquire"

    def test_holder_empties_the_lock_file_when_it_lets_go_but_never_deletes_it(self, first_session: Session):
        first_session.run("acquire", INTEGRATE_LOCK)

        first_session.run("release", INTEGRATE_LOCK)

        assert (first_session.state_directory / f"{INTEGRATE_LOCK}.lock").read_text() == ""

    def test_run_writes_its_own_identity_into_the_lock_file_while_its_command_runs(
        self, first_session: Session, tmp_path: Path
    ):
        marker = tmp_path / "finish-marker"
        running = first_session.popen(
            "run", STACK_LOCK, "--", "sh", "-c", WAIT_FOR_MARKER_COMMAND.format(marker=marker)
        )
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")

        stamp = first_session.stamp(STACK_LOCK)
        marker.touch()
        collect_output(running)

        assert stamp["holder_pid"] == running.pid
        assert stamp["hold_kind"] == "run"


class TestOwnerDetection:
    def test_owner_is_the_nearest_ancestor_named_claude_even_through_an_intermediate_process(
        self, first_session: Session, claude_named_shell: Path
    ):
        script = f"sh -c '{sys.executable} {LOCKCTL_SCRIPT} acquire {INTEGRATE_LOCK}; echo inner'; echo outer"
        shell = first_session.spawn(str(claude_named_shell), "-c", script, environment={"AGENT_SYNC_OWNER_PID": None})

        output = collect_output(shell).stdout

        assert f"owner pid {shell.pid}" in output


class TestHolderStartup:
    def test_holder_frees_the_lock_when_its_acquirer_is_gone_before_it_is_ready(self, first_session: Session):
        holder = start_holder_whose_acquirer_is_gone(first_session, INTEGRATE_LOCK)

        assert collect_output(holder).returncode == 0
        assert first_session.record(INTEGRATE_LOCK) is None
        assert f"release lock={INTEGRATE_LOCK}" in first_session.events()
        assert first_session.run("acquire", INTEGRATE_LOCK).returncode == 0


class TestHolderResilience:
    def test_holder_keeps_holding_when_its_record_cannot_be_written(
        self, first_session: Session, fake_herdr: FakeHerdr
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        first_session.block_record_writes(INTEGRATE_LOCK)
        reads_before = fake_herdr.read_count(FIRST_PANE_ID)

        fake_herdr.set_status(FIRST_PANE_ID, "idle")
        wait_until(
            lambda: fake_herdr.read_count(FIRST_PANE_ID) >= reads_before + POLLS_TO_SURVIVE,
            "the holder to try and fail to rewrite its record",
        )
        first_session.unblock_record_writes(INTEGRATE_LOCK)

        record = wait_for_recorded_herdr_status(first_session, INTEGRATE_LOCK, "idle")
        assert record["holder_pid"] == holder_pid
        assert process_is_running(holder_pid)
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_holder_keeps_holding_when_it_cannot_open_the_files_it_needs_to_check_on_its_owner(
        self, first_session: Session
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]

        with file_descriptors_exhausted(holder_pid):
            time.sleep(SURVIVAL_WINDOW_SECONDS)
            holder_survived = process_is_running(holder_pid)

        assert holder_survived
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_holder_keeps_holding_when_herdr_answers_with_bytes_that_are_not_text(
        self, first_session: Session, fake_herdr: FakeHerdr
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        reads_before = fake_herdr.read_count(FIRST_PANE_ID)

        fake_herdr.reply_with(NOT_TEXT_HERDR_REPLY)

        wait_until(
            lambda: fake_herdr.read_count(FIRST_PANE_ID) >= reads_before + POLLS_TO_SURVIVE,
            "the holder to go on reading herdr after an answer that is not text",
        )
        assert process_is_running(holder_pid)
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0

    def test_holder_keeps_holding_when_reading_herdr_fails_in_a_way_nobody_anticipated(
        self, first_session: Session, fake_herdr: FakeHerdr
    ):
        first_session.run("acquire", INTEGRATE_LOCK)
        holder_pid = first_session.record(INTEGRATE_LOCK)["holder_pid"]
        reads_before = fake_herdr.read_count(FIRST_PANE_ID)

        fake_herdr.reply_with(DEEPLY_NESTED_HERDR_REPLY)

        wait_until(
            lambda: fake_herdr.read_count(FIRST_PANE_ID) >= reads_before + POLLS_TO_SURVIVE,
            "the holder to go on reading herdr after an answer that cannot be parsed",
        )
        assert process_is_running(holder_pid)
        assert first_session.run("check", INTEGRATE_LOCK).returncode == 0
