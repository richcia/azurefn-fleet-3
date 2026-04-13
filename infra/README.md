# Infrastructure — Azure Storage Account, Function App & Monitoring

Bicep templates to provision the Azure Storage Account, `yankees-roster` blob container, Azure Function App, Application Insights, and alerting required by the project.

## Structure

```
infra/
├── main.bicep                 # Top-level orchestrator
└── modules/
    ├── storage.bicep          # Storage Account + blob container
    ├── functionapp.bicep      # Linux Consumption Function App + managed identity
    ├── monitoring.bicep       # Log Analytics Workspace + Application Insights
    └── alerts.bicep           # Action Group (email) + exception alert rule
```

## Deployment

```bash
az deployment group create \
  --resource-group <resource-group-name> \
  --template-file infra/main.bicep \
  --parameters trapiEndpoint=https://<your-aoai-endpoint>
```

Optional parameters (defaults shown):

| Parameter              | Default                          | Description                                              |
|------------------------|----------------------------------|----------------------------------------------------------|
| `location`             | Resource group region            | Azure region for all resources                           |
| `project`              | `1985-NY-Yankees`                | Value applied to the `project` tag                       |
| `owner`                | `rciapala`                       | Value applied to the `owner` tag                         |
| `trapiEndpoint`        | *(required)*                     | Azure OpenAI endpoint URL                                |
| `trapiDeploymentName`  | `gpt-4o`                         | Azure OpenAI deployment (model alias)                    |
| `trapiApiVersion`      | `2024-02-01`                     | Azure OpenAI API version                                 |
| `alertEmailAddress`    | `ops-alerts@example.com`         | Email address for function-exception alert notifications |

## Outputs

| Output                         | Description                                                                          |
|--------------------------------|--------------------------------------------------------------------------------------|
| `storageAccountName`           | Name of the provisioned Storage Account. Use as `AzureWebJobsStorage__accountName`  |
| `storageAccountId`             | Resource ID of the provisioned Storage Account                                       |
| `functionAppName`              | Name of the provisioned Function App                                                 |
| `functionAppId`                | Resource ID of the provisioned Function App                                          |
| `functionAppPrincipalId`       | Principal ID of the system-assigned managed identity (use for RBAC assignments)      |
| `functionAppDefaultHostname`   | Default hostname of the Function App                                                 |
| `appInsightsId`                | Resource ID of the Application Insights instance                                     |
| `appInsightsConnectionString`  | Application Insights connection string (set as app setting automatically)            |
| `logAnalyticsWorkspaceId`      | Resource ID of the Log Analytics Workspace backing Application Insights              |
| `exceptionAlertRuleId`         | Resource ID of the exception alert rule                                              |

## Identity-based access

`allowSharedKeyAccess: false` is set on the Storage Account so connection strings and shared keys are disabled. The Function App uses `AzureWebJobsStorage__accountName` (identity-based storage access) and must be granted the **Storage Blob Data Owner** and **Storage Queue Data Contributor** roles via RBAC using the `functionAppPrincipalId` output.

## Function App configuration

The Function App is provisioned with:
- **Plan**: Linux Consumption (`Y1` / Dynamic)
- **Runtime**: Python 3.11 (`linuxFxVersion: Python|3.11`)
- **Identity**: System-assigned managed identity
- **App settings**: `AzureWebJobsStorage__accountName`, `STORAGE_ACCOUNT_NAME`, `TRAPI_ENDPOINT`, `TRAPI_DEPLOYMENT_NAME`, `TRAPI_API_VERSION`, `FUNCTIONS_WORKER_RUNTIME`, `FUNCTIONS_EXTENSION_VERSION`, `APPLICATIONINSIGHTS_CONNECTION_STRING`

> **Note**: The Consumption plan introduces cold-start latency. This is acceptable for the nightly batch workload but may add a few seconds to the first execution after an idle period.

## Observability

### Application Insights

A workspace-based Application Insights instance (`appi<hash>`) backed by a Log Analytics Workspace (`law<hash>`) is provisioned automatically. The `APPLICATIONINSIGHTS_CONNECTION_STRING` app setting is wired into the Function App so all traces, exceptions, and custom dimensions are forwarded without additional SDK configuration.

### Sampling settings (`host.json`)

`samplingSettings.excludedTypes` is set to `Request;Exception` so that:
- **Request** traces are never dropped (operational breadcrumb for every invocation)
- **Exception** traces are never dropped (guaranteed capture for alert accuracy)

All other telemetry types (Dependency, Trace, etc.) remain subject to adaptive sampling to control cost.

### Alert rule

An Azure Monitor Scheduled Query Rule fires at **severity 1** whenever the `exceptions` table in Application Insights contains **more than 0 rows** within a rolling 24-hour window (evaluated hourly). Notifications are sent to the email address configured via the `alertEmailAddress` parameter.

### Log queries

#### Roster write events (traces table)

Use this KQL query in Application Insights Logs to find all successful blob-write events:

```kusto
traces
| where customDimensions.event == "blob_write_complete"
| project timestamp, message, blob_name = tostring(customDimensions.blob_name)
| order by timestamp desc
```

#### Function execution summary

```kusto
traces
| where customDimensions.event in ("function_start", "function_complete", "function_error")
| project timestamp, event = tostring(customDimensions.event), past_due = tostring(customDimensions.past_due), error = tostring(customDimensions.error)
| order by timestamp desc
```

#### TRAPI call results

```kusto
traces
| where customDimensions.event == "trapi_call_complete"
| project timestamp, player_count = toint(customDimensions.player_count)
| order by timestamp desc
```
