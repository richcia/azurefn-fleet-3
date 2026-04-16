"""Blob writer for storing the Yankees roster to Azure Blob Storage."""

import json
import logging
import os
import time
from datetime import datetime, timezone

from azure.core.exceptions import HttpResponseError, ResourceExistsError, ServiceRequestError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger("blob_writer")

_CREDENTIAL = DefaultAzureCredential()

_CONTAINER_NAME = "yankees-roster"

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3  # maximum number of retry attempts after the initial request


def write_roster_blob(roster: object, *, failed: bool = False) -> str:
    """Write the roster list as a JSON blob to Azure Blob Storage.

    The blob is named ``YYYY-MM-DD.json`` using today's UTC date and stored in
    the ``yankees-roster`` container. Failed payloads are routed to the
    ``failed/`` blob prefix.

    Configuration is read from environment variables:
        STORAGE_ACCOUNT_NAME - Azure Storage account name (required)

    Authentication uses DefaultAzureCredential — no connection strings or keys.

    Args:
        roster: JSON-serializable payload to upload.
        failed: Whether to route the payload to ``failed/{run_date_utc}.json``.

    Returns:
        The blob name (e.g. ``2026-03-31.json`` or ``failed/2026-03-31.json``).

    Raises:
        ValueError: If STORAGE_ACCOUNT_NAME is not set.
        ServiceRequestError: If a transient network error persists after all
            retries are exhausted (e.g. connection timeout, DNS failure).
        HttpResponseError: If Azure Storage returns a non-transient HTTP error
            (e.g. 403 Forbidden), or returns 503 ServiceUnavailable and all
            retries are exhausted.
    """
    account_name = os.environ.get("STORAGE_ACCOUNT_NAME")
    if not account_name:
        raise ValueError("STORAGE_ACCOUNT_NAME environment variable is not set")

    account_url = f"https://{account_name}.blob.core.windows.net"
    run_date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blob_name = f"{'failed/' if failed else ''}{run_date_utc}.json"

    client = BlobServiceClient(
        account_url=account_url, credential=_CREDENTIAL, retry_total=0
    )
    blob_client = client.get_blob_client(container=_CONTAINER_NAME, blob=blob_name)

    for attempt in range(_MAX_RETRIES + 1):
        delay = 2 ** attempt  # 1 s, 2 s, 4 s between retries
        try:
            blob_client.upload_blob(
                json.dumps(roster),
                overwrite=False,
                if_none_match="*",
                content_settings=ContentSettings(content_type="application/json; charset=utf-8"),
            )
            logger.info(
                "blob_write_succeeded",
                extra={
                    "custom_dimensions": {
                        "event": "blob_write_succeeded",
                        "blob_uri": blob_client.url,
                    }
                },
            )
            return blob_name
        except ResourceExistsError:
            raise
        except ServiceRequestError as exc:
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "Transient storage error on attempt %d/%d; retrying in %ds: %s",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    delay,
                    exc,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Blob upload failed after %d retries — account=%s, blob=%s: %s",
                    _MAX_RETRIES,
                    account_name,
                    blob_name,
                    exc,
                )
                raise
        except HttpResponseError as exc:
            if exc.status_code == 503 and attempt < _MAX_RETRIES:
                logger.warning(
                    "ServiceUnavailable (503) on attempt %d/%d; retrying in %ds: %s",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    delay,
                    exc,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Blob upload HTTP error — account=%s, blob=%s, status=%s: %s",
                    account_name,
                    blob_name,
                    exc.status_code,
                    exc,
                )
                raise
