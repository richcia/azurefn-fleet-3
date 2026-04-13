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


def _make_error_response(status_code: int, text: str = "Internal Server Error", headers: dict = None) -> MagicMock:
    """Return a mock requests.Response representing an HTTP error."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = status_code
    mock_resp.text = text
    mock_resp.headers = headers or {}
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

    def test_invalid_entry_not_a_dict_raises_value_error(self):
        players = [
            {"name": "Don Mattingly", "position": "1B"},
            "not a dict",
        ]
        with pytest.raises(ValueError, match="expected object"):
            _parse_roster_content(json.dumps(players))

    def test_invalid_entry_missing_position_raises_value_error(self):
        players = [{"name": "Missing Position"}]
        with pytest.raises(ValueError, match="missing required field"):
            _parse_roster_content(json.dumps(players))

    def test_invalid_entry_missing_name_raises_value_error(self):
        players = [{"position": "P"}]
        with pytest.raises(ValueError, match="missing required field"):
            _parse_roster_content(json.dumps(players))

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="Could not parse TRAPI response"):
            _parse_roster_content("this is not json")

    def test_invalid_json_error_includes_preview_not_full_content(self):
        """Long invalid content should be truncated in the error message."""
        long_bad_content = "x" * 500
        with pytest.raises(ValueError) as exc_info:
            _parse_roster_content(long_bad_content)
        msg = str(exc_info.value)
        assert "content length=500" in msg
        assert "..." in msg
        # The full 500-char string should NOT appear verbatim
        assert "x" * 500 not in msg

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

    @patch("trapi_client.time.sleep")
    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_500_raises_runtime_error(self, mock_post, mock_token, mock_sleep, monkeypatch):
        """RuntimeError raised on HTTP 500 after exhausting all retries."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_error_response(500, "Internal Server Error")

        with pytest.raises(RuntimeError, match="TRAPI request failed with HTTP 500"):
            fetch_1985_yankees_roster()

        assert mock_post.call_count == 4  # 1 initial + 3 retries

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_401_raises_runtime_error(self, mock_post, mock_token, monkeypatch):
        """RuntimeError raised on HTTP 401 Unauthorized."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_error_response(401, "Unauthorized")

        with pytest.raises(RuntimeError, match="TRAPI request failed with HTTP 401"):
            fetch_1985_yankees_roster()

    @patch("trapi_client.time.sleep")
    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_429_raises_runtime_error(self, mock_post, mock_token, mock_sleep, monkeypatch):
        """RuntimeError raised on HTTP 429 Too Many Requests after exhausting all retries."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_error_response(429, "Too Many Requests")

        with pytest.raises(RuntimeError, match="TRAPI request failed with HTTP 429"):
            fetch_1985_yankees_roster()

        assert mock_post.call_count == 4  # 1 initial + 3 retries

    @patch("trapi_client.time.sleep")
    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_429_retries_and_succeeds(self, mock_post, mock_token, mock_sleep, monkeypatch):
        """HTTP 429 without Retry-After uses exponential backoff and succeeds on second attempt."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.side_effect = [
            _make_error_response(429, "Too Many Requests"),  # no Retry-After header
            _make_ok_response(SAMPLE_PLAYERS),
        ]

        roster = fetch_1985_yankees_roster()

        assert roster == SAMPLE_PLAYERS
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1 second (exponential backoff)

    @patch("trapi_client.time.sleep")
    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_429_uses_retry_after_header(self, mock_post, mock_token, mock_sleep, monkeypatch):
        """HTTP 429 with a Retry-After header uses the header value as the sleep delay."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.side_effect = [
            _make_error_response(429, "Too Many Requests", headers={"Retry-After": "15"}),
            _make_ok_response(SAMPLE_PLAYERS),
        ]

        roster = fetch_1985_yankees_roster()

        assert roster == SAMPLE_PLAYERS
        mock_sleep.assert_called_once_with(15)  # value from Retry-After header

    @patch("trapi_client.time.sleep")
    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_429_non_integer_retry_after_falls_back_to_backoff(self, mock_post, mock_token, mock_sleep, monkeypatch):
        """HTTP 429 with non-integer Retry-After (e.g. HTTP-date) falls back to exponential backoff."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.side_effect = [
            _make_error_response(429, "Too Many Requests", headers={"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"}),
            _make_ok_response(SAMPLE_PLAYERS),
        ]

        roster = fetch_1985_yankees_roster()

        assert roster == SAMPLE_PLAYERS
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1 second (fallback exponential backoff)

    @patch("trapi_client.time.sleep")
    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_500_retries_and_succeeds(self, mock_post, mock_token, mock_sleep, monkeypatch):
        """HTTP 500 is retried and succeeds on the third attempt."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.side_effect = [
            _make_error_response(500, "Internal Server Error"),
            _make_error_response(500, "Internal Server Error"),
            _make_ok_response(SAMPLE_PLAYERS),
        ]

        roster = fetch_1985_yankees_roster()

        assert roster == SAMPLE_PLAYERS
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("trapi_client.time.sleep")
    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_exponential_backoff_delays(self, mock_post, mock_token, mock_sleep, monkeypatch):
        """Retry delays follow exponential backoff: 1s, 2s, 4s."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_error_response(500, "Internal Server Error")

        with pytest.raises(RuntimeError):
            fetch_1985_yankees_roster()

        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert sleep_calls == [1, 2, 4]

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_http_401_does_not_retry(self, mock_post, mock_token, monkeypatch):
        """HTTP 401 (non-retryable) raises RuntimeError immediately without retrying."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_post.return_value = _make_error_response(401, "Unauthorized")

        with pytest.raises(RuntimeError, match="TRAPI request failed with HTTP 401"):
            fetch_1985_yankees_roster()

        assert mock_post.call_count == 1  # no retries

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
    def test_non_json_2xx_response_raises_value_error(
        self, mock_post, mock_token, monkeypatch
    ):
        """ValueError raised when a 2xx response body is not valid JSON (e.g., HTML proxy page)."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.text = "<html>Gateway error</html>"
        mock_resp.json.side_effect = ValueError("No JSON object could be decoded")

        mock_post.return_value = mock_resp

        with pytest.raises(ValueError, match="non-JSON body"):
            fetch_1985_yankees_roster()

    @patch("trapi_client._get_bearer_token", return_value="fake-token")
    @patch("trapi_client.requests.post")
    def test_markdown_fenced_content_is_parsed(self, mock_post, mock_token, monkeypatch):
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
