import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from azure.core.exceptions import HttpResponseError, ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


DATA_STORAGE_ACCOUNT_NAME_ENV = "DATA_STORAGE_ACCOUNT_NAME"
CONTAINER_NAME = "yankees-roster"
FAILED_PREFIX = "failed"

_DEFAULT_AZURE_CREDENTIAL = DefaultAzureCredential()
_LOGGER = logging.getLogger(__name__)


def _resolve_run_date_utc(run_date_utc: str | None = None) -> str:
    return run_date_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _is_duplicate_write_conflict(exc: HttpResponseError) -> bool:
    status_code = getattr(exc, "status_code", None)
    error_code = getattr(exc, "error_code", None)
    return (
        (status_code == 409 and error_code == "BlobAlreadyExists")
        or (status_code == 412 and error_code in {"ConditionNotMet", "PreconditionFailed"})
    )


class BlobWriter:
    def __init__(
        self,
        *,
        account_name: str | None = None,
        credential: Any | None = None,
        container_name: str = CONTAINER_NAME,
    ):
        resolved_account_name = account_name or os.getenv(DATA_STORAGE_ACCOUNT_NAME_ENV)
        if not resolved_account_name:
            raise ValueError(f"{DATA_STORAGE_ACCOUNT_NAME_ENV} is required")
        self._service_client = BlobServiceClient(
            account_url=f"https://{resolved_account_name}.blob.core.windows.net",
            credential=credential or _DEFAULT_AZURE_CREDENTIAL,
        )
        self._container_name = container_name

    def write(self, roster_json: dict[str, Any], run_date_utc: str | None = None) -> str | None:
        resolved_run_date_utc = _resolve_run_date_utc(run_date_utc)
        blob_client = self._service_client.get_blob_client(
            container=self._container_name,
            blob=f"{resolved_run_date_utc}.json",
        )

        try:
            blob_client.upload_blob(
                json.dumps(roster_json).encode("utf-8"),
                overwrite=False,
                if_none_match="*",
            )
        except ResourceExistsError:
            _LOGGER.info("blob_write_conflict", extra={"blob_uri": blob_client.url})
            return None
        except HttpResponseError as exc:
            if _is_duplicate_write_conflict(exc):
                _LOGGER.info("blob_write_conflict", extra={"blob_uri": blob_client.url})
                return None
            raise

        _LOGGER.info("blob_write_succeeded", extra={"blob_uri": blob_client.url})
        return blob_client.url

    def write_failed(self, response_payload: Any, run_date_utc: str | None = None) -> str:
        resolved_run_date_utc = _resolve_run_date_utc(run_date_utc)
        blob_client = self._service_client.get_blob_client(
            container=self._container_name,
            blob=f"{FAILED_PREFIX}/{resolved_run_date_utc}.json",
        )
        blob_client.upload_blob(
            json.dumps(response_payload).encode("utf-8"),
            overwrite=True,
        )
        _LOGGER.info("blob_write_succeeded", extra={"blob_uri": blob_client.url})
        return blob_client.url
