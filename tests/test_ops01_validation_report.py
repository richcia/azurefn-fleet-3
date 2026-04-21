from pathlib import Path


def test_ops01_validation_report_covers_required_checks() -> None:
    report_path = Path(__file__).resolve().parents[1] / "results" / "ops_validation_report_OPS-01_741.md"
    report = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "function_started",
        "trapi_request_sent",
        "trapi_response_received",
        "blob_write_succeeded",
        "function_completed",
        "player_count_returned",
        "retention is configured to 30 days",
        "sampling is enabled",
        "All three alert rules are configured with `enabled: true`",
        "Verify at least one alert instance fired",
    ]
    for phrase in required_phrases:
        assert phrase in report
