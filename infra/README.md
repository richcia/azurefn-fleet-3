# Infrastructure — 1985-NY-Yankees Azure Function

Bicep templates that provision the Azure infrastructure for the **1985-NY-Yankees** project.

## Resources Provisioned

| Resource | Type | Notes |
|---|---|---|
| Storage Account | `Microsoft.Storage/storageAccounts` | StorageV2, Standard LRS, HTTPS-only, public-blob-access disabled |
| Blob Container | `Microsoft.Storage/storageAccounts/blobServices/containers` | `yankees-roster` — stores the nightly roster output |
| App Service Plan | `Microsoft.Web/serverfarms` | Consumption (Y1 / Dynamic) |
| Function App | `Microsoft.Web/sites` | Python 3.11, HTTPS-only, FTP disabled |
| Role Assignment | `Microsoft.Authorization/roleAssignments` | Storage Blob Data Contributor scoped to the Storage Account |

All resources are tagged with:

```
project = 1985-NY-Yankees
owner   = rciapala
```

## Directory Layout

```
infra/
├── main.bicep                  # Entry-point template
└── modules/
    ├── storage.bicep           # Storage Account + Blob Container
    ├── functionapp.bicep       # App Service Plan + Function App
    └── rbac.bicep              # Managed Identity → Storage RBAC
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `location` | `string` | resource-group location | Azure region |
| `prefix` | `string` | `yankees85` | Short prefix (3–11 chars) used to derive resource names |
| `appInsightsConnectionString` | `string` (secure) | `''` | Application Insights connection string (optional) |

## Deployment

### Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) ≥ 2.50
- Bicep CLI (`az bicep install`)
- An existing Resource Group

### Lint / Validate

```bash
az bicep build --file infra/main.bicep
```

### Deploy

```bash
az deployment group create \
  --resource-group <RESOURCE_GROUP> \
  --template-file infra/main.bicep \
  --parameters prefix=yankees85
```

### Validate After Deployment

```bash
# Confirm Function App is running with Managed Identity
az functionapp show \
  --resource-group <RESOURCE_GROUP> \
  --name <FUNCTION_APP_NAME> \
  --query "{name:name, state:state, identity:identity.type}" \
  --output table

# Confirm Storage blob service properties
az storage blob service-properties show \
  --account-name <STORAGE_ACCOUNT_NAME> \
  --auth-mode login
```

## Security Notes

- The Function App uses a **system-assigned Managed Identity** — no shared keys or API keys are stored in application settings.
- The Managed Identity is granted the built-in **Storage Blob Data Contributor** role (`ba92f5b4-2d11-453d-a403-e96b0029c9fe`) scoped to the Storage Account, following least-privilege principles.
- Public blob access is disabled on the Storage Account.
- Minimum TLS version is set to 1.2 across all resources.
- FTP/FTPS is disabled on the Function App.
