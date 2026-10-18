# Proposal: Bind Each Project To One Curated Provider Scope

## Status

- **Implemented** (Phase 1–4 development complete).
- Scope: provider-schema registry, project bindings, Change Request identity scope, and project-bound Change Request dispatch.
- Goal: make the provider-schema pair a curated, declared property of each project instead of deriving identity scope from an internal project name.
- Validation: Phase 4 V-1 through V-5 and its UI/backend regression gates passed; earlier-phase validation is recorded in the phase task plans.
- Remaining work: assign approved pairs to existing projects and cut over existing SIMS identities as described in the [project scope cutover](../../CHANGE_REQUEST_INGESTER/CUTOVER_AND_DEPLOYMENT/PROJECT_PROVIDER_SCOPE_CUTOVER.md).

## Summary

A project must declare one approved provider code and one provider-schema code. Shape Shifter owns a curated registry that names each pair's SIMS scope as `provider://<provider-code>/<provider-schema>`. SIMS continues to own scopes; it is not asked to own SEAD provider records. The Change Request ingester uses the pair bound to the saved project instead of `sead-change-request:{project_name}`. Projects using the same provider schema share a scope; different schemas from one provider can use different entity keys without colliding.

## Problem

The scope is part of the business key. `source_identity_keys` is unique per `(source_identity_uuid, key_type)`, and lookup is `(scope_uuid, entity_type, key_type, key_value)`, so a business key is only interpretable together with its scope. Today the Change Request ingester builds the scope from the project name (`_build_scope_name` in `backend/app/services/ingester_runtime.py`). The choice of scope has three consequences.

1. **Scope is unstable.** Project names are mutable internal labels. Renaming a project changes the scope and silently re-identifies every previously resolved record.
2. **Project scope is too narrow.** A provider that delivers the same logical record through two projects using one schema produces two Source Identities and, for `provider_owned` entities, two allocated aggregates. Resubmission and update workflows — the reason SIMS exists — then cannot find the earlier identity.
3. **Provider-only scope is too broad.** One provider can deliver different kinds of data whose `EntityConfig.keys` have different meanings. A single provider-wide scope could resolve unrelated records to one Source Identity when their entity type and key values happen to match.

The reviewed provider registry and project binding rules are implemented, but existing checked-in projects have no assigned provider-schema pair. Change Request still builds the scope from caller input and the project name, so it does not yet use the saved binding.

## Scope

- A curated registry owned by Shape Shifter: provider code, display name, and the provider-schema codes and SIMS scope names approved for that provider.
- Required `data_provider_code` and `provider_schema` values in project metadata, selected from the registry.
- One SIMS source scope per provider and provider-schema pair for Change Request runs.
- Enforcement at project validation, project save, and ingestion.

## Non-Goals

