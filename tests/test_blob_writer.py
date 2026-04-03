"""Unit tests for blob_writer.py.

All Azure SDK calls are mocked so these tests run without any real Azure
credentials or network access.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ClientAuthenticationError, ResourceExistsError

import blob_writer
from blob_writer import CONTAINER_NAME, get_blob_name, write_roster, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROSTER = [
    {"name": "Don Mattingly", "position": "1B", "number": 23},
    {"name": "Dave Winfield", "position": "RF", "number": 31},
    {"name": "Rickey Henderson", "position": "LF", "number": 24},
]

_STORAGE_ACCOUNT = "mystorageacct"
_FIXED_DATE = datetime(2025, 4, 1, tzinfo=timezone.utc)


def _make_mocks():
    """Return (mock_service_client, mock_blob_client)."""
    mock_blob_client = MagicMock()
    mock_service_client = MagicMock()
    mock_service_client.get_blob_client.return_value = mock_blob_client
    return mock_service_client, mock_blob_client


# ---------------------------------------------------------------------------
# Tests – get_blob_name
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tests – successful upload
# ---------------------------------------------------------------------------


class TestSuccessfulUpload:
    @patch("blob_writer.BlobServiceClient")
    def test_upload_returns_blob_name(self, mock_bsc_cls):
        mock_service, _ = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_credential = MagicMock()

        result = write_roster(_ROSTER, _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

        assert result == "roster-20250401.json"

    @patch("blob_writer.BlobServiceClient")
    def test_upload_sends_valid_json(self, mock_bsc_cls):
        mock_service, mock_blob_client = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster(_ROSTER, _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

        mock_blob_client.upload_blob.assert_called_once()
        args, _ = mock_blob_client.upload_blob.call_args
        parsed = json.loads(args[0].decode("utf-8"))
        assert parsed == _ROSTER

    @patch("blob_writer.BlobServiceClient")
    def test_upload_uses_correct_container(self, mock_bsc_cls):
        mock_service, _ = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster(_ROSTER, _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

        mock_service.get_blob_client.assert_called_once_with(
            container=CONTAINER_NAME, blob="roster-20250401.json"
        )

    @patch("blob_writer.BlobServiceClient")
    def test_upload_uses_correct_account_url(self, mock_bsc_cls):
        mock_service, _ = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster(_ROSTER, _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

        expected_url = f"https://{_STORAGE_ACCOUNT}.blob.core.windows.net"
        mock_bsc_cls.assert_called_once_with(
            account_url=expected_url, credential=mock_credential
        )

    @patch("blob_writer.BlobServiceClient")
    def test_upload_overwrite_is_true(self, mock_bsc_cls):
        mock_service, mock_blob_client = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster(_ROSTER, _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

        _, kwargs = mock_blob_client.upload_blob.call_args
        assert kwargs.get("overwrite") is True

    @patch("blob_writer.BlobServiceClient")
    @patch("blob_writer.DefaultAzureCredential")
    def test_uses_default_azure_credential_when_none_provided(
        self, mock_credential_cls, mock_bsc_cls
    ):
        mock_service, _ = _make_mocks()
        mock_bsc_cls.return_value = mock_service

        write_roster(_ROSTER, _STORAGE_ACCOUNT, _FIXED_DATE)

        mock_credential_cls.assert_called_once()

    @patch("blob_writer.BlobServiceClient")
    def test_idempotent_same_date_produces_same_blob_name(self, mock_bsc_cls):
        mock_service, mock_blob_client = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_credential = MagicMock()

        date = datetime(2025, 4, 1, tzinfo=timezone.utc)
        name1 = write_roster([{"n": "A"}], _STORAGE_ACCOUNT, date, mock_credential)
        name2 = write_roster([{"n": "B"}], _STORAGE_ACCOUNT, date, mock_credential)

        assert name1 == name2
        assert mock_blob_client.upload_blob.call_count == 2


# ---------------------------------------------------------------------------
# Tests – empty roster guard
# ---------------------------------------------------------------------------


class TestEmptyRosterGuard:
    @patch("blob_writer.BlobServiceClient")
    def test_empty_roster_writes_empty_list_json(self, mock_bsc_cls):
        """An empty roster should upload a valid JSON empty array (not be blocked)."""
        mock_service, mock_blob_client = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster([], _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

        args, _ = mock_blob_client.upload_blob.call_args
        assert json.loads(args[0].decode("utf-8")) == []

    @patch("blob_writer.BlobServiceClient")
    def test_empty_roster_still_returns_blob_name(self, mock_bsc_cls):
        mock_service, _ = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_credential = MagicMock()

        result = write_roster([], _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

        assert result == "roster-20250401.json"


# ---------------------------------------------------------------------------
# Tests – error / storage error handling
# ---------------------------------------------------------------------------


class TestStorageErrors:
    @patch("blob_writer.BlobServiceClient")
    def test_auth_failure_propagates(self, mock_bsc_cls):
        """ClientAuthenticationError raised by the SDK should propagate unchanged."""
        mock_service, mock_blob_client = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_blob_client.upload_blob.side_effect = ClientAuthenticationError(
            message="Failed to acquire token"
        )
        mock_credential = MagicMock()

        with pytest.raises(ClientAuthenticationError):
            write_roster(_ROSTER, _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

    @patch("blob_writer.BlobServiceClient")
    def test_storage_error_on_upload_propagates(self, mock_bsc_cls):
        """Any exception from upload_blob should propagate unchanged."""
        mock_service, mock_blob_client = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_blob_client.upload_blob.side_effect = RuntimeError("Unexpected storage error")
        mock_credential = MagicMock()

        with pytest.raises(RuntimeError, match="Unexpected storage error"):
            write_roster(_ROSTER, _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

    @patch("blob_writer.BlobServiceClient")
    def test_no_account_key_in_module(self, mock_bsc_cls):
        """Verify DefaultAzureCredential is used, not a connection string or key."""
        mock_service, _ = _make_mocks()
        mock_bsc_cls.return_value = mock_service
        mock_credential = MagicMock()

        write_roster(_ROSTER, _STORAGE_ACCOUNT, _FIXED_DATE, mock_credential)

        _, bsc_kwargs = mock_bsc_cls.call_args
        assert "connection_string" not in bsc_kwargs
        assert "account_key" not in bsc_kwargs

    @patch("blob_writer.BlobServiceClient")
    def test_missing_storage_account_env_raises_environment_error(self, mock_bsc_cls):
        """write_roster reads STORAGE_ACCOUNT_NAME from env and raises if missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError, match="STORAGE_ACCOUNT_NAME"):
                write_roster(_ROSTER)
        # BlobServiceClient should never be called when the env var is absent
        mock_bsc_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Tests – main entry point
