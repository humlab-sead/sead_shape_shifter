---
name: implement-phase-task-plan
description: Implement one validated phase task plan without redesigning or broadening its scope. Use when the user asks to implement, execute, or work through a phase task plan or its T* task IDs. Do not use for creating proposals, phase plans, or task plans.
---

# Implement a Phase Task Plan

Implement one validated phase task plan, making only the changes mapped to its task IDs.

The user's instructions take precedence over this skill. Follow applicable repository and directory-specific instructions according to their defined precedence. If an instruction conflict prevents completion, report it instead of guessing.

## Inputs

Determine from the user's request or current conversation:

- the repository-relative task plan document

Infer details when the conversation or verified repository content establishes them.

Do not treat labels, examples, or placeholder text as input values.

## References

Before implementing, read:

- [Task plan detailed guide](references/task-plan-detailed.md)
- [Proposal document structure](references/proposal-document-structure.md)
- [Coding practices](references/coding-practices.md)
- the task plan and its linked proposal and phase plan
- applicable repository instruction files, including `AGENTS.md`

## Preconditions

- Confirm the selected phase is marked ready in the phase plan.
- Confirm the task plan is marked Validated and has no unresolved placeholder or blocking question.
- Confirm the repository still matches the plan's verified targets, dependencies, and expected current behavior.

If a precondition fails, do not edit implementation files. Report the mismatch with the relevant path, symbol, observed behavior, and affected task or criterion ID.

## Workflow

1. Implement tasks in dependency order, making only changes mapped to the task plan's `T*` IDs.
2. Preserve the documented contracts, compatibility behavior, migration rules, security requirements, and scope limits.
3. Create or update only deliverables named by the task plan. Do not redesign the solution or add unrelated improvements.
4. Run every specified `V*` validation check. Record actual results and any pre-existing baseline failures.
5. Update the task plan's progress tracker and completion items only after the corresponding work and validation are complete.
6. If verified repository state conflicts with the plan, stop and report. Do not invent a replacement design or broaden scope.

## Limits

- Do not modify implementation, tests, configuration, or documentation outside the task plan's named deliverables.
- Do not redesign the solution, broaden scope, or add unrelated improvements.
- Do not mark work or validation complete without fresh evidence.
- Do not invent repository facts, paths, symbols, commands, APIs, or tests.

## Output

Return a concise implementation report with completed task IDs, changed deliverables, validation results, and any follow-up work. If work stops, return the mismatch report instead.
