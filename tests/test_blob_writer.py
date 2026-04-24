"""Unit tests for src/blob_writer.py."""
import json
import os
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import HttpResponseError, ResourceExistsError

from src.blob_writer import BlobWriter


PAYLOAD = {"players": [{"name": "Don Mattingly", "position": "1B", "jersey_number": 23}]}
RUN_DATE = "2026-04-24"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("ROSTER_STORAGE_ACCOUNT_NAME", "mystorageaccount")
    monkeypatch.setenv("ROSTER_CONTAINER_NAME", "yankees-roster")


@pytest.fixture()
def writer():
    with patch("src.blob_writer._DEFAULT_AZURE_CREDENTIAL"):
        yield BlobWriter()


class TestBlobWriterInit:
    def test_raises_value_error_when_storage_account_name_missing(self, monkeypatch):
        monkeypatch.delenv("ROSTER_STORAGE_ACCOUNT_NAME", raising=False)
        with patch("src.blob_writer._DEFAULT_AZURE_CREDENTIAL"):
            with pytest.raises(ValueError, match="ROSTER_STORAGE_ACCOUNT_NAME"):
                BlobWriter()

    def test_raises_value_error_when_storage_account_name_empty(self, monkeypatch):
        monkeypatch.setenv("ROSTER_STORAGE_ACCOUNT_NAME", "   ")
        with patch("src.blob_writer._DEFAULT_AZURE_CREDENTIAL"):
            with pytest.raises(ValueError, match="ROSTER_STORAGE_ACCOUNT_NAME"):
                BlobWriter()

    def test_account_url_uses_storage_account_name(self):
        with patch("src.blob_writer._DEFAULT_AZURE_CREDENTIAL"):
            bw = BlobWriter()
        assert bw._account_url == "https://mystorageaccount.blob.core.windows.net"

    def test_container_name_defaults_to_yankees_roster(self, monkeypatch):
        monkeypatch.delenv("ROSTER_CONTAINER_NAME", raising=False)
        with patch("src.blob_writer._DEFAULT_AZURE_CREDENTIAL"):
            bw = BlobWriter()
        assert bw._container_name == "yankees-roster"

    def test_container_name_from_env(self, monkeypatch):
        monkeypatch.setenv("ROSTER_CONTAINER_NAME", "custom-container")
        with patch("src.blob_writer._DEFAULT_AZURE_CREDENTIAL"):
            bw = BlobWriter()
        assert bw._container_name == "custom-container"


