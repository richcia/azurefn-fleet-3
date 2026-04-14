● Read spec.md
  └ 125 lines read

● Read spec.md
  └ L1:126 (125 lines read)

Here is the design review, followed by the updated `spec.md` written back to disk.

---

## Design Review — `spec.md`

### Summary
A nightly Azure Function (Timer Trigger) that queries GPT-4o via TRAPI for the 1985 NY Yankees roster and persists results to Azure Blob Storage. The "No API Keys" constraint correctly implies Managed Identity. The core functional intent is clear, but the spec is largely template placeholder text — most architecture, NFR, resource, and observability sections are unfilled, making it unimplementable as written.

---

### Findings

**🔴 Critical**

| # | Title | Evidence | Recommendation |
|---|-------|----------|----------------|
| C1 | Architecture section entirely placeholder | Lines 55–68: high-level design, tech stack, deployment model all `[placeholder]` | Fill in: Python, Azure Functions v2 Consumption, Bicep IaC, GitHub Actions CI/CD |
| C2 | Non-functional requirements incomplete | Lines 45–49: Performance, Scalability, Reliability, Cost all blank | Define concrete targets (e.g., function completes within 4 min, 99.5% monthly uptime) |
| C3 | Resource requirements all placeholder | Lines 74–83 | Specify: Consumption Plan Function App, StorageV2 account, `yankees-roster` blob container, system-assigned Managed Identity |
| C4 | Monitoring & Operations entirely placeholder | Lines 89–97 | Specify: Application Insights, structured logging, exception alerting, 30-day log retention |
| C5 | No idempotency strategy | Not mentioned anywhere | Define: blob write must use a fixed key (e.g., `yankees-roster/roster.json`) and overwrite on each run to be idempotent |
| C6 | No error handling / failure recovery | Not mentioned | Specify retry policy for TRAPI call (e.g., 3 retries, exponential backoff) and blob write failure behavior |
| C7 | TRAPI authentication not specified | Req 1 says "using TRAPI" with no auth detail | Specify: Managed Identity bearer token via `DefaultAzureCredential` — no stored secrets |
| C8 | Blob naming/versioning convention absent | Req 2 says "store to blob" with no path or format | Define: `yankees-roster/roster.json`, JSON format, overwrite each nightly run |

**🟠 Major**

| # | Title | Evidence | Recommendation |
|---|-------|----------|----------------|
| M1 | Acceptance criteria for Req 1 is untestable | "All players are returned" — no expected count or source of truth | Add: "Response contains ≥ 25 player records with name, position, and uniform number fields" |
| M2 | No function execution timeout specified | GPT-4o can have high latency; Consumption plan default is 5 min | Set `functionTimeout` to `00:04:00` in `host.json`; document expected TRAPI p95 latency |
| M3 | Output blob format not specified | Req 2 mentions "blob" but not shape | Define JSON schema for output: array of `{ name, position, number }` objects |
| M4 | No structured logging requirements | Logging section is placeholder | Require: log TRAPI response time, player count retrieved, blob write success/failure with Application Insights |

**🟡 Minor**

| # | Title | Recommendation |
|---|-------|----------------|
| m1 | Typo: "Requirementes" | Fix to "Requirements" (Req 3 dependencies line) |
| m2 | Timeline all placeholder | Fill in or remove |
| m3 | Success Criteria are generic template items | Make project-specific (e.g., "roster.json present in `yankees-roster` container after first nightly run") |
| m4 | Open Questions has only placeholder | Replace with real open questions or remove section |

---

Now writing the updated spec:

● Read spec.md
  └ L1:5 (4 lines read)

● skill(customize-cloud-agent)

Now writing the updated `spec.md` with all critical and major findings applied inline:

● Read spec.md
  └ 125 lines read

