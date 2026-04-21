from __future__ import annotations

import importlib
import logging
import sys
from unittest.mock import Mock

import pytest
from azure.core.exceptions import ResourceExistsError


def _reload_blob_writer_module(monkeypatch: pytest.MonkeyPatch, account_name: str, container_name: str | None = None):
    monkeypatch.setenv("ROSTER_STORAGE_ACCOUNT_NAME", account_name)
    if container_name is None:
        monkeypatch.delenv("ROSTER_CONTAINER_NAME", raising=False)
    else:
        monkeypatch.setenv("ROSTER_CONTAINER_NAME", container_name)

    sys.modules.pop("src.blob_writer", None)
    return importlib.import_module("src.blob_writer")


def test_write_uses_conditional_upload_and_returns_blob_uri(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    module = _reload_blob_writer_module(monkeypatch, account_name="acct", container_name="my-container")

    mock_credential = object()
    mock_blob_client = Mock()
    mock_blob_client.url = "https://acct.blob.core.windows.net/my-container/2026-01-01.json"
    mock_service_client = Mock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    monkeypatch.setattr(module, "DefaultAzureCredential", Mock(return_value=mock_credential))
    monkeypatch.setattr(module, "BlobServiceClient", Mock(return_value=mock_service_client))

    caplog.set_level(logging.INFO)

    writer = module.BlobWriter()
    blob_uri = writer.write({"players": []}, run_date_utc="2026-01-01")

    module.BlobServiceClient.assert_called_once_with(
        account_url="https://acct.blob.core.windows.net",
        credential=mock_credential,
    )
    mock_service_client.get_blob_client.assert_called_once_with(
        container="my-container",
        blob="2026-01-01.json",
    )
    mock_blob_client.upload_blob.assert_called_once_with('{"players": []}', overwrite=False)
    assert blob_uri == mock_blob_client.url
    assert any(record.message == "blob_write_succeeded" and record.blob_uri == mock_blob_client.url for record in caplog.records)


def test_write_returns_none_on_resource_exists_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_blob_writer_module(monkeypatch, account_name="acct", container_name="my-container")

    mock_blob_client = Mock()
    mock_blob_client.upload_blob.side_effect = ResourceExistsError("already exists")
    mock_service_client = Mock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    monkeypatch.setattr(module, "DefaultAzureCredential", Mock(return_value=object()))
    monkeypatch.setattr(module, "BlobServiceClient", Mock(return_value=mock_service_client))

    writer = module.BlobWriter()

    assert writer.write({"players": []}, run_date_utc="2026-01-01") is None


def test_write_failed_uses_failed_prefix_and_default_container(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_blob_writer_module(monkeypatch, account_name="acct")

    mock_blob_client = Mock()
    mock_blob_client.url = "https://acct.blob.core.windows.net/yankees-roster/failed/2026-01-01.json"
    mock_service_client = Mock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    monkeypatch.setattr(module, "DefaultAzureCredential", Mock(return_value=object()))
    monkeypatch.setattr(module, "BlobServiceClient", Mock(return_value=mock_service_client))

    writer = module.BlobWriter()
    blob_uri = writer.write_failed({"error": "bad payload"}, run_date_utc="2026-01-01")

    mock_service_client.get_blob_client.assert_called_once_with(
        container="yankees-roster",
        blob="failed/2026-01-01.json",
    )
    mock_blob_client.upload_blob.assert_called_once_with('{"error": "bad payload"}', overwrite=False)
    assert blob_uri == mock_blob_client.url


def test_blob_writer_requires_storage_account_name(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_blob_writer_module(monkeypatch, account_name="")

    with pytest.raises(ValueError, match="ROSTER_STORAGE_ACCOUNT_NAME is required"):
        module.BlobWriter()


def test_write_failed_uses_custom_container_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_blob_writer_module(monkeypatch, account_name="acct", container_name="custom-container")

    mock_blob_client = Mock()
    mock_blob_client.url = "https://acct.blob.core.windows.net/custom-container/failed/2026-01-01.json"
    mock_service_client = Mock()
    mock_service_client.get_blob_client.return_value = mock_blob_client

    monkeypatch.setattr(module, "DefaultAzureCredential", Mock(return_value=object()))
    monkeypatch.setattr(module, "BlobServiceClient", Mock(return_value=mock_service_client))

    writer = module.BlobWriter()
    blob_uri = writer.write_failed({"error": "bad payload"}, run_date_utc="2026-01-01")

    mock_service_client.get_blob_client.assert_called_once_with(
        container="custom-container",
        blob="failed/2026-01-01.json",
    )
    assert blob_uri == mock_blob_client.url
