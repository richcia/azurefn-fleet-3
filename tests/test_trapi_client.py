"""Unit tests for trapi_client module."""

from unittest.mock import MagicMock, patch

import pytest
from openai import AuthenticationError, APIStatusError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ROSTER = [
    "Don Mattingly",
    "Dave Winfield",
    "Rickey Henderson",
    "Willie Randolph",
    "Ron Guidry",
]

SAMPLE_CONTENT = "\n".join(SAMPLE_ROSTER)


def _make_completion_response(content: str) -> MagicMock:
    """Build a minimal mock that looks like a ChatCompletion response."""
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_auth_error() -> AuthenticationError:
    """Return a minimal AuthenticationError for testing."""
    raw_response = MagicMock()
    raw_response.headers = {}
    return AuthenticationError(
        message="Unauthorized",
        response=raw_response,
        body={"error": {"message": "Unauthorized", "type": "invalid_request_error"}},
    )


def _make_api_status_error(status_code: int = 500) -> APIStatusError:
    """Return a minimal APIStatusError for testing."""
    raw_response = MagicMock()
    raw_response.headers = {}
    raw_response.status_code = status_code
    return APIStatusError(
        message="Internal Server Error",
        response=raw_response,
        body={"error": {"message": "Internal Server Error"}},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("trapi_client.TRAPI_ENDPOINT", "https://fake-trapi.example.com")
@patch("trapi_client._build_client")
@patch("trapi_client._get_token", return_value="mock-token")
def test_successful_response(mock_token, mock_build_client):
    """get_1985_yankees_roster returns a non-empty list on a successful response."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_completion_response(
        SAMPLE_CONTENT
    )
    mock_build_client.return_value = mock_client

    import trapi_client

    result = trapi_client.get_1985_yankees_roster()

    assert isinstance(result, list)
    assert len(result) == len(SAMPLE_ROSTER)
    assert result[0] == "Don Mattingly"
    mock_token.assert_called_once()
    mock_build_client.assert_called_once_with(bearer_token="mock-token")


@patch("trapi_client.TRAPI_ENDPOINT", "https://fake-trapi.example.com")
@patch("trapi_client._build_client")
@patch("trapi_client._get_token", return_value="mock-token")
def test_empty_response_raises(mock_token, mock_build_client):
    """get_1985_yankees_roster raises ValueError when GPT-4o returns empty content."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_completion_response("")
    mock_build_client.return_value = mock_client

    import trapi_client

    with pytest.raises(ValueError, match="empty roster"):
        trapi_client.get_1985_yankees_roster()


@patch("trapi_client.TRAPI_ENDPOINT", "https://fake-trapi.example.com")
@patch("trapi_client._build_client")
@patch("trapi_client._get_token", return_value="mock-token")
def test_http_error_propagates(mock_token, mock_build_client):
    """get_1985_yankees_roster propagates APIStatusError on HTTP errors."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = _make_api_status_error(500)
    mock_build_client.return_value = mock_client

    import trapi_client

    with pytest.raises(APIStatusError):
        trapi_client.get_1985_yankees_roster()


@patch("trapi_client.TRAPI_ENDPOINT", "https://fake-trapi.example.com")
@patch("trapi_client._get_token")
def test_auth_failure_propagates(mock_token):
    """get_1985_yankees_roster propagates AuthenticationError on auth failure."""
    mock_token.side_effect = _make_auth_error()

    import trapi_client

    with pytest.raises(AuthenticationError):
        trapi_client.get_1985_yankees_roster()


def test_missing_trapi_endpoint_raises(monkeypatch):
    """get_1985_yankees_roster raises ValueError when TRAPI_ENDPOINT is not set."""
    import trapi_client

    monkeypatch.setattr(trapi_client, "TRAPI_ENDPOINT", "")
    with pytest.raises(ValueError, match="TRAPI_ENDPOINT"):
        trapi_client.get_1985_yankees_roster()


@patch("trapi_client.TRAPI_ENDPOINT", "https://fake-trapi.example.com")
@patch("trapi_client._build_client")
@patch("trapi_client._get_token", return_value="mock-token")
def test_whitespace_only_response_raises(mock_token, mock_build_client):
    """get_1985_yankees_roster raises ValueError when content is only whitespace."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_completion_response(
        "   \n\n\t  "
    )
    mock_build_client.return_value = mock_client

    import trapi_client

    with pytest.raises(ValueError, match="empty roster"):
        trapi_client.get_1985_yankees_roster()


@patch("trapi_client.TRAPI_ENDPOINT", "https://fake-trapi.example.com")
@patch("trapi_client._build_client")
@patch("trapi_client._get_token", return_value="mock-token")
def test_strips_blank_lines(mock_token, mock_build_client):
    """get_1985_yankees_roster strips blank lines from GPT-4o output."""
    content_with_blanks = "\n".join(["", "Don Mattingly", "", "Dave Winfield", ""])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_completion_response(
        content_with_blanks
    )
    mock_build_client.return_value = mock_client

    import trapi_client

    result = trapi_client.get_1985_yankees_roster()

    assert result == ["Don Mattingly", "Dave Winfield"]
