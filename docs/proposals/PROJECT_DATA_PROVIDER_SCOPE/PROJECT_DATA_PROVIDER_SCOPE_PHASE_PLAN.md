# Project Data Provider Scope Phase Plan

## Summary

This plan sequences the approved decisions in [Project Data Provider Scope](./PROJECT_DATA_PROVIDER_SCOPE.md). Shape Shifter will register providers and their schemas, bind each project to one provider-schema pair, and derive Change Request identity scopes from the saved project. The production scope switch is separate operational work, planned in [Move Existing Projects To Provider-Schema Scopes](../CHANGE_REQUEST_INGESTER/CUTOVER_AND_DEPLOYMENT/PROJECT_PROVIDER_SCOPE_CUTOVER.md).

## Problem

Change Request runs currently use a project-name scope. That scope changes with a project rename and keeps records from the same provider schema in separate identity namespaces. A provider-only scope would also be too broad when one provider delivers data with different `EntityConfig.keys`. The provider code is optional, and the ingest request can supply the code and override the scope. The new scope must come from a stable provider-schema binding.

## Scope

This plan covers the curated provider-schema registry, project creation and save rules, project validation, the provider-schema picklist, Change Request runtime inputs, fixed provider reconciliation, business-key validation, output metadata, and the remaining Change Request entry-point work.

It does not create SEAD provider rows, add a second business-key declaration, redesign FK linking, assign provider-schema pairs to existing projects, decide the treatment of existing SIMS identities, or derive scopes from mutable projects or arbitrary datasets. Phase 3 derives a `business_id` from `EntityConfig.keys`; broader FK use belongs to issue #507. The project assignments, identity decision, per-schema key review, and per-project enablement belong to [Move Existing Projects To Provider-Schema Scopes](../CHANGE_REQUEST_INGESTER/CUTOVER_AND_DEPLOYMENT/PROJECT_PROVIDER_SCOPE_CUTOVER.md).

## Current Position

- The reviewed `mal` registry and project binding checks are implemented, but the repository's current project files have no populated provider-schema pair.
- The Change Request runtime currently uses `sead-change-request:{project_name}` unless a runtime scope override is supplied. Its provider lookup uses the code supplied in submission context.
- The current provider lookup cannot resolve `data_provider` against the stock authority-service configuration described in the proposal. Change Request does not read a project's fixed provider row or `EntityConfig.keys`; its SIMS serializer uses every nonempty row field.

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

Make Change Request validation and ingestion use the authorized saved project's provider-schema pair, scope, fixed SEAD provider row, and declared business keys.

**Focus**

- Load the authorized project for each run and prevent request metadata or runtime overrides from selecting its provider, schema, or scope.
- Require exactly one fixed `data_provider` row in the saved project, with `data_provider_id` as `public_id`; verify the operator-entered ID/code pair against SEAD before SIMS and keep the target row lookup-only.
- Derive `business_id` from ordered `EntityConfig.keys`; reject missing, blank, or duplicate keys within a transformed delivery and incompatible key meaning across projects sharing a provider-schema pair before any SIMS call.
- Return the effective scope and run ID in the response and bundle manifest.

**Depends On**

- Phase 2 project binding and Phase 1 registry lookup.
- Review of a provider schema's declared keys before its first live run, establishing that repeated keys across deliveries name the same source entity.

**Outputs**

- A provider-schema-scoped Change Request path validated before production cutover.
- A response and bundle that identify the SIMS scope and run that produced them.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-4`) The saved provider-schema pair selects the SIMS scope, while the authorized project supplies the fixed provider row; caller-supplied project, provider, schema, and scope values cannot override them, and the response and manifest contain the effective scope and run ID.
- `PH3-AC-2` (from `P-AC-5`) A missing or unregistered saved pair fails before an identity request, file write, or target-database access.
- `PH3-AC-3` (from `P-AC-6`) The authorized project's single fixed provider row supplies an operator-reconciled `data_provider_id`; its ID and code match one existing SEAD provider before SIMS, and the bundle emits exactly one lookup-only provider row.
- `PH3-AC-4` (from `P-AC-7`) `EntityConfig.keys` supplies the tracked business keys and a deterministic `business_id`. Missing, blank, or duplicate keys in the transformed delivery, or incompatible key meaning within a provider-schema scope, block all SIMS calls; changed meaning requires a new schema code or explicit identity migration.

**Validation Milestones**

- `VM-4` Authorized and tampered requests show that the saved project controls scope and the fixed provider row, and invalid pairs cause no side effects (`PH3-AC-1`, `PH3-AC-2`).
- `VM-5` Fixed provider-row reconciliation, pre-SIMS key validation, response metadata, and bundle output meet `PH3-AC-1`, `PH3-AC-3`, and `PH3-AC-4` while preserving the one-provider-row and one-submission-row bundle contract.

**Task-Plan Handoff**

- Sources: `P-AC-4` through `P-AC-7`. Preserve one scope per provider-schema pair, `provider://<provider-code>/<provider-schema>`, no caller override, and lookup-only target-provider data. Read the fixed provider row and ordered keys only from the authorized saved project. Validate the full transformed delivery before any SIMS call. Repeated keys across deliveries mean the same source entity; review that promise for each schema before enabling it.