```
# Project Specification

This file defines the complete project requirements and specification. 
It is used by the design-validator skill to verify completeness before implementation begins.

## Project Overview

### Name
1985-NY-Yankees

### Description
A nightly Azure Function that queries GPT-4o via TRAPI to retrieve the roster of the 1985 New York Yankees and persists the results as a JSON blob in Azure Blob Storage. Authentication uses Managed Identity exclusively — no API keys or stored secrets.

### Owner/Team
rciapala

---

## Requirements

### Functional Requirements

#### Requirement 1: Get Players
- **Description:** Query GPT-4o via TRAPI using a Managed Identity bearer token to retrieve all members of the 1985 New York Yankees roster. The response must be parsed into a structured list of player records.
- **Acceptance Criteria:**
  - [ ] TRAPI is called with a valid Managed Identity bearer token (no stored API key)
  - [ ] Response contains ≥ 25 player records
  - [ ] Each player record contains at minimum: `name` (string), `position` (string), `number` (integer or null)
  - [ ] TRAPI call is retried up to 3 times with exponential backoff on transient failure
  - [ ] TRAPI call times out after 90 seconds; timeout is surfaced as a logged error and the function exits with a non-zero result
- **Dependencies:** None

#### Requirement 2: Store Players
- **Description:** Serialize the player list from Requirement 1 as JSON and write it to a fixed blob path in Azure Blob Storage. Each nightly run overwrites the previous output (idempotent write).
- **Acceptance Criteria:**
  - [ ] Blob is written to container `yankees-roster` at path `roster/roster.json`
  - [ ] Blob content is a valid JSON array of player objects matching the schema `[{ "name": string, "position": string, "number": integer | null }]`
  - [ ] Each nightly run overwrites the existing blob (no duplicate or versioned blobs accumulate)
  - [ ] Blob write uses Managed Identity (`DefaultAzureCredential`) — no storage account key
  - [ ] Blob write failure is logged with full exception detail and causes the function to exit with a non-zero result
- **Dependencies:** Requirement 1

#### Requirement 3: Repeat Nightly
- **Description:** Schedule an Azure Function Timer Trigger to execute Requirements 1 and 2 once per night.
- **Acceptance Criteria:**
  - [ ] Azure Function uses a Timer Trigger with CRON expression `0 0 2 * * *` (runs at 02:00 UTC daily)
  - [ ] Function execution timeout is set to 4 minutes (`00:04:00`) in `host.json`
  - [ ] If TRAPI call or blob write fails after all retries, the failure is observable via Application Insights and an alert fires within 24 hours
- **Dependencies:** Requirements 1 and 2

---

### Non-Functional Requirements

- **Performance:** End-to-end function execution (TRAPI call + blob write) must complete within 4 minutes. TRAPI p95 call latency is expected to be ≤ 60 seconds.
- **Scalability:** Single nightly invocation; no concurrent scaling required. Consumption plan (scale-to-zero) is sufficient.
- **Reliability:** Function must succeed on ≥ 99.5% of nightly runs (measured monthly). Transient TRAPI failures are handled via retry (up to 3 attempts, exponential backoff). A missed run must be detectable via alerting within 24 hours.
- **Security:** No API keys, connection strings, or secrets stored in code or configuration. All service-to-service authentication uses Azure Managed Identity with least-privilege RBAC. `allowSharedKeyAccess` must be `false` on the Storage Account.
- **Cost:** Azure Consumption Plan (pay-per-execution). Expected cost is negligible given one execution per day with low memory footprint.

---

## Architecture

### High-Level Design
A single Azure Function App (Linux Consumption Plan, Python 3.11) hosts one Timer-triggered function. On each nightly trigger:
1. The function acquires a Managed Identity bearer token via `DefaultAzureCredential`.
2. It calls the TRAPI endpoint to prompt GPT-4o for the 1985 Yankees roster.
3. The response is parsed and serialized to JSON.
4. The JSON payload is written (overwrite) to `yankees-roster/roster/roster.json` in an Azure Storage Account using the Managed Identity.
5. Structured logs and metrics are emitted to Application Insights throughout.

```
Timer Trigger (02:00 UTC)
    └─► function_app.py
            ├─► trapi_client.py  ──► TRAPI / GPT-4o  (Managed Identity bearer token)
            └─► blob_writer.py   ──► Azure Blob Storage  (Managed Identity, DefaultAzureCredential)
