# azurefn-fleet-3

## First-time OIDC setup for GitHub Actions CD

Use `.github/workflows/cd-setup.yml` to provision the Microsoft Entra app registration, service principal, and federated identity credential used by GitHub Actions OIDC.

### Prerequisites

1. You have Azure permissions to create app registrations/service principals (for example, Application Administrator or equivalent delegated rights).
2. You already have a **bootstrap** OIDC-enabled identity that can sign in from GitHub Actions and manage app registrations.
3. You know the Azure tenant ID and subscription ID used for deployments.

### Run CD Setup workflow

1. In GitHub, open **Actions** > **CD Setup**.
2. Click **Run workflow** and provide:
   - `azure_subscription_id`: target subscription ID
   - `azure_tenant_id`: target tenant ID
   - `bootstrap_client_id`: client ID of existing bootstrap OIDC identity
   - `app_registration_name`: display name for the new GitHub Actions app registration
   - `federated_credential_name`: unique credential name inside the app registration
   - `subject_type`: `branch` or `environment`
   - `subject_value`: branch name (for `branch`) or environment name (for `environment`)
3. Wait for the run to finish and copy values from the workflow summary.

### Configure repository secrets

After the setup run, create/update repository secrets:

- `AZURE_CLIENT_ID` (from workflow summary)
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

These are consumed by deployment workflows such as `.github/workflows/cd.yml` via `azure/login@v2`.

## Promote staging to production

Use `.github/workflows/cd-promote.yml` to run a manual, OIDC-authenticated slot promotion with gates.

1. In GitHub, open **Actions** > **CD Promote**.
2. Click **Run workflow** and provide:
   - `source-slot` (default: `staging`)
   - `target-slot` (default: `production`)
3. The workflow:
   - runs a pre-swap smoke test on the source slot,
   - swaps source to target via `az functionapp deployment slot swap`,
   - verifies the target slot has the promoted deployment marker and passes a post-swap smoke test.

### Subject examples

- Branch trust for `main`: `repo:richcia/azurefn-fleet-3:ref:refs/heads/main`
- Environment trust for `staging`: `repo:richcia/azurefn-fleet-3:environment:staging`

The subject must exactly match the GitHub repo + branch/environment used by the deployment workflow.

### Idempotency behavior

`cd-setup.yml` is idempotent:

- Reuses existing app registration if the display name already exists
- Reuses existing service principal if already present
- Recreates the same named federated credential so re-runs converge to the requested subject configuration without duplicates
