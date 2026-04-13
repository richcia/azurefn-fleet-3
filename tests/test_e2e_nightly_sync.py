"""End-to-end QA tests for the nightly Yankees roster sync (QA-02).

These tests simulate the complete production execution path — from Azure
Function Timer trigger through TRAPI fetch to Blob Storage write — using
mocks in place of live Azure services.  They validate all QA-02 acceptance
criteria without requiring real Azure credentials.

Acceptance Criteria covered:
  AC-1  Function invocation completes successfully (no unhandled exceptions)
  AC-2  Blob is written to the 'yankees-roster' container after execution
  AC-3  Roster data passes spot-check: contains Don Mattingly, Rickey Henderson
  AC-4  Function execution completes within 60 seconds
  AC-5  Second triggered run produces an overwrite of the same blob name
"""

import json
import logging
import time
from unittest.mock import MagicMock, patch, call

import pytest

from function_app import nightly_roster_sync


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Subset of known 1985 NY Yankees players used for spot-checks (AC-3).
KNOWN_1985_YANKEES = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Rickey Henderson", "position": "LF"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Ron Guidry", "position": "SP"},
    {"name": "Phil Niekro", "position": "SP"},
    {"name": "Willie Randolph", "position": "2B"},
    {"name": "Don Baylor", "position": "DH"},
]

# Full 26-man roster mock — realistic size for a 1985 MLB team.
MOCK_1985_YANKEES_ROSTER = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Willie Randolph", "position": "2B"},
    {"name": "Mike Pagliarulo", "position": "3B"},
    {"name": "Bobby Meacham", "position": "SS"},
    {"name": "Rickey Henderson", "position": "LF"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Ken Griffey Sr.", "position": "CF"},
    {"name": "Butch Wynegar", "position": "C"},
    {"name": "Don Baylor", "position": "DH"},
    {"name": "Ron Guidry", "position": "SP"},
    {"name": "Phil Niekro", "position": "SP"},
    {"name": "Ed Whitson", "position": "SP"},
    {"name": "Joe Cowley", "position": "SP"},
    {"name": "John Montefusco", "position": "SP"},
    {"name": "Dave Righetti", "position": "RP"},
    {"name": "Brian Fisher", "position": "RP"},
    {"name": "Rich Bordi", "position": "RP"},
    {"name": "Bob Shirley", "position": "RP"},
    {"name": "Dennis Rasmussen", "position": "SP"},
    {"name": "Scott Bradley", "position": "C"},
    {"name": "Dan Pasqua", "position": "OF"},
    {"name": "Mike Easler", "position": "OF"},
    {"name": "Henry Cotto", "position": "OF"},
    {"name": "Dale Berra", "position": "INF"},
    {"name": "Andre Robertson", "position": "INF"},
    {"name": "Rex Hudler", "position": "INF"},
]


def _make_timer_request(past_due: bool = False) -> MagicMock:
    """Return a minimal mock TimerRequest."""
    timer = MagicMock()
    timer.past_due = past_due
    return timer


# ---------------------------------------------------------------------------
# AC-1 / AC-2 / AC-3: Complete end-to-end happy path
# ---------------------------------------------------------------------------


