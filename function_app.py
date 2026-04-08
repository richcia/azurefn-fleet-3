"""Azure Function App — nightly Timer Trigger for the 1985 NY Yankees roster."""

import logging

import azure.functions as func

import blob_writer
import trapi_client

app = func.FunctionApp()

logger = logging.getLogger(__name__)


@app.timer_trigger(
    schedule="0 0 0 * * *",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def nightly_roster_sync(timer: func.TimerRequest) -> None:
    """Fetch the 1985 NY Yankees roster from TRAPI and write it to blob storage.

    Runs nightly at 00:00 UTC via a Timer Trigger (NCRONTAB: ``0 0 0 * * *``).
    Structured log entries are emitted at INFO level for start, roster count,
    and blob write completion. Any exception is logged at ERROR level and
    re-raised so that Azure Functions marks the execution as failed.
    """
    logger.info("nightly_roster_sync: starting")

    try:
        roster = trapi_client.fetch_1985_yankees_roster()
        logger.info("nightly_roster_sync: fetched %d players", len(roster))

        blob_name = blob_writer.write_roster_blob(roster)
        logger.info(
            "nightly_roster_sync: roster written to blob '%s'", blob_name
        )
    except Exception as exc:
        logger.exception("nightly_roster_sync: error - %s", exc)
        raise
