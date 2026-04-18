from datetime import datetime

import blob_writer
from validator import ValidationResult


class DummyBlobClient:
    def __init__(self, url: str):
        self.url = url
        self.upload_calls = []
        self.raise_exists = False

    def upload_blob(self, data, overwrite, if_none_match):
        self.upload_calls.append(
            {
                "data": data,
                "overwrite": overwrite,
                "if_none_match": if_none_match,
            }
        )
        if self.raise_exists:
            raise blob_writer.ResourceExistsError("exists")


class DummyBlobServiceClient:
    def __init__(self):
        self.container = None
        self.blob = None
        self.blob_client = DummyBlobClient("https://data.blob.core.windows.net/yankees-roster/path")

    def get_blob_client(self, container, blob):
        self.container = container
        self.blob = blob
        self.blob_client.url = f"https://data.blob.core.windows.net/{container}/{blob}"
        return self.blob_client



def test_write_valid_roster_to_primary_prefix_with_conditional_put(monkeypatch):
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "data")

    dummy_service = DummyBlobServiceClient()
    monkeypatch.setattr(blob_writer, "_DEFAULT_AZURE_CREDENTIAL", object())
    monkeypatch.setattr(blob_writer, "BlobServiceClient", lambda account_url, credential: dummy_service)

    payload = {"players": [{"name": "Don Mattingly", "position": "1B", "jersey_number": 23}]}
    result = blob_writer.write_roster_blob(payload, ValidationResult(is_valid=True, player_count=1), "2026-04-18")

    assert dummy_service.container == "yankees-roster"
    assert dummy_service.blob == "2026-04-18.json"
    assert dummy_service.blob_client.upload_calls[0]["if_none_match"] == "*"
    assert dummy_service.blob_client.upload_calls[0]["overwrite"] is False
    assert result.endswith("/yankees-roster/2026-04-18.json")



def test_second_write_same_day_catches_resource_exists_and_logs(monkeypatch):
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "data")

    dummy_service = DummyBlobServiceClient()
    dummy_service.blob_client.raise_exists = True

    events = []
    monkeypatch.setattr(blob_writer, "_DEFAULT_AZURE_CREDENTIAL", object())
    monkeypatch.setattr(blob_writer, "BlobServiceClient", lambda account_url, credential: dummy_service)
    monkeypatch.setattr(blob_writer.LOGGER, "info", lambda message, extra: events.append(extra))

    uri = blob_writer.write_roster_blob(
        {"players": []},
        ValidationResult(is_valid=True, player_count=0),
        "2026-04-18",
    )

    assert events
    assert events[0]["event"] == "blob_write_skipped_exists"
    assert events[1]["event"] == "blob_write_succeeded"
    assert events[1]["write_status"] == "already_exists"
    assert uri.endswith("/yankees-roster/2026-04-18.json")
    assert dummy_service.blob_client.upload_calls[0]["if_none_match"] == "*"
    assert dummy_service.blob_client.upload_calls[0]["overwrite"] is False



def test_failed_validation_writes_to_failed_prefix(monkeypatch):
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "data")

    dummy_service = DummyBlobServiceClient()
    monkeypatch.setattr(blob_writer, "_DEFAULT_AZURE_CREDENTIAL", object())
    monkeypatch.setattr(blob_writer, "BlobServiceClient", lambda account_url, credential: dummy_service)

    payload = {"raw": "response"}
    uri = blob_writer.write_roster_blob(
        payload,
        ValidationResult(is_valid=False, player_count=0, error_message="bad", error_code="missing_players_array"),
        "2026-04-18",
    )

    assert dummy_service.blob == "failed/2026-04-18.json"
    assert uri.endswith("/yankees-roster/failed/2026-04-18.json")



def test_success_emits_blob_write_succeeded_with_blob_uri(monkeypatch):
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "data")

    dummy_service = DummyBlobServiceClient()
    events = []
    monkeypatch.setattr(blob_writer, "_DEFAULT_AZURE_CREDENTIAL", object())
    monkeypatch.setattr(blob_writer, "BlobServiceClient", lambda account_url, credential: dummy_service)
    monkeypatch.setattr(blob_writer.LOGGER, "info", lambda message, extra: events.append(extra))

    uri = blob_writer.write_roster_blob(
        {"players": []},
        ValidationResult(is_valid=True, player_count=0),
        "2026-04-18",
    )

    assert events
    assert events[0]["event"] == "blob_write_succeeded"
    assert events[0]["blob_uri"] == uri
    assert events[0]["write_status"] == "created"



def test_uses_default_azure_credential_and_data_storage_app_setting(monkeypatch):
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "myacct")

    seen = {}

    def fake_blob_service_client(account_url, credential):
        seen["account_url"] = account_url
        seen["credential"] = credential
        return DummyBlobServiceClient()

    credential = object()
    monkeypatch.setattr(blob_writer, "_DEFAULT_AZURE_CREDENTIAL", credential)
    monkeypatch.setattr(blob_writer, "BlobServiceClient", fake_blob_service_client)

    blob_writer.write_roster_blob(
        {"players": []},
        ValidationResult(is_valid=True, player_count=0),
        "2026-04-18",
    )

    assert seen["account_url"] == "https://myacct.blob.core.windows.net"
    assert seen["credential"] is credential


def test_default_run_date_uses_utc_date(monkeypatch):
    monkeypatch.setenv("DATA_STORAGE_ACCOUNT_NAME", "data")

    class FakeDatetime:
        @staticmethod
        def now(tz):
            assert tz is blob_writer.timezone.utc
            return datetime(2026, 4, 18, 2, 30, tzinfo=blob_writer.timezone.utc)

    dummy_service = DummyBlobServiceClient()
    monkeypatch.setattr(blob_writer, "_DEFAULT_AZURE_CREDENTIAL", object())
    monkeypatch.setattr(blob_writer, "BlobServiceClient", lambda account_url, credential: dummy_service)
    monkeypatch.setattr(blob_writer, "datetime", FakeDatetime)

    blob_writer.write_roster_blob(
        {"players": []},
        ValidationResult(is_valid=True, player_count=0),
    )

    assert dummy_service.blob == "2026-04-18.json"
