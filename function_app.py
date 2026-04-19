import logging

import azure.functions as func
from opentelemetry import metrics

from src.blob_writer import BlobWriter
from src.validator import validate_roster_response
from trapi_client import TRAPIRetryExhaustedError, RosterValidationError, fetch_1985_yankees_roster

app = func.FunctionApp()
_LOGGER = logging.getLogger(__name__)
_METER = metrics.get_meter(__name__)
_PLAYER_COUNT_RETURNED = _METER.create_histogram(
    "player_count_returned",
    unit="players",
    description="Number of players returned from TRAPI.",
)


@app.function_name(name="GetAndStoreYankeesRoster")
@app.timer_trigger(
    arg_name="timer",
    schedule="0 0 2 * * *",
    run_on_startup=False,
    use_monitor=True,
)
def get_and_store_yankees_roster(timer: func.TimerRequest) -> None:
    del timer
    _LOGGER.info("function_started")
    writer = BlobWriter()
    try:
        roster_payload = fetch_1985_yankees_roster()
        validation_result = validate_roster_response(roster_payload)
        if not validation_result.is_valid:
            writer.write_failed(roster_payload)
            message = validation_result.error.message if validation_result.error else "Roster validation failed"
            raise RuntimeError(message)

        players = validation_result.players or []
        player_count = len(players)
        blob_uri = writer.write(roster_payload)
        _PLAYER_COUNT_RETURNED.record(player_count)
        _LOGGER.info(
            "function_completed",
            extra={
                "player_count": player_count,
                "blob_uri": blob_uri,
                "write_conflict": blob_uri is None,
            },
        )
    except RosterValidationError as exc:
        writer.write_failed(exc.response_payload)
        raise RuntimeError(str(exc)) from exc
    except TRAPIRetryExhaustedError as exc:
        writer.write_failed(exc.response_payload)
        raise RuntimeError(str(exc)) from exc
