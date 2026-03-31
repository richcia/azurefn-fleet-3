# Project Specification

This file contains the design for an Azure Function

## Project Overview

### Name
1985-NY-Yankees

### Description
Nightly Azure Function that queries GPT-4o via TRAPI to retrieve the complete 1985 New York Yankees roster and persists the result as a dated JSON blob in Azure Blob Storage. The function runs once per day, is idempotent, uses Managed Identity for all authentication, and emits structured telemetry to Application Insights.

### Owner/Team
rciapala

---

## Requirements

### Functional Requirements

#### Requirement 1: Get Players
- **Description:** Call the TRAPI GPT-4o endpoint with a structured prompt requesting the full 1985 NY Yankees roster. Parse and validate the JSON response, asserting a minimum of 25 players each with `name` (string), `position` (string), and `uniform_number` (integer or null) fields.
- **Prompt Template:** `"Return a JSON array of all players on the 1985 New York Yankees roster. Each object must include: name (string), position (string), uniform_number (integer or null). Return only valid JSON with no prose."`
- **Acceptance Criteria:**
  - [ ] Response contains >= 25 player objects
  - [ ] Each player object contains `name`, `position`, and `uniform_number` fields
  - [ ] Function retries up to 3 times with 30s backoff if response is invalid or TRAPI returns 429/503
  - [ ] TRAPI call uses Managed Identity Bearer token (no API keys or connection strings)
- **Dependencies:**
  - TRAPI endpoint URL and Entra ID resource ID (to be confirmed — see Open Questions)

#### Requirement 2: Store Players
- **Description:** Write the validated roster JSON array to Azure Blob Storage. Blob path: `yankees-roster/1985-roster/{YYYY-MM-DD}.json` (date = UTC run date). Also overwrite `yankees-roster/1985-roster/latest.json` with the same content. Content-Type: `application/json`.
- **Acceptance Criteria:**
  - [ ] Dated blob (`YYYY-MM-DD.json`) is created or overwritten on each successful run
  - [ ] `latest.json` blob is overwritten on each successful run
  - [ ] Blob write uses Managed Identity (`Storage Blob Data Contributor` role)
  - [ ] Blob write success is confirmed before emitting success telemetry
- **Dependencies:**
  - Validated roster payload from Requirement 1

#### Requirement 3: Repeat Nightly
- **Description:** Configure a Timer trigger using NCRONTAB schedule `0 0 2 * * *` (2:00 AM UTC daily). Schedule is stored in app setting `TIMER_SCHEDULE` for slot-safe override. `runOnStartup` must be `false` in all non-local environments.
- **Acceptance Criteria:**
  - [ ] Function executes automatically at 2:00 AM UTC every day
  - [ ] `runOnStartup` is `false` in staging and production slots
  - [ ] Schedule is configurable via `TIMER_SCHEDULE` app setting without redeployment
- **Dependencies:**
  - Requirements 1 and 2

### Non-Functional Requirements

- **Performance:** End-to-end execution time < 3 minutes per nightly run. HTTP timeouts: 30s connect / 60s read on TRAPI calls. `functionTimeout` set to `00:05:00` in `host.json`.
- **Scalability:** Single-instance workload. Set `"maxConcurrentCalls": 1` in `host.json` to prevent overlapping Timer runs. No horizontal scale-out required.
- **Reliability:** 99.5% monthly successful run rate (no more than 3 missed or failed runs per month). Automatic retry policy: max 3 retries with 30s fixed delay interval configured in `host.json`. Alert fires if no successful run is detected within 26 hours.
- **Security:** No API keys, connection strings, or secrets in code or app settings. All service authentication via System-assigned Managed Identity using `DefaultAzureCredential`. Blob Storage access via `Storage Blob Data Contributor` RBAC role. TRAPI access via Entra ID Bearer token.
- **Cost:** Estimated < $5/month on Consumption Plan (1 invocation/day × minimal duration + App Insights ingestion at negligible volume + Standard LRS Storage).

---

## Architecture

### High-Level Design

End-to-end data flow:

1. **Azure Timer Trigger** fires at 2:00 AM UTC (`0 0 2 * * *`).
2. **Function** acquires an Entra ID Bearer token for TRAPI via `DefaultAzureCredential` (Managed Identity).
3. **TRAPI/GPT-4o call**: POST structured prompt to TRAPI endpoint. Parse JSON response. Validate: array length >= 25, required fields present. Retry up to 3× with 30s backoff on failure or invalid response.
4. **Blob write**: Using Managed Identity, write validated roster JSON to:
   - `yankees-roster/1985-roster/{UTC-date}.json` (dated, idempotent overwrite)
   - `yankees-roster/1985-roster/latest.json` (always-current pointer)
5. **Telemetry**: Emit structured log entry and `RosterFetchSuccess` custom event to Application Insights with fields: `runDate`, `playerCount`, `blobUri`, `durationMs`, `status`.
6. On any unrecoverable failure after retries: emit `RosterFetchFailure` event; alert fires via Application Insights alert rule.

### Technology Stack
- **Language(s):** Python 3.11
- **Framework(s):** Azure Functions v2 programming model (Python)
- **Cloud Platform:** Azure
- **Storage:** Azure Blob Storage — Standard LRS, Hot tier, container: `yankees-roster`
- **AI/LLM:** GPT-4o via TRAPI (internal endpoint — see Open Questions for URL confirmation)
- **Message Queues:** Not applicable

