"""Azure Function App — nightly 1985 Yankees roster sync."""

import logging

import azure.functions as func

import blob_writer
import trapi_client

app = func.FunctionApp()

logger = logging.getLogger("function_app")


@app.timer_trigger(
    schedule="0 0 0 * * *",
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=False,
)
def nightly_roster_sync(mytimer: func.TimerRequest) -> None:
    """Fetch the 1985 Yankees roster from TRAPI and persist it to Blob Storage."""
    logger.info("nightly_roster_sync: starting")

    try:
        roster = trapi_client.fetch_1985_yankees_roster()
        logger.info("nightly_roster_sync: fetched %d players", len(roster))

        blob_name = blob_writer.write_roster_blob(roster)
        logger.info("nightly_roster_sync: roster written to blob %s", blob_name)
    except Exception as exc:
        logger.error("nightly_roster_sync: failed — %s", exc)
        raise
