"""Unit tests for blob_writer module."""
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from blob_writer import CONTAINER_NAME, get_blob_name, write_roster


class TestGetBlobName:
    def test_returns_timestamped_name_for_given_date(self):
        date = datetime(2024, 7, 4)
        assert get_blob_name(date) == "roster-20240704.json"

    def test_returns_timestamped_name_for_today_when_no_date(self):
        with patch("blob_writer.datetime") as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 15)
            result = get_blob_name()
        assert result == "roster-20240115.json"

    def test_name_format_matches_pattern(self):
        date = datetime(2026, 12, 31)
        name = get_blob_name(date)
        assert name.startswith("roster-")
        assert name.endswith(".json")
        assert len(name) == len("roster-YYYYMMDD.json")


class TestWriteRoster:
    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_uses_correct_container_name(self, mock_credential_cls, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service
        mock_blob_client = MagicMock()
        mock_service.get_blob_client.return_value = mock_blob_client

        write_roster([], "myaccount", datetime(2024, 7, 4))

        mock_service.get_blob_client.assert_called_once_with(
            container=CONTAINER_NAME, blob="roster-20240704.json"
        )

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_uses_correct_blob_name(self, mock_credential_cls, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service
        mock_blob_client = MagicMock()
        mock_service.get_blob_client.return_value = mock_blob_client

        result = write_roster([], "myaccount", datetime(2025, 3, 1))

        assert result == "roster-20250301.json"

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_writes_json_as_utf8(self, mock_credential_cls, mock_service_cls):
        roster = [{"name": "Don Mattingly", "position": "1B"}]
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service
        mock_blob_client = MagicMock()
        mock_service.get_blob_client.return_value = mock_blob_client

        write_roster(roster, "myaccount", datetime(2024, 7, 4))

        call_args = mock_blob_client.upload_blob.call_args
        uploaded_data = call_args[0][0]
        assert isinstance(uploaded_data, bytes)
        parsed = json.loads(uploaded_data.decode("utf-8"))
        assert parsed == roster

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_upload_blob_called_with_overwrite_true(self, mock_credential_cls, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service
        mock_blob_client = MagicMock()
        mock_service.get_blob_client.return_value = mock_blob_client

        write_roster([], "myaccount", datetime(2024, 7, 4))

        mock_blob_client.upload_blob.assert_called_once()
        _, kwargs = mock_blob_client.upload_blob.call_args
        assert kwargs.get("overwrite") is True

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_constructs_correct_account_url(self, mock_credential_cls, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service
        mock_blob_client = MagicMock()
        mock_service.get_blob_client.return_value = mock_blob_client

        write_roster([], "storageacct123", datetime(2024, 7, 4))

        mock_service_cls.assert_called_once_with(
            account_url="https://storageacct123.blob.core.windows.net",
            credential=mock_credential_cls.return_value,
        )

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_uses_default_azure_credential(self, mock_credential_cls, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service
        mock_blob_client = MagicMock()
        mock_service.get_blob_client.return_value = mock_blob_client

        write_roster([], "myaccount", datetime(2024, 7, 4))

        mock_credential_cls.assert_called_once()

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_returns_blob_name(self, mock_credential_cls, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service
        mock_service.get_blob_client.return_value = MagicMock()

        result = write_roster([{"name": "Dave Winfield"}], "myaccount", datetime(2024, 7, 4))

        assert result == "roster-20240704.json"

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_empty_roster_writes_empty_list_json(self, mock_credential_cls, mock_service_cls):
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service
        mock_blob_client = MagicMock()
        mock_service.get_blob_client.return_value = mock_blob_client

        write_roster([], "myaccount", datetime(2024, 7, 4))

        call_args = mock_blob_client.upload_blob.call_args
        uploaded_data = call_args[0][0]
        assert json.loads(uploaded_data.decode("utf-8")) == []

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_idempotent_same_date_same_blob_name(self, mock_credential_cls, mock_service_cls):
        """Two calls with the same date produce the same blob name (overwrite=True ensures idempotency)."""
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service
        mock_blob_client = MagicMock()
        mock_service.get_blob_client.return_value = mock_blob_client

        date = datetime(2024, 7, 4)
        name1 = write_roster([{"n": "A"}], "myaccount", date)
        name2 = write_roster([{"n": "B"}], "myaccount", date)

        assert name1 == name2
        assert mock_blob_client.upload_blob.call_count == 2
