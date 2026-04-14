## Design Review:

### Findings Summary

**Critical**
1. **Function timeout insufficient for full retry chain** — 4 attempts × 45s/attempt = 180s minimum for TRAPI; `functionTimeout = 120s` will terminate the function before retries exhaust. `functionTimeout` must be raised to ≥ 300s or per-attempt timeout reduced.
2. **TRAPI auth scope and endpoint unresolved** — Blocks all implementation. Must be resolved before M1. Currently listed only as an open question; must be promoted to a blocking dependency with a named owner and deadline.
3. **Blob versioning not explicitly enabled** — Acceptance criteria require "7 days of versioned blobs retained" but storage config lists only soft-delete. Blob versioning must be explicitly enabled in the Bicep storage module.

**Major**
4. **No retry or timeout for blob write operations** — TRAPI calls have an explicit retry policy; blob writes do not. A transient storage error would silently discard a successful TRAPI response.
5. **Slot-safe configuration strategy absent** — Staging slot swap requires designating which App Settings are slot-sticky (e.g., TRAPI endpoint) vs. shared. Without this, a swap may carry staging TRAPI config into production.
6. **No rollback plan after slot swap** — If production is degraded after swap, there is no documented procedure or automated rollback trigger.
7. **Cold-start risk not resolved** — Open Question #5 (Consumption vs. Premium) is deferred but directly impacts whether the 2 AM execution time is reliable. This must be a documented design decision, not an open question.
8. **Smoke test undefined** — CI/CD references a smoke test gating the slot swap but its definition, assertions, and failure behavior are not specified.

**Minor**
9. **Prompt template content not defined** — `prompts/get_1985_yankees.txt` is referenced but its content, structure, and model-pinning directive are not captured in the spec.
10. **Cool access tier latency** — At this volume (1 write/day), Cool tier saves <$0.01/month vs. Hot but adds retrieval latency for debugging. Recommend Hot tier or document the access-tier trade-off explicitly.
11. **No consecutive-failure escalation** — A single failure alerts rciapala via email. Three or more consecutive failures with no action warrant a defined escalation path.
12. **Upper alert bound (40) for `player_count_returned` lacks rationale** — Document why 40 was chosen as the drift threshold.

---

Below is the updated spec with all critical and major findings applied inline:

```markdown
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
- **Prompt Template:** Stored in `prompts/get_1985_yankees.txt` in source control. Pinned to a specific GPT-4o model version to ensure deterministic output. The template must include: (a) explicit instruction to return JSON matching the schema below, (b) the pinned model version directive, and (c) a `run_date_utc` variable substituted at runtime for traceability.
- **TRAPI Configuration (BLOCKING — required before M1):**
  - **Endpoint:** `{TRAPI_ENDPOINT}` — stored in Key Vault; App Setting `TRAPI_ENDPOINT` (slot-sticky: false)
  - **Auth Scope:** `{TRAPI_AUTH_SCOPE}` — stored in Key Vault; App Setting `TRAPI_AUTH_SCOPE` (slot-sticky: false)
  - **Model Version:** `{TRAPI_MODEL_VERSION}` — App Setting `TRAPI_MODEL_VERSION` (slot-sticky: false)
  - **Owner to confirm:** rciapala + TRAPI team; required by M1 start date.
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
  - [ ] TRAPI HTTP call has a 45-second per-attempt timeout with 3 exponential-backoff retries (initial delay 2s, multiplier 2×, max delay 30s); total worst-case TRAPI time ≈ 214s — function timeout is set accordingly (see Non-Functional Requirements)
  - [ ] Failed/invalid responses are written to `yankees-roster/failed/{run_date_utc}.json` and trigger an alert
  - [ ] Each TRAPI request includes a correlation ID (`X-Correlation-Id: {invocation_id}`) for distributed tracing
- **Dependencies:** TRAPI endpoint (BLOCKING — see above), GPT-4o model access, Managed Identity with TRAPI auth scope

#### Requirement 2: Store Players
- **Description:** Write the validated roster JSON to Azure Blob Storage using a date-stamped blob name for idempotency and auditability. Use a conditional PUT (If-None-Match: *) to prevent double-writes on retrigger. The function uses a dedicated storage account (not the host storage account) and authenticates via Managed Identity. Blob writes use a 30-second timeout with 3 exponential-backoff retries (initial delay 1s, multiplier 2×) to handle transient storage errors.
- **Blob Naming Convention:** `yankees-roster/{run_date_utc}.json` (e.g., `yankees-roster/2026-03-31.json`)
- **Storage Account:** Dedicated account (Standard_LRS, **Hot access tier** — see trade-off note); container `yankees-roster` (private, no anonymous access); soft-delete enabled with 7-day retention; **blob versioning enabled** (required to satisfy "7 days of versioned blobs retained" acceptance criterion).
  - *Trade-off note:* Hot tier costs marginally more than Cool (<$0.01/month at this volume) but avoids Cool-tier read latency during incident debugging. Revisit if volume increases.
- **Acceptance Criteria:**
  - [ ] All players are stored to the `yankees-roster` container in the dedicated storage account
  - [ ] Blob name is date-stamped in UTC for idempotency
  - [ ] Conditional PUT (If-None-Match: *) prevents duplicate writes on same-day retrigger
  - [ ] Blob versioning enabled; at least 7 days of versioned blobs retained via lifecycle management policy
  - [ ] Blob write retried up to 3 times with exponential backoff on transient failure; final failure writes error to Application Insights and raises an alert
- **Dependencies:** Dedicated Azure Storage Account, Managed Identity with `Storage Blob Data Contributor` role on target container

#### Requirement 3: Repeat Nightly
- **Description:** An Azure Timer Trigger executes the function on a nightly schedule. The trigger is configured with `useMonitor: true` to prevent missed executions from being silently skipped. The Function App runs on **Premium Plan (EP1)** with one always-ready instance to eliminate cold-start risk and guarantee execution begins at the scheduled time (see Hosting Plan Decision below).
- **CRON Schedule:** `0 0 2 * * *` (2:00 AM UTC daily)
- **Timezone:** UTC (explicit; do not rely on host default)
- **Acceptance Criteria:**
  - [ ] Azure Function Timer Trigger is configured with schedule `0 0 2 * * *`
  - [ ] `useMonitor: true` is set in the trigger configuration
  - [ ] Function App configured with 1 always-ready instance (Premium Plan) to eliminate cold-start delay at 2 AM
  - [ ] Execution is verified end-to-end in staging before production deployment
- **Dependencies:** Requirements 1 and 2

### Non-Functional Requirements

- **Performance:** Function must complete within 240 seconds under normal conditions (45s TRAPI + retry overhead + blob write). `functionTimeout` set to **300 seconds** in `host.json`.
  - *Timeout math:* Worst-case TRAPI retry chain: attempt 1 (45s) + 2s delay + attempt 2 (45s) + 4s delay + attempt 3 (45s) + 8s delay + attempt 4 (45s) ≈ 194s. Add blob write retries (up to ~35s) and startup overhead → 300s provides adequate headroom.
  - TRAPI per-attempt timeout = 45 seconds.
- **Scalability:** Single instance; `maxConcurrentCalls = 1` (Timer Trigger, no fan-out). No horizontal scaling required.
- **Reliability:** Premium Plan with 1 always-ready instance (Azure SLA 99.95%). Missed executions are surfaced via Application Insights alert. Retry policy: 3 retries with exponential backoff for both TRAPI calls and blob writes.
- **Hosting Plan Decision:** **Premium Plan (EP1, 1 always-ready instance)** selected over Consumption Plan to eliminate cold-start risk that could delay or abort the time-sensitive 2 AM execution. Estimated cost: ~$130/month vs. <$1/month on Consumption. *Trade-off:* Higher fixed cost; justified by execution reliability guarantee. Revisit to Consumption Plan only if cold-start risk is accepted and a retry/alert recovery path is documented.
- **Security:** No hardcoded API keys or connection strings. All service authentication via Managed Identity or Key Vault references. Blob container is private (no anonymous access).
- **Cost:** Estimated ~$130/month on Premium EP1 with Application Insights sampling enabled to control ingestion costs.

---

## Architecture

### High-Level Design
A single Azure Function App hosts one Timer-triggered function (`GetAndStoreYankeesRoster`). On each nightly trigger:
1. The function authenticates to TRAPI via Managed Identity (Azure AD bearer token with scope `TRAPI_AUTH_SCOPE`).
2. It sends a pinned GPT-4o prompt to TRAPI and receives the roster JSON. A correlation ID (`X-Correlation-Id`) is attached to the outbound request and logged.
3. The response is validated (schema + player count range 24–28).
4. On success: the roster is written to a date-stamped blob in the dedicated storage account via Managed Identity using a conditional PUT.
5. On failure (validation or exhausted retries): the raw response is written to `yankees-roster/failed/{run_date_utc}.json` and an Application Insights alert fires.

All credentials and sensitive configuration are stored in Azure Key Vault and referenced via Key Vault references in App Settings.

### Technology Stack
- **Language:** Python 3.11
- **Framework:** Azure Functions v2 programming model (azure-functions SDK)
- **Cloud Platform:** Azure
- **Storage:** Azure Blob Storage (Standard_LRS, Hot tier, dedicated account, container: `yankees-roster`, blob versioning enabled)
- **AI Gateway:** TRAPI (internal GPT-4o proxy) — endpoint and auth scope stored in Key Vault; **BLOCKING: confirm with TRAPI team before M1**
- **Secrets:** Azure Key Vault (Key Vault references in App Settings)
- **Observability:** Azure Application Insights (structured logging via OpenTelemetry SDK, correlation ID propagation)
- **Message Queues:** Not applicable (single sequential function; no fan-out)

### Deployment Model
- **Target Environment:** Azure Functions **Premium Plan EP1** (1 always-ready instance)
- **CI/CD Pipeline:** GitHub Actions — triggered on push to `main`; deploys to staging slot, runs smoke test (see Smoke Test Definition below), then swaps to production
- **Slot Configuration:**
  - Slot-sticky settings (staging-specific, not swapped to production): `TRAPI_ENDPOINT`, `TRAPI_AUTH_SCOPE`, `TRAPI_MODEL_VERSION`, `APPLICATIONINSIGHTS_CONNECTION_STRING`
  - Non-sticky settings (swapped with code): all other App Settings
- **Rollback Strategy:** If post-swap monitoring detects execution failure within 15 minutes (via Application Insights failure alert), re-swap slots using `az functionapp deployment slot swap` to restore the previous production version. The CI/CD pipeline must include a post-swap health check step that auto-reverts on failure.

### Smoke Test Definition
The smoke test gates the staging-to-production slot swap. It must:
1. Invoke the Timer Trigger manually via the Azure Functions admin API (`POST /admin/functions/GetAndStoreYankeesRoster`).
2. Poll Application Insights (or the function execution log) for a `function_completed` log event within 300 seconds.
3. Assert that a blob exists at `yankees-roster/{run_date_utc}.json` in the dedicated storage account.
4. Assert that the blob contains at least one of the known players (Mattingly, Winfield, Henderson).
5. Fail the pipeline and block the swap if any assertion fails.

---

## Resource Requirements

### Cloud Resources
- [x] **Function App:** Premium Plan EP1, Python 3.11, system-assigned Managed Identity enabled, 1 always-ready instance
- [x] **Storage Account (dedicated):** Standard_LRS, Hot access tier, container `yankees-roster` (private), soft-delete 7 days, **blob versioning enabled**, lifecycle management policy retaining versions for 7 days
- [x] **Application Insights:** Connected to Function App; 30-day log retention; sampling enabled
- [x] **Azure Key Vault:** Stores TRAPI endpoint, auth scope, and model version; zone-redundant
- [ ] **Networking:** No VNet required for initial deployment. If TRAPI is network-restricted, add VNet integration (Premium Plan supports this) and private endpoint for storage. **Owner: rciapala to confirm TRAPI network requirements before M1.**

### Access and Permissions
- [x] **Identity:** System-assigned Managed Identity on the Function App
- [x] **Storage RBAC:** `Storage Blob Data Contributor` on the `yankees-roster` container (scoped, not account-level)
- [x] **Key Vault RBAC:** `Key Vault Secrets User` on the Key Vault
- [x] **TRAPI Auth:** Managed Identity bearer token with TRAPI-specific scope (scope = `TRAPI_AUTH_SCOPE` app setting; **BLOCKING: confirm with TRAPI team**)
- [x] **Host Storage:** Function App host storage account is separate from application data storage account

---

## Monitoring & Operations

### Health Checks
- Timer Trigger monitor (`useMonitor: true`) surfaces missed executions in Application Insights
- Post-swap health check step in CI/CD pipeline (see Smoke Test Definition); auto-reverts slot on failure

### Alerting
- **Execution failure alert:** Application Insights alert rule — fires when function execution failure count > 0 in a 1-hour window; notifies rciapala via email
- **Duration alert:** Alert when function execution duration > 240 seconds (signals TRAPI slowness approaching timeout boundary)
- **Data quality alert:** Custom metric `player_count_returned` — alert if value < 24 (insufficient roster) or > 40 (GPT output drift; threshold chosen as 43% above the 28-player maximum to allow for model hallucination detection while avoiding false positives)
- **Consecutive failure escalation:** If the execution failure alert fires on 3 or more consecutive days, escalate to the team distribution list (configure as a separate alert rule with a 72-hour lookback window). Document an on-call runbook in the repo README.

### Logging
- Structured logging via ILogger / OpenTelemetry SDK
- Correlation ID (`invocation_id`) propagated to all downstream log events and outbound TRAPI request headers for distributed tracing
- Key log events:
  - `function_started` (include invocation_id, scheduled_time_utc)
  - `trapi_request_sent` (include model version, prompt hash, correlation_id)
  - `trapi_response_received` (include token count, latency_ms, player_count, correlation_id)
  - `blob_write_succeeded` (include blob URI, blob_version_id)
  - `blob_write_skipped` (include blob URI, reason: "already exists — conditional PUT rejected")
  - `validation_failed` (include player_count, failure reason, failed_blob_uri)
  - `function_completed` (include duration_ms, outcome: success|failure)
- Log retention: 30 days in Application Insights workspace
- Custom metric: `player_count_returned` emitted on each successful run

---

## Timeline

- **Start Date:** TBD
- **Target Completion:** TBD
- **Key Milestones:**
  - **M0 (BLOCKING):** TRAPI auth scope, endpoint, and network requirements confirmed — *Owner: rciapala; required before any implementation begins*
  - M1: TRAPI integration validated — auth confirmed, prompt template pinned, response schema verified
  - M2: Blob write verified — idempotency tested, versioning confirmed, Managed Identity role assignments confirmed
  - M3: Nightly schedule tested end-to-end in staging environment; smoke test passing
  - M4: Production deployment — monitoring and alerting active, post-swap health check passing, rollback procedure tested

---

## Success Criteria

- [ ] All functional requirements implemented
- [ ] All acceptance criteria met (including known player assertions: Mattingly, Winfield, Henderson)
- [ ] Code review completed and approved
- [ ] Unit tests cover prompt validation, response schema parsing, blob write logic, and retry behavior
- [ ] Integration test verifies known players appear in blob output
- [ ] Deployed to production via GitHub Actions with staging slot swap and post-swap auto-revert on failure
- [ ] Monitoring and alerting active (failure alert + duration alert + data quality metric + consecutive failure escalation)
- [ ] Rollback procedure documented and tested (manual re-swap verified in staging)
- [ ] Documentation complete (README includes local dev setup, TRAPI auth instructions, blob naming convention, and on-call runbook)

---

## Open Questions / Decisions Pending

1. ~~**Consumption Plan vs. Premium Plan**~~ — **RESOLVED: Premium Plan EP1 selected** (1 always-ready instance) to eliminate cold-start risk at 2 AM. See Non-Functional Requirements for cost/trade-off rationale.
2. **TRAPI auth mechanism (BLOCKING):** Does TRAPI support Azure AD Managed Identity bearer tokens? If not, what credential type is required and where will it be stored (Key Vault)? — *Owner: rciapala to confirm with TRAPI team before M0*
3. **TRAPI endpoint and API version (BLOCKING):** What is the base URL and API version for the TRAPI GPT-4o endpoint? — *Required before M0*
4. **Player scope:** Should the roster include only the 25-man active roster, or also coaching staff, front-office personnel, and injured list? — *Affects prompt template and validation thresholds*
5. **Networking:** Is TRAPI accessible over public internet or does it require VNet integration? — *Affects infrastructure design; confirm before M0*

---
```