**Readiness**

Ready for a task plan.

### Phase 4: Remaining Change Request Development Work

**Goal**

Close the development gaps left after Phase 3 in the Change Request entry points and validation coverage.

**Focus**

- Require an authorized saved project on the project-independent Data Ingestion page, or exclude the Change Request ingester there. The page has no project selector, so the ingester either runs against an unrelated selected project or finds no project at all.
- Extend response and manifest parity coverage to the `inline_staging` strategy, which carries the same scope and run ID fields as the other two strategies but has no dedicated assertion.
- Keep project requirement and blocked-key guidance visible in both entry points so an operator sees why a run cannot start.

**Depends On**

- Phases 1–3 and their validation milestones.
- No cutover decision. The scope switch is planned in [Move Existing Projects To Provider-Schema Scopes](../CHANGE_REQUEST_INGESTER/CUTOVER_AND_DEPLOYMENT/PROJECT_PROVIDER_SCOPE_CUTOVER.md).

**Outputs**

- Change Request entry points that cannot run without an authorized saved project.
- Parity coverage for all three deploy strategies.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-4`) No Change Request validate or ingest route accepts a run without an authorized saved project, including the project-independent Data Ingestion page.
- `PH4-AC-2` (from `P-AC-5`) A run started without an authorized project, or with an unresolved saved pair, fails before any identity request, file write, or target-database access.
- `PH4-AC-3` (from `P-AC-4`) Response, in-memory artifact, and emitted manifest agree on the effective scope and run ID for `inline_insert`, `copy_csv`, and `inline_staging`.

**Validation Milestones**

- `VM-6` Entry-point tests show every Change Request route requires an authorized project and produces no side effects when it is absent (`PH4-AC-1`, `PH4-AC-2`).
- `VM-7` Parity checks cover all three deploy strategies on scope and run ID (`PH4-AC-3`).

**Task-Plan Handoff**

- Sources: `P-AC-4`, `P-AC-5`. Start from the Phase 3 behavior: the route already authorizes a top-level `project_name` and fails closed on an unresolved pair. Decide per entry point whether to add a project selector or to hide the ingester, and record that choice in the phase task plan. Provider assignments, identity treatment, and the per-schema key review are out of scope here; they belong to the cutover proposal.

**Readiness**

Ready for a task plan.

## Cross-Phase Rules

- Keep `provider://<provider-code>/<provider-schema>` stable and unique for each registered pair; never use `scope_uuid` or a target `data_provider_id` as the scope input.
- Keep pair validation local and deterministic. SIMS and target-database calls belong to ingestion, after saved-project checks.
- Preserve the lookup-only target `data_provider` contract and one provider row plus one submission row per bundle; the trusted project fixed row supplies the provider ID.
- Validate every tracked business key from `EntityConfig.keys` before SIMS. A repeated key across deliveries reuses identity within the same scope; a duplicate within one transformed entity table blocks the run.
- Keep existing project-scope behavior only until an explicit cutover decision. After cutover, fail closed instead of falling back to the project name. The switch itself is planned in [Move Existing Projects To Provider-Schema Scopes](../CHANGE_REQUEST_INGESTER/CUTOVER_AND_DEPLOYMENT/PROJECT_PROVIDER_SCOPE_CUTOVER.md), not in a development phase.
- Treat direct project-file edits as repository-reviewed changes; application save checks alone cannot prevent them. Live project files under `data/` are deployment data, so a cutover edit is applied while ingestion for that project is stopped.

## Validation Strategy

Validate registry and project rules in isolation first (`VM-1` through `VM-3`). Then validate trusted project input, the fixed provider ID/code against SEAD, keys before SIMS, and emitted scope/run metadata in Change Request runs (`VM-4`, `VM-5`). Then close the remaining entry-point and strategy-parity gaps (`VM-6`, `VM-7`). Project assignments, the identity treatment decision, the per-schema key review, and per-project enablement are validated by the cutover record described in [Move Existing Projects To Provider-Schema Scopes](../CHANGE_REQUEST_INGESTER/CUTOVER_AND_DEPLOYMENT/PROJECT_PROVIDER_SCOPE_CUTOVER.md), not by this plan.
