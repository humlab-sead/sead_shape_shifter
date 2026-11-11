# AI Project Advisor — Phase Plan

**Date:** November 8, 2026  
**Status:** Delivery plan; implementation has not started  
**Source:** [AI Project Advisor proposal](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md), revised November 8, 2026  
**Repository baseline:** `staging` commit `95c56d8ccb779225ee3104c3035c192780519642`

## Summary

Deliver the explanation MVP before adding investigation tools. Establish input provenance, claim-support rules, provider disclosure, and reviewed evaluation scenarios first; then validate the harness and build the product. Later phases add bounded investigations, resolve whether generated experiments are needed, and introduce proposal and apply as separate capabilities.

This plan groups the proposal's nine delivery steps into seven phases: evaluation and framework spikes share Phase 2, and MVP backend and frontend share Phase 3 with an internal validation gate. These are sequencing choices, not changes to the proposal. Later capabilities remain disabled until their own acceptance criteria pass.

## Problem

Project authors need explanations grounded in the configuration and data actually checked. Existing validation and foreign-key diagnostics provide useful inputs, but lack the unified provenance, claim controls, provider policies, and enforceable execution budgets required for the Advisor.

## Scope

Cover the proposal's full delivery sequence, starting with `S1`/`S2` × `G1`/`G4` using `E1` and authorized `E2`. Extend to evidence-backed verify/review, development-environment handoff through MCP, controlled experiments where justified, validated proposals, and approved apply.

Exclude general shell or IDE-agent access, silent project changes, identity allocation, undocumented SEAD policy, staffing, and release dates. Exact commands, implementation files, test cases, and task tracking belong in phase task plans. This document does not replace the archived phase plan or change the source proposal.

## Current Position

- The revised proposal records the staging review and defines `P-AC-1` through `P-AC-16`. No Advisor implementation is claimed by this plan.
- Preview and validation already execute the pipeline. Results expose validation mode and completion coverage, but lack the configuration digest and run identity needed for Advisor input compatibility.
- Integrity inspection, link baseline reproduction, retained link snapshots, and alternative-key trials are reuse candidates. Their existing output caps and projected merge budgets do not establish full-operation time, memory, or concurrency guarantees.
- General project normalization writes shared caches. Investigation must use an isolated path or disable those writes.
- Pydantic AI is preferred pending its spike. Generated-code compatibility and isolation are a separate later decision. Deployment availability and source freshness must be reconfirmed during foundation work.

## Phase Plan

### Phase 1: Grounding contracts and reviewed scenarios

**Goal**

Define the contracts and evaluation standard needed to implement the MVP without inventing project facts or overstating results.

**Focus**

- Confirm deployment inputs and reusable diagnostics against the recorded baseline.
- Define per-result provenance, saved/editor input compatibility, referenced-input identity, validation coverage, citation identity, claim-support combinations, and context-size behavior.
- Curate the initial versioned knowledge pack and define external-source provenance and refresh handling.
- Define provider-specific disclosure and record retention; select the local/hosted providers to test and the governed Advisor store.
- Freeze maintainer-reviewed MVP scenarios, accepted alternatives, evidence requirements, repeated-run counts, and pass thresholds before implementation.

**Depends On**

- The revised source proposal and access to its relevant configuration, target-model, and SEAD/SIMS sources.
- A designated maintainer who can approve expected findings and the evaluation standard.

**Outputs**

