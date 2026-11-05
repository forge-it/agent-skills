import subprocess

import pytest
from agent_sync_common import (
    ProcessIdentity,
    find_process_group_members,
    is_same_process_alive,
    read_process_stat,
    terminate_process,
    terminate_process_group,
)

from tests.utils.constants import SAMPLE_OWNER_PID, SAMPLE_START_TICKS
from tests.utils.helpers import process_is_running, read_start_ticks, wait_until


class TestReadProcessStat:
    def test_read_process_stat_returns_nothing_for_a_process_that_is_gone(self, procfs_without_processes):
        assert read_process_stat(SAMPLE_OWNER_PID) is None

    def test_read_process_stat_raises_when_the_entry_exists_but_cannot_be_read(
        self, procfs_where_a_stat_cannot_be_read
    ):
        with pytest.raises(OSError):
            read_process_stat(SAMPLE_OWNER_PID)

    def test_read_process_stat_reads_a_process_whose_name_is_not_utf8(
        self, procfs_with_a_process_named_in_invalid_utf8
    ):
        stat = read_process_stat(SAMPLE_OWNER_PID)

        assert stat
        assert stat.start_ticks == SAMPLE_START_TICKS


class TestIsSameProcessAlive:
    def test_is_same_process_alive_is_false_for_a_process_that_is_gone(self, procfs_without_processes):
        assert not is_same_process_alive(ProcessIdentity(SAMPLE_OWNER_PID, SAMPLE_START_TICKS))

    def test_is_same_process_alive_is_true_when_the_entry_cannot_be_read(self, procfs_where_a_stat_cannot_be_read):
        assert is_same_process_alive(ProcessIdentity(SAMPLE_OWNER_PID, SAMPLE_START_TICKS))

    def test_is_same_process_alive_is_false_for_a_pid_reused_by_a_process_whose_name_is_not_utf8(
        self, procfs_with_a_process_named_in_invalid_utf8
    ):
        assert not is_same_process_alive(ProcessIdentity(SAMPLE_OWNER_PID, SAMPLE_START_TICKS + 1))

    def test_is_same_process_alive_is_true_for_the_pid_with_its_own_start_ticks(self, sleeping_process):
        identity = ProcessIdentity(sleeping_process.pid, read_start_ticks(sleeping_process.pid))

        assert is_same_process_alive(identity)

    def test_is_same_process_alive_is_false_when_the_pid_was_reused_by_a_process_started_later(self, sleeping_process):
        reused_pid = ProcessIdentity(sleeping_process.pid, read_start_ticks(sleeping_process.pid) + 1)

        assert not is_same_process_alive(reused_pid)


class TestTerminateProcess:
    def test_terminate_process_leaves_a_process_alone_whose_pid_was_reused(self, sleeping_process):
        reused_pid = ProcessIdentity(sleeping_process.pid, read_start_ticks(sleeping_process.pid) + 1)

        assert terminate_process(reused_pid)

        assert process_is_running(sleeping_process.pid)

    def test_terminate_process_stops_the_process_it_was_given(self, sleeping_process: subprocess.Popen[bytes]):
        identity = ProcessIdentity(sleeping_process.pid, read_start_ticks(sleeping_process.pid))

        assert terminate_process(identity)

        sleeping_process.wait()
        assert not process_is_running(sleeping_process.pid)


class TestTerminateProcessGroup:
    def test_terminate_process_group_stops_the_grandchildren_of_a_shell_too(self, shell_with_a_grandchild):
        shell, grandchild_pid = shell_with_a_grandchild

        assert terminate_process_group(shell.pid)

        wait_until(lambda: not process_is_running(grandchild_pid), "the grandchild to be stopped")
        assert find_process_group_members(shell.pid) == []

    def test_terminate_process_group_never_signals_the_unknown_group_id_zero(self):
        assert terminate_process_group(0)
