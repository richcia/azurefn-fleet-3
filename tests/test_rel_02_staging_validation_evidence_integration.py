import json
import os
from pathlib import Path

import pytest


@pytest.mark.integration
def test_rel_02_staging_evidence_satisfies_acceptance_criteria():
    if os.environ.get("RUN_INTEGRATION_TESTS", "").lower() != "true":
        pytest.skip("Set RUN_INTEGRATION_TESTS=true to run integration tests.")

    evidence_path = Path(__file__).resolve().parents[1] / "results" / "REL-02-staging-validation-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert evidence["run_duration_seconds"] > 0
    assert evidence["run_duration_seconds"] <= 60

    run_date_utc = evidence["run_date_utc"]
    assert run_date_utc
    assert evidence["blob_path"] == f"yankees-roster/{run_date_utc}.json"

    key_events = set(evidence["key_events"])
    assert {"function_started", "trapi_request_sent", "trapi_response_received", "blob_write_succeeded", "function_completed"}.issubset(key_events)

    assert 24 <= int(evidence["player_count_returned"]) <= 28
    assert evidence["valid_run_alerts"] == []
    assert 0 < float(evidence["deliberate_failure_alert_minutes"]) <= 5
