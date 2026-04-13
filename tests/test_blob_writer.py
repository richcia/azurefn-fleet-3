"""Unit tests for blob_writer.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import HttpResponseError, ServiceRequestError

from blob_writer import write_roster_blob


SAMPLE_ROSTER = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Rickey Henderson", "position": "LF"},
]


class TestWriteRosterBlob:
    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer._CREDENTIAL")
    def test_success_returns_blob_name(self, mock_cred, mock_bsc, monkeypatch):
        """Returns blob name with expected pattern 'roster-YYYYMMDD.json' on successful upload."""
        import re
        monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "myaccount")

        mock_blob_client = MagicMock()
        mock_bsc.return_value.get_blob_client.return_value = mock_blob_client

        result = write_roster_blob(SAMPLE_ROSTER)

        assert re.fullmatch(r"roster-\d{8}\.json", result), (
            f"Blob name '{result}' does not match expected pattern 'roster-YYYYMMDD.json'"
        )
        mock_blob_client.upload_blob.assert_called_once()

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer._CREDENTIAL")
    def test_upload_called_with_json_data(self, mock_cred, mock_bsc, monkeypatch):
        """The blob is uploaded with JSON-encoded roster data and overwrite=True."""
        monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "myaccount")

        mock_blob_client = MagicMock()
        mock_bsc.return_value.get_blob_client.return_value = mock_blob_client

        write_roster_blob(SAMPLE_ROSTER)

        call_args = mock_blob_client.upload_blob.call_args
        uploaded_data = call_args[0][0]
        assert json.loads(uploaded_data) == SAMPLE_ROSTER
        assert call_args[1]["overwrite"] is True

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer._CREDENTIAL")
    def test_uses_correct_container(self, mock_cred, mock_bsc, monkeypatch):
        """Blob is stored in the 'yankees-roster' container."""
        monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "myaccount")

        mock_blob_client = MagicMock()
        mock_bsc.return_value.get_blob_client.return_value = mock_blob_client

        write_roster_blob(SAMPLE_ROSTER)

        call_kwargs = mock_bsc.return_value.get_blob_client.call_args[1]
        assert call_kwargs["container"] == "yankees-roster"

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer._CREDENTIAL")
    def test_account_url_uses_storage_account_name(self, mock_cred, mock_bsc, monkeypatch):
        """BlobServiceClient is created with the correct account URL."""
        monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "myaccount")

        write_roster_blob(SAMPLE_ROSTER)

        call_kwargs = mock_bsc.call_args[1]
        assert call_kwargs["account_url"] == "https://myaccount.blob.core.windows.net"

    def test_missing_storage_account_name_raises_value_error(self, monkeypatch):
        """ValueError raised when STORAGE_ACCOUNT_NAME is not set."""
        monkeypatch.delenv("STORAGE_ACCOUNT_NAME", raising=False)

        with pytest.raises(ValueError, match="STORAGE_ACCOUNT_NAME environment variable is not set"):
            write_roster_blob(SAMPLE_ROSTER)

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer._CREDENTIAL")
    def test_empty_roster_uploaded(self, mock_cred, mock_bsc, monkeypatch):
        """An empty roster list is uploaded as a JSON array with a valid blob name."""
        import re
        monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "myaccount")

        mock_blob_client = MagicMock()
        mock_bsc.return_value.get_blob_client.return_value = mock_blob_client

        result = write_roster_blob([])

        call_args = mock_blob_client.upload_blob.call_args
        assert json.loads(call_args[0][0]) == []
        assert re.fullmatch(r"roster-\d{8}\.json", result), (
            f"Blob name '{result}' does not match expected pattern 'roster-YYYYMMDD.json'"
        )

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer._CREDENTIAL")
    def test_storage_sdk_http_error_propagates(self, mock_cred, mock_bsc, monkeypatch):
        """HttpResponseError from the storage SDK is propagated to the caller."""
        monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "myaccount")

        mock_blob_client = MagicMock()
        mock_bsc.return_value.get_blob_client.return_value = mock_blob_client
        mock_blob_client.upload_blob.side_effect = HttpResponseError(message="403 Forbidden")

        with pytest.raises(HttpResponseError):
            write_roster_blob(SAMPLE_ROSTER)

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer._CREDENTIAL")
    def test_storage_sdk_service_request_error_propagates(self, mock_cred, mock_bsc, monkeypatch):
        """ServiceRequestError (e.g. network failure) from the storage SDK is propagated to the caller."""
        monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "myaccount")

        mock_blob_client = MagicMock()
        mock_bsc.return_value.get_blob_client.return_value = mock_blob_client
        mock_blob_client.upload_blob.side_effect = ServiceRequestError(message="Connection timeout")

        with pytest.raises(ServiceRequestError):
            write_roster_blob(SAMPLE_ROSTER)
