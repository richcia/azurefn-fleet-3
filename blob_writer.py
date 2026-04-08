"""Azure Blob Storage writer for the 1985 Yankees roster."""

import json
import logging
import os
from datetime import datetime, timezone

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

_CONTAINER_NAME = "yankees-roster"
# Reused across invocations to avoid repeated token acquisition overhead.
_CREDENTIAL = DefaultAzureCredential()


def write_roster_blob(roster: list[dict]) -> str:
    """Write the roster JSON to Azure Blob Storage.

    Uses ``DefaultAzureCredential`` for authentication — no storage keys required.

    The ``yankees-roster`` container must exist before this function is called.
    It is provisioned automatically by the Bicep infrastructure templates under
    ``/infra/modules/storage.bicep``.

    Environment variables:
        STORAGE_ACCOUNT_NAME: Azure Storage account name (required).

    Args:
        roster: List of player dicts, each with at least ``name`` and ``position``.

    Returns:
        The blob name written (e.g. ``roster-20240101.json``).

    Raises:
        ValueError: If ``STORAGE_ACCOUNT_NAME`` is not set.
    """
    account_name = os.environ.get("STORAGE_ACCOUNT_NAME", "")
    if not account_name:
        raise ValueError(
            "STORAGE_ACCOUNT_NAME environment variable is not set. "
            "Set it to your Azure Storage account name."
        )

    account_url = f"https://{account_name}.blob.core.windows.net"
    client = BlobServiceClient(account_url=account_url, credential=_CREDENTIAL)

    blob_name = f"roster-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    blob_client = client.get_blob_client(container=_CONTAINER_NAME, blob=blob_name)

    data = json.dumps(roster, indent=2)
    # overwrite=True is intentional: one authoritative roster blob per day.
    blob_client.upload_blob(data, overwrite=True)

    return blob_name
