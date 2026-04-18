import pytest

import function_app
from validator import ValidationResult


class TimerStub:
    def __init__(self, past_due=False):
        self.past_due = past_due


def _valid_payload():
    return {
        "players": [
            {"name": "Don Mattingly", "position": "1B", "jersey_number": 23},
            {"name": "Dave Winfield", "position": "RF", "jersey_number": 31},
            {"name": "Rickey Henderson", "position": "LF", "jersey_number": 24},
        ]
    }


def test_timer_trigger_schedule_and_use_monitor_configuration():
    fn = next(f for f in function_app.app.get_functions() if f.get_function_name() == "GetAndStoreYankeesRoster")
    trigger_binding = next(b for b in fn.get_bindings() if b.type == "timerTrigger")

    assert trigger_binding.schedule == "0 0 2 * * *"
    assert trigger_binding.use_monitor is True


def test_get_and_store_yankees_roster_success_logs_key_events(monkeypatch):
    payload = _valid_payload()
    events = []

    monkeypatch.setattr(function_app, "fetch_roster", lambda: (payload, 123))
    monkeypatch.setattr(
        function_app,
        "validate",
        lambda response: ValidationResult(is_valid=True, player_count=len(response["players"])),
    )
    monkeypatch.setattr(function_app, "write_roster_blob", lambda response, result: "https://storage/yankees-roster/2026-04-18.json")
    monkeypatch.setattr(function_app.LOGGER, "info", lambda _message, extra: events.append(extra))

    function_app.get_and_store_yankees_roster(TimerStub(past_due=False))

    event_names = [event["event"] for event in events]
    assert "function_started" in event_names
    assert "trapi_response_received" in event_names
    assert "function_completed" in event_names
    trapi_event = next(event for event in events if event["event"] == "trapi_response_received")
    assert trapi_event["player_count"] == len(payload["players"])
    assert isinstance(trapi_event["latency_ms"], int)
    assert trapi_event["token_count"] == 123


def test_get_and_store_yankees_roster_raises_on_validation_failure(monkeypatch):
    payload = {"players": []}

    monkeypatch.setattr(function_app, "fetch_roster", lambda: (payload, 0))
    monkeypatch.setattr(
        function_app,
        "validate",
        lambda _response: ValidationResult(
            is_valid=False,
            player_count=0,
            error_message="missing required players",
            error_code="missing_required_players",
        ),
    )

    write_calls = {}

    def fake_write_roster_blob(response, result):
        write_calls["response"] = response
        write_calls["result"] = result
        return "https://storage/yankees-roster/failed/2026-04-18.json"

    monkeypatch.setattr(function_app, "write_roster_blob", fake_write_roster_blob)

    with pytest.raises(RuntimeError, match="Roster validation failed"):
        function_app.get_and_store_yankees_roster(TimerStub(past_due=True))

    assert write_calls["response"] == payload
    assert write_calls["result"].is_valid is False


def test_get_and_store_yankees_roster_emits_player_count_metric_on_success(monkeypatch):
    payload = _valid_payload()
    metric_calls = []

    monkeypatch.setattr(function_app, "fetch_roster", lambda: (payload, 123))
    monkeypatch.setattr(
        function_app,
        "validate",
        lambda response: ValidationResult(is_valid=True, player_count=len(response["players"])),
    )
    monkeypatch.setattr(function_app, "write_roster_blob", lambda response, result: "https://storage/yankees-roster/2026-04-18.json")
    monkeypatch.setattr(function_app.LOGGER, "info", lambda _message, extra: None)

    class CounterStub:
        def add(self, value):
            metric_calls.append(value)

    monkeypatch.setattr(function_app, "_PLAYER_COUNT_RETURNED_COUNTER", CounterStub())

    function_app.get_and_store_yankees_roster(TimerStub(past_due=False))

    assert metric_calls == [len(payload["players"])]


def test_get_and_store_yankees_roster_does_not_emit_player_count_metric_on_validation_failure(monkeypatch):
    payload = {"players": []}
    metric_calls = []

    monkeypatch.setattr(function_app, "fetch_roster", lambda: (payload, 0))
    monkeypatch.setattr(
        function_app,
        "validate",
        lambda _response: ValidationResult(
            is_valid=False,
            player_count=0,
            error_message="missing required players",
            error_code="missing_required_players",
        ),
    )
    monkeypatch.setattr(function_app, "write_roster_blob", lambda _response, _result: "https://storage/yankees-roster/failed/2026-04-18.json")

    class CounterStub:
        def add(self, value):
            metric_calls.append(value)

    monkeypatch.setattr(function_app, "_PLAYER_COUNT_RETURNED_COUNTER", CounterStub())

    with pytest.raises(RuntimeError, match="Roster validation failed"):
        function_app.get_and_store_yankees_roster(TimerStub(past_due=True))

    assert metric_calls == []
