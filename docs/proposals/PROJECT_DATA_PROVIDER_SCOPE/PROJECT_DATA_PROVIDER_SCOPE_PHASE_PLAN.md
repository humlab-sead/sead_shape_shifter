# Project Data Provider Scope Phase Plan

## Summary

This plan sequences the approved decisions in [Project Data Provider Scope](./PROJECT_DATA_PROVIDER_SCOPE.md). Shape Shifter will register providers and their schemas, bind each project to one provider-schema pair, and derive Change Request identity scopes from the saved project. The production scope switch follows validation of keys within each selected scope and a decision about existing SIMS identities.

## Problem

Change Request runs currently use a project-name scope. That scope changes with a project rename and keeps records from the same provider schema in separate identity namespaces. A provider-only scope would also be too broad when one provider delivers data with different `EntityConfig.keys`. The provider code is optional, and the ingest request can supply the code and override the scope. The new scope must come from a stable provider-schema binding.

## Scope

This plan covers the curated provider-schema registry, project creation and save rules, project validation, the provider-schema picklist, Change Request runtime inputs and output metadata, and the cutover from project scopes to provider-schema scopes.

It does not create SEAD provider rows, choose or serialize business-key columns, or derive scopes from mutable projects or arbitrary datasets. The key contract for each provider schema and target provider-ID lookup remain prerequisites to the ingestion phase.

## Current Position

- Project metadata has an optional `data_provider_code` and no `provider_schema`; the repository's current project files have no populated provider-schema pair.
- Project validation does not check the pair, and the raw-YAML save path does not reject identity changes before writing.
- The Change Request runtime currently uses `sead-change-request:{project_name}` unless a runtime scope override is supplied. Its provider lookup uses the code supplied in submission context.
- The current provider lookup cannot resolve `data_provider` against the stock authority-service configuration described in the proposal.

## Phase Plan

### Phase 1: Curated Provider Registry

**Goal**

Provide one reviewed provider record with a fixed SIMS scope name for each approved provider schema.

**Focus**

- Add the shared registry and a read interface for provider and schema selection.
- Validate unique provider codes, unique schema codes within a provider, and unique scope names; require `scope_name` to equal `provider://<provider-code>/<provider-schema>`.
- Preserve used pair-to-scope assignments through registry review; do not require live SIMS checks for project validation.

**Depends On**

- The proposal's decision that Shape Shifter curates provider-schema pairs and SIMS owns scopes.

**Outputs**

- A locally readable registry and provider-schema list that later phases can use without a database or SIMS request.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) Provider `mal` has two distinct registered scopes, `provider://mal/archeobotany/arbodat-pilot` and `provider://mal/radiocarbon/strucke-pilot`; duplicate provider codes, duplicate schema codes within a provider, duplicate scopes, and mismatched names are rejected. BugsCEP is absent from the initial registry.
- `PH1-AC-2` (from `P-AC-1`) A provider-schema pair or scope name already bound to a project cannot be reassigned to a different provider or key contract.

**Validation Milestones**

- `VM-1` Registry checks accept the two `mal` schemas and reject duplicate, mismatched, and reassigned identities (`PH1-AC-1`, `PH1-AC-2`).

**Task-Plan Handoff**

- Source: `P-AC-1`. Keep one code-reviewed file for `mal` with display name `MAL` and the two approved pilot schemas; expose only a read interface and treat each `scope_name` as a stable contract. SIMS may create a named scope on first resolution. No open proposal decision blocks this phase.

**Readiness**

Ready for a task plan.

### Phase 2: Project Binding And Save Rules

**Goal**

Make the provider-schema pair a validated initial project assignment that application saves cannot change.

**Focus**

- Require a registered pair for new projects and allow one initial assignment for existing unbound projects.
- Add provider-schema selection and a fixed-pair display to the project UI.
- Reject changes or removal of either code before every application project-save path writes, including raw YAML and backup restore.

**Depends On**

- Phase 1 registry lookup and provider-schema list.

**Outputs**

- Project metadata and application save paths that preserve the assigned pair.
- A validation result for a missing or unregistered pair.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-2`) New projects require one registered provider-schema pair; existing unbound projects can receive an initial pair, and project validation rejects missing or unregistered pairs.
- `PH2-AC-2` (from `P-AC-3`) Multiple projects can use one pair, and one provider can have several schemas; every application save path rejects a changed or removed assigned code or schema before writing.
- `PH2-AC-3` (from `P-AC-5`) A missing or unregistered pair fails project validation without a SIMS or target-database request.

**Validation Milestones**

- `VM-2` Project creation, initial assignment, shared-pair binding, and validation meet `PH2-AC-1` and `PH2-AC-3`.
- `VM-3` Metadata, raw-YAML, and restore saves leave both assigned codes unchanged on rejected writes (`PH2-AC-2`).

**Task-Plan Handoff**

- Sources: `P-AC-2`, `P-AC-3`, `P-AC-5`. Preserve deterministic validation and block changes on the server, not only in the UI. Assigning the approved pairs to existing project files belongs to Phase 4; no project assignment value is needed to plan this phase.

**Readiness**

Ready for a task plan.

### Phase 3: Provider-Scoped Change Request Integration

**Goal**

Make Change Request validation and ingestion use the authorized saved project's provider-schema pair, scope, and SEAD provider lookup.

**Focus**

- Load the authorized project for each run and prevent request metadata or runtime overrides from selecting its provider, schema, or scope.
- Resolve the target `data_provider_id` from SEAD through the chosen lookup path; keep the target `data_provider` row lookup-only.
- Use declared keys that are unique within the selected provider-schema scope and return the effective scope and run ID in the response and bundle manifest.

**Depends On**

- Phase 2 project binding and Phase 1 registry lookup.
- Decisions on the target provider-ID lookup and on declared keys that are unique across deliveries using each provider schema.

**Outputs**

- A provider-schema-scoped Change Request path validated before production cutover.
- A response and bundle that identify the SIMS scope and run that produced them.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-4`) The saved provider-schema pair selects the SIMS scope, while the provider code selects target-provider lookup; caller-supplied project, provider, schema, and scope values cannot override them, and the response and manifest contain the effective scope and run ID.
- `PH3-AC-2` (from `P-AC-5`) A missing or unregistered saved pair fails before an identity request, file write, or target-database access.
- `PH3-AC-3` (from `P-AC-6`) Exactly one target `data_provider` row is derived from SEAD resolution, with no target ID or row data taken from the registry or project metadata.
- `PH3-AC-4` (from `P-AC-7`) Tracked identity work is blocked without a declared key contract unique within its provider-schema scope; a changed key meaning requires a new schema code or explicit identity migration, with no project-name fallback.

