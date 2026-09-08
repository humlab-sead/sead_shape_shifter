---
name: "Task Plan Detailed Instructions"
description: "Use when creating or updating repository-validated implementation plans, phase work breakdowns, implementation checklists, or execution trackers."
---


# Copilot Instructions: Phase Task Plans

When asked to plan a development phase, produce a Markdown implementation plan detailed enough for another coding agent to execute.

Unless implementation is explicitly requested, create or update only the requested planning document. Do not modify implementation, test, configuration, or unrelated documentation files.

## Planning Process

Before writing the plan:

1. Extract the goal, scope, constraints, and acceptance criteria.
2. Inspect relevant project instructions, code, tests, configuration, and documentation.
3. Trace affected callers, consumers, contracts, schemas, and data flows where relevant.
4. Locate existing project commands and similar implementations.
5. Identify dependencies, risks, ambiguities, and behavior that must be preserved.
6. Validate the completed plan using the checklist below.

Do not use `TBD` for facts that reasonable repository inspection can establish.

## Output

Return only the Markdown plan unless the user asks for explanation.

Prefer repository-specific detail over generic guidance. Name verified files, symbols, commands, APIs, and tests when useful.

Use one of these readiness states:

* **Validated** — checked against the repository and ready for implementation.
* **Draft** — useful, but specified facts or decisions remain unverified.
* **Blocked** — a missing decision or dependency prevents reliable planning.

Explain why a plan is Draft or Blocked.

## Default Structure

1. Phase Summary
2. Repository Findings
3. Scope
4. Work Breakdown
5. Acceptance-Criteria Coverage
6. Validation And Testing
7. Progress Tracker
8. Definition Of Done
9. Risks And Open Questions — when relevant

## Phase Summary

Include:

* Phase title and goal.
* Plan readiness.
* Constraints and dependencies.
* Acceptance criteria as a numbered checklist using IDs such as `AC-1`.

Preserve the supplied acceptance criteria, but clarify them into observable outcomes when necessary.

## Repository Findings

Summarize only findings that affect implementation:

| Evidence                  | Finding          | Planning implication          |
| ------------------------- | ---------------- | ----------------------------- |
| `path/to/file.py::symbol` | Current behavior | Required change or constraint |

Prefer paths and symbols over line numbers. Clearly distinguish verified findings from assumptions.

## Scope

State:

* **In scope**
* **Out of scope**
* Affected components, layers, contracts, data, tests, and documentation

Do not add unrelated improvements.

## Work Breakdown

Create the fewest independently implementable and reviewable work areas, normally 2–6.

For each work area include:

### Area N: Action-oriented title

**Objective:** Observable result of this area.

**Affected code:** Verified files, symbols, tests, or configuration.

**Dependencies:** Preceding areas or unresolved decisions.

**Tasks:**

* [ ] State what changes, where it changes, and important constraints.
* [ ] Include compatibility, error handling, migration, or security work when relevant.
* [ ] Identify tests or other evidence that confirm the behavior.

**Completion evidence:** State the observable condition that proves the area is complete.

Order areas according to implementation dependencies.

## Acceptance-Criteria Coverage

Map every acceptance criterion to implementation and validation:

| Criterion | Work area | Validation             | Expected evidence |
| --------- | --------- | ---------------------- | ----------------- |
| `AC-1`    | Area 1    | Relevant test or check | Observable result |

No acceptance criterion may remain unmapped.

## Validation And Testing

Use verified repository commands when available:

| Check            | Command or method    | Covers            | Expected result |
| ---------------- | -------------------- | ----------------- | --------------- |
| Focused tests    | `<verified-command>` | `AC-1`            | Tests pass      |
| Regression tests | `<verified-command>` | Existing behavior | No regressions  |

Include relevant:

* Unit, component, integration, and contract tests.
* Negative, boundary, and regression cases.
* Type checking, linting, and formatting.
* Migration and data-integrity checks.
* Security and authorization checks.
* Documentation or generated-artifact checks.

Do not claim that a command passes unless it was actually run. Distinguish baseline checks run during planning from checks planned for implementation.

## Progress Tracker

| Area   | Status      | Dependencies | Notes |
| ------ | ----------- | ------------ | ----- |
| Area 1 | Not started | None         |       |

Use: Not started, In progress, Blocked, or Done.

## Definition Of Done

Include a phase-specific checklist confirming that:

* [ ] Every acceptance criterion has implementation and validation evidence.
* [ ] All work areas and deliverables are complete.
* [ ] Required tests and quality checks pass.
* [ ] Behavior identified for preservation has been regression-tested.
* [ ] Contracts, migrations, documentation, and generated artifacts are synchronized where applicable.
* [ ] Deviations and follow-up work are documented.
* [ ] No unresolved question affects correctness.

## Risks And Open Questions

Include only concrete risks and unresolved decisions that could block or materially change implementation.

For an open question, state why it matters, what depends on it, and the recommended resolution when evidence supports one.

## Rules

* Do not invent repository facts.
* Inspect before using placeholders.
* Mark files to be created explicitly.
* Record necessary assumptions and how they will be verified.
* Prefer established project conventions.
* Make tasks concrete and independently checkable.
* Use direct verbs such as implement, update, remove, migrate, test, and validate.
* Avoid vague tasks such as “look into,” “handle,” or “address.”
* Do not repeat the same content across sections.
* Keep simple plans short; add detail only when complexity requires it.

## Final Plan Validation

Before returning the plan, confirm that:

* Referenced existing files, symbols, commands, and tests were verified.
* Proposed changes match repository architecture and conventions.
* Affected callers, consumers, and contracts were considered.
* Every acceptance criterion maps to work and validation.
* Tasks are ordered by their actual dependencies.
* Risks and assumptions are explicit.
* Another coding agent could begin without repeating the initial investigation.

If any check fails, correct the plan or mark it Draft or Blocked.
