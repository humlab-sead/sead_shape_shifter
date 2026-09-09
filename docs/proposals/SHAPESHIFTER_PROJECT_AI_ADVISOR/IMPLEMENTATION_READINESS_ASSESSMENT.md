# Implementation Readiness Assessment

**Date:** 2026-07-04
**Assesses:** [SHAPESHIFTER_PROJECT_AI_ADVISOR.md](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md) and [SHAPESHIFTER_PROJECT_AI_ADVISOR_PHASE_PLAN.md](./SHAPESHIFTER_PROJECT_AI_ADVISOR_PHASE_PLAN.md)

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

## Not ready: Phase 3 (Frontend)

The frontend surface has several open design questions:

| Gap | Why it blocks implementation |
|---|---|
| Tab vs. drawer not decided | Different component trees, different state management |
| Citation chip navigation undefined | "Navigate to the relevant entity" — open a panel? scroll in the YAML editor? affects backend citation target design |
| No streaming decision | Chat UX without streaming feels broken; affects API design (SSE vs. request-response) |
| No loading/error/progress states designed | LLM calls are slow; users need visible feedback |

## Trivial gaps (won't block)

- **Phase 5** (Data-to-Configuration Assistance) is listed as future work in the proposal's Non-Goals ("Data-to-configuration help") but appears in-scope in the phase plan. Minor inconsistency.
- **No performance/latency budget.** For an MVP this is acceptable, but should be noted as a risk.
- **Knowledge pack file format** (YAML vs. JSON) and runtime loading path not specified. Minor; can be decided during Phase 0.

## Verdict

The proposal is **backend-implementation-ready** with about a day of pre-work on the three gaps above. The frontend needs UX design before coding can start. Phase 0 has no blockers at all.
