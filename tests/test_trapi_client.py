"""Unit tests for trapi_client.py."""

import os
import pytest
from unittest.mock import MagicMock, patch

import openai

import trapi_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(content: str | None) -> MagicMock:
    """Build a minimal mock that mimics openai.types.chat.ChatCompletion."""
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


SAMPLE_ROSTER_TEXT = "\n".join(
    [
        "Don Mattingly",
        "Dave Winfield",
        "Rickey Henderson",
        "Ron Guidry",
        "Dave Righetti",
        "Phil Niekro",
    ]
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFetchRoster:
    """Tests for trapi_client.fetch_roster()."""

    def test_success_returns_player_list(self, monkeypatch):
        """fetch_roster returns a non-empty list of player name strings."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_response(
            SAMPLE_ROSTER_TEXT
        )

        players = trapi_client.fetch_roster(client=mock_client)

        assert isinstance(players, list)
        assert len(players) > 0
        assert "Don Mattingly" in players
        assert "Dave Winfield" in players

    def test_success_strips_whitespace(self, monkeypatch):
        """Player names are stripped of surrounding whitespace."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_response(
            "  Don Mattingly  \n  Dave Winfield  \n"
        )

        players = trapi_client.fetch_roster(client=mock_client)

        assert players == ["Don Mattingly", "Dave Winfield"]

    def test_success_ignores_blank_lines(self, monkeypatch):
        """Blank lines in the model response are ignored."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_response(
            "Don Mattingly\n\nDave Winfield\n\n"
        )

        players = trapi_client.fetch_roster(client=mock_client)

        assert players == ["Don Mattingly", "Dave Winfield"]

    def test_empty_response_raises_value_error(self, monkeypatch):
        """A response with empty content raises ValueError."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_response("")

        with pytest.raises(ValueError, match="empty or null"):
            trapi_client.fetch_roster(client=mock_client)

    def test_none_content_raises_value_error(self, monkeypatch):
        """A response with None content raises ValueError."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_response(None)

        with pytest.raises(ValueError, match="empty or null"):
            trapi_client.fetch_roster(client=mock_client)

    def test_whitespace_only_response_raises_value_error(self, monkeypatch):
        """A response containing only whitespace raises ValueError."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_response("   \n\n   ")

        with pytest.raises(ValueError, match="empty or null"):
            trapi_client.fetch_roster(client=mock_client)

    def test_no_choices_raises_value_error(self, monkeypatch):
        """A response with an empty choices list raises ValueError."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        mock_client = MagicMock()
        response = MagicMock()
        response.choices = []
        mock_client.chat.completions.create.return_value = response

        with pytest.raises(ValueError, match="empty or null"):
            trapi_client.fetch_roster(client=mock_client)

    def test_api_error_propagates(self, monkeypatch):
        """An APIError raised by the SDK is propagated to the caller."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APIError(
            message="Internal Server Error",
            request=MagicMock(),
            body=None,
        )

        with pytest.raises(openai.APIError):
            trapi_client.fetch_roster(client=mock_client)

    def test_api_timeout_propagates(self, monkeypatch):
        """An APITimeoutError raised by the SDK is propagated to the caller."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APITimeoutError(
            request=MagicMock()
        )

        with pytest.raises(openai.APITimeoutError):
            trapi_client.fetch_roster(client=mock_client)

    def test_uses_deployment_env_var(self, monkeypatch):
        """The AZURE_OPENAI_DEPLOYMENT_NAME env var is passed as the model."""
        monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "my-custom-deployment")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_response(
            "Don Mattingly"
        )

        trapi_client.fetch_roster(client=mock_client)

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs.get("model") == "my-custom-deployment"

    def test_no_api_key_in_module(self):
        """Verify that no API key or secret is hard-coded in the module source."""
        import inspect
        source = inspect.getsource(trapi_client)
        for forbidden in ("api_key=", "OPENAI_API_KEY", "Bearer sk-"):
            assert forbidden not in source, (
                f"Forbidden secret pattern '{forbidden}' found in trapi_client source"
            )


class TestGetClient:
    """Tests for trapi_client.get_client()."""

    def test_get_client_uses_managed_identity(self, monkeypatch):
        """get_client() uses DefaultAzureCredential, not an API key."""
        monkeypatch.setenv("TRAPI_ENDPOINT", "https://fake.openai.azure.com/")

        with (
            patch("trapi_client.DefaultAzureCredential") as mock_cred_cls,
            patch("trapi_client.get_bearer_token_provider") as mock_token_provider,
            patch("trapi_client.AzureOpenAI") as mock_azure_openai,
        ):
            mock_cred_cls.return_value = MagicMock()
            mock_token_provider.return_value = MagicMock()
            mock_azure_openai.return_value = MagicMock()

            trapi_client.get_client()

            mock_cred_cls.assert_called_once()
            mock_token_provider.assert_called_once()
            # Confirm AzureOpenAI was NOT given an api_key parameter
            call_kwargs = mock_azure_openai.call_args.kwargs
            assert "api_key" not in call_kwargs