Reviewed contracts, initial knowledge-pack content, frozen MVP fixtures, evaluation policy, provider/store decisions, and a deployment-specific reuse inventory. No production Advisor behavior is delivered.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-2`, `P-AC-5`, `P-AC-6`, `P-AC-14`) Contracts distinguish saved/editor inputs, changed references, unavailable provenance, partial/sample coverage, valid support labels, and truncated context.
- `PH1-AC-2` (from `P-AC-4`, `P-AC-12`, `P-AC-13`) Disclosure, governed storage, retention, and export handling are defined for the selected providers; unresolved categories are withheld.
- `PH1-AC-3` (from `P-AC-1`, `P-AC-3`, `P-AC-11`) Reviewed fixtures cover the four MVP scope/goal cells, clarification, acceptable alternatives, support requirements, and predeclared repeat-run/pass thresholds. Skill comparison provenance is specified without making skill agreement the oracle.
- `PH1-AC-4` (from `P-AC-9`, `P-AC-16`) The inventory identifies compatible existing diagnostics, missing controls, selected spike providers, and assumptions needing deployment verification.

**Validation Milestones**

- `VM-1` Contract and fixture review accepts all four phase criteria (`PH1-AC-1`, `PH1-AC-2`, `PH1-AC-3`, `PH1-AC-4`) and records unresolved decisions with their required resolution points.

**Task-Plan Handoff**

Use the proposal's Planning Handoff as fixed input. Scope the task plan to contracts, curation, and fixtures; do not implement the Advisor or its tool loop. Source questions 1–4 and 10 must be resolved here for the MVP; exact-replay retention can be completed before Phase 4.

**Readiness**

Requires a named decision: designate the maintainer who approves fixture expectations and evaluation thresholds. Provider, provenance, and storage choices are outputs of this phase, not assumed decisions.

### Phase 2: Minimal evaluation runner and framework spike

**Goal**

Establish reproducible evaluation and select the harness before production integration.

**Focus**

- Build and exercise the minimal runner against the frozen scenarios before evaluating the candidate harness.
- Test structured responses, typed dependencies, bounded service-backed function tools, and the selected local/hosted providers.
- Demonstrate MCP compatibility through a limited adapter prototype; keep the embedded call path in-process.
- Compare LangGraph only where a required behavior could change the harness choice. Keep generated-code isolation outside this spike.

**Depends On**

- Phase 1 contracts, fixtures, thresholds, provider policy, and selected provider configurations.

**Outputs**

A versioned evaluation runner, recorded comparison runs, and a documented harness decision. The MCP prototype is not a deployed investigation interface.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-11`) The runner uses pinned fixture versions, scores accepted alternatives consistently, records repeated results and skill-run provenance, and detects deliberate contract violations.
- `PH2-AC-2` (from `P-AC-16`, `P-AC-9`) The spike demonstrates structured project responses, injected dependencies, bounded authorized service operations, selected providers, and the MCP adapter/client compatibility required by the proposal. It records Pydantic AI as selected or explains why LangGraph is necessary.
- `PH2-AC-3` (from `P-AC-4`, `P-AC-12`, `P-AC-16`) Spike runs obey disclosure policy and local-only behavior, do not mutate project state, and make no generated-code sandbox decision.

**Validation Milestones**

- `VM-2` Runner verification and the framework comparison report cover `PH2-AC-1`, `PH2-AC-2`, and `PH2-AC-3`; the harness decision is recorded before production model/tool integration.

**Task-Plan Handoff**

Use reviewed fixtures and ordinary backend services. Do not build a second agent loop or production MCP exposure. Resolve source question 5 through the spike; retain framework/provider versions and observed limitations.

**Readiness**

Requires Phase 1 outputs, including the selected providers and approved evaluation/disclosure policies. No harness choice is treated as settled before `VM-2`.

### Phase 3: Explanation MVP and user evaluation

**Goal**

Deliver usable, grounded explain/recommend chat without investigation tools or project changes.

**Focus**

- Assemble `E1` and authorized `E2`; implement input compatibility, coverage limits, claim-support checks, citations, redaction, and bounded clarification.
- Integrate the selected harness and governed conversation/audit records.
- Pass backend scenarios before frontend user evaluation. Then provide navigation to cited inputs, original validation results, historical/stale labels, and context completeness.
- Record user-evaluation findings before extending the product to tool-driven investigations.

**Depends On**

- Phases 1 and 2 contracts, knowledge pack, runner, policies, governed store, and harness decision.
- A frontend form and interaction decision: tab/drawer, response/streaming behavior, and citation navigation.

**Outputs**

