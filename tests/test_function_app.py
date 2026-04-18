import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import function_app


def _valid_payload(player_count: int = 24):
    return {
        "players": [
            {"name": f"Player {i}", "position": "P", "jersey_number": i}
            for i in range(1, player_count + 1)
        ],
        "usage": {"total_tokens": 123},
    }


def test_timer_trigger_metadata():
    functions = function_app.app.get_functions()
    assert len(functions) == 1
    bindings = functions[0].get_bindings()
    timer = next(binding for binding in bindings if binding.type == "timerTrigger")
    assert timer.schedule == "0 0 2 * * *"
    assert timer.use_monitor is True


def test_success_path_writes_roster_and_emits_metric(monkeypatch):
    raw = json.dumps(
        {
            "usage": {"total_tokens": 123},
            "choices": [{"message": {"content": json.dumps(_valid_payload())}}],
        }
    )

    fetch_mock = MagicMock(return_value=raw)
    write_roster_mock = MagicMock(return_value="yankees-roster/2026-01-01.json")
    write_failed_mock = MagicMock()
    log_mock = MagicMock()

    monkeypatch.setattr(function_app, "fetch_roster", fetch_mock)
    monkeypatch.setattr(function_app, "write_roster", write_roster_mock)
    monkeypatch.setattr(function_app, "write_failed", write_failed_mock)
    monkeypatch.setattr(function_app, "_log_event", log_mock)

    function_app.get_and_store_yankees_roster(SimpleNamespace(past_due=False))

    fetch_mock.assert_called_once()
    write_roster_mock.assert_called_once()
    write_failed_mock.assert_not_called()

    event_names = [call.args[0] for call in log_mock.call_args_list]
    assert "function_started" in event_names
    assert "trapi_request_sent" in event_names
    assert "trapi_response_received" in event_names
    assert "blob_write_succeeded" in event_names
    assert "function_completed" in event_names
    assert "player_count_returned" in event_names


def test_invalid_response_writes_failed_blob(monkeypatch):
    raw = json.dumps(_valid_payload(player_count=10))

    monkeypatch.setattr(function_app, "fetch_roster", MagicMock(return_value=raw))
    monkeypatch.setattr(function_app, "write_roster", MagicMock())
    write_failed_mock = MagicMock(return_value=f"yankees-roster/failed/{date.today().isoformat()}.json")
    monkeypatch.setattr(function_app, "write_failed", write_failed_mock)
    log_mock = MagicMock()
    monkeypatch.setattr(function_app, "_log_event", log_mock)

    function_app.get_and_store_yankees_roster(SimpleNamespace(past_due=False))

    write_failed_mock.assert_called_once()
    event_names = [call.args[0] for call in log_mock.call_args_list]
    assert "blob_write_succeeded" in event_names
    assert "function_completed" in event_names


def test_empty_choices_writes_failed_blob(monkeypatch):
    raw = json.dumps({"choices": []})

    monkeypatch.setattr(function_app, "fetch_roster", MagicMock(return_value=raw))
    monkeypatch.setattr(function_app, "write_roster", MagicMock())
    write_failed_mock = MagicMock(return_value="yankees-roster/failed/2026-01-01.json")
    monkeypatch.setattr(function_app, "write_failed", write_failed_mock)
    log_mock = MagicMock()
    monkeypatch.setattr(function_app, "_log_event", log_mock)

    function_app.get_and_store_yankees_roster(SimpleNamespace(past_due=False))

    write_failed_mock.assert_called_once_with(raw, write_failed_mock.call_args.args[1])
    event_names = [call.args[0] for call in log_mock.call_args_list]
    assert "trapi_response_received" in event_names
    assert "blob_write_succeeded" in event_names


def test_trapi_exception_writes_failed_blob_and_reraises(monkeypatch):
    error = RuntimeError("boom")
    error.response = SimpleNamespace(text='{"error":"failed"}')
    monkeypatch.setattr(function_app, "fetch_roster", MagicMock(side_effect=error))
    write_failed_mock = MagicMock(return_value="yankees-roster/failed/2026-01-01.json")
    log_mock = MagicMock()
    monkeypatch.setattr(function_app, "write_failed", write_failed_mock)
    monkeypatch.setattr(function_app, "_log_event", log_mock)

    try:
        function_app.get_and_store_yankees_roster(SimpleNamespace(past_due=False))
        assert False, "expected exception"
    except RuntimeError:
        pass

    write_failed_mock.assert_called_once_with('{"error":"failed"}', write_failed_mock.call_args.args[1])
    event_names = [call.args[0] for call in log_mock.call_args_list]
    assert "trapi_response_received" in event_names
