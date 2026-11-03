# Investigation findings: SRP and entity-specific type-code audit

**Brief:** [brief.md](./brief.md)  
**Tracking issue:** [humlab-sead/sead_shape_shifter#624](https://github.com/humlab-sead/sead_shape_shifter/issues/624)  
**Status:** Partially conclusive  
**Environment / baseline:** Repository `humlab-sead/sead_shape_shifter`, branch `dev`, commit `4a04566be18331576c06c9dd7bb6560520aa7f11` (`Merge pull request #625`), 2026-10-28. The worktree contained the untracked investigation brief; no tracked application changes were present.

## Executive summary

This is a maintainability audit, not an investigation of a reported runtime failure. The targeted Core review did not establish a remaining SRP or fixed-entity type-code finding. The Backend review identified two supported candidates for maintainer review:

1. `AutoFixService` handles general fix actions but also embeds fixed-entity `system_id` repairs. Those repairs are selected using string values stored in the generic `FixAction.new_value` field.
2. `MaterializationService` manages materialization and unmaterialization, and also owns a separately callable workflow for synchronizing mapping-sidecar links from saved materialized rows.

These are supported hypotheses about maintenance costs, not confirmed defects or proven SRP violations. The evidence does not establish user-visible failures or data impact. `ProjectMapper` was checked as a calibration example: commit `f762e96e` moved fixed-entity load issue collection into a dedicated collector, and the current mapper calls a collector registry. That fixed case is not reported as outstanding.

Coverage was targeted rather than class-by-class exhaustive. The findings therefore describe the reviewed candidates and screened patterns, not every class in Core or Backend.

## Verified observations and reproduction

No runtime symptom was reported, so there was no failure to reproduce. The review traced current class responsibilities, dispatch conditions, call sites, tests, and the `ProjectMapper` history. Search results were used to find candidates; source and usage were checked before classifying them.

### Findings

| ID | Layer | Class and methods | Concern | Priority | Evidence status |
| --- | --- | --- | --- | --- | --- |
| F1 | Backend | `AutoFixService._apply_action`, `_update_values` | Fixed-entity `system_id` repair operations are embedded in the general fix service and selected through string sentinels in a generic action payload. | Medium | Supported hypothesis |
| F2 | Backend | `MaterializationService.sync_materialized_entity_mappings` | The class combines materialization lifecycle and saved-row-to-mapping-sidecar synchronization, which is independently exposed through an API route. | Low | Supported hypothesis |

Priority is a review order for maintainability work, not operational severity. Neither item is a confirmed runtime defect.

### F1 — Fixed-entity repair operation codes in `AutoFixService`

**Verified structure:** `FixActionType` defines the generic `UPDATE_VALUES` action in [fix.py](../../../backend/app/models/fix.py#L11) and documents it as fixed-entity `system_id` repair at [fix.py](../../../backend/app/models/fix.py#L22). Three strategy classes create this action with `new_value` set to `"fill_null_system_ids"`, `"fix_duplicate_system_ids"`, or `"fix_invalid_system_ids"` in [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L125), [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L154), and [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L183). The general action dispatcher routes `UPDATE_VALUES` to `_update_values` at [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L352) and [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L360). That method checks for entity type `"fixed"` and branches on the three sentinel strings at [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L424), [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L437), and [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L456).

This makes the payload’s `new_value` serve two roles: an action-specific operation code and a value field. Adding or changing one of these repairs requires coordination between a strategy, the generic action executor, and its payload convention. A search of `backend/tests/` found no references to `UPDATE_VALUES` or these sentinel strings. Existing tests cover other actions, including column removal and addition, in [test_auto_fix_service.py](../../../backend/tests/services/test_auto_fix_service.py#L98) and [test_auto_fix_service.py](../../../backend/tests/services/test_auto_fix_service.py#L372).

**Counterevidence:** The service already uses separate `AutoFixStrategy` implementations to generate suggestions, and all three fixed-entity repairs operate on the same `system_id` column. A small, closed operation set can be reasonable to handle in one service. An enum-based dispatcher is not itself a smell, and the evidence does not show that the current implementation has caused a defect.

**Assessment:** The fixed-entity segment is verified; the claim that it creates meaningful maintenance burden is a **Supported hypothesis**. The concern is specifically the nested string discriminator in a generic action payload, not the mere presence of fixed-entity logic in an auto-fix feature.

**Focused recommendation:** Before adding more value-repair operations, decide whether the action model should represent each operation explicitly, for example with a typed operation field or a focused handler. Preserve the existing suggestion and apply behavior. Add tests for each fixed `system_id` repair and for unknown operation values as part of any change. Do not replace the full dispatcher with a broader pattern unless the action set grows enough to justify it.

### F2 — Mapping-sidecar synchronization in `MaterializationService`

**Verified structure:** [MaterializationService](../../../backend/app/services/materialization_service.py#L48) has separate methods for mapping-sidecar synchronization, materialization, and unmaterialization: [materialization_service.py](../../../backend/app/services/materialization_service.py#L289), [materialization_service.py](../../../backend/app/services/materialization_service.py#L392), and [materialization_service.py](../../../backend/app/services/materialization_service.py#L535). The mapping synchronization method loads saved materialized rows, computes manual links, and reads or writes a `MappingManager` catalog in [materialization_service.py](../../../backend/app/services/materialization_service.py#L312). It is separately available through `PATCH /projects/{project_name}/mapping/from-materialized/{entity_name}` in [materialization.py](../../../backend/app/api/v1/endpoints/materialization.py#L131). Tests group this workflow separately from lifecycle tests in [test_materialization_service.py](../../../backend/tests/services/test_materialization_service.py#L754).

These call paths change different state: the lifecycle methods update the project entity configuration and materialized values, while mapping synchronization updates the mapping sidecar. That provides a concrete reason to consider whether the workflows need separate implementation responsibilities.

**Counterevidence:** Sidecar synchronization operates only on saved materialized rows and is exposed by the materialization API module. It shares the project lock and materialized-entity context with the lifecycle, so keeping the workflow coordinated in one service may be intentional. The evidence does not show that these responsibilities have changed independently or caused maintenance problems.

**Assessment:** The separate workflows and state writes are **Verified**; the conclusion that they should be split is a **Supported hypothesis**.

**Focused recommendation:** Do not extract a new service solely because the methods are separate. If mapping-sidecar behavior is expected to evolve independently, consider moving that workflow behind a dedicated collaborator while preserving the endpoint contract, project locking, optimistic version check, and additive-versus-replacement link behavior. Keep the existing mapping synchronization tests as regression coverage.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | Audit baseline | Branch and revision recorded above; `rtk git status --short --branch`, `rtk git log -1 --oneline` | Baseline is `dev` at `4a04566b`; only the untracked investigation directory was present. | Verified |
| E2 | Fixed `ProjectMapper` case | Commit [`f762e96e`](https://github.com/humlab-sead/sead_shape_shifter/commit/f762e96e); current [project_mapper.py](../../../backend/app/mappers/project_mapper.py#L140), [project_load_issue_collectors.py](../../../backend/app/mappers/project_load_issue_collectors.py#L6), and [fixed_entity_load_issue_collector.py](../../../backend/app/mappers/fixed_entity_load_issue_collector.py#L24) | The commit added a dedicated fixed-entity load issue collector and reduced `ProjectMapper`; current mapper delegates collection through the registry. | Verified; calibration only |
| E3 | Generic fix action contains fixed-entity operation codes | [fix.py](../../../backend/app/models/fix.py#L22), [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L424), [auto_fix_service.py](../../../backend/app/services/auto_fix_service.py#L456) | Three fixed `system_id` repairs are distinguished through `new_value` strings in the shared action model. | Verified structure; maintenance impact is a supported hypothesis |
| E4 | Fixed-value action test search | Search for `UPDATE_VALUES`, `fill_null_system_ids`, `fix_duplicate_system_ids`, and `fix_invalid_system_ids` under `backend/tests/` | No matches. This establishes a test-coverage gap for these operation names, not a runtime failure. | Verified |
| E5 | Materialization and mapping-sync call paths | [materialization_service.py](../../../backend/app/services/materialization_service.py#L289), [materialization.py](../../../backend/app/api/v1/endpoints/materialization.py#L131), [test_materialization_service.py](../../../backend/tests/services/test_materialization_service.py#L754) | Mapping synchronization has a distinct method, route, and test group alongside materialization lifecycle methods. | Verified structure; SRP impact is a supported hypothesis |
| E6 | Core type-specific behavior and alternatives | [extract.py](../../../src/extract.py#L24), [extract.py](../../../src/extract.py#L235), [test_subset_service.py](../../../tests/process/test_subset_service.py#L84), [entity.py](../../../src/specifications/entity.py#L41), [entity_config_mapper.py](../../../backend/app/mappers/entity_config_mapper.py#L218) | Reviewed examples include focused source-alias behavior with a test and type-specific validation/mapping registries. | No Core smell confirmed in these examples |
| E7 | Project-service delegation | [project_service.py](../../../backend/app/services/project_service.py#L93), [project_service.py](../../../backend/app/services/project_service.py#L96), [project_service.py](../../../backend/app/services/project_service.py#L111), [project_service.py](../../../backend/app/services/project_service.py#L122) | The broad service composes project utilities, project operations, entity operations, and a file manager. Size alone was not treated as evidence of an SRP problem. | Verified counterevidence; not a full class review |

## Timeline or causal chain

There is no failure timeline. For calibration, commit `f762e96e` (`fix(validation): surface project load failures`) moved fixed-entity load issue collection into a dedicated collector. The current [ProjectMapper](../../../backend/app/mappers/project_mapper.py#L140) calls the project-load collector registry. This confirms that the cited mapper example is a completed change, not a remaining finding.

## Root-cause assessment

**Confirmed mechanism:** No runtime failure or root cause was reported or established. The audit found code structures that may increase maintenance effort; whether they have caused material costs remains unverified.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| Core has a remaining class that combines unrelated responsibilities or embeds problematic fixed-entity behavior. | Targeted review of `TableConfig`, pipeline orchestration, subset extraction, fixed-entity specifications, and fixed-entity mapping logic. | The reviewed type branches correspond to configuration semantics, registered type-specific specifications, or focused extraction behavior. The derived-entity alias case has a targeted test. | No candidate substantiated in reviewed examples; broader Core coverage remains incomplete. |
| `AutoFixService` embeds a type-coded fixed-entity operation protocol in a general action model. | Generic `UPDATE_VALUES` actions carry one of three string operation codes; `_update_values` checks for fixed entities and dispatches on those values. | The operations share one column and purpose; no defect or demonstrated maintenance failure was found. Other action types use explicit enum dispatch. | Supported hypothesis |
| `MaterializationService` combines independently changing materialization and mapping-sidecar responsibilities. | Separate methods and API routes manage materialization lifecycle and sidecar synchronization; their state changes differ. | Synchronization is limited to materialized rows and shares the project lock and feature context. Independent change history was not established. | Supported hypothesis |
| The fixed-entity `ProjectMapper` example remains open. | The relevant history and current mapper were checked. | `f762e96e` added a collector; current mapper delegates collection through a registry. | Ruled out |

## Impact and extent

**Confirmed affected cases:** None. No user-visible behavior, data loss, or failed operation was established.

**Potential wider impact:** Changes to fixed `system_id` repair operations may require coordinated updates to the suggestion strategy, generic executor, and string-valued action payload. The current test search found no coverage for these operations. Mapping-sidecar changes may also touch the same service as entity materialization even when they concern a separate API operation. These are plausible maintenance risks, not measured impacts.

**Coverage limits:** Core and Backend were considered separately, but this was a targeted audit, not an exhaustive manual review of every production class. Candidate discovery used Graphify and text searches for type-dependent branches; those searches do not detect every form of dynamic dispatch or responsibility overlap. In Core, selected modules included `src/model.py`, `src/normalizer.py`, `src/extract.py`, `src/specifications/entity.py`, `src/specifications/foreign_key.py`, `src/specifications/materialize.py`, `src/column_availability.py`, `src/reconciliation/fixed_entity_mapping_changes.py`, `src/loaders/sql_loaders.py`, and `src/types/fixed_entity_types.py`. In Backend, selected modules included `auto_fix_service.py`, `fix.py`, `materialization_service.py`, `project_service.py`, `validation_service.py`, `dependency_service.py`, `entity_config_mapper.py`, `project_mapper.py`, `project_load_issue_collectors.py`, and `project_data_provider_service.py`. The remaining classes in these layers were not reviewed individually. Frontend and Ingesters were not audited.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Keep `AutoFixService` as-is and add tests for the three fixed `system_id` repair operations. | Improves confidence without changing the action contract. | Leaves the string discriminator and coordinated edits in place. | Cover null, duplicate, and invalid ID repairs, plus handling of an unknown operation. |
| Make fixed-value operation kinds explicit in the action model or isolate them behind a focused handler. | Makes the fixed-specific behavior and accepted operation set clearer; can reduce the generic payload’s dual use. | Changing the action schema may affect API clients or stored suggestions. A handler abstraction may add needless complexity if the operation set remains small. | Confirm the action model’s compatibility requirements and preserve existing confirmation, preview, and apply behavior. |
| Keep mapping synchronization in `MaterializationService` unless it changes independently. | Avoids an unneeded class split and keeps materialized-row context together. | Future sidecar changes continue to touch a service that also owns lifecycle logic. | Reassess when sidecar synchronization has independent changes or additional callers. |
| Extract mapping synchronization into a collaborator if independent evolution is confirmed. | Separates sidecar read/reconcile/write logic from entity lifecycle and serialization. | Splitting may complicate locking and project-state coordination. | Preserve the route contract, project lock, snapshot version check, additive/replacement semantics, and existing tests. |

**Recommended next step:** Review F1 with maintainers first, because it combines fixed-entity behavior with an untyped operation discriminator and currently has no matching test references. Decide whether the action model is expected to grow before choosing between focused tests and a typed operation representation. Treat F2 as a conditional extraction, not immediate work; confirm that mapping-sidecar behavior has an independent reason to change before opening an implementation issue.

**Prevention / regression detection:** Add operation-level tests before changing fixed `system_id` repair dispatch. For any future extraction of mapping synchronization, retain tests for additive sync, replacement of manual links, preservation of reconciliation links, compound keys, invalid rows, and version-checked writes.

## Unresolved questions and blockers

- Are fixed `system_id` repair operations part of a stable API contract, and are more operation kinds planned?
- Does mapping-sidecar synchronization have independent callers or change history beyond the current route and tests?
- A complete class-by-class assessment of Core and Backend remains outstanding; the current findings should not be read as proof that no other candidates exist.

No blocker prevents the targeted findings above. The smallest next step is a maintainer decision on whether F1’s fixed-value actions are expected to expand; that determines whether test coverage alone is sufficient or whether the action representation should change.

## Verification record

- `rtk git status --short --branch` and `rtk git log -1 --oneline`: confirmed the baseline branch, revision, and worktree state.
- `rtk git show --stat --oneline f762e96e`: confirmed the mapper calibration change includes a dedicated fixed-entity load issue collector and a reduced `ProjectMapper`.
- `rtk graphify explain "MaterializationService"`: used to inspect service relationships; source and API call sites were then checked directly.
- Ripgrep searches over `src/` and `backend/app/` for type-dependent branches were used to find candidate locations. Candidate conclusions above were checked against relevant source and tests.
- Search for `UPDATE_VALUES` and the three fixed-entity operation strings under `backend/tests/`: no matches.
- No tests were run. This investigation assessed code structure and test presence; it did not attempt to reproduce a runtime defect.
- No production source code was changed.

## References

- [Investigation brief](./brief.md)
- [Tracking issue #624](https://github.com/humlab-sead/sead_shape_shifter/issues/624)
- [Calibration commit f762e96e](https://github.com/humlab-sead/sead_shape_shifter/commit/f762e96e)
