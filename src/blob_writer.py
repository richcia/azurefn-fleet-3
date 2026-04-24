import json
import logging
import os
from typing import Any

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, ContentSettings

_DEFAULT_AZURE_CREDENTIAL = DefaultAzureCredential()
_LOGGER = logging.getLogger(__name__)

_CONTAINER_NAME_DEFAULT = "yankees-roster"


class BlobWriter:
    """Writes roster payloads to Azure Blob Storage using Managed Identity auth."""

    def __init__(self) -> None:
        storage_account_name = os.getenv("ROSTER_STORAGE_ACCOUNT_NAME", "").strip()
        if not storage_account_name:
            raise ValueError(
                "ROSTER_STORAGE_ACCOUNT_NAME environment variable is required but not set."
            )
        self._account_url = f"https://{storage_account_name}.blob.core.windows.net"
        self._container_name = os.getenv("ROSTER_CONTAINER_NAME", _CONTAINER_NAME_DEFAULT).strip()

    def _get_blob_client(self, blob_name: str) -> BlobClient:
        return BlobClient(
            account_url=self._account_url,
            container_name=self._container_name,
            blob_name=blob_name,
            credential=_DEFAULT_AZURE_CREDENTIAL,
        )

    def write(self, payload: Any, run_date_utc: str) -> str | None:
        """Upload payload to yankees-roster/{run_date_utc}.json using a conditional PUT.

        Returns the blob URI on success, or None if the blob already exists (409 conflict).
        Non-conflict errors (transient, auth) propagate to the caller.
        """
        blob_name = f"{run_date_utc}.json"
        blob_client = self._get_blob_client(blob_name)
        data = json.dumps(payload, indent=2)
        try:
            # overwrite=False combined with if_none_match="*" ensures a conditional PUT
            # (If-None-Match: *) that prevents duplicate writes on same-day retrigger.
            blob_client.upload_blob(
                data=data,
                overwrite=False,
                content_settings=ContentSettings(content_type="application/json"),
                if_none_match="*",
            )
        except ResourceExistsError:
            _LOGGER.warning(
                "blob_write_conflict",
                extra={"blob_name": blob_name, "run_date_utc": run_date_utc},
            )
            return None
        blob_uri = blob_client.url
        _LOGGER.info("blob_write_succeeded", extra={"blob_uri": blob_uri})
        return blob_uri

    def write_failed(self, payload: Any, run_date_utc: str) -> None:
        """Upload payload to yankees-roster/failed/{run_date_utc}.json with overwrite=True."""
        blob_name = f"failed/{run_date_utc}.json"
        blob_client = self._get_blob_client(blob_name)
        data = json.dumps(payload, indent=2)
        try:
            blob_client.upload_blob(
                data=data,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json"),
            )
        except Exception:
            _LOGGER.exception(
                "blob_failed_write_error",
                extra={"blob_name": blob_name, "run_date_utc": run_date_utc},
            )
            raise
        _LOGGER.info("blob_failed_write_succeeded", extra={"blob_name": blob_name})
