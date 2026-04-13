  # 1985 NY Yankees Roster — Nightly Azure Function

Nightly Azure Function that fetches the 1985 New York Yankees roster from an Azure OpenAI TRAPI endpoint and persists it as a JSON blob in Azure Blob Storage.

## Architecture

| Component | Technology |
|---|---|
| Trigger | Azure Functions Timer (daily at 00:00 UTC) |
| Roster source | Azure OpenAI (TRAPI) |
| Persistence | Azure Blob Storage (`yankees-roster` container) |
| Observability | Application Insights + Log Analytics Workspace |
| Alerting | Azure Monitor Scheduled Query Rule (email) |

## Repository Structure

```
.
├── function_app.py          # Timer Trigger — nightly roster sync
├── blob_writer.py           # Blob Storage writer with retry logic
├── trapi_client.py          # Azure OpenAI TRAPI client
├── host.json                # Functions host config (sampling settings)
├── requirements.txt         # Python dependencies
├── tests/                   # Unit tests (pytest)
└── infra/                   # Bicep IaC templates
    ├── main.bicep
    └── modules/
        ├── storage.bicep
        ├── functionapp.bicep
        ├── monitoring.bicep
        └── alerts.bicep
```

## Local Development

```bash
pip install -r requirements.txt
cp local.settings.json.example local.settings.json
# fill in values in local.settings.json
python -m pytest tests/ -v --cov=function_app --cov=blob_writer --cov=trapi_client --cov-report=term-missing
```

## Deployment

See [`infra/README.md`](infra/README.md) for full Bicep deployment instructions.

---

## Monitoring & Alerting

### Overview

Production observability is provided by a workspace-based **Application Insights** instance backed by a **Log Analytics Workspace**, both provisioned automatically via Bicep (`infra/modules/monitoring.bicep`). The `APPLICATIONINSIGHTS_CONNECTION_STRING` app setting is injected into the Function App so all traces, exceptions, and custom dimensions are forwarded automatically.

Adaptive sampling is enabled but **Request** and **Exception** telemetry types are excluded from sampling (`host.json`) to guarantee every invocation and every failure is captured.

### Log Retention

Both the Log Analytics Workspace and Application Insights instance are configured with a **30-day retention period**, satisfying the minimum retention requirement.

| Resource | Retention |
|---|---|
| Log Analytics Workspace | 30 days |
| Application Insights | 30 days |

### Structured Log Events

The function emits the following structured log events to Application Insights via `custom_dimensions`:

| Event | Fields | Description |
|---|---|---|
| `function_start` | `past_due` | Emitted at the start of each invocation |
| `trapi_call_start` | — | Emitted before the TRAPI HTTP call |
| `trapi_call_complete` | `player_count` | Emitted after a successful TRAPI call |
| `blob_write_complete` | `blob_name`, `player_count` | Emitted after successful blob write |
| `function_complete` | — | Emitted on successful completion |
| `function_error` | `error` | Emitted when an unhandled exception occurs |

### KQL Log Queries

#### Successful execution trace

Run in **Application Insights → Logs** to confirm a nightly execution succeeded:

```kusto
traces
| where customDimensions.event in ("function_start", "function_complete", "function_error")
| project timestamp, event = tostring(customDimensions.event), past_due = tostring(customDimensions.past_due), error = tostring(customDimensions.error)
| order by timestamp desc
```

#### Blob write events (player count + blob name)

```kusto
traces
| where customDimensions.event == "blob_write_complete"
| project timestamp, message, blob_name = tostring(customDimensions.blob_name), player_count = toint(customDimensions.player_count)
| order by timestamp desc
```

#### TRAPI call results

```kusto
traces
| where customDimensions.event == "trapi_call_complete"
| project timestamp, player_count = toint(customDimensions.player_count)
| order by timestamp desc
```

#### Recent exceptions (for alert validation)

```kusto
exceptions
| project timestamp, type, outerMessage, customDimensions
| order by timestamp desc
| take 20
```

### Alert Rule

An Azure Monitor **Scheduled Query Rule** fires at severity 1 whenever the `exceptions` table contains more than 0 rows within a rolling 24-hour window (evaluated hourly). Notifications are delivered to the email address configured via the `alertEmailAddress` Bicep parameter.

| Setting | Value |
|---|---|
| Severity | 1 (critical) |
| Evaluation frequency | Every 1 hour |
| Window size | 24 hours |
| Threshold | `exceptions` count > 0 |
| Notification channel | Email (Action Group) |

### Injecting a Test Failure

To validate that the alert rule fires correctly, inject a test failure by temporarily setting an invalid `TRAPI_ENDPOINT` app setting (e.g. `https://invalid-endpoint.example.com`) and triggering the function manually via the Azure portal. Within one evaluation cycle (up to 1 hour) the alert should fire and an email notification should be received on the configured channel.

> **Important**: Restore the correct `TRAPI_ENDPOINT` value immediately after the test.

### Pre-Go-Live Checklist

- [ ] Confirm alert email recipients are correct in the `alertEmailAddress` parameter before first nightly run
- [ ] Verify Application Insights connection string is present in Function App settings
- [ ] Run the KQL queries above after the first nightly execution to confirm traces appear
- [ ] Inject a test failure and confirm alert notification is received

