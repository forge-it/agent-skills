import os
import shlex
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import agent_sync_common
import pytest
from agent_sync_common import (
    OWNER_PID_ENVIRONMENT_VARIABLE,
    OWNER_PROCESS_NAME,
    ZOMBIE_STATE,
    EnvironmentProblem,
    ProcessGroupIdentity,
    ProcessIdentity,
    ProcessStat,
    find_group_members_of,
    find_owner_process,
    find_process_group_members,
    has_libproc_owner_name,
    is_same_process_alive,
    read_process_stat,
)
from process_table_darwin import MICROSECONDS_PER_SECOND, parse_launch_names

from tests.utils.builders import BASH_BINARY
from tests.utils.constants import SCRIPTS_DIRECTORY
from tests.utils.helpers import process_is_running, read_pid_file, wait_until

ON_MACOS_ONLY = pytest.mark.skipif(sys.platform != "darwin", reason="reads the process table through libproc")
LAUNCHD_PID = 1
START_TIME_TOLERANCE_SECONDS = 60
ARGUMENT_COUNT_BYTES = 4
PATH_TERMINATOR_AND_PADDING = b"\0\0\0\0"
PRINT_OWNER_PID = "from agent_sync_common import find_owner_process; print(find_owner_process().pid)"


def build_launch_arguments(executed_path: str, arguments: list[str], environment: list[str]) -> bytes:
    """KERN_PROCARGS2 as the kernel lays it out: argc, the path executed, NUL padding, argv, environment."""
    argument_count = len(arguments).to_bytes(ARGUMENT_COUNT_BYTES, sys.byteorder)
    saved_strings = b"".join(entry.encode() + b"\0" for entry in [*arguments, *environment])
    return argument_count + executed_path.encode() + PATH_TERMINATOR_AND_PADDING + saved_strings


def process_is_zombie(pid: int) -> bool:
    stat = read_process_stat(pid)
    return bool(stat) and stat.state == ZOMBIE_STATE


@pytest.fixture
def reaped_process() -> subprocess.Popen[bytes]:
    """A process that has exited and been waited for, so its pid names nothing."""
    process = subprocess.Popen(["true"], process_group=0)
    process.wait()
    return process


@pytest.fixture
def zombie_child() -> Iterator[subprocess.Popen[bytes]]:
    """A child that exited and that nobody waits for, so it stays a zombie until the fixture reaps it."""
    child = subprocess.Popen(["true"], process_group=0)
    wait_until(lambda: process_is_zombie(child.pid), "the child to exit and wait to be reaped")
    yield child
    child.wait()


@pytest.fixture
def zombie_leader_of_a_live_group(tmp_path: Path) -> Iterator[tuple[subprocess.Popen[bytes], int]]:
    """A process group whose leader exited unreaped while its background child still runs."""
    pid_file = tmp_path / "survivor-pid"
    leader = subprocess.Popen(["sh", "-c", f"sleep 600 & echo $! > {pid_file}"], process_group=0)
    survivor_pid = read_pid_file(pid_file)
    wait_until(lambda: process_is_zombie(leader.pid), "the group leader to exit and wait to be reaped")
    yield leader, survivor_pid
    os.kill(survivor_pid, signal.SIGKILL)
    leader.wait()


@pytest.fixture
def claude_symlink_process(claude_named_shell: Path) -> Iterator[subprocess.Popen[bytes]]:
    """A shell started through a symlink named `claude`, which the kernel names after the symlink's target."""
    process = subprocess.Popen([str(claude_named_shell), "-c", "sleep 600; true"])
    yield process
    process.kill()
    process.wait()


class TestParseLaunchNames:
    def test_parse_launch_names_returns_the_basenames_of_the_executed_path_and_of_argv_zero(self):
        launch_arguments = build_launch_arguments(
            "/Users/someone/.local/bin/claude", ["claude", "--resume"], ["HOME=/Users/someone"]
        )

        assert parse_launch_names(launch_arguments) == ("claude", "claude")

    def test_parse_launch_names_keeps_the_name_the_process_was_started_under_apart_from_the_target(self):
        launch_arguments = build_launch_arguments("/opt/claude/versions/2.1.316", ["claude"], [])

        assert parse_launch_names(launch_arguments) == ("2.1.316", "claude")

    def test_parse_launch_names_does_not_read_the_environment_as_arguments(self):
        launch_arguments = build_launch_arguments("/bin/zsh", ["-zsh"], ["_=/usr/local/bin/claude"])

        assert parse_launch_names(launch_arguments) == ("zsh", "-zsh")

    def test_parse_launch_names_has_no_argv_zero_when_the_process_has_no_arguments(self):
        launch_arguments = build_launch_arguments("/bin/zsh", [], ["_=/usr/local/bin/claude"])

        assert parse_launch_names(launch_arguments) == ("zsh",)

    def test_parse_launch_names_is_empty_for_an_empty_answer(self):
        assert parse_launch_names(b"") == ()