The explanation MVP, passing backend evaluation, and recorded user-evaluation results with the decision on readiness to extend.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-1`, `P-AC-3`, `P-AC-11`) All four MVP scope/goal cells and bounded clarification satisfy the predeclared quality thresholds without project configuration changes.
- `PH3-AC-2` (from `P-AC-5`, `P-AC-6`, `P-AC-14`) Context includes authorized deployment state when available, checks per-result inputs, handles changed references and incompatible saved/editor results, preserves validation mode/completion coverage, and exposes context truncation and limitations.
- `PH3-AC-3` (from `P-AC-2`, `P-AC-6`) Direct observations bind to recorded fields; invalid support combinations and unknown citations are rejected or handled as specified. Original validation results and duplicate message identities remain distinguishable.
- `PH3-AC-4` (from `P-AC-4`, `P-AC-12`) Questions, history, records, and logs obey disclosure/retention rules and project access controls. Local-only mode makes no outbound provider calls; project state remains unchanged.
- `PH3-AC-5` (from `P-AC-1`, `P-AC-2`, `P-AC-3`, `P-AC-6`, `P-AC-14`) The UI exposes clarification, citations, support/scope, original reports, and historical/incomplete context. User-evaluation findings have recorded dispositions before Phase 4 begins.

**Validation Milestones**

- `VM-3` Backend contract and model evaluations pass `PH3-AC-1`, `PH3-AC-2`, `PH3-AC-3`, and `PH3-AC-4` before frontend user evaluation.
- `VM-4` End-to-end user evaluation covers `PH3-AC-5` and confirms the backend guarantees remain visible in the product. Unresolved findings that prevent safe or useful advice block expansion.

**Task-Plan Handoff**

Preserve mapper/directive rules and existing validator payloads. Missing or stale results never trigger an unavailable probe. Resolve the MVP portion of source question 3 and the frontend decisions in question 11 before implementation of the affected behavior.

**Readiness**

Requires Phases 1–2 outputs and the frontend interaction decision. The combined phase retains a mandatory backend-to-user-evaluation gate.

### Phase 4: Bounded investigations, MCP, and handoff

**Goal**

Enable evidence-backed verify/review through authorized source reads and approved host probes.

**Focus**

- Reuse compatible integrity/link diagnostics, retained snapshots, and key trials; add source retrieval, bounded differential operations, and cross-entity scans as supported operations.
- Select and prove enforceable limits across loading, upstream normalization, trials, serialization, and simultaneous requests before enabling each Tier 2 probe.
- Expose the same authoritative services through in-process functions and an authenticated external MCP adapter.
- Persist artifacts and export investigation packets. Enable history comparisons only when authorized snapshots have sufficient provenance; otherwise state the limitation.

**Depends On**

- Phase 3 user-evaluation gate and passing regression suite.
- Recorded execution mechanism and numerical budgets, MCP clients/exposure/authentication decisions, and input-retention/exact-replay policy.

**Outputs**

Individually gated Tier 1/2 tools, external MCP access for supported deployments, provenance-bound artifacts, and governed session export. Unsupported probes and history comparisons remain disabled.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-7`, `P-AC-8`, `P-AC-11`) Supported source reads, probes, differential runs, and scans return scoped artifacts with actual inputs, limitations, and replay status. Evaluations cover false positives, wider defects, and causes ruled out; entity-only results never become unscanned project-wide conclusions.
- `PH4-AC-2` (from `P-AC-4`, `P-AC-9`, `P-AC-12`) Both adapters use the same services with per-call caller/project checks, disclosure filtering, artifacts, and mutation protection. Reused diagnostics pass these controls; replacements have a recorded rationale. Shared pipeline caches are disabled or isolated.
- `PH4-AC-3` (from `P-AC-10`, `P-AC-12`) Each enabled Tier 2 probe demonstrates full-operation time/memory and query limits, termination, applicable query cancellation, cleanup, and concurrent-request bounds. Exhaustion reports remaining questions and offers explicit continuation.
- `PH4-AC-4` (from `P-AC-6`, `P-AC-7`, `P-AC-13`) Export contains the question, manifest, claims, citations, artifacts, conclusions, disclosure handling, and reproduction limits. Expired/unretained snapshots and unavailable history are explicit and cannot support claims of exact replay or pre-existing failure.

**Validation Milestones**

- `VM-5` Fixture-based investigations and adapter comparisons pass `PH4-AC-1`, `PH4-AC-2`, and `PH4-AC-4`, including cross-project and prompt-injection cases and retained-input trial consistency.
- `VM-6` Execution-limit, cancellation, cleanup, and concurrency checks pass `PH4-AC-3` and mutation/cache checks in `PH4-AC-2` before each probe is enabled.

**Task-Plan Handoff**

Keep MCP transport separate from tool ownership. Existing merge estimates are admission checks, not proof of hard limits. Resolve source questions 3, 7, and 8 before exposure. Resolve question 9 before history comparisons; its absence must not block unrelated tools.

**Readiness**

Requires Phase 3 outputs and named execution, retention, and MCP decisions. Tool-specific task plans must not assume the existing troubleshooters already meet every Advisor guarantee.

