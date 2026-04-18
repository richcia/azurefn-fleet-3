import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

import pytest
@pytest.mark.integration
def test_rel_03_production_evidence_satisfies_acceptance_criteria():
    if os.environ.get("RUN_INTEGRATION_TESTS", "").lower() != "true":
        pytest.skip("Set RUN_INTEGRATION_TESTS=true to run integration tests.")

    evidence_path = Path(__file__).resolve().parents[1] / "results" / "REL-03-production-signoff-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert evidence["production_slot_swap_completed"] is True
    workflow_run_url = evidence["slot_swap_workflow_run_url"]
    assert workflow_run_url.startswith("https://github.com/richcia/azurefn-fleet-3/actions/runs/")

    run_id = urlparse(workflow_run_url).path.rstrip("/").split("/")[-1]
    request = Request(
        f"https://api.github.com/repos/richcia/azurefn-fleet-3/actions/runs/{run_id}",
        headers={"Accept": "application/vnd.github+json"},
    )
    with urlopen(request, timeout=30) as response:
        run_data = json.loads(response.read().decode("utf-8"))
    assert run_data["status"] == "completed"
    assert run_data["conclusion"] == "success"

    nightly = evidence["first_nightly_execution"]
    run_date_utc = nightly["run_date_utc"]
    assert run_date_utc
    assert nightly["observed_at_utc"]
    assert nightly["blob_path"] == f"yankees-roster/{run_date_utc}.json"

    storage_account_name = os.environ.get("REL_03_PRODUCTION_STORAGE_ACCOUNT_NAME")
    if not storage_account_name:
        pytest.skip("Set REL_03_PRODUCTION_STORAGE_ACCOUNT_NAME to verify production blob existence.")
    blob_name = nightly["blob_path"].split("/", maxsplit=1)[1]
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    assert blob_service_client.get_blob_client("yankees-roster", blob_name).exists()

    rules = set(evidence["production_alert_rules_active"])
    assert {"alert-function-execution-failure", "alert-function-duration", "alert-player-count-out-of-range"} == rules
    resource_group = os.environ.get("REL_03_RESOURCE_GROUP")
    if not resource_group:
        pytest.skip("Set REL_03_RESOURCE_GROUP to verify production alert rules.")
    result = subprocess.run(
        [
            "az",
            "monitor",
            "scheduled-query",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[?enabled==`true`].name",
            "-o",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    enabled_rules = set(json.loads(result.stdout))
    assert rules.issubset(enabled_rules)

    assert 0 < float(evidence["deliberate_failure_alert_minutes"]) <= 5
    assert evidence["release_notes_path"] == "results/REL-03-release-notes.md"

    checks = evidence["spec_success_criteria_checked"]
    assert len(checks) == 8
    assert all(checks)

    release_notes = (Path(__file__).resolve().parents[1] / evidence["release_notes_path"]).read_text(encoding="utf-8")
    checked_lines = [line for line in release_notes.splitlines() if line.lstrip().startswith("- [x] ")]
    assert len(checked_lines) >= 8
