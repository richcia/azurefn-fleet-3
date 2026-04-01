# Copilot Review Instructions (Repository-wide)

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
- For Markdown spec/design docs:

  Follow these instructions when reviewing Markdown files related to project specifications, design documents, and other planning artifacts. The goal is actionable, contextual feedback.

  ### Required workflow for Markdown spec/design reviews
  1) **Design review pass**
  - Use Design Review Guidance specified in `.github/agents/design-review-agent.md` as the basis for design reviews of markdown files

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


  ## Output format (for Markdown spec/design reviews)
  - **Critical (inline comments):** only the highest-severity issues that must be fixed.
  - **Findings (summary list):**
    - Critical
    - Major
    - Minor
    - Questions / Clarifications
  - **Suggested edits:** provide specific replacement text or new sections (copy/paste friendly).
