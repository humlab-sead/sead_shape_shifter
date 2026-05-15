---
agent: agent
description: Explore the codebase and produce an implementation plan or checklist for a proposal that touches existing code
---

Produce an implementation plan for the following change request:

**Change:** `{CHANGE_DESCRIPTION}`

---

## Your Task

1. **Explore the codebase** to understand the current state of all code, files, and tests relevant to this change. Do not skip this step — the plan must be grounded in what actually exists, not assumptions.

2. **Identify what needs to change** across all affected layers (core, backend, frontend, tests, config, docs). Be specific: file paths, class names, method names.

3. **Produce a delivery checklist** organized by layer and dependency order. Each item should be a concrete, actionable step — not a vague category. Items that must be done before others should appear first.

4. **Flag risks and open questions** that the checklist does not resolve. Keep this short.

5. **Optionally draft the proposal** using the structure from `.github/instructions/proposal-writing-guide.instructions.md`: Summary, Problem, Scope, Proposed Design, Tradeoffs and Risks, Validation, Final Recommendation. Only include this if a written proposal is part of the ask.

---

## Output Format

### Current State
*What exists today, relevant to this change.*

### What Changes
*Per-layer breakdown of files and symbols that need to be added, modified, or removed.*

### Delivery Checklist
- [ ] Step 1 (layer: reason)
- [ ] Step 2 ...
- [ ] Tests: ...

### Risks and Open Questions
*Only items the checklist does not already answer.*

---

## Constraints

- Base findings on actual code — use search and file reads before drawing conclusions.
- Do not invent file names or class structures. If something is unclear, say so.
- Keep the checklist items short and independently completable where possible.
- Do not pad with sections that add no information for this specific change.
