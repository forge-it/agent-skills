import pytest
from agent_sync_common import HerdrError, HerdrStatus, read_pane_reading, run_herdr

from tests.utils.constants import FIRST_PANE_ID, HERDR_SESSION_NAME, OTHER_HERDR_SESSION_NAME
from tests.utils.helpers import FakeHerdr
from tests.utils.samples import NOT_TEXT_HERDR_REPLY


class TestReadPaneReading:
    def test_read_pane_reading_returns_the_status_of_the_pane(self, fake_herdr: FakeHerdr):
        fake_herdr.set_status(FIRST_PANE_ID, "idle")

        reading = read_pane_reading(FIRST_PANE_ID, "")

        assert reading
        assert reading.status == HerdrStatus.IDLE

    def test_read_pane_reading_reads_a_pane_recorded_in_the_session_the_caller_runs_in(
        self, fake_herdr: FakeHerdr, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("HERDR_SESSION", HERDR_SESSION_NAME)

        assert read_pane_reading(FIRST_PANE_ID, HERDR_SESSION_NAME)

    def test_read_pane_reading_returns_nothing_for_a_pane_recorded_in_another_herdr_session(
        self, fake_herdr: FakeHerdr, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("HERDR_SESSION", HERDR_SESSION_NAME)

        assert read_pane_reading(FIRST_PANE_ID, OTHER_HERDR_SESSION_NAME) is None
        assert fake_herdr.read_count(FIRST_PANE_ID) == 0

    def test_read_pane_reading_returns_nothing_when_only_the_caller_runs_in_a_herdr_session(
        self, fake_herdr: FakeHerdr, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("HERDR_SESSION", HERDR_SESSION_NAME)

        assert read_pane_reading(FIRST_PANE_ID, "") is None

    def test_read_pane_reading_returns_nothing_when_only_the_pane_was_recorded_in_a_herdr_session(
        self, fake_herdr: FakeHerdr
    ):
        assert read_pane_reading(FIRST_PANE_ID, HERDR_SESSION_NAME) is None

    def test_read_pane_reading_returns_nothing_when_herdr_prints_bytes_that_are_not_text(self, fake_herdr: FakeHerdr):
        fake_herdr.reply_with(NOT_TEXT_HERDR_REPLY)

        assert read_pane_reading(FIRST_PANE_ID, "") is None


class TestRunHerdr:
    def test_run_herdr_reports_output_that_is_not_text_as_a_herdr_error(self, fake_herdr: FakeHerdr):
        fake_herdr.reply_with(NOT_TEXT_HERDR_REPLY)

        with pytest.raises(HerdrError, match="could not be run"):
            run_herdr(["agent", "get", FIRST_PANE_ID])
