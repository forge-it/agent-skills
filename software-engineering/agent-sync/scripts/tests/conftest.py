import os
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tests.utils.builders import (
    add_linked_worktree,
    add_worktree_of_bare_repository,
    build_bare_repository,
    build_claude_named_shell,
    build_git_repository,
)
from tests.utils.constants import (
    FIRST_PANE_ID,
    INTEGRATE_LOCK,
    LOCKCTL_SCRIPT,
    NAG_SCRIPT,
    NO_IDLE_REQUIRED,
    SECOND_PANE_ID,
    TEST_TIMEOUT_SECONDS,
)
from tests.utils.helpers import FakeHerdr, GitSpy, LockPoacher, Session, wait_for_idle_observation


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "timeout(seconds): fail a test that runs longer (pytest-timeout)")


def pytest_collection_modifyitems(items: list[pytest.Item]):
    """No test may hang the suite: every test without its own limit gets the default one."""
    for item in items:
        if not item.get_closest_marker("timeout"):
            item.add_marker(pytest.mark.timeout(TEST_TIMEOUT_SECONDS))


def start_owner_process() -> subprocess.Popen[bytes]:
    return subprocess.Popen(["sleep", "600"])


@pytest.fixture
def owner_process() -> Iterator[subprocess.Popen[bytes]]:
    process = start_owner_process()
    yield process
    process.kill()
    process.wait()


@pytest.fixture
def second_owner_process() -> Iterator[subprocess.Popen[bytes]]:
    process = start_owner_process()
    yield process
    process.kill()
    process.wait()


@pytest.fixture
def fake_herdr(tmp_path: Path) -> FakeHerdr:
    herdr = FakeHerdr(tmp_path / "fake-herdr")
    herdr.set_status(FIRST_PANE_ID, "working")
    herdr.set_status(SECOND_PANE_ID, "working")
    return herdr


@pytest.fixture(autouse=True)
def only_the_fake_herdr_is_reachable(fake_herdr: FakeHerdr, monkeypatch: pytest.MonkeyPatch):
    """Whatever a test runs, in this process or a child, finds the fake herdr first."""
    monkeypatch.setenv("PATH", os.pathsep.join([str(fake_herdr.binary.parent), os.environ["PATH"]]))
    monkeypatch.setenv("HERDR_BIN_PATH", str(fake_herdr.binary))
    monkeypatch.setenv("AGENT_SYNC_HERDR", str(fake_herdr.binary))
    monkeypatch.delenv("HERDR_SESSION", raising=False)


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    return build_git_repository(tmp_path / "repository")


@pytest.fixture
def linked_worktree(git_repository: Path) -> Path:
    return add_linked_worktree(git_repository, "linked-worktree")


@pytest.fixture
def bare_repository(git_repository: Path, tmp_path: Path) -> Path:
    return build_bare_repository(git_repository, tmp_path / "bare-repository.git")


@pytest.fixture
def bare_repository_worktree(bare_repository: Path, tmp_path: Path) -> Path:
    return add_worktree_of_bare_repository(bare_repository, tmp_path / "bare-repository-worktree")


@pytest.fixture
def git_spy(tmp_path: Path) -> GitSpy:
    return GitSpy(tmp_path / "git-spy")


@pytest.fixture
def plain_directory(tmp_path: Path) -> Path:
    directory = tmp_path / "not-a-repository"
    directory.mkdir()
    return directory


@pytest.fixture
def claude_named_shell(tmp_path: Path) -> Path:
    return build_claude_named_shell(tmp_path / "fake-claude")


@pytest.fixture
def first_session(
    git_repository: Path, owner_process: subprocess.Popen[bytes], fake_herdr: FakeHerdr, tmp_path: Path
) -> Session:
    return Session(
        script=LOCKCTL_SCRIPT,
        repository=git_repository,
        owner_pid=owner_process.pid,
        pane_id=FIRST_PANE_ID,
        herdr=fake_herdr,
        state_home=tmp_path / "state-1",
    )


@pytest.fixture
def second_session(
    git_repository: Path, second_owner_process: subprocess.Popen[bytes], fake_herdr: FakeHerdr, tmp_path: Path
) -> Session:
    return Session(
        script=LOCKCTL_SCRIPT,
        repository=git_repository,
        owner_pid=second_owner_process.pid,
        pane_id=SECOND_PANE_ID,
        herdr=fake_herdr,
        state_home=tmp_path / "state-2",
    )


@pytest.fixture
def nag_session(
    git_repository: Path, owner_process: subprocess.Popen[bytes], fake_herdr: FakeHerdr, tmp_path: Path
) -> Session:
    return Session(
        script=NAG_SCRIPT,
        repository=git_repository,
        owner_pid=owner_process.pid,
        pane_id=FIRST_PANE_ID,
        herdr=fake_herdr,
        state_home=tmp_path / "state-nag",
    )


@pytest.fixture
def second_nag_session(
    git_repository: Path, second_owner_process: subprocess.Popen[bytes], fake_herdr: FakeHerdr, tmp_path: Path
) -> Session:
    """Another orchestrator on the same machine: nag ids are shared through the same state home."""
    return Session(
        script=NAG_SCRIPT,
        repository=git_repository,
        owner_pid=second_owner_process.pid,
        pane_id=SECOND_PANE_ID,
        herdr=fake_herdr,
        state_home=tmp_path / "state-nag",
    )


@pytest.fixture
def lockctl_session_factory(
    git_repository: Path, fake_herdr: FakeHerdr, tmp_path: Path
) -> Iterator[Callable[..., Session]]:
    owner_processes = []

    def build_session(index: int, repository: Path | None = None) -> Session:
        owner_process = start_owner_process()
        owner_processes.append(owner_process)
        pane_id = f"w{index}:p{index}"
        fake_herdr.set_status(pane_id, "working")
        return Session(
            script=LOCKCTL_SCRIPT,
            repository=repository or git_repository,
            owner_pid=owner_process.pid,
            pane_id=pane_id,
            herdr=fake_herdr,
            state_home=tmp_path / f"state-{index}",
        )

    yield build_session
    for owner_process in owner_processes:
        owner_process.kill()
        owner_process.wait()


@pytest.fixture
def idle_integrate_holder(first_session: Session, fake_herdr: FakeHerdr) -> Session:
    """Took the lock asking for no idle time at all, so the pane being idle is enough to steal."""
    first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED)
    fake_herdr.set_status(FIRST_PANE_ID, "idle")
    wait_for_idle_observation(first_session, INTEGRATE_LOCK)
    return first_session


@pytest.fixture
def idle_integrate_holder_with_default_threshold(first_session: Session, fake_herdr: FakeHerdr) -> Session:
    first_session.run("acquire", INTEGRATE_LOCK)
    fake_herdr.set_status(FIRST_PANE_ID, "idle")
    wait_for_idle_observation(first_session, INTEGRATE_LOCK)
    return first_session


@pytest.fixture
def lock_poacher_factory() -> Iterator[Callable[..., LockPoacher]]:
    poachers = []

    def build_poacher(session: Session, lock: str, watched_file: Path | None = None) -> LockPoacher:
        poacher = LockPoacher(session, lock, watched_file)
        poachers.append(poacher)
        return poacher

    yield build_poacher
    for poacher in poachers:
        poacher.stop()
