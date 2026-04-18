import json
import os
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

_CONTAINER_NAME = "yankees-roster"
_STORAGE_ACCOUNT_ENV_VARS = ("STORAGE_ACCOUNT_NAME", "AzureWebJobsStorage__accountName")


def _get_storage_account_name() -> str:
    for env_var in _STORAGE_ACCOUNT_ENV_VARS:
        value = os.getenv(env_var)
        if value:
            return value

    raise ValueError(
        "Storage account name is not configured. "
        "Set STORAGE_ACCOUNT_NAME or AzureWebJobsStorage__accountName."
    )


def _get_blob_client(blob_name: str):
    account_name = _get_storage_account_name()
    service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    return service_client.get_blob_client(container=_CONTAINER_NAME, blob=blob_name)


def write_roster(data: Any, run_date_utc: str) -> None:
    blob_name = f"{run_date_utc}.json"
    payload = json.dumps(data).encode("utf-8")
    blob_client = _get_blob_client(blob_name)
    blob_client.upload_blob(payload, overwrite=False, if_none_match="*")


def write_failed(raw: Any, run_date_utc: str) -> None:
    blob_name = f"failed/{run_date_utc}.json"
    if isinstance(raw, bytes):
        payload = raw
    elif isinstance(raw, str):
        payload = raw.encode("utf-8")
    else:
        payload = json.dumps(raw).encode("utf-8")

    blob_client = _get_blob_client(blob_name)
    blob_client.upload_blob(payload, overwrite=False, if_none_match="*")
