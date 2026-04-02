# Project Specification

This file defines the complete project requirements and specification. 
It is used by the design-validator skill to verify completeness before implementation begins.

## Project Overview

### Name
1985-NY-Yankees

### Description
List the members of the 1985 New York Yankees

### Owner/Team
rciapala

---

## Requirements

### Functional Requirements

#### Requirement 1: Get Players
- **Description:** Get members of 1985 Yankees from GPT-4o using TRAPI
- **Acceptance Criteria:**
  - [ ] All players are returned
- **Dependencies:** 

#### Requirement 2: Store Players
- **Description:** Store members of 1985 Yankees to an Azure Storage Blob
- **Acceptance Criteria:**
  - [ ] All players are stored to an Azure Storage Blob
- **Dependencies:** 

#### Requirement 3: Repeat nightly
- **Description:** Repeat Requirements 1 and 2 nightly
- **Acceptance Criteria:**
  - [ ] Azure Function is configured to execute nightly
- **Dependencies:** 
  - Requirementes 1 and 2
 

### Non-Functional Requirements

- **Performance:** Single nightly execution; no latency SLA required beyond completing within the Azure Functions timeout (10 min default Consumption).
- **Scalability:** Nightly low-frequency trigger; no horizontal scaling required.
- **Reliability:** Up to 3 retries with exponential back-off on TRAPI/GPT-4o failures. Blob writes are idempotent (date-keyed path).
- **Security:** No API Keys. Authentication via System-assigned Managed Identity only.
- **Cost:** Consumption plan (pay-per-execution); single execution per day minimises cost.

---

## Architecture

### High-Level Design
A timer-triggered Azure Function (Python) executes nightly at 2:00 AM UTC. It acquires an OAuth token via the Function App's system-assigned Managed Identity to call the TRAPI GPT-4o endpoint and retrieves the 1985 New York Yankees roster. The response is serialised as a JSON array and written to an Azure Blob Storage container, keyed by date (`1985-yankees/YYYY-MM-DD.json`). Telemetry is emitted to Application Insights.

### Technology Stack
- **Language(s):** Python 3.11
- **Framework(s):** Azure Functions v2 (Python programming model)
- **Cloud Platform:** Azure
- **Databases:** Azure Blob Storage (container: `yankees-roster`)
- **Message Queues:** N/A

### Deployment Model
- **Target Environment:** Azure Functions — Consumption plan (Serverless)
- **CI/CD Pipeline:** GitHub Actions
- **Infrastructure as Code:** Bicep

---

## Resource Requirements

### Cloud Resources
- [x] Compute: Azure Function App (Consumption plan, Python 3.11)
- [x] Storage: Azure Storage Account (blob output container `yankees-roster` + function host state)
- [x] Observability: Application Insights instance (new, provisioned via Bicep)
- [ ] Networking: No VNet integration required (public endpoints, HTTPS-only)

### Access and Permissions
- [x] Identity/authentication method: System-assigned Managed Identity on Function App
- [x] Service principals/managed identities: System-assigned MI (no user-assigned or service principals)
- [x] Required RBAC roles: `Storage Blob Data Contributor` on Storage Account; TRAPI audience scope TBD (DEF-01)

---

## Monitoring & Operations

### Health Checks
- Azure Functions built-in health endpoint (`/api/health` or portal monitoring). Timer trigger execution status visible in Application Insights.

### Alerting
- Alert rule on `exceptions` table in Application Insights: fire when nightly execution fails (any unhandled exception or final retry exhausted). Notification channel: TBD — see DEF-04.

### Logging
- Structured logging via Python `logging` module integrated with Application Insights SDK. Logs retained per Application Insights workspace default (90 days). Log fields: `run_date`, `player_count`, `duration_ms`, `status`.

---

## Timeline

- **Start Date:** [YYYY-MM-DD]
- **Target Completion:** [YYYY-MM-DD]
- **Key Milestones:** [List of milestones]

---

## Success Criteria

- [ ] All functional requirements implemented
- [ ] All acceptance criteria met
- [ ] Code review completed and approved
- [ ] Test coverage at or above threshold
- [ ] Deployed to production
- [ ] Monitoring and alerting active
- [ ] Documentation complete

---

## Open Questions / Decisions Pending

> All decisions resolved as of 2026-04-02. See `decisions.md` for the full decision log.
> The following items remain **deferred** and are gated before specific implementation tasks begin:

1. **DEF-01** — Exact TRAPI endpoint URL and required OAuth scopes/audience for GPT-4o access. **Owner:** rciapala. **Blocks:** INF-03, APP-01.
2. **DEF-02** — Target Azure subscription ID and resource group name. **Owner:** rciapala. **Blocks:** INF-01, INF-02, INF-03, REL-01.
3. **DEF-03** — Target Azure region for all resources. **Owner:** rciapala. **Blocks:** INF-01.
4. **DEF-04** — Alert notification channel (email, Teams, PagerDuty, etc.). **Owner:** rciapala. **Blocks:** OPS-02.

---
