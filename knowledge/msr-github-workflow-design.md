# GitHub Workflow Design — Reference Links

Authoritative URLs for GitHub Actions best practices and design patterns.

---

## GitHub Actions Core Best Practices

| Topic | URL |
|---|---|
| GitHub Actions overview | https://docs.github.com/en/actions/about-github-actions/understanding-github-actions |
| Security hardening for GitHub Actions | https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions |
| Best practices for using secrets | https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions |
| Workflow syntax reference | https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions |
| Reusing workflows | https://docs.github.com/en/actions/sharing-automations/reusing-workflows |
| Caching dependencies to speed up workflows | https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows |
| Storing workflow data as artifacts | https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow |
| Using environments for deployment | https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment |
| Controlling permissions for `GITHUB_TOKEN` | https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token |
| Disabling and enabling workflows | https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/disabling-and-enabling-a-workflow |

---

## Security & Identity

| Topic | URL |
|---|---|
| OpenID Connect (OIDC) in GitHub Actions | https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect |
| Configure OIDC with Azure (federated identity) | https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect |
| Configuring federated identity credentials (Azure AD) | https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-create-trust |
| Preventing script injection attacks | https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#understanding-the-risk-of-script-injections |
| Pinning actions to a full commit SHA | https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-third-party-actions |
| Dependabot for Actions version updates | https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot |

---

## CI/CD Design Patterns

| Topic | URL |
|---|---|
| Deployment protection rules | https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment#deployment-protection-rules |
| Manual approval gates (`environment` + reviewers) | https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/reviewing-deployments |
| Triggering workflows (`push`, `workflow_dispatch`, `schedule`) | https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows |
| `workflow_dispatch` with input parameters | https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#workflow_dispatch |
| Matrix strategy for parallel jobs | https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/running-variations-of-jobs-in-a-workflow |
| Job dependencies (`needs`) and conditional execution | https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#jobsjob_idneeds |
| Concurrency control (cancel in-progress runs) | https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#concurrency |
| Deployment slots swap pattern (blue/green) | https://learn.microsoft.com/en-us/azure/app-service/deploy-best-practices#use-deployment-slots |

---

## Deploying to Azure

| Topic | URL |
|---|---|
| Deploy to Azure Functions (GitHub Actions) | https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-github-actions |
| Azure Login action (`azure/login`) | https://github.com/Azure/login |
| Azure Functions Core Tools action | https://github.com/Azure/functions-action |
| Deploy Bicep via GitHub Actions | https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-github-actions |
| Azure CLI action (`azure/cli`) | https://github.com/Azure/cli |
| What-if deployment for Bicep/ARM validation | https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-what-if |

---

## Reliability & Observability

| Topic | URL |
|---|---|
| Workflow run logs and debugging | https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/monitoring-workflows/using-workflow-run-logs |
| Enabling debug logging | https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/troubleshooting-workflows/enabling-debug-logging |
| Job summaries (`$GITHUB_STEP_SUMMARY`) | https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions#adding-a-job-summary |
| Status badges for workflows | https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/monitoring-workflows/adding-a-workflow-status-badge |
| Notifications for workflow failures | https://docs.github.com/en/account-and-profile/managing-subscriptions-and-notifications-on-github/setting-up-notifications/configuring-notifications#github-actions-notification-options |
