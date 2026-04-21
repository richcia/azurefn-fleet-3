import logging
import os
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

import azure.functions as func
from opentelemetry import metrics

from src.blob_writer import BlobWriter
from src.validator import validate_roster_response
from trapi_client import TRAPIRetryExhaustedError, RosterValidationError, fetch_1985_yankees_roster

app = func.FunctionApp()
_LOGGER = logging.getLogger(__name__)
_METER = metrics.get_meter(__name__)
_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "get_1985_yankees.txt"
_PLAYER_COUNT_RETURNED = _METER.create_counter(
    "player_count_returned",
    unit="players",
    description="Total players returned from TRAPI.",
)


def _prompt_hash() -> str:
    try:
        prompt_text = _PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()


@app.function_name(name="GetAndStoreYankeesRoster")
@app.timer_trigger(
    arg_name="timer",
    schedule="0 0 2 * * *",
    run_on_startup=False,
    use_monitor=True,
)
def get_and_store_yankees_roster(timer: func.TimerRequest) -> None:
    del timer
    run_date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    model_version = os.getenv("TRAPI_DEPLOYMENT_NAME", "")
    prompt_hash = _prompt_hash()
    _LOGGER.info("function_started", extra={"run_date_utc": run_date_utc})
    writer = BlobWriter()
    try:
        _LOGGER.info(
            "trapi_request_sent",
            extra={
                "model_version": model_version,
                "prompt_hash": prompt_hash,
            },
        )
        started = time.perf_counter()
        roster_payload = fetch_1985_yankees_roster()
        latency_ms = int((time.perf_counter() - started) * 1000)
        players_from_response = roster_payload.get("players", []) if isinstance(roster_payload, dict) else []
        player_count_from_response = len(players_from_response) if isinstance(players_from_response, list) else 0
        token_count = (
            int(roster_payload.get("usage", {}).get("total_tokens", 0))
            if isinstance(roster_payload, dict)
            else 0
        )
        _LOGGER.info(
            "trapi_response_received",
            extra={
                "token_count": token_count,
                "latency_ms": latency_ms,
                "player_count": player_count_from_response,
            },
        )
        validation_result = validate_roster_response(roster_payload)
        if not validation_result.is_valid:
            writer.write_failed(roster_payload, run_date_utc=run_date_utc)
            message = validation_result.error.message if validation_result.error else "Roster validation failed"
            raise RuntimeError(message)

        players = validation_result.players or []
        player_count = len(players)
        blob_uri = writer.write(roster_payload, run_date_utc=run_date_utc)
        _PLAYER_COUNT_RETURNED.add(player_count, {"run_date_utc": run_date_utc})
        _LOGGER.info(
            "function_completed",
            extra={
                "player_count": player_count,
                "blob_uri": blob_uri,
                "write_conflict": blob_uri is None,
            },
        )
    except RosterValidationError as exc:
        writer.write_failed(exc.response_payload, run_date_utc=run_date_utc)
        raise RuntimeError(str(exc)) from exc
    except TRAPIRetryExhaustedError as exc:
        writer.write_failed(exc.response_payload, run_date_utc=run_date_utc)
        raise RuntimeError(str(exc)) from exc
