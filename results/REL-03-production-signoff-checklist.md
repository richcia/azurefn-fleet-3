# REL-03 — Production Deployment and Monitoring Activation Sign-off

Use this checklist to complete production sign-off after REL-01 and REL-02.

## Run Metadata

- Deployment date (UTC): `____________________`
- Validator: `____________________`
- GitHub Actions run URL: `____________________`

## Acceptance Criteria Sign-off

- [ ] Production slot swap completed via GitHub Actions pipeline  
  - Evidence: workflow run URL `________________________________________`
- [ ] First nightly execution at 2:00 AM UTC writes blob successfully  
  - Evidence: blob path `yankees-roster/{run_date_utc}.json`
- [ ] All three alert rules active in production Application Insights  
  - Required rules: `alert-function-execution-failure`, `alert-function-duration`, `alert-player-count-out-of-range`
- [ ] Failure alert test (deliberate exception) fires within 5 minutes in production  
  - Evidence: alert fire time `__________` minutes
- [ ] All spec success criteria checked off and documented in release notes  
  - Evidence: `results/REL-03-release-notes.md`

## Application Insights Verification Queries

### Confirm first nightly blob write

```kusto
traces
| where timestamp >= ago(24h)
| where customDimensions.event == "blob_write_succeeded"
| project timestamp, blob_name=tostring(customDimensions.blob_name), message
| order by timestamp desc
```

### Confirm alert activity for deliberate failure

```kusto
AppTraces
| where TimeGenerated >= ago(1h)
| where Message has "alert-function-execution-failure" or Message has "fired"
| order by TimeGenerated desc
```

## First-night Risk Mitigation

- [ ] Calendar reminder set to verify blob by 2:15 AM UTC on first production night

## Machine-readable Evidence (for automated verification)

Save sign-off evidence to `results/REL-03-production-signoff-evidence.json` using this schema:

```json
{
  "production_slot_swap_completed": true,
  "slot_swap_workflow_run_url": "https://github.com/richcia/azurefn-fleet-3/actions/runs/123456789",
  "first_nightly_execution": {
    "run_date_utc": "2026-04-19",
    "observed_at_utc": "2026-04-19T02:15:00Z",
    "blob_path": "yankees-roster/2026-04-19.json"
  },
  "production_alert_rules_active": [
    "alert-function-execution-failure",
    "alert-function-duration",
    "alert-player-count-out-of-range"
  ],
  "deliberate_failure_alert_minutes": 4.0,
  "release_notes_path": "results/REL-03-release-notes.md",
  "spec_success_criteria_checked": [
    true,
    true,
    true,
    true,
    true,
    true,
    true,
    true
  ]
}
```