# ---------------------------------------------------------------------------


class TestMain:
    @patch("blob_writer.write_roster", return_value="roster-20250401.json")
    def test_main_calls_write_roster_with_env_vars(self, mock_write):
        env = {
            "STORAGE_ACCOUNT_NAME": _STORAGE_ACCOUNT,
            "ROSTER_JSON": '[{"name": "Don Mattingly"}]',
        }
        with patch.dict(os.environ, env, clear=False):
            main()

        mock_write.assert_called_once_with([{"name": "Don Mattingly"}], _STORAGE_ACCOUNT)

    def test_main_raises_when_storage_account_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError, match="STORAGE_ACCOUNT_NAME"):
                main()

    @patch("blob_writer.write_roster", return_value="roster-20250401.json")
    def test_main_defaults_to_empty_roster_when_no_roster_json(self, mock_write):
        env = {"STORAGE_ACCOUNT_NAME": _STORAGE_ACCOUNT}
        with patch.dict(os.environ, env, clear=True):
            main()

        mock_write.assert_called_once_with([], _STORAGE_ACCOUNT)

    @patch("blob_writer.write_roster", return_value="roster-20250401.json")
    def test_main_prints_blob_path(self, mock_write, capsys):
        env = {"STORAGE_ACCOUNT_NAME": _STORAGE_ACCOUNT}
        with patch.dict(os.environ, env, clear=True):
            main()

        captured = capsys.readouterr()
        assert CONTAINER_NAME in captured.out
        assert "roster-20250401.json" in captured.out
