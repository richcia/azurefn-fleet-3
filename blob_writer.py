import json
import os
from datetime import datetime, timezone
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

CONTAINER_NAME = "yankees-roster"


def get_blob_name(date: Optional[datetime] = None) -> str:
    """Return a timestamped blob name for the given date (defaults to today UTC)."""
    if date is None:
        date = datetime.now(timezone.utc)
    return f"roster-{date.strftime('%Y%m%d')}.json"


def write_roster(
    roster: list,
    storage_account_name: str,
    date: Optional[datetime] = None,
    credential: Optional[object] = None,
) -> str:
    """Write the player roster as UTF-8 JSON to the 'yankees-roster' blob container.

    Args:
        roster: List of player records to serialize as JSON.
        storage_account_name: Azure Storage account name (without .blob.core.windows.net).
        date: Optional date override for the blob name (defaults to UTC today).
        credential: Optional Azure credential; defaults to DefaultAzureCredential().

    Returns:
        The blob name that was written.
    """

    if credential is None:
        credential = DefaultAzureCredential()

    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    service_client = BlobServiceClient(account_url=account_url, credential=credential)

    blob_name = get_blob_name(date)
    blob_client = service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)

    data = json.dumps(roster, ensure_ascii=False, indent=2).encode("utf-8")
    blob_client.upload_blob(data, overwrite=True)

    return blob_name


def main():
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
