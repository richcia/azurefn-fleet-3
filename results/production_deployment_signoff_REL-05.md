# REL-05 Production Deployment Sign-off

- Run Date (UTC): ____________________
- CD Promote Workflow Run URL: ____________________
- Production Function App: ____________________
- Production Storage Account: ____________________
- Validator: ____________________
- Validation Timestamp (UTC): ____________________

## Acceptance Criteria Validation

- [ ] CD Promote workflow completes without errors.
  - Evidence: Workflow run URL and conclusion: ____________________
- [ ] Smoke test passes in production slot post-swap.
  - Evidence: Post-swap smoke test HTTP status and attempt: ____________________
- [ ] All three alert rules active in production App Insights.
  - Required alert rules:
    - Execution failure alert
    - Duration alert
    - Data quality alert (`player_count_returned`)
  - Evidence: Alert rule names/IDs and Enabled status: ____________________
- [ ] First nightly production trigger fires and blob appears in production storage account.
  - Evidence:
    - Nightly run timestamp (UTC): ____________________
    - Blob path (`yankees-roster/{run_date_utc}.json`): ____________________
    - Blob ETag: ____________________
- [ ] Code review approved and all `spec.md` success criteria checked off.
  - Evidence: PR approval link and `spec.md` success-criteria section updated: ____________________
- [ ] README reviewed and published.
  - Evidence: README commit/PR link: ____________________

## Verification Procedure

1. Run `.github/workflows/cd-promote.yml` with:
   - `source-slot`: `staging`
   - `target-slot`: `production`
2. Confirm all promote workflow stages succeeded:
   - pre-swap smoke test
   - slot swap
   - post-swap version verification
   - post-swap smoke test
3. Confirm production alerts in App Insights:
   - `execution-failure-alert`
   - `duration-alert`
   - `player-count-data-quality-alert`
4. After the next `02:00 UTC` timer run, verify:
   - production invocation exists in App Insights requests/traces
   - `yankees-roster/{run_date_utc}.json` exists in production storage
5. Confirm PR code review is approved and `spec.md` Success Criteria are checked.
6. Confirm README remains current and published in default branch.

## Sign-off

- Platform Engineering Sign-off: ____________________
- Date (UTC): ____________________
