import json
from unittest.mock import MagicMock, patch

import pytest

from blob_writer import write_roster_to_blob, CONTAINER_NAME, DEFAULT_BLOB_NAME


SAMPLE_PLAYERS = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Rickey Henderson", "position": "LF"},
]

STORAGE_ACCOUNT = "mystorageaccount"


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_to_blob_calls_upload(mock_credential_cls, mock_service_client_cls):
    """write_roster_to_blob should upload the correct JSON payload to the correct blob."""
    mock_credential = MagicMock()
    mock_credential_cls.return_value = mock_credential

    mock_blob_client = MagicMock()
    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container_client
    mock_service_client_cls.return_value = mock_service

    write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT)

    # BlobServiceClient constructed with correct URL and credential
    mock_service_client_cls.assert_called_once_with(
        account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=mock_credential,
    )

    # Container client obtained for the expected container
    mock_service.get_container_client.assert_called_once_with(CONTAINER_NAME)

    # Blob client obtained for the default blob name
    mock_container_client.get_blob_client.assert_called_once_with(DEFAULT_BLOB_NAME)

    # upload_blob called with correct JSON and overwrite=True
    expected_data = json.dumps(SAMPLE_PLAYERS, indent=2)
    mock_blob_client.upload_blob.assert_called_once_with(expected_data, overwrite=True)


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_to_blob_custom_blob_name(mock_credential_cls, mock_service_client_cls):
    """write_roster_to_blob should use the provided blob_name when given."""
    mock_blob_client = MagicMock()
    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container_client
    mock_service_client_cls.return_value = mock_service

    custom_name = "roster_2026-04-04.json"
    write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT, blob_name=custom_name)

    mock_container_client.get_blob_client.assert_called_once_with(custom_name)


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_to_blob_uses_default_azure_credential(
    mock_credential_cls, mock_service_client_cls
):
    """Authentication must use DefaultAzureCredential (no connection strings or keys)."""
    mock_service = MagicMock()
    mock_service_client_cls.return_value = mock_service
    mock_service.get_container_client.return_value = MagicMock()

    write_roster_to_blob([], STORAGE_ACCOUNT)

    # DefaultAzureCredential instantiated exactly once with no extra args
    mock_credential_cls.assert_called_once_with()


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_to_blob_empty_list(mock_credential_cls, mock_service_client_cls):
    """write_roster_to_blob should handle an empty player list gracefully."""
    mock_blob_client = MagicMock()
    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container_client
    mock_service_client_cls.return_value = mock_service

    write_roster_to_blob([], STORAGE_ACCOUNT)

    expected_data = json.dumps([], indent=2)
    mock_blob_client.upload_blob.assert_called_once_with(expected_data, overwrite=True)


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_to_blob_container_name(mock_credential_cls, mock_service_client_cls):
    """write_roster_to_blob must target the 'yankees-roster' container."""
    mock_service = MagicMock()
    mock_service_client_cls.return_value = mock_service
    mock_service.get_container_client.return_value = MagicMock()

    write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT)

    args, _ = mock_service.get_container_client.call_args
    assert args[0] == "yankees-roster"
