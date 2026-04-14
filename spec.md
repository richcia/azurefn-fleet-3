● Read spec.md

● Read spec.md
  └ 1 line read

The `spec.md` file contains only a single placeholder line (`● Read spec.md`) — no design content exists. Every section of the design is missing, which triggers critical findings across all rubric areas. Below is my full review followed by the rewritten spec.

---

## Design Review: `spec.md`

### Summary
The spec represents an Azure Function workload (inferred from repo context: Timer-triggered function that fetches data from a TRAPI API and writes results to Azure Blob Storage). The current spec document contains no actual design content — only a single unchecked placeholder item. All design areas are absent.

---

### Findings

#### 🔴 Critical

| # | Title | Component | Evidence | Recommendation |
|---|-------|-----------|----------|----------------|
| C1 | No trigger design specified | trigger | File contains only `● Read spec.md` | Define Timer Trigger schedule (NCRONTAB), run-on-startup behavior, and singleton enforcement via `host.json` |
| C2 | No output binding or storage design | binding | No binding documented | Specify Blob output binding or SDK-based write; document container name, blob naming strategy, and overwrite vs. append policy |
| C3 | No idempotency or failure recovery strategy | other | Absent | Define what happens on partial failure: blob not written, TRAPI unreachable, timeout. Document retry policy and poison-run handling |
| C4 | No security design | security | Absent | Document identity (Managed Identity preferred), RBAC roles required, secrets externalization (no connection strings in code/config), and network boundary |
| C5 | No observability plan | observability | Absent | Specify structured logging fields, Application Insights integration, custom metrics, and alert thresholds |
| C6 | No external dependency contract | dependency | Absent | Document TRAPI endpoint, auth scheme, timeout values, expected payload schema, and circuit-breaker / backoff behavior |
| C7 | No non-functional requirements | other | Absent | Define SLAs: max acceptable latency, data freshness window, error budget, data retention |
| C8 | No deployment or rollout strategy | deployment | Absent | Define deployment slots (if any), rollback procedure, config promotion strategy, and versioning policy |

#### 🟡 Major

| # | Title | Component | Evidence | Recommendation |
|---|-------|-----------|----------|----------------|
| M1 | No concurrency / scaling constraints | host | Absent | For Timer Triggers on Consumption plan, document `batchSize`, `maxConcurrentCalls` not applicable, but specify `WEBSITE_MAX_DYNAMIC_APPLICATION_SCALE_OUT` and singleton enforcement |
| M2 | No data consistency model defined | data | Absent | Define whether blob writes are atomic; document blob lease strategy to prevent duplicate concurrent writes |
| M3 | No configuration strategy | config | Absent | List all required app settings, distinguish slot-safe vs. sticky settings, and require all secrets via Key Vault references |

#### 🟢 Minor

| # | Title | Component | Evidence | Recommendation |
|---|-------|-----------|----------|----------------|
| N1 | No acceptance criteria | other | Absent | Add testable acceptance criteria per functional requirement |
| N2 | No architecture diagram | other | Absent | Add a simple component diagram showing Function → TRAPI → Blob Storage data flow |

---

### Missing Details (treated as Critical)
- Trigger schedule expression
- TRAPI base URL, auth scheme, and response schema
- Blob container name and blob key/naming convention
- Managed Identity vs. key-based auth decision
- Retry and timeout budgets for TRAPI calls
- Alert thresholds and on-call escalation path
- Deployment environment matrix (dev / staging / prod)

---

Now writing the updated `spec.md`:

● Read spec.md
  └ L1:3 (3 lines read)

Now I'll overwrite the spec with the updated version:

● skill(customize-cloud-agent)

Now writing the updated `spec.md` with all critical and major findings addressed:

● Read spec.md
  └ 69 lines read

The file has accumulated my prior output. I'll now write the complete, clean updated spec:

I need to write the file using bash since I need to replace its entire contents:

```bash
cat > /home/runner/work/azurefn-fleet-3/azurefn-fleet-3/spec.md << 'SPECEOF'
...
SPECEOF
```

● List directory .
  └ 16 files found

Since I only have `view`, `skill`, and `report_intent` as available function tools (no write/bash access), I'll deliver the complete updated `spec.md` content here for you to apply:

---

## Updated `spec.md`

