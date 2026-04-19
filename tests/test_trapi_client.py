import logging
import types

import pytest

import trapi_client
from src.validator import ValidationErrorKind

pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._payload


def _players(count):
    return [
        {"name": f"Player {i}", "position": "P", "jersey_number": i}
        for i in range(1, count + 1)
    ]


@pytest.fixture
def configure_env(monkeypatch):
    monkeypatch.setattr(trapi_client, "TRAPI_ENDPOINT", "https://trapi.example")
    monkeypatch.setattr(trapi_client, "TRAPI_DEPLOYMENT_NAME", "gpt-4o-2026-01-01")
    monkeypatch.setattr(trapi_client, "TRAPI_API_VERSION", "2025-04-01-preview")
    monkeypatch.setattr(trapi_client, "TRAPI_AUTH_SCOPE", "api://trapi/.default")


def test_fetch_roster_uses_prompt_file_timeout_scope_and_logs(monkeypatch, configure_env, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        types.SimpleNamespace(get_token=lambda scope: types.SimpleNamespace(token="token") if scope == "api://trapi/.default" else None),
    )
    monkeypatch.setattr(trapi_client.time, "perf_counter", lambda: 1.0)

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            200,
            {"players": _players(24), "usage": {"total_tokens": 321}},
        )

    monkeypatch.setattr(trapi_client.requests, "post", fake_post)

    response = trapi_client.fetch_1985_yankees_roster()

    assert response["players"][0]["name"] == "Player 1"
    assert captured["timeout"] == 45
    assert captured["json"]["messages"][0]["content"] == trapi_client._load_prompt()
    assert captured["json"]["model"] == "gpt-4o-2026-01-01"
    assert (
        captured["url"]
        == "https://trapi.example/openai/deployments/gpt-4o-2026-01-01/chat/completions?api-version=2025-04-01-preview"
    )
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert any(r.message == "trapi_request_sent" for r in caplog.records)
    received = next(r for r in caplog.records if r.message == "trapi_response_received")
    assert received.model_version == "gpt-4o-2026-01-01"
    assert received.prompt_hash == trapi_client._prompt_hash(trapi_client._load_prompt())
    assert received.token_count == 321
    assert received.player_count == 24


def test_fetch_roster_retries_with_exponential_backoff(monkeypatch, configure_env):
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        types.SimpleNamespace(get_token=lambda _: types.SimpleNamespace(token="token")),
    )

    statuses = [429, 500, 503, 200]
    calls = {"count": 0}
    sleeps = []

    def fake_post(*_, **__):
        status = statuses[calls["count"]]
        calls["count"] += 1
        if status == 200:
            return FakeResponse(200, {"players": _players(24), "usage": {"total_tokens": 77}})
        return FakeResponse(status, {})

    monkeypatch.setattr(trapi_client.requests, "post", fake_post)
    monkeypatch.setattr(trapi_client.time, "sleep", lambda s: sleeps.append(s))

    response = trapi_client.fetch_1985_yankees_roster()

    assert response["players"][0]["name"] == "Player 1"
    assert calls["count"] == 4
    assert sleeps == [1, 2, 4]


def test_fetch_roster_raises_after_retry_exhaustion(monkeypatch, configure_env):
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        types.SimpleNamespace(get_token=lambda _: types.SimpleNamespace(token="token")),
    )
    monkeypatch.setattr(trapi_client.requests, "post", lambda *_, **__: FakeResponse(503, {}))
    monkeypatch.setattr(trapi_client.time, "sleep", lambda *_: None)

    with pytest.raises(RuntimeError, match="http 503"):
        trapi_client.fetch_1985_yankees_roster()


def test_fetch_roster_does_not_retry_non_retryable_status(monkeypatch, configure_env):
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        types.SimpleNamespace(get_token=lambda _: types.SimpleNamespace(token="token")),
    )
    calls = {"count": 0}

    def fake_post(*_, **__):
        calls["count"] += 1
        return FakeResponse(400, {})

    monkeypatch.setattr(trapi_client.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="http 400"):
        trapi_client.fetch_1985_yankees_roster()

    assert calls["count"] == 1


def test_fetch_roster_raises_typed_validation_error(monkeypatch, configure_env):
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        types.SimpleNamespace(get_token=lambda _: types.SimpleNamespace(token="token")),
    )
    monkeypatch.setattr(
        trapi_client.requests,
        "post",
        lambda *_, **__: FakeResponse(200, {"players": [{"name": "Don Mattingly"}], "usage": {"total_tokens": 5}}),
    )

    with pytest.raises(trapi_client.RosterValidationError) as exc:
        trapi_client.fetch_1985_yankees_roster()

    assert exc.value.kind == ValidationErrorKind.SCHEMA_FAILURE
    assert exc.value.response_payload == {"players": [{"name": "Don Mattingly"}], "usage": {"total_tokens": 5}}


def test_fetch_roster_raises_typed_validation_error_for_non_object_payload(monkeypatch, configure_env):
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        types.SimpleNamespace(get_token=lambda _: types.SimpleNamespace(token="token")),
    )
    monkeypatch.setattr(
        trapi_client.requests,
        "post",
        lambda *_, **__: FakeResponse(200, ["not-an-object"]),
    )

    with pytest.raises(trapi_client.RosterValidationError) as exc:
        trapi_client.fetch_1985_yankees_roster()

    assert exc.value.kind == ValidationErrorKind.SCHEMA_FAILURE
    assert exc.value.response_payload == ["not-an-object"]
