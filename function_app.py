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

os.environ["TZ"] = "UTC"
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
    player_count = 0

    try:
        prompt_text = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
        _log_event(
            "trapi_request_sent",
            model_version=os.getenv("TRAPI_DEPLOYMENT_NAME", "gpt-4o"),
            prompt_hash=hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        )

        raw_response = fetch_roster(str(PROMPT_PATH))
        payload = json.loads(raw_response)
        total_tokens = payload.get("usage", {}).get("total_tokens") if isinstance(payload, dict) else None

        roster_payload = payload
        if isinstance(payload, dict) and "players" not in payload:
            choices = payload.get("choices")
            first_choice = choices[0] if isinstance(choices, list) and choices else {}
            content = first_choice.get("message", {}).get("content")
            if isinstance(content, str):
                try:
                    roster_payload = json.loads(content)
                except json.JSONDecodeError:
                    roster_payload = {}
            elif isinstance(content, dict):
                roster_payload = content

        is_valid, data, error = validate_response(json.dumps(roster_payload))
        player_count = len(data["players"]) if is_valid and data else 0

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
        response_text = getattr(getattr(exc, "response", None), "text", None)
        failure_payload = raw_response or response_text or str(exc)
        blob_uri = write_failed(failure_payload, run_date)
        _log_event(
            "trapi_response_received",
            token_count=None,
            latency_ms=int((time.monotonic() - start) * 1000),
            player_count=0,
            error=str(exc),
        )
        _log_event("blob_write_succeeded", blob_uri=blob_uri, player_count=0)
        raise
    finally:
        _log_event(
            "function_completed",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
