from lockctl_context import describe_busy

from tests.utils.builders import build_command_context, build_lock_record
from tests.utils.constants import OTHER_SAMPLE_WORKTREE, SAMPLE_HOLDER_PID, SAMPLE_OWNER_PID, STACK_LOCK


class TestDescribeBusy:
    def test_describe_busy_reports_an_acquire_hold_of_the_caller_as_taken_by_acquire_not_as_a_run(self):
        winner = build_lock_record(hold_kind="acquire")

        message = describe_busy(build_command_context(), STACK_LOCK, winner, wait_seconds=0.0)

        assert f"held by you through `acquire` (holder pid {SAMPLE_HOLDER_PID}" in message
        assert "your own `run`" not in message

    def test_describe_busy_reports_a_run_hold_of_the_caller_as_the_callers_own_run(self):
        runner = build_lock_record(hold_kind="run")

        message = describe_busy(build_command_context(), STACK_LOCK, runner, wait_seconds=0.0)

        assert f"held by your own `run` (pid {SAMPLE_HOLDER_PID}" in message

    def test_describe_busy_names_the_worktree_when_the_callers_own_session_holds_the_lock_from_another_one(self):
        other_worktree_hold = build_lock_record(hold_kind="acquire", scope=OTHER_SAMPLE_WORKTREE)

        message = describe_busy(build_command_context(), STACK_LOCK, other_worktree_hold, wait_seconds=0.0)

        assert f"worktree {OTHER_SAMPLE_WORKTREE}" in message
        assert "that is your own session, but the hold was taken from another worktree" in message
        assert "held by you" not in message

    def test_describe_busy_does_not_call_another_owners_hold_the_callers_own(self):
        foreign_hold = build_lock_record(owner_pid=SAMPLE_OWNER_PID + 1)

        message = describe_busy(build_command_context(), STACK_LOCK, foreign_hold, wait_seconds=0.0)

        assert "your own" not in message
        assert f"owner pid {SAMPLE_OWNER_PID + 1}" in message

    def test_describe_busy_says_how_long_the_wait_lasted_before_giving_up(self):
        foreign_hold = build_lock_record(owner_pid=SAMPLE_OWNER_PID + 1)

        message = describe_busy(build_command_context(), STACK_LOCK, foreign_hold, wait_seconds=90.0)

        assert message.startswith("gave up after 1m 30s: ")
