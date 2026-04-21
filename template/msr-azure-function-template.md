# Azure Function Design Template

> **Instructions:** Fill in every field. Fields marked `[DEFAULT: ...]` may be kept as-is if the default is appropriate.
> Fields marked `[REQUIRED]` have no safe default and must be specified before implementation begins.
> Group each function in its own section if the app hosts multiple functions.

---

## 1. Project Overview

| Field | Value |
|---|---|
| **Function App Name** | [REQUIRED] |
| **Function Name(s)** | [REQUIRED] |
| **Owner / Team** | [REQUIRED] |
| **Description** | [REQUIRED] One sentence: what business problem does this solve? |
| **Target Environment(s)** | [DEFAULT: `dev`, `stage`, `prod`] |
| **Language / Runtime** | [DEFAULT: Python 3.11] |
| **Azure Functions SDK Version** | [DEFAULT: v2 programming model (`azure-functions >= 1.17`)] |

---

## 2. Trigger & Bindings

> Priority: **Critical** — wrong trigger choice invalidates the entire design.

### 2.1 Trigger

| Field | Value |
|---|---|
| **Trigger Type** | [REQUIRED] `TimerTrigger` \| `HttpTrigger` \| `QueueTrigger` \| `ServiceBusTrigger` \| `BlobTrigger` \| `EventHubTrigger` \| `CosmosDBTrigger` |
| **Trigger Configuration** | [REQUIRED] Schedule string (CRON), route, queue/topic name, blob path, etc. |
| **Timezone** | [DEFAULT: UTC — always set explicitly; never rely on host default] |
| **`useMonitor`** (Timer only) | [DEFAULT: `true` — surfaces missed executions in Application Insights] |
| **Auth Level** (HTTP only) | [DEFAULT: `function` — never `anonymous` in production] |
| **Cardinality** (batch triggers) | [DEFAULT: single-message (`cardinality: one`)] |
| **Prefetch Count** (Service Bus) | [DEFAULT: 1 — increase only after load testing] |

### 2.2 Input Bindings

| Binding Type | Resource Name | Connection Setting Name | Notes |
|---|---|---|---|
| [e.g., BlobInput] | [REQUIRED] | [REQUIRED — App Setting key, not literal value] | |

### 2.3 Output Bindings

| Binding Type | Resource Name | Connection Setting Name | Notes |
|---|---|---|---|
| [e.g., BlobOutput] | [REQUIRED] | [REQUIRED — App Setting key, not literal value] | |

---

## 3. Functional Requirements

> Priority: **Critical** — each requirement maps directly to an acceptance criterion.

### Requirement Template (repeat for each requirement)

#### Requirement N: [Short Name]

- **Description:** [REQUIRED]
- **Input:** [REQUIRED] Data source, schema, format
- **Output:** [REQUIRED] Destination, schema, format
- **Expected Response Schema:**
  ```json
  {}
  ```
- **Acceptance Criteria:**
  - [ ] [REQUIRED] Measurable, testable criterion
- **Dependencies:** [REQUIRED] External services, other requirements

---

## 4. Reliability

> Priority: **Critical** — unspecified retry and failure behavior leads to data loss or duplicates.

| Field | Value |
|---|---|
| **Idempotency Strategy** | [REQUIRED] Conditional write (`If-None-Match`), deduplication ID, upsert, etc. |
| **Retry Policy — Max Attempts** | [DEFAULT: 3] |
| **Retry Policy — Strategy** | [DEFAULT: Exponential backoff, initial interval 2 s, max interval 30 s] |
| **Retry Policy — Scope** | [DEFAULT: Per outbound HTTP/SDK call; NOT host-level retry for Timer triggers] |
| **Poison Message Handling** (queue/bus) | [DEFAULT: Dead-letter after max delivery count = 3; alert on DLQ depth > 0] |
| **Partial Failure Behavior** | [REQUIRED] Roll back? Write to `failed/` prefix? Raise alert and halt? |
| **`functionTimeout`** | [DEFAULT: `00:05:00` (5 min) on Consumption; max `00:10:00`] |
| **`maxDequeueCount`** (queue only) | [DEFAULT: 3 — after which message is dead-lettered] |

---

## 5. Scalability & Performance

> Priority: **High** — affects cost and SLA.

| Field | Value |
|---|---|
| **Hosting Plan** | [DEFAULT: Consumption (serverless)] |
| **`maxConcurrentCalls`** | [DEFAULT: 1 for Timer/sequential; tune for queue-based] |
| **`maxConcurrentActivities`** (Durable) | [DEFAULT: not applicable] |
| **Expected Execution Duration (p95)** | [REQUIRED] e.g., < 30 s |
| **Alert Threshold — Duration** | [DEFAULT: 2× expected p95 duration] |
| **Cold-Start Sensitivity** | [DEFAULT: low (Timer/background); document if latency-sensitive HTTP] |
| **Scale-Out Limit** | [DEFAULT: Consumption default (200 instances); set `functionAppScaleLimit` if lower needed] |
| **Throughput Target (msg/s or req/s)** | [DEFAULT: N/A for single-instance Timer] |

