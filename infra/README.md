# Infrastructure — Azure Storage Account + Function App

Bicep templates to provision the Azure Storage Account, `yankees-roster` blob container, and Azure Function App required by the project.

## Structure

```
infra/
├── main.bicep                 # Top-level orchestrator
└── modules/
    ├── storage.bicep          # Storage Account + blob container
    └── functionapp.bicep      # Linux Consumption Function App + managed identity
```

## Deployment

```bash
az deployment group create \
  --resource-group <resource-group-name> \
  --template-file infra/main.bicep \
  --parameters trapiEndpoint=https://<your-aoai-endpoint>
```

Optional parameters (defaults shown):

| Parameter              | Default               | Description                                         |
|------------------------|-----------------------|-----------------------------------------------------|
| `location`             | Resource group region | Azure region for all resources                      |
| `project`              | `1985-NY-Yankees`     | Value applied to the `project` tag                  |
| `owner`                | `rciapala`            | Value applied to the `owner` tag                    |
| `trapiEndpoint`        | *(required)*          | Azure OpenAI endpoint URL                           |
| `trapiDeploymentName`  | `gpt-4o`              | Azure OpenAI deployment (model alias)               |
| `trapiApiVersion`      | `2024-02-01`          | Azure OpenAI API version                            |

## Outputs

| Output                       | Description                                                                          |
|------------------------------|--------------------------------------------------------------------------------------|
| `storageAccountName`         | Name of the provisioned Storage Account. Use as `AzureWebJobsStorage__accountName`  |
| `storageAccountId`           | Resource ID of the provisioned Storage Account                                       |
| `functionAppName`            | Name of the provisioned Function App                                                 |
| `functionAppId`              | Resource ID of the provisioned Function App                                          |
| `functionAppPrincipalId`     | Principal ID of the system-assigned managed identity (use for RBAC assignments)      |
| `functionAppDefaultHostname` | Default hostname of the Function App                                                 |

## Identity-based access

`allowSharedKeyAccess: false` is set on the Storage Account so connection strings and shared keys are disabled. The Function App uses `AzureWebJobsStorage__accountName` (identity-based storage access) and must be granted the **Storage Blob Data Owner** and **Storage Queue Data Contributor** roles via RBAC using the `functionAppPrincipalId` output.

## Function App configuration

The Function App is provisioned with:
- **Plan**: Linux Consumption (`Y1` / Dynamic)
- **Runtime**: Python 3.11 (`linuxFxVersion: Python|3.11`)
- **Identity**: System-assigned managed identity
- **App settings**: `AzureWebJobsStorage__accountName`, `STORAGE_ACCOUNT_NAME`, `TRAPI_ENDPOINT`, `TRAPI_DEPLOYMENT_NAME`, `TRAPI_API_VERSION`, `FUNCTIONS_WORKER_RUNTIME`, `FUNCTIONS_EXTENSION_VERSION`

> **Note**: The Consumption plan introduces cold-start latency. This is acceptable for the nightly batch workload but may add a few seconds to the first execution after an idle period.
