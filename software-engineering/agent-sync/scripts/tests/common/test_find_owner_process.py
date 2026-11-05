import os

import agent_sync_common
import pytest
from agent_sync_common import EnvironmentProblem, find_owner_process


class TestFindOwnerProcess:
    def test_find_owner_process_fails_when_no_ancestor_has_the_owner_process_name(self, monkeypatch):
        monkeypatch.delenv(agent_sync_common.OWNER_PID_ENVIRONMENT_VARIABLE, raising=False)
        monkeypatch.setattr(agent_sync_common, "OWNER_PROCESS_NAME", "no-such-process-name")

        with pytest.raises(EnvironmentProblem, match="no `no-such-process-name` process"):
            find_owner_process()

    def test_find_owner_process_prefers_the_override_over_the_ancestry(self, monkeypatch):
        monkeypatch.setenv(agent_sync_common.OWNER_PID_ENVIRONMENT_VARIABLE, str(os.getpid()))

        assert find_owner_process().pid == os.getpid()

    def test_find_owner_process_rejects_an_override_that_is_not_a_process_id(self, monkeypatch):
        monkeypatch.setenv(agent_sync_common.OWNER_PID_ENVIRONMENT_VARIABLE, "not-a-pid")

        with pytest.raises(EnvironmentProblem, match="must be a process id"):
            find_owner_process()
