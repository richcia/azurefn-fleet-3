import function_app


class _FakeTimer:
    def __init__(self, past_due: bool) -> None:
        self.past_due = past_due


class _FakeLogger:
    def __init__(self) -> None:
        self.info_calls = []
        self.exception_calls = []

    def info(self, message, *args, **kwargs):
        self.info_calls.append((message, kwargs))

    def exception(self, message, *args, **kwargs):
        self.exception_calls.append((message, kwargs))


class _FakeHistogram:
    def __init__(self) -> None:
        self.records = []

    def record(self, value, attributes=None):
        self.records.append((value, attributes or {}))


def test_configure_opentelemetry_uses_application_insights_connection_string(monkeypatch):
    observed = {}

    def fake_configure(*, connection_string):
        observed["connection_string"] = connection_string

    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test-key")
    monkeypatch.setattr(function_app, "configure_azure_monitor", fake_configure)
    monkeypatch.setattr(function_app, "_OTEL_CONFIGURED", False)

    function_app._configure_opentelemetry()

    assert observed["connection_string"] == "InstrumentationKey=test-key"
    assert function_app._OTEL_CONFIGURED is True


def test_nightly_roster_sync_emits_required_structured_fields_and_metric(monkeypatch):
    fake_logger = _FakeLogger()
    fake_histogram = _FakeHistogram()

    monkeypatch.setenv("TRAPI_DEPLOYMENT_NAME", "gpt-4o-2024-08-06")
    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "mystorage")
    monkeypatch.setattr(function_app, "logger", fake_logger)
    monkeypatch.setattr(function_app, "_PLAYER_COUNT_METRIC", fake_histogram)
    monkeypatch.setattr(
        function_app.trapi_client, "fetch_1985_yankees_roster", lambda: [{"name": "Don Mattingly"}, {"name": "Rickey Henderson"}]
    )
    monkeypatch.setattr(function_app.blob_writer, "write_roster_blob", lambda roster: "roster-20260416.json")

    function_app.nightly_roster_sync(_FakeTimer(past_due=False))

    logged_events = []
    for _, kwargs in fake_logger.info_calls:
        dimensions = kwargs["extra"]["custom_dimensions"]
        logged_events.append(dimensions["event"])
        for required_field in (
            "model_version",
            "prompt_hash",
            "token_count",
            "latency_ms",
            "player_count",
            "blob_uri",
        ):
            assert required_field in dimensions

    assert logged_events == [
        "function_started",
        "trapi_request_sent",
        "trapi_response_received",
        "blob_write_succeeded",
        "function_completed",
    ]
    assert fake_histogram.records
    value, attributes = fake_histogram.records[0]
    assert value == 2
    assert attributes["player_count_returned"] == 2
