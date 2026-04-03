"""Unit tests for blob_writer.py.

All Azure SDK calls are mocked so these tests run without any real Azure
credentials or network access.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call

import pytest
from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError

import blob_writer
from blob_writer import upload_roster, _CONTAINER_NAME, _DEFAULT_BLOB_NAME

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROSTER = [
    {"name": "Don Mattingly", "position": "1B", "number": 23},
    {"name": "Dave Winfield", "position": "RF", "number": 31},
    {"name": "Rickey Henderson", "position": "LF", "number": 24},
]

_STORAGE_ACCOUNT = "mystorageacct"


def _make_mock_clients(container_exists: bool = True):
    """Return (mock_blob_service_client, mock_container_client, mock_blob_client)."""
    mock_blob_client = MagicMock()
    mock_container_client = MagicMock()
    mock_container_client.exists.return_value = container_exists
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client

    return mock_service_client, mock_container_client, mock_blob_client


# ---------------------------------------------------------------------------
# Tests – successful upload
# ---------------------------------------------------------------------------


class TestSuccessfulUpload:
    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_upload_returns_blob_name(self, mock_cred_cls, mock_bsc_cls):
        mock_service, _, _ = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        result = upload_roster(_ROSTER, _STORAGE_ACCOUNT)

        assert result == _DEFAULT_BLOB_NAME

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_upload_sends_valid_json(self, mock_cred_cls, mock_bsc_cls):
        mock_service, _, mock_blob_client = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        upload_roster(_ROSTER, _STORAGE_ACCOUNT)

        mock_blob_client.upload_blob.assert_called_once()
        args, kwargs = mock_blob_client.upload_blob.call_args
        uploaded_data = args[0]
        parsed = json.loads(uploaded_data.decode("utf-8"))
        assert parsed == _ROSTER

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_upload_uses_correct_container(self, mock_cred_cls, mock_bsc_cls):
        mock_service, _, _ = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        upload_roster(_ROSTER, _STORAGE_ACCOUNT)

        mock_service.get_container_client.assert_called_once_with(_CONTAINER_NAME)

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_upload_uses_correct_account_url(self, mock_cred_cls, mock_bsc_cls):
        mock_service, _, _ = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        upload_roster(_ROSTER, _STORAGE_ACCOUNT)

        expected_url = f"https://{_STORAGE_ACCOUNT}.blob.core.windows.net"
        mock_bsc_cls.assert_called_once_with(expected_url, credential=mock_cred_cls.return_value)

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_upload_content_type_is_json(self, mock_cred_cls, mock_bsc_cls):
        mock_service, _, mock_blob_client = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        upload_roster(_ROSTER, _STORAGE_ACCOUNT)

        _, kwargs = mock_blob_client.upload_blob.call_args
        assert kwargs.get("content_type") == "application/json"

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_upload_custom_blob_name(self, mock_cred_cls, mock_bsc_cls):
        mock_service, mock_container_client, _ = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service
        custom_name = "custom_roster.json"

        result = upload_roster(_ROSTER, _STORAGE_ACCOUNT, blob_name=custom_name)

        assert result == custom_name
        mock_container_client.get_blob_client.assert_called_once_with(custom_name)

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_upload_timestamped_blob_name(self, mock_cred_cls, mock_bsc_cls):
        mock_service, mock_container_client, _ = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        result = upload_roster(_ROSTER, _STORAGE_ACCOUNT, timestamped=True)

        # Blob name should include a timestamp suffix
        assert result.startswith("roster_")
        assert result.endswith(".json")
        assert len(result) > len("roster_.json")


# ---------------------------------------------------------------------------
# Tests – overwrite behaviour
# ---------------------------------------------------------------------------


class TestOverwrite:
    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_overwrite_true_by_default(self, mock_cred_cls, mock_bsc_cls):
        mock_service, _, mock_blob_client = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        upload_roster(_ROSTER, _STORAGE_ACCOUNT)

        _, kwargs = mock_blob_client.upload_blob.call_args
        assert kwargs.get("overwrite") is True

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_overwrite_false_passes_through(self, mock_cred_cls, mock_bsc_cls):
        mock_service, _, mock_blob_client = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        upload_roster(_ROSTER, _STORAGE_ACCOUNT, overwrite=False)

        _, kwargs = mock_blob_client.upload_blob.call_args
        assert kwargs.get("overwrite") is False

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_overwrite_existing_blob_succeeds(self, mock_cred_cls, mock_bsc_cls):
        """Calling upload twice with overwrite=True should succeed."""
        mock_service, _, mock_blob_client = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        upload_roster(_ROSTER, _STORAGE_ACCOUNT, overwrite=True)
        upload_roster(_ROSTER, _STORAGE_ACCOUNT, overwrite=True)

        assert mock_blob_client.upload_blob.call_count == 2


# ---------------------------------------------------------------------------
# Tests – error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_missing_container_raises_resource_not_found(self, mock_cred_cls, mock_bsc_cls):
        mock_service, _, _ = _make_mock_clients(container_exists=False)
        mock_bsc_cls.return_value = mock_service

        with pytest.raises(ResourceNotFoundError):
            upload_roster(_ROSTER, _STORAGE_ACCOUNT)

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_missing_container_error_mentions_container_name(self, mock_cred_cls, mock_bsc_cls):
        mock_service, _, _ = _make_mock_clients(container_exists=False)
        mock_bsc_cls.return_value = mock_service

        with pytest.raises(ResourceNotFoundError, match=_CONTAINER_NAME):
            upload_roster(_ROSTER, _STORAGE_ACCOUNT)

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_auth_failure_propagates(self, mock_cred_cls, mock_bsc_cls):
        """ClientAuthenticationError raised by the SDK should propagate unchanged."""
        mock_service, mock_container_client, mock_blob_client = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service
        mock_blob_client.upload_blob.side_effect = ClientAuthenticationError(
            message="Failed to acquire token"
        )

        with pytest.raises(ClientAuthenticationError):
            upload_roster(_ROSTER, _STORAGE_ACCOUNT)

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_no_account_key_in_module(self, mock_cred_cls, mock_bsc_cls):
        """Verify DefaultAzureCredential is used, not a connection string or key."""
        mock_service, _, _ = _make_mock_clients()
        mock_bsc_cls.return_value = mock_service

        upload_roster(_ROSTER, _STORAGE_ACCOUNT)

        mock_cred_cls.assert_called_once()
        # BlobServiceClient must NOT have been called with a connection_string keyword
        _, bsc_kwargs = mock_bsc_cls.call_args
        assert "connection_string" not in bsc_kwargs
        assert "account_key" not in bsc_kwargs
