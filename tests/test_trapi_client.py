"""Unit tests for trapi_client.py."""

import json
from unittest.mock import MagicMock, patch

import pytest

import trapi_client
from trapi_client import _parse_roster_content, fetch_1985_yankees_roster


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_PLAYERS = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Rickey Henderson", "position": "LF"},
]


def _make_ok_response(players: list) -> MagicMock:
    """Return a mock requests.Response with status 200 and a valid GPT-4o payload."""
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(players)}}]
    }
    return mock_resp


def _make_error_response(status_code: int, text: str = "Internal Server Error") -> MagicMock:
    """Return a mock requests.Response representing an HTTP error."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = status_code
    mock_resp.text = text
    return mock_resp


# ---------------------------------------------------------------------------
# _parse_roster_content
# ---------------------------------------------------------------------------


class TestParseRosterContent:
    def test_plain_json_array(self):
        content = json.dumps(SAMPLE_PLAYERS)
        result = _parse_roster_content(content)
        assert result == SAMPLE_PLAYERS

    def test_markdown_fenced_json(self):
        content = "```json\n" + json.dumps(SAMPLE_PLAYERS) + "\n```"
        result = _parse_roster_content(content)
        assert result == SAMPLE_PLAYERS

    def test_markdown_fenced_no_language(self):
        content = "```\n" + json.dumps(SAMPLE_PLAYERS) + "\n```"
        result = _parse_roster_content(content)
        assert result == SAMPLE_PLAYERS

    def test_empty_array(self):
        result = _parse_roster_content("[]")
        assert result == []

    def test_filters_out_incomplete_entries(self):
        players = [
            {"name": "Don Mattingly", "position": "1B"},
            {"name": "Missing Position"},  # no position field
            {"position": "P"},              # no name field
            "not a dict",                   # completely wrong type
        ]
        result = _parse_roster_content(json.dumps(players))
        assert len(result) == 1
        assert result[0]["name"] == "Don Mattingly"

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="Could not parse TRAPI response"):
            _parse_roster_content("this is not json")

    def test_non_list_json_raises_value_error(self):
        with pytest.raises(ValueError, match="Expected a JSON array"):
            _parse_roster_content('{"name": "Don Mattingly", "position": "1B"}')

    def test_whitespace_stripped(self):
        content = "  \n  " + json.dumps(SAMPLE_PLAYERS) + "  \n  "
        result = _parse_roster_content(content)
        assert result == SAMPLE_PLAYERS


# ---------------------------------------------------------------------------
# fetch_1985_yankees_roster
# ---------------------------------------------------------------------------


class TestFetch1985YankeesRoster:
    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_success_path(self, mock_post, mock_token, monkeypatch):
        """Success path: returns a non-empty list of player dicts."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_ok_response(SAMPLE_PLAYERS)

        roster = fetch_1985_yankees_roster()

        assert isinstance(roster, list)
        assert len(roster) == 3
        assert roster[0]["name"] == "Don Mattingly"
        assert roster[0]["position"] == "1B"
        mock_post.assert_called_once()
        # Verify Bearer token is in the request headers
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer fake-token"

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_empty_response(self, mock_post, mock_token, monkeypatch):
        """Empty list returned when GPT-4o returns an empty JSON array."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_ok_response([])

        roster = fetch_1985_yankees_roster()

        assert roster == []

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_500_raises_runtime_error(self, mock_post, mock_token, monkeypatch):
        """RuntimeError raised on HTTP 500."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_error_response(500, "Internal Server Error")

        with pytest.raises(RuntimeError, match="TRAPI request failed with HTTP 500"):
            fetch_1985_yankees_roster()

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_401_raises_runtime_error(self, mock_post, mock_token, monkeypatch):
        """RuntimeError raised on HTTP 401 Unauthorized."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_error_response(401, "Unauthorized")

        with pytest.raises(RuntimeError, match="TRAPI request failed with HTTP 401"):
            fetch_1985_yankees_roster()

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_429_raises_runtime_error(self, mock_post, mock_token, monkeypatch):
        """RuntimeError raised on HTTP 429 Too Many Requests (rate limiting)."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_error_response(429, "Too Many Requests")

        with pytest.raises(RuntimeError, match="TRAPI request failed with HTTP 429"):
            fetch_1985_yankees_roster()

    def test_missing_endpoint_raises_value_error(self, monkeypatch):
        """ValueError raised when TRAPI_ENDPOINT is not set."""
        monkeypatch.delenv("TRAPI_ENDPOINT", raising=False)

        with pytest.raises(ValueError, match="TRAPI_ENDPOINT environment variable is not set"):
            fetch_1985_yankees_roster()

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_malformed_response_structure_raises_value_error(
        self, mock_post, mock_token, monkeypatch
    ):
        """ValueError raised when GPT-4o response is missing expected keys."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"unexpected": "format"}

        mock_post.return_value = mock_resp

        with pytest.raises(ValueError, match="Unexpected TRAPI response structure"):
            fetch_1985_yankees_roster()

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_response_with_markdown_fences(self, mock_post, mock_token, monkeypatch):
        """Content wrapped in markdown fences is correctly parsed."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        fenced = "```json\n" + json.dumps(SAMPLE_PLAYERS) + "\n```"
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": fenced}}]
        }
        mock_post.return_value = mock_resp

        roster = fetch_1985_yankees_roster()
        assert len(roster) == 3

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_url_construction_uses_env_vars(self, mock_post, mock_token, monkeypatch):
        """The request URL uses TRAPI_DEPLOYMENT_NAME and TRAPI_API_VERSION env vars."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        monkeypatch.setenv("TRAPI_DEPLOYMENT_NAME", "my-gpt4o")
        monkeypatch.setenv("TRAPI_API_VERSION", "2024-05-01-preview")
        mock_post.return_value = _make_ok_response(SAMPLE_PLAYERS)

        fetch_1985_yankees_roster()

        called_url = mock_post.call_args[0][0]
        assert "my-gpt4o" in called_url
        assert "2024-05-01-preview" in called_url

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_trailing_slash_stripped_from_endpoint(self, mock_post, mock_token, monkeypatch):
        """Trailing slashes in TRAPI_ENDPOINT do not produce double slashes in URL."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com/")
        mock_post.return_value = _make_ok_response(SAMPLE_PLAYERS)

        fetch_1985_yankees_roster()

        called_url = mock_post.call_args[0][0]
        assert "//" not in called_url.replace("https://", "")
