from collections.abc import Callable
from pathlib import Path

from tests.utils.constants import SLOW_TERMINATION_COMMAND, STACK_LOCK
from tests.utils.helpers import (
    LockPoacher,
    Session,
    collect_output,
    wait_for_command_to_run_under,
    wait_until,
)


class TestHandoverWaitsForTheCommand:
    def test_release_hands_the_lock_over_only_once_a_slow_command_is_gone(
        self,
        first_session: Session,
        second_session: Session,
        tmp_path: Path,
        lock_poacher_factory: Callable[..., LockPoacher],
    ):
        ready_marker = tmp_path / "ready"
        gone_marker = tmp_path / "gone"
        first_session.run("acquire", STACK_LOCK)
        command = SLOW_TERMINATION_COMMAND.format(ready_marker=ready_marker, gone_marker=gone_marker)
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", command)
        wait_until(ready_marker.exists, "the command to be ready")
        wait_for_command_to_run_under(first_session, STACK_LOCK)
        waiter = lock_poacher_factory(second_session, STACK_LOCK, gone_marker)
        waiter.start()

        released = first_session.run("release", STACK_LOCK)

        collect_output(running)
        assert released.returncode == 0
        assert waiter.won_the_lock()
        assert waiter.watched_file_existed_when_it_won

    def test_steal_force_hands_the_lock_over_only_once_a_slow_command_is_gone(
        self,
        first_session: Session,
        second_session: Session,
        lockctl_session_factory: Callable[[int], Session],
        tmp_path: Path,
        lock_poacher_factory: Callable[..., LockPoacher],
    ):
        ready_marker = tmp_path / "ready"
        gone_marker = tmp_path / "gone"
        first_session.run("acquire", STACK_LOCK)
        command = SLOW_TERMINATION_COMMAND.format(ready_marker=ready_marker, gone_marker=gone_marker)
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", command)
        wait_until(ready_marker.exists, "the command to be ready")
        wait_for_command_to_run_under(first_session, STACK_LOCK)
        waiter = lock_poacher_factory(lockctl_session_factory(3), STACK_LOCK, gone_marker)
        waiter.start()

        second_session.run("steal", STACK_LOCK, "--force")

        collect_output(running)
        assert waiter.won_the_lock()
        assert waiter.watched_file_existed_when_it_won

    def test_release_of_a_lock_held_by_a_run_hands_the_lock_over_only_once_its_slow_command_is_gone(
        self,
        first_session: Session,
        second_session: Session,
        tmp_path: Path,
        lock_poacher_factory: Callable[..., LockPoacher],
    ):
        ready_marker = tmp_path / "ready"
        gone_marker = tmp_path / "gone"
        command = SLOW_TERMINATION_COMMAND.format(ready_marker=ready_marker, gone_marker=gone_marker)
        running = first_session.popen("run", STACK_LOCK, "--", "sh", "-c", command)
        wait_until(ready_marker.exists, "the command to be ready")
        wait_until(lambda: first_session.record(STACK_LOCK), "the run command to publish its record")
        waiter = lock_poacher_factory(second_session, STACK_LOCK, gone_marker)
        waiter.start()

        released = first_session.run("release", STACK_LOCK)

        collect_output(running)
        assert released.returncode == 0
        assert waiter.won_the_lock()
        assert waiter.watched_file_existed_when_it_won
