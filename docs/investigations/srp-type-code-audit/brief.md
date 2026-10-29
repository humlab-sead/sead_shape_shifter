# Investigation brief: Remaining SRP and entity-specific type-code concerns

**Tracking issue:** [#624](https://github.com/humlab-sead/sead_shape_shifter/issues/624)

## Objective

Identify and substantiate remaining production classes in Core and Backend that either combine responsibilities with independent reasons to change or embed fixed entity-specific behavior in otherwise general classes. Produce a prioritized, evidence-based set of findings and focused follow-up recommendations. Do not implement refactors as part of this investigation.

**Mode:** Investigation only. Implementing any recommended change requires separate authorization.

## Issue description

**Observed behavior:** This is a code-quality audit, not a reported runtime failure. Issue #624 asks for classes that may not follow the Single Responsibility Principle (SRP) or contain entity-specific "type code" behavior in the object-oriented sense. The user clarified that `ProjectMapper` was an example of this smell and has already been fixed. That status is user-reported and was not independently verified while preparing this brief.

**Expected behavior / invariant:** Report only classes for which code and usage provide concrete reasons to believe that separate responsibilities or entity-specific behavior create a maintainability problem. Do not treat every conditional, mapper, or domain-specific rule as a violation. No repository-wide rule requiring polymorphism or one method per class has been established.

**Impact:** No user-visible failure or data impact is currently established. The possible impact is higher maintenance cost when a class must change for unrelated responsibilities or when adding an entity requires editing general-purpose code.

**Known evidence and timeline:**

| Observation or artifact | Source / location | Date or version | Status / qualification |
| --- | --- | --- | --- |
| Issue #624 requests an audit for SRP and entity-specific type-code concerns. | [GitHub issue #624](https://github.com/humlab-sead/sead_shape_shifter/issues/624) | 2026-10-28 | Verified in the issue text. |
| `ProjectMapper` was an example of the smell and has since been fixed. | User report recorded in [GitHub issue #624](https://github.com/humlab-sead/sead_shape_shifter/issues/624) | 2026-10-28 | Reported, not independently verified during brief creation. Treat as a calibration example, not an open finding. |
| The project separates Core and Backend responsibilities and documents the mapper's API/Core role. | [DESIGN.md](../../DESIGN.md), [AGENTS.md](../../../AGENTS.md) | Working tree reviewed 2026-10-28 | Verified in current documentation; confirm relevant constraints against current code during the investigation. |

This audit is not based on a specific failure timeline. Record the investigation's exact commit, branch, and worktree state when it starts.

## Working hypotheses

- **H1:** One or more remaining Core classes combine responsibilities that can be evidenced as independently changing or used. Check class behavior, callers, tests, and history where useful.
- **H2:** One or more remaining Backend classes contain fixed entity-specific branches within otherwise general behavior. Check the branch conditions, the responsibilities they select, and whether the class is an intentional factory or dispatcher.
- **H3:** Some apparent candidates are intentional domain rules, mapping responsibilities, or registered dispatch and should not be reported as code smells. Record contrary evidence and any candidates that remain uncertain.
- **H4:** No additional clear examples may be found in the reviewed scope. This is a valid result; do not manufacture findings to fill a list.

## System context

Shape Shifter is a monorepo with a Core transformation engine in `src/`, a FastAPI Backend in `backend/app/`, a Vue Frontend in `frontend/`, and pluggable Ingesters in `ingesters/`. The project design describes Core as owning the transformation pipeline and the Backend as owning API services and API/Core mappers. The repository instructions also require API/Core conversion through `ProjectMapper` and keep directive resolution at that mapper.

These rules constrain recommendations: a proposed separation must preserve the documented layer responsibilities. The fixed `ProjectMapper` example can help calibrate what the user means by entity-specific code, but it is not an outstanding finding to reopen.

**Relevant entry points:**

- [Project design](../../DESIGN.md), especially "High-Level Architecture" and "Components and Responsibilities".
- [Repository architecture instructions](../../../AGENTS.md), especially "Cross-Cutting Rules".
- Core production code under `src/` and its tests under `tests/`.
- Backend production code under `backend/app/` and its tests under `backend/tests/`.
- The [tracking issue #624](https://github.com/humlab-sead/sead_shape_shifter/issues/624).

**Environment and baseline:** The brief was prepared on branch `dev`; the worktree was clean before this brief was created. The exact commit was not recorded. At investigation start, record the current commit, branch, date, and worktree state. Locate the change that fixed the `ProjectMapper` example in Git history if possible; if it cannot be identified, record that limitation.

## Investigation priorities

### 1. Establish the baseline and calibrate the examples

- Record the current repository commit, branch, and worktree state.
- Locate and inspect the `ProjectMapper` change and its relevant tests, if identifiable. Summarize the specific pattern that was fixed and use it only to calibrate the audit.
- Confirm that the fixed code is not being reported as an outstanding issue. If the history cannot establish what changed, preserve the user's report as unverified context.

### 2. Review Core classes

- Review production classes in `src/` for the two concerns defined in this brief. Track which modules or class groups were reviewed so the report states the actual coverage.
- For each candidate, inspect its methods, callers, relevant tests, and nearby abstractions. Use search or graph results to find candidates, but verify each against source and usage.
- Do not use class size, method count, or the presence of a conditional as sufficient evidence.

### 3. Review Backend classes and layer interactions

- Review production classes in `backend/app/` using the same criteria and record coverage separately from Core.
- For mapper, service, and orchestration candidates, trace relevant API/Core data flow and check the documented mapper responsibilities before recommending a separation.
- Inspect Frontend or Ingester code only when evidence from a Core or Backend candidate makes that dependency necessary. Do not present those layers as fully audited unless they are separately reviewed.

### 4. Test candidate explanations and assess impact

- For each candidate, identify the exact class, methods, type checks or responsibilities, and call paths that support the concern.
- Test alternate explanations, including intentional domain behavior, a mapper's required conversion role, and a factory or registry whose primary responsibility is dispatch.
- Use relevant tests or safe local checks only when needed to establish current behavior. Record exact commands and outcomes; do not infer test results.
- Rank substantiated findings by impact and explain which behavior and tests a future refactor should preserve.

### 5. Recommend next actions

- For each substantiated finding, propose a focused refactoring direction without prescribing a design pattern unless the code supports it.
- If no clear finding remains in a reviewed layer, say so and list any coverage limits or unresolved candidates.
- Recommend separate implementation issues only where the evidence supports actionable work. Do not create those issues as part of this investigation.

## Scope and constraints

**In scope:**

- Production classes in Core (`src/`) and Backend (`backend/app/`), reviewed as separate layers.
- SRP concerns and fixed entity-specific type-code behavior as defined in this brief.
- Relevant callers, tests, documentation, and Git history needed to verify or reject candidate findings.
- The `ProjectMapper` change as a calibration example, not as an open finding.

**Secondary scope:**

- Frontend (`frontend/`) and Ingesters (`ingesters/`) only when a specific Core or Backend candidate cannot be assessed without tracing that dependency. Record any such review separately.
- Other code-quality concerns only when they directly change the assessment of an in-scope candidate.

**Out of scope:**

- An exhaustive audit of Frontend, Ingesters, generated files, or test-only classes.
- Treating every conditional or entity-specific rule as a smell, or replacing all type checks with polymorphism or a registry.
- Creating a reusable code-smell skill or automated scanner.
- Implementing refactors, changing production code, or creating follow-up implementation issues.

**Permissions / safety:** Use read-only source, test, and history inspection by default. Safe, isolated local tests may be run when needed to verify behavior. Do not change application code, production data, infrastructure, or databases; do not deploy, migrate, commit, push, rewrite history, or run destructive commands. Obtain separate explicit authorization before any out-of-scope or mutating action.

## Expected deliverables

Produce `docs/investigations/srp-type-code-audit/findings.md` containing:

1. A summary of the audit status, reviewed layers, coverage, and material limitations.
2. The baseline commit and a short account of how the fixed `ProjectMapper` case was used to calibrate the review.
3. A findings table with layer, class and methods, concern type, concrete code evidence, impact, priority, and evidence status.
4. For each candidate, relevant counterevidence, an explanation of why it is or is not a concern, and behavior or tests to preserve.
5. Focused recommendations, unresolved questions, and proposed follow-up work. Findings may conclude that no clear cases were confirmed in a reviewed layer.
6. A reproducible record of commands, tests, and results actually used. Do not claim tests passed unless they were run.

Use `Verified`, `Supported hypothesis`, `Unverified`, or `Ruled out` for material claims and explain the basis. Separate confirmed findings from subjective or unresolved candidates. Do not claim a root cause for this broad audit; state when the evidence supports only a maintainability concern or when the assessment remains uncertain.

## Completion criteria

- Core and Backend review coverage is recorded separately, including modules or class groups not reviewed.
- The `ProjectMapper` example is either tied to its verified change history or clearly left as user-reported context; it is not presented as an outstanding finding.
- Every reported finding cites concrete class/method and code evidence and includes contrary evidence or plausible intentional explanations considered.
- Recommendations are prioritized, scoped, and identify relevant behavior or tests to preserve.
- The report distinguishes confirmed findings, rejected candidates, unresolved candidates, and unreviewed scope.
- No source change or refactor is made under this investigation brief.

## References

- [Tracking issue #624](https://github.com/humlab-sead/sead_shape_shifter/issues/624)
- [Project design](../../DESIGN.md)
- [Repository architecture instructions](../../../AGENTS.md)
