import json
import logging
import os
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError


_LOGGER = logging.getLogger(__name__)


class BlobWriter:
    def __init__(self) -> None:
        account_name = os.getenv("ROSTER_STORAGE_ACCOUNT_NAME", "").strip()
        if not account_name:
            raise ValueError("ROSTER_STORAGE_ACCOUNT_NAME is required")

        self._container_name = os.getenv("ROSTER_CONTAINER_NAME", "yankees-roster")
        account_url = f"https://{account_name}.blob.core.windows.net"
        self._blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=DefaultAzureCredential(),
        )

    def write(self, payload: Any, run_date_utc: str) -> str | None:
        blob_client = self._blob_service_client.get_blob_client(
            container=self._container_name,
            blob=f"{run_date_utc}.json",
        )
        try:
            blob_client.upload_blob(json.dumps(payload), overwrite=False)
        except ResourceExistsError:
            return None

        _LOGGER.info("blob_write_succeeded", extra={"blob_uri": blob_client.url})
        return blob_client.url

    def write_failed(self, payload: Any, run_date_utc: str) -> str | None:
        blob_client = self._blob_service_client.get_blob_client(
            container=self._container_name,
            blob=f"failed/{run_date_utc}.json",
        )
        try:
            blob_client.upload_blob(json.dumps(payload), overwrite=False)
        except ResourceExistsError:
            return None
        return blob_client.url