---

## 6. Security

> Priority: **Critical** — must be resolved before any deployment.

| Field | Value |
|---|---|
| **Identity Type** | [DEFAULT: System-assigned Managed Identity] |
| **No Hardcoded Secrets** | [DEFAULT: required — all secrets via Key Vault references or Managed Identity] |
| **Key Vault Name** | [REQUIRED if any secrets cannot use Managed Identity] |
| **Secret References in App Settings** | [DEFAULT: `@Microsoft.KeyVault(SecretUri=...)` syntax] |
| **Storage — Anonymous Access** | [DEFAULT: disabled on all containers and blobs] |
| **HTTP Trigger Auth Level** | [DEFAULT: `function`; document if `anonymous` is intentional] |
| **Network Restriction** | [DEFAULT: public endpoint; document if VNet integration is required] |
| **RBAC Assignments** | [REQUIRED] List each: identity → role → scope (resource/container level, not subscription) |
| **Least-Privilege Check** | [DEFAULT: scope RBAC to the tightest resource boundary (container, not account)] |
| **Credential Rotation Plan** | [DEFAULT: Managed Identity — not required; document rotation cadence for any static keys] |

### RBAC Assignment Table

| Identity | Role | Scope (Resource ID / Container) |
|---|---|---|
| [Function App MI] | `Storage Blob Data Contributor` | [REQUIRED — container-level preferred] |
| [Function App MI] | `Key Vault Secrets User` | [REQUIRED if Key Vault used] |

---

## 7. Data Consistency

> Priority: **High** — specifies what "correct" means for writes.

| Field | Value |
|---|---|
| **Write Semantics** | [DEFAULT: at-least-once; document if exactly-once is required] |
| **Duplicate-Write Protection** | [DEFAULT: Conditional PUT `If-None-Match: *` for blob; dedup ID for Service Bus] |
| **Transaction Boundary** | [DEFAULT: single blob/message write is atomic; document multi-resource transactions] |
| **Data Retention** | [DEFAULT: 30-day blob soft-delete; align with compliance requirements] |
| **Blob Soft-Delete Retention** | [DEFAULT: 7 days] |
| **Blob Naming Convention** | [REQUIRED] e.g., `{container}/{yyyy-MM-dd}.json` |
| **Schema Validation** | [DEFAULT: validate before write; reject and dead-letter on schema mismatch] |
| **Failed-Write Destination** | [DEFAULT: `{container}/failed/{run_date_utc}.json`] |

---

## 8. Observability

> Priority: **High** — unobservable functions are unoperatable in production.

| Field | Value |
|---|---|
| **Application Insights Resource** | [DEFAULT: dedicated workspace-based App Insights per app] |
| **Log Retention** | [DEFAULT: 30 days] |
| **Sampling** | [DEFAULT: adaptive sampling enabled to control ingestion cost] |
| **Structured Logging** | [DEFAULT: OpenTelemetry SDK; all log entries include `run_id`, `function_name`, `environment`] |
| **Correlation / Trace ID** | [DEFAULT: propagate `invocation_id` on all outbound calls] |
| **Custom Metrics** | [REQUIRED] List domain-specific metrics to emit (e.g., `records_written`, `validation_failures`) |
| **Alert — Execution Failure** | [DEFAULT: fire when failure count > 0 in 1-hour window; notify owner via email] |
| **Alert — Duration** | [DEFAULT: fire when execution duration > 2× expected p95] |
| **Alert — DLQ Depth** (queue only) | [DEFAULT: fire when DLQ depth > 0] |
| **Dashboard** | [DEFAULT: Azure Monitor workbook with execution count, duration, failure rate, custom metrics] |

### Custom Metrics Table

| Metric Name | Type | Description | Alert Threshold |
|---|---|---|---|
| [REQUIRED] | Counter \| Gauge | [REQUIRED] | [REQUIRED] |

---

## 9. Configuration

> Priority: **High** — misconfiguration is the most common cause of environment-specific failures.

| Field | Value |
|---|---|
| **App Settings (non-secret)** | [REQUIRED] List all; include description and default value |
| **App Settings (secret)** | [REQUIRED] List all; must be Key Vault references — never literal values |
| **Slot-Safe Settings** | [DEFAULT: mark settings that must NOT swap as `slotSetting: true` in Bicep] |
| **`host.json` — `functionTimeout`** | [DEFAULT: `00:05:00`] |
| **`host.json` — `maxConcurrentCalls`** | [DEFAULT: 1 for Timer; 16 for queue] |
| **`host.json` — logging level** | [DEFAULT: `Information` in prod; `Debug` allowed in dev only] |
| **Environment Differentiation** | [DEFAULT: separate resource groups per environment (`rg-{app}-{env}`)] |

