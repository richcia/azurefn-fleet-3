"""Azure Function App — nightly 1985 Yankees roster sync."""

import hashlib
import logging
import os
import time

import azure.functions as func
from opentelemetry.metrics import get_meter

import blob_writer
import trapi_client
from azure.monitor.opentelemetry import configure_azure_monitor

app = func.FunctionApp()

logger = logging.getLogger("function_app")
_OTEL_CONFIGURED = False
_METER = get_meter("function_app")
_PLAYER_COUNT_METRIC = _METER.create_histogram(
    "player_count_returned",
    unit="{players}",
    description="Number of players returned for successful roster sync runs.",
)


def _configure_opentelemetry() -> None:
    global _OTEL_CONFIGURED
    if _OTEL_CONFIGURED:
        return

    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        return

    configure_azure_monitor(connection_string=connection_string)
    _OTEL_CONFIGURED = True


def _build_dimensions(
    *,
    event: str,
    model_version: str,
    prompt_hash: str,
    token_count: int,
    latency_ms: int,
    player_count: int,
    blob_uri: str,
    **extra_dimensions: object,
) -> dict:
    dimensions = {
        "event": event,
        "model_version": model_version,
        "prompt_hash": prompt_hash,
        "token_count": token_count,
        "latency_ms": latency_ms,
        "player_count": player_count,
        "blob_uri": blob_uri,
    }
    dimensions.update(extra_dimensions)
    return dimensions


_configure_opentelemetry()


@app.timer_trigger(
    schedule="0 0 0 * * *",  # Six-field Azure CRON: second minute hour day month dayOfWeek — runs at 00:00:00 UTC daily
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True,
)
def nightly_roster_sync(mytimer: func.TimerRequest) -> None:
    """Fetch the 1985 Yankees roster from TRAPI and persist it to Blob Storage."""
    model_version = os.environ.get("TRAPI_DEPLOYMENT_NAME", "gpt-4o")
    prompt_hash = hashlib.sha256(trapi_client._USER_PROMPT.encode("utf-8")).hexdigest()[:16]
    token_count = -1
    player_count = 0
    blob_uri = ""

    logger.info(
        "nightly_roster_sync: function_started",
        extra={
            "custom_dimensions": _build_dimensions(
                event="function_started",
                model_version=model_version,
                prompt_hash=prompt_hash,
                token_count=token_count,
                latency_ms=0,
                player_count=player_count,
                blob_uri=blob_uri,
                past_due=mytimer.past_due,
            )
        },
    )

    try:
        trapi_started_at = time.perf_counter()
        logger.info(
            "nightly_roster_sync: trapi_request_sent",
            extra={
                "custom_dimensions": _build_dimensions(
                    event="trapi_request_sent",
                    model_version=model_version,
                    prompt_hash=prompt_hash,
                    token_count=token_count,
                    latency_ms=0,
                    player_count=player_count,
                    blob_uri=blob_uri,
                )
            },
        )
        roster = trapi_client.fetch_1985_yankees_roster()
        latency_ms = int((time.perf_counter() - trapi_started_at) * 1000)
        player_count = len(roster)
        logger.info(
            "nightly_roster_sync: trapi_response_received",
            extra={
                "custom_dimensions": _build_dimensions(
                    event="trapi_response_received",
                    model_version=model_version,
                    prompt_hash=prompt_hash,
                    token_count=token_count,
                    latency_ms=latency_ms,
                    player_count=player_count,
                    blob_uri=blob_uri,
                )
            },
        )

        blob_name = blob_writer.write_roster_blob(roster)
        storage_account = os.environ.get("STORAGE_ACCOUNT_NAME")
        blob_uri = (
            f"https://{storage_account}.blob.core.windows.net/yankees-roster/{blob_name}"
            if storage_account
            else blob_name
        )
        logger.info(
            "nightly_roster_sync: blob_write_succeeded",
            extra={
                "custom_dimensions": _build_dimensions(
                    event="blob_write_succeeded",
                    model_version=model_version,
                    prompt_hash=prompt_hash,
                    token_count=token_count,
                    latency_ms=latency_ms,
                    player_count=player_count,
                    blob_uri=blob_uri,
                )
            },
        )
        _PLAYER_COUNT_METRIC.record(
            player_count,
            attributes={
                "event": "function_completed",
                "model_version": model_version,
                "prompt_hash": prompt_hash,
                "blob_uri": blob_uri,
                "player_count_returned": player_count,
            },
        )
        logger.info(
            "nightly_roster_sync: function_completed",
            extra={
                "custom_dimensions": _build_dimensions(
                    event="function_completed",
                    model_version=model_version,
                    prompt_hash=prompt_hash,
                    token_count=token_count,
                    latency_ms=latency_ms,
                    player_count=player_count,
                    blob_uri=blob_uri,
                )
            },
        )
    except Exception as exc:
        logger.exception(
            "nightly_roster_sync: function_failed",
            extra={
                "custom_dimensions": _build_dimensions(
                    event="function_failed",
                    model_version=model_version,
                    prompt_hash=prompt_hash,
                    token_count=token_count,
                    latency_ms=0,
                    player_count=player_count,
                    blob_uri=blob_uri,
                    error_type=type(exc).__name__,
                )
            },
        )
        raise
