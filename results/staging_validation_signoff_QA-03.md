# QA-03 Staging Validation Sign-off Checklist

- Run Date (UTC): ____________________
- Function App (staging): ____________________
- Storage Account: ____________________
- Validator: ____________________
- Validation Timestamp (UTC): ____________________

## Acceptance Criteria Validation

- [ ] Timer Trigger fires at 2:00 AM UTC in staging.
  - Evidence: Timer execution record for `GetAndStoreYankeesRoster` at `02:00:00Z` in staging.
- [ ] Blob `yankees-roster/{run_date_utc}.json` exists in the staging data storage account.
  - Evidence: Blob path and ETag: ____________________
- [ ] Blob contains 24–28 players including Mattingly, Winfield, Henderson.
  - Evidence:
    - Player count: ____________________
    - Mattingly present: Yes / No
    - Winfield present: Yes / No
    - Henderson present: Yes / No
- [ ] No blob exists in `yankees-roster/failed/` for the same run date.
  - Evidence: failed blob check result: ____________________
- [ ] App Insights shows all five log events for the run.
  - Required events:
    - `function_started`
    - `trapi_request_sent`
    - `trapi_response_received`
    - `blob_write_succeeded`
    - `function_completed`
  - Evidence: ____________________
- [ ] `player_count_returned` metric visible in Metrics Explorer for the run.
  - Evidence: Metric datapoint timestamp/value: ____________________
- [ ] Function duration is under 60 seconds.
  - Evidence: Duration: ____________________ seconds

## Validation Procedure (Staging)

1. Execute `.github/workflows/integration-staging.yml` (workflow_dispatch) to trigger `tests/test_integration.py`.
2. Record run_date_utc from the created blob name (`YYYY-MM-DD.json`) and store it above.
3. Validate timer and duration in App Insights:
   - `requests | where name contains "GetAndStoreYankeesRoster" | where timestamp > ago(24h) | order by timestamp desc`
4. Validate required log events:
   - `traces | where timestamp > ago(24h) | where message in ("function_started","trapi_request_sent","trapi_response_received","blob_write_succeeded","function_completed") | order by timestamp desc`
5. Validate metric visibility:
   - Metrics Explorer > `player_count_returned` filtered to the validation window/run date.
6. Validate no failed blob for run date:
   - Confirm absence of `yankees-roster/failed/{run_date_utc}.json`.

## Sign-off

- QA Sign-off: ____________________
- Date (UTC): ____________________