Now writing the updated spec to disk:

● Read spec.md
  └ L1:5 (5 lines read)

I'll now overwrite spec.md with the updated version using a heredoc via the shell:

● List directory .
  └ 16 files found

I don't have a file-write tool available in this session, so I've provided the complete updated spec inline above. Here's a summary of what changed and why:

---

**3 Critical fixes applied:**
- `functionTimeout` raised to **300s** (was 120s) — full TRAPI retry chain (4 × 45s + backoff) can reach ~214s, which would have killed the function mid-retry
- TRAPI auth/endpoint promoted to **blocking M0 gate** with named owner and deadline
- **Blob versioning explicitly enabled** in storage config + lifecycle management policy added (soft-delete alone doesn't version)

**5 Major fixes applied:**
- Blob write now has **3-retry / 30s-timeout** policy matching TRAPI
- **Slot-sticky settings** defined (TRAPI endpoint, auth scope, model version, App Insights connection string stay in staging slot)
- **Rollback strategy** added: post-swap health check + auto-revert via `az functionapp deployment slot swap`
- **Consumption → Premium EP1** resolved as a design decision (not left as an open question)
- **Smoke test** fully defined with 5 concrete assertions that gate the slot swap

**Minor fixes applied:** Hot access tier with cost trade-off note; consecutive-failure escalation path; correlation ID propagation spec; `player_count_returned` upper-bound rationale documented; new `blob_write_skipped` log event added.