**Validation Milestones**

- `VM-4` Authorized and tampered requests show that the saved project controls scope and provider lookup, and invalid pairs cause no side effects (`PH3-AC-1`, `PH3-AC-2`).
- `VM-5` Provider lookup, declared-key checks, response metadata, and bundle output meet `PH3-AC-1`, `PH3-AC-3`, and `PH3-AC-4` while preserving the existing one-provider-row and one-submission-row bundle contract.

**Task-Plan Handoff**

- Sources: `P-AC-4` through `P-AC-7`. Preserve one scope per provider-schema pair, `provider://<provider-code>/<provider-schema>`, no caller override, and lookup-only target-provider data. Before a task plan, choose the target provider-ID lookup and the key contract for each schema; the proposal leaves both open.

**Readiness**

Requires decisions on target provider-ID resolution and business keys within each provider-schema scope.

### Phase 4: Existing Projects And Scope Cutover

**Goal**

Move eligible projects to provider-schema scopes without silently abandoning earlier identities or changing the target bundle contract.

**Focus**

- Assign approved provider-schema pairs to existing unbound projects before enforcing new scopes; keep BugsCEP outside the initial registry and cutover.
- Decide and apply the treatment of identities under `sead-change-request:{project}` before switching those projects.
- Compare bundle and provider-lookup behavior with the prior path; defer the switch when assignments, keys, or identity treatment are unresolved.

**Depends On**

- Phases 1–3 and their validation milestones.
- Approved provider-schema assignments for existing projects and a decision to migrate or abandon existing project-scoped SIMS identities.

**Outputs**

- Projects eligible for provider-schema-scoped ingestion, with a recorded cutover decision for existing identities.
- A verified provider-schema-scope path with no project-name fallback after cutover.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-2`) Each project enabled for the new scope has one registered provider-schema assignment; BugsCEP is not enabled by the initial registry.
- `PH4-AC-2` (from `P-AC-4`) Cutover follows the approved treatment of existing project-scoped identities; enabled runs use only the assigned provider-schema scope and record it with the run ID.
- `PH4-AC-3` (from `P-AC-5`) An unresolved pair blocks a run before identity, file, or target-database side effects; it never falls back to a project scope.
- `PH4-AC-4` (from `P-AC-6`) The promoted path still derives one provider row and one submission row, with the provider target ID resolved from SEAD.
- `PH4-AC-5` (from `P-AC-7`) Key requirements are met within each enabled provider-schema scope before its switch.

**Validation Milestones**

- `VM-6` Existing-project assignments and the approved identity treatment are checked before any provider-schema scope switch (`PH4-AC-1`, `PH4-AC-2`, `PH4-AC-5`).
- `VM-7` Cutover checks confirm no project-scope fallback or side effects for blocked runs, and parity for provider and submission rows in completed bundles (`PH4-AC-2`, `PH4-AC-3`, `PH4-AC-4`).

**Task-Plan Handoff**

- Sources: `P-AC-2`, `P-AC-4` through `P-AC-7`. Name the existing projects and approved provider-schema assignments in the phase task plan. The decision to migrate or abandon old SIMS identities must precede that task plan; do not treat a new scope as an implicit migration.

**Readiness**

Requires a decision on existing SIMS identities and approved assignments for existing projects.

## Cross-Phase Rules

- Keep `provider://<provider-code>/<provider-schema>` stable and unique for each registered pair; never use `scope_uuid` or a target `data_provider_id` as the scope input.
- Keep pair validation local and deterministic. SIMS and target-database calls belong to ingestion, after saved-project checks.
- Preserve the lookup-only target `data_provider` contract and one provider row plus one submission row per bundle.
- Keep existing project-scope behavior only until an explicit cutover decision. After cutover, fail closed instead of falling back to the project name.
- Treat direct project-file edits as repository-reviewed changes; application save checks alone cannot prevent them.

## Validation Strategy

Validate registry and project rules in isolation first (`VM-1` through `VM-3`). Then validate trusted project input, target-provider lookup, keys within each provider-schema scope, and emitted scope/run metadata in Change Request runs (`VM-4`, `VM-5`). Before cutover, verify existing assignments and identity treatment, then compare the promoted bundle contract with the prior path while checking that blocked runs have no side effects (`VM-6`, `VM-7`).
