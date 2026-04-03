"""Unit tests for blob_writer module."""
import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from blob_writer import CONTAINER_NAME, get_blob_name, write_roster, main


class TestGetBlobName:
    def test_returns_timestamped_name_for_given_date(self):
        date = datetime(2024, 7, 4, tzinfo=timezone.utc)
        assert get_blob_name(date) == "roster-20240704.json"

    def test_returns_timestamped_name_for_today_when_no_date(self):
        with patch("blob_writer.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, tzinfo=timezone.utc)
            result = get_blob_name()
        assert result == "roster-20240115.json"

    def test_name_format_matches_pattern(self):
        date = datetime(2026, 12, 31, tzinfo=timezone.utc)
        name = get_blob_name(date)
        assert name.startswith("roster-")
        assert name.endswith(".json")
        assert len(name) == len("roster-YYYYMMDD.json")


class TestWriteRoster:
    def _make_mocks(self):
        mock_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_service.get_blob_client.return_value = mock_blob_client
        return mock_service, mock_blob_client

    @patch("blob_writer.BlobServiceClient")
    def test_uses_correct_container_name(self, mock_service_cls):
        mock_service, mock_blob_client = self._make_mocks()
        mock_service_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster([], "myaccount", datetime(2024, 7, 4, tzinfo=timezone.utc), mock_credential)

        mock_service.get_blob_client.assert_called_once_with(
            container=CONTAINER_NAME, blob="roster-20240704.json"
        )

    @patch("blob_writer.BlobServiceClient")
    def test_uses_correct_blob_name(self, mock_service_cls):
        mock_service, _ = self._make_mocks()
        mock_service_cls.return_value = mock_service
        mock_credential = MagicMock()

        result = write_roster([], "myaccount", datetime(2025, 3, 1, tzinfo=timezone.utc), mock_credential)

        assert result == "roster-20250301.json"

    @patch("blob_writer.BlobServiceClient")
    def test_writes_json_as_utf8(self, mock_service_cls):
        roster = [{"name": "Don Mattingly", "position": "1B"}]
        mock_service, mock_blob_client = self._make_mocks()
        mock_service_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster(roster, "myaccount", datetime(2024, 7, 4, tzinfo=timezone.utc), mock_credential)

        call_args = mock_blob_client.upload_blob.call_args
        uploaded_data = call_args[0][0]
        assert isinstance(uploaded_data, bytes)
        parsed = json.loads(uploaded_data.decode("utf-8"))
        assert parsed == roster

    @patch("blob_writer.BlobServiceClient")
    def test_upload_blob_called_with_overwrite_true(self, mock_service_cls):
        mock_service, mock_blob_client = self._make_mocks()
        mock_service_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster([], "myaccount", datetime(2024, 7, 4, tzinfo=timezone.utc), mock_credential)

        mock_blob_client.upload_blob.assert_called_once()
        _, kwargs = mock_blob_client.upload_blob.call_args
        assert kwargs.get("overwrite") is True

    @patch("blob_writer.BlobServiceClient")
    def test_constructs_correct_account_url(self, mock_service_cls):
        mock_service, _ = self._make_mocks()
        mock_service_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster([], "storageacct123", datetime(2024, 7, 4, tzinfo=timezone.utc), mock_credential)

        mock_service_cls.assert_called_once_with(
            account_url="https://storageacct123.blob.core.windows.net",
            credential=mock_credential,
        )

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_uses_default_azure_credential_when_none_provided(self, mock_credential_cls, mock_service_cls):
        mock_service, _ = self._make_mocks()
        mock_service_cls.return_value = mock_service

        write_roster([], "myaccount", datetime(2024, 7, 4, tzinfo=timezone.utc))

        mock_credential_cls.assert_called_once()

    @patch("blob_writer.BlobServiceClient")
    def test_returns_blob_name(self, mock_service_cls):
        mock_service, _ = self._make_mocks()
        mock_service_cls.return_value = mock_service
        mock_credential = MagicMock()

        result = write_roster([{"name": "Dave Winfield"}], "myaccount", datetime(2024, 7, 4, tzinfo=timezone.utc), mock_credential)

        assert result == "roster-20240704.json"

    @patch("blob_writer.BlobServiceClient")
    def test_empty_roster_writes_empty_list_json(self, mock_service_cls):
        mock_service, mock_blob_client = self._make_mocks()
        mock_service_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster([], "myaccount", datetime(2024, 7, 4, tzinfo=timezone.utc), mock_credential)

        call_args = mock_blob_client.upload_blob.call_args
        uploaded_data = call_args[0][0]
        assert json.loads(uploaded_data.decode("utf-8")) == []

    @patch("blob_writer.BlobServiceClient")
    def test_idempotent_same_date_same_blob_name(self, mock_service_cls):
        """Two calls with the same date produce the same blob name (overwrite=True ensures idempotency)."""
        mock_service, mock_blob_client = self._make_mocks()
        mock_service_cls.return_value = mock_service
        mock_credential = MagicMock()

        date = datetime(2024, 7, 4, tzinfo=timezone.utc)
        name1 = write_roster([{"n": "A"}], "myaccount", date, mock_credential)
        name2 = write_roster([{"n": "B"}], "myaccount", date, mock_credential)

        assert name1 == name2
        assert mock_blob_client.upload_blob.call_count == 2


class TestMain:
    @patch("blob_writer.write_roster", return_value="roster-20240704.json")
    def test_main_calls_write_roster_with_env_vars(self, mock_write):
        env = {"STORAGE_ACCOUNT_NAME": "myaccount", "ROSTER_JSON": '[{"name": "Babe Ruth"}]'}
        with patch.dict(os.environ, env, clear=False):
            main()
        mock_write.assert_called_once_with([{"name": "Babe Ruth"}], "myaccount")

    def test_main_raises_when_storage_account_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError, match="STORAGE_ACCOUNT_NAME"):
                main()

    @patch("blob_writer.write_roster", return_value="roster-20240704.json")
    def test_main_defaults_to_empty_roster_when_no_roster_json(self, mock_write):
        env = {"STORAGE_ACCOUNT_NAME": "myaccount"}
        with patch.dict(os.environ, env, clear=True):
            main()
        mock_write.assert_called_once_with([], "myaccount")
