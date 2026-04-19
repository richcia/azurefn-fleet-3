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

## Sign-off

- QA Sign-off: ____________________
- Date (UTC): ____________________
