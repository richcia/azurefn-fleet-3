# azurefn-fleet-3

## Local development setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `local.settings.json` from the example and update values for your environment:
   ```bash
   cp local.settings.json.example local.settings.json
   ```
4. Sign in locally so `DefaultAzureCredential` can get tokens:
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

## GitHub Actions workflows (OIDC + deployments)

### 1) Run `cd-setup.yml` (configure OIDC federated identity)

1. Open **Actions** → **CD Setup** (`.github/workflows/cd-setup.yml`).
2. Click **Run workflow** and provide:
   - `azure_subscription_id`
   - `azure_tenant_id`
   - `bootstrap_client_id`
   - `app_registration_name`
   - `federated_credential_name`
   - `subject_type` (`branch` or `environment`)
   - `subject_value` (branch/environment value)
3. After completion, copy the emitted values and set repository/environment variables:
   - `AZURE_CLIENT_ID`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`
4. Ensure deployment targets are configured:
   - environment variable `AZURE_RESOURCE_GROUP`
   - secret `AZURE_FUNCTIONAPP_NAME`

### 2) Run `cd-infra.yml` (deploy/validate infrastructure)

1. Open **Actions** → **CD Infra** (`.github/workflows/cd-infra.yml`).
2. Click **Run workflow**.
3. Set inputs:
   - `environment`: `staging` or `production`
   - `storage_container_name`: keep `yankees-roster` unless intentionally changing
4. Confirm the workflow finishes with successful Bicep deployment and storage/RBAC validation.

### 3) Run `cd-app.yml` (deploy Function App code)

1. Open **Actions** → **CD App** (`.github/workflows/cd-app.yml`).
2. Click **Run workflow**.
3. Set `environment` to `staging` (recommended before promote) or `production`.
4. Confirm deployment and smoke test succeed.

### 4) Run `cd-promote.yml` (promote staging to production)

1. Open **Actions** → **CD Promote** (`.github/workflows/cd-promote.yml`).
2. Click **Run workflow**.
3. Use:
   - `source-slot`: `staging`
   - `target-slot`: `production`
4. Confirm pre-swap smoke test, slot swap, post-swap verification, and post-swap smoke test all pass.

### OIDC subject examples

- Branch trust for `main`: `repo:richcia/azurefn-fleet-3:ref:refs/heads/main`
- Environment trust for `staging`: `repo:richcia/azurefn-fleet-3:environment:staging`

`cd-setup.yml` is idempotent: it reuses existing app/service principal and updates the named federated credential to the requested subject.