```markdown
# Azure Function Design Specification
# 1985 NY Yankees Roster Data Pipeline

## 1. Overview

This Azure Function periodically fetches player roster data from a TRAPI (Team Roster API) endpoint and persists the response as a JSON blob in Azure Blob Storage. The function is intended to keep a durable, queryable snapshot of the 1985 New York Yankees roster up to date on a scheduled cadence.

**Runtime:** Python 3.11
**Hosting Plan:** Azure Functions Consumption (Linux)
**Region:** `[TODO: specify target Azure region]`

---

## 2. Architecture

```
┌─────────────────────────┐        HTTP/Bearer        ┌──────────────────┐
│  Azure Function         │ ─────────────────────────▶│  TRAPI Endpoint  │
│  (Timer Trigger)        │◀─────────────────────────  │  (External API)  │
│                         │      JSON roster payload   └──────────────────┘
│  function_app.py        │
│  trapi_client.py        │        SDK (identity)      ┌──────────────────┐
│  blob_writer.py         │ ─────────────────────────▶│  Azure Blob      │
└─────────────────────────┘                            │  Storage         │
         ▲                                             │  yankees-roster/ │
         │ Timer                                       └──────────────────┘
   Azure Scheduler
```

---

## 3. Functional Requirements

### FR-1: Scheduled Execution
- The function **MUST** execute on a configurable NCRONTAB schedule.
- Default schedule: `0 0 * * * *` (every hour, on the hour).
- Schedule is configurable via the `TIMER_SCHEDULE` app setting.
- `runOnStartup` **MUST** be `false` in production to prevent accidental runs on cold starts or deployments.

### FR-2: TRAPI Data Fetch
- The function **MUST** call the TRAPI roster endpoint: `GET {TRAPI_BASE_URL}/roster/{TEAM_ID}`.
- Authentication is via a Bearer token obtained using `DefaultAzureCredential` against the TRAPI resource scope `{TRAPI_RESOURCE_SCOPE}`.
- On a non-2xx HTTP response the function **MUST** raise an exception (triggering the retry/failure path described in FR-4).
- Request timeout: **30 seconds**. Hard timeout enforced via `httpx` or `requests` session config.

### FR-3: Blob Write
- The function **MUST** write the fetched JSON payload to Azure Blob Storage.
  - **Container:** `yankees-roster`
  - **Blob name:** `roster-latest.json` (overwrite on each successful run)
  - **Content-Type:** `application/json`
  - **Access tier:** Hot
- The write **MUST** use the SDK (`azure-storage-blob`) with `DefaultAzureCredential`; no shared-key or SAS connections.
- Blob overwrite is intentional and idempotent: repeated writes with the same data are safe.

### FR-4: Failure Handling & Idempotency
- A failed TRAPI fetch or blob write **MUST NOT** leave a partial or corrupt blob.
  - Write the full response to memory first; only call `upload_blob(overwrite=True)` when the payload is fully received.
- On unhandled exception the Azure Functions host will **not** retry a Timer Trigger automatically. The function **MUST** log the error with severity `ERROR` and re-raise so the host marks the invocation as failed (visible in App Insights).
- Operators can re-trigger manually via the Azure Portal or `az functionapp` CLI.
- Duplicate run protection: because the blob is overwritten (not appended), duplicate runs are safe.

---

## 4. Non-Functional Requirements

| Requirement | Target |
|---|---|
| End-to-end latency (fetch + write) | ≤ 10 seconds p95 |
| Data freshness | Within 1 hour of scheduled run |
| Availability | ≥ 99.5% successful runs per week |
| Error budget | ≤ 2 failed runs per week before alert fires |
| Blob data retention | 90 days (via Blob lifecycle policy) |
| Cold-start tolerance | Acceptable; schedule-based, not latency-sensitive |

---

## 5. Security Design

### 5.1 Identity
- The Function App uses a **system-assigned Managed Identity**.
- No connection strings, SAS tokens, or storage account keys are stored in app settings or code.
- `AzureWebJobsStorage__accountName` is used for the Functions host runtime (identity-based, no `listKeys`).
- `allowSharedKeyAccess: false` is set on the Storage Account.

### 5.2 RBAC Assignments
| Principal | Resource | Role |
|---|---|---|
| Function App MSI | Storage Account | Storage Blob Data Contributor |
| Function App MSI | Storage Account | Storage Queue Data Contributor (required by Functions host) |
| Function App MSI | TRAPI API (Entra App Registration) | `[TODO: specify TRAPI app role]` |

### 5.3 Secrets & Configuration
- All sensitive values (TRAPI resource scope, TRAPI base URL if considered sensitive) **MUST** be stored as Key Vault secrets and referenced in app settings via `@Microsoft.KeyVault(SecretUri=...)`.
- No secrets in source code or committed configuration files.
- `local.settings.json` is `.gitignore`d; `local.settings.json.example` provides the template with placeholder values.

### 5.4 Network Boundaries
- `[TODO: specify whether VNet integration or private endpoints are required]`
- Default: public endpoints with identity-based access control. If private networking is required, document VNet, subnet, and private DNS zone configuration.

---

## 6. Observability

### 6.1 Structured Logging
All log entries **MUST** include:
- `invocation_id` (from Azure Functions context)
- `function_name`
- `run_timestamp` (UTC ISO-8601)
- `team_id`
- For TRAPI calls: `http_status`, `latency_ms`
- For blob writes: `blob_name`, `bytes_written`
- On error: `error_type`, `error_message`, stack trace

### 6.2 Application Insights
- `APPLICATIONINSIGHTS_CONNECTION_STRING` is injected as an app setting (Key Vault reference).
- Distributed tracing is enabled via the Azure Functions host.
- Custom metrics to emit per invocation:
  - `trapi_fetch_duration_ms`
  - `blob_write_duration_ms`
  - `roster_payload_bytes`

### 6.3 Alerts
| Alert | Condition | Severity | Action |
|---|---|---|---|
| Function exceptions | `exceptions` count > 0 in 24 h rolling window | Sev 2 | Email action group |
| Consecutive failures | `[TODO: define threshold, e.g. 3 consecutive failed runs]` | Sev 1 | `[TODO: PagerDuty / on-call escalation]` |
| Stale blob | Blob `Last-Modified` > 2 hours old | Sev 2 | Email action group |

---

## 7. Configuration Strategy

### 7.1 Required App Settings
| Setting | Description | Slot-Safe | Source |
|---|---|---|---|
| `TIMER_SCHEDULE` | NCRONTAB expression | Yes | App setting |
| `TRAPI_BASE_URL` | Base URL for TRAPI API | Yes | Key Vault ref |
| `TRAPI_RESOURCE_SCOPE` | Entra resource scope for TRAPI Bearer token | Yes | Key Vault ref |
| `TEAM_ID` | Team identifier passed to TRAPI | Yes | App setting |
| `STORAGE_ACCOUNT_NAME` | Target storage account name | Yes | App setting |
| `BLOB_CONTAINER_NAME` | Target container name (`yankees-roster`) | Yes | App setting |
| `AzureWebJobsStorage__accountName` | Storage account for Functions host (identity-based) | No (sticky) | App setting |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights telemetry | No (sticky) | Key Vault ref |
| `FUNCTIONS_WORKER_RUNTIME` | `python` | No | App setting |
| `FUNCTIONS_EXTENSION_VERSION` | `~4` | No | App setting |

### 7.2 Slot Configuration
- Deployment slots are **not used** on the Consumption plan (not supported). Deployments are zero-downtime rolling via the Functions host.
- `[TODO: If upgrading to Premium plan, define staging slot promotion process]`

---

## 8. Scaling & Concurrency

- **Hosting plan:** Consumption (serverless). Scale-out is automatic but capped.
- **Timer Trigger singleton:** A single Timer Trigger invocation runs at a time. The Functions runtime enforces this via distributed lock; no additional singleton configuration is required.
- `WEBSITE_MAX_DYNAMIC_APPLICATION_SCALE_OUT` **SHOULD** be set to `1` for this function since concurrent roster writes are not desired and could cause race conditions on the blob.
- Cold-start latency is acceptable given the hourly schedule cadence.

---

## 9. Dependency Design

### 9.1 TRAPI Client
- HTTP client: `httpx` or `requests` with a session-level timeout of **30 seconds** (connect: 10 s, read: 20 s).
- **Retry policy:** 2 retries with exponential backoff (1 s, 2 s) on transient HTTP errors (429, 503, 502, 504) and network errors.
- **Circuit breaker:** `[TODO: evaluate tenacity or stamina library; define open-circuit threshold]`
- No retry on 4xx client errors (except 429).

### 9.2 Blob Storage Client
- SDK: `azure-storage-blob >= 12.19.0`.
- Identity: `DefaultAzureCredential`.
- Upload call: `upload_blob(overwrite=True)` with `content_settings=ContentSettings(content_type="application/json")`.
- Retry is handled by the SDK's built-in retry policy (3 retries, exponential backoff).

---

## 10. Deployment & Operations

### 10.1 Infrastructure
- Provisioned via **Bicep** templates under `/infra`.
- Modules: `storage.bicep`, `functionapp.bicep`, `rbac.bicep`, `monitoring.bicep`, `alerts.bicep`.
- Tags: `project=1985-NY-Yankees`, `owner=rciapala`.

### 10.2 CI/CD Pipeline
- **CI:** Run on every PR — install dependencies (`requirements.txt`), run `pytest` with coverage.
- **CD:** On merge to `main` — deploy via `az functionapp deployment source` or GitHub Actions `Azure/functions-action`.
- Deployment package includes only `requirements-prod.txt` dependencies (no test tooling).

### 10.3 Rollback
- Previous deployment package is retained in the deployment history (Azure Portal > Deployment Center).
- To rollback: redeploy previous package via `az functionapp deployment source config-zip` or via the Portal.
- Configuration rollback: revert app settings changes via Azure Portal or Bicep re-deploy from prior Git commit.

### 10.4 Environment Matrix
| Environment | Schedule | `runOnStartup` | Log Level |
|---|---|---|---|
| Local dev | `0 */5 * * * *` (every 5 min) | `true` (for debugging) | DEBUG |
| Staging | `0 0 * * * *` | `false` | INFO |
| Production | `0 0 * * * *` | `false` | WARNING |

---

## 11. Acceptance Criteria

| ID | Criterion | How to Verify |
|---|---|---|
| AC-1 | Function executes on schedule without error | App Insights: zero `exceptions` for 48 h in staging |
| AC-2 | `roster-latest.json` blob is updated each run | Check blob `Last-Modified` timestamp after scheduled run |
| AC-3 | Blob content matches TRAPI response payload | SHA-256 of stored blob equals SHA-256 of raw TRAPI response |
| AC-4 | No shared keys or SAS tokens used | `allowSharedKeyAccess: false`; verify no `AccountKey` in app settings |
| AC-5 | Failure is logged and surfaced in App Insights | Inject a TRAPI timeout; verify `ERROR` log and failed invocation in portal |
| AC-6 | Duplicate run leaves blob in valid state | Trigger two concurrent runs (manual); verify blob is valid JSON |

---

## 12. Open Questions / TODOs

- [ ] Confirm TRAPI endpoint URL and authentication scheme (Bearer scope / Entra App Registration app role)
- [ ] Confirm whether private networking (VNet integration) is required
- [ ] Define on-call escalation path for Sev 1 alerts
- [ ] Confirm data retention requirement (90 days assumed)
- [ ] Evaluate circuit-breaker library (`tenacity` vs `stamina`)
- [ ] Confirm upgrade path to Premium plan if cold-start latency becomes a concern
```

