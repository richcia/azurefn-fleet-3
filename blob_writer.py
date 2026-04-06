import json
from datetime import date

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

CONTAINER_NAME = "yankees-roster"


def get_blob_name(run_date: date | None = None) -> str:
    """Return the blob name for a given date (defaults to today).

    Args:
        run_date: The date to use for the blob name. Defaults to today.

    Returns:
        Blob name in the form ``roster-YYYY-MM-DD.json``.
    """
    if run_date is None:
        run_date = date.today()
    return f"roster-{run_date.isoformat()}.json"


def write_roster_to_blob(
    players: list,
    storage_account_name: str,
    blob_name: str | None = None,
) -> None:
    """Serialize the player list as JSON and write it to the 'yankees-roster' container.

    Uses DefaultAzureCredential (Managed Identity) — no connection string or key required.
    If the blob already exists it is overwritten, making the operation idempotent.

    Args:
        players: List of player records to store.
        storage_account_name: Azure Storage Account name (without .blob.core.windows.net).
        blob_name: Blob name to write. Defaults to ``roster-YYYY-MM-DD.json`` for today.
    """
    if blob_name is None:
        blob_name = get_blob_name()

    credential = DefaultAzureCredential()
    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    service_client = BlobServiceClient(account_url=account_url, credential=credential)
    container_client = service_client.get_container_client(CONTAINER_NAME)
    blob_client = container_client.get_blob_client(blob_name)
    data = json.dumps(players, indent=2)
    blob_client.upload_blob(data, overwrite=True)
