"""Unit tests for trapi_client.py."""

import json
import os
import pathlib
from unittest.mock import MagicMock, patch, call

import pytest
import requests

import trapi_client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ROSTER = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Rickey Henderson", "position": "LF"},
]

_VALID_RESPONSE_BODY = {
    "choices": [
        {
            "message": {
                "content": json.dumps(_VALID_ROSTER),
            }
        }
    ]
}


def _make_response(status_code: int, body: dict | None = None, headers: dict | None = None) -> MagicMock:
    """Build a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = (200 <= status_code < 300)
    resp.headers = headers or {}
    if body is not None:
        resp.json.return_value = body
        resp.text = json.dumps(body)
    else:
        resp.json.side_effect = ValueError("no body")
        resp.text = ""
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def set_trapi_endpoint(monkeypatch):
    """Ensure TRAPI_ENDPOINT is always set so tests can reach the HTTP layer."""
    monkeypatch.setenv("TRAPI_ENDPOINT", "https://trapi.example.com")


@pytest.fixture(autouse=True)
def mock_credential(monkeypatch):
    """Replace DefaultAzureCredential with a stub that returns a fake token."""
    fake_token = MagicMock()
    fake_token.token = "fake-bearer-token"
    cred = MagicMock()
    cred.get_token.return_value = fake_token
    monkeypatch.setattr(trapi_client, "_DEFAULT_AZURE_CREDENTIAL", cred)
    return cred


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_bearer_token_uses_module_level_credential(self, mock_credential):
        """_get_bearer_token must use the module-level _DEFAULT_AZURE_CREDENTIAL."""
        token = trapi_client._get_bearer_token()
        mock_credential.get_token.assert_called_once_with(trapi_client._TRAPI_SCOPE)
        assert token == "fake-bearer-token"

    def test_trapi_scope_is_cognitiveservices(self):
        """Auth scope must target cognitiveservices.azure.com."""
        assert trapi_client._TRAPI_SCOPE == "https://cognitiveservices.azure.com/.default"

    def test_module_level_credential_is_reused(self, mock_credential):
        """Each call to _get_bearer_token reuses the same credential instance."""
        with patch("requests.post") as mock_post:
            mock_post.return_value = _make_response(200, _VALID_RESPONSE_BODY)
            trapi_client.fetch_1985_yankees_roster()
            trapi_client.fetch_1985_yankees_roster()
        # Both calls should use the same credential (get_token called once per fetch)
        assert mock_credential.get_token.call_count == 2
        # Always called with same scope
        for c in mock_credential.get_token.call_args_list:
            assert c == call(trapi_client._TRAPI_SCOPE)


# ---------------------------------------------------------------------------
# Timeout tests
# ---------------------------------------------------------------------------

class TestTimeout:
    def test_timeout_is_45_seconds(self):
        """_REQUEST_TIMEOUT constant must be 45 seconds."""
        assert trapi_client._REQUEST_TIMEOUT == 45

    def test_post_called_with_45_second_timeout(self):
        """requests.post must be called with timeout=45."""
        with patch("requests.post") as mock_post:
            mock_post.return_value = _make_response(200, _VALID_RESPONSE_BODY)
            trapi_client.fetch_1985_yankees_roster()
        _, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 45

    def test_timeout_exception_raises_runtime_error_after_all_retries(self):
        """All retries exhausted on Timeout → RuntimeError."""
        with patch("requests.post", side_effect=requests.exceptions.Timeout), \
             patch("time.sleep"):
            with pytest.raises(RuntimeError, match="timed out"):
                trapi_client.fetch_1985_yankees_roster()

    def test_timeout_retried_before_exhaustion(self):
        """Timeout on first attempt is retried; success on second attempt returns roster."""
        with patch("requests.post") as mock_post, patch("time.sleep"):
            mock_post.side_effect = [
                requests.exceptions.Timeout,
                _make_response(200, _VALID_RESPONSE_BODY),
            ]
            roster = trapi_client.fetch_1985_yankees_roster()
        assert roster == _VALID_ROSTER
        assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# Retry tests
# ---------------------------------------------------------------------------

class TestRetry:
    def test_max_retries_constant_is_3(self):
        """_MAX_RETRIES must be 3."""
        assert trapi_client._MAX_RETRIES == 3

    def test_5xx_triggers_retry(self):
        """A 500 response on first attempt should be retried."""
        with patch("requests.post") as mock_post, patch("time.sleep"):
            mock_post.side_effect = [
                _make_response(500),
                _make_response(200, _VALID_RESPONSE_BODY),
            ]
            roster = trapi_client.fetch_1985_yankees_roster()
        assert roster == _VALID_ROSTER
        assert mock_post.call_count == 2

    def test_5xx_all_retries_exhausted_raises_runtime_error(self):
        """Persistent 500 across all attempts raises RuntimeError."""
        with patch("requests.post", return_value=_make_response(500)), \
             patch("time.sleep"):
            with pytest.raises(RuntimeError, match="HTTP 500"):
                trapi_client.fetch_1985_yankees_roster()

    def test_exponential_backoff_delays_on_5xx(self):
        """Verify exponential backoff delays: 1s, 2s, 4s for attempts 0..2."""
        sleep_calls = []
        with patch("requests.post") as mock_post, \
             patch("time.sleep", side_effect=lambda d: sleep_calls.append(d)):
            mock_post.side_effect = [
                _make_response(500),
                _make_response(503),
                _make_response(502),
                _make_response(200, _VALID_RESPONSE_BODY),
            ]
            trapi_client.fetch_1985_yankees_roster()
        assert sleep_calls == [1, 2, 4]

    def test_4xx_non_429_not_retried(self):
        """A 400 response should not be retried — raises RuntimeError immediately."""
        with patch("requests.post", return_value=_make_response(400)):
            with pytest.raises(RuntimeError, match="HTTP 400"):
                trapi_client.fetch_1985_yankees_roster()

    def test_timeout_retry_uses_exponential_backoff(self):
        """Timeout retries also use exponential backoff delays."""
        sleep_calls = []
        with patch("requests.post") as mock_post, \
             patch("time.sleep", side_effect=lambda d: sleep_calls.append(d)):
            mock_post.side_effect = [
                requests.exceptions.Timeout,
                requests.exceptions.Timeout,
                _make_response(200, _VALID_RESPONSE_BODY),
            ]
            trapi_client.fetch_1985_yankees_roster()
        assert sleep_calls == [1, 2]

    def test_all_timeout_retries_exhausted(self):
        """4 timeouts (initial + 3 retries) → RuntimeError."""
        with patch("requests.post", side_effect=requests.exceptions.Timeout), \
             patch("time.sleep"):
            with pytest.raises(RuntimeError, match="timed out"):
                trapi_client.fetch_1985_yankees_roster()


# ---------------------------------------------------------------------------
# Model version pinning tests
# ---------------------------------------------------------------------------

class TestModelVersionPinning:
    def test_default_model_version_constant(self):
        """_DEFAULT_MODEL_VERSION must be a specific GPT-4o version."""
        assert trapi_client._DEFAULT_MODEL_VERSION == "gpt-4o-2024-08-06"

    def test_model_field_present_in_payload(self):
        """The request payload must include a 'model' key."""
        with patch("requests.post") as mock_post:
            mock_post.return_value = _make_response(200, _VALID_RESPONSE_BODY)
            trapi_client.fetch_1985_yankees_roster()
        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        assert "model" in payload

    def test_model_field_uses_default_version(self, monkeypatch):
        """When TRAPI_MODEL_VERSION is unset, payload uses _DEFAULT_MODEL_VERSION."""
        monkeypatch.delenv("TRAPI_MODEL_VERSION", raising=False)
        with patch("requests.post") as mock_post:
            mock_post.return_value = _make_response(200, _VALID_RESPONSE_BODY)
            trapi_client.fetch_1985_yankees_roster()
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["model"] == trapi_client._DEFAULT_MODEL_VERSION

    def test_model_field_overridable_via_env(self, monkeypatch):
        """TRAPI_MODEL_VERSION env var overrides the default model version."""
        monkeypatch.setenv("TRAPI_MODEL_VERSION", "gpt-4o-2024-05-13")
        with patch("requests.post") as mock_post:
            mock_post.return_value = _make_response(200, _VALID_RESPONSE_BODY)
            trapi_client.fetch_1985_yankees_roster()
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["model"] == "gpt-4o-2024-05-13"


# ---------------------------------------------------------------------------
# Prompt loading tests
# ---------------------------------------------------------------------------

class TestPromptLoading:
    def test_prompt_file_exists(self):
        """prompts/get_1985_yankees.txt must exist in the repository."""
        assert trapi_client._USER_PROMPT_FILE.exists(), (
            f"Prompt file not found: {trapi_client._USER_PROMPT_FILE}"
        )

    def test_load_user_prompt_returns_nonempty_string(self):
        """_load_user_prompt() must return a non-empty string."""
        prompt = trapi_client._load_user_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_user_prompt_loaded_from_file_in_payload(self, tmp_path, monkeypatch):
        """Payload 'user' message content must equal the contents of the prompt file."""
        # Write a custom prompt to a temp file and point the module at it.
        custom_prompt_file = tmp_path / "get_1985_yankees.txt"
        custom_prompt_file.write_text("Custom test prompt\n", encoding="utf-8")
        monkeypatch.setattr(trapi_client, "_USER_PROMPT_FILE", custom_prompt_file)

        with patch("requests.post") as mock_post:
            mock_post.return_value = _make_response(200, _VALID_RESPONSE_BODY)
            trapi_client.fetch_1985_yankees_roster()

        _, kwargs = mock_post.call_args
        messages = kwargs["json"]["messages"]
        user_message = next(m for m in messages if m["role"] == "user")
        assert user_message["content"] == "Custom test prompt"

    def test_prompt_contains_1985_yankees_reference(self):
        """Prompt text must reference 1985 New York Yankees."""
        prompt = trapi_client._load_user_prompt()
        assert "1985" in prompt
        assert "Yankees" in prompt


# ---------------------------------------------------------------------------
# Successful response parsing tests
# ---------------------------------------------------------------------------

class TestSuccessfulResponse:
    def test_returns_roster_list(self):
        """Successful response returns a list of player dicts."""
        with patch("requests.post") as mock_post:
            mock_post.return_value = _make_response(200, _VALID_RESPONSE_BODY)
            roster = trapi_client.fetch_1985_yankees_roster()
        assert roster == _VALID_ROSTER

    def test_missing_endpoint_raises_value_error(self, monkeypatch):
        """ValueError raised when TRAPI_ENDPOINT is not set."""
        monkeypatch.delenv("TRAPI_ENDPOINT")
        with pytest.raises(ValueError, match="TRAPI_ENDPOINT"):
            trapi_client.fetch_1985_yankees_roster()

    def test_authorization_header_uses_bearer_token(self):
        """The Authorization header must be 'Bearer <token>'."""
        with patch("requests.post") as mock_post:
            mock_post.return_value = _make_response(200, _VALID_RESPONSE_BODY)
            trapi_client.fetch_1985_yankees_roster()
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer fake-bearer-token"
