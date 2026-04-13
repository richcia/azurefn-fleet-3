"""Blob writer for storing the Yankees roster to Azure Blob Storage."""

import json
import os
from datetime import datetime, timezone

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

_CREDENTIAL = DefaultAzureCredential()

_CONTAINER_NAME = "yankees-roster"


def write_roster_blob(roster: list) -> str:
    """Write the roster list as a JSON blob to Azure Blob Storage.

    The blob is named ``roster-YYYYMMDD.json`` using today's UTC date and
    stored in the ``yankees-roster`` container.

    Configuration is read from environment variables:
        STORAGE_ACCOUNT_NAME - Azure Storage account name (required)

    Authentication uses DefaultAzureCredential — no connection strings or keys.

    Args:
        roster: List of player dicts to serialise and upload.

    Returns:
        The blob name (e.g. ``roster-20240101.json``).

    Raises:
        ValueError: If STORAGE_ACCOUNT_NAME is not set.
    """
    account_name = os.environ.get("STORAGE_ACCOUNT_NAME")
    if not account_name:
        raise ValueError("STORAGE_ACCOUNT_NAME environment variable is not set")

    account_url = f"https://{account_name}.blob.core.windows.net"
    blob_name = f"roster-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"

    client = BlobServiceClient(account_url=account_url, credential=_CREDENTIAL)
    blob_client = client.get_blob_client(container=_CONTAINER_NAME, blob=blob_name)
    blob_client.upload_blob(json.dumps(roster), overwrite=True)

    return blob_name
