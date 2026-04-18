import pytest
from azure.core.exceptions import ResourceExistsError

import blob_writer


class _FakeBlobClient:
    def __init__(self, should_raise=False):
        self.upload_calls = []
        self.should_raise = should_raise

    def upload_blob(self, data, overwrite=False, if_none_match=None):
        self.upload_calls.append((data, overwrite, if_none_match))
        if self.should_raise:
            raise ResourceExistsError("already exists")


class _FakeServiceClient:
    def __init__(self, blob_client):
        self._blob_client = blob_client
        self.get_blob_client_calls = []

    def get_blob_client(self, container, blob):
        self.get_blob_client_calls.append((container, blob))
        return self._blob_client


def test_write_roster_writes_expected_blob_with_conditional_put(monkeypatch):
    fake_blob_client = _FakeBlobClient()
    fake_service_client = _FakeServiceClient(fake_blob_client)
    blob_service_client_calls = []
    default_credential_calls = []

    def fake_default_credential():
        default_credential_calls.append(True)
        return object()

    def fake_blob_service_client(account_url, credential):
        blob_service_client_calls.append((account_url, credential))
        return fake_service_client

    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "acct123")
    monkeypatch.setattr(blob_writer, "DefaultAzureCredential", fake_default_credential)
    monkeypatch.setattr(blob_writer, "BlobServiceClient", fake_blob_service_client)

    payload = {"players": [{"name": "Don Mattingly"}]}
    blob_writer.write_roster(payload, "2026-03-31")

    assert len(default_credential_calls) == 1
    assert blob_service_client_calls[0][0] == "https://acct123.blob.core.windows.net"
    assert fake_service_client.get_blob_client_calls == [("yankees-roster", "2026-03-31.json")]
    assert fake_blob_client.upload_calls and fake_blob_client.upload_calls[0][1] is False
    assert fake_blob_client.upload_calls[0][2] == "*"


def test_write_roster_raises_resource_exists_for_duplicate_write(monkeypatch):
    fake_blob_client = _FakeBlobClient(should_raise=True)
    fake_service_client = _FakeServiceClient(fake_blob_client)

    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "acct123")
    monkeypatch.setattr(blob_writer, "DefaultAzureCredential", lambda: object())
    monkeypatch.setattr(blob_writer, "BlobServiceClient", lambda account_url, credential: fake_service_client)

    with pytest.raises(ResourceExistsError):
        blob_writer.write_roster({"players": []}, "2026-03-31")


def test_write_failed_writes_to_failed_prefix(monkeypatch):
    fake_blob_client = _FakeBlobClient()
    fake_service_client = _FakeServiceClient(fake_blob_client)

    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "acct123")
    monkeypatch.setattr(blob_writer, "DefaultAzureCredential", lambda: object())
    monkeypatch.setattr(blob_writer, "BlobServiceClient", lambda account_url, credential: fake_service_client)

    blob_writer.write_failed("raw response", "2026-03-31")

    assert fake_service_client.get_blob_client_calls == [
        ("yankees-roster", "failed/2026-03-31.json")
    ]
    assert fake_blob_client.upload_calls and fake_blob_client.upload_calls[0][1] is False
    assert fake_blob_client.upload_calls[0][2] == "*"


def test_write_roster_uses_azurewebjobsstorage_account_name_fallback(monkeypatch):
    fake_blob_client = _FakeBlobClient()
    fake_service_client = _FakeServiceClient(fake_blob_client)
    blob_service_client_calls = []

    monkeypatch.delenv("STORAGE_ACCOUNT_NAME", raising=False)
    monkeypatch.setenv("AzureWebJobsStorage__accountName", "acct456")
    monkeypatch.setattr(blob_writer, "DefaultAzureCredential", lambda: object())
    monkeypatch.setattr(
        blob_writer,
        "BlobServiceClient",
        lambda account_url, credential: blob_service_client_calls.append((account_url, credential))
        or fake_service_client,
    )

    blob_writer.write_roster({"players": []}, "2026-04-01")

    assert blob_service_client_calls[0][0] == "https://acct456.blob.core.windows.net"


def test_write_failed_raises_resource_exists_for_duplicate_write(monkeypatch):
    fake_blob_client = _FakeBlobClient(should_raise=True)
    fake_service_client = _FakeServiceClient(fake_blob_client)

    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "acct123")
    monkeypatch.setattr(blob_writer, "DefaultAzureCredential", lambda: object())
    monkeypatch.setattr(blob_writer, "BlobServiceClient", lambda account_url, credential: fake_service_client)

    with pytest.raises(ResourceExistsError):
        blob_writer.write_failed("raw response", "2026-03-31")


def test_write_roster_requires_storage_account_env_var(monkeypatch):
    monkeypatch.delenv("STORAGE_ACCOUNT_NAME", raising=False)
    monkeypatch.delenv("AzureWebJobsStorage__accountName", raising=False)

    with pytest.raises(ValueError):
        blob_writer.write_roster({"players": []}, "2026-03-31")
