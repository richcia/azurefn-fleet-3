import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import azure.functions as func

from blob_writer import write_failed, write_roster
from response_validator import validate_response
from trapi_client import fetch_roster

os.environ.setdefault("TZ", "UTC")
if hasattr(time, "tzset"):
    time.tzset()

PROMPT_PATH = Path(__file__).parent / "prompts" / "get_1985_yankees.txt"
logger = logging.getLogger(__name__)
app = func.FunctionApp()


def _log_event(event: str, level: int = logging.INFO, **fields: object) -> None:
    logger.log(level, event, extra={"custom_dimensions": {"event": event, **fields}})


@app.timer_trigger(schedule="0 0 2 * * *", arg_name="mytimer", run_on_startup=False, use_monitor=True)
def get_and_store_yankees_roster(mytimer: func.TimerRequest) -> None:
    start = time.monotonic()
    now_utc = datetime.now(timezone.utc)
    run_date = now_utc.date()

    _log_event(
        "function_started",
        function_name="GetAndStoreYankeesRoster",
        trigger_timestamp=now_utc.isoformat(),
        past_due=getattr(mytimer, "past_due", False),
    )

    raw_response: str | None = None

    try:
        prompt_text = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
        _log_event(
            "trapi_request_sent",
            model_version=os.getenv("TRAPI_DEPLOYMENT_NAME", "gpt-4o"),
            prompt_hash=hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        )

        raw_response = fetch_roster(str(PROMPT_PATH))
        is_valid, data, error = validate_response(raw_response)

        player_count = len(data["players"]) if is_valid and data else 0
        total_tokens = None
        try:
            payload = json.loads(raw_response)
            total_tokens = payload.get("usage", {}).get("total_tokens")
        except json.JSONDecodeError:
            total_tokens = None

        _log_event(
            "trapi_response_received",
            token_count=total_tokens,
            latency_ms=int((time.monotonic() - start) * 1000),
            player_count=player_count,
        )

        if is_valid and data is not None:
            blob_uri = write_roster(data, run_date)
            _log_event("player_count_returned", metric_value=player_count)
        else:
            blob_uri = write_failed(raw_response, run_date)
            if error:
                logger.warning("Validation failed: %s", error)

        _log_event("blob_write_succeeded", blob_uri=blob_uri, player_count=player_count)
    except Exception as exc:
        failure_payload = raw_response if raw_response is not None else str(exc)
        blob_uri = write_failed(failure_payload, run_date)
        _log_event("blob_write_succeeded", blob_uri=blob_uri, player_count=0)
        raise
    finally:
        _log_event(
            "function_completed",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
