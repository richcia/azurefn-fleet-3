"""
tests/test_trapi_client.py

Unit tests for trapi_client.py.

All external dependencies (DefaultAzureCredential, httpx.Client) are mocked
so the tests run without real Azure credentials or network access.
"""
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from trapi_client import (
    BACKOFF_BASE,
    MAX_RETRIES,
    _get_bearer_token,
    _parse_roster,
    get_roster,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status_code: int, body: dict | str) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if isinstance(body, dict):
        resp.json.return_value = body
        resp.text = json.dumps(body)
    else:
        resp.json.side_effect = ValueError("not json")
        resp.text = body
    resp.request = MagicMock()

    def raise_for_status():
        if status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {status_code}",
                request=resp.request,
                response=resp,
            )

    resp.raise_for_status.side_effect = raise_for_status
    return resp


def _roster_response(players: list[dict]) -> MagicMock:
    """Build a successful TRAPI chat-completion response containing *players*."""
    body = {
        "choices": [
            {"message": {"content": json.dumps(players)}}
        ]
    }
    return _make_response(200, body)


SAMPLE_PLAYERS = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Ron Guidry", "position": "SP"},
]


# ---------------------------------------------------------------------------
# _get_bearer_token
# ---------------------------------------------------------------------------


class TestGetBearerToken:
    def test_returns_token_string(self):
        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok123")
        result = _get_bearer_token(cred, "api://trapi/.default")
        assert result == "tok123"
        cred.get_token.assert_called_once_with("api://trapi/.default")


# ---------------------------------------------------------------------------
# _parse_roster
# ---------------------------------------------------------------------------


class TestParseRoster:
    def test_valid_json_array(self):
        content = json.dumps(SAMPLE_PLAYERS)
        players = _parse_roster(content)
        assert players == SAMPLE_PLAYERS

    def test_strips_markdown_code_fence(self):
        content = "```json\n" + json.dumps(SAMPLE_PLAYERS) + "\n```"
        players = _parse_roster(content)
        assert players == SAMPLE_PLAYERS

    def test_strips_plain_code_fence(self):
        content = "```\n" + json.dumps(SAMPLE_PLAYERS) + "\n```"
        players = _parse_roster(content)
        assert players == SAMPLE_PLAYERS

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            _parse_roster("not json at all")

    def test_non_array_raises_value_error(self):
        with pytest.raises(ValueError, match="Expected a JSON array"):
            _parse_roster('{"name": "Don Mattingly"}')

    def test_player_not_dict_raises_value_error(self):
        with pytest.raises(ValueError, match="not an object"):
            _parse_roster('["Don Mattingly"]')

    def test_player_missing_name_raises_value_error(self):
        with pytest.raises(ValueError, match="missing required fields"):
            _parse_roster('[{"position": "1B"}]')

    def test_player_missing_position_raises_value_error(self):
        with pytest.raises(ValueError, match="missing required fields"):
            _parse_roster('[{"name": "Don Mattingly"}]')

    def test_coerces_values_to_str(self):
        # position given as an integer (edge case)
        content = '[{"name": "Don Mattingly", "position": 1}]'
        players = _parse_roster(content)
        assert players[0]["position"] == "1"

    def test_empty_array(self):
        players = _parse_roster("[]")
        assert players == []


# ---------------------------------------------------------------------------
# get_roster – success path
# ---------------------------------------------------------------------------


