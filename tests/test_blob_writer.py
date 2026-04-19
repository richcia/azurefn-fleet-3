import logging
import types

from azure.core.exceptions import HttpResponseError, ResourceExistsError

from src import blob_writer


class FakeBlobClient:
    def __init__(self, url: str, upload_side_effect=None):
        self.url = url
        self.upload_calls = []
        self._upload_side_effect = upload_side_effect

    def upload_blob(self, payload, **kwargs):
        self.upload_calls.append({"payload": payload, "kwargs": kwargs})
        if self._upload_side_effect is not None:
            raise self._upload_side_effect


class FakeBlobServiceClient:
    def __init__(self, account_url, credential, blob_client):
        self.account_url = account_url
        self.credential = credential
        self._blob_client = blob_client
        self.get_blob_client_calls = []

    def get_blob_client(self, *, container, blob):
        self.get_blob_client_calls.append({"container": container, "blob": blob})
        return self._blob_client


def test_write_uses_default_credential_conditional_put_and_logs_success(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "storageacct")
    sentinel_credential = object()
    fake_blob_client = FakeBlobClient("https://storageacct.blob.core.windows.net/yankees-roster/2026-03-31.json")
    captured = {}

    def fake_service_client(account_url, credential):
        service_client = FakeBlobServiceClient(account_url, credential, fake_blob_client)
        captured["service_client"] = service_client
        return service_client

    monkeypatch.setattr(blob_writer, "_DEFAULT_AZURE_CREDENTIAL", sentinel_credential)
    monkeypatch.setattr(blob_writer, "BlobServiceClient", fake_service_client)

    writer = blob_writer.BlobWriter()
    result = writer.write({"players": []}, run_date_utc="2026-03-31")

    assert result == fake_blob_client.url
    assert captured["service_client"].account_url == "https://storageacct.blob.core.windows.net"
    assert captured["service_client"].credential is sentinel_credential
    assert captured["service_client"].get_blob_client_calls == [
        {"container": "yankees-roster", "blob": "2026-03-31.json"}
    ]
    assert fake_blob_client.upload_calls[0]["kwargs"] == {"overwrite": False, "if_none_match": "*"}
    record = next(r for r in caplog.records if r.message == "blob_write_succeeded")
    assert record.blob_uri == fake_blob_client.url


def test_write_handles_409_conflict_without_raising(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "storageacct")
    conflict_error = HttpResponseError(message="conflict")
    conflict_error.status_code = 409
    conflict_error.error_code = "BlobAlreadyExists"
    fake_blob_client = FakeBlobClient(
        "https://storageacct.blob.core.windows.net/yankees-roster/2026-03-31.json",
        upload_side_effect=conflict_error,
    )
    monkeypatch.setattr(
        blob_writer,
        "BlobServiceClient",
        lambda account_url, credential: FakeBlobServiceClient(account_url, credential, fake_blob_client),
    )
    monkeypatch.setattr(
        blob_writer,
        "_DEFAULT_AZURE_CREDENTIAL",
        types.SimpleNamespace(get_token=lambda *_: None),
    )

    writer = blob_writer.BlobWriter()
    result = writer.write({"players": []}, run_date_utc="2026-03-31")

    assert result is None
    record = next(r for r in caplog.records if r.message == "blob_write_conflict")
    assert record.blob_uri == fake_blob_client.url


def test_write_reraises_non_duplicate_http_response_error(monkeypatch):
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "storageacct")
    conflict_error = HttpResponseError(message="conflict")
    conflict_error.status_code = 409
    conflict_error.error_code = "ContainerBeingDeleted"
    fake_blob_client = FakeBlobClient(
        "https://storageacct.blob.core.windows.net/yankees-roster/2026-03-31.json",
        upload_side_effect=conflict_error,
    )
    monkeypatch.setattr(
        blob_writer,
        "BlobServiceClient",
        lambda account_url, credential: FakeBlobServiceClient(account_url, credential, fake_blob_client),
    )

    writer = blob_writer.BlobWriter()

    try:
        writer.write({"players": []}, run_date_utc="2026-03-31")
    except HttpResponseError as exc:
        assert exc is conflict_error
    else:
        raise AssertionError("Expected HttpResponseError to be re-raised for non-duplicate conflicts")


def test_write_handles_412_duplicate_conflict_without_raising(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "storageacct")
    conflict_error = HttpResponseError(message="precondition failed")
    conflict_error.status_code = 412
    conflict_error.error_code = "ConditionNotMet"
    fake_blob_client = FakeBlobClient(
        "https://storageacct.blob.core.windows.net/yankees-roster/2026-03-31.json",
        upload_side_effect=conflict_error,
    )
    monkeypatch.setattr(
        blob_writer,
        "BlobServiceClient",
        lambda account_url, credential: FakeBlobServiceClient(account_url, credential, fake_blob_client),
    )

    writer = blob_writer.BlobWriter()
    result = writer.write({"players": []}, run_date_utc="2026-03-31")

    assert result is None
    record = next(r for r in caplog.records if r.message == "blob_write_conflict")
    assert record.blob_uri == fake_blob_client.url


def test_write_handles_resource_exists_error_without_raising(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "storageacct")
    fake_blob_client = FakeBlobClient(
        "https://storageacct.blob.core.windows.net/yankees-roster/2026-03-31.json",
        upload_side_effect=ResourceExistsError(message="exists"),
    )
    monkeypatch.setattr(
        blob_writer,
        "BlobServiceClient",
        lambda account_url, credential: FakeBlobServiceClient(account_url, credential, fake_blob_client),
    )

    writer = blob_writer.BlobWriter()
    result = writer.write({"players": []}, run_date_utc="2026-03-31")

    assert result is None
    record = next(r for r in caplog.records if r.message == "blob_write_conflict")
    assert record.blob_uri == fake_blob_client.url


def test_write_failed_uses_failed_prefix_without_conditional_put(monkeypatch):
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "storageacct")
    fake_blob_client = FakeBlobClient("https://storageacct.blob.core.windows.net/yankees-roster/failed/2026-03-31.json")
    captured = {}

    def fake_service_client(account_url, credential):
        service_client = FakeBlobServiceClient(account_url, credential, fake_blob_client)
        captured["service_client"] = service_client
        return service_client

    monkeypatch.setattr(blob_writer, "BlobServiceClient", fake_service_client)
    monkeypatch.setattr(
        blob_writer,
        "_DEFAULT_AZURE_CREDENTIAL",
        types.SimpleNamespace(get_token=lambda *_: None),
    )

    writer = blob_writer.BlobWriter()
    result = writer.write_failed({"error": "invalid roster"}, run_date_utc="2026-03-31")

    assert result == fake_blob_client.url
    assert captured["service_client"].get_blob_client_calls == [
        {"container": "yankees-roster", "blob": "failed/2026-03-31.json"}
    ]
    assert fake_blob_client.upload_calls[0]["kwargs"] == {"overwrite": True}