class TestBlobWriterWrite:
    def test_write_returns_blob_uri_on_success(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.url = (
            "https://mystorageaccount.blob.core.windows.net/yankees-roster/2026-04-24.json"
        )
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            result = writer.write(PAYLOAD, RUN_DATE)

        assert result == "https://mystorageaccount.blob.core.windows.net/yankees-roster/2026-04-24.json"

    def test_write_uploads_to_correct_blob_name(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://mystorageaccount.blob.core.windows.net/yankees-roster/2026-04-24.json"
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client) as mock_cls:
            writer.write(PAYLOAD, RUN_DATE)

        mock_cls.assert_called_once()
        _, kwargs = mock_cls.call_args
        assert kwargs["blob_name"] == "2026-04-24.json"

    def test_write_uses_conditional_put_if_none_match(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://example.com/blob"
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            writer.write(PAYLOAD, RUN_DATE)

        upload_call_kwargs = mock_blob_client.upload_blob.call_args[1]
        assert upload_call_kwargs.get("if_none_match") == "*"
        assert upload_call_kwargs.get("overwrite") is False

    def test_write_serializes_json_with_indent_2(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://example.com/blob"
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            writer.write(PAYLOAD, RUN_DATE)

        upload_call_kwargs = mock_blob_client.upload_blob.call_args[1]
        data_sent = upload_call_kwargs.get("data") or mock_blob_client.upload_blob.call_args[0][0]
        # Verify it is valid JSON with indent=2
        parsed = json.loads(data_sent)
        assert parsed == PAYLOAD
        assert "  " in data_sent  # indent=2 produces 2-space indentation

    def test_write_sets_content_type_application_json(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://example.com/blob"
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            writer.write(PAYLOAD, RUN_DATE)

        upload_call_kwargs = mock_blob_client.upload_blob.call_args[1]
        content_settings = upload_call_kwargs.get("content_settings")
        assert content_settings is not None
        assert content_settings.content_type == "application/json"

    def test_write_returns_none_on_conflict(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = ResourceExistsError("blob already exists")
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            result = writer.write(PAYLOAD, RUN_DATE)

        assert result is None

    def test_write_does_not_raise_on_resource_exists_error(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = ResourceExistsError("conflict")
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            # Should not raise
            result = writer.write(PAYLOAD, RUN_DATE)
        assert result is None


class TestBlobWriterWriteFailed:
    def test_write_failed_uploads_to_failed_prefix(self, writer):
        mock_blob_client = MagicMock()
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client) as mock_cls:
            writer.write_failed(PAYLOAD, RUN_DATE)

        mock_cls.assert_called_once()
        _, kwargs = mock_cls.call_args
        assert kwargs["blob_name"] == f"failed/{RUN_DATE}.json"

    def test_write_failed_uses_overwrite_true(self, writer):
        mock_blob_client = MagicMock()
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            writer.write_failed(PAYLOAD, RUN_DATE)

        upload_call_kwargs = mock_blob_client.upload_blob.call_args[1]
        assert upload_call_kwargs.get("overwrite") is True

    def test_write_failed_serializes_json_with_indent_2(self, writer):
        mock_blob_client = MagicMock()
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            writer.write_failed(PAYLOAD, RUN_DATE)

        upload_call_kwargs = mock_blob_client.upload_blob.call_args[1]
        data_sent = upload_call_kwargs.get("data") or mock_blob_client.upload_blob.call_args[0][0]
        parsed = json.loads(data_sent)
        assert parsed == PAYLOAD
        assert "  " in data_sent

    def test_write_failed_sets_content_type_application_json(self, writer):
        mock_blob_client = MagicMock()
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            writer.write_failed(PAYLOAD, RUN_DATE)

        upload_call_kwargs = mock_blob_client.upload_blob.call_args[1]
        content_settings = upload_call_kwargs.get("content_settings")
        assert content_settings is not None
        assert content_settings.content_type == "application/json"


class TestBlobWriterAuthentication:
    def test_blob_client_uses_default_azure_credential(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://example.com/blob"
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client) as mock_cls:
            writer.write(PAYLOAD, RUN_DATE)

        _, kwargs = mock_cls.call_args
        # Credential should be the module-level DefaultAzureCredential instance
        import src.blob_writer as bw_module
        assert kwargs["credential"] is bw_module._DEFAULT_AZURE_CREDENTIAL

    def test_no_sas_token_in_account_url(self):
        with patch("src.blob_writer._DEFAULT_AZURE_CREDENTIAL"):
            bw = BlobWriter()
        assert "?" not in bw._account_url
        assert "sig=" not in bw._account_url
        assert "sv=" not in bw._account_url


class TestBlobWriterErrorPropagation:
    def test_write_propagates_http_response_error(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = HttpResponseError("429 Too Many Requests")
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            with pytest.raises(HttpResponseError):
                writer.write(PAYLOAD, RUN_DATE)

    def test_write_failed_propagates_http_response_error(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = HttpResponseError("503 Service Unavailable")
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            with pytest.raises(HttpResponseError):
                writer.write_failed(PAYLOAD, RUN_DATE)

    def test_write_failed_logs_error_before_reraising(self, writer):
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = HttpResponseError("503 Service Unavailable")
        with patch("src.blob_writer.BlobClient", return_value=mock_blob_client):
            with patch("src.blob_writer._LOGGER") as mock_logger:
                with pytest.raises(HttpResponseError):
                    writer.write_failed(PAYLOAD, RUN_DATE)
        mock_logger.exception.assert_called_once()
        call_args = mock_logger.exception.call_args
        assert "blob_failed_write_error" in call_args[0][0]
