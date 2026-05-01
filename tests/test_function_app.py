"""Unit tests for function_app.py – structured log events and OTel metric."""
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_payload(player_count: int = 25) -> dict:
    """Build a minimal valid roster payload with the requested player count."""
    players = [
        {"name": f"Player {i}", "position": "P", "jersey_number": i}
        for i in range(1, player_count + 1)
    ]
    return {"players": players, "usage": {"total_tokens": 100}}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ROSTER_STORAGE_ACCOUNT_NAME", "teststorage")
    monkeypatch.setenv("ROSTER_CONTAINER_NAME", "yankees-roster")
    monkeypatch.setenv("TRAPI_DEPLOYMENT_NAME", "gpt-4o-2024-11")


@pytest.fixture()
def _patch_imports():
    """Patch all external I/O dependencies used by function_app."""
    with (
        patch("function_app._configure_azure_monitor", None),
        patch("function_app._PROMPT_PATH") as mock_path,
        patch("function_app.BlobWriter") as mock_writer_cls,
        patch("function_app.fetch_1985_yankees_roster") as mock_fetch,
        patch("function_app.validate_roster_response") as mock_validate,
        patch("function_app._PLAYER_COUNT_RETURNED") as mock_metric,
    ):
        mock_path.read_text.return_value = "prompt text"
        yield {
            "mock_path": mock_path,
            "mock_writer_cls": mock_writer_cls,
            "mock_writer": mock_writer_cls.return_value,
            "mock_fetch": mock_fetch,
            "mock_validate": mock_validate,
            "mock_metric": mock_metric,
        }


def _invoke(patches, payload=None, blob_uri="https://storage.blob.core.windows.net/yankees-roster/2026-04-24.json"):
    """Call get_and_store_yankees_roster with the given mocks configured."""
    if payload is None:
        payload = _make_valid_payload()

    patches["mock_fetch"].return_value = payload

    validation = MagicMock()
    validation.is_valid = True
    validation.players = payload.get("players", [])
    validation.error = None
    patches["mock_validate"].return_value = validation

    patches["mock_writer"].write.return_value = blob_uri

    import function_app
    timer = MagicMock()
    with patch("function_app._LOGGER") as mock_logger:
        function_app.get_and_store_yankees_roster(timer)
    return mock_logger


# ---------------------------------------------------------------------------
# Test: function_started
# ---------------------------------------------------------------------------

class TestFunctionStartedLog:
    def test_function_started_is_logged(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        log_calls = [c.args[0] for c in mock_logger.info.call_args_list]
        assert "function_started" in log_calls

    def test_function_started_includes_run_date_utc(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        started_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "function_started"
        )
        extra = started_call.kwargs.get("extra", {})
        assert "run_date_utc" in extra
        # Verify it looks like a date string (YYYY-MM-DD)
        assert len(extra["run_date_utc"]) == 10


# ---------------------------------------------------------------------------
# Test: trapi_request_sent
# ---------------------------------------------------------------------------

class TestTrapiRequestSentLog:
    def test_trapi_request_sent_is_logged(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        log_calls = [c.args[0] for c in mock_logger.info.call_args_list]
        assert "trapi_request_sent" in log_calls

    def test_trapi_request_sent_includes_model_version(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        sent_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "trapi_request_sent"
        )
        extra = sent_call.kwargs.get("extra", {})
        assert "model_version" in extra

    def test_trapi_request_sent_includes_prompt_hash(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        sent_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "trapi_request_sent"
        )
        extra = sent_call.kwargs.get("extra", {})
        assert "prompt_hash" in extra


# ---------------------------------------------------------------------------
# Test: trapi_response_received
# ---------------------------------------------------------------------------

class TestTrapiResponseReceivedLog:
    def test_trapi_response_received_is_logged(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        log_calls = [c.args[0] for c in mock_logger.info.call_args_list]
        assert "trapi_response_received" in log_calls

    def test_trapi_response_received_includes_token_count(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        recv_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "trapi_response_received"
        )
        extra = recv_call.kwargs.get("extra", {})
        assert "token_count" in extra
        assert extra["token_count"] == 100

    def test_trapi_response_received_includes_latency_ms(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        recv_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "trapi_response_received"
        )
        extra = recv_call.kwargs.get("extra", {})
        assert "latency_ms" in extra
        assert isinstance(extra["latency_ms"], int)

    def test_trapi_response_received_includes_player_count(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        recv_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "trapi_response_received"
        )
        extra = recv_call.kwargs.get("extra", {})
        assert "player_count" in extra
        assert extra["player_count"] == 25


# ---------------------------------------------------------------------------
# Test: blob_write_succeeded
# ---------------------------------------------------------------------------

class TestBlobWriteSucceededLog:
    def test_blob_write_succeeded_is_logged_when_uri_returned(self, _patch_imports):
        mock_logger = _invoke(
            _patch_imports,
            blob_uri="https://storage.blob.core.windows.net/yankees-roster/2026-04-24.json",
        )
        log_calls = [c.args[0] for c in mock_logger.info.call_args_list]
        assert "blob_write_succeeded" in log_calls

    def test_blob_write_succeeded_includes_blob_uri(self, _patch_imports):
        uri = "https://storage.blob.core.windows.net/yankees-roster/2026-04-24.json"
        mock_logger = _invoke(_patch_imports, blob_uri=uri)
        write_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "blob_write_succeeded"
        )
        extra = write_call.kwargs.get("extra", {})
        assert extra.get("blob_uri") == uri

    def test_blob_write_succeeded_not_logged_when_uri_is_none(self, _patch_imports):
        mock_logger = _invoke(_patch_imports, blob_uri=None)
        log_calls = [c.args[0] for c in mock_logger.info.call_args_list]
        assert "blob_write_succeeded" not in log_calls


# ---------------------------------------------------------------------------
# Test: function_completed
# ---------------------------------------------------------------------------

class TestFunctionCompletedLog:
    def test_function_completed_is_logged(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        log_calls = [c.args[0] for c in mock_logger.info.call_args_list]
        assert "function_completed" in log_calls

    def test_function_completed_includes_player_count(self, _patch_imports):
        mock_logger = _invoke(_patch_imports)
        completed_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "function_completed"
        )
        extra = completed_call.kwargs.get("extra", {})
        assert "player_count" in extra
        assert extra["player_count"] == 25

    def test_function_completed_includes_blob_uri(self, _patch_imports):
        uri = "https://storage.blob.core.windows.net/yankees-roster/2026-04-24.json"
        mock_logger = _invoke(_patch_imports, blob_uri=uri)
        completed_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "function_completed"
        )
        extra = completed_call.kwargs.get("extra", {})
        assert extra.get("blob_uri") == uri

    def test_function_completed_includes_write_conflict_false_when_uri_returned(self, _patch_imports):
        mock_logger = _invoke(
            _patch_imports,
            blob_uri="https://storage.blob.core.windows.net/yankees-roster/2026-04-24.json",
        )
        completed_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "function_completed"
        )
        extra = completed_call.kwargs.get("extra", {})
        assert extra.get("write_conflict") is False

    def test_function_completed_includes_write_conflict_true_when_uri_is_none(self, _patch_imports):
        mock_logger = _invoke(_patch_imports, blob_uri=None)
        completed_call = next(
            c for c in mock_logger.info.call_args_list if c.args[0] == "function_completed"
        )
        extra = completed_call.kwargs.get("extra", {})
        assert extra.get("write_conflict") is True


