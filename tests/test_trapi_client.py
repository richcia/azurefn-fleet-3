import json
from types import SimpleNamespace

import pytest

import trapi_client


class DummyResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def _set_required_env(monkeypatch):
    monkeypatch.setenv("TRAPI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("TRAPI_DEPLOYMENT_NAME", "gpt-4o")
    monkeypatch.setenv("TRAPI_API_VERSION", "2024-02-01")


def test_fetch_roster_uses_timeout_and_parses_json(monkeypatch):
    _set_required_env(monkeypatch)

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyResponse(
            200,
            {"choices": [{"message": {"content": '{"players":[{"name":"Don Mattingly","position":"1B","jersey_number":23}]}'}}]},
        )

    monkeypatch.setattr(trapi_client.requests, "post", fake_post)
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        SimpleNamespace(get_token=lambda scope: SimpleNamespace(token=f"token-for-{scope}")),
    )

    roster = trapi_client.fetch_roster()

    assert captured["timeout"] == 45
    assert captured["url"].endswith("/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-01")
    assert captured["headers"]["Authorization"].startswith("Bearer token-for-")
    assert roster["players"][0]["name"] == "Don Mattingly"


@pytest.mark.parametrize("status_code", [429, 500, 502, 503])
def test_fetch_roster_retries_transient_status_with_exponential_backoff(monkeypatch, status_code):
    _set_required_env(monkeypatch)

    responses = [
        DummyResponse(status_code, {"error": "transient error"}),
        DummyResponse(status_code, {"error": "transient error"}),
        DummyResponse(200, {"choices": [{"message": {"content": '{"players":[]}'}}]}),
    ]
    sleeps = []

    def fake_post(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(trapi_client.requests, "post", fake_post)
    monkeypatch.setattr(trapi_client.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        SimpleNamespace(get_token=lambda scope: SimpleNamespace(token="token")),
    )

    result = trapi_client.fetch_roster()

    assert result == {"players": []}
    assert sleeps == [1, 2]


def test_fetch_roster_logs_prompt_hash_each_request(monkeypatch):
    _set_required_env(monkeypatch)

    calls = []

    def fake_info(message, extra):
        calls.append((message, extra))

    monkeypatch.setattr(trapi_client.LOGGER, "info", fake_info)
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        SimpleNamespace(get_token=lambda scope: SimpleNamespace(token="token")),
    )
    monkeypatch.setattr(
        trapi_client.requests,
        "post",
        lambda *args, **kwargs: DummyResponse(200, {"choices": [{"message": {"content": json.dumps({"players": []})}}]}),
    )

    trapi_client.fetch_roster()

    assert calls
    assert all("prompt_sha256" in extra for _, extra in calls)
    assert all(extra["event"] == "trapi_request_sent" for _, extra in calls)


