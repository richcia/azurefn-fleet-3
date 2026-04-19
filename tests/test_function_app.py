import logging

import pytest

import function_app
import trapi_client
from src.validator import ValidationErrorKind

pytestmark = pytest.mark.unit


def _players(count):
    return [
        {"name": f"Player {i}", "position": "P", "jersey_number": i}
        for i in range(1, count + 1)
    ]


class FakeWriter:
    def __init__(self):
        self.write_calls = []
        self.write_failed_calls = []

    def write(self, payload):
        self.write_calls.append(payload)
        blob_uri = "https://storage.example/yankees-roster/2026-04-19.json"
        logging.getLogger(__name__).info("blob_write_succeeded", extra={"blob_uri": blob_uri})
        return blob_uri

    def write_failed(self, payload):
        self.write_failed_calls.append(payload)
        return "https://storage.example/yankees-roster/failed/2026-04-19.json"


def test_timer_trigger_config_includes_schedule_and_use_monitor():
    function = next(
        item
        for item in function_app.app.get_functions()
        if item.get_function_name() == "GetAndStoreYankeesRoster"
    )
    trigger = next(binding for binding in function.get_bindings() if binding.type == "timerTrigger")

    assert trigger.schedule == "0 0 2 * * *"
    assert trigger.use_monitor is True


def test_get_and_store_yankees_roster_happy_path(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    fake_writer = FakeWriter()
    recorded = []
    players = [
        {"name": "Don Mattingly", "position": "1B", "jersey_number": 23},
        {"name": "Dave Winfield", "position": "RF", "jersey_number": 31},
        {"name": "Rickey Henderson", "position": "LF", "jersey_number": 24},
        *_players(25),
    ]
    roster_payload = {"players": players, "usage": {"total_tokens": 10}}

    def fake_fetch():
        logging.getLogger(__name__).info("trapi_request_sent")
        logging.getLogger(__name__).info(
            "trapi_response_received",
            extra={"player_count": 28, "token_count": 10, "latency_ms": 5},
        )
        return roster_payload

    monkeypatch.setattr(function_app, "BlobWriter", lambda: fake_writer)
    monkeypatch.setattr(function_app, "fetch_1985_yankees_roster", fake_fetch)
    monkeypatch.setattr(
        function_app,
        "_PLAYER_COUNT_RETURNED",
        type("Metric", (), {"record": lambda self, value: recorded.append(value)})(),
    )

    function_app.get_and_store_yankees_roster(None)

    assert fake_writer.write_calls == [roster_payload]
    assert fake_writer.write_failed_calls == []
    assert recorded == [28]
    stored_players = fake_writer.write_calls[0]["players"]
    stored_names = {player["name"] for player in stored_players}
    assert {"Don Mattingly", "Dave Winfield", "Rickey Henderson"}.issubset(stored_names)
    emitted_events = {record.message for record in caplog.records}
    assert {
        "function_started",
        "trapi_request_sent",
        "trapi_response_received",
        "blob_write_succeeded",
        "function_completed",
    }.issubset(emitted_events)


def test_get_and_store_yankees_roster_trapi_failure_path(monkeypatch):
    fake_writer = FakeWriter()

    def raise_trapi_error():
        raise RuntimeError("trapi unavailable")

    monkeypatch.setattr(function_app, "BlobWriter", lambda: fake_writer)
    monkeypatch.setattr(function_app, "fetch_1985_yankees_roster", raise_trapi_error)

    with pytest.raises(RuntimeError, match="trapi unavailable"):
        function_app.get_and_store_yankees_roster(None)

    assert fake_writer.write_calls == []
    assert fake_writer.write_failed_calls == []


def test_get_and_store_yankees_roster_validation_failure_path(monkeypatch):
    fake_writer = FakeWriter()
    invalid_payload = {"players": [{"name": "Don Mattingly"}], "usage": {"total_tokens": 5}}

    def raise_validation_error():
        raise trapi_client.RosterValidationError(
            kind=ValidationErrorKind.SCHEMA_FAILURE,
            message="players[0] missing required field: position",
            response_payload=invalid_payload,
        )

    monkeypatch.setattr(function_app, "BlobWriter", lambda: fake_writer)
    monkeypatch.setattr(function_app, "fetch_1985_yankees_roster", raise_validation_error)

    with pytest.raises(RuntimeError, match="missing required field"):
        function_app.get_and_store_yankees_roster(None)

    assert fake_writer.write_calls == []
    assert fake_writer.write_failed_calls == [invalid_payload]


def test_get_and_store_yankees_roster_direct_validation_failure_path(monkeypatch):
    fake_writer = FakeWriter()
    invalid_payload = {"players": [{"name": "Don Mattingly"}]}

    monkeypatch.setattr(function_app, "BlobWriter", lambda: fake_writer)
    monkeypatch.setattr(function_app, "fetch_1985_yankees_roster", lambda: invalid_payload)

    with pytest.raises(RuntimeError, match="missing required field"):
        function_app.get_and_store_yankees_roster(None)

    assert fake_writer.write_calls == []
    assert fake_writer.write_failed_calls == [invalid_payload]


def test_get_and_store_yankees_roster_raises_when_failed_blob_write_fails(monkeypatch):
    class FailingWriter(FakeWriter):
        def write_failed(self, payload):
            super().write_failed(payload)
            raise RuntimeError("failed blob write")

    invalid_payload = {"players": [{"name": "Don Mattingly"}]}
    monkeypatch.setattr(function_app, "BlobWriter", lambda: FailingWriter())
    monkeypatch.setattr(function_app, "fetch_1985_yankees_roster", lambda: invalid_payload)

    with pytest.raises(RuntimeError, match="failed blob write"):
        function_app.get_and_store_yankees_roster(None)


def test_normal_condition_calls_fetch_once_and_uses_sub_60_second_trapi_timeout(monkeypatch):
    fake_writer = FakeWriter()
    roster_payload = {"players": _players(24), "usage": {"total_tokens": 10}}
    fetch_calls = {"count": 0}

    def fake_fetch():
        fetch_calls["count"] += 1
        return roster_payload

    monkeypatch.setattr(function_app, "BlobWriter", lambda: fake_writer)
    monkeypatch.setattr(function_app, "fetch_1985_yankees_roster", fake_fetch)
    monkeypatch.setattr(
        function_app,
        "_PLAYER_COUNT_RETURNED",
        type("Metric", (), {"record": lambda self, value: None})(),
    )

    function_app.get_and_store_yankees_roster(None)

    assert fetch_calls["count"] == 1
    assert trapi_client.TRAPI_TIMEOUT_SECONDS <= 60