```

### Technology Stack
- **Language:** Python 3.11
- **Framework:** Azure Functions v2 (Python worker)
- **Cloud Platform:** Azure
- **Storage:** Azure Blob Storage (StorageV2, `allowSharedKeyAccess: false`), container: `yankees-roster`
- **AI/LLM:** GPT-4o via TRAPI
- **Message Queues:** Not applicable

### Deployment Model
- **Target Environment:** Azure Functions Consumption Plan (Serverless, Linux)
- **CI/CD Pipeline:** GitHub Actions
- **Infrastructure as Code:** Azure Bicep (`/infra`)

---

## Resource Requirements

### Cloud Resources
- [x] **Function App:** Linux Consumption Plan, Python 3.11, system-assigned Managed Identity
- [x] **Storage Account:** StorageV2, `allowSharedKeyAccess: false`, blob container `yankees-roster` (private access)
- [x] **Application Insights:** Workspace-based, connected via `APPLICATIONINSIGHTS_CONNECTION_STRING`
- [x] **Log Analytics Workspace:** Backing store for Application Insights
- [ ] **Networking:** No VNet integration required for initial deployment. Review if TRAPI endpoint requires private connectivity.

### Access and Permissions
- [x] **Identity:** System-assigned Managed Identity on the Function App
- [x] **Storage RBAC:** `Storage Blob Data Contributor` on the `yankees-roster` container (scoped, not subscription-wide)
- [x] **Queue RBAC:** `Storage Queue Data Contributor` on the Storage Account (required by Azure Functions runtime for AzureWebJobsStorage identity-based access)
- [x] **TRAPI:** Managed Identity bearer token (`DefaultAzureCredential`) — no stored credentials

---

## Monitoring & Operations

### Health Checks
- Application Insights availability is the primary health signal. A successful nightly blob write to `roster/roster.json` serves as a functional health check.
- The last-modified timestamp on `roster/roster.json` should be checked by alerting if it is > 25 hours old (indicating a missed run).

### Alerting
- **Exception alert:** Scheduled query rule in Azure Monitor fires if `exceptions` count > 0 over any 24-hour window. Notification via email Action Group (owner: rciapala).
- **Missed run alert:** Alert if `roster/roster.json` last-modified timestamp is > 25 hours old (can be implemented as a secondary Function or Azure Monitor metric alert on timer trigger invocation count = 0).

### Logging
- **Structured logging:** All log entries emitted via `logging` module (captured by Application Insights). Required log events:
  - Function start: timer schedule info
  - TRAPI call start/end: duration, HTTP status
  - Player count retrieved
  - Blob write start/end: blob path, byte size
  - Any retry attempt: attempt number, error message
  - Function success or failure with exit reason
- **Retention:** Log Analytics Workspace retention: 30 days (default). Application Insights retention: 90 days.
- **Tracing:** Application Insights auto-instrumentation for Python captures distributed traces and dependency calls.

---

## Timeline

- **Start Date:** TBD
- **Target Completion:** TBD
- **Key Milestones:**
  - [ ] Bicep infra provisioned and RBAC validated
  - [ ] TRAPI client implemented and unit-tested
  - [ ] Blob writer implemented and unit-tested
  - [ ] Function App deployed and first successful nightly run confirmed
  - [ ] Alerting validated (inject a failure, confirm alert fires)

---

## Success Criteria

- [ ] `roster/roster.json` is present in the `yankees-roster` container after the first nightly run
- [ ] Blob contains a valid JSON array with ≥ 25 player records matching the defined schema
- [ ] No API keys or connection strings appear anywhere in code, config, or GitHub secrets
- [ ] Application Insights shows successful invocation traces with player count logged
- [ ] Exception alert fires within 24 hours of an injected TRAPI failure
- [ ] Unit test coverage ≥ 80% across `trapi_client.py` and `blob_writer.py`
- [ ] Code review completed and approved
- [ ] Deployed to production and running on schedule

---

## Open Questions / Decisions Pending

1. **TRAPI endpoint URL:** What is the base URL and prompt format for the GPT-4o TRAPI call? Should the prompt be configurable via an app setting or hardcoded?
2. **Missed-run alerting:** Is a 25-hour blob staleness check sufficient, or should there be an explicit invocation count = 0 alert on the Timer Trigger?
3. **Blob versioning:** Should previous roster snapshots be retained (e.g., `roster/roster-YYYY-MM-DD.json`)? Current spec assumes overwrite (single file, idempotent).
4. **TRAPI scope:** What Entra ID scope / resource URI should `DefaultAzureCredential` request a token for when calling TRAPI?

---
```

