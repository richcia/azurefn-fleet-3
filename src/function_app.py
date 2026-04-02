import logging
import azure.functions as func

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 0 0 * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,  # Disable singleton monitor; nightly run is idempotent
)
def nightly_timer_trigger(myTimer: func.TimerRequest) -> None:
    """Nightly timer trigger that fires at 00:00:00 UTC every day."""
    if myTimer.past_due:
        logging.warning("The timer is past due.")

    logging.info("Nightly timer trigger fired.")
