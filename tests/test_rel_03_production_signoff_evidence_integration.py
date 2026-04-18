import json
import os
from pathlib import Path

import pytest


@pytest.mark.integration
def test_rel_03_production_evidence_satisfies_acceptance_criteria():
    if os.environ.get("RUN_INTEGRATION_TESTS", "").lower() != "true":
        pytest.skip("Set RUN_INTEGRATION_TESTS=true to run integration tests.")

    evidence_path = Path(__file__).resolve().parents[1] / "results" / "REL-03-production-signoff-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert evidence["production_slot_swap_completed"] is True
    assert evidence["slot_swap_workflow_run_url"].startswith("https://github.com/richcia/azurefn-fleet-3/actions/runs/")

    nightly = evidence["first_nightly_execution"]
    run_date_utc = nightly["run_date_utc"]
    assert run_date_utc
    assert nightly["observed_at_utc"]
    assert nightly["blob_path"] == f"yankees-roster/{run_date_utc}.json"

    rules = set(evidence["production_alert_rules_active"])
    assert {"alert-function-execution-failure", "alert-function-duration", "alert-player-count-out-of-range"} == rules

    assert 0 < float(evidence["deliberate_failure_alert_minutes"]) <= 5
    assert evidence["release_notes_path"] == "results/REL-03-release-notes.md"

    checks = evidence["spec_success_criteria_checked"]
    assert len(checks) == 8
    assert all(checks)
