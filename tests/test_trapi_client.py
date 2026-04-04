import json
from unittest.mock import MagicMock, patch

import pytest
import requests

import trapi_client


def _make_trapi_response(players: list) -> MagicMock:
    """Build a mock requests.Response for a TRAPI chat completions call."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(players),
                }
            }
        ]
    }
    return mock_response


SAMPLE_ROSTER = [
    "Don Mattingly",
    "Dave Winfield",
    "Rickey Henderson",
    "Ron Guidry",
    "Phil Niekro",
    "Ken Griffey Sr.",
    "Willie Randolph",
    "Mike Pagliarulo",
    "Dave Righetti",
    "Bobby Meacham",
]


class TestGetYankeesRoster:
    """Tests for get_1985_yankees_roster()."""

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_returns_nonempty_list(self, mock_cred_cls, mock_post):
        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_post.return_value = _make_trapi_response(SAMPLE_ROSTER)

        result = trapi_client.get_1985_yankees_roster()

        assert isinstance(result, list)
        assert len(result) > 0

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_returns_string_items(self, mock_cred_cls, mock_post):
        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_post.return_value = _make_trapi_response(SAMPLE_ROSTER)

        result = trapi_client.get_1985_yankees_roster()

        assert all(isinstance(name, str) for name in result)

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_uses_bearer_token_in_request(self, mock_cred_cls, mock_post):
        fake_token = "my-entra-token"
        mock_cred_cls.return_value.get_token.return_value.token = fake_token
        mock_post.return_value = _make_trapi_response(SAMPLE_ROSTER)

        trapi_client.get_1985_yankees_roster()

        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == f"Bearer {fake_token}"

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_no_api_key_in_request(self, mock_cred_cls, mock_post):
        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_post.return_value = _make_trapi_response(SAMPLE_ROSTER)

        trapi_client.get_1985_yankees_roster()

        _, kwargs = mock_post.call_args
        headers = kwargs["headers"]
        assert "api-key" not in headers
        assert "Ocp-Apim-Subscription-Key" not in headers

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_requests_correct_scope(self, mock_cred_cls, mock_post):
        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_post.return_value = _make_trapi_response(SAMPLE_ROSTER)

        trapi_client.get_1985_yankees_roster()

        mock_cred_cls.return_value.get_token.assert_called_once_with(
            trapi_client.TRAPI_SCOPE
        )

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_url_contains_deployment_and_version(self, mock_cred_cls, mock_post):
        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_post.return_value = _make_trapi_response(SAMPLE_ROSTER)

        trapi_client.get_1985_yankees_roster()

        call_url = mock_post.call_args[0][0]
        assert trapi_client.TRAPI_DEPLOYMENT in call_url
        assert "api-version=" in call_url

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_raises_on_http_error(self, mock_cred_cls, mock_post):
        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            trapi_client.get_1985_yankees_roster()

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_raises_on_empty_list_response(self, mock_cred_cls, mock_post):
        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_post.return_value = _make_trapi_response([])

        with pytest.raises(ValueError):
            trapi_client.get_1985_yankees_roster()

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_raises_on_non_json_response(self, mock_cred_cls, mock_post):
        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Sorry, I cannot answer that."}}]
        }
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="TRAPI returned invalid JSON format"):
            trapi_client.get_1985_yankees_roster()

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_raises_on_timeout(self, mock_cred_cls, mock_post):
        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_post.side_effect = requests.exceptions.Timeout()

        with pytest.raises(requests.exceptions.Timeout, match="TRAPI request timed out"):
            trapi_client.get_1985_yankees_roster()

    @patch("trapi_client.requests.post")
    @patch("trapi_client.DefaultAzureCredential")
    def test_env_override_endpoint(self, mock_cred_cls, mock_post, monkeypatch):
        monkeypatch.setattr(trapi_client, "TRAPI_ENDPOINT", "https://custom-trapi.example.com")
        monkeypatch.setattr(trapi_client, "TRAPI_DEPLOYMENT", "my-gpt4o")

        mock_cred_cls.return_value.get_token.return_value.token = "fake-token"
        mock_post.return_value = _make_trapi_response(SAMPLE_ROSTER)

        trapi_client.get_1985_yankees_roster()

        call_url = mock_post.call_args[0][0]
        assert "custom-trapi.example.com" in call_url
        assert "my-gpt4o" in call_url
