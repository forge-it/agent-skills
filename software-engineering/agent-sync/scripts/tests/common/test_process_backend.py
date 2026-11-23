import errno
import os

import agent_sync_common
import pytest
from agent_sync_common import (
    LIBPROC_BACKEND,
    OWNER_PID_ENVIRONMENT_VARIABLE,
    PROCFS_BACKEND,
    EnvironmentProblem,
    ProcessBackend,
    ProcessStat,
    find_owner_process,
    read_own_identity,
    select_process_backend,
)

from tests.utils.constants import SAMPLE_OWNER_PID, SAMPLE_START_TICKS

SUPPORTED_PLATFORMS_PATTERN = r"Linux \(procfs\) and macOS \(libproc\)"


def build_backend(read_stat) -> ProcessBackend:
    return ProcessBackend(read_stat, lambda group_id: [], lambda pid, stat: False)


def read_stat_of_a_command_whose_parent_belongs_to_another_user(pid: int) -> ProcessStat:
    if pid == os.getpid():
        return ProcessStat("python", "S", SAMPLE_OWNER_PID, SAMPLE_OWNER_PID, SAMPLE_START_TICKS)
    raise PermissionError(errno.EPERM, "Operation not permitted")


def read_stat_of_an_absent_process(pid: int) -> None:
    return None


class TestSelectProcessBackend:
    def test_select_process_backend_reads_procfs_on_linux(self):
        assert select_process_backend("linux") is PROCFS_BACKEND

    def test_select_process_backend_reads_libproc_on_macos(self):
        assert select_process_backend("darwin") is LIBPROC_BACKEND

    @pytest.mark.parametrize("platform_name", ["win32", "freebsd14", "cygwin"])
    def test_select_process_backend_refuses_every_other_platform_naming_the_supported_ones(self, platform_name: str):
        backend = select_process_backend(platform_name)

        with pytest.raises(EnvironmentProblem, match=f"{SUPPORTED_PLATFORMS_PATTERN}, not '{platform_name}'"):
            backend.read_stat(SAMPLE_OWNER_PID)
        with pytest.raises(EnvironmentProblem, match=SUPPORTED_PLATFORMS_PATTERN):
            backend.find_group_members(SAMPLE_OWNER_PID)

    def test_read_own_identity_names_both_supported_platforms_when_the_process_table_has_no_entry(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(agent_sync_common, "PROCESS_BACKEND", build_backend(read_stat_of_an_absent_process))

        with pytest.raises(EnvironmentProblem, match=SUPPORTED_PLATFORMS_PATTERN):
            read_own_identity()


class TestFindOwnerProcessInTheFaceOfAnUninspectableProcess:
    def test_find_owner_process_ends_the_walk_at_an_ancestor_that_cannot_be_inspected(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv(OWNER_PID_ENVIRONMENT_VARIABLE, raising=False)
        backend = build_backend(read_stat_of_a_command_whose_parent_belongs_to_another_user)
        monkeypatch.setattr(agent_sync_common, "PROCESS_BACKEND", backend)

        with pytest.raises(EnvironmentProblem, match="no `claude` process among the ancestors"):
            find_owner_process()

    def test_find_owner_process_rejects_an_override_that_cannot_be_inspected(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(OWNER_PID_ENVIRONMENT_VARIABLE, str(SAMPLE_OWNER_PID))
        backend = build_backend(read_stat_of_a_command_whose_parent_belongs_to_another_user)
        monkeypatch.setattr(agent_sync_common, "PROCESS_BACKEND", backend)

        with pytest.raises(EnvironmentProblem, match="another user"):
            find_owner_process()