- Owning or editing SEAD `tbl_data_providers` rows from Shape Shifter. The provider entity stays `identity_tracking: reconciled` / `reconciliation: lookup-only` in `data/specs/sead_standard_model.yml`.
- Making different providers converge on one shared entity. That remains a reconciliation and review outcome.
- Teaching SIMS about SEAD data providers. SIMS keeps scopes only.
- Changing the business-key columns declared in `EntityConfig.keys` or redesigning FK linking. Phase 3 must validate and serialize those declared keys for SIMS; broader FK use of a computed `business_id` belongs to [issue #507](https://github.com/humlab-sead/sead_shape_shifter/issues/507).
- Creating scopes from mutable project names, individual submissions, or arbitrary datasets. A provider-schema code names a reviewed key contract that can be reused across projects.

## Current Behavior

| Concern | Current state |
|---|---|
| Project declaration | `ProjectMetadata` has provider-code and provider-schema fields, and the reviewed `mal` registry lists two pilot schemas; checked-in projects remain unassigned |
| Validation | Backend project validation checks the registered pair but does not require the fixed provider row |
| Ingestion gate | `sead_change_request` requires the code and fails when it does not resolve (`ingesters/sead_change_request/ingester.py`) |
| Resolution | The code is resolved through the reconciliation client, not a local registry |
| Scope | `sead-change-request:{project_name}` |
| Ingest request | The caller can supply `project_name` and `data_provider_code` in `submission_context`; `sims_scope_name` can override the runtime scope |
| Project save | Application saves reject a changed or removed assigned provider-schema pair; they do not yet protect the tracked key meaning |
| Bundle metadata | Exactly one `data_provider` row and one `submission` row are derived per run |

Provider resolution cannot succeed against a stock authority service: `data_provider` is absent from `sead_authority_service/config/entities.yml` and `config/identity_policy.yml`, and `src/reconcile.py` rejects an unknown query type. The fixed project row and target ID/code check replace that lookup for Change Request runs.

## Proposed Design

### Split ownership

- **SIMS owns scopes.** `scope_name` is the identity contract. SIMS assigns `scope_uuid`; it is never a registry or resolve input.
- **Shape Shifter owns the registry.** It maps each approved provider and provider-schema pair to a `scope_name`. The provider code identifies the expected SEAD provider when the fixed row is checked. The registry does not author SEAD rows.

### Provider registry

Store one YAML file per provider under a shared registry directory, mirroring the existing `GLOBAL_DATA_SOURCE_DIR` / `shared/data-sources` pattern: a new setting such as `GLOBAL_DATA_PROVIDER_DIR`, resolved under the application root, plus a small service and a read endpoint for the picklist. Each provider file lists its approved schemas. The initial registry contains `mal` (`MAL`) with two pilot schemas; BugsCEP is excluded.

```yaml
code: mal
name: MAL
schemas:
  - provider_schema: archeobotany/arbodat-pilot
    scope_name: provider://mal/archeobotany/arbodat-pilot
  - provider_schema: radiocarbon/strucke-pilot
    scope_name: provider://mal/radiocarbon/strucke-pilot
```

Rules:

- `code` is a stable provider business key and must be unique across provider files. `provider_schema` names the key contract for one kind of delivery; it is unique within that provider. The slash in a schema code is part of the code, not a project path.
- `scope_name` must equal `provider://<code>/<provider_schema>` for each entry. One provider may have several schema scopes, but each pair has exactly one scope. Duplicate provider codes, duplicate schema codes within a provider, duplicate scope names, and mismatched names are rejected.
- Each full slash-separated `scope_name` is one SIMS scope. The slash does not create a SIMS parent scope or set `parent_scope_uuid`.
- The registry is the approved list of provider-schema pairs and scope names. Project validation checks it locally; SIMS creates a named scope on first resolution if it does not already exist.
- A provider's code and a used provider-schema pair and scope name cannot be changed or reused for a different provider or key contract after projects have bound to them. The display name may be corrected without changing identity.
- The registry must not store environment-specific target IDs such as `data_provider_id`. Each project records its operator-reconciled target ID in its fixed `data_provider` entity.
- Registry changes are code-reviewed files, not runtime state.

### Project binding

`metadata.data_provider_code` and `metadata.provider_schema` become required and must match one registered pair. New projects require both at creation. Existing projects without a complete pair may receive one initial assignment during migration. A provider may serve many projects, and projects using a compatible key contract may share one provider schema.

Once assigned, a project's provider code and provider-schema code cannot be changed or removed. Every application project-save path, including metadata edits, raw YAML, and backup restore, must reject a different or missing pair before writing. The UI presents the bound pair as fixed after initial assignment. Project YAML changes made outside the application require repository review; the scope-switch decision must account for any such changes before ingestion resumes.

### Scope derivation

Change Request validation and ingestion identify a project that the caller is authorized to use. The backend loads that project's saved provider code and provider-schema code, verifies the pair against the registry, and passes the saved project name, provider code, and resulting `scope_name` to the ingester. Caller-supplied `data_provider_code`, `provider_schema`, `project_name`, and `sims_scope_name` cannot replace those values. A missing or unregistered saved pair fails closed before any identity work, with no scope derived from the project name.

Each project has a fixed `data_provider` entity with exactly one row, `public_id: data_provider_id`, and `data_provider_code` as its key. The operator reconciles the provider against SEAD by entering the correct target `data_provider_id` in that row. Project validation checks the row count, required fields, positive integer ID, and agreement with the saved provider code without a live database call. Before SIMS work, ingestion confirms that the ID and code identify the same existing SEAD provider row. The bundle uses this trusted row as a lookup-only reference and does not create another provider row or accept one from the submitted workbook.

`EntityConfig.keys` is the only declaration of source business-key columns. For each tracked project entity, Shape Shifter derives one `business_id` from the ordered, normalized key values and sends that value as the SIMS business key. A validator checks the complete transformed delivery before any SIMS call: required key values must be present, the computed key must be unique within each entity in that delivery, and projects bound to the same provider-schema pair must use the same reviewed key meaning. Repeating a key in a later delivery means the same source entity and must reuse its SIMS identity. The validator cannot prove that two distinct real-world records never share a key across deliveries; provider-schema approval must establish that rule. A change to `EntityConfig.keys` or serialization that changes identity meaning requires a new provider-schema code or an explicit identity migration.

The effective scope and run ID are recorded together in the ingest response and the bundle manifest, because a `run_id` is unique only within its scope (`resolve_batches` is keyed `(scope_name, run_id)`).

### Enforcement points

| Point | Check | On failure |
|---|---|---|
| Project validation | Saved provider-schema pair registered; one fixed provider row has a positive ID and matching code | Field-specific validation errors without a database call |
| Project creation | Initial pair present and registered | Creation rejected |
| Project save | Initial assignment is valid; an assigned pair and its tracked key meaning are unchanged | Save rejected before writing if a bound pair or tracked key declaration changes |
| Ingestion | Authorized saved pair and fixed provider row are valid; tracked business keys are present and unique in the transformed delivery; shared schema key meaning is unchanged | Fail before any SIMS call or bundle write |

## Alternatives Considered

- **Let SIMS own the provider list.** Rejected. SIMS has no provider concept; `data_provider` is a SEAD table, and its scope names are not provider-shaped. It would push SEAD domain data into the identity service.
- **Derive the scope from the project name (current).** Rejected. Unstable across renames and too narrow across projects.
- **Use one scope per provider.** Rejected. One provider may deliver unrelated data with different `EntityConfig.keys`; equal key values would then share an identity namespace without a shared key contract.
- **Free-text provider code validated against SEAD at request time.** Rejected. It makes every save depend on a live database query and keeps the namespace undeclared.
- **Store the provider UUID as the scope.** Deferred. It couples SIMS to a SEAD table, requires backfilling an optional column, and makes environment-specific IDs part of the identity key.

## Risks And Tradeoffs

- **Schema-scope key collisions.** Projects assigned the same provider schema share a scope. A key that is only unique within one project, such as a per-delivery sample name, would merge distinct records. The validator catches missing and duplicate keys within a delivery; provider-schema review must establish that the same key always names the same source entity across deliveries.
- **Incorrect manual provider ID.** A fixed row can contain an ID for the wrong SEAD provider. Ingestion checks the saved ID and code against the target before SIMS work; project validation remains independent of the target database.
- **Schema-code changes.** The pilot schema codes become durable identity names once used. Moving an existing project to a new schema code requires an explicit identity migration or a decision to start new identities.
- **Cross-provider duplicates remain.** Shared metadata converges only through reconciliation and review. Provider scoping prevents accidental merging but does not create convergence.
- **Scope strings are immutable.** Renaming or reusing a provider code, provider-schema code, or scope name re-identifies records. Registry review must preserve used pairs and their scope names.
- **Out-of-band project edits.** Direct file edits can bypass application save checks. Such edits require repository review, and ingestion must load the saved project rather than trust request metadata.
- **Migration.** Existing identities live under `sead-change-request:{project}`. SIMS has no scope-merge operation, so those identities are orphaned after cutover unless the change lands before real submissions or an explicit alias migration is run.
- **New configuration surface.** A registry adds a file format and a read endpoint. File changes use repository review.

## Testing And Validation

- Register one provider with two pilot schema codes; confirm their scopes are `provider://mal/archeobotany/arbodat-pilot` and `provider://mal/radiocarbon/strucke-pilot`. Confirm two projects sharing a pair share one scope and two schemas of one provider do not.
- Confirm registry validation rejects duplicate provider codes, duplicate schema codes within a provider, duplicate scope names, and names that do not match their pair. Confirm project validation rejects a missing or unregistered pair.
- Confirm new projects require a registered pair, existing unbound projects can receive one initial assignment, and subsequent changes or removal of either code are rejected before metadata, raw-YAML, or restore writes.
- Confirm ingestion fails before any identity request or bundle write when the saved project pair is unresolved, and that caller-supplied project, provider, schema, or scope values cannot override the saved pair or its fixed provider row.
- Confirm the transformed delivery rejects absent, blank, or duplicate declared keys before any SIMS call; matching keys in later deliveries reuse identity within a scope, and projects sharing a pair use the same reviewed key meaning. Confirm the emitted response and manifest record both scope and run ID.
- Confirm each project has exactly one fixed `data_provider` row with the operator-reconciled SEAD ID; ingestion rejects a missing, malformed, or mismatched ID/code before SIMS and emits one lookup-only provider row plus one submission row.

## Acceptance Criteria

- `P-AC-1` Approved providers are declared in one Shape Shifter registry with a unique `code`, a display `name`, and one or more unique `provider_schema` entries. Each entry has `scope_name` equal to `provider://<code>/<provider_schema>`. Duplicate provider codes, duplicate schema codes within a provider, duplicate scope names, and mismatched names are rejected; used pairs and scopes cannot be reassigned. The initial approved set is provider `mal` with the two stated pilot schemas, excluding BugsCEP.
- `P-AC-2` Every new project declares exactly one `data_provider_code` and one `provider_schema` that form a registered pair. Existing projects without a complete pair may receive an initial assignment. A missing or unregistered pair fails project validation.
- `P-AC-3` Any number of projects may bind the same provider-schema pair, and one provider may have several schemas. Once a project has a pair, every application save path rejects a change or removal of either code before writing.
- `P-AC-4` Change Request runs use the authorized saved project's provider-schema pair and scope for identity resolution and its fixed provider row for the target ID, with no project-name fallback or caller override. The effective scope and run ID appear in the ingest response and the bundle manifest.
- `P-AC-5` A missing or unregistered provider-schema pair blocks validation and ingestion before any identity request, file write, or database access.
- `P-AC-6` Every project has exactly one fixed `data_provider` row with `data_provider_id` as `public_id`. Its operator-entered ID and provider code must identify the same existing SEAD row before SIMS work. The registry and project metadata contain no target ID, the submitted workbook cannot supply the provider row, and the bundle contains exactly one lookup-only provider row.
- `P-AC-7` `EntityConfig.keys` supplies the ordered business-key columns for each tracked project entity. A deterministic `business_id` derived from those values is sent to SIMS. Missing, blank, or duplicate keys in the transformed delivery, or incompatible key meaning for projects sharing a provider-schema pair, block all SIMS calls. Repeated keys across deliveries reuse identity; changing key meaning requires a new schema code or explicit identity migration.

## Planning Handoff

Fixed decisions:

- Shape Shifter owns `(provider code, provider-schema code) → provider://<code>/<provider_schema>`; SIMS owns scopes and may create a named scope on first resolution.
- `scope_name` is the contract; `scope_uuid` is never a registry or resolve input. Provider codes, schema codes, and scope names remain stable after use.
- One provider-schema pair per project; many projects per pair; several schema scopes may belong to one provider. BugsCEP is excluded from the initial registry.
- The backend uses the authorized saved project to select the provider and scope; request fields and runtime overrides cannot change them.
- An assigned project provider-schema pair cannot change or be removed through application save paths. Existing unbound projects may be assigned once.
- The registry holds no environment-specific target IDs.
- Each project's fixed `data_provider` entity has one operator-reconciled SEAD ID; ingestion verifies its ID/code pair before SIMS work.
- `EntityConfig.keys` alone declares business-key columns. Key validation runs before every SIMS call, and the computed `business_id` uses a stable serialization.
- Scope and run ID are emitted together.

Constraints to preserve:

- `data_provider` stays `lookup-only` in the target model.
- Bundle output of exactly one `data_provider` row and one `submission` row is unchanged; the provider row comes from the trusted fixed entity.
- Validation must remain deterministic and must not depend on a live SIMS or database call.
- Provider-schema review must establish that a key identifies the same source entity across deliveries. Runtime validation rejects missing or duplicate keys within each delivery before SIMS.

Open questions, with the phase by which each must be resolved:

| Question | Resolve by |
|---|---|
| Are existing `sead-change-request:*` identities migrated or abandoned at cutover? | Before the scope-switch phase |

## Final Recommendation

Adopt the split-ownership design: Shape Shifter curates provider-schema pairs and fixes each scope name as `provider://<provider-code>/<provider-schema>`, SIMS owns scopes, and a project declares one pair that cannot change after assignment. Derive the Change Request scope, fixed provider row, and declared keys from the authorized saved project. Validate the provider ID and keys before SIMS work.
