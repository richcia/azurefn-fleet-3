from pathlib import Path


def test_rel_02_signoff_checklist_contains_required_outputs_and_events():
    checklist = (
        Path(__file__).resolve().parents[1]
        / "results"
        / "REL-02-staging-validation-signoff-checklist.md"
    ).read_text(encoding="utf-8")

    assert "Staging Validation Sign-off Checklist" in checklist
    assert "Function executes successfully in staging within 60 seconds" in checklist
    assert "Blob `yankees-roster/{run_date_utc}.json` written to staging storage account" in checklist
    assert "function_started" in checklist
    assert "trapi_request_sent" in checklist
    assert "trapi_response_received" in checklist
    assert "blob_write_succeeded" in checklist
    assert "function_completed" in checklist
    assert "`player_count_returned` custom metric emitted with value 24–28" in checklist
    assert "No failure or data quality alerts triggered during valid run" in checklist
    assert "fired within 5 minutes" in checklist


def test_rel_02_evidence_template_exists_with_expected_keys():
    evidence = (
        Path(__file__).resolve().parents[1]
        / "results"
        / "REL-02-staging-validation-evidence.json"
    ).read_text(encoding="utf-8")

    assert '"run_duration_seconds"' in evidence
    assert '"blob_path"' in evidence
    assert '"key_events"' in evidence
    assert '"player_count_returned"' in evidence
    assert '"valid_run_alerts"' in evidence
    assert '"deliberate_failure_alert_minutes"' in evidence
