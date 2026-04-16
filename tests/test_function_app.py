from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import function_app


def _valid_roster(count: int = 24) -> list[dict]:
    return [
        {
            "name": f"Player {idx}",
            "position": "IF",
            "jersey_number": idx,
        }
        for idx in range(1, count + 1)
    ]


def test_timer_trigger_configuration():
    functions = function_app.app.get_functions()
    assert len(functions) == 1
    trigger = functions[0].get_bindings_dict()["bindings"][0]

    assert functions[0].get_function_name() == "GetAndStoreYankeesRoster"
    assert trigger["schedule"] == "0 0 2 * * *"
    assert trigger["useMonitor"] is True


def test_get_and_store_yankees_roster_success(monkeypatch):
    monkeypatch.setattr(function_app.trapi_client, "fetch_1985_yankees_roster", Mock(return_value=_valid_roster()))
    monkeypatch.setattr(function_app.blob_writer, "write_roster_blob", Mock(return_value="roster-20260416.json"))
    failed_writer = Mock()
    monkeypatch.setattr(function_app, "_write_failed_blob", failed_writer)
    logger_mock = Mock()
    monkeypatch.setattr(function_app, "logger", logger_mock)

    function_app.get_and_store_yankees_roster(SimpleNamespace(past_due=False))

    function_app.blob_writer.write_roster_blob.assert_called_once()
    failed_writer.assert_not_called()
    events = [call.kwargs["extra"]["custom_dimensions"]["event"] for call in logger_mock.info.call_args_list]
    assert events == [
        "function_started",
        "trapi_request_sent",
        "trapi_response_received",
        "blob_write_succeeded",
        "function_completed",
    ]
    response_log = logger_mock.info.call_args_list[2].kwargs["extra"]
    assert response_log["custom_measurements"]["player_count_returned"] == 24


def test_get_and_store_yankees_roster_validation_failure(monkeypatch):
    monkeypatch.setattr(function_app.trapi_client, "fetch_1985_yankees_roster", Mock(return_value=_valid_roster(count=23)))
    monkeypatch.setattr(function_app.blob_writer, "write_roster_blob", Mock())
    failed_writer = Mock(return_value="failed/roster-20260416T120000Z.json")
    monkeypatch.setattr(function_app, "_write_failed_blob", failed_writer)
    logger_mock = Mock()
    monkeypatch.setattr(function_app, "logger", logger_mock)

    with pytest.raises(ValueError):
        function_app.get_and_store_yankees_roster(SimpleNamespace(past_due=False))

    function_app.blob_writer.write_roster_blob.assert_not_called()
    failed_writer.assert_called_once()
    error_dimensions = logger_mock.exception.call_args.kwargs["extra"]["custom_dimensions"]
    assert error_dimensions["event"] == "function_failed"
    assert error_dimensions["failure_blob_name"].startswith("failed/")


def test_validate_roster_schema_required_fields():
    with pytest.raises(ValueError, match="jersey_number"):
        function_app._validate_roster_schema([{"name": "Don Mattingly", "position": "1B"}] * 24)
