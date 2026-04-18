# REL-02 — Staging Validation Sign-off Checklist

Use this checklist during staging validation for `GetAndStoreYankeesRoster`.

## Run Metadata

- Validation date (UTC): `____________________`
- Function app / slot: `____________________`
- Trigger method (Portal/CLI): `____________________`
- Validator: `____________________`

## Acceptance Criteria Sign-off

- [ ] Function executes successfully in staging within 60 seconds  
  - Evidence: execution duration `__________` seconds
- [ ] Blob `yankees-roster/{run_date_utc}.json` written to staging storage account  
  - Evidence: blob URI `________________________________________`
- [ ] All five key log events visible in Application Insights Traces  
  - Events: `function_started`, `trapi_request_sent`, `trapi_response_received`, `blob_write_succeeded`, `function_completed`
- [ ] `player_count_returned` custom metric emitted with value 24–28  
  - Evidence: metric value `__________`
- [ ] No failure or data quality alerts triggered during valid run
- [ ] Deliberate failure test confirms failure alert fires within 5 minutes

## Application Insights Evidence

### Trace query for the five key events

```kusto
traces
| where timestamp >= ago(2h)
| where customDimensions.event in (
    "function_started",
    "trapi_request_sent",
    "trapi_response_received",
    "blob_write_succeeded",
    "function_completed"
)
| project timestamp, event=tostring(customDimensions.event), message
| order by timestamp asc
```

### Metric query for `player_count_returned`

```kusto
union isfuzzy=true
(
  customMetrics
  | where timestamp >= ago(2h)
  | where name == "player_count_returned"
  | project timestamp, metric_value=todouble(value)
),
(
  AppMetrics
  | where TimeGenerated >= ago(2h)
  | where Name == "player_count_returned"
  | project timestamp=TimeGenerated, metric_value=todouble(Val)
)
| order by timestamp desc
```

## Alert Verification

### Valid run (no alert expected)

- [ ] `alert-function-execution-failure` did not fire
- [ ] `alert-player-count-out-of-range` did not fire

### Deliberate failure (alert expected within 5 minutes)

1. Temporarily set a known-bad `TRAPI_ENDPOINT` in staging.
2. Manually trigger `GetAndStoreYankeesRoster`.
3. Confirm `alert-function-execution-failure` fired within 5 minutes (rule evaluation frequency is `PT5M`).
4. Restore the original `TRAPI_ENDPOINT` immediately.
5. Re-run a valid invocation and confirm alert resolves.

## Final Approval

- Signed off by: `____________________`
- Timestamp (UTC): `____________________`
- Notes: `____________________________________________________________`