@ON_MACOS_ONLY
class TestLibprocProcessFacts:
    def test_read_process_stat_reports_the_parent_group_name_and_start_time_of_a_live_process(
        self, sleeping_process: subprocess.Popen[bytes]
    ):
        stat = read_process_stat(sleeping_process.pid)

        assert stat
        assert stat.name == "sleep"
        assert stat.state != ZOMBIE_STATE
        assert stat.parent_pid == os.getpid()
        assert stat.process_group_id == os.getpgid(sleeping_process.pid)
        started_seconds_ago = time.time() - stat.start_ticks / MICROSECONDS_PER_SECOND
        assert 0 <= started_seconds_ago < START_TIME_TOLERANCE_SECONDS

    def test_is_same_process_alive_is_true_for_the_identity_libproc_reported(
        self, sleeping_process: subprocess.Popen[bytes]
    ):
        stat = read_process_stat(sleeping_process.pid)

        assert is_same_process_alive(ProcessIdentity(sleeping_process.pid, stat.start_ticks))

    def test_is_same_process_alive_is_false_for_a_pid_reused_a_microsecond_later(
        self, sleeping_process: subprocess.Popen[bytes]
    ):
        stat = read_process_stat(sleeping_process.pid)

        assert not is_same_process_alive(ProcessIdentity(sleeping_process.pid, stat.start_ticks + 1))

    def test_read_process_stat_returns_nothing_for_a_pid_that_is_gone(self, reaped_process: subprocess.Popen[bytes]):
        assert read_process_stat(reaped_process.pid) is None

    def test_is_same_process_alive_is_false_once_the_process_is_reaped(self, sleeping_process: subprocess.Popen[bytes]):
        identity = ProcessIdentity(sleeping_process.pid, read_process_stat(sleeping_process.pid).start_ticks)

        sleeping_process.kill()
        sleeping_process.wait()

        assert not is_same_process_alive(identity)

    def test_read_process_stat_does_not_wrap_a_pid_beyond_32_bits_onto_a_live_process(self):
        assert read_process_stat(os.getpid() + 2**32) is None

    def test_read_process_stat_raises_for_a_process_of_another_user(self):
        if os.geteuid() == 0:
            pytest.skip("root may inspect every process")

        with pytest.raises(PermissionError):
            read_process_stat(LAUNCHD_PID)

    def test_is_same_process_alive_is_true_for_a_process_of_another_user(self):
        if os.geteuid() == 0:
            pytest.skip("root may inspect every process")

        assert is_same_process_alive(ProcessIdentity(LAUNCHD_PID, 1))


@ON_MACOS_ONLY
class TestLibprocZombies:
    def test_read_process_stat_reports_an_unreaped_child_as_a_zombie(self, zombie_child: subprocess.Popen[bytes]):
        stat = read_process_stat(zombie_child.pid)

        assert stat
        assert stat.state == ZOMBIE_STATE
        assert stat.parent_pid == os.getpid()

    def test_is_same_process_alive_is_false_for_an_unreaped_child_with_its_own_start_time(
        self, zombie_child: subprocess.Popen[bytes]
    ):
        identity = ProcessIdentity(zombie_child.pid, read_process_stat(zombie_child.pid).start_ticks)

        assert not is_same_process_alive(identity)
        assert not process_is_running(zombie_child.pid)

    def test_find_process_group_members_leaves_out_a_zombie(self, zombie_child: subprocess.Popen[bytes]):
        assert find_process_group_members(zombie_child.pid) == []

    def test_find_process_group_members_lists_the_live_members_of_a_group_whose_leader_is_a_zombie(
        self, zombie_leader_of_a_live_group
    ):
        leader, survivor_pid = zombie_leader_of_a_live_group

        assert find_process_group_members(leader.pid) == [survivor_pid]


