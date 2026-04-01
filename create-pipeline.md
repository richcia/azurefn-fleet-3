# Copilot Pipeline Authoring Prompt

## 1) Objective
Create a reusable engineering pipeline in this repository that implements the lifecycle:

Trigger -> Design -> Plan -> Assign -> Implement -> Review -> Deploy -> Monitor -> Service

The pipeline must:
- Use `spec.md` as the implementation input.
- Use `project-type.md` to determine project-specific design requirements.
- Treat GitHub Copilot as orchestrator.
- Write all generated source code under `src/`.
- Persist orchestration audit trail to `results/copilot-progress.md`.
- Persist task-specific audit trail in each related GitHub Issue.
- Enforce all requirements in `MSR Design Standards`.
- Perform real GitHub Issue automation (GitHub Actions/API), not documentation-only logs.

## 2) Invocation Prompts (Discrete)
The orchestration must trigger when user intent matches any of:
- "engineer this spec"
- "run the pipeline"
- "implement spec.md"

Intent matching must be case-insensitive and tolerant of punctuation differences.

## 3) Required Files To Create/Update
Create or update the following:
- `copilot-instructions.md` (main orchestrator contract)
- `.github/skills/<skill-name>/` (one folder per skill)
- `.github/workflows/*.yml` (automation workflows)
- `results/copilot-progress.md` (run-by-run orchestration audit)

Do not modify `spec.md` directly. Missing design data must be requested through `DESIGN:` issues.

## 4) Lifecycle State Machine Contract

### Trigger
Inputs:
- User prompt matching invocation patterns.

Actions:
- Initialize run context (timestamp, branch, SHA, actor, run URL).
- Create a new GitHub Project named:
  - `<ProjectTypeName>_<YYYYMMDD-HHMMSS>`
- Start `results/copilot-progress.md` entry for this run.

Exit Criteria:
- Run context created.
- Project created and ready for issue association.

### Design
Inputs:
- `spec.md`
- `project-type.md`
- `MSR Design Standards`

Actions:
- Validate `spec.md` completeness against required design fields for detected project type.
- Create or update one idempotent issue with title prefix `DESIGN:`.
- Include in `DESIGN:` issue:
  - validation status
  - checklist of missing/partial details
  - explicit suggested defaults
  - instructions for user to update `spec.md`
  - instruction to check all resolved items and close issue

Rules:
- Never create `IMPLEMENT:` issues in this stage.
- Never edit `spec.md`.

Exit Criteria:
- `DESIGN:` issue exists.
- If complete and closed with all checklist items resolved, proceed to Plan.
- If incomplete, stop and wait for user closure.

### Plan
Precondition:
- `DESIGN:` issue is closed.

Runtime Gate Revalidation (mandatory before issue creation):
- Closed `DESIGN:` issue contains no unchecked checklist items.
- Current `spec.md` includes all required design details.

Failure Behavior:
- Reopen `DESIGN:` issue.
- Comment with missing items.
- Stop Plan stage.

Actions on Success:
- Create/update discrete `IMPLEMENT:` issues with:
  - clear scope
  - verifiable inputs/outputs
  - file ownership boundaries
  - machine-readable dependencies
- Dependency metadata format (required):
  - `Depends on: #123, #124` or `Depends on: none`
- Ensure issues can run in parallel where possible without same-file conflicts.
- Ensure these issue types exist (create if missing):
  - CI/CD provisioning script task
  - dependent cloud services provisioning script task
  - deployed service health check script task
- Record created/updated issue numbers in workflow summary.

Exit Criteria:
- All required `IMPLEMENT:` issues exist and are associated to project.
- Dependency graph is complete and machine-readable.

### Assign
Inputs:
- Open `IMPLEMENT:` issues and dependency graph.

Actions:
- Assign issues to coding agents/skills.
- Compute execution waves from dependency graph.
- Allow parallel execution only for dependency-ready issues with no file ownership conflict.

Exit Criteria:
- Assignment map exists.
- Execution order is deterministic.

### Implement
Inputs:
- Assigned `IMPLEMENT:` issue.

Actions:
- Implement issue scope only.
- Add/maintain unit tests for issue acceptance.
- Iterate until acceptance criteria pass.

Rules:
- Respect dependency order.
- Respect file ownership boundaries.
- Follow `MSR Design Standards`.

Exit Criteria:
- Issue implementation complete.
- Related unit tests pass.

### Review
Inputs:
- Implementation + tests for each `IMPLEMENT:` issue.

Actions:
- Perform review across:
  - correctness
  - test adequacy
  - standards compliance
- Use separate subagent/reviewer per standards category where possible.
- Classify findings as:
  - `BLOCKING`
  - `WARNING`
  - `SUGGESTION`
- Iterate until all `BLOCKING` findings are resolved and tests pass.

Required Close Command:
- Close completed issue with:
  - `gh issue close <number> --comment "Review approved. All BLOCKING findings resolved and unit tests passed."`

Exit Criteria:
- Issue closed only after zero `BLOCKING` and passing tests.

### Deploy
Actions:
- Create approval-gate issues via workflow `deploy-approval-issues.yml`:
  - `DEPLOY: Approve dev environment provisioning`
  - `DEPLOY: Approve stage environment provisioning`
  - `DEPLOY: Approve prod environment provisioning`
  - `DEPLOY: Approve CI/CD pipeline provisioning`
  - `DEPLOY: Approve deployment execution via CI/CD`

Approval Signal:
- User comments `APPROVED` or `APPROVE`.

