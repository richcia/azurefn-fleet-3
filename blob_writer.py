import json

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

CONTAINER_NAME = "yankees-roster"
DEFAULT_BLOB_NAME = "roster.json"


def write_roster_to_blob(
    players: list,
    storage_account_name: str,
    blob_name: str = DEFAULT_BLOB_NAME,
) -> None:
    """Serialize the player list as JSON and write it to the 'yankees-roster' container.

    Args:
        players: List of player records to store.
        storage_account_name: Azure Storage Account name (without .blob.core.windows.net).
        blob_name: Blob name to write (defaults to roster.json, overwriting on each run).
    """
    credential = DefaultAzureCredential()
    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    service_client = BlobServiceClient(account_url=account_url, credential=credential)
    container_client = service_client.get_container_client(CONTAINER_NAME)
    blob_client = container_client.get_blob_client(blob_name)
    data = json.dumps(players, indent=2)
    blob_client.upload_blob(data, overwrite=True)
