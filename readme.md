  # 1985 NY Yankees Roster — Nightly Azure Function

[![CI](https://github.com/richcia/azurefn-fleet-3/actions/workflows/ci.yml/badge.svg)](https://github.com/richcia/azurefn-fleet-3/actions/workflows/ci.yml)

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

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11 | `python --version` |
| Azure Functions Core Tools | v4 | `func --version` — [install guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) |
| Azure CLI | latest | `az --version` — [install guide](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) |

## Local Development

```bash
# 1. Clone and install dependencies
pip install -r requirements.txt

# 2. Create local settings file and fill in values
cp local.settings.json.example local.settings.json
# Edit local.settings.json with your TRAPI endpoint, auth scope, and storage account names

# 3. Run the function locally with Core Tools
func start

# 4. Run unit tests with coverage
python -m pytest tests/ -v \
  --cov=function_app --cov=blob_writer --cov=trapi_client \
  --cov-report=term-missing
```

> **Note**: `DefaultAzureCredential` is used for both blob storage and TRAPI authentication. Run `az login` before starting the function locally to authenticate via the Azure CLI.

## Required App Settings (`local.settings.json` / Function App)

All settings live under `Values` in `local.settings.json` (local) or as App Settings in the Function App (production).

| Variable | Required | Default | Description |
|---|---|---|---|
| `AzureWebJobsStorage__accountName` | Yes | — | Storage account name for identity-based AzureWebJobs storage (no connection string / shared key). |
| `FUNCTIONS_WORKER_RUNTIME` | Yes | `python` | Must be `python` for Python Azure Functions. |
| `FUNCTIONS_EXTENSION_VERSION` | Yes | `~4` | Azure Functions runtime version. Must be `~4`. |
| `DATA_STORAGE_ACCOUNT_NAME` | Yes | — | Dedicated data storage account name where the `yankees-roster` blob container lives. |
| `TRAPI_ENDPOINT` | Yes | — | Azure OpenAI endpoint URL, e.g. `https://<resource>.openai.azure.com`. |
| `TRAPI_DEPLOYMENT_NAME` | No | `gpt-4o` | Azure OpenAI deployment (model alias). |
| `TRAPI_API_VERSION` | No | `2024-02-01` | Azure OpenAI Chat Completions API version. |
| `TRAPI_AUTH_SCOPE` | No | `https://cognitiveservices.azure.com/.default` | OAuth scope requested by `DefaultAzureCredential` for TRAPI bearer token acquisition. |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | No | — | Application Insights connection string. Optional (recommended); if unset, telemetry is disabled locally. Injected automatically in production via Bicep. |

Example `Values` block:

```json
{
  "Values": {
    "AzureWebJobsStorage__accountName": "<host-storage-account-name>",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "FUNCTIONS_EXTENSION_VERSION": "~4",
    "DATA_STORAGE_ACCOUNT_NAME": "<data-storage-account-name>",
    "TRAPI_ENDPOINT": "https://<resource>.openai.azure.com",
    "TRAPI_DEPLOYMENT_NAME": "gpt-4o",
    "TRAPI_API_VERSION": "2024-02-01",
    "TRAPI_AUTH_SCOPE": "https://cognitiveservices.azure.com/.default"
  }
}
```

## TRAPI Authentication (Local and Production)

- The function uses `DefaultAzureCredential` to request a bearer token for `TRAPI_AUTH_SCOPE` (defaults to `https://cognitiveservices.azure.com/.default`).
- Local development path: run `az login`, then start the app with `func start`.
- Production path: Function App system-assigned managed identity is used automatically.
- Grant the calling identity an Azure OpenAI data-plane RBAC role (for example, `Cognitive Services OpenAI User`) on the target Azure OpenAI/TRAPI resource.
- For local dev, verify your signed-in identity and role assignment before running:

```bash
az account show --query user.name -o tsv
az role assignment list \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<aoai-resource-name> \
  --assignee <your-object-id> \
  --query "[].roleDefinitionName" -o tsv
```

## Blob Naming and Failed Prefix Behavior

- Container: `yankees-roster`
- Successful validation writes to: `yankees-roster/{run_date_utc}.json` (for example `yankees-roster/2026-03-31.json`)
- Validation failure writes raw payload to: `yankees-roster/failed/{run_date_utc}.json`
- The blob upload uses `If-None-Match: *` semantics to avoid duplicate writes for the same run date.

## Deployment

### 1. Provision infrastructure

```bash
# Log in and set your subscription
az login
az account set --subscription <subscription-id>

# Create a resource group (if it doesn't exist)
az group create --name <resource-group-name> --location eastus

# Deploy Bicep templates
az deployment group create \
  --resource-group <resource-group-name> \
  --template-file infra/main.bicep \
  --parameters trapiEndpoint=https://<your-aoai-endpoint>
```

Bicep parameters:

| Parameter | Required | Default | Description |
|---|---|---|---|
| `trapiEndpoint` | Yes | — | Azure OpenAI endpoint URL |
| `location` | No | Resource group region | Azure region for all resources |
| `trapiDeploymentName` | No | `gpt-4o` | Azure OpenAI deployment name |
| `trapiApiVersion` | No | `2024-02-01` | Azure OpenAI API version |
| `alertEmailAddress` | No | `ops-alerts@example.com` | Email address for exception alert notifications |

See [`infra/README.md`](infra/README.md) for full infrastructure details and outputs.

### 2. Deploy function code

```bash
# Publish using Azure Functions Core Tools
func azure functionapp publish <function-app-name>
```

The `storageAccountName` and `functionAppName` values are emitted as outputs from the Bicep deployment.

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