@ON_MACOS_ONLY
class TestLibprocProcessGroups:
    def test_find_process_group_members_lists_a_shell_and_its_grandchild(self, shell_with_a_grandchild):
        shell, grandchild_pid = shell_with_a_grandchild

        assert sorted(find_process_group_members(shell.pid)) == sorted([shell.pid, grandchild_pid])

    def test_find_process_group_members_is_empty_for_a_group_that_is_gone(
        self, reaped_process: subprocess.Popen[bytes]
    ):
        assert find_process_group_members(reaped_process.pid) == []

    def test_find_group_members_of_lists_the_group_whose_leader_has_the_recorded_start_time(
        self, shell_with_a_grandchild
    ):
        shell, grandchild_pid = shell_with_a_grandchild
        group = ProcessGroupIdentity(shell.pid, read_process_stat(shell.pid).start_ticks)

        assert sorted(find_group_members_of(group)) == sorted([shell.pid, grandchild_pid])

    def test_find_group_members_of_is_empty_when_the_group_id_now_belongs_to_a_process_started_later(
        self, shell_with_a_grandchild
    ):
        shell, _ = shell_with_a_grandchild
        reused_group = ProcessGroupIdentity(shell.pid, read_process_stat(shell.pid).start_ticks + 1)

        assert find_group_members_of(reused_group) == []


@ON_MACOS_ONLY
class TestLibprocOwnerDetection:
    def test_the_kernel_names_a_symlink_named_claude_after_its_target(
        self, claude_symlink_process: subprocess.Popen[bytes]
    ):
        stat = read_process_stat(claude_symlink_process.pid)

        assert stat
        assert stat.name == BASH_BINARY.name
        assert stat.name != OWNER_PROCESS_NAME

    def test_has_libproc_owner_name_matches_a_process_started_through_a_symlink_named_claude(
        self, claude_symlink_process: subprocess.Popen[bytes]
    ):
        stat = read_process_stat(claude_symlink_process.pid)

        assert has_libproc_owner_name(claude_symlink_process.pid, stat)

    def test_has_libproc_owner_name_does_not_match_a_process_with_another_name(
        self, sleeping_process: subprocess.Popen[bytes]
    ):
        stat = read_process_stat(sleeping_process.pid)

        assert not has_libproc_owner_name(sleeping_process.pid, stat)

    def test_has_libproc_owner_name_does_not_match_a_process_whose_launch_arguments_cannot_be_read(self):
        stat = ProcessStat("launchd", "S", 0, LAUNCHD_PID, 1)

        assert not has_libproc_owner_name(LAUNCHD_PID, stat)

    def test_find_owner_process_finds_a_symlink_named_claude_through_an_intermediate_process(
        self, claude_named_shell: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv(OWNER_PID_ENVIRONMENT_VARIABLE, raising=False)
        inner_command = f"{shlex.quote(sys.executable)} -c {shlex.quote(PRINT_OWNER_PID)}; echo inner"
        script = f"sh -c {shlex.quote(inner_command)}; echo outer"

        shell = subprocess.Popen(
            [str(claude_named_shell), "-c", script],
            stdout=subprocess.PIPE,
            text=True,
            cwd=SCRIPTS_DIRECTORY,
        )
        output, _ = shell.communicate(timeout=30)

        assert output.split() == [str(shell.pid), "inner", "outer"]

    def test_find_owner_process_names_a_live_override_process(
        self, sleeping_process: subprocess.Popen[bytes], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv(OWNER_PID_ENVIRONMENT_VARIABLE, str(sleeping_process.pid))

        owner = find_owner_process()

        assert owner == ProcessIdentity(sleeping_process.pid, read_process_stat(sleeping_process.pid).start_ticks)

    def test_find_owner_process_rejects_an_override_that_is_gone(
        self, reaped_process: subprocess.Popen[bytes], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv(OWNER_PID_ENVIRONMENT_VARIABLE, str(reaped_process.pid))

        with pytest.raises(EnvironmentProblem, match="is not a running process"):
            find_owner_process()

    def test_find_owner_process_rejects_an_override_that_is_a_zombie(
        self, zombie_child: subprocess.Popen[bytes], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv(OWNER_PID_ENVIRONMENT_VARIABLE, str(zombie_child.pid))

        with pytest.raises(EnvironmentProblem, match="is not a running process"):
            find_owner_process()

    def test_find_owner_process_rejects_an_override_that_belongs_to_another_user(self, monkeypatch: pytest.MonkeyPatch):
        if os.geteuid() == 0:
            pytest.skip("root may inspect every process")
        monkeypatch.setenv(OWNER_PID_ENVIRONMENT_VARIABLE, str(LAUNCHD_PID))

        with pytest.raises(EnvironmentProblem, match="another user"):
            find_owner_process()


@ON_MACOS_ONLY
def test_the_backend_selected_on_macos_is_libproc():
    assert agent_sync_common.PROCESS_BACKEND is agent_sync_common.LIBPROC_BACKEND
