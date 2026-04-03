"""
blob_writer.py – uploads a roster list as JSON to Azure Blob Storage.

Authentication is performed exclusively via DefaultAzureCredential (no
connection strings, account keys, or SAS tokens).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

CONTAINER_NAME = "yankees-roster"


def get_blob_name(date: Optional[datetime] = None) -> str:
    """Return a timestamped blob name for the given date (defaults to today UTC).

    Parameters
    ----------
    date:
        Optional datetime to use for the timestamp. Defaults to ``datetime.now(timezone.utc)``.

    Returns
    -------
    str
        Blob name in the format ``roster-YYYYMMDD.json``.
    """
    if date is None:
        date = datetime.now(timezone.utc)
    return f"roster-{date.strftime('%Y%m%d')}.json"


def write_roster(
    players: list,
    storage_account_name: Optional[str] = None,
    date: Optional[datetime] = None,
    credential: Optional[object] = None,
) -> str:
    """Serialize *players* to JSON and upload it to the 'yankees-roster' blob container.

    Authentication is performed via ``DefaultAzureCredential``; no connection
    strings or account keys are used.

    Parameters
    ----------
    players:
        List of player objects to serialize as JSON. Must be JSON-serialisable.
    storage_account_name:
        Azure Storage account name (e.g. ``"mystorageacct"``).  If omitted,
        the value of the ``STORAGE_ACCOUNT_NAME`` environment variable is used.
    date:
        Optional timezone-aware datetime (preferably UTC) to use for the blob
        name. Defaults to ``datetime.now(timezone.utc)`` (UTC today).
    credential:
        Optional Azure credential object. Defaults to ``DefaultAzureCredential()``.

    Returns
    -------
    str
        The blob name that was written (e.g. ``roster-20250101.json``).

    Raises
    ------
    EnvironmentError
        If ``storage_account_name`` is not provided and ``STORAGE_ACCOUNT_NAME``
        environment variable is not set.
    azure.core.exceptions.ClientAuthenticationError
        If authentication via DefaultAzureCredential fails.
    azure.core.exceptions.ResourceExistsError
        If the blob already exists and ``overwrite`` is not True.
    """
    if storage_account_name is None:
        storage_account_name = os.environ.get("STORAGE_ACCOUNT_NAME")
        if not storage_account_name:
            raise EnvironmentError(
                "Required environment variable 'STORAGE_ACCOUNT_NAME' is not set."
            )

    if credential is None:
        credential = DefaultAzureCredential()

    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    service_client = BlobServiceClient(account_url=account_url, credential=credential)

    blob_name = get_blob_name(date)
    blob_client = service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)

    data = json.dumps(players, ensure_ascii=False, indent=2).encode("utf-8")

    logger.info(
        "Uploading roster (%d players) to blob '%s' in container '%s' (account '%s')",
        len(players),
        blob_name,
        CONTAINER_NAME,
        storage_account_name,
    )

    blob_client.upload_blob(data, overwrite=True)

    logger.info("Upload complete: %s/%s", CONTAINER_NAME, blob_name)
    return blob_name


def main() -> None:
    """Entry point: read environment variables and write the roster to blob storage."""
    storage_account_name = os.environ.get("STORAGE_ACCOUNT_NAME")
    if not storage_account_name:
        raise EnvironmentError(
            "Required environment variable 'STORAGE_ACCOUNT_NAME' is not set."
        )
    roster = json.loads(os.environ.get("ROSTER_JSON", "[]"))
    blob_name = write_roster(roster, storage_account_name)
    print(f"Wrote roster to {CONTAINER_NAME}/{blob_name}")


if __name__ == "__main__":
    main()
