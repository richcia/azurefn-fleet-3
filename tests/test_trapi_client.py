"""Unit tests for trapi_client.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from trapi_client import (
    TRAPIError,
    _parse_roster,
    fetch_1985_yankees_roster,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_PLAYERS = [
    {"name": "Don Mattingly", "position": "First Base"},
    {"name": "Dave Winfield", "position": "Right Field"},
    {"name": "Rickey Henderson", "position": "Left Field"},
]


def _make_trapi_response(players: list | None = None, content: str | None = None) -> dict:
    """Build a minimal TRAPI chat-completions response dict."""
    if content is None:
        content = json.dumps(players or SAMPLE_PLAYERS)
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                }
            }
        ]
    }


def _mock_credential(token: str = "fake-token") -> MagicMock:
    cred = MagicMock()
    token_obj = MagicMock()
    token_obj.token = token
    cred.get_token.return_value = token_obj
    return cred


# ---------------------------------------------------------------------------
# _parse_roster unit tests
# ---------------------------------------------------------------------------


class TestParseRoster:
    def test_parses_plain_json_array(self):
        content = json.dumps(SAMPLE_PLAYERS)
        result = _parse_roster(content)
        assert len(result) == 3
        assert result[0] == {"name": "Don Mattingly", "position": "First Base"}

    def test_parses_markdown_fenced_json(self):
        content = "```json\n" + json.dumps(SAMPLE_PLAYERS) + "\n```"
        result = _parse_roster(content)
        assert len(result) == 3

    def test_parses_plain_fenced_json(self):
        content = "```\n" + json.dumps(SAMPLE_PLAYERS) + "\n```"
        result = _parse_roster(content)
        assert len(result) == 3

    def test_skips_entries_missing_required_fields(self):
        players = [
            {"name": "Don Mattingly", "position": "First Base"},
            {"name": "Dave Winfield"},  # missing position
            {"position": "Right Field"},  # missing name
        ]
        result = _parse_roster(json.dumps(players))
        assert len(result) == 1

    def test_skips_non_dict_entries(self):
        mixed = [{"name": "Don Mattingly", "position": "1B"}, "not-a-dict", 42]
        result = _parse_roster(json.dumps(mixed))
        assert len(result) == 1

    def test_raises_value_error_on_non_list_response(self):
        with pytest.raises(ValueError, match="non-list"):
            _parse_roster(json.dumps({"name": "Don Mattingly", "position": "1B"}))

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_roster("this is not json")

    def test_empty_array_returns_empty_list(self):
        result = _parse_roster("[]")
        assert result == []

    def test_coerces_values_to_str(self):
        players = [{"name": 42, "position": True}]
        result = _parse_roster(json.dumps(players))
        assert result[0]["name"] == "42"
        assert result[0]["position"] == "True"


# ---------------------------------------------------------------------------
# fetch_1985_yankees_roster unit tests
# ---------------------------------------------------------------------------


class TestFetch1985YankeesRoster:
    @patch("trapi_client.requests.post")
    def test_success_returns_player_list(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = _make_trapi_response()
        mock_post.return_value = mock_resp

        result = fetch_1985_yankees_roster(credential=_mock_credential())

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["name"] == "Don Mattingly"
        assert result[0]["position"] == "First Base"

    @patch("trapi_client.requests.post")
    def test_success_passes_bearer_token(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = _make_trapi_response()
        mock_post.return_value = mock_resp

        fetch_1985_yankees_roster(credential=_mock_credential("my-token"))

        _args, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer my-token"

    @patch("trapi_client.requests.post")
    def test_empty_choices_returns_empty_list(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"choices": []}
        mock_post.return_value = mock_resp

        result = fetch_1985_yankees_roster(credential=_mock_credential())

        assert result == []

    @patch("trapi_client.requests.post")
    def test_empty_message_content_returns_empty_list(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"choices": [{"message": {"content": ""}}]}
        mock_post.return_value = mock_resp

        result = fetch_1985_yankees_roster(credential=_mock_credential())

        assert result == []

    @patch("trapi_client.requests.post")
    def test_http_error_raises_trapi_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"
        mock_post.return_value = mock_resp

        with pytest.raises(TRAPIError, match="429"):
            fetch_1985_yankees_roster(credential=_mock_credential())

    @patch("trapi_client.requests.post")
    def test_http_500_raises_trapi_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        with pytest.raises(TRAPIError, match="500"):
            fetch_1985_yankees_roster(credential=_mock_credential())

    @patch("trapi_client.requests.post")
    def test_http_401_raises_trapi_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        with pytest.raises(TRAPIError, match="401"):
            fetch_1985_yankees_roster(credential=_mock_credential())

    @patch("trapi_client.requests.post")
    def test_custom_endpoint_is_used(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = _make_trapi_response()
        mock_post.return_value = mock_resp

        fetch_1985_yankees_roster(
            credential=_mock_credential(),
            endpoint="https://custom.endpoint/openai/chat/completions",
        )

        _args, kwargs = mock_post.call_args
        assert _args[0] == "https://custom.endpoint/openai/chat/completions"

    @patch("trapi_client.requests.post")
    def test_api_version_is_passed_as_query_param(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = _make_trapi_response()
        mock_post.return_value = mock_resp

        fetch_1985_yankees_roster(
            credential=_mock_credential(),
            api_version="2025-01-01",
        )

        _args, kwargs = mock_post.call_args
        assert kwargs["params"]["api-version"] == "2025-01-01"

    @patch("trapi_client.requests.post")
    def test_markdown_fenced_response_is_parsed(self, mock_post):
        fenced = "```json\n" + json.dumps(SAMPLE_PLAYERS) + "\n```"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = _make_trapi_response(content=fenced)
        mock_post.return_value = mock_resp

        result = fetch_1985_yankees_roster(credential=_mock_credential())
        assert len(result) == 3

    @patch("trapi_client.requests.post")
    def test_returns_only_name_and_position_keys(self, mock_post):
        extra_fields = [
            {"name": "Don Mattingly", "position": "1B", "extra": "ignored"},
        ]
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = _make_trapi_response(content=json.dumps(extra_fields))
        mock_post.return_value = mock_resp

        result = fetch_1985_yankees_roster(credential=_mock_credential())
        # Only name and position should be in the output dict
        assert set(result[0].keys()) == {"name", "position"}

    def test_uses_default_credential_when_none_provided(self):
        """Ensure DefaultAzureCredential is instantiated when no credential is passed."""
        with patch("trapi_client.DefaultAzureCredential") as mock_cls, \
             patch("trapi_client.requests.post") as mock_post:
            mock_cred = MagicMock()
            token_obj = MagicMock()
            token_obj.token = "auto-token"
            mock_cred.get_token.return_value = token_obj
            mock_cls.return_value = mock_cred

            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = _make_trapi_response()
            mock_post.return_value = mock_resp

            fetch_1985_yankees_roster()

            mock_cls.assert_called_once()
