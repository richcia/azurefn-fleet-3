# Project Specification

This file contains the design for an Azure Function

## Project Overview

### Name
1985-NY-Yankees

### Description
List the members of the 1985 New York Yankees by querying GPT-4o via TRAPI nightly and persisting the structured roster to Azure Blob Storage using Managed Identity for all service authentication.

### Owner/Team
rciapala

---

## Requirements

### Functional Requirements

#### Requirement 1: Get Players
- **Description:** Query GPT-4o via TRAPI using a pinned, version-controlled prompt template to retrieve the 1985 New York Yankees roster. The response must be validated for completeness (expected player count: 24–28 active roster members) before proceeding. If validation fails, write the raw response to a `failed/` blob prefix and raise an alert — do not write to the primary output path.
- **Prompt Template:** Stored in `prompts/get_1985_yankees.txt` in source control. Pinned to a specific GPT-4o model version to reduce model drift; determinism/reproducibility must be enforced via TRAPI request parameters (e.g., temperature=0 or equivalent) and by relying on the schema and roster-count validation described below, rather than by model pinning alone.
- **Expected Response Schema:**
  ```json
  {
    "players": [
      { "name": "string", "position": "string", "jersey_number": "integer" }
    ]
  }
  ```
- **Acceptance Criteria:**
  - [ ] All players are returned (24–28 roster members, including known players: Don Mattingly, Dave Winfield, Rickey Henderson)
  - [ ] Response is validated against expected schema before blob write
  - [ ] TRAPI HTTP call has a 45-second timeout with 3 exponential-backoff retries
  - [ ] Failed/invalid responses are written to `failed/{run_date_utc}.json` in the `yankees-roster` container and trigger an alert
- **Dependencies:** TRAPI endpoint, GPT-4o model access, Managed Identity with TRAPI auth scope

#### Requirement 2: Store Players
- **Description:** Write the validated roster JSON to Azure Blob Storage using a date-stamped blob name for idempotency and auditability. Use a conditional PUT (If-None-Match) to prevent double-writes on retrigger. The function uses a dedicated storage account (not the host storage account) and authenticates via Managed Identity.
- **Blob Naming Convention:** `{run_date_utc}.json` (e.g., `2026-03-31.json`) within the `yankees-roster` container
- **Storage Account:** Dedicated account (Standard_LRS, Cool access tier); container `yankees-roster` (private, no anonymous access); soft-delete enabled with 7-day retention.
- **Acceptance Criteria:**
  - [ ] All players are stored to the `yankees-roster` container in the dedicated storage account
  - [ ] Blob name is date-stamped in UTC for idempotency
  - [ ] Conditional PUT prevents duplicate writes on same-day retrigger
  - [ ] Deleted blobs are recoverable for at least 7 days via soft-delete retention policy
- **Dependencies:** Dedicated Azure Storage Account, Managed Identity with `Storage Blob Data Contributor` role on target container

#### Requirement 3: Repeat Nightly
- **Description:** An Azure Timer Trigger executes the function on a nightly schedule. The trigger is configured with `useMonitor: true` to prevent missed executions from being silently skipped.
- **CRON Schedule:** `0 0 2 * * *` (2:00 AM UTC daily)
- **Timezone:** UTC (explicit; do not rely on host default)
- **Acceptance Criteria:**
  - [ ] Azure Function Timer Trigger is configured with schedule `0 0 2 * * *`
  - [ ] `useMonitor: true` is set in the trigger configuration
  - [ ] Execution is verified end-to-end in staging before production deployment
- **Dependencies:** Requirements 1 and 2

### Non-Functional Requirements

- **Performance:** Function must complete within 60 seconds under normal conditions. `functionTimeout` set to 120 seconds in `host.json` as a safety buffer. TRAPI HTTP call timeout = 45 seconds.
- **Scalability:** Single logical execution per scheduled run (Timer Trigger, no fan-out). Rely on Timer Trigger’s singleton behavior; no horizontal scaling required.
- **Reliability:** Best-effort execution on Consumption Plan (Azure SLA ~99.95%). Missed executions are surfaced via Application Insights alert. Retry policy: 3 retries with exponential backoff for TRAPI calls.
- **Security:** No hardcoded API keys or connection strings. All service authentication via Managed Identity or Key Vault references. Blob container is private (no anonymous access).
- **Cost:** Estimated <$1/month on Consumption Plan at 1 execution/day. Application Insights sampling enabled to control ingestion costs.

---

## Architecture

### High-Level Design
A single Azure Function App hosts one Timer-triggered function (`GetAndStoreYankeesRoster`). On each nightly trigger:
1. The function authenticates to TRAPI via Managed Identity (Azure AD bearer token).
2. It sends a pinned GPT-4o prompt to TRAPI and receives the roster JSON.
3. The response is validated (schema + player count range).
4. On success: the roster is written to a date-stamped blob in the dedicated storage account via Managed Identity.
5. On failure: the raw response is written to `failed/` prefix and an Application Insights alert fires.

All credentials and sensitive configuration are stored in Azure Key Vault and referenced via Key Vault references in App Settings.

