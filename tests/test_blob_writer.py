"""Unit tests for blob_writer.py."""

import json
import re
from unittest.mock import MagicMock, patch

import pytest

from blob_writer import write_roster_blob

SAMPLE_PLAYERS = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Rickey Henderson", "position": "LF"},
]


def _make_mock_blob_service_client():
    """Return a mock BlobServiceClient with a chained mock blob client."""
    mock_blob_client = MagicMock()
    mock_service_client = MagicMock()
    mock_service_client.get_blob_client.return_value = mock_blob_client
    return mock_service_client, mock_blob_client


# ---------------------------------------------------------------------------
# write_roster_blob
# ---------------------------------------------------------------------------


class TestWriteRosterBlob:
    @patch("blob_writer.BlobServiceClient")
    def test_writes_to_correct_container(self, mock_bsc_cls, monkeypatch):
        """Blob is uploaded to the 'yankees-roster' container."""
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "myaccount")
        monkeypatch.delenv("BLOB_NAME", raising=False)

        mock_service_client, _ = _make_mock_blob_service_client()
        mock_bsc_cls.return_value = mock_service_client

        write_roster_blob(SAMPLE_PLAYERS)

        mock_service_client.get_blob_client.assert_called_once()
        _, kwargs = mock_service_client.get_blob_client.call_args
        assert kwargs["container"] == "yankees-roster"

    @patch("blob_writer.BlobServiceClient")
    def test_blob_name_is_timestamped_by_default(self, mock_bsc_cls, monkeypatch):
        """When BLOB_NAME is not set, the blob name follows the timestamped pattern."""
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "myaccount")
        monkeypatch.delenv("BLOB_NAME", raising=False)

        mock_service_client, _ = _make_mock_blob_service_client()
        mock_bsc_cls.return_value = mock_service_client

        returned_name = write_roster_blob(SAMPLE_PLAYERS)

        assert re.match(r"^roster_\d{8}T\d{6}Z\.json$", returned_name), (
            f"Blob name '{returned_name}' does not match expected timestamp pattern"
        )
        _, kwargs = mock_service_client.get_blob_client.call_args
        assert kwargs["blob"] == returned_name

    @patch("blob_writer.BlobServiceClient")
    def test_blob_name_uses_env_var_when_set(self, mock_bsc_cls, monkeypatch):
        """When BLOB_NAME env var is set, it is used as-is."""
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "myaccount")
        monkeypatch.setenv("BLOB_NAME", "fixed-roster.json")

        mock_service_client, _ = _make_mock_blob_service_client()
        mock_bsc_cls.return_value = mock_service_client

        returned_name = write_roster_blob(SAMPLE_PLAYERS)

        assert returned_name == "fixed-roster.json"
        _, kwargs = mock_service_client.get_blob_client.call_args
        assert kwargs["blob"] == "fixed-roster.json"

    @patch("blob_writer.BlobServiceClient")
    def test_content_is_valid_json_matching_input(self, mock_bsc_cls, monkeypatch):
        """The content uploaded to blob storage is valid JSON equal to the input roster."""
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "myaccount")
        monkeypatch.delenv("BLOB_NAME", raising=False)

        mock_service_client, mock_blob_client = _make_mock_blob_service_client()
        mock_bsc_cls.return_value = mock_service_client

        write_roster_blob(SAMPLE_PLAYERS)

        mock_blob_client.upload_blob.assert_called_once()
        uploaded_content = mock_blob_client.upload_blob.call_args[0][0]
        parsed = json.loads(uploaded_content)
        assert parsed == SAMPLE_PLAYERS

    @patch("blob_writer.BlobServiceClient")
    def test_account_url_uses_account_name_env_var(self, mock_bsc_cls, monkeypatch):
        """BlobServiceClient is constructed with the correct account URL."""
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "myaccount")
        monkeypatch.delenv("BLOB_NAME", raising=False)

        mock_service_client, _ = _make_mock_blob_service_client()
        mock_bsc_cls.return_value = mock_service_client

        write_roster_blob(SAMPLE_PLAYERS)

        mock_bsc_cls.assert_called_once()
        _, kwargs = mock_bsc_cls.call_args
        assert kwargs["account_url"] == "https://myaccount.blob.core.windows.net"

    @patch("blob_writer.BlobServiceClient")
    def test_upload_called_with_overwrite_true(self, mock_bsc_cls, monkeypatch):
        """upload_blob is called with overwrite=True."""
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "myaccount")
        monkeypatch.delenv("BLOB_NAME", raising=False)

        mock_service_client, mock_blob_client = _make_mock_blob_service_client()
        mock_bsc_cls.return_value = mock_service_client

        write_roster_blob(SAMPLE_PLAYERS)

        _, kwargs = mock_blob_client.upload_blob.call_args
        assert kwargs.get("overwrite") is True

    @patch("blob_writer.BlobServiceClient")
    def test_custom_credential_is_passed_to_service_client(
        self, mock_bsc_cls, monkeypatch
    ):
        """A custom credential provided to write_roster_blob is forwarded."""
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "myaccount")
        monkeypatch.delenv("BLOB_NAME", raising=False)

        mock_service_client, _ = _make_mock_blob_service_client()
        mock_bsc_cls.return_value = mock_service_client
        fake_credential = MagicMock()

        write_roster_blob(SAMPLE_PLAYERS, credential=fake_credential)

        _, kwargs = mock_bsc_cls.call_args
        assert kwargs["credential"] is fake_credential

    def test_missing_account_name_raises_value_error(self, monkeypatch):
        """ValueError raised when AZURE_STORAGE_ACCOUNT_NAME is not set."""
        monkeypatch.delenv("AZURE_STORAGE_ACCOUNT_NAME", raising=False)

        with pytest.raises(ValueError, match="AZURE_STORAGE_ACCOUNT_NAME"):
            write_roster_blob(SAMPLE_PLAYERS)

    @patch("blob_writer.BlobServiceClient")
    def test_empty_players_list_writes_empty_array(self, mock_bsc_cls, monkeypatch):
        """An empty players list writes an empty JSON array."""
        monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "myaccount")
        monkeypatch.delenv("BLOB_NAME", raising=False)

        mock_service_client, mock_blob_client = _make_mock_blob_service_client()
        mock_bsc_cls.return_value = mock_service_client

        write_roster_blob([])

        uploaded_content = mock_blob_client.upload_blob.call_args[0][0]
        assert json.loads(uploaded_content) == []