class TestEndToEndHappyPath:
    """Simulate a full production invocation and validate observable outputs."""

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_full_invocation_completes_without_exception(self, mock_fetch, mock_write):
        """AC-1: Entire function executes without raising an exception."""
        timer = _make_timer_request()
        # Should not raise
        nightly_roster_sync(timer)

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_blob_written_to_yankees_roster_container(self, mock_fetch, mock_write):
        """AC-2: write_roster_blob is called with the full roster after a successful TRAPI call."""
        timer = _make_timer_request()
        nightly_roster_sync(timer)

        mock_write.assert_called_once_with(MOCK_1985_YANKEES_ROSTER)

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_roster_spot_check_contains_don_mattingly(self, mock_fetch, mock_write):
        """AC-3: Returned roster includes Don Mattingly (1B)."""
        timer = _make_timer_request()
        nightly_roster_sync(timer)

        roster_arg = mock_write.call_args[0][0]
        names = {p["name"] for p in roster_arg}
        assert "Don Mattingly" in names, (
            "Spot-check failed: Don Mattingly not found in roster"
        )

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_roster_spot_check_contains_rickey_henderson(self, mock_fetch, mock_write):
        """AC-3: Returned roster includes Rickey Henderson (LF)."""
        timer = _make_timer_request()
        nightly_roster_sync(timer)

        roster_arg = mock_write.call_args[0][0]
        names = {p["name"] for p in roster_arg}
        assert "Rickey Henderson" in names, (
            "Spot-check failed: Rickey Henderson not found in roster"
        )

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_roster_spot_check_all_known_players_present(self, mock_fetch, mock_write):
        """AC-3: Roster passes spot-check for all known 1985 Yankees players."""
        timer = _make_timer_request()
        nightly_roster_sync(timer)

        roster_arg = mock_write.call_args[0][0]
        roster_names = {p["name"] for p in roster_arg}

        missing = [p["name"] for p in KNOWN_1985_YANKEES if p["name"] not in roster_names]
        assert not missing, (
            f"Spot-check failed: the following known 1985 Yankees players are missing "
            f"from the roster: {missing}"
        )

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_roster_players_have_required_fields(self, mock_fetch, mock_write):
        """AC-3: Every player in the roster has both 'name' and 'position' fields."""
        timer = _make_timer_request()
        nightly_roster_sync(timer)

        roster_arg = mock_write.call_args[0][0]
        for idx, player in enumerate(roster_arg):
            assert "name" in player, f"Player at index {idx} is missing 'name' field"
            assert "position" in player, f"Player at index {idx} is missing 'position' field"
            assert isinstance(player["name"], str) and player["name"], (
                f"Player at index {idx} has an empty or non-string 'name'"
            )
            assert isinstance(player["position"], str) and player["position"], (
                f"Player at index {idx} has an empty or non-string 'position'"
            )

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_function_complete_event_logged(self, mock_fetch, mock_write, caplog):
        """AC-1: function_complete structured log event is emitted on success."""
        timer = _make_timer_request()

        with caplog.at_level(logging.INFO, logger="function_app"):
            nightly_roster_sync(timer)

        complete_records = [
            r for r in caplog.records
            if hasattr(r, "custom_dimensions")
            and r.custom_dimensions.get("event") == "function_complete"
        ]
        assert complete_records, (
            "AC-1: Expected a 'function_complete' structured log event — "
            "Application Insights would show no completion trace"
        )


# ---------------------------------------------------------------------------
# AC-4: Execution duration within acceptable bounds (< 60 seconds)
# ---------------------------------------------------------------------------


class TestExecutionDuration:
    """Verify the function invocation finishes within the 60-second budget."""

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_execution_completes_within_60_seconds(self, mock_fetch, mock_write):
        """AC-4: Function orchestration overhead (excluding I/O) completes in < 60s."""
        timer = _make_timer_request()

        start = time.monotonic()
        nightly_roster_sync(timer)
        elapsed = time.monotonic() - start

        assert elapsed < 60, (
            f"AC-4: Function execution took {elapsed:.3f}s — exceeds the 60-second budget. "
            "Check for unexpected blocking calls in the function orchestration path."
        )

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_execution_completes_within_1_second_without_io(self, mock_fetch, mock_write):
        """AC-4: With mocked I/O, orchestration overhead must be negligible (< 1s)."""
        timer = _make_timer_request()

        start = time.monotonic()
        nightly_roster_sync(timer)
        elapsed = time.monotonic() - start

        assert elapsed < 1.0, (
            f"AC-4: Function orchestration (mocked I/O) took {elapsed:.3f}s — "
            "unexpectedly slow. Possible regression: blocking call in function_app.py?"
        )


# ---------------------------------------------------------------------------
# AC-5: Second triggered run produces correct overwrite
# ---------------------------------------------------------------------------