Required approval handlers:
- `.github/workflows/on-deploy-env-approval.yml`
  - matches environment-oriented DEPLOY titles (dev/development, stage/staging, prod/production; one or many)
  - runs `infrastructure/provision_cloud.py` for inferred target environments
- `.github/workflows/on-deploy-cicd-approval.yml`
  - handles "DEPLOY: Approve CI/CD pipeline provisioning"
  - runs `infrastructure/provision_cicd.py`
- `.github/workflows/on-deploy-service-approval.yml`
  - handles "DEPLOY: Approve deployment execution via CI/CD"
  - triggers `ci-cd.yml`

Each handler must:
- Trigger on `issue_comment`.
- Detect `APPROVED|APPROVE`.
- Post execution output and validation results to the issue.
- On success: close issue.
- On failure: post warning with manual retry guidance.

Exit Criteria:
- Approved steps executed with evidence comments.
- Deployment status auditable from issues.

### Monitor
Start Condition:
- Environment provisioned and service deployed.

Actions:
- Run health check every hour.
- On health check failure:
  - create/update `DIAGNOSE:` issue with failure context and run URL
  - fail monitor workflow job after issue update
- Monitor logs for errors.
- On detected error:
  - create/update `DIAGNOSE:` issue with error details.

Exit Criteria:
- Continuous monitoring active.
- Failures always produce diagnosable issue artifacts.

### Service
Operational steady state:
- Service remains monitored.
- New incidents route to `DIAGNOSE:` process.

### Diagnose
Trigger:
- New or updated issue with title prefix `DIAGNOSE:`.

Actions:
- Parse issue failure details.
- Determine top 3 likely root causes.
- Add mitigations and recommended resolutions for each cause.
- Post findings back to same issue.

Exit Criteria:
- `DIAGNOSE:` issue contains triage-ready root-cause analysis.

## 5) GitHub Issue Automation Requirements (Mandatory)

Implement executable automation in `.github/workflows/` using `actions/github-script` or `gh` CLI with `GITHUB_TOKEN`.

Workflow permissions (minimum):
- `issues: write`
- `contents: read`

Workflow policy:
- Ensure all workflows have correct syntax
- Ensure all workflows have clean, succinct yaml
- Only create yml files that github can fully process


Issue upsert policy:
- Use stable titles.
- Find open issue by exact title.
- Update/comment existing issue instead of duplicating.

Project association:
- Create project each run (`<ProjectTypeName>_<timestamp>`).
- Associate every created pipeline issue to that project.
- When adding issue to project/card, use GitHub Issue `id` as `content_id` (not issue number).

Traceability (required in issue body/comments):
- Workflow run URL
- Commit SHA

Design/Plan gate rules:
- Trigger stage may create/update only `DESIGN:`.
- Plan stage may create/update `IMPLEMENT:` only after design gate passes.

## 6) Copilot Skills and Subagents

Create one skill per lifecycle responsibility under `.github/skills/<skill-name>/`.

Minimum skill set:
- design-validator
- issue-planner
- dependency-scheduler
- implementer
- test-author
- reviewer-standards
- deploy-orchestrator
- monitor-operator
- diagnose-investigator
- audit-recorder

Skill contract:
- Purpose
- Inputs
- Outputs
- Constraints
- Hand-off conditions

Use external skills when appropriate:
- https://github.com/agentskills/agentskills
- https://agentskills.io/specification

## 7) Audit Logging Requirements

### Global Run Log
File: `results/copilot-progress.md`

For each run append:
- run id
- timestamp
- triggering prompt
- branch + commit SHA
- workflow run URL(s)
- stage transitions and outcomes
- created/updated issue references
- blocking events and resolution links

### Issue-Level Audit
Each pipeline issue must contain:
- stage-specific actions taken
- command/workflow evidence
- validation outcomes
- next-step decision and rationale

## 8) MSR Design Standards (Enforcement Contract)

### Code Standards
Python:
- Format with `black`
- Lint with `flake8` (configured via `.flake8`)

### Security Standards
- No API keys or secrets committed to repository.
- Use secure secret handling through GitHub Actions secrets/environment protections.

### Privacy Standards
- No sensitive user data in logs/issues by default.
- Redact incident payloads before posting to issues.

### Responsible AI Standards
- Log model/tool decisions affecting architecture or behavior.
- Keep human approval checkpoints for deployment-impacting actions.

### Repository Conventions
- Follow existing design/coding patterns in this repository.
- Keep generated implementation code under `src/`.

## 9) Acceptance Criteria (Definition of Done)

Pipeline is complete only if all are true:
- Init stage builds required skills/workflows, installs them, and validates readiness before Trigger.
- Invocation prompts trigger orchestration reliably.
- `DESIGN:` gate created and enforced before Plan.
- Plan runtime revalidation prevents invalid `IMPLEMENT:` issue creation.
- `IMPLEMENT:` issues are discrete, dependency-aware, and parallel-safe.
- Assign/Implement/Review honor dependency graph and file conflict rules.
- Deploy approvals are issue-comment driven and handler workflows execute real scripts.
- Monitor creates/updates `DIAGNOSE:` issues on failures and fails job accordingly.
- Diagnose flow posts top 3 root causes with mitigations/resolutions.
- Project is created per run and all issues are associated.
- `results/copilot-progress.md` contains complete per-run audit evidence.
- All required workflows exist in `.github/workflows/`.

## 10) Non-Goals
- Do not directly edit `spec.md`.
- Do not simulate issue creation with markdown-only logs.
- Do not bypass approval gates for deployment actions.
