import json
import os
from datetime import date
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

CONTAINER_NAME = "yankees-roster"


def _blob_service_client() -> BlobServiceClient:
    account_name = os.environ["STORAGE_ACCOUNT_NAME"]
    account_url = f"https://{account_name}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())


def write_roster(data: dict[str, Any], run_date_utc: date) -> str:
    blob_name = f"{run_date_utc.isoformat()}.json"
    blob_client = _blob_service_client().get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    blob_client.upload_blob(json.dumps(data), overwrite=False)
    return f"{CONTAINER_NAME}/{blob_name}"


def write_failed(raw: str, run_date_utc: date) -> str:
    blob_name = f"failed/{run_date_utc.isoformat()}.json"
    blob_client = _blob_service_client().get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    blob_client.upload_blob(raw, overwrite=True)
    return f"{CONTAINER_NAME}/{blob_name}"