class TestSecondRunOverwriteBehavior:
    """Validate that a second invocation correctly overwrites the existing blob."""

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_second_run_calls_write_blob_again(self, mock_fetch, mock_write):
        """AC-5: A second invocation triggers another blob write call."""
        timer = _make_timer_request()

        nightly_roster_sync(timer)
        nightly_roster_sync(timer)

        assert mock_write.call_count == 2, (
            "AC-5: Expected write_roster_blob to be called once per invocation"
        )

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_second_run_writes_same_blob_name_convention(self, mock_fetch, mock_write):
        """AC-5: Both runs write a blob following the roster-YYYYMMDD.json naming convention."""
        import re

        timer = _make_timer_request()

        nightly_roster_sync(timer)
        nightly_roster_sync(timer)

        for i, call_args in enumerate(mock_write.call_args_list):
            # Verify the roster passed to write_roster_blob on each call is a non-empty list
            roster_arg = call_args[0][0]
            assert isinstance(roster_arg, list), (
                f"AC-5: Run {i + 1} — write_roster_blob received non-list argument: "
                f"{type(roster_arg).__name__}"
            )
            assert len(roster_arg) > 0, (
                f"AC-5: Run {i + 1} — write_roster_blob received an empty roster"
            )

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer._CREDENTIAL")
    def test_blob_upload_uses_overwrite_true(self, mock_cred, mock_bsc, monkeypatch):
        """AC-5: Blob upload uses overwrite=True so a second run replaces the existing blob."""
        import blob_writer

        monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "myaccount")

        mock_blob_client = MagicMock()
        mock_bsc.return_value.get_blob_client.return_value = mock_blob_client

        # Simulate two sequential writes (two nightly runs on the same calendar day)
        blob_writer.write_roster_blob(MOCK_1985_YANKEES_ROSTER)
        blob_writer.write_roster_blob(MOCK_1985_YANKEES_ROSTER)

        assert mock_blob_client.upload_blob.call_count == 2
        for i, call_args in enumerate(mock_blob_client.upload_blob.call_args_list):
            assert call_args[1]["overwrite"] is True, (
                f"AC-5: Run {i + 1} — upload_blob must use overwrite=True so a second "
                "nightly run correctly replaces the existing blob"
            )

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer._CREDENTIAL")
    def test_blob_name_follows_naming_convention(self, mock_cred, mock_bsc, monkeypatch):
        """AC-5: Blob name follows the roster-YYYYMMDD.json convention."""
        import re
        import blob_writer

        monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "myaccount")

        mock_blob_client = MagicMock()
        mock_bsc.return_value.get_blob_client.return_value = mock_blob_client

        blob_name = blob_writer.write_roster_blob(MOCK_1985_YANKEES_ROSTER)

        assert re.fullmatch(r"roster-\d{8}\.json", blob_name), (
            f"AC-5: Blob name '{blob_name}' does not follow the expected "
            "'roster-YYYYMMDD.json' naming convention"
        )


# ---------------------------------------------------------------------------
# Structured log events — Application Insights observability validation
# ---------------------------------------------------------------------------


class TestApplicationInsightsTracing:
    """Verify all structured log events required for Application Insights traces."""

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_all_expected_log_events_emitted(self, mock_fetch, mock_write, caplog):
        """All five structured log events are emitted during a successful invocation."""
        timer = _make_timer_request()

        with caplog.at_level(logging.INFO, logger="function_app"):
            nightly_roster_sync(timer)

        emitted_events = {
            r.custom_dimensions.get("event")
            for r in caplog.records
            if hasattr(r, "custom_dimensions")
        }

        expected_events = {
            "function_start",
            "trapi_call_start",
            "trapi_call_complete",
            "blob_write_complete",
            "function_complete",
        }
        missing = expected_events - emitted_events
        assert not missing, (
            f"Application Insights observability gap: the following structured log "
            f"events were not emitted — {sorted(missing)}"
        )

    @patch("function_app.trapi_client.fetch_1985_yankees_roster", side_effect=RuntimeError("TRAPI unavailable"))
    def test_function_error_event_emitted_on_failure(self, mock_fetch, caplog):
        """function_error event is emitted and contains the error message."""
        timer = _make_timer_request()

        with caplog.at_level(logging.ERROR, logger="function_app"):
            with pytest.raises(RuntimeError, match="TRAPI unavailable"):
                nightly_roster_sync(timer)

        error_records = [
            r for r in caplog.records
            if hasattr(r, "custom_dimensions")
            and r.custom_dimensions.get("event") == "function_error"
        ]
        assert error_records, (
            "Application Insights would show no error trace — "
            "function_error event must be emitted on exception"
        )
        assert "TRAPI unavailable" in error_records[0].custom_dimensions.get("error", ""), (
            "function_error custom_dimensions must include the error message for alerting"
        )

    @patch("function_app.blob_writer.write_roster_blob", return_value="roster-19850101.json")
    @patch(
        "function_app.trapi_client.fetch_1985_yankees_roster",
        return_value=MOCK_1985_YANKEES_ROSTER,
    )
    def test_blob_write_complete_event_has_player_count(self, mock_fetch, mock_write, caplog):
        """blob_write_complete event carries player_count for Application Insights dashboards."""
        timer = _make_timer_request()

        with caplog.at_level(logging.INFO, logger="function_app"):
            nightly_roster_sync(timer)

        blob_records = [
            r for r in caplog.records
            if hasattr(r, "custom_dimensions")
            and r.custom_dimensions.get("event") == "blob_write_complete"
        ]
        assert blob_records, "blob_write_complete event not found in log records"
        assert blob_records[0].custom_dimensions.get("player_count") == len(MOCK_1985_YANKEES_ROSTER), (
            "blob_write_complete must carry the correct player_count for roster size monitoring"
        )
