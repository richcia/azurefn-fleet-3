import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from validator import ValidationResult

LOGGER = logging.getLogger(__name__)

CONTAINER_NAME = "yankees-roster"
DATA_STORAGE_ACCOUNT_NAME_ENV = "DATA_STORAGE_ACCOUNT_NAME"

_DEFAULT_AZURE_CREDENTIAL = DefaultAzureCredential()


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _resolve_run_date_utc(run_date_utc: str | None = None) -> str:
    if run_date_utc:
        return run_date_utc
    return datetime.now(timezone.utc).date().isoformat()


def _build_blob_service_client() -> BlobServiceClient:
    account_name = _get_required_env(DATA_STORAGE_ACCOUNT_NAME_ENV)
    account_url = f"https://{account_name}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=_DEFAULT_AZURE_CREDENTIAL)


def _upload_json(blob_name: str, payload: Any) -> str:
    blob_client = _build_blob_service_client().get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    blob_uri = blob_client.url
    data = json.dumps(payload)

    try:
        blob_client.upload_blob(data=data, overwrite=False, if_none_match="*")
    except ResourceExistsError:
        LOGGER.info(
            "Blob already exists for run date; skipping duplicate write",
            extra={"event": "blob_write_skipped_exists", "blob_uri": blob_uri},
        )
        return blob_uri

    LOGGER.info("Blob write succeeded", extra={"event": "blob_write_succeeded", "blob_uri": blob_uri})
    return blob_uri


def write_roster_blob(response_payload: Any, validation_result: ValidationResult, run_date_utc: str | None = None) -> str:
    run_date = _resolve_run_date_utc(run_date_utc)
    blob_name = (
        f"{run_date}.json"
        if validation_result.is_valid
        else f"failed/{run_date}.json"
    )
    return _upload_json(blob_name=blob_name, payload=response_payload)
