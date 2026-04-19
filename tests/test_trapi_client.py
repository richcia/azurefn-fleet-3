import logging
import types

import pytest

import trapi_client


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._payload


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
            {"players": [{"name": "Don Mattingly"}], "usage": {"total_tokens": 321}},
        )

    monkeypatch.setattr(trapi_client.requests, "post", fake_post)

    response = trapi_client.fetch_1985_yankees_roster()

    assert response["players"][0]["name"] == "Don Mattingly"
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
    assert received.player_count == 1


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
            return FakeResponse(200, {"players": [{"name": "Dave Winfield"}], "usage": {"total_tokens": 77}})
        return FakeResponse(status, {})

    monkeypatch.setattr(trapi_client.requests, "post", fake_post)
    monkeypatch.setattr(trapi_client.time, "sleep", lambda s: sleeps.append(s))

    response = trapi_client.fetch_1985_yankees_roster()

    assert response["players"][0]["name"] == "Dave Winfield"
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
