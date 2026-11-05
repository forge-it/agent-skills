import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tests.utils.constants import FIRST_PANE_ID, INTEGRATE_LOCK, NO_IDLE_REQUIRED, STACK_LOCK
from tests.utils.helpers import (
    FakeHerdr,
    OrphanedCommand,
    Session,
    leave_an_orphaned_command,
    wait_for_idle_observation,
)


@pytest.fixture
def orphan_in_an_acquired_lock(first_session: Session, tmp_path: Path) -> Iterator[OrphanedCommand]:
    """The `run` process of a command inside a lock taken with `acquire` was killed; the holder lives on."""
    first_session.run("acquire", STACK_LOCK, environment=NO_IDLE_REQUIRED)
    orphan = leave_an_orphaned_command(first_session, STACK_LOCK, tmp_path / "orphan-pid")
    yield orphan
    orphan.kill()


@pytest.fixture
def orphan_of_a_killed_run_holding_the_lock(first_session: Session, tmp_path: Path) -> Iterator[OrphanedCommand]:
    """The `run` process that held the lock itself was killed: the flock is free, the record stale."""
    orphan = leave_an_orphaned_command(first_session, STACK_LOCK, tmp_path / "orphan-pid")
    yield orphan
    orphan.kill()


@pytest.fixture
def unrelated_process_group() -> Iterator[subprocess.Popen[bytes]]:
    process = subprocess.Popen(["sleep", "600"], process_group=0)
    yield process
    process.kill()
    process.wait()


@pytest.fixture
def idle_holder_in_linked_worktree(first_session: Session, fake_herdr: FakeHerdr, linked_worktree: Path) -> Session:
    """Took `integrate` from a linked worktree asking for no idle time, then went idle."""
    first_session.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED, working_directory=linked_worktree)
    fake_herdr.set_status(FIRST_PANE_ID, "idle")
    wait_for_idle_observation(first_session, INTEGRATE_LOCK)
    return first_session


@pytest.fixture
def bare_layout_holder(
    lockctl_session_factory: Callable[..., Session], fake_herdr: FakeHerdr, bare_repository_worktree: Path
) -> Session:
    """In a bare repository with worktrees, took `integrate` from a worktree, then went idle."""
    holder = lockctl_session_factory(1, bare_repository_worktree)
    holder.run("acquire", INTEGRATE_LOCK, environment=NO_IDLE_REQUIRED)
    fake_herdr.set_status(holder.pane_id, "idle")
    wait_for_idle_observation(holder, INTEGRATE_LOCK)
    return holder


@pytest.fixture
def bare_layout_thief(lockctl_session_factory: Callable[..., Session], bare_repository_worktree: Path) -> Session:
    return lockctl_session_factory(2, bare_repository_worktree)