### Phase 5: Controlled-experiment decision and validation

**Goal**

Establish whether approved host tools suffice or isolated generated experiments are justified and compatible.

**Focus**

- Run the separate compatibility/isolation spike against a representative validator and its actual dependencies.
- Prefer approved-host-tool orchestration where it answers the required question. Record that outcome without introducing a generated-code runtime.
- If generated execution is selected, prove its restrictions, explicit input delivery, resource enforcement, and artifact behavior before enabling Tier 3.

**Depends On**

- Phase 4 approved operations, evaluation scenarios, artifacts, and execution controls.
- An experiment question that demonstrates the need to compare the two execution approaches.

**Outputs**

A documented host-tool-versus-isolated-runtime decision and compatibility results. Tier 3 is enabled only if selected and proven; a host-tool outcome completes this phase without generated execution.

**Acceptance Criteria**

- `PH5-AC-1` (from `P-AC-7`, `P-AC-9`, `P-AC-11`) The chosen approach reproduces a representative validator result with the required dependencies and records actual inputs, outputs, scope, and limitations. An unsupported interpreter subset is not accepted as application compatibility.
- `PH5-AC-2` (from `P-AC-4`, `P-AC-10`, `P-AC-12`) If generated execution is selected, checks demonstrate no direct filesystem, environment, database, or network access, bounded execution, approved explicit input delivery, and no prohibited mutations. If it is not selected, Tier 3 remains disabled.

**Validation Milestones**

- `VM-7` Compatibility comparison and, where selected, isolation/resource checks cover `PH5-AC-1` and `PH5-AC-2`. The recorded decision determines which capability is eligible for release.

**Task-Plan Handoff**

Resolve source question 6. This spike does not reopen the harness choice. Do not equate a host-tool decision with authorization for arbitrary generated code, or make Tier 3 mandatory for subsequent proposals.

**Readiness**

Requires Phase 4 outputs and selection of the representative experiment. The isolation mechanism is a spike output; production Tier 3 work requires the recorded decision and passing checks.

### Phase 6: Validated proposal generation

**Goal**

Produce reviewable, validator-checked configuration changes without applying them.

**Focus**

- Add `G5` using current compatible inputs and the application-managed proposal lifecycle.
- Store the exact diff, base/candidate digests, candidate validation version/results, provenance, and approval state.
- Show the stored diff and validation limits. Separate proposal drafting, review, and approval from the later apply operation.

**Depends On**

- Phases 4–5 investigation/evaluation gates and the recorded experiment decision; generated execution itself is not required when host tools were selected.
- A fixed proposal-state and approval-binding contract from the source proposal.

**Outputs**

Stored, inspectable proposals with validated candidates and approval records. Applying changes remains unavailable.

**Acceptance Criteria**

- `PH6-AC-1` (from `P-AC-11`, `P-AC-15`) Proposed candidates are checked before display, with exact diff, base/candidate digests, validation results/version, and state recorded. Invalid candidates are not presented as validated proposals.
- `PH6-AC-2` (from `P-AC-2`, `P-AC-6`, `P-AC-12`, `P-AC-15`) The displayed proposal binds to its recorded inputs and candidate. Changed proposals or validation cannot retain approval for the old change; generating, inspecting, or approving a proposal does not apply it.

**Validation Milestones**

- `VM-8` Proposal and lifecycle evaluations cover `PH6-AC-1` and `PH6-AC-2`, including invalid candidates, changed digests/results, and preservation of original project state.

**Task-Plan Handoff**

Use application records for approval, independently of framework pause/deferred-tool signals. Preserve normal project validation and mapper rules. Do not introduce the apply endpoint in this phase.

**Readiness**

Requires Phases 4–5 outputs and a finalized proposal lifecycle contract; no automatic approval or application is assumed.

### Phase 7: Approved apply and recovery

**Goal**

Apply only the exact current, authorized, approved proposal and provide the agreed recovery path.

**Focus**

- Add `G6` as a deterministic application operation through the normal project update path.
- Recheck caller/project access, approval binding, stored diff, base and candidate digests, and validation freshness.
- Record the apply outcome and recovery details; block stale or changed proposals and require renewed review.

**Depends On**

- Phase 6 passing proposal/lifecycle evaluation.
- A recovery mechanism and approval-validity policy, resolved before apply implementation.

**Outputs**

Explicitly approved apply with recorded results, stale-state rejection, and demonstrated recovery.