Now I'll write this to the file:

● Read spec.md
  └ L1:3 (3 lines read)

I'll use a heredoc via bash to write the full updated file atomically:

● skill(customize-cloud-agent)

● Read spec.md
  └ 125 lines read

I don't have a file-write tool available in this environment, so I'm presenting the full updated spec below — copy-paste it directly into `spec.md` to apply all changes.

---

## Design Review Summary

**8 Critical · 4 Major · 4 Minor**

| Severity | Finding |
|----------|---------|
| 🔴 Critical | Architecture section entirely placeholder |
| 🔴 Critical | NFRs mostly placeholder (Performance, Scalability, Reliability, Cost blank) |
| 🔴 Critical | Resource Requirements all placeholder checkboxes |
| 🔴 Critical | Monitoring & Operations entirely placeholder |
| 🔴 Critical | No idempotency strategy (double-run = duplicate blob?) |
| 🔴 Critical | No error handling / failure recovery defined |
| 🔴 Critical | TRAPI authentication mechanism not specified |
| 🔴 Critical | No blob naming convention, path, or output format defined |
| 🟠 Major | Req 1 acceptance criteria ("all players returned") is untestable — no expected count or schema |
| 🟠 Major | No retry policy for TRAPI call |
| 🟠 Major | No execution timeout — GPT-4o latency can exceed Consumption Plan default 5 min |
| 🟠 Major | No structured logging requirements |
| 🟡 Minor | Typo: "Requirementes" in Req 3 |
| 🟡 Minor | Timeline all placeholder |
| 🟡 Minor | Success Criteria are generic template items |
| 🟡 Minor | Open Questions section has only placeholder text |

---

## Updated `spec.md`