### App Settings Table

| Setting Name | Secret? | Default Value | Description |
|---|---|---|---|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Yes (KV ref) | — | App Insights ingestion key |
| `AzureWebJobsStorage` | Yes (KV ref) | — | Host storage account connection |
| [REQUIRED custom settings] | | | |

---

## 10. External Dependencies

> Priority: **High** — unspecified timeouts and fallbacks become production incidents.

| Dependency | Type | Endpoint / Resource | Timeout | Retry | Circuit Breaker | Fallback |
|---|---|---|---|---|---|---|
| [REQUIRED] | HTTP \| SDK \| DB | [REQUIRED] | [DEFAULT: 30 s] | [DEFAULT: 3× exp backoff] | [DEFAULT: none — document if needed] | [DEFAULT: dead-letter / write to `failed/`] |

---

## 11. Deployment & Operations

> Priority: **High** — incomplete deployment design blocks go-live.

### 11.1 Infrastructure as Code

| Field | Value |
|---|---|
| **IaC Technology** | [DEFAULT: Bicep] |
| **Resources Provisioned by IaC** | [DEFAULT: Function App, dedicated Storage Account, App Insights, Key Vault, all RBAC assignments] |
| **State Management** | [DEFAULT: Azure Resource Manager (no Terraform state file needed)] |

### 11.2 CI/CD Pipelines

| Pipeline | Trigger | Default Behavior |
|---|---|---|
| **CI** | Push to `main` | Run all unit tests; disabled by default |
| **CD App** | Manual | Deploy to environment specified as parameter; run smoke test |
| **CD Promote** | Manual | Swap slots: source=`stage` → target=`prod` |
| **CD Infra** | Manual | Provision all Azure resources for specified environment; run validation test |

| Field | Value |
|---|---|
| **Auth for CD workflows** | [DEFAULT: Managed Identity with federated credential (OIDC) — no stored secrets] |
| **Smoke Test Definition** | [REQUIRED] What constitutes a passing smoke test post-deploy? |
| **Rollback Strategy** | [DEFAULT: re-run CD Promote in reverse (swap back); document if manual steps needed] |
| **Deployment Slots** | [DEFAULT: `stage` + `prod` slots on the same Function App for zero-downtime swap] |

### 11.3 Versioning

| Field | Value |
|---|---|
| **Breaking-Change Strategy** | [DEFAULT: new function name for incompatible changes; blue/green via slots for non-breaking] |
| **Pinned Model / API Versions** | [REQUIRED] Pin all external AI model versions and API versions to prevent drift |

### 11.4 Runbook

| Scenario | Response |
|---|---|
| Function execution failure | Check App Insights failures blade → review logs for root cause → re-trigger manually if safe |
| Dead-letter queue non-empty | Inspect DLQ message → fix data or code → replay or discard |
| Missed timer execution | Verify `useMonitor: true` → check host logs → trigger manually if data is stale |
| Deployment failure | Re-run CD App pipeline → if still failing, run CD Promote to roll back |

---

## 12. Non-Functional Requirements Summary

| Category | Requirement | Default |
|---|---|---|
| Performance | Max execution duration | 60 s (set `functionTimeout` to 2× as buffer) |
| Scalability | Max concurrent instances | 1 (Timer); plan-default for queue-based |
| Reliability | Availability SLA | ~99.95% (Consumption Plan) |
| Security | Secret storage | Key Vault references only — no plaintext in App Settings or source |
| Cost | Estimated monthly cost | [REQUIRED] Provide estimate; enable App Insights sampling |
| Compliance | Data classification | [REQUIRED] Public / Internal / Confidential / Restricted |

---

## 13. Acceptance Criteria Checklist

> All items must be checked before production deployment sign-off.

### Functional
- [ ] All functional requirements implemented and verified in staging
- [ ] Schema validation in place for all inbound and outbound data
- [ ] Failed writes routed to `failed/` prefix with alert

### Reliability
- [ ] Idempotency verified: re-triggering same execution produces no duplicates
- [ ] Retry logic tested against simulated transient failures
- [ ] Poison message handling verified end-to-end (queue triggers only)

### Security
- [ ] No secrets in source code, `local.settings.json` committed, or workflow YAML
- [ ] All RBAC assignments scoped to minimum required resource
- [ ] Blob containers have anonymous access disabled

### Observability
- [ ] Structured logs emitted with `run_id` and `environment` on every execution
- [ ] All alert rules deployed and tested in staging
- [ ] Custom metrics visible in App Insights

### Deployment
- [ ] IaC provisions all resources idempotently
- [ ] Smoke test passes in staging before production promotion
- [ ] Rollback procedure documented and tested

---

*Template version: 1.0 — maintained in `knowledge/msr-azure-function-template.md`*
