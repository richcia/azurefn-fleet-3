import logging
import os
import time

import azure.functions as func
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import metrics

from blob_writer import write_roster_blob
from trapi_client import fetch_roster
from validator import validate

LOGGER = logging.getLogger(__name__)
_AZURE_MONITOR_CONFIGURED = False
_METER = metrics.get_meter(__name__)
_PLAYER_COUNT_RETURNED_COUNTER = _METER.create_counter(
    "player_count_returned",
    unit="1",
    description="Count of players returned after successful roster validation.",
)


def _configure_azure_monitor_if_available() -> None:
    global _AZURE_MONITOR_CONFIGURED
    if _AZURE_MONITOR_CONFIGURED:
        return
    if not os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        return
    try:
        configure_azure_monitor()
        _AZURE_MONITOR_CONFIGURED = True
    except Exception:
        LOGGER.exception("Failed to configure Azure Monitor OpenTelemetry")


_configure_azure_monitor_if_available()

app = func.FunctionApp()


@app.function_name(name="GetAndStoreYankeesRoster")
@app.timer_trigger(
    arg_name="timer",
    schedule="0 0 2 * * *",
    run_on_startup=False,
    use_monitor=True,
)
def get_and_store_yankees_roster(timer: func.TimerRequest) -> None:
    LOGGER.info(
        "Function started",
        extra={
            "event": "function_started",
            "schedule": "0 0 2 * * *",
            "past_due": bool(getattr(timer, "past_due", False)),
        },
    )

    started_at = time.perf_counter()
    response_payload, token_count = fetch_roster()
    latency_ms = int((time.perf_counter() - started_at) * 1000)

    players = response_payload.get("players") if isinstance(response_payload, dict) else None
    player_count = len(players) if isinstance(players, list) else 0

    LOGGER.info(
        "TRAPI response received",
        extra={
            "event": "trapi_response_received",
            "player_count": player_count,
            "latency_ms": latency_ms,
            "token_count": token_count,
        },
    )

    validation_result = validate(response_payload)
    if not validation_result.is_valid:
        failed_blob_uri = write_roster_blob(response_payload, validation_result)
        raise RuntimeError(
            "Roster validation failed "
            f"(code={validation_result.error_code}, message={validation_result.error_message}, failed_blob_uri={failed_blob_uri})"
        )

    blob_uri = write_roster_blob(response_payload, validation_result)
    try:
        _PLAYER_COUNT_RETURNED_COUNTER.add(validation_result.player_count)
    except Exception:
        LOGGER.warning(
            "Failed to emit player_count_returned metric",
            extra={"event": "player_count_metric_emit_failed", "player_count": validation_result.player_count},
            exc_info=True,
        )
    LOGGER.info(
        "Function completed",
        extra={
            "event": "function_completed",
            "player_count": validation_result.player_count,
            "blob_uri": blob_uri,
        },
    )