### Technology Stack
- **Language:** Python 3.11
- **Framework:** Azure Functions v2 programming model (azure-functions SDK)
- **Cloud Platform:** Azure
- **Storage:** Azure Blob Storage (Standard_LRS, dedicated account, container: `yankees-roster`)
- **AI Gateway:** TRAPI (internal GPT-4o proxy) — endpoint and auth scope to be confirmed by owner
- **Secrets:** Azure Key Vault (Key Vault references in App Settings)
- **Observability:** Azure Application Insights (structured logging via OpenTelemetry SDK)
- **Message Queues:** Not applicable (single sequential function; no fan-out)

### Deployment Model
- **Target Environment:** Azure Functions Consumption Plan (serverless)
- **CI/CD Pipeline:** GitHub Actions — triggered on push to `main`; deploys to staging slot, runs smoke test, then swaps to production
- **Infrastructure as Code:** Bicep — provisions Function App, dedicated Storage Account, App Insights workspace, Key Vault, and all Managed Identity role assignments

---

## Resource Requirements

### Cloud Resources
- [x] **Function App:** Consumption Plan, Python 3.11, system-assigned Managed Identity enabled
- [x] **Storage Account (dedicated):** Standard_LRS, container `yankees-roster` (private), soft-delete 7 days, Cool access tier
- [x] **Application Insights:** Connected to Function App; 30-day log retention; sampling enabled
- [x] **Azure Key Vault:** Stores TRAPI credentials (if Managed Identity auth is unsupported by TRAPI); zone-redundant
- [ ] **Networking:** No VNet required for initial deployment. If TRAPI is network-restricted, add VNet integration and private endpoint for storage.

### Access and Permissions
- [x] **Identity:** System-assigned Managed Identity on the Function App
- [x] **Storage RBAC:** `Storage Blob Data Contributor` on the `yankees-roster` container (scoped, not account-level)
- [x] **Key Vault RBAC:** `Key Vault Secrets User` on the Key Vault (if TRAPI credentials are stored there)
- [x] **TRAPI Auth:** Managed Identity bearer token with TRAPI-specific scope (scope TBD — confirm with TRAPI team)
- [ ] **Host Storage:** Function App host storage account is separate from application data storage account

---

## Monitoring & Operations

### Health Checks
- Custom HTTP-triggered `/api/health` function implemented in the Function App and configured as the App Service Health Check path
- Timer Trigger monitor (`useMonitor: true`) surfaces missed executions in Application Insights

### Alerting
- **Execution failure alert:** Application Insights alert rule — fires when function execution failure count > 0 in a 1-hour window; notifies rciapala via email
- **Duration alert:** Alert when function execution duration > 90 seconds (signals TRAPI slowness)
- **Data quality alert:** Custom metric `player_count_returned` — alert if value < 24 or > 40 (GPT output drift), emitted on both successful runs and validation-failure runs so out-of-range responses still trigger this alert

### Logging
- Structured logging via ILogger / OpenTelemetry SDK
- Key log events: `function_started`, `trapi_request_sent` (include model version, prompt hash), `trapi_response_received` (include token count, latency ms, player count), `blob_write_succeeded` (include blob URI), `function_completed`
- Log retention: 30 days in Application Insights workspace
- Custom metric: `player_count_returned` emitted on every run, including when player-count validation fails and the response is written to the `failed/` blob prefix

---

## Timeline

- **Start Date:** TBD
- **Target Completion:** TBD
- **Key Milestones:**
  - M1: TRAPI integration validated — auth confirmed, prompt template pinned, response schema verified
  - M2: Blob write verified — idempotency tested, Managed Identity role assignments confirmed
  - M3: Nightly schedule tested end-to-end in staging environment
  - M4: Production deployment — monitoring and alerting active, smoke test passing

---

## Success Criteria

- [ ] All functional requirements implemented
- [ ] All acceptance criteria met (including known player assertions: Mattingly, Winfield, Henderson)
- [ ] Code review completed and approved
- [ ] Unit tests cover prompt validation, response schema parsing, and blob write logic
- [ ] Integration test verifies known players appear in blob output
- [ ] Deployed to production via GitHub Actions with staging slot swap
- [ ] Monitoring and alerting active (failure alert + duration alert + data quality metric)
- [ ] Documentation complete (README includes local dev setup, TRAPI auth instructions, and blob naming convention)

---

## Open Questions / Decisions Pending

1. **TRAPI auth mechanism:** Does TRAPI support Azure AD Managed Identity bearer tokens? If not, what credential type is required and where will it be stored (Key Vault)? — *Owner: rciapala to confirm with TRAPI team*
2. **TRAPI endpoint and API version:** What is the base URL and API version for the TRAPI GPT-4o endpoint? — *Required before implementation*
3. **Player scope:** Should the roster include only the 25-man active roster, or also coaching staff, front-office personnel, and injured list? — *Affects prompt template and validation thresholds*
4. **Networking:** Is TRAPI accessible over public internet or does it require VNet integration? — *Affects infrastructure design*
5. **Consumption Plan vs. Premium Plan:** Is there a strict SLA on the 2 AM execution time? If yes, Premium Plan with always-ready instances is required to eliminate cold-start risk.

---

