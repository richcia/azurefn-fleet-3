# Infrastructure — Azure Storage Account

Bicep templates to provision the Azure Storage Account and `yankees-roster` blob container required by the project.

## Structure

```
infra/
├── main.bicep           # Top-level orchestrator
└── modules/
    └── storage.bicep    # Storage Account + blob container
```

## Deployment

```bash
az deployment group create \
  --resource-group <resource-group-name> \
  --template-file infra/main.bicep
```

Optional parameters (defaults shown):

| Parameter  | Default               | Description                                |
|------------|-----------------------|--------------------------------------------|
| `location` | Resource group region | Azure region for all resources             |
| `project`  | `1985-NY-Yankees`     | Value applied to the `project` tag         |
| `owner`    | `rciapala`            | Value applied to the `owner` tag           |

## Outputs

| Output               | Description                                                                      |
|----------------------|----------------------------------------------------------------------------------|
| `storageAccountName` | Name of the provisioned Storage Account. Use as `AzureWebJobsStorage__accountName` |
| `storageAccountId`   | Resource ID of the provisioned Storage Account                                   |

## Identity-based access

`allowSharedKeyAccess: false` is set on the Storage Account so connection strings and shared keys are disabled. Configure the Function App (or any consumer) using the `AzureWebJobsStorage__accountName` application setting and grant it the **Storage Blob Data Owner** and **Storage Queue Data Contributor** roles via RBAC.