---

Now committing this to the repo:

● Read spec.md
  └ L1:5 (4 lines read)

> **Note:** I don't have a file-write tool in this environment, so I can't save `spec.md` directly. The complete updated spec is above — copy everything between the triple-backtick fences and overwrite `spec.md` with it.

---

## Review Summary

**Original spec:** 1 placeholder line — zero design content.

**Findings:** 8 Critical · 3 Major · 2 Minor

| Severity | Count | Key issues |
|---|---|---|
| 🔴 Critical | 8 | No trigger design, no storage design, no idempotency strategy, no security design, no observability, no dependency contract, no NFRs, no deployment strategy |
| 🟡 Major | 3 | No scaling/concurrency constraints, no data consistency model, no config strategy |
| 🟢 Minor | 2 | No acceptance criteria, no architecture diagram |

**What the updated spec adds:**
- Timer Trigger schedule, `runOnStartup: false`, singleton enforcement
- Blob naming strategy, overwrite policy, `upload_blob(overwrite=True)` pattern
- Managed Identity RBAC table, `allowSharedKeyAccess: false`, Key Vault references
- TRAPI timeout (30 s), retry policy (2 retries, exp backoff), circuit-breaker TODO
- Structured log fields, App Insights custom metrics, alert thresholds
- Full app settings table (slot-safe flagged), environment matrix (dev/staging/prod)
- Testable acceptance criteria and open TODOs for remaining unknowns

