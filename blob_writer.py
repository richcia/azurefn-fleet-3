"""
blob_writer.py – uploads a roster list as JSON to Azure Blob Storage.

Authentication is performed exclusively via DefaultAzureCredential (no
connection strings, account keys, or SAS tokens).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

_DEFAULT_BLOB_NAME = "roster.json"
_CONTAINER_NAME = "yankees-roster"


def upload_roster(
    roster: list[Any],
    storage_account_name: str,
    blob_name: str = _DEFAULT_BLOB_NAME,
    *,
    overwrite: bool = True,
    timestamped: bool = False,
) -> str:
    """Serialize *roster* to JSON and upload it to Azure Blob Storage.

    Parameters
    ----------
    roster:
        List of player objects (must be JSON-serialisable).
    storage_account_name:
        Name of the Azure Storage Account (e.g. ``"mystorageacct"``).
    blob_name:
        Target blob name inside the container.  Defaults to
        ``"roster.json"``.
    overwrite:
        If ``True`` (default) an existing blob is silently overwritten.
        Pass ``False`` to raise an error when the blob already exists.
    timestamped:
        When ``True`` the current UTC timestamp is embedded in the blob
        name, e.g. ``"roster_20250101T120000Z.json"``.  *blob_name* is
        used as a prefix in that case.

    Returns
    -------
    str
        The final blob name that was used for the upload.

    Raises
    ------
    azure.core.exceptions.ResourceNotFoundError
        If the target container does not exist.
    azure.core.exceptions.ClientAuthenticationError
        If authentication via DefaultAzureCredential fails.
    """
    if timestamped:
        stem = blob_name.removesuffix(".json")
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        blob_name = f"{stem}_{ts}.json"

    payload = json.dumps(roster, ensure_ascii=False, indent=2)
    data = payload.encode("utf-8")

    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential()

    logger.info(
        "Uploading roster to blob '%s' in container '%s' (account '%s')",
        blob_name,
        _CONTAINER_NAME,
        storage_account_name,
    )

    blob_service_client = BlobServiceClient(account_url, credential=credential)
    container_client = blob_service_client.get_container_client(_CONTAINER_NAME)

    # Proactively check that the container exists so we can raise a clear error.
    if not container_client.exists():
        raise ResourceNotFoundError(
            f"Container '{_CONTAINER_NAME}' not found in storage account "
            f"'{storage_account_name}'.  Ensure the container has been provisioned."
        )

    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(data, overwrite=overwrite, content_type="application/json")

    logger.info("Upload complete: %s", blob_name)
    return blob_name
