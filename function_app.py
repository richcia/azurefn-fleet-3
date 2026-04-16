"""Azure Function App — nightly 1985 Yankees roster sync."""

import json
import logging
import os
from datetime import datetime, timezone

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

import blob_writer
import trapi_client

app = func.FunctionApp()

logger = logging.getLogger("function_app")
_FAILURE_CREDENTIAL = DefaultAzureCredential()


def _validate_roster_schema(roster: list) -> None:
    player_count = len(roster)
    if player_count < 24 or player_count > 28:
        raise ValueError(
            f"Expected 24-28 players in roster, received {player_count}"
        )

    for idx, player in enumerate(roster):
        if not isinstance(player, dict):
            raise ValueError(f"Player at index {idx} is not an object")
        for field in ("name", "position", "jersey_number"):
            if field not in player:
                raise ValueError(
                    f"Player at index {idx} missing required field '{field}'"
                )


def _write_failed_blob(payload: dict) -> str:
    account_name = os.environ.get("STORAGE_ACCOUNT_NAME")
    if not account_name:
        raise ValueError("STORAGE_ACCOUNT_NAME environment variable is not set")

    account_url = f"https://{account_name}.blob.core.windows.net"
    blob_name = f"failed/roster-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    client = BlobServiceClient(
        account_url=account_url, credential=_FAILURE_CREDENTIAL, retry_total=0
    )
    blob_client = client.get_blob_client(container="yankees-roster", blob=blob_name)
    blob_client.upload_blob(
        json.dumps(payload),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json; charset=utf-8"),
    )
    return blob_name


@app.function_name(name="GetAndStoreYankeesRoster")
@app.timer_trigger(
    schedule="0 0 2 * * *",  # Six-field Azure CRON: second minute hour day month dayOfWeek — UTC
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True,
)
def get_and_store_yankees_roster(mytimer: func.TimerRequest) -> None:
    """Fetch the 1985 Yankees roster from TRAPI and persist it to Blob Storage."""
    roster = None
    player_count = 0
    logger.info(
        "get_and_store_yankees_roster: starting (past_due=%s)",
        mytimer.past_due,
        extra={
            "custom_dimensions": {"event": "function_started", "past_due": mytimer.past_due}
        },
    )

    try:
        logger.info(
            "get_and_store_yankees_roster: sending TRAPI request",
            extra={"custom_dimensions": {"event": "trapi_request_sent"}},
        )
        roster = trapi_client.fetch_1985_yankees_roster()
        _validate_roster_schema(roster)
        player_count = len(roster)
        logger.info(
            "get_and_store_yankees_roster: received TRAPI response with %d players",
            player_count,
            extra={
                "custom_dimensions": {
                    "event": "trapi_response_received",
                    "player_count": player_count,
                },
                "custom_measurements": {"player_count_returned": player_count},
            },
        )

        blob_name = blob_writer.write_roster_blob(roster)
        logger.info(
            "get_and_store_yankees_roster: roster written to blob %s",
            blob_name,
            extra={
                "custom_dimensions": {
                    "event": "blob_write_succeeded",
                    "blob_name": blob_name,
                    "player_count": player_count,
                }
            },
        )
        logger.info(
            "get_and_store_yankees_roster: complete",
            extra={"custom_dimensions": {"event": "function_completed"}},
        )
    except Exception as exc:
        failure_blob_name = None
        try:
            failure_blob_name = _write_failed_blob(
                {"error": str(exc), "roster": roster, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
            )
        except Exception:
            logger.exception(
                "get_and_store_yankees_roster: failed to persist failure payload",
                extra={"custom_dimensions": {"event": "failure_blob_write_failed"}},
            )
        logger.exception(
            "get_and_store_yankees_roster: failed — %s",
            exc,
            extra={
                "custom_dimensions": {
                    "event": "function_failed",
                    "error": str(exc),
                    "failure_blob_name": failure_blob_name,
                },
                "custom_measurements": {"player_count_returned": player_count},
            },
        )
        raise