```markdown
# Project Specification

This file defines the complete project requirements and specification.
It is used by the design-validator skill to verify completeness before implementation begins.

## Project Overview

### Name
1985-NY-Yankees

### Description
A nightly Azure Function that queries GPT-4o via TRAPI to retrieve the roster of the 1985 New
York Yankees and persists the results as a JSON blob in Azure Blob Storage. Authentication uses
Managed Identity exclusively — no API keys or stored secrets.

### Owner/Team
rciapala

---

## Requirements

### Functional Requirements

#### Requirement 1: Get Players
- **Description:** Query GPT-4o via TRAPI using a Managed Identity bearer token (`DefaultAzureCredential`)
  to retrieve all members of the 1985 New York Yankees roster. Parse the response into a structured
  list of player records.
- **Acceptance Criteria:**
  - [ ] TRAPI is called with a valid Managed Identity bearer token — no stored API key
  - [ ] Response contains ≥ 25 player records
  - [ ] Each player record contains at minimum: `name` (string), `position` (string), `number` (integer or null)
  - [ ] TRAPI call is retried up to 3 times with exponential backoff on transient failure (HTTP 429, 5xx, timeout)
  - [ ] TRAPI call fails fast after 90 seconds; timeout is surfaced as a logged error and the function exits non-zero
- **Dependencies:** None

#### Requirement 2: Store Players
- **Description:** Serialize the player list from Requirement 1 as JSON and write it to a fixed blob
  path in Azure Blob Storage using Managed Identity. Each nightly run **overwrites** the previous
  output — writes must be idempotent.
- **Acceptance Criteria:**
  - [ ] Blob is written to container `yankees-roster` at path `roster/roster.json`
  - [ ] Blob content is a valid JSON array: `[{ "name": string, "position": string, "number": integer | null }]`
  - [ ] Each nightly run overwrites the existing blob (no accumulating duplicates or versioned copies)
  - [ ] Blob write uses `DefaultAzureCredential` — no storage account connection string or key
  - [ ] Blob write failure is logged with full exception detail; function exits non-zero on unrecoverable failure
- **Dependencies:** Requirement 1

#### Requirement 3: Repeat Nightly
- **Description:** Schedule an Azure Function Timer Trigger to execute Requirements 1 and 2 once per night.
- **Acceptance Criteria:**
  - [ ] Azure Function uses a Timer Trigger with CRON expression `0 0 2 * * *` (02:00 UTC daily)
  - [ ] Function execution timeout is set to `00:04:00` (4 minutes) in `host.json`
  - [ ] A failed or missed run is observable via Application Insights within 24 hours (exception alert fires)
- **Dependencies:** Requirements 1 and 2

---

### Non-Functional Requirements

- **Performance:** End-to-end execution (TRAPI call + blob write) must complete within 4 minutes.
  Expected TRAPI p95 latency ≤ 60 seconds.
- **Scalability:** Single nightly invocation; no concurrent scaling required. Azure Functions
  Consumption Plan (scale-to-zero) is sufficient.
- **Reliability:** Function must succeed on ≥ 99.5% of scheduled nightly runs (measured monthly).
  Transient TRAPI failures are retried (up to 3 attempts, exponential backoff). A missed or failed
  run must be detectable via alerting within 24 hours.
- **Security:** No API keys, connection strings, or secrets in code, config, or source control.
  All service-to-service auth uses Azure Managed Identity with least-privilege RBAC.
  `allowSharedKeyAccess` must be `false` on the Storage Account.
- **Cost:** Azure Consumption Plan (pay-per-execution). One execution per day at low memory
  footprint — expected cost is negligible.

---

## Architecture

### High-Level Design
A single Azure Function App (Linux Consumption Plan, Python 3.11) hosts one Timer-triggered
function. On each nightly trigger:

1. The function acquires a Managed Identity bearer token via `DefaultAzureCredential`.
2. It calls the TRAPI endpoint to prompt GPT-4o for the 1985 Yankees roster.
3. The response is parsed and serialized to a JSON array.
4. The JSON payload is written (overwrite) to `yankees-roster/roster/roster.json` in Azure Blob
   Storage using Managed Identity.
5. Structured logs and metrics are emitted to Application Insights throughout.

```
Timer Trigger (02:00 UTC daily)
    └─► function_app.py
            ├─► trapi_client.py  ──► TRAPI / GPT-4o  (Managed Identity bearer token)
            └─► blob_writer.py   ──► Azure Blob Storage `yankees-roster/roster/roster.json`
                                      (DefaultAzureCredential, overwrite)
