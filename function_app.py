"""Azure Function App — nightly 1985 Yankees roster sync."""

import logging

import azure.functions as func

import blob_writer
import trapi_client

app = func.FunctionApp()

logger = logging.getLogger("function_app")


@app.timer_trigger(
    schedule="0 0 0 * * *",  # Six-field Azure CRON: second minute hour day month dayOfWeek — runs at 00:00:00 UTC daily
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True,
)
def nightly_roster_sync(mytimer: func.TimerRequest) -> None:
    """Fetch the 1985 Yankees roster from TRAPI and persist it to Blob Storage."""
    logger.info(
        "nightly_roster_sync: starting (past_due=%s)",
        mytimer.past_due,
        extra={"custom_dimensions": {"event": "function_start", "past_due": mytimer.past_due}},
    )

    try:
        logger.info(
            "nightly_roster_sync: initiating TRAPI call",
            extra={"custom_dimensions": {"event": "trapi_call_start"}},
        )
        roster = trapi_client.fetch_1985_yankees_roster()
        player_count = len(roster)
        logger.info(
            "nightly_roster_sync: fetched %d players",
            player_count,
            extra={"custom_dimensions": {"event": "trapi_call_complete", "player_count": player_count}},
        )

        blob_name = blob_writer.write_roster_blob(roster)
        logger.info(
            "nightly_roster_sync: roster written to blob %s",
            blob_name,
            extra={"custom_dimensions": {"event": "blob_write_complete", "blob_name": blob_name, "player_count": player_count}},
        )
        logger.info(
            "nightly_roster_sync: complete",
            extra={"custom_dimensions": {"event": "function_complete"}},
        )
    except Exception as exc:
        logger.exception(
            "nightly_roster_sync: failed — %s",
            exc,
            extra={"custom_dimensions": {"event": "function_error", "error": str(exc)}},
        )
        raise