**Acceptance Criteria**

- `PH7-AC-1` (from `P-AC-12`, `P-AC-15`) The apply operation checks authorization, approved state, exact-change binding, and configuration/validation freshness, then applies only that stored change. Investigation permission or a framework signal cannot authorize apply.
- `PH7-AC-2` (from `P-AC-11`, `P-AC-15`) Stale, changed, unauthorized, or approval-expired requests cannot apply. The defined failure and recovery scenarios preserve or restore the expected project state, with recorded outcomes.

**Validation Milestones**

- `VM-9` End-to-end approved-apply, rejection, failure, and recovery evaluations cover `PH7-AC-1` and `PH7-AC-2`; earlier explanation/investigation guarantees pass regression checks.

**Task-Plan Handoff**

Resolve source question 12 before implementing apply. Keep recovery and approval records in application control; approval remains bound to the exact change and its validation.

**Readiness**

Requires Phase 6 outputs and the named recovery and approval-validity decisions.

## Cross-Phase Rules

1. Preserve the proposal's scope/evidence separation and mapper/directive, validation-code, identity-authority, and provider-binding contracts. Unavailable evidence narrows claims.
2. Input provenance records what was actually checked. Later assembly never assigns current identifiers to unknown historical inputs; exact replay requires retained originals.
3. Application services own caller/project access, disclosure, resource limits, and records. In-process adapters and MCP share those guarantees; generated text cannot expand permissions.
4. Keep the validator's original report and execution coverage separate from Advisor interpretation. Citation existence does not prove semantic support.
5. Retain the existing editor and troubleshooters while adding the Advisor. Reused behavior needs parity checks and the additional controls before exposure; unsupported capabilities remain unavailable.
6. Promote each capability only after its relevant milestones pass. New phases add regression fixtures for delivered capabilities; they do not relax earlier thresholds.
7. Store Advisor records only under the agreed access/retention rules. Investigation never mutates project, source, provider, materialized, or shared runtime state. G6 is the sole later approved-change path in this plan.

## Validation Strategy

Use deterministic contract checks for provenance, coverage, support labels, citations, disclosure, and mutation protection. Use frozen maintainer-reviewed scenarios and repeated model runs for explanation quality and claim support. Record skill comparison inputs and versions as supporting data. Require backend acceptance before user evaluation and full-operation control checks before probe exposure.

The source-criterion coverage below identifies the delivery gates; Phase 1 and Phase 2 define and verify supporting contracts and evaluation machinery, rather than claiming product completion.

| Source criteria | Delivery coverage |
|-----------------|-------------------|
| `P-AC-1`, `P-AC-3` | `PH3-AC-1`, `PH3-AC-5`; `VM-3`, `VM-4` |
| `P-AC-2` | `PH3-AC-3`, `PH3-AC-5`; `VM-3`, `VM-4`; maintained by `PH6-AC-2` |
| `P-AC-4`, `P-AC-5`, `P-AC-6`, `P-AC-14` | `PH3-AC-2`, `PH3-AC-3`, `PH3-AC-4`, `PH3-AC-5`; `VM-3`, `VM-4`; extended by `PH4-AC-2`, `PH4-AC-4` |
| `P-AC-7`, `P-AC-8`, `P-AC-9`, `P-AC-10` | `PH4-AC-1`, `PH4-AC-2`, `PH4-AC-3`, `PH4-AC-4`; `VM-5`, `VM-6`; controlled experiments add `VM-7` where selected |
| `P-AC-11` | `PH1-AC-3`, `PH2-AC-1`, and phase-specific evaluations throughout `VM-1`–`VM-9` |
| `P-AC-12` | `PH3-AC-4`, `PH4-AC-2`, `PH4-AC-3`, `PH5-AC-2`, `PH6-AC-2`, `PH7-AC-1` |
| `P-AC-13` | `PH4-AC-4`; `VM-5` |
| `P-AC-15` | `PH6-AC-1`, `PH6-AC-2`, `PH7-AC-1`, `PH7-AC-2`; `VM-8`, `VM-9` |
| `P-AC-16` | `PH2-AC-2`, `PH2-AC-3`; `VM-2` |

At each exit, retain the phase-criterion-to-milestone results and update readiness before creating the next implementation task plan. If a spike fails or a policy remains unresolved, keep the affected capability disabled and record the required decision; do not treat phase ordering as evidence that a gate has passed.
