import json
import re
from datetime import date
from unittest.mock import MagicMock, call, patch

import pytest
from azure.core.exceptions import ResourceExistsError, ServiceRequestError

from blob_writer import CONTAINER_NAME, get_blob_name, write_roster_to_blob

SAMPLE_PLAYERS = [
    {"name": "Don Mattingly", "position": "1B"},
    {"name": "Dave Winfield", "position": "RF"},
    {"name": "Rickey Henderson", "position": "LF"},
]

STORAGE_ACCOUNT = "mystorageaccount"


# ---------------------------------------------------------------------------
# get_blob_name helpers
# ---------------------------------------------------------------------------


def test_get_blob_name_default_is_today():
    """get_blob_name() without args returns roster-YYYY-MM-DD.json for today."""
    today = date.today()
    expected = f"roster-{today.isoformat()}.json"
    assert get_blob_name() == expected


def test_get_blob_name_with_explicit_date():
    """get_blob_name() accepts an explicit date."""
    d = date(2026, 4, 6)
    assert get_blob_name(d) == "roster-2026-04-06.json"


def test_get_blob_name_format():
    """get_blob_name() result matches roster-YYYY-MM-DD.json pattern."""
    pattern = re.compile(r"^roster-\d{4}-\d{2}-\d{2}\.json$")
    assert pattern.match(get_blob_name())


# ---------------------------------------------------------------------------
# write_roster_to_blob – successful write
# ---------------------------------------------------------------------------


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_successful(mock_credential_cls, mock_service_client_cls):
    """write_roster_to_blob should upload the correct JSON payload to the correct blob."""
    mock_credential = MagicMock()
    mock_credential_cls.return_value = mock_credential

    mock_blob_client = MagicMock()
    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container_client
    mock_service_client_cls.return_value = mock_service

    blob_name = "roster-2026-04-06.json"
    write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT, blob_name=blob_name)

    # BlobServiceClient constructed with correct URL and credential
    mock_service_client_cls.assert_called_once_with(
        account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=mock_credential,
    )

    # Container client obtained for the expected container
    mock_service.get_container_client.assert_called_once_with(CONTAINER_NAME)

    # Blob client obtained with the provided name
    mock_container_client.get_blob_client.assert_called_once_with(blob_name)

    # upload_blob called with correct JSON and overwrite=True
    expected_data = json.dumps(SAMPLE_PLAYERS, indent=2)
    mock_blob_client.upload_blob.assert_called_once_with(expected_data, overwrite=True)


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_uses_default_azure_credential(mock_credential_cls, mock_service_client_cls):
    """Authentication must use DefaultAzureCredential — no connection strings or keys."""
    mock_service = MagicMock()
    mock_service_client_cls.return_value = mock_service
    mock_service.get_container_client.return_value = MagicMock()

    write_roster_to_blob([], STORAGE_ACCOUNT, blob_name="roster-2026-04-06.json")

    # DefaultAzureCredential instantiated exactly once with no extra args
    mock_credential_cls.assert_called_once_with()


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_targets_yankees_container(mock_credential_cls, mock_service_client_cls):
    """write_roster_to_blob must target the 'yankees-roster' container."""
    mock_service = MagicMock()
    mock_service_client_cls.return_value = mock_service
    mock_service.get_container_client.return_value = MagicMock()

    write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT, blob_name="roster-2026-04-06.json")

    args, _ = mock_service.get_container_client.call_args
    assert args[0] == "yankees-roster"


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_default_blob_name_uses_today(mock_credential_cls, mock_service_client_cls):
    """When no blob_name is provided, the name defaults to roster-YYYY-MM-DD.json (today)."""
    mock_blob_client = MagicMock()
    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container_client
    mock_service_client_cls.return_value = mock_service

    today = date.today()
    expected_blob_name = f"roster-{today.isoformat()}.json"

    write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT)

    mock_container_client.get_blob_client.assert_called_once_with(expected_blob_name)


# ---------------------------------------------------------------------------
# Blob overwrite idempotency
# ---------------------------------------------------------------------------


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_overwrite_idempotency(mock_credential_cls, mock_service_client_cls):
    """Calling write_roster_to_blob twice with the same blob_name must overwrite, not fail."""
    mock_blob_client = MagicMock()
    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container_client
    mock_service_client_cls.return_value = mock_service

    blob_name = "roster-2026-04-06.json"
    expected_data = json.dumps(SAMPLE_PLAYERS, indent=2)

    # First write
    write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT, blob_name=blob_name)
    # Second write (simulates a re-run on the same day)
    write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT, blob_name=blob_name)

    assert mock_blob_client.upload_blob.call_count == 2
    for c in mock_blob_client.upload_blob.call_args_list:
        assert c == call(expected_data, overwrite=True)


# ---------------------------------------------------------------------------
# Storage exception propagation
# ---------------------------------------------------------------------------


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_propagates_storage_exception(mock_credential_cls, mock_service_client_cls):
    """write_roster_to_blob must not swallow exceptions from the Azure SDK."""
    mock_blob_client = MagicMock()
    mock_blob_client.upload_blob.side_effect = ServiceRequestError("network error")

    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container_client
    mock_service_client_cls.return_value = mock_service

    with pytest.raises(ServiceRequestError):
        write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT, blob_name="roster-2026-04-06.json")


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_propagates_resource_exists_error(
    mock_credential_cls, mock_service_client_cls
):
    """write_roster_to_blob should propagate ResourceExistsError if overwrite=True still fails."""
    mock_blob_client = MagicMock()
    mock_blob_client.upload_blob.side_effect = ResourceExistsError("blob conflict")

    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container_client
    mock_service_client_cls.return_value = mock_service

    with pytest.raises(ResourceExistsError):
        write_roster_to_blob(SAMPLE_PLAYERS, STORAGE_ACCOUNT, blob_name="roster-2026-04-06.json")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@patch("blob_writer.BlobServiceClient")
@patch("blob_writer.DefaultAzureCredential")
def test_write_roster_empty_list(mock_credential_cls, mock_service_client_cls):
    """write_roster_to_blob should handle an empty player list gracefully."""
    mock_blob_client = MagicMock()
    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container_client
    mock_service_client_cls.return_value = mock_service

    write_roster_to_blob([], STORAGE_ACCOUNT, blob_name="roster-2026-04-06.json")

    expected_data = json.dumps([], indent=2)
    mock_blob_client.upload_blob.assert_called_once_with(expected_data, overwrite=True)
