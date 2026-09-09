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

The target document may come from the current conversation. Do not derive it from repository naming patterns alone. If the destination remains ambiguous, ask one concise clarifying question.

Do not treat labels, examples, or placeholder text as input values.

## References

Before writing or revising a phase plan, read:

- [Phase plan guide](references/phase-plan.md)
- [Proposal document structure](references/proposal-document-structure.md)
- applicable repository instruction files, including `AGENTS.md`

## Workflow

1. Read the source proposal and extract its confirmed decisions, Planning Handoff, and `P-AC-*` criteria as the source of work.
2. Inspect the repository only as needed to confirm current state and phase boundaries. Do not perform task-level file, symbol, or test inventory.
3. When `graphify-out/graph.json` exists, begin with a scoped `.venv/bin/graphify query "<phase question>"`. Verify findings in current source.
4. Create ordered phases with explicit dependencies, outputs, `PH<N>-AC-<N>` criteria mapped to `P-AC-*`, validation milestones, and task-plan handoff details.
5. Mark a phase ready for a task plan only when no unresolved decision can change its implementation or validation. Record other decisions as blocking questions.

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