class TestGetRosterSuccess:
    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_returns_player_list_on_200(self, mock_client_cls, mock_sleep):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = _roster_response(SAMPLE_PLAYERS)

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        players = get_roster(
            credential=cred,
            endpoint="https://trapi.example.com",
            scope="api://trapi/.default",
            model="gpt-4o",
        )

        assert players == SAMPLE_PLAYERS
        mock_sleep.assert_not_called()

    @patch("trapi_client.TRAPI_MODEL", "gpt-4o-env")
    @patch("trapi_client.TRAPI_SCOPE", "api://env/.default")
    @patch("trapi_client.TRAPI_ENDPOINT", "https://trapi.env.example.com")
    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_uses_defaults_from_module(self, mock_client_cls, mock_sleep):
        """When no explicit args are passed, get_roster uses module-level constants."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = _roster_response(SAMPLE_PLAYERS)

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        players = get_roster(credential=cred)
        assert players == SAMPLE_PLAYERS

        # URL must use the patched module-level endpoint
        call_url = mock_client.post.call_args[0][0]
        assert call_url.startswith("https://trapi.env.example.com/")

    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    @patch("trapi_client.DefaultAzureCredential")
    def test_creates_default_credential_when_none(
        self, mock_cred_cls, mock_client_cls, mock_sleep
    ):
        mock_cred = MagicMock()
        mock_cred.get_token.return_value = MagicMock(token="tok")
        mock_cred_cls.return_value = mock_cred

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = _roster_response(SAMPLE_PLAYERS)

        players = get_roster(
            endpoint="https://trapi.example.com",
            scope="api://trapi/.default",
            model="gpt-4o",
        )

        mock_cred_cls.assert_called_once()
        assert players == SAMPLE_PLAYERS


# ---------------------------------------------------------------------------
# get_roster – retry logic
# ---------------------------------------------------------------------------


class TestGetRosterRetry:
    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_retries_on_429_then_succeeds(self, mock_client_cls, mock_sleep):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        mock_client.post.side_effect = [
            _make_response(429, {}),
            _roster_response(SAMPLE_PLAYERS),
        ]

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        players = get_roster(
            credential=cred,
            endpoint="https://trapi.example.com",
            scope="api://trapi/.default",
        )

        assert players == SAMPLE_PLAYERS
        assert mock_client.post.call_count == 2
        mock_sleep.assert_called_once()

    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_retries_on_503_then_succeeds(self, mock_client_cls, mock_sleep):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        mock_client.post.side_effect = [
            _make_response(503, {}),
            _make_response(503, {}),
            _roster_response(SAMPLE_PLAYERS),
        ]

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        players = get_roster(
            credential=cred,
            endpoint="https://trapi.example.com",
            scope="api://trapi/.default",
        )

        assert players == SAMPLE_PLAYERS
        assert mock_client.post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_raises_after_max_retries_exhausted_429(
        self, mock_client_cls, mock_sleep
    ):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        # MAX_RETRIES + 1 = 4 total attempts, all return 429
        mock_client.post.return_value = _make_response(429, {})

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        with pytest.raises(httpx.HTTPStatusError):
            get_roster(
                credential=cred,
                endpoint="https://trapi.example.com",
                scope="api://trapi/.default",
            )

        assert mock_client.post.call_count == MAX_RETRIES + 1
        assert mock_sleep.call_count == MAX_RETRIES

    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_raises_after_max_retries_exhausted_503(
        self, mock_client_cls, mock_sleep
    ):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        mock_client.post.return_value = _make_response(503, {})

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        with pytest.raises(httpx.HTTPStatusError):
            get_roster(
                credential=cred,
                endpoint="https://trapi.example.com",
                scope="api://trapi/.default",
            )

        assert mock_client.post.call_count == MAX_RETRIES + 1

    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_exponential_backoff_delays(self, mock_client_cls, mock_sleep):
        """Verify sleep durations follow BACKOFF_BASE ** attempt pattern."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        mock_client.post.return_value = _make_response(429, {})

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        with pytest.raises(httpx.HTTPStatusError):
            get_roster(
                credential=cred,
                endpoint="https://trapi.example.com",
                scope="api://trapi/.default",
            )

        expected_delays = [
            BACKOFF_BASE**i for i in range(MAX_RETRIES)
        ]
        actual_delays = [c[0][0] for c in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_does_not_retry_on_400(self, mock_client_cls, mock_sleep):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        mock_client.post.return_value = _make_response(400, {})

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        with pytest.raises(httpx.HTTPStatusError):
            get_roster(
                credential=cred,
                endpoint="https://trapi.example.com",
                scope="api://trapi/.default",
            )

        # Only one attempt – no retries on 400
        assert mock_client.post.call_count == 1
        mock_sleep.assert_not_called()

    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_does_not_retry_on_401(self, mock_client_cls, mock_sleep):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        mock_client.post.return_value = _make_response(401, {})

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        with pytest.raises(httpx.HTTPStatusError):
            get_roster(
                credential=cred,
                endpoint="https://trapi.example.com",
                scope="api://trapi/.default",
            )

        assert mock_client.post.call_count == 1
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# get_roster – response parsing errors
# ---------------------------------------------------------------------------


class TestGetRosterParsingErrors:
    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_raises_on_malformed_response_structure(
        self, mock_client_cls, mock_sleep
    ):
        """Response missing 'choices' key raises ValueError."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        bad_body = {"result": "unexpected"}
        mock_client.post.return_value = _make_response(200, bad_body)

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        with pytest.raises(ValueError, match="Unexpected TRAPI response structure"):
            get_roster(
                credential=cred,
                endpoint="https://trapi.example.com",
                scope="api://trapi/.default",
            )

    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_raises_on_invalid_json_content(self, mock_client_cls, mock_sleep):
        """Model returning non-JSON content raises ValueError."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        bad_content_body = {
            "choices": [{"message": {"content": "Sorry, I cannot help with that."}}]
        }
        mock_client.post.return_value = _make_response(200, bad_content_body)

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        with pytest.raises(ValueError, match="not valid JSON"):
            get_roster(
                credential=cred,
                endpoint="https://trapi.example.com",
                scope="api://trapi/.default",
            )

    @patch("trapi_client.time.sleep")
    @patch("trapi_client.httpx.Client")
    def test_raises_on_non_array_json_content(self, mock_client_cls, mock_sleep):
        """Model returning a JSON object (not array) raises ValueError."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        bad_content_body = {
            "choices": [{"message": {"content": '{"players": []}'}}]
        }
        mock_client.post.return_value = _make_response(200, bad_content_body)

        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok")

        with pytest.raises(ValueError, match="Expected a JSON array"):
            get_roster(
                credential=cred,
                endpoint="https://trapi.example.com",
                scope="api://trapi/.default",
            )
