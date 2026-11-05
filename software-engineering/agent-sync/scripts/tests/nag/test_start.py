import re

from tests.utils.constants import BUSY_EXIT_CODE, HERDR_UNAVAILABLE, NAG_DEFAULT_MINIMUM, REVIEW_TITLE
from tests.utils.helpers import FakeHerdr, Session, collect_output, process_is_running, wait_until


class TestStart:
    def test_start_notifies_immediately_with_the_title_body_and_request_sound(
        self, nag_session: Session, fake_herdr: FakeHerdr
    ):
        started = nag_session.run("start", "design", "--title", REVIEW_TITLE, "--body", "pick one", "--every", "60s")

        assert started.returncode == 0
        wait_until(fake_herdr.notifications, "the first notification")
        assert fake_herdr.notifications() == [[REVIEW_TITLE, "--sound", "request", "--body", "pick one"]]

    def test_start_without_a_body_sends_no_body_option(self, nag_session: Session, fake_herdr: FakeHerdr):
        nag_session.run("start", "design", "--title", REVIEW_TITLE, "--every", "60s")

        wait_until(fake_herdr.notifications, "the first notification")
        assert fake_herdr.notifications() == [[REVIEW_TITLE, "--sound", "request"]]

    def test_start_repeats_the_notification_every_interval(self, nag_session: Session, fake_herdr: FakeHerdr):
        nag_session.run("start", "design", "--title", REVIEW_TITLE, "--every", "0.3s")

        wait_until(lambda: len(fake_herdr.notifications()) >= 3, "three repeated notifications")

    def test_start_defaults_to_one_notification_every_five_minutes(self, nag_session: Session):
        nag_session.run("start", "design", "--title", REVIEW_TITLE)

        assert nag_session.nag_record("design")["every_seconds"] == 300.0

    def test_start_with_a_running_id_replaces_the_nag(self, nag_session: Session, fake_herdr: FakeHerdr):
        nag_session.run("start", "design", "--title", "first title", "--every", "60s")
        wait_until(fake_herdr.notifications, "the first notification")
        old_loop_pid = nag_session.nag_record("design")["nagger_pid"]

        replaced = nag_session.run("start", "design", "--title", "second title", "--every", "60s")

        assert replaced.returncode == 0
        assert "replaced" in replaced.output
        wait_until(lambda: len(fake_herdr.notifications()) == 2, "the replacement's immediate notification")
        assert fake_herdr.notifications()[1][0] == "second title"
        assert not process_is_running(old_loop_pid)
        assert nag_session.run("list").stdout.count("design") == 1

    def test_start_rejects_an_invalid_id(self, nag_session: Session):
        rejected = nag_session.run("start", "Bad_Id", "--title", REVIEW_TITLE)

        assert rejected.returncode == 2
        assert "invalid nag id" in rejected.output

    def test_start_requires_a_title(self, nag_session: Session):
        rejected = nag_session.run("start", "design")

        assert rejected.returncode == 2
        assert "--title" in rejected.output

    def test_start_rejects_an_invalid_interval(self, nag_session: Session):
        rejected = nag_session.run("start", "design", "--title", REVIEW_TITLE, "--every", "soon")

        assert rejected.returncode == 2
        assert "invalid duration" in rejected.output

    def test_start_fails_and_leaves_no_loop_when_herdr_is_unavailable(self, nag_session: Session):
        failed = nag_session.run("start", "design", "--title", REVIEW_TITLE, environment=HERDR_UNAVAILABLE)

        assert failed.returncode == 2
        assert "first notification failed" in failed.output
        assert "herdr could not be run" in failed.output
        assert nag_session.nag_record("design") is None
        assert "no running nags" in nag_session.run("list").stdout

    def test_start_fails_with_the_herdr_error_when_herdr_rejects_the_first_notification(
        self, nag_session: Session, fake_herdr: FakeHerdr
    ):
        fake_herdr.fail_notifications()

        failed = nag_session.run("start", "design", "--title", REVIEW_TITLE)

        assert failed.returncode == 2
        assert "simulated notification failure" in failed.output
        assert nag_session.nag_record("design") is None

    def test_start_keeps_running_and_shows_the_last_error_when_a_later_notification_fails(
        self, nag_session: Session, fake_herdr: FakeHerdr
    ):
        nag_session.run("start", "design", "--title", REVIEW_TITLE, "--every", "0.3s")
        wait_until(fake_herdr.notifications, "the first notification")

        fake_herdr.fail_notifications()
        wait_until(lambda: (nag_session.nag_record("design") or {}).get("last_error"), "the failure to be recorded")

        listed = nag_session.run("list").stdout
        assert "last error: " in listed
        assert "simulated notification failure" in listed

    def test_start_resumes_notifying_once_herdr_works_again(self, nag_session: Session, fake_herdr: FakeHerdr):
        nag_session.run("start", "design", "--title", REVIEW_TITLE, "--every", "0.3s")
        fake_herdr.fail_notifications()
        wait_until(lambda: (nag_session.nag_record("design") or {}).get("last_error"), "the failure to be recorded")
        notifications_before = len(fake_herdr.notifications())

        fake_herdr.recover_notifications()

        wait_until(lambda: len(fake_herdr.notifications()) > notifications_before, "notifications to resume")
        wait_until(lambda: not (nag_session.nag_record("design") or {}).get("last_error"), "the error to clear")

    def test_start_rejects_an_interval_of_zero(self, nag_session: Session, fake_herdr: FakeHerdr):
        rejected = nag_session.run(
            "start", "design", "--title", REVIEW_TITLE, "--every", "0s", environment=NAG_DEFAULT_MINIMUM
        )

        assert rejected.returncode == 2
        assert "at least 30s" in rejected.output
        assert fake_herdr.notifications() == []

    def test_start_rejects_an_interval_below_thirty_seconds(self, nag_session: Session):
        rejected = nag_session.run(
            "start", "design", "--title", REVIEW_TITLE, "--every", "29s", environment=NAG_DEFAULT_MINIMUM
        )

        assert rejected.returncode == 2
        assert "at least 30s" in rejected.output
        assert nag_session.nag_record("design") is None

    def test_start_accepts_an_interval_of_exactly_thirty_seconds(self, nag_session: Session):
        started = nag_session.run(
            "start", "design", "--title", REVIEW_TITLE, "--every", "30s", environment=NAG_DEFAULT_MINIMUM
        )

        assert started.returncode == 0

    def test_start_refuses_to_replace_the_nag_of_another_session(
        self, nag_session: Session, second_nag_session: Session
    ):
        nag_session.run("start", "design", "--title", "first title", "--every", "60s")
        loop_pid = nag_session.nag_record("design")["nagger_pid"]

        refused = second_nag_session.run("start", "design", "--title", "intruder", "--every", "60s")

        assert refused.returncode == BUSY_EXIT_CODE
        assert "belongs to another session" in refused.output
        assert nag_session.nag_record("design")["title"] == "first title"
        assert process_is_running(loop_pid)

    def test_start_with_force_replaces_the_nag_of_another_session(
        self, nag_session: Session, second_nag_session: Session
    ):
        nag_session.run("start", "design", "--title", "first title", "--every", "60s")
        old_loop_pid = nag_session.nag_record("design")["nagger_pid"]

        replaced = second_nag_session.run("start", "design", "--title", "second title", "--every", "60s", "--force")

        assert replaced.returncode == 0
        assert nag_session.nag_record("design")["title"] == "second title"
        assert not process_is_running(old_loop_pid)


class TestStartInParallel:
    def test_two_concurrent_starts_of_the_same_id_leave_exactly_one_loop_that_stop_can_end(self, nag_session: Session):
        racing = [
            nag_session.popen("start", "design", "--title", REVIEW_TITLE, "--every", "60s"),
            nag_session.popen("start", "design", "--title", REVIEW_TITLE, "--every", "60s"),
        ]

        results = [collect_output(process) for process in racing]

        loop_pids = [int(re.search(r"loop pid (\d+)", result.stdout).group(1)) for result in results]
        assert [result.returncode for result in results] == [0, 0]
        assert sorted(process_is_running(loop_pid) for loop_pid in loop_pids) == [False, True]
        recorded_loop_pid = nag_session.nag_record("design")["nagger_pid"]
        assert process_is_running(recorded_loop_pid)
        assert nag_session.run("stop", "design").returncode == 0
        assert not any(process_is_running(loop_pid) for loop_pid in loop_pids)
