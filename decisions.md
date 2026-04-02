# Team Decision Log — 1985-NY-Yankees Project

> **Status:** Approved (PRJ-01)  
> **Reviewed by:** @copilot (senior engineer review), @richcia (product owner / rciapala)  
> **Date:** 2026-04-02  

This document records all decisions and open-question resolutions required before implementation begins, as required by task PRJ-01.

---

## Task Plan Review Summary

The implementation task plan (`results/task-plan.json`) has been reviewed against `spec.md`. The plan covers four delivery waves:

| Wave | Name | Key Tasks |
|------|------|-----------|
| 1 | Foundation | PRJ-01, INF-01, INF-02, INF-03, REL-01 |
| 2 | Core Build | APP-01, APP-02, APP-03, SEC-01 |
| 3 | Hardening | APP-04, OPS-01, OPS-02, SEC-02 |
| 4 | Release Readiness | QA-01, QA-02, REL-02, DOC-01 |

The plan is **approved** subject to the deferred items below being resolved before the affected tasks begin.

---

## Resolved Decisions

### D-01 — Implementation Language / Runtime
- **Decision:** Python (v3.11)
- **Rationale:** Idiomatic choice for AI/data workloads; strong Azure Functions SDK and Azure SDK for Python support; broad team familiarity.
- **Impact:** INF-01 (Function App runtime), APP-01–APP-04, SEC-01.
- **Owner:** @richcia

### D-02 — Blob Output Format
- **Decision:** JSON array (`.json`)
- **Rationale:** Machine-readable, schema-extensible, directly serializable from a Python list. Easier to consume by downstream tools than CSV or plain text.
- **Example output:** `[{"name": "Don Mattingly", "position": "1B"}, ...]`
- **Impact:** INF-02, APP-02, APP-03, QA-01.
- **Owner:** @richcia

### D-03 — Blob Container Name and Output Naming Convention
- **Decision:**
  - Container: `yankees-roster`
  - Blob path: `1985-yankees/YYYY-MM-DD.json` (e.g., `1985-yankees/2026-04-02.json`)
- **Rationale:** Human-readable, idempotent (date-keyed), supports historical run retention.
- **Impact:** INF-02, APP-02, APP-03.
- **Owner:** @richcia

### D-04 — Nightly Cron Schedule
- **Decision:** `0 2 * * *` (2:00 AM UTC daily)
- **Rationale:** Low-traffic time window; avoids peak Azure region load; aligns with common batch job conventions.
- **Impact:** INF-01, APP-01, REL-01.
- **Owner:** @richcia

### D-05 — Azure Hosting Plan
- **Decision:** Consumption plan
- **Rationale:** Nightly single-execution workload has negligible throughput requirements; Consumption plan is cost-optimal and operationally simple.
- **Impact:** INF-01.
- **Owner:** @richcia

### D-06 — Application Insights
- **Decision:** Provision a new Application Insights instance as part of INF-01 Bicep templates.
- **Rationale:** No existing instance confirmed; bundling with INF-01 keeps infrastructure self-contained and auditable.
- **Impact:** INF-01, OPS-01, OPS-02.
- **Owner:** @richcia

### D-07 — Retry and Idempotency
- **Decision:** Implement up to 3 retries with exponential back-off on TRAPI/GPT-4o call failures. Blob writes use date-keyed paths (D-03), making nightly runs naturally idempotent (overwrite on re-run).
- **Rationale:** TRAPI is an external dependency; transient failures should be handled gracefully without requiring manual re-triggers.
- **Impact:** APP-01, APP-04.
- **Owner:** @richcia

### D-08 — Authentication Method
- **Decision:** System-assigned Managed Identity on the Function App for both TRAPI token acquisition and Azure Storage access. No API keys or connection strings in code or configuration.
- **Rationale:** Spec explicitly requires "No API Keys". Managed Identity eliminates secret rotation and reduces attack surface.
- **Impact:** INF-03, SEC-01, SEC-02, APP-01.
- **Owner:** @richcia

### D-09 — Infrastructure as Code Tooling
- **Decision:** Bicep (with GitHub Actions for CI/CD)
- **Rationale:** Native Azure IaC with first-class Azure CLI support; consistent with common Azure-native teams. GitHub Actions already assumed in the task plan.
- **Impact:** INF-01, INF-02, INF-03, REL-01.
- **Owner:** @richcia

---

## Deferred Items (Blocked on External Input)

The following open questions are **deferred** pending input from the product owner or platform team. The tasks that depend on each item are noted. No implementation work on those tasks should begin until the item is resolved.

| ID | Question | Blocking Tasks | Owner | Due |
|----|----------|---------------|-------|-----|
| DEF-01 | Exact TRAPI endpoint URL and required OAuth scopes/audience for GPT-4o access | INF-03, APP-01 | rciapala | Before Wave 2 starts |
| DEF-02 | Target Azure subscription ID and resource group name for deployment | INF-01, INF-02, INF-03, REL-01 | rciapala | Before Wave 1 exits |
| DEF-03 | Target Azure region for all resources | INF-01 | rciapala | Before Wave 1 exits |
| DEF-04 | Alert notification channel (email, Teams, PagerDuty, etc.) | OPS-02 | rciapala | Before Wave 3 exits |

> **Action required:** @richcia (rciapala) to resolve DEF-01, DEF-02, and DEF-03 before the Foundation wave exit criteria can be met and the Core Build wave begins.

---

## Assumptions Confirmed

The following assumptions from `task-plan.json` are hereby confirmed:

- Azure is the target cloud platform. ✅
- A single Azure Storage Account serves both the Function App host requirements and blob output. ✅
- No VNet integration is required (spec is silent on network isolation). ✅
- A Consumption hosting plan is acceptable for the nightly, low-frequency trigger. ✅ (see D-05)
- The blob container name and path convention are now decided. ✅ (see D-03)

---

## Approval

| Role | Name | Decision |
|------|------|----------|
| Product Owner | @richcia (rciapala) | **Approved** — per issue comment 2026-04-02 |
| Senior Engineer (Copilot) | @copilot | **Approved** — reviewed task plan, spec, and wave structure |

> The task plan is formally approved. Implementation may begin on the Foundation wave (INF-01, INF-02, REL-01) immediately. INF-03 and APP-01 are gated on DEF-01 resolution.
