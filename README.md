# azurefn-fleet-3

## Local development setup

Prerequisites:
- Python 3.11
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local) (`func start`)
- Azure CLI (`az`)

1. Create and activate a Python 3.11 virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```
   On Windows, use `.venv\\Scripts\\Activate.ps1` (PowerShell) or `.venv\\Scripts\\activate.bat` (CMD).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `local.settings.json` from the example:
   ```bash
   cp local.settings.json.example local.settings.json
   ```
4. Configure required values in `local.settings.json`:

   | Setting | Required | Description |
   |---|---|---|
   | `AzureWebJobsStorage__accountName` | Yes | Host storage account name used by Azure Functions runtime. |
   | `FUNCTIONS_WORKER_RUNTIME` | Yes | Worker runtime (`python`). |
   | `FUNCTIONS_EXTENSION_VERSION` | Yes | Functions host version (`~4`). |
   | `WEBSITE_TIME_ZONE` | Yes | Timezone for local/runtime behavior (`UTC`). |
   | `DATA_STORAGE_ACCOUNT_NAME` | Yes | Storage account for host/runtime storage integration checks. |
   | `ROSTER_STORAGE_ACCOUNT_NAME` | Yes | Dedicated storage account that stores roster blobs. |
   | `ROSTER_CONTAINER_NAME` | Yes | Target blob container (`yankees-roster`). |
   | `TRAPI_ENDPOINT` | Yes | TRAPI endpoint URL used by the function. |
   | `TRAPI_DEPLOYMENT_NAME` | Yes | TRAPI model deployment name. |
   | `TRAPI_API_VERSION` | Yes | TRAPI API version. |
   | `TRAPI_AUTH_SCOPE` | Yes | AAD scope for TRAPI token acquisition (default `api://trapi/.default`). |
   | `APPLICATIONINSIGHTS_CONNECTION_STRING` | Optional | App Insights connection string for local telemetry export. |
5. Sign in locally so `DefaultAzureCredential` can get tokens:
   ```bash
   az login
   ```
5. Start the Azure Functions host:
   ```bash
   func start
   ```

## TRAPI authentication

- The function requests a bearer token for scope `api://trapi/.default` (`TRAPI_AUTH_SCOPE`).
- In Azure, the Function App uses Managed Identity through `DefaultAzureCredential`.
- For local development, `DefaultAzureCredential` can use your Azure CLI session from `az login`.
- To manually obtain and inspect a local token:
  ```bash
  az account get-access-token --scope api://trapi/.default --query accessToken -o tsv
  ```
- You can override the scope in `local.settings.json` with `TRAPI_AUTH_SCOPE` when needed.

## Blob naming convention

- Container name: `yankees-roster`
- Success blob path: `yankees-roster/{run_date_utc}.json`
- `run_date_utc` is `YYYY-MM-DD` (UTC) by default.
- Failed payloads are written as: `yankees-roster/failed/{run_date_utc}.json`

## CI/CD setup (Azure federated identity + workflows)

### 1) Create Azure AD app registration and service principal

```bash
APP_NAME="azurefn-fleet-3-gha"
APP_OBJECT_ID=$(az ad app create --display-name "$APP_NAME" --query id -o tsv)
CLIENT_ID=$(az ad app show --id "$APP_OBJECT_ID" --query appId -o tsv)
az ad sp create --id "$CLIENT_ID" >/dev/null
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
```

### 2) Add federated credentials for GitHub OIDC

```bash
REPO_SUBJECT_MAIN="repo:richcia/azurefn-fleet-3:ref:refs/heads/main"
REPO_SUBJECT_STAGING="repo:richcia/azurefn-fleet-3:environment:staging"
REPO_SUBJECT_PROD="repo:richcia/azurefn-fleet-3:environment:prod"

az ad app federated-credential create --id "$APP_OBJECT_ID" --parameters "{\"name\":\"gh-main\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"$REPO_SUBJECT_MAIN\",\"audiences\":[\"api://AzureADTokenExchange\"]}"
az ad app federated-credential create --id "$APP_OBJECT_ID" --parameters "{\"name\":\"gh-staging\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"$REPO_SUBJECT_STAGING\",\"audiences\":[\"api://AzureADTokenExchange\"]}"
az ad app federated-credential create --id "$APP_OBJECT_ID" --parameters "{\"name\":\"gh-prod\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"$REPO_SUBJECT_PROD\",\"audiences\":[\"api://AzureADTokenExchange\"]}"
```

### 3) Configure GitHub secrets/variables

Configure environment secrets for `staging` and `prod`:
- `CLIENT_ID` = `$CLIENT_ID`
- `TENANT_ID` = `$TENANT_ID`
- `SUBSCRIPTION_ID` = `$SUBSCRIPTION_ID`
- `AZURE_FUNCTIONAPP_NAME` = deployed Function App name

Also set environment variables used by workflows:
- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` (same values as above)
- `AZURE_RESOURCE_GROUP`
- `TRAPI_ENDPOINT`, `TRAPI_DEPLOYMENT_NAME`, `ALERT_EMAIL_ADDRESS`
- Optional: `AZURE_LOCATION`, `SMOKE_TEST_FUNCTION_NAME`

Do **not** configure a client secret; workflows use OIDC (`azure/login`) with federated identity.

### 4) Run `cd-infra.yml` (deploy/validate infrastructure)

1. Open **Actions** → **CD Infra** (`.github/workflows/cd-infra.yml`).
2. Click **Run workflow**.
3. Set input:
   - `environment`: `staging` or `prod`
4. Ensure the selected GitHub Environment also defines:
   - secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
   - variables: `AZURE_RESOURCE_GROUP`, `TRAPI_ENDPOINT`, `TRAPI_DEPLOYMENT_NAME`, `ALERT_EMAIL_ADDRESS` (optional `AZURE_LOCATION`, defaults to `eastus`)
5. Confirm the workflow finishes with successful Bicep deployment plus validation of Function App, Storage accounts, Key Vault, Application Insights, and required RBAC assignments.

### 5) Run `cd-app.yml` (deploy Function App code)

1. Open **Actions** → **CD App** (`.github/workflows/cd-app.yml`).
2. Click **Run workflow**.
3. Set `environment` to `staging` (recommended before promote) or `prod`.
4. Confirm deployment and smoke test succeed.

### 6) Run `cd-promote.yml` (promote staging to production)

1. Open **Actions** → **CD Promote** (`.github/workflows/cd-promote.yml`).
2. Click **Run workflow**.
3. Use:
   - `source`: `staging`
   - `target`: `prod`
4. Confirm pre-swap smoke test, slot swap, post-swap verification, and post-swap smoke test all pass.

### OIDC subject examples

- Branch trust for `main`: `repo:richcia/azurefn-fleet-3:ref:refs/heads/main`
- Environment trust for `staging`: `repo:richcia/azurefn-fleet-3:environment:staging`

## Running tests

- Unit tests:
  ```bash
  python -m pytest tests -v -m "not integration"
  ```
- Integration tests:
  ```bash
  RUN_INTEGRATION_TESTS=true python -m pytest tests/integration/test_roster_integration.py -v -m integration
  ```
  Integration tests also require valid Azure and TRAPI-related environment values (for example: `AZURE_FUNCTIONAPP_NAME`, `TRAPI_ENDPOINT`, `TRAPI_DEPLOYMENT_NAME`, `TRAPI_API_VERSION`, and `DATA_STORAGE_ACCOUNT_NAME`).
