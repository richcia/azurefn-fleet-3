from pathlib import Path
from unittest.mock import MagicMock

import requests

import trapi_client


class _Response:
    def __init__(self, status_code=200, text='{"ok": true}'):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError("http error")
            err.response = self
            raise err


def test_fetch_roster_success(monkeypatch, tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("hello", encoding="utf-8")

    monkeypatch.setenv("TRAPI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("TRAPI_DEPLOYMENT_NAME", "gpt-4o")
    monkeypatch.setenv("TRAPI_API_VERSION", "2024-02-01")
    monkeypatch.setattr(trapi_client, "_get_bearer_token", lambda: "token")

    post = MagicMock(return_value=_Response())
    monkeypatch.setattr(trapi_client.requests, "post", post)

    result = trapi_client.fetch_roster(str(prompt))

    assert result == '{"ok": true}'
    assert post.call_args.kwargs["timeout"] == 45


def test_fetch_roster_retries_on_timeout(monkeypatch, tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("hello", encoding="utf-8")

    monkeypatch.setenv("TRAPI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setattr(trapi_client, "_get_bearer_token", lambda: "token")

    attempts = {"count": 0}

    def _post(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 4:
            raise requests.Timeout("timeout")
        return _Response()

    monkeypatch.setattr(trapi_client.requests, "post", _post)
    monkeypatch.setattr(trapi_client.time, "sleep", lambda _: None)

    result = trapi_client.fetch_roster(str(prompt))
    assert result == '{"ok": true}'
    assert attempts["count"] == 4


def test_fetch_roster_does_not_retry_4xx(monkeypatch, tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("hello", encoding="utf-8")

    monkeypatch.setenv("TRAPI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setattr(trapi_client, "_get_bearer_token", lambda: "token")

    def _post(*args, **kwargs):
        return _Response(status_code=400)

    monkeypatch.setattr(trapi_client.requests, "post", _post)

    try:
        trapi_client.fetch_roster(str(prompt))
        assert False, "expected HTTPError"
    except requests.HTTPError:
        pass
