# Copilot Review Instructions (Repository-wide)

## General Guidelines for Reviewing Pull Requests in this Repository

When reviewing pull requests in this repository:

- Be specific and actionable:
   - Reference exact file paths and (when applicable) the nearest heading/section or line range.
   - Prefer concrete suggested edits (or example snippets) over general advice.

- Focus on correctness, clarity, and consistency:
   - Call out inconsistencies in naming/terminology and requirements vs implementation mismatches.
   - Highlight missing acceptance criteria or unclear requirements when you see them.

- Keep feedback organized:
   - Separate “Critical issues” from “Suggestions / Nice-to-haves”.
   - If there are multiple findings, provide a short summary list first, then details.

- For Markdown spec/design docs (i.e. spec.md, design.md, etc.):

  - Follow `Required workflow for Markdown spec/design reviews` when reviewing Markdown files related to project specifications, design documents, and other planning artifacts. The goal is actionable, contextual feedback.

## Required workflow for Markdown spec/design reviews

1) **Design review pass**
- Use `Design Review Guidance for Markdown Specs/Design Docs` specified below as the basis for design reviews of markdown files

2) **Inline comments for critical issues**
- Add critical feedback as **inline PR comments** on the relevant lines when possible (tight coupling to the exact requirement/section).
- Add suggestions as "copilot fixes" that the author can easily apply (for example: “Replace this sentence with: ...” or “Add the following acceptance criteria: ...”).

3) **Summarize major + minor findings**
- For major and minor feedback, compile a list of findings as a **Findings** section (either:
  - at the end of the Markdown doc as suggested text to add, OR
  - as a PR comment that the author can paste into the doc).

4) **Reference exact sections**
- Always reference the relevant heading/section/requirement in the doc (e.g., “Functional Requirement 1”, “Non-functional requirements”, etc.).

5) **Azure Functions best practices (with links)**
- When commenting on Azure Function design/architecture, ground recommendations in Azure Functions best practices and include links to authoritative Microsoft/Azure docs when relevant (for example: triggers/bindings, hosting plan choices, identity, storage, retries, idempotency, observability, and security).

## Design Review Guidance for Markdown Specs/Design Docs

### Review Rubric
1. Trigger and binding suitability for workload characteristics
2. Function granularity, cohesion, and separation of responsibilities
3. Idempotency, retries, poison message handling, and failure recovery
4. Concurrency, scaling behavior, cold-start sensitivity, and throughput limits
5. Security design: authN/authZ, secrets handling, least privilege, network boundaries
6. Data consistency, transaction boundaries, and duplicate event protection
7. Observability: structured logging, distributed tracing, metrics, and alertability
8. Configuration strategy: environment settings, slot-safe config, and secret externalization
9. Dependency design: external service timeouts, circuit breakers, and backpressure
10. Deployment and operations readiness: versioning, rollout safety, and rollback strategy

### Approach
1. Summarize the intended workload and non-functional goals.
2. Identify strengths briefly.
3. List findings ordered by severity (critical, major, minor).
4. List missing design details as critical findings
5. For each finding, provide rationale and a specific recommendation.
6. Note trade-offs for each major recommendation.

### Output format (for Markdown spec/design reviews)
- **Critical (inline comments):** only the highest-severity issues that must be fixed.
- **Findings (summary list):**
  - Critical
  - Major
  - Minor
  - Questions / Clarifications
- **Suggested edits:** provide specific replacement text or new sections (copy/paste friendly).