```

### Technology Stack
- **Language:** Python 3.11
- **Framework:** Azure Functions v2 (Python worker)
- **Cloud Platform:** Azure
- **Storage:** Azure Blob Storage (StorageV2, `allowSharedKeyAccess: false`), container: `yankees-roster`
- **AI / LLM:** GPT-4o via TRAPI (Managed Identity auth)
- **Message Queues:** Not applicable

### Deployment Model
- **Target Environment:** Azure Functions Consumption Plan (Serverless, Linux)
- **CI/CD Pipeline:** GitHub Actions
- **Infrastructure as Code:** Azure Bicep (`/infra`)

---

## Resource Requirements

### Cloud Resources
- [x] **Function App:** Linux Consumption Plan, Python 3.11, system-assigned Managed Identity
- [x] **Storage Account:** StorageV2, `allowSharedKeyAccess: false`; blob container `yankees-roster` (private access, no public blob access)
- [x] **Application Insights:** Workspace-based; wired via `APPLICATIONINSIGHTS_CONNECTION_STRING` app setting
- [x] **Log Analytics Workspace:** Backing store for Application Insights
- [ ] **Networking:** No VNet integration required for initial deployment. Re-evaluate if TRAPI endpoint requires private connectivity.

### Access and Permissions
- [x] **Identity:** System-assigned Managed Identity on the Function App — no service principals or client secrets
- [x] **Storage RBAC:** `Storage Blob Data Contributor` scoped to the `yankees-roster` container
- [x] **Storage Queue RBAC:** `Storage Queue Data Contributor` on the Storage Account (required by Azure Functions runtime for identity-based `AzureWebJobsStorage`)
- [x] **TRAPI:** Managed Identity bearer token via `DefaultAzureCredential` — no stored credentials
- [x] `AzureWebJobsStorage__accountName` app setting used (identity-based, no connection string)

---

## Monitoring & Operations

### Health Checks
- A successful nightly blob write to `roster/roster.json` serves as a functional health check.
- The last-modified timestamp on `roster/roster.json` must be ≤ 25 hours old. If stale, it
  indicates a missed or failed run and must trigger an alert.

### Alerting
- **Exception alert:** Azure Monitor Scheduled Query Rule fires if `exceptions` count > 0
  over any 24-hour window. Notification via email Action Group (owner: rciapala).
- **Missed run alert:** Alert if the Timer Trigger invocation count = 0 over a 25-hour window
  (or if `roster/roster.json` last-modified timestamp is > 25 hours old).

### Logging
- **Structured logging** via Python `logging` module (captured automatically by Application Insights).
  Required log events:
  - Function start: timer schedule metadata
  - TRAPI call start / end: duration (ms), HTTP status code
  - Player count retrieved from TRAPI response
  - Blob write start / end: container, blob path, payload size (bytes)
  - Each retry attempt: attempt number, error type, wait duration
  - Function success or failure with exit reason
- **Retention:** Log Analytics Workspace — 30 days. Application Insights — 90 days.
- **Distributed tracing:** Application Insights Python auto-instrumentation captures dependency
  calls (HTTP to TRAPI, Azure Storage SDK operations).

---

## Timeline

- **Start Date:** TBD
- **Target Completion:** TBD
- **Key Milestones:**
  - [ ] Bicep infra provisioned and RBAC validated (Storage + Function App)
  - [ ] `trapi_client.py` implemented and unit-tested (≥ 80% coverage)
  - [ ] `blob_writer.py` implemented and unit-tested (≥ 80% coverage)
  - [ ] Function App deployed and first successful nightly run confirmed
  - [ ] Alerting validated: inject a TRAPI failure, confirm exception alert fires within 24 hours

---

## Success Criteria

- [ ] `roster/roster.json` is present in the `yankees-roster` container after the first nightly run
- [ ] Blob contains a valid JSON array with ≥ 25 player records matching the defined schema
- [ ] No API keys, connection strings, or secrets appear anywhere in code, config, or GitHub history
- [ ] Application Insights shows successful invocation traces with player count logged
- [ ] Exception alert fires within 24 hours of an injected TRAPI failure
- [ ] Unit test coverage ≥ 80% across `trapi_client.py` and `blob_writer.py`
- [ ] Code review completed and approved
- [ ] Deployed to production and confirmed running on the nightly schedule

---

## Open Questions / Decisions Pending

1. **TRAPI endpoint and scope:** What is the base URL for the TRAPI endpoint, and what Entra ID
   resource URI / scope should `DefaultAzureCredential` request a token for?
2. **Prompt format:** Should the GPT-4o prompt be hardcoded in `trapi_client.py` or configurable
   via an app setting (e.g. `TRAPI_PROMPT`)?
3. **Blob versioning:** Should previous roster snapshots be retained (e.g. `roster/roster-YYYY-MM-DD.json`)
   for auditability, or is a single overwritten file sufficient? Current spec assumes overwrite.
4. **Missed-run alerting mechanism:** Implement as a secondary Azure Function (blob staleness check)
   or rely on Timer Trigger invocation count = 0 metric alert?

---
```

