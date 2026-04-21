from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

import pytest
import requests

import trapi_client


def _build_players(count: int) -> list[dict[str, object]]:
    return [
        {
            "name": f"Player {i}",
            "position": "P",
            "jersey_number": i,
        }
        for i in range(1, count + 1)
    ]


@dataclass
class _MockResponse:
    status_code: int
    payload: Any
    json_error: bool = False

    def json(self) -> Any:
        if self.json_error:
            raise ValueError("invalid json")
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


def test_fetch_retries_on_429_with_backoff_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    success_payload = {"players": _build_players(24), "usage": {"total_tokens": 321}}
    responses = [
        _MockResponse(status_code=429, payload={"error": "too many requests"}),
        _MockResponse(status_code=200, payload=success_payload),
    ]
    post = Mock(side_effect=responses)
    sleep = Mock()

    monkeypatch.setattr(trapi_client, "_load_prompt", Mock(return_value="prompt"))
    monkeypatch.setattr(trapi_client, "_get_bearer_token", Mock(return_value="token"))
    monkeypatch.setattr(trapi_client, "_build_url", Mock(return_value="https://example.test"))
    monkeypatch.setattr(trapi_client.random, "uniform", Mock(return_value=0.25))
    monkeypatch.setattr(trapi_client.time, "sleep", sleep)
    monkeypatch.setattr(trapi_client.requests, "post", post)

    result = trapi_client.fetch_1985_yankees_roster()

    assert result == success_payload
    assert post.call_count == 2
    sleep.assert_called_once_with(1.25)


def test_fetch_401_raises_immediately_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    post = Mock(side_effect=[_MockResponse(status_code=401, payload={"error": "unauthorized"})])
    sleep = Mock()

    monkeypatch.setattr(trapi_client, "_load_prompt", Mock(return_value="prompt"))
    monkeypatch.setattr(trapi_client, "_get_bearer_token", Mock(return_value="token"))
    monkeypatch.setattr(trapi_client, "_build_url", Mock(return_value="https://example.test"))
    monkeypatch.setattr(trapi_client.time, "sleep", sleep)
    monkeypatch.setattr(trapi_client.requests, "post", post)

    with pytest.raises(requests.HTTPError):
        trapi_client.fetch_1985_yankees_roster()

    assert post.call_count == 1
    sleep.assert_not_called()


def test_fetch_raises_retry_exhausted_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    post = Mock(
        side_effect=[
            _MockResponse(status_code=429, payload=None, json_error=True),
            _MockResponse(status_code=429, payload=None, json_error=True),
            _MockResponse(status_code=429, payload=None, json_error=True),
            _MockResponse(status_code=429, payload=None, json_error=True),
        ]
    )
    sleep = Mock()

    monkeypatch.setattr(trapi_client, "_load_prompt", Mock(return_value="prompt"))
    monkeypatch.setattr(trapi_client, "_get_bearer_token", Mock(return_value="token"))
    monkeypatch.setattr(trapi_client, "_build_url", Mock(return_value="https://example.test"))
    monkeypatch.setattr(trapi_client.random, "uniform", Mock(return_value=0.0))
    monkeypatch.setattr(trapi_client.time, "sleep", sleep)
    monkeypatch.setattr(trapi_client.requests, "post", post)

    with pytest.raises(trapi_client.TRAPIRetryExhaustedError) as exc_info:
        trapi_client.fetch_1985_yankees_roster()

    assert exc_info.value.status_code == 429
    assert exc_info.value.retries == trapi_client.TRAPI_MAX_RETRIES
    assert exc_info.value.response_payload == {"status_code": 429}
    assert post.call_count == trapi_client.TRAPI_MAX_RETRIES + 1
    assert sleep.call_count == trapi_client.TRAPI_MAX_RETRIES
    assert [call.args[0] for call in sleep.call_args_list] == [1.0, 2.0, 4.0]


def test_prompt_loading_normalization_and_hashing(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("\n Return JSON only.   \nList players now.   \n", encoding="utf-8")
    monkeypatch.setattr(trapi_client, "PROMPT_PATH", prompt_file)

    prompt_text = trapi_client._load_prompt()
    prompt_hash = trapi_client._prompt_hash(prompt_text)

    assert prompt_text == "Return JSON only.\nList players now."
    assert prompt_hash == hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
