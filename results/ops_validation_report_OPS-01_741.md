# OPS-01 Validation Report (PR #741)

## Scope
Validate structured logs, OpenTelemetry custom metric visibility, sampling configuration, workspace retention, and alert status for staging.

## Validation Summary
- [x] Structured log events emitted by function code and covered by tests:
  - `function_started`
  - `trapi_request_sent`
  - `trapi_response_received`
  - `blob_write_succeeded`
  - `function_completed`
- [x] `player_count_returned` custom metric is emitted in function code and covered by tests.
- [x] Log Analytics Workspace retention is configured to 30 days in `infra/modules/monitoring.bicep`.
- [x] Application Insights sampling is enabled in `host.json` under `logging.applicationInsights.samplingSettings.isEnabled`.
- [x] All three alert rules are configured with `enabled: true` in `infra/modules/alerts.bicep`.
- [ ] Test alert fire verified in staging for at least one rule.

## Evidence (repository)
- `tests/test_function_app.py`
- `tests/test_app03_configuration.py`
- `tests/test_ops01_infra_configuration.py`
- `function_app.py`
- `host.json`
- `infra/modules/monitoring.bicep`
- `infra/modules/alerts.bicep`

## Staging Validation Status
Direct staging telemetry validation from this execution environment is blocked because Azure CLI is not authenticated (`az account show` requires `az login`).

Run the following after authenticating to Azure and targeting the staging resource group to complete the final unchecked criterion:

```bash
# 1) Force at least one failure run to trigger the execution failure alert
az functionapp config appsettings set --resource-group <staging-rg> --name <staging-function-app> --settings TRAPI_ENDPOINT=https://example.invalid
curl -X POST "https://<staging-function-app>.azurewebsites.net/admin/functions/GetAndStoreYankeesRoster?code=<host-or-function-key>"

# 2) Validate alerts are enabled
az monitor alert list --resource-group <staging-rg> --query "[?contains(name, 'alert-')].{name:name, enabled:enabled}" -o table

# 3) Verify at least one alert instance fired in the last 24h
az monitor app-insights query --app <staging-appinsights-name> --analytics-query "alertsmanagementresources | where TimeGenerated > ago(24h) | where MonitorCondition =~ 'Fired' | project AlertRule=AlertRule, MonitorCondition, TimeGenerated" -o table
```
