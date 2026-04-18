from datetime import date
from unittest.mock import MagicMock

import blob_writer


class _BlobServiceClientFake:
    def __init__(self):
        self.blob_client = MagicMock()

    def get_blob_client(self, container, blob):
        self.container = container
        self.blob = blob
        return self.blob_client


def test_write_roster_uses_expected_path_and_no_overwrite(monkeypatch):
    fake = _BlobServiceClientFake()
    monkeypatch.setattr(blob_writer, "_blob_service_client", lambda: fake)

    result = blob_writer.write_roster({"players": []}, date(2026, 1, 2))

    assert result == "yankees-roster/2026-01-02.json"
    fake.blob_client.upload_blob.assert_called_once()
    assert fake.blob_client.upload_blob.call_args.kwargs["overwrite"] is False


def test_write_failed_uses_failed_prefix(monkeypatch):
    fake = _BlobServiceClientFake()
    monkeypatch.setattr(blob_writer, "_blob_service_client", lambda: fake)

    result = blob_writer.write_failed("raw", date(2026, 1, 2))

    assert result == "yankees-roster/failed/2026-01-02.json"
    fake.blob_client.upload_blob.assert_called_once_with("raw", overwrite=True)
