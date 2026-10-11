---
name: create-phase-plan
description: Create an ordered phase plan that sequences an approved proposal into delivery phases. Use when the user asks to create or update a phase plan, delivery sequencing document, or migration phase plan. Do not use for proposals, phase task plans, implementation checklists, or implementation work.
---

# Create a Phase Plan

Create one ordered phase plan that sequences an approved proposal into delivery phases.

The user's instructions take precedence over this skill. Follow applicable repository and directory-specific instructions according to their defined precedence. If an instruction conflict prevents completion, report it instead of guessing.

## Inputs

Determine from the user's request or current conversation:

- the source proposal path
- the repository-relative target document

Infer details when the conversation or verified repository content establishes them.

An explicit target from the user or the current conversation takes precedence. Otherwise, name and place the phase plan per the Document Naming rule in [Proposal document structure](references/proposal-document-structure.md). If the source proposal path is unknown, ask one concise clarifying question.

Preserve the path of an existing phase plan when updating it. If a user-supplied target does not follow the convention, confirm the path before writing.

Do not treat labels, examples, or placeholder text as input values.

## References

Before drafting, read:

- [Phase plan guide](references/phase-plan.md)
- [Proposal document structure](references/proposal-document-structure.md)
- the repository root [AGENTS.md](../../../AGENTS.md) and [`.github/AGENTS.md`](../../../.github/AGENTS.md)
- [phase plan instructions](../../../.github/instructions/phase-plan.instructions.md)
- [proposal structure instructions](../../../.github/instructions/proposal-document-structure.instructions.md)
- [writing style instructions](../../../.github/instructions/writing-style.instructions.md)

Use the repository instructions for project-specific rules if they differ from the skill references.

## Phase Plan Standard

- Keep the plan focused on delivery order from the verified current state to the proposal's target state. Do not repeat the full proposal or turn the plan into a task checklist, implementation specification, or project tracker.
- Use the default sections Summary, Problem, Scope, Current Position, Phase Plan, Cross-Phase Rules, Validation Strategy, and Final Recommendation. Keep Summary, Problem, Scope, and Phase Plan; compress or omit other sections when they do not help explain delivery.
- Keep Scope delivery-oriented. In Current Position, summarize proposal decisions and verified repository facts; label assumptions and open questions.
- Make each phase a meaningful delivery step with a goal, focus, dependencies, outputs, checkable `PH<N>-AC-<N>` criteria mapped to source `P-AC-*` criteria, validation milestones mapped to those criteria, a Task-Plan Handoff, and a readiness state.
- Cover every known gap. Prefer 3–7 phases, using fewer for small work and more only when needed. State structural assumptions about phase ordering or grouping when details are missing.
- Include cross-phase rules only when they affect sequencing, validation, or phase boundaries. For migrations, include fallback, exception, or cutover work when relevant; use parity as a measure when replacing legacy behavior.
- Keep exact commands, test files, fixtures, assertions, and implementation steps for the phase task plan.

## Workflow

1. Confirm the request calls for a phase plan and identify its source proposal and target path.
2. Read the source proposal and use its confirmed decisions, Planning Handoff, and `P-AC-*` criteria as the plan's authority.
3. Inspect the repository only far enough to confirm current state, known gaps, and phase boundaries. Do not perform task-level file, symbol, or test inventory.
4. When `graphify-out/graph.json` exists, begin repository discovery with a scoped `.venv/bin/graphify query "<phase question>"`. Verify relevant findings in current source.
5. Sequence meaningful phases from current state to target state. Make dependencies explicit and cover each known gap.
6. Check that phase criteria map to proposal criteria and validation milestones, deferred work is visible, and planned behavior is not described as current behavior.
7. Mark a phase ready for a task plan only when no unresolved decision can change its implementation or validation. Record other decisions as blocking questions.

## Limits

- Produce one phase plan only.
- Do not create phase task plans, implementation checklists, or code changes.
- Do not invent commands, test names, file paths, APIs, owners, or dates.
- Keep exact commands, test files, fixtures, assertions, and implementation steps for the phase task plan.
- Repository inspection outside the target document must be read-only.
- Modify only the target document.
- If the target already exists, update it only when the user clearly requested an update. Otherwise, ask before replacing it.

## Output

When editing is authorized and filesystem tools are available:

1. Write the phase plan to the target document.
2. Return a concise completion message with the target path.

Otherwise, return the completed phase plan Markdown.
