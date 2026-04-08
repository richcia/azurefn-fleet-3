"""Blob writer module for persisting the 1985 NY Yankees roster to Azure Blob Storage."""

import json
import os
from datetime import datetime, timezone

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

_CONTAINER_NAME = "yankees-roster"

_DEFAULT_AZURE_CREDENTIAL = DefaultAzureCredential()


def write_roster_blob(players: list[dict], credential=None) -> str:
    """Write the roster JSON to the 'yankees-roster' container in Azure Blob Storage.

    Authentication uses ``DefaultAzureCredential`` — no connection strings or
    account keys are used.

    Environment variables:
        AZURE_STORAGE_ACCOUNT_NAME: Name of the Azure Storage account (required).
        BLOB_NAME: Fixed blob name to use instead of a timestamped name (optional).

    Args:
        players: List of player dicts (each with at least ``name`` and ``position``).
        credential: Azure credential to use (defaults to a shared
            ``DefaultAzureCredential`` instance).

    Returns:
        The blob name that was written.

    Raises:
        ValueError: If ``AZURE_STORAGE_ACCOUNT_NAME`` is not set.
    """
    account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "").strip()
    if not account_name:
        raise ValueError(
            "AZURE_STORAGE_ACCOUNT_NAME environment variable is not set. "
            "Set it to the name of your Azure Storage account."
        )

    blob_name = os.environ.get("BLOB_NAME", "").strip()
    if not blob_name:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        blob_name = f"roster_{timestamp}.json"

    account_url = f"https://{account_name}.blob.core.windows.net"
    credential = credential or _DEFAULT_AZURE_CREDENTIAL

    service_client = BlobServiceClient(account_url=account_url, credential=credential)
    blob_client = service_client.get_blob_client(
        container=_CONTAINER_NAME, blob=blob_name
    )

    content = json.dumps(players, ensure_ascii=False)
    blob_client.upload_blob(content, overwrite=True)

    return blob_name
