---
name: create-phase-task-plan
description: Create a repository-verified task plan for one ready phase. Use when the user asks to create or update a phase task plan, work breakdown, implementation checklist, or execution tracker for a single phase. Do not use for proposals, phase plans, or implementation work.
---

# Create a Phase Task Plan

Create one repository-verified task plan for a single ready phase.

The user's instructions take precedence over this skill. Follow applicable repository and directory-specific instructions according to their defined precedence. If an instruction conflict prevents completion, report it instead of guessing.

## Inputs

Determine from the user's request or current conversation:

- the source proposal path
- the source phase plan path
- the selected phase identifier
- the repository-relative target document

Infer details when the conversation or verified repository content establishes them.

An explicit target from the user or the current conversation takes precedence. Otherwise, name and place the task plan per the Document Naming rule in [Proposal document structure](references/proposal-document-structure.md). If the source proposal path or phase number is unknown, ask one concise clarifying question.

Preserve the path of an existing task plan when updating it. If a user-supplied target does not follow the convention, confirm the path before writing.

Do not treat labels, examples, or placeholder text as input values.

## References

Before drafting, read:

- the repository root [AGENTS.md](../../../AGENTS.md) and [`.github/AGENTS.md`](../../../.github/AGENTS.md)
- [phase task plan instructions](../../../.github/instructions/task-plan.instructions.md)
- [Proposal document structure](references/proposal-document-structure.md)
- [writing style instructions](../../../.github/instructions/writing-style.instructions.md)

Also read applicable subsystem instructions for any code, tests, configuration, or data the plan covers. Use repository instructions for project-specific rules if they differ from this skill.

## Task Plan Standard

- Keep the plan specific to one phase and detailed enough for another coding agent to execute without repeating the initial investigation. Do not turn it into a multi-phase plan or modify implementation files.
- Use the standard sections: Phase Summary, Repository Findings, Scope, Work Breakdown, Acceptance-Criteria Coverage, Validation And Testing, Deliverables, Progress Tracker, and Definition Of Done. Add Risks And Open Questions only when they identify a real issue. Omit irrelevant sections rather than leaving them empty.
- Start Repository Findings with the repository basis: branch and commit when available, planning date, and whether uncommitted changes were considered. Record relevant verified findings with their implementation implications; distinguish them from assumptions.
- State in-scope and out-of-scope work and the affected components, contracts, data, tests, and documentation. Break work into the fewest independently implementable and reviewable areas, normally 2–6. For each area, state its objective, affected code, dependencies, tasks, and completion evidence.
- Give tasks stable `T*` IDs, exact verified targets, current and required behavior, implementation details, relevant constraints, validation IDs, and completion evidence. Mark proposed files `NEW`.
- Preserve every `PH*-AC-*` criterion and its source `P-AC-*` mapping. Map each criterion to task IDs and validation IDs, and ensure every referenced ID exists.
- Give each validation check a stable `V-*` ID and an executable command or manual method. Consider unit, integration, contract, negative, boundary, and regression checks, plus type, lint, migration, security, and documentation checks when relevant. Name exact test targets, cases, fixtures or inputs, and expected results. Record baseline status as Pass, Fail, or Not run with the reason; never report a planned check as a completed result.
- List every deliverable with its exact path, producing task IDs, and completion evidence. Include a phase-specific Definition Of Done covering criteria, work areas, deliverables, required checks, preserved behavior, synchronized artifacts, deviations, and unresolved questions. Track work with Not started, In progress, Blocked, or Done statuses.
- Include only concrete risks and open questions. State why each matters, what depends on it, and a recommended resolution when repository findings support one.
- Use **Validated** only when the source phase is ready, repository targets are verified, executable validation methods are specified, and no unresolved decision or placeholder can change implementation. Use **Draft** when repository investigation or user confirmation remains. Use **Blocked** when an external decision or dependency prevents completing the plan or starting work. Explain Draft or Blocked status.

## Workflow

1. Read the source proposal and phase plan. Confirm the selected phase is marked ready and identify its `PH*-AC-*` criteria, source `P-AC-*` criteria, fixed decisions, constraints, dependencies, and validation milestones.
2. If the phase is not ready, produce a Blocked task plan that names the blocking decision. Do not mark it Validated.
3. When `graphify-out/graph.json` exists, begin repository discovery with a scoped `.venv/bin/graphify query "<phase question>"`. Use `path` or `explain` to follow relationships, then verify findings in current project instructions, source, tests, configuration, and documentation. Trace affected callers, consumers, contracts, schemas, and data flows where relevant.
4. Verify repository targets and existing commands, and run relevant baseline checks when safe and proportionate. Record the branch, commit, planning date, and whether uncommitted changes were considered.
5. Produce one task plan with verified findings, exact existing targets, proposed files marked `NEW`, ordered `T*` tasks, `V*` validation checks, baseline results, deliverables, and full acceptance-criteria coverage.
6. Check task dependencies, links, IDs, validation methods, deliverables, and Definition Of Done. Report discrepancies between Graphify and current source or tests; do not invent a replacement design.
7. Set readiness to Validated only when the source phase is ready, repository targets are verified, validation methods are executable, and no unresolved placeholder or decision can change implementation.

## Limits

- Produce one phase task plan only.
- Do not modify implementation, tests, configuration, or unrelated documentation.
- Preserve `PH*-AC-*` and source `P-AC-*` mappings. Map phase criteria to `T*` task IDs and `V*` validation IDs.
- Use verified repository facts. Do not invent files, symbols, commands, APIs, or test names.
- Treat Graphify as a navigation aid, not the source of truth. If it conflicts with source or tests, plan from current source and note the discrepancy.
- Repository inspection outside the target document must be read-only.
- Modify only the target document.
- If the target already exists, update it only when the user clearly requested an update. Otherwise, ask before replacing it.

## Output

When editing is authorized and filesystem tools are available:

1. Write the task plan to the target document.
2. Return a concise completion message with the target path.

Otherwise, return the completed task plan Markdown.
