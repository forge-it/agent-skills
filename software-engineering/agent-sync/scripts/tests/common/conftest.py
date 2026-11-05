import subprocess
from collections.abc import Iterator
from pathlib import Path

import agent_sync_common
import pytest

from tests.utils.builders import write_stat_of_a_process_named_in_invalid_utf8
from tests.utils.constants import SAMPLE_OWNER_PID, SAMPLE_START_TICKS
from tests.utils.helpers import read_pid_file


@pytest.fixture
def sleeping_process() -> Iterator[subprocess.Popen[bytes]]:
    process = subprocess.Popen(["sleep", "600"])
    yield process
    process.kill()
    process.wait()


@pytest.fixture
def shell_with_a_grandchild(tmp_path: Path) -> Iterator[tuple[subprocess.Popen[bytes], int]]:
    """A shell in its own process group whose `sleep` is a background child of the shell."""
    pid_file = tmp_path / "grandchild-pid"
    shell = subprocess.Popen(["sh", "-c", f"sleep 600 & echo $! > {pid_file}; wait"], process_group=0)
    yield shell, read_pid_file(pid_file)
    shell.kill()
    shell.wait()


@pytest.fixture
def procfs_without_processes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    process_directory = tmp_path / "empty-proc"
    process_directory.mkdir()
    monkeypatch.setattr(agent_sync_common, "PROCESS_DIRECTORY", process_directory)


@pytest.fixture
def procfs_where_a_stat_cannot_be_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The stat of SAMPLE_OWNER_PID exists, yet reading it fails with an error that is not "no such
    file": it is a directory."""
    process_directory = tmp_path / "unreadable-proc"
    (process_directory / str(SAMPLE_OWNER_PID) / "stat").mkdir(parents=True)
    monkeypatch.setattr(agent_sync_common, "PROCESS_DIRECTORY", process_directory)


@pytest.fixture
def procfs_with_a_process_named_in_invalid_utf8(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    process_directory = tmp_path / "odd-names-proc"
    write_stat_of_a_process_named_in_invalid_utf8(process_directory, SAMPLE_OWNER_PID, SAMPLE_START_TICKS)
    monkeypatch.setattr(agent_sync_common, "PROCESS_DIRECTORY", process_directory)
