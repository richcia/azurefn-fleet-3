# Infrastructure — 1985-NY-Yankees

Bicep templates to provision all Azure resources for the 1985-NY-Yankees project.

## Resources Provisioned

| Resource | Name | Notes |
|---|---|---|
| Resource Group | `rg-1985-ny-yankees` | Subscription-scope deployment |
| Storage Account | `st1985nyyankees` | Standard LRS, TLS 1.2+, public blob access disabled |
| Blob Container | `yankees-roster` | Private, inside the Storage Account |
| Log Analytics Workspace | `law-1985-ny-yankees` | PerGB2018 SKU, 30-day retention |
| Application Insights | `appi-1985-ny-yankees` | Workspace-based, linked to Function App |
| App Service Plan | `asp-1985-ny-yankees` | Consumption (Y1/Dynamic), Linux |
| Function App | `func-1985-ny-yankees` | Python 3.11, Linux Consumption, System-Assigned MI |

All resources are tagged with `project: 1985-NY-Yankees` and `owner: rciapala`.

No secrets or connection strings are stored in Bicep or parameter files.  
The Function App uses a **System-Assigned Managed Identity** with identity-based storage access (`AzureWebJobsStorage__accountName` + `AzureWebJobsStorage__credential: managedidentity`).

---

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed and authenticated (`az login`)
- [Bicep CLI](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/install) v0.25+ (or use `az bicep install`)
- Target Azure subscription ID

---

## Deployment

### Step 1 — Create the Resource Group

```bash
az deployment sub create \
  --location eastus \
  --template-file infra/resourcegroup.bicep \
  --parameters infra/resourcegroup.bicepparam
```

### Step 2 — Deploy Core Infrastructure

```bash
az deployment group create \
  --resource-group rg-1985-ny-yankees \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam
```

### Step 3 — Validate Deployed Resources

```bash
az resource list --resource-group rg-1985-ny-yankees --output table
```

Expected output includes:
- `Microsoft.Storage/storageAccounts` — `st1985nyyankees`
- `Microsoft.OperationalInsights/workspaces` — `law-1985-ny-yankees`
- `Microsoft.Insights/components` — `appi-1985-ny-yankees`
- `Microsoft.Web/serverfarms` — `asp-1985-ny-yankees`
- `Microsoft.Web/sites` — `func-1985-ny-yankees`

---

## File Structure

```
infra/
├── main.bicep               # Resource group-scope orchestration template
├── main.bicepparam          # Parameters for main.bicep (no secrets)
├── resourcegroup.bicep      # Subscription-scope resource group template
├── resourcegroup.bicepparam # Parameters for resource group
├── README.md                # This file
└── modules/
    ├── storage.bicep        # Storage Account + yankees-roster blob container
    ├── monitoring.bicep     # Log Analytics Workspace + Application Insights
    └── functionapp.bicep    # App Service Plan + Python Function App
```

---

## Security Notes

- No API keys or connection strings are used in any Bicep or parameter file.
- The Function App connects to Azure Storage using a **System-Assigned Managed Identity** (no `AzureWebJobsStorage` connection string).
- After deploying, assign the `Storage Blob Data Contributor`, `Storage Queue Data Contributor`, and `Storage Table Data Contributor` roles to the Function App's managed identity on the Storage Account (see task INF-02).
- Blob public access is disabled on the Storage Account.
- FTPS is disabled and minimum TLS version is 1.2 on the Function App.
