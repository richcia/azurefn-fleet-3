import logging
from datetime import datetime, timezone

import pytest
from azure.core.exceptions import HttpResponseError, ResourceExistsError, ServiceRequestError

import blob_writer


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 3, 31, 0, 0, 0, tzinfo=timezone.utc)


def test_write_roster_blob_uses_conditional_put_and_logs_success(monkeypatch, caplog):
    captured = {}

    class FakeBlobClient:
        url = "https://dedicatedacct.blob.core.windows.net/yankees-roster/2026-03-31.json"

        def upload_blob(self, data, **kwargs):
            captured["data"] = data
            captured["kwargs"] = kwargs

    class FakeBlobServiceClient:
        def __init__(self, **kwargs):
            captured["service_client_kwargs"] = kwargs

        def get_blob_client(self, container, blob):
            captured["container"] = container
            captured["blob"] = blob
            return FakeBlobClient()

    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "dedicatedacct")
    monkeypatch.setattr(blob_writer, "datetime", _FixedDateTime)
    monkeypatch.setattr(blob_writer, "BlobServiceClient", FakeBlobServiceClient)

    caplog.set_level(logging.INFO, logger="blob_writer")

    blob_name = blob_writer.write_roster_blob([{"name": "Don Mattingly", "position": "1B"}])

    assert blob_name == "2026-03-31.json"
    assert captured["container"] == "yankees-roster"
    assert captured["blob"] == "2026-03-31.json"
    assert captured["kwargs"]["overwrite"] is False
    assert captured["kwargs"]["if_none_match"] == "*"
    success_record = next(record for record in caplog.records if record.msg == "blob_write_succeeded")
    assert success_record.custom_dimensions["event"] == "blob_write_succeeded"
    assert success_record.custom_dimensions["blob_uri"] == FakeBlobClient.url


def test_write_roster_blob_raises_resource_exists_error_on_duplicate(monkeypatch):
    class FakeBlobClient:
        def upload_blob(self, *_args, **_kwargs):
            raise ResourceExistsError("already exists")

    class FakeBlobServiceClient:
        def __init__(self, **_kwargs):
            pass

        def get_blob_client(self, **_kwargs):
            return FakeBlobClient()

    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "dedicatedacct")
    monkeypatch.setattr(blob_writer, "datetime", _FixedDateTime)
    monkeypatch.setattr(blob_writer, "BlobServiceClient", FakeBlobServiceClient)

    with pytest.raises(ResourceExistsError):
        blob_writer.write_roster_blob([{"name": "Willie Randolph", "position": "2B"}])


def test_write_roster_blob_routes_failed_payload_to_failed_prefix(monkeypatch):
    captured = {}

    class FakeBlobClient:
        url = "https://dedicatedacct.blob.core.windows.net/yankees-roster/failed/2026-03-31.json"

        def upload_blob(self, *_args, **_kwargs):
            return None

    class FakeBlobServiceClient:
        def __init__(self, **_kwargs):
            pass

        def get_blob_client(self, container, blob):
            captured["container"] = container
            captured["blob"] = blob
            return FakeBlobClient()

    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "dedicatedacct")
    monkeypatch.setattr(blob_writer, "datetime", _FixedDateTime)
    monkeypatch.setattr(blob_writer, "BlobServiceClient", FakeBlobServiceClient)

    blob_name = blob_writer.write_roster_blob({"invalid": "response"}, failed=True)

    assert blob_name == "failed/2026-03-31.json"
    assert captured["container"] == "yankees-roster"
    assert captured["blob"] == "failed/2026-03-31.json"


def test_write_roster_blob_requires_storage_account_name(monkeypatch):
    monkeypatch.delenv("STORAGE_ACCOUNT_NAME", raising=False)

    with pytest.raises(ValueError, match="STORAGE_ACCOUNT_NAME"):
        blob_writer.write_roster_blob([{"name": "Ron Guidry", "position": "P"}])


def test_write_roster_blob_retries_on_service_request_error(monkeypatch):
    attempts = {"count": 0}

    class FakeBlobClient:
        url = "https://dedicatedacct.blob.core.windows.net/yankees-roster/2026-03-31.json"

        def upload_blob(self, *_args, **_kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise ServiceRequestError("temporary network issue")

    class FakeBlobServiceClient:
        def __init__(self, **_kwargs):
            pass

        def get_blob_client(self, **_kwargs):
            return FakeBlobClient()

    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "dedicatedacct")
    monkeypatch.setattr(blob_writer, "datetime", _FixedDateTime)
    monkeypatch.setattr(blob_writer, "BlobServiceClient", FakeBlobServiceClient)
    monkeypatch.setattr(blob_writer.time, "sleep", lambda *_args: None)

    blob_name = blob_writer.write_roster_blob([{"name": "Rickey Henderson", "position": "OF"}])

    assert blob_name == "2026-03-31.json"
    assert attempts["count"] == 2


def test_write_roster_blob_raises_http_response_error_for_non_retryable_status(monkeypatch):
    class FakeBlobClient:
        def upload_blob(self, *_args, **_kwargs):
            exc = HttpResponseError("forbidden")
            exc.status_code = 403
            raise exc

    class FakeBlobServiceClient:
        def __init__(self, **_kwargs):
            pass

        def get_blob_client(self, **_kwargs):
            return FakeBlobClient()

    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "dedicatedacct")
    monkeypatch.setattr(blob_writer, "datetime", _FixedDateTime)
    monkeypatch.setattr(blob_writer, "BlobServiceClient", FakeBlobServiceClient)

    with pytest.raises(HttpResponseError):
        blob_writer.write_roster_blob([{"name": "Dave Winfield", "position": "OF"}])
