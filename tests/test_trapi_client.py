"""
Unit tests for trapi_client.py.

All external calls (DefaultAzureCredential, requests.post) are mocked so that
the tests run without real Azure credentials or network access.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
import requests

import trapi_client


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_ROSTER = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Rickey Henderson", "position": "LF"},
]

SAMPLE_RESPONSE_JSON = {
    "choices": [
        {
            "message": {
                "content": json.dumps(SAMPLE_ROSTER),
            }
        }
    ]
}


def _make_mock_response(data: dict, status_code: int = 200) -> MagicMock:
    """Return a mock that behaves like a requests.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = data
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# Tests for _get_access_token
# ---------------------------------------------------------------------------


class TestGetAccessToken:
    @patch("trapi_client.DefaultAzureCredential")
    def test_returns_token_string(self, mock_cred_cls):
        mock_token = MagicMock()
        mock_token.token = "fake-token-abc"
        mock_cred_cls.return_value.get_token.return_value = mock_token

        token = trapi_client._get_access_token()

        assert token == "fake-token-abc"
        mock_cred_cls.return_value.get_token.assert_called_once_with(
            trapi_client._DEFAULT_TOKEN_SCOPE
        )

    @patch("trapi_client.DefaultAzureCredential")
    def test_uses_env_scope(self, mock_cred_cls, monkeypatch):
        monkeypatch.setenv("TRAPI_TOKEN_SCOPE", "api://custom/.default")
        mock_token = MagicMock()
        mock_token.token = "scoped-token"
        mock_cred_cls.return_value.get_token.return_value = mock_token

        token = trapi_client._get_access_token()

        assert token == "scoped-token"
        mock_cred_cls.return_value.get_token.assert_called_once_with(
            "api://custom/.default"
        )

    @patch("trapi_client.DefaultAzureCredential")
    def test_explicit_scope_overrides_env(self, mock_cred_cls, monkeypatch):
        monkeypatch.setenv("TRAPI_TOKEN_SCOPE", "api://env/.default")
        mock_token = MagicMock()
        mock_token.token = "explicit-token"
        mock_cred_cls.return_value.get_token.return_value = mock_token

        token = trapi_client._get_access_token(scope="api://explicit/.default")

        assert token == "explicit-token"
        mock_cred_cls.return_value.get_token.assert_called_once_with(
            "api://explicit/.default"
        )


# ---------------------------------------------------------------------------
# Tests for _call_trapi
# ---------------------------------------------------------------------------


class TestCallTrapi:
    @patch("trapi_client.requests.post")
    def test_returns_content_on_success(self, mock_post):
        mock_post.return_value = _make_mock_response(SAMPLE_RESPONSE_JSON)

        content = trapi_client._call_trapi(
            "https://trapi.example.com/openai/deployments/gpt-4o/chat/completions",
            "my-token",
            trapi_client.PROMPT,
        )

        assert content == json.dumps(SAMPLE_ROSTER)

    @patch("trapi_client.requests.post")
    def test_raises_on_http_error(self, mock_post):
        mock_post.return_value = _make_mock_response({}, status_code=401)

        with pytest.raises(requests.HTTPError):
            trapi_client._call_trapi(
                "https://trapi.example.com/endpoint",
                "bad-token",
                "prompt",
            )

    @patch("trapi_client.requests.post")
    def test_sends_correct_headers_and_payload(self, mock_post):
        mock_post.return_value = _make_mock_response(SAMPLE_RESPONSE_JSON)

        trapi_client._call_trapi(
            "https://trapi.example.com/endpoint",
            "bearer-token-xyz",
            "Tell me something",
        )

        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer bearer-token-xyz"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["json"]["model"] == "gpt-4o"
        assert kwargs["json"]["messages"][0]["content"] == "Tell me something"
        assert kwargs["timeout"] == 60


# ---------------------------------------------------------------------------
# Tests for _parse_roster
# ---------------------------------------------------------------------------


class TestParseRoster:
    def test_parses_plain_json_array(self):
        content = json.dumps(SAMPLE_ROSTER)
        result = trapi_client._parse_roster(content)
        assert result == SAMPLE_ROSTER

    def test_parses_json_code_fence(self):
        content = f"```json\n{json.dumps(SAMPLE_ROSTER)}\n```"
        result = trapi_client._parse_roster(content)
        assert result == SAMPLE_ROSTER

    def test_parses_plain_code_fence(self):
        content = f"```\n{json.dumps(SAMPLE_ROSTER)}\n```"
        result = trapi_client._parse_roster(content)
        assert result == SAMPLE_ROSTER

    def test_raises_on_empty_list(self):
        with pytest.raises(ValueError, match="non-empty"):
            trapi_client._parse_roster("[]")

    def test_raises_on_non_list(self):
        with pytest.raises(ValueError):
            trapi_client._parse_roster('{"name": "Don Mattingly"}')

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            trapi_client._parse_roster("not json at all")


# ---------------------------------------------------------------------------
# Tests for get_1985_yankees_roster (integration of all helpers)
# ---------------------------------------------------------------------------


class TestGet1985YankeesRoster:
    @patch("trapi_client.DefaultAzureCredential")
    @patch("trapi_client.requests.post")
    def test_returns_roster_list(self, mock_post, mock_cred_cls, monkeypatch):
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com/chat")
        mock_token = MagicMock()
        mock_token.token = "test-token"
        mock_cred_cls.return_value.get_token.return_value = mock_token
        mock_post.return_value = _make_mock_response(SAMPLE_RESPONSE_JSON)

        roster = trapi_client.get_1985_yankees_roster()

        assert isinstance(roster, list)
        assert len(roster) > 0
        assert roster[0]["name"] == "Don Mattingly"

    @patch("trapi_client.DefaultAzureCredential")
    @patch("trapi_client.requests.post")
    def test_endpoint_argument_overrides_env(
        self, mock_post, mock_cred_cls, monkeypatch
    ):
        monkeypatch.delenv("TRAPI_ENDPOINT", raising=False)
        mock_token = MagicMock()
        mock_token.token = "t"
        mock_cred_cls.return_value.get_token.return_value = mock_token
        mock_post.return_value = _make_mock_response(SAMPLE_RESPONSE_JSON)

        roster = trapi_client.get_1985_yankees_roster(
            endpoint="https://override.example.com/chat"
        )

        assert len(roster) == len(SAMPLE_ROSTER)
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://override.example.com/chat"

    def test_raises_when_endpoint_not_configured(self, monkeypatch):
        monkeypatch.delenv("TRAPI_ENDPOINT", raising=False)

        with pytest.raises(ValueError, match="TRAPI_ENDPOINT"):
            trapi_client.get_1985_yankees_roster()

    @patch("trapi_client.DefaultAzureCredential")
    @patch("trapi_client.requests.post")
    def test_no_api_key_used(self, mock_post, mock_cred_cls, monkeypatch):
        """Confirm no hard-coded API key is passed; only a Bearer token."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com/chat")
        mock_token = MagicMock()
        mock_token.token = "managed-identity-token"
        mock_cred_cls.return_value.get_token.return_value = mock_token
        mock_post.return_value = _make_mock_response(SAMPLE_RESPONSE_JSON)

        trapi_client.get_1985_yankees_roster()

        _, kwargs = mock_post.call_args
        auth_header = kwargs["headers"]["Authorization"]
        assert auth_header.startswith("Bearer ")
        assert "api-key" not in kwargs["headers"]
        assert "api_key" not in kwargs["headers"]
