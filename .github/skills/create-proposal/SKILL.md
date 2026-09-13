---
name: create-proposal
description: Create or revise a decision-focused software design proposal. Use when the user asks to draft, write, create, or update a proposal. Do not use for phase plans, task plans, implementation checklists, or implementation work.
---

# Create a Proposal

Create or revise one decision-focused proposal for the requested change.

The user's instructions take precedence over this skill. Follow applicable repository and directory-specific instructions according to their defined precedence. If an instruction conflict prevents completion, report it instead of guessing.

## Inputs

Determine from the user's request or current conversation:

- the change or problem the proposal should address
- the repository-relative target document

Infer proposal details when the conversation or verified repository content establishes them.

The target document may come from the current conversation. Do not derive it from repository naming patterns alone. If the destination remains ambiguous, ask one concise clarifying question.

Do not treat labels, examples, or placeholder text as input values.

## References

Before writing or revising a proposal, read:

- [Proposal writing guide](references/proposal-writing-guide.md)
- [Proposal document structure](references/proposal-document-structure.md)
- [Proposal template](references/proposal-template.md)
- applicable repository instruction files, including `AGENTS.md`

## Workflow

1. Identify the decision the proposal must support.
2. Inspect the repository only as needed to verify current behavior, feasibility, interfaces, constraints, and migration risks.
3. Separate verified facts from assumptions and open questions.
4. Write the proposal using the required structure.
5. Define observable acceptance criteria with stable `P-AC-*` identifiers.
6. Include a Planning Handoff when later work will require a phase plan.
7. Check that planned behavior is not described as existing or completed behavior.

## Limits

- Produce one proposal only.
- Do not create a phase plan, task plan, implementation checklist, or code changes.
- Do not perform a file-by-file implementation inventory.
- Do not invent repository facts, paths, commands, APIs, tests, owners, or dates.
- Use `TBD` only when a required field cannot be meaningfully completed.
- Repository inspection outside the target document must be read-only.
- Modify only the target document.
- If the target already exists, update it only when the user clearly requested an update. Otherwise, ask before replacing it.

## Output

When editing is authorized and filesystem tools are available:

1. Write the proposal to the target document.
2. Return a concise completion message with the target path.

Otherwise, return the completed proposal Markdown.