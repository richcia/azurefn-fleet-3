"""Unit tests for function_app.py (nightly Timer Trigger)."""

import logging
from unittest.mock import MagicMock, patch, call

import pytest

import function_app
from function_app import nightly_roster_sync


SAMPLE_ROSTER = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Rickey Henderson", "position": "LF"},
]


def _make_timer_request(past_due: bool = False) -> MagicMock:
    """Return a minimal mock TimerRequest."""
    timer = MagicMock()
    timer.past_due = past_due
    return timer


class TestNightlyRosterSync:
    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-20240101.json")
    @patch("function_app.trapi_client.fetch_1985_yankees_roster", return_value=SAMPLE_ROSTER)
    def test_success_calls_fetch_then_write(self, mock_fetch, mock_write):
        """fetch_1985_yankees_roster is called before write_roster_blob."""
        timer = _make_timer_request()

        calls = MagicMock()
        calls.attach_mock(mock_fetch, "fetch")
        calls.attach_mock(mock_write, "write")

        nightly_roster_sync(timer)

        assert calls.mock_calls == [
            call.fetch(),
            call.write(SAMPLE_ROSTER),
        ]

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-20240101.json")
    @patch("function_app.trapi_client.fetch_1985_yankees_roster", return_value=SAMPLE_ROSTER)
    def test_success_logs_start_count_and_completion(self, mock_fetch, mock_write, caplog):
        """INFO log entries are emitted for start, roster count, and blob write completion."""
        timer = _make_timer_request()

        with caplog.at_level(logging.INFO, logger="function_app"):
            nightly_roster_sync(timer)

        messages = [r.message for r in caplog.records]
        assert any("nightly_roster_sync: starting" in m for m in messages), "Expected 'starting' log entry"
        assert any("initiating TRAPI call" in m for m in messages), "Expected 'initiating TRAPI call' log entry"
        assert any("fetched 3 players" in m for m in messages), "Expected roster count (3) in log"
        assert any("roster-20240101.json" in m for m in messages), "Expected blob name in log"
        assert any("nightly_roster_sync: complete" in m for m in messages), "Expected 'complete' log entry"

    @patch("function_app.trapi_client.fetch_1985_yankees_roster", side_effect=RuntimeError("TRAPI down"))
    def test_fetch_error_is_logged_and_re_raised(self, mock_fetch, caplog):
        """Errors from fetch are logged at ERROR level and then re-raised."""
        timer = _make_timer_request()

        with caplog.at_level(logging.ERROR, logger="function_app"):
            with pytest.raises(RuntimeError, match="TRAPI down"):
                nightly_roster_sync(timer)

        error_messages = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert any("TRAPI down" in m for m in error_messages), "Expected error to be logged"

    @patch("function_app.blob_writer.write_roster_blob", side_effect=ValueError("STORAGE_ACCOUNT_NAME not set"))
    @patch("function_app.trapi_client.fetch_1985_yankees_roster", return_value=SAMPLE_ROSTER)
    def test_write_error_is_logged_and_re_raised(self, mock_fetch, mock_write, caplog):
        """Errors from blob write are logged at ERROR level and then re-raised."""
        timer = _make_timer_request()

        with caplog.at_level(logging.ERROR, logger="function_app"):
            with pytest.raises(ValueError, match="STORAGE_ACCOUNT_NAME not set"):
                nightly_roster_sync(timer)

        error_messages = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert any("STORAGE_ACCOUNT_NAME not set" in m for m in error_messages)

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-20240101.json")
    @patch("function_app.trapi_client.fetch_1985_yankees_roster", return_value=[])
    def test_empty_roster_logs_zero_count(self, mock_fetch, mock_write, caplog):
        """An empty roster is handled without error and logs count 0."""
        timer = _make_timer_request()

        with caplog.at_level(logging.INFO, logger="function_app"):
            nightly_roster_sync(timer)

        messages = [r.message for r in caplog.records]
        assert any("nightly_roster_sync: starting" in m for m in messages), "Expected 'starting' log entry"
        assert any("fetched 0 players" in m for m in messages), "Expected count 0 in log"

    def test_timer_trigger_schedule_is_nightly_midnight(self):
        """Timer Trigger CRON expression matches the agreed nightly midnight schedule."""
        funcs = function_app.app.get_functions()
        func_names = [f.get_function_name() for f in funcs]
        assert "nightly_roster_sync" in func_names, (
            f"Expected 'nightly_roster_sync' in registered functions; got {func_names}"
        )

        roster_func = next(f for f in funcs if f.get_function_name() == "nightly_roster_sync")
        bindings = roster_func.get_bindings_dict().get("bindings", [])
        timer_binding = next((b for b in bindings if b.get("type") == "timerTrigger"), None)
        assert timer_binding is not None, "Expected a timerTrigger binding"
        schedule = timer_binding.get("schedule", "")
        assert schedule == "0 0 0 * * *", (
            f"Expected nightly CRON '0 0 0 * * *', got '{schedule}'"
        )