# ---------------------------------------------------------------------------
# Test: _PLAYER_COUNT_RETURNED metric
# ---------------------------------------------------------------------------

class TestPlayerCountReturnedMetric:
    def test_player_count_returned_add_is_called(self, _patch_imports):
        _invoke(_patch_imports)
        _patch_imports["mock_metric"].add.assert_called_once()

    def test_player_count_returned_called_with_correct_count(self, _patch_imports):
        _invoke(_patch_imports)
        call_args = _patch_imports["mock_metric"].add.call_args
        assert call_args.args[0] == 25

    def test_player_count_returned_called_with_run_date_utc_attribute(self, _patch_imports):
        _invoke(_patch_imports)
        call_args = _patch_imports["mock_metric"].add.call_args
        attributes = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("attributes", {})
        assert "run_date_utc" in attributes

    def test_player_count_returned_not_called_on_validation_failure(self, _patch_imports):
        from src.validator import ValidationErrorKind
        _patch_imports["mock_fetch"].return_value = _make_valid_payload()

        validation = MagicMock()
        validation.is_valid = False
        validation.players = None
        error = MagicMock()
        error.message = "Too few players"
        validation.error = error
        _patch_imports["mock_validate"].return_value = validation

        import function_app
        timer = MagicMock()
        with patch("function_app._LOGGER"):
            with pytest.raises(RuntimeError):
                function_app.get_and_store_yankees_roster(timer)

        _patch_imports["mock_metric"].add.assert_not_called()


# ---------------------------------------------------------------------------
# Test: error handling — all exceptions convert to RuntimeError
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_trapi_retry_exhausted_error_raises_runtime_error(self, _patch_imports):
        from trapi_client import TRAPIRetryExhaustedError
        _patch_imports["mock_fetch"].side_effect = TRAPIRetryExhaustedError(
            status_code=429, retries=3, response_payload={}
        )
        import function_app
        timer = MagicMock()
        with patch("function_app._LOGGER"):
            with pytest.raises(RuntimeError):
                function_app.get_and_store_yankees_roster(timer)

    def test_roster_validation_error_raises_runtime_error(self, _patch_imports):
        from trapi_client import RosterValidationError
        from src.validator import ValidationErrorKind
        _patch_imports["mock_fetch"].side_effect = RosterValidationError(
            kind=ValidationErrorKind.PLAYER_COUNT_OUT_OF_RANGE,
            message="Too few players",
            response_payload={},
        )
        import function_app
        timer = MagicMock()
        with patch("function_app._LOGGER"):
            with pytest.raises(RuntimeError):
                function_app.get_and_store_yankees_roster(timer)

    def test_inline_validation_failure_raises_runtime_error(self, _patch_imports):
        """validate_roster_response returns invalid → RuntimeError."""
        _patch_imports["mock_fetch"].return_value = _make_valid_payload()

        validation = MagicMock()
        validation.is_valid = False
        validation.players = None
        error = MagicMock()
        error.message = "bad payload"
        validation.error = error
        _patch_imports["mock_validate"].return_value = validation

        import function_app
        timer = MagicMock()
        with patch("function_app._LOGGER"):
            with pytest.raises(RuntimeError, match="bad payload"):
                function_app.get_and_store_yankees_roster(timer)

    def test_log_event_order(self, _patch_imports):
        """Verify the five key log events appear in the correct order."""
        mock_logger = _invoke(_patch_imports)
        log_calls = [c.args[0] for c in mock_logger.info.call_args_list]
        expected_order = [
            "function_started",
            "trapi_request_sent",
            "trapi_response_received",
            "blob_write_succeeded",
            "function_completed",
        ]
        # All five must appear
        for event in expected_order:
            assert event in log_calls, f"Missing log event: {event}"
        # And in order
        indices = [log_calls.index(e) for e in expected_order]
        assert indices == sorted(indices), "Log events are not in expected order"
