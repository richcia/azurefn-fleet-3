import logging
import time

import azure.functions as func

from blob_writer import write_roster_blob
from trapi_client import fetch_roster
from validator import validate

LOGGER = logging.getLogger(__name__)

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
    response_payload = fetch_roster()
    latency_ms = int((time.perf_counter() - started_at) * 1000)

    players = response_payload.get("players") if isinstance(response_payload, dict) else None
    player_count = len(players) if isinstance(players, list) else 0

    LOGGER.info(
        "TRAPI response received",
        extra={
            "event": "trapi_response_received",
            "player_count": player_count,
            "latency_ms": latency_ms,
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
    LOGGER.info(
        "Function completed",
        extra={
            "event": "function_completed",
            "player_count": validation_result.player_count,
            "blob_uri": blob_uri,
        },
    )