def test_fetch_roster_logs_prompt_hash_for_each_retry_attempt(monkeypatch):
    _set_required_env(monkeypatch)

    logs = []
    responses = [
        DummyResponse(429, {"error": "retry"}),
        DummyResponse(200, {"choices": [{"message": {"content": json.dumps({"players": []})}}]}),
    ]

    monkeypatch.setattr(trapi_client.LOGGER, "info", lambda message, extra: logs.append(extra))
    monkeypatch.setattr(trapi_client.requests, "post", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr(trapi_client.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        SimpleNamespace(get_token=lambda scope: SimpleNamespace(token="token")),
    )

    trapi_client.fetch_roster()

    assert len(logs) == 2
    assert all("prompt_sha256" in extra for extra in logs)
    assert all(extra["event"] == "trapi_request_sent" for extra in logs)
    assert logs[0]["prompt_sha256"] == logs[1]["prompt_sha256"]


def test_default_azure_credential_token_scope(monkeypatch):
    monkeypatch.delenv("TRAPI_AUTH_SCOPE", raising=False)
    seen = {}

    def fake_get_token(scope):
        seen["scope"] = scope
        return SimpleNamespace(token="abc")

    monkeypatch.setattr(trapi_client, "_DEFAULT_AZURE_CREDENTIAL", SimpleNamespace(get_token=fake_get_token))
    token = trapi_client._get_bearer_token()

    assert token == "abc"
    assert seen["scope"] == "https://cognitiveservices.azure.com/.default"


def test_custom_trapi_auth_scope_from_env(monkeypatch):
    monkeypatch.setenv("TRAPI_AUTH_SCOPE", "api://trapi/.default")
    seen = {}

    def fake_get_token(scope):
        seen["scope"] = scope
        return SimpleNamespace(token="abc")

    monkeypatch.setattr(trapi_client, "_DEFAULT_AZURE_CREDENTIAL", SimpleNamespace(get_token=fake_get_token))
    token = trapi_client._get_bearer_token()

    assert token == "abc"
    assert seen["scope"] == "api://trapi/.default"


def test_empty_trapi_auth_scope_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("TRAPI_AUTH_SCOPE", "   ")
    seen = {}

    def fake_get_token(scope):
        seen["scope"] = scope
        return SimpleNamespace(token="abc")

    monkeypatch.setattr(trapi_client, "_DEFAULT_AZURE_CREDENTIAL", SimpleNamespace(get_token=fake_get_token))
    token = trapi_client._get_bearer_token()

    assert token == "abc"
    assert seen["scope"] == "https://cognitiveservices.azure.com/.default"


def test_prompt_is_loaded_from_runtime_path(monkeypatch, tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text(
        "model: gpt-4o-2024-05-13\n\nsystem:\nSystem text\n\nuser:\nUser text",
        encoding="utf-8",
    )
    monkeypatch.setattr(trapi_client, "PROMPT_TEMPLATE_PATH", prompt_file)

    prompt = trapi_client._load_prompt_template()

    assert prompt["model"] == "gpt-4o-2024-05-13"
    assert prompt["system"] == "System text"
    assert prompt["user"] == "User text"


def test_default_prompt_path_points_to_repo_prompt_file():
    assert trapi_client.PROMPT_TEMPLATE_PATH.name == "get_1985_yankees.txt"
    assert trapi_client.PROMPT_TEMPLATE_PATH.parent.name == "prompts"
    assert trapi_client.PROMPT_TEMPLATE_PATH.exists()


def test_prompt_with_crlf_line_endings_is_loaded(monkeypatch, tmp_path):
    prompt_file = tmp_path / "prompt-crlf.txt"
    prompt_file.write_bytes(
        b"model: gpt-4o-2024-05-13\r\n\r\nsystem:\r\nSystem text\r\n\r\nuser:\r\nUser text"
    )
    monkeypatch.setattr(trapi_client, "PROMPT_TEMPLATE_PATH", prompt_file)

    prompt = trapi_client._load_prompt_template()

    assert prompt["model"] == "gpt-4o-2024-05-13"
    assert prompt["system"] == "System text"
    assert prompt["user"] == "User text"


def test_prompt_with_cr_only_line_endings_is_loaded(monkeypatch, tmp_path):
    prompt_file = tmp_path / "prompt-cr.txt"
    prompt_file.write_bytes(
        b"model: gpt-4o-2024-05-13\r\rsystem:\rSystem text\r\ruser:\rUser text"
    )
    monkeypatch.setattr(trapi_client, "PROMPT_TEMPLATE_PATH", prompt_file)

    prompt = trapi_client._load_prompt_template()

    assert prompt["model"] == "gpt-4o-2024-05-13"
    assert prompt["system"] == "System text"
    assert prompt["user"] == "User text"


def test_fetch_roster_retries_on_timeout(monkeypatch):
    _set_required_env(monkeypatch)

    attempts = {"count": 0}
    sleeps = []

    def fake_post(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise trapi_client.requests.Timeout("timeout")
        return DummyResponse(200, {"choices": [{"message": {"content": '{"players":[]}'}}]})

    monkeypatch.setattr(trapi_client.requests, "post", fake_post)
    monkeypatch.setattr(trapi_client.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        SimpleNamespace(get_token=lambda scope: SimpleNamespace(token="token")),
    )

    assert trapi_client.fetch_roster() == {"players": []}
    assert sleeps == [1, 2]


def test_fetch_roster_raises_for_non_transient_http_error(monkeypatch):
    _set_required_env(monkeypatch)

    monkeypatch.setattr(trapi_client.requests, "post", lambda *args, **kwargs: DummyResponse(400, {"error": "bad request"}))
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        SimpleNamespace(get_token=lambda scope: SimpleNamespace(token="token")),
    )

    with pytest.raises(Exception, match="HTTP 400"):
        trapi_client.fetch_roster()


@pytest.mark.parametrize("status_code", [429, 500, 502, 503])
def test_fetch_roster_retries_exhausted_raises_http_error(monkeypatch, status_code):
    _set_required_env(monkeypatch)

    sleeps = []
    monkeypatch.setattr(
        trapi_client.requests,
        "post",
        lambda *args, **kwargs: DummyResponse(status_code, {"error": "transient error"}),
    )
    monkeypatch.setattr(trapi_client.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(
        trapi_client,
        "_DEFAULT_AZURE_CREDENTIAL",
        SimpleNamespace(get_token=lambda scope: SimpleNamespace(token="token")),
    )

    with pytest.raises(Exception, match=f"HTTP {status_code}"):
        trapi_client.fetch_roster()

    assert sleeps == [1, 2, 4]
