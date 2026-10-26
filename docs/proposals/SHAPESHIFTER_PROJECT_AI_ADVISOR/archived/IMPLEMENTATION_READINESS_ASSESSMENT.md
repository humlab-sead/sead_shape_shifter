# Implementation Readiness Assessment

**Date:** 2026-07-04
**Revised:** 2026-10-16
**Assesses:** [SHAPESHIFTER_PROJECT_AI_ADVISOR.md](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md) and [SHAPESHIFTER_PROJECT_AI_ADVISOR_PHASE_PLAN.md](./SHAPESHIFTER_PROJECT_AI_ADVISOR_PHASE_PLAN.md)

The revision covers the investigation capability added to the proposal. Investigation inserted a phase before the frontend and a sandboxed-execution phase after it, so the phase numbering used here follows the revised plan.

---

## Ready to start now: Phase 0 (Knowledge Foundation)

The Knowledge Foundation phase can begin today. The rule schema is fully specified (10 fields), the source documents are enumerated, an example rule exists, and the curation rules are clear. No blocking decisions remain.

## Ready with minor pre-work: Phases 1–2 (Backend API + Evaluation Harness)

The backend API and evaluation harness are well-specified but have three gaps that should be closed before coding starts:

### 1. No LLM prompt template

The proposal says the model "explains what the deterministic layer found," but there's no system prompt, no few-shot examples, and no specification for how assembled context is formatted for the model. Prompt quality is the single biggest determinant of feature quality. A draft system prompt and one formatted example context+response pair would close this gap.

### 2. No concrete API contract

The response shape is described in prose — `answer`, `reasoning_summary`, `citations`, `suggested_next_actions` — but there are no Pydantic model definitions. Given the proposal already names the file (`backend/app/models/advisor.py`), sketching the model classes would cost little and prevent rework.

### 3. No error/fallback behavior

What happens when the LLM provider is unreachable? When the response cannot be parsed? When a citation ID is hallucinated? The proposal says "reject or flag" but doesn't specify the user-visible behavior. A one-paragraph fallback policy per error class is needed.

## Ready with minor pre-work: Phase 3 (Investigation)

Tiers 1 and 2 reuse services the backend already has, so no new execution surface is required. Four gaps should be closed first:

### 1. Citation IDs do not match real validation codes

The proposal's citation examples use placeholder identifiers such as `validation.message.E1023`, but the validators emit codes that are already stable and machine-readable, for example `FK_REMOTE_EMPTY`, `FK_DATA_INTEGRITY`, `EMPTY_RESULT`, `COLUMN_NOT_FOUND`, and `NON_UNIQUE_KEYS`. The citation scheme should be defined against the real codes so citations resolve without a mapping table that can drift.

### 2. No message-to-source mapping

Nothing currently connects a reported message to the check that produced it. Source retrieval needs either a declared mapping from issue codes to source locations, or a search step that resolves them at run time. This is the difference between citing a file and line, and citing a file that merely contains the string.

### 3. Evidence artifact persistence undefined

The proposal defines the artifact fields but not where artifacts live. Attaching them to the advisor response and the session keeps them auditable; persisting them server-side additionally supports reproduction. Decide which, and note that artifacts can contain project data, so retention interacts with the redaction rules.

### 4. Read-only data access unconfirmed

Pipeline probing runs loaders against the project's data sources. Confirm that probing uses read-only credentials and that a probe cannot mutate a source. The proposal requires this; the mechanism is unverified.

## Not ready: Phase 4 (Frontend)

The frontend surface has several open design questions:

| Gap | Why it blocks implementation |
|---|---|
| Tab vs. drawer not decided | Different component trees, different state management |
| Citation chip navigation undefined | "Navigate to the relevant entity" — open a panel? scroll in the YAML editor? affects backend citation target design |
| No streaming decision | Chat UX without streaming feels broken; affects API design (SSE vs. request-response) |
| No loading/error/progress states designed | LLM calls are slow; users need visible feedback |
| Evidence artifact display undefined | Artifacts carry tables of counts and values plus a `limitations` field; the surface must show both without burying the answer |
| Source citation target undefined | A code location may need to open outside the browser; decide before fixing the citation `target` shape |

The last two are new in this revision. Investigation produces artifacts and source citations, so the frontend renders them, and the backend citation `target` shape depends on those decisions.

## Not ready: Phase 5 (Sandboxed Experiment Execution)

| Gap | Why it blocks implementation |
|---|---|
| Isolation mechanism undecided | Container, subprocess, or separate service — each changes deployment, dependencies, and the threat model |
| Execution policy undefined | Whether generated code may run at all may differ by environment; the proposal requires a local-only mode, so the same decision must cover deployment topology |
| Resource limits unset | Time and memory bounds need values, and unbounded runs are the main availability risk |
| Artifact retention unbounded | Sandbox output can be large; retention and size limits interact with redaction |

The phase is sequenced after the frontend precisely so these decisions do not gate the user-facing surface.

## Brief assessment of Phases 6–8

| Phase | Status | Note |
|---|---|---|
| Phase 6 (Structured Proposal Generation) | Mostly ready | Depends on the Phase 3 outcome, since proposals should rest on verified problems. The proposal response shape is undefined; the review-only constraint is clear. |
| Phase 7 (Data-To-Configuration Assistance) | Ready | Same shape as Phase 6 with source-type coverage still open. |
| Phase 8 (Approval-Based Apply) | Requires a decision | The approval requirement is clear; the recovery and rollback mechanism is not. |

## Trivial gaps (won't block)

- **The Data-to-Configuration inconsistency is resolved.** The earlier assessment noted that data-to-configuration appeared as future work in the proposal but as an in-scope phase in the plan. The proposal now lists investigation, structured proposal generation, data-to-configuration help, and approval-based apply together as future phases, matching the plan.
- **No performance/latency budget.** This now matters more than it did. A single question may trigger several pipeline runs, and each run loads and normalizes real data. A per-question bound on run count, and a stated latency expectation, should be added.
- **Knowledge pack file format** (YAML vs. JSON) and runtime loading path not specified. Minor; can be decided during Phase 0.

## Verdict

The proposal is **backend-implementation-ready through Phase 3** with about a day of pre-work on the three original gaps plus the four investigation gaps above. The frontend needs UX design before coding can start, and now also a decision on how evidence artifacts and source citations are displayed. Phase 5 and Phase 8 each require a named decision before they can be planned, and both are sequenced so they do not block earlier phases. Phase 0 has no blockers at all.