### Deployment Model
- **Target Environment:** Azure Functions Consumption Plan (Linux, Python 3.11). If cold-start latency becomes a concern after initial deployment, migrate to Flex Consumption.
- **CI/CD Pipeline:** GitHub Actions — CI on PR/push to `main` (pytest, flake8, 80% coverage gate); CD on merge to `main` (ZIP deploy with `WEBSITE_RUN_FROM_PACKAGE=1` to production).
- **Infrastructure as Code:** Bicep — modules for: Function App + App Service Plan, Storage Account + container, Application Insights (workspace-based), Log Analytics Workspace, Managed Identity role assignment (`Storage Blob Data Contributor`).

---

## Resource Requirements

### Cloud Resources
- [x] **Function App** — Consumption Plan, Linux, Python 3.11, System-assigned Managed Identity enabled
- [x] **Azure Storage Account** — Standard LRS, Hot tier; container: `yankees-roster` (private access, no public blob access)
- [x] **Application Insights** — Workspace-based, connected to Log Analytics Workspace; connection string stored in `APPLICATIONINSIGHTS_CONNECTION_STRING` app setting
- [x] **Log Analytics Workspace** — 90-day retention minimum
- [ ] **Networking** — No VNet or private endpoint required if TRAPI is a public SaaS endpoint. If TRAPI is an internal corporate API, add VNet integration and private DNS (see Open Questions).

### Access and Permissions
- [x] **Identity/Authentication method:** System-assigned Managed Identity on Function App; `DefaultAzureCredential` in code
- [x] **Service principal / Managed Identity:** System-assigned (no separate service principal required)
- [x] **Required RBAC roles:**
  - `Storage Blob Data Contributor` on the target Storage Account (scoped to resource, not subscription)
  - TRAPI-specific role or Entra ID app registration audience (to be confirmed — see Open Questions)

---

## Monitoring & Operations

### Health Checks
- Application Insights availability test: verify `latest.json` blob was updated within the last 26 hours (simple storage read check via Logic App or custom availability test).
- Timer trigger execution history visible in Azure Portal → Function App → Monitor.

### Alerting
- **Run Failure Alert:** `exceptions/count > 0` scoped to this Function App — severity 2, notify via email to rciapala.
- **Missed Run Alert:** Absence of `customEvents` where `name == 'RosterFetchSuccess'` in the last 26 hours — severity 2, notify via email to rciapala. (26-hour window accounts for minor timer drift.)
- **Retry Exhaustion Alert:** Custom metric `RosterFetchRetryExhausted` > 0 — severity 1.

### Logging
- **Aggregation:** Application Insights (workspace-based) connected to Log Analytics.
- **Structured log schema per run:**
  ```json
  {
    "runDate": "2026-03-31",
    "playerCount": 28,
    "blobUri": "https://<account>.blob.core.windows.net/yankees-roster/1985-roster/2026-03-31.json",
    "durationMs": 4821,
    "status": "success",
    "retryCount": 0
  }
  ```
- **Retention:** 90 days in Log Analytics Workspace.
- **Sensitive data:** No PII or secrets are logged. Managed Identity tokens must never be logged.

---

## host.json Configuration

```json
{
  "version": "2.0",
  "functionTimeout": "00:05:00",
  "retry": {
    "strategy": "fixedDelay",
    "maxRetryCount": 3,
    "delayInterval": "00:00:30"
  },
  "extensions": {
    "queues": {
      "maxDequeueCount": 1
    }
  }
}
```

---

## Timeline

- **Start Date:** TBD
- **Target Completion:** TBD
- **Key Milestones:**
  1. M1: Bicep IaC complete, Function App + Storage + App Insights deployed to dev environment
  2. M2: TRAPI integration complete with unit tests (prompt, parser, validator) at >= 80% coverage
  3. M3: End-to-end integration test passing in staging (mocked TRAPI or dev TRAPI)
  4. M4: Production deployment with alerting active and first nightly run verified

---

## Success Criteria

- [ ] All functional requirements implemented
- [ ] All acceptance criteria met (including player count >= 25 and field validation)
- [ ] Code review completed and approved
- [ ] Unit test coverage >= 80% on function logic (prompt building, response parsing, validation, blob path generation)
- [ ] Integration test passing: mocked TRAPI → correct blob content → structured log emitted
- [ ] Deployed to production via GitHub Actions CI/CD pipeline
- [ ] Monitoring and alerting active (run failure alert + missed run alert verified in staging)
- [ ] No secrets or connection strings in code or app settings (Managed Identity only)
- [ ] Documentation complete (README with local dev setup, IaC deployment instructions)

---

## Open Questions / Decisions Pending

1. **TRAPI endpoint URL and Entra ID audience:** What is the base URL for the TRAPI GPT-4o endpoint, and does it support Entra ID Managed Identity Bearer token authentication? This is a blocker for the security design.
2. **TRAPI network boundary:** Is TRAPI a public SaaS endpoint or a corporate internal API requiring VNet integration and private DNS resolution?
3. **Roster output schema:** Does any downstream consumer require the roster JSON to conform to a specific schema beyond `{name, position, uniform_number}`?
4. **Blob lifecycle policy:** Should historical dated blobs (`1985-roster/YYYY-MM-DD.json`) be retained indefinitely or subject to an Azure Blob lifecycle management policy (e.g., delete after 90 days)?
5. **Target Azure subscription and resource group:** What subscription, resource group, and region should resources be deployed to?
6. **Deployment environment names:** What are the environment names (e.g., dev, staging, production) and what are the promotion gates between them?

---
