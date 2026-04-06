"""Unit tests for trapi_client.py.

Covers:
- Successful response parsing
- Empty response handling
- HTTP 429 retry logic
- HTTP 500 error propagation
- Missing environment variable errors
"""

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import requests

import trapi_client


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

PLAYERS = ["Rickey Henderson", "Don Mattingly", "Dave Winfield", "Ron Guidry"]


def _make_response(status_code: int, content: str | None = None) -> MagicMock:
    """Build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    if content is not None:
        resp.json.return_value = {
            "choices": [
                {"message": {"content": content}}
            ]
        }
    if status_code != 200:
        http_err = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


def _env(monkeypatch):
    monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com/chat")
    monkeypatch.setenv("TRAPI_SCOPE", "api://trapi/.default")


# ---------------------------------------------------------------------------
# Tests: environment variable validation
# ---------------------------------------------------------------------------

def test_missing_endpoint_raises(monkeypatch):
    monkeypatch.delenv("TRAPI_ENDPOINT", raising=False)
    monkeypatch.setenv("TRAPI_SCOPE", "api://trapi/.default")
    with pytest.raises(EnvironmentError, match="TRAPI_ENDPOINT"):
        trapi_client.get_roster()


def test_missing_scope_raises(monkeypatch):
    monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com/chat")
    monkeypatch.delenv("TRAPI_SCOPE", raising=False)
    with pytest.raises(EnvironmentError, match="TRAPI_SCOPE"):
        trapi_client.get_roster()


# ---------------------------------------------------------------------------
# Tests: successful response parsing
# ---------------------------------------------------------------------------

def test_successful_response_returns_player_list(monkeypatch):
    _env(monkeypatch)
    ok_resp = _make_response(200, json.dumps(PLAYERS))

    with patch("trapi_client.DefaultAzureCredential") as mock_cred, \
         patch("trapi_client.requests.post", return_value=ok_resp):
        mock_cred.return_value.get_token.return_value.token = "fake-token"
        result = trapi_client.get_roster()

    assert result == PLAYERS


def test_parse_response_returns_list_of_strings():
    data = {
        "choices": [
            {"message": {"content": json.dumps(["Alice", "Bob"])}}
        ]
    }
    result = trapi_client._parse_response(data)
    assert result == ["Alice", "Bob"]


# ---------------------------------------------------------------------------
# Tests: empty response handling
# ---------------------------------------------------------------------------

def test_empty_content_returns_empty_list(monkeypatch):
    _env(monkeypatch)
    ok_resp = _make_response(200, "")

    with patch("trapi_client.DefaultAzureCredential") as mock_cred, \
         patch("trapi_client.requests.post", return_value=ok_resp):
        mock_cred.return_value.get_token.return_value.token = "fake-token"
        result = trapi_client.get_roster()

    assert result == []


def test_parse_response_empty_content_returns_empty_list():
    data = {"choices": [{"message": {"content": ""}}]}
    assert trapi_client._parse_response(data) == []


def test_empty_json_array_response(monkeypatch):
    _env(monkeypatch)
    ok_resp = _make_response(200, "[]")

    with patch("trapi_client.DefaultAzureCredential") as mock_cred, \
         patch("trapi_client.requests.post", return_value=ok_resp):
        mock_cred.return_value.get_token.return_value.token = "fake-token"
        result = trapi_client.get_roster()

    assert result == []


# ---------------------------------------------------------------------------
# Tests: HTTP 429 retry
# ---------------------------------------------------------------------------

def test_http_429_retries_and_succeeds(monkeypatch):
    _env(monkeypatch)
    rate_limit_resp = _make_response(429)
    ok_resp = _make_response(200, json.dumps(PLAYERS))

    with patch("trapi_client.DefaultAzureCredential") as mock_cred, \
         patch("trapi_client.requests.post", side_effect=[rate_limit_resp, ok_resp]), \
         patch("trapi_client.time.sleep"):
        mock_cred.return_value.get_token.return_value.token = "fake-token"
        result = trapi_client.get_roster(max_retries=3)

    assert result == PLAYERS


def test_http_429_exhausts_retries_raises(monkeypatch):
    _env(monkeypatch)
    rate_limit_resp = _make_response(429)

    with patch("trapi_client.DefaultAzureCredential") as mock_cred, \
         patch("trapi_client.requests.post", return_value=rate_limit_resp), \
         patch("trapi_client.time.sleep"):
        mock_cred.return_value.get_token.return_value.token = "fake-token"
        with pytest.raises(RuntimeError, match="failed after"):
            trapi_client.get_roster(max_retries=2)


# ---------------------------------------------------------------------------
# Tests: HTTP 500 error propagation
# ---------------------------------------------------------------------------

def test_http_500_raises_immediately(monkeypatch):
    _env(monkeypatch)
    server_err_resp = _make_response(500)

    with patch("trapi_client.DefaultAzureCredential") as mock_cred, \
         patch("trapi_client.requests.post", return_value=server_err_resp):
        mock_cred.return_value.get_token.return_value.token = "fake-token"
        with pytest.raises(requests.HTTPError):
            trapi_client.get_roster()


# ---------------------------------------------------------------------------
# Tests: malformed response handling
# ---------------------------------------------------------------------------

def test_parse_response_invalid_json_raises():
    data = {"choices": [{"message": {"content": "not json"}}]}
    with pytest.raises(RuntimeError, match="Could not parse JSON"):
        trapi_client._parse_response(data)


def test_parse_response_non_array_raises():
    data = {"choices": [{"message": {"content": '{"key": "value"}'}}]}
    with pytest.raises(RuntimeError, match="Expected a JSON array"):
        trapi_client._parse_response(data)


def test_parse_response_missing_choices_raises():
    with pytest.raises(RuntimeError, match="Unexpected TRAPI response structure"):
        trapi_client._parse_response({})


# ---------------------------------------------------------------------------
# Tests: network / request exception retry
# ---------------------------------------------------------------------------

def test_request_exception_retries_then_raises(monkeypatch):
    _env(monkeypatch)
    with patch("trapi_client.DefaultAzureCredential") as mock_cred, \
         patch("trapi_client.requests.post", side_effect=requests.ConnectionError("connection refused")), \
         patch("trapi_client.time.sleep"):
        mock_cred.return_value.get_token.return_value.token = "fake-token"
        with pytest.raises(RuntimeError, match="failed after"):
            trapi_client.get_roster(max_retries=1)
