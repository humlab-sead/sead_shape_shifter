# Deployment-Time Staging — Phase 1 Task Plan

## Phase Summary

**Phase:** 1 — Establish Aggregate And Target-ID Eligibility. **Readiness:** Validated for execution. The [phase plan](./DEPLOYMENT_TIME_STAGING_PHASE_PLAN.md) marks Phase 1 ready for a task plan; its inputs are the [proposal](./DEPLOYMENT_TIME_STAGING.md), the current target model, and a representative deployed SEAD schema. Schema access is needed to finish the phase, not to start it.

**Goal:** Derive the non-SIMS aggregate children from effective target-model identity, check their parent chains, and establish which deployed ID generators can support deployment-time allocation. This phase establishes the contract and inventory. Phase 2 implements staged ID/FK mapping, and Phase 3 promotes it.

**Acceptance criteria**

1. [ ] `PH1-AC-1` (from `P-AC-10`): derive each candidate from effective `child` identity and a valid chain ending at a tracked or reconciled root; reject invalid chains without an entity allowlist. Record that insertion requires a resolved root target ID.
2. [ ] `PH1-AC-2` (from `P-AC-3`, `P-AC-9`, `P-AC-10`): identify missing or unsupported generators, ambiguous target relations, and dependency cycles before enabling an entity; verify that an out-of-date sequence can advance without reusing an ID.

**Fixed constraints:** Preserve SIMS-assigned IDs for tracked roots. Accept children of reconciled roots only when the root has a known target ID. Do not use `role`, FK shape, or `public_id_generation: database_sequence` as a child-eligibility shortcut. New `value_type` roots and the semantic role of `value_type_item` remain outside this phase. Do not switch the current direct-to-target renderer or remove generation-time reservation before the later staging work is ready.

## Repository Findings

**Repository basis:** `conditional-target-model-requirements` at `e15f73a9`, planned 2026-10-14. Current uncommitted proposal, phase-plan, `sead_superset_model.yml`, and untracked `TARGET_MODEL_REVIEW_20261013.md` content were considered. They contain the settled `analysis_entity` child decision and other ongoing edits; preserve them. Other dirty files were not changed for this plan. Graphify identified `resolve_effective_identity()` callers; the findings below were verified in current source. No Graphify/source discrepancy was found.

| Verified source | Finding and implementation implication |
| --- | --- |
| `src/target_model/effective_identity.py::resolve_effective_identity` | `aggregate_parent` implies effective `child`; role defaults apply only without a parent. It resolves one entity, not a full parent chain. Extend this shared Core path for chain/root results; do not create an entity-name list. |
| `src/target_model/spec_validator.py::TargetModelSpecValidator._validate_aggregate_parent` | Checks missing, unknown, self-referential, and conflicting immediate parents, plus the direct parent FK. It does not detect multi-entity cycles or a chain ending at an unsupported root. Preserve its existing issue behavior while adding graph checks. |
| `resources/target_models/sead_superset_model.yml`; `resources/target_models/TARGET_MODEL_REVIEW_20261013.md` | The current model has `analysis_entity → dataset`, `analysis_value → analysis_entity`, `sample_dimension → sample`, and `value_type_item → value_type`. The review is in progress and does not establish deployed generator behavior. `value_type_item` can be a child of an existing reconciled `value_type` despite its unresolved role choice. |
| `ingesters/sead_change_request/planning.py::plan_table`; `ingesters/sead_change_request/orchestration.py::orchestrate_identity_assignments`; `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker.reserve_target_id` | `public_id_generation: database_sequence` currently selects `RESERVE_DATABASE_ID`, and the runtime consumes `nextval` during preparation. `SeadChangeRequestIngester._prepare_change_request` shares this path between validation and ingestion. Keep it as current behavior in Phase 1; replacement is later work. |
| `ingesters/sead_change_request/sql_builder.py::_render_sequence_synchronization` | Existing generated SQL advances sequences after explicit SIMS IDs. Reuse its behavior as a preservation and stale-sequence reference; do not conflate it with new child allocation. |
| `tests/target_model/test_effective_identity.py`, `test_spec_validator.py`, `test_spec_files.py`; `backend/tests/ingesters/test_sead_change_request_planning.py`, `test_sead_change_request_preflight.py` | Existing tests cover single-entity defaults, immediate-parent errors, model loading, reservation routing, and SIMS preflight. They provide exact extension and regression targets. The spec fixtures are symlinks to resource YAML, so model-file tests read current resources. |
| `backend/tests/ingesters/test_sead_change_request_runtime.py::test_target_sequence_reservation_uses_loopback_disposable_postgres` | Existing PostgreSQL integration convention uses `SEAD_DISPOSABLE_POSTGRES_*` and a loopback-only disposable database. No representative deployed-schema inventory or stale-child-sequence check exists in this path. |

## Scope

**In scope:** Pure Core aggregate-chain resolution and validation; review of relevant MVP aggregate-parent assignments; a reproducible derived child/root inventory; read-only inspection of deployed relation, ID-column, sequence/identity, default, and trigger metadata; disposable-clone sequence-behavior checks; focused tests and review documentation. The target model may be corrected where the review confirms an ownership error.

**Out of scope:** Staging tables, deployment SQL, row-level ID-map/FK resolution, changing `RESERVE_DATABASE_ID` or the default renderer, Sqitch promotion, new `value_type` roots, unrelated target-model role or requiredness decisions, and updates/resubmissions. A model candidate is not automatically enabled for insertion: the root target ID and deployed generator must be supported when the later staging path is used.

## Work Breakdown

### Area 1: Derive and validate aggregate ownership

**Objective:** A reusable model-based result identifies each child's root and rejects invalid chains before staging work uses it.

**Affected code:** `src/target_model/effective_identity.py::resolve_effective_identity`, `src/target_model/spec_validator.py::TargetModelSpecValidator._validate_aggregate_parent`, `tests/target_model/test_effective_identity.py`, `tests/target_model/test_spec_validator.py`.

**Dependencies:** Settled tracked/reconciled root policy in the proposal.

**Tasks**

- [ ] `T1.1` **Add full-chain resolution.** Target: `src/target_model/effective_identity.py` and `tests/target_model/test_effective_identity.py`. Current → required: the resolver classifies one entity → a pure helper walks effective `aggregate_parent` links and returns the ordered chain and tracked or reconciled root for every effective child. Report unknown parents, missing parent for explicit `child`, multi-entity cycles, terminal roots that are neither tracked nor reconciled, and missing root `public_id` metadata. Treat a separately tracked entity as its own root; include a child of a reconciled root. Use effective identity throughout; do not infer ownership from role, ordinary FK shape, or `public_id_generation`. **Validation:** `V-1` with tracked, reconciled, multi-level, bridge-role child, missing-parent, bad-root, and cycle cases.
- [ ] `T1.2` **Expose graph errors through model validation.** Target: `src/target_model/spec_validator.py::TargetModelSpecValidator.validate` / `_validate_aggregate_parent` and `tests/target_model/test_spec_validator.py`. Current → required: only immediate-parent errors are reported → full-chain failures also produce entity-specific `SpecValidationIssue` results before a candidate is accepted. Keep existing immediate-parent issue codes and direct-parent-FK checks stable; avoid duplicate diagnostics for the same broken chain. **Validation:** `V-1`, `V-2` with two- and three-entity cycles, unsupported terminal roots, and existing immediate-parent cases.

**Completion evidence:** Tests identify the same root for each valid chain and fail closed for invalid chains; all current target-model specs still validate unless a reviewed ownership correction is required.

### Area 2: Review relevant model assignments and record the candidate inventory

**Objective:** The MVP-relevant child/root relationships are reviewed without waiting for unrelated target-model decisions.

**Affected data and tests:** `resources/target_models/sead_superset_model.yml`, `resources/target_models/TARGET_MODEL_REVIEW_20261013.md` (existing untracked working document), `tests/target_model/test_spec_files.py`.

**Dependencies:** `T1.1` and `T1.2` for reproducible chain results.

**Tasks**

- [ ] `T2.1` **Confirm ownership and document derived candidates.** Target: the three files above. Current → required: the review records selected decisions but no complete derived child/root inventory → record each candidate's model entity, parent chain, root identity type, target table, and `public_id`, with MVP relevance and any unsupported relationship noted. Check at least `analysis_entity → dataset`, analysis-value and abundance descendants, `sample_dimension → sample`, `sample_group_reference → sample_group`, and `value_type_item → value_type`. Confirm the direct parent FK, correct only proven MVP ownership mistakes in YAML, and add file-level assertions for settled cases. State explicitly that a reconciled root must have a known target ID when a child is inserted; Phase 2 enforces this per row. Keep the `value_type_item` role decision and wider requiredness review separate. **Validation:** `V-1`, `V-2` and the inventory review in `V-4`.

**Completion evidence:** Review table is derived from current effective identity and matches the model/test assertions. No hard-coded runtime entity list or role-based exclusion is introduced.

### Area 3: Verify deployed ID generators and stale-sequence behavior

**Objective:** Each candidate has a recorded supported or unsupported ID-generation result from a representative deployed SEAD schema.

**Affected code and documentation:** `scripts/review_staging_id_generators.py` (**NEW**), `tests/target_model/test_staging_id_generator_review.py` (**NEW**), `resources/target_models/TARGET_MODEL_REVIEW_20261013.md`.

**Dependencies:** Area 2 candidate inventory and access to a representative deployed SEAD schema with a read-only connection; a disposable clone for sequence mutation.

**Tasks**

- [ ] `T3.1` **Implement a read-only schema audit.** Target: the two **NEW** files above. Current → required: no model-derived deployed-schema audit exists → load the supplied target-model YAML, use Area 1's derived candidates, and inspect PostgreSQL catalogs. Resolve each unqualified `target_table` to exactly one schema-qualified relation; report zero/multiple matches. For each candidate, report `public_id` column presence/type, serial or identity mode and default, associated sequence via `pg_get_serial_sequence`, sequence increment/cycle metadata, and enabled insert triggers. Mark triggers for manual review because catalog metadata alone cannot prove whether a trigger rewrites an ID. Do not consume sequence values or hard-code candidate names. Return a nonzero status with actionable entity/table diagnostics when a candidate is unsupported or needs manual review. Tests use controlled catalog results for serial, `GENERATED BY DEFAULT`, `GENERATED ALWAYS`, missing default/sequence/column, ambiguous relation, and an insert trigger needing review. **Validation:** `V-3`, `V-4`.
- [ ] `T3.2` **Record generator results and verify safe synchronization.** Target: `resources/target_models/TARGET_MODEL_REVIEW_20261013.md`. Current → required: no deployed-schema result exists → run the audit against a representative deployed schema, record database/schema version or snapshot identifier and each candidate's relation, generator, supported status, and reason. Review enabled insert-trigger definitions and check behavior on a disposable clone before declaring that candidate supported. On the clone only, put a supported child sequence behind its table's highest ID, apply the planned sequence-synchronization rule, and confirm the next allocated ID exceeds every existing ID. Record the `GENERATED ALWAYS` explicit-insert override requirement and any unsupported default or trigger as Phase 2/3 inputs. Do not enable an unsupported entity or mutate the representative/source database. **Validation:** `V-4`, `V-5`.

**Completion evidence:** The review has a reproducible inventory and schema results; missing/ambiguous/unsupported cases are explicit, and the disposable clone confirms stale-sequence recovery without an ID collision.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-10`) | `T1.1`, `T1.2`, `T2.1` | `V-1`, `V-2`, `V-4` | Every effective child has a valid tracked/reconciled root and documented root-ID prerequisite, or a named model error. |
| `PH1-AC-2` (from `P-AC-3`, `P-AC-9`, `P-AC-10`) | `T1.2`, `T3.1`, `T3.2` | `V-1`, `V-3`, `V-4`, `V-5` | Cycles and generator/relation failures are explicit; a stale sequence advances above existing IDs on a disposable clone. |

## Validation And Testing

Planning did not run tests or connect to a database. Commands below are for implementation handoff. The new script and test file exist only after `T3.1`.

| ID | Command or manual method | Expected result | Baseline |
| --- | --- | --- | --- |
| `V-1` | `uv run pytest tests/target_model/test_effective_identity.py tests/target_model/test_spec_validator.py -q` | Chain/root, multi-level, reconciled-root, missing-parent, bad-root, and cycle cases pass; prior issue codes remain stable. | Not run: planning-only request. |
| `V-2` | `uv run pytest tests/target_model/test_spec_files.py -q` | Both linked SEAD spec files validate; settled `analysis_entity`, `value_type_item`, and bridge-child relationships match the model. | Not run: planning-only request. |
| `V-3` | `uv run pytest tests/target_model/test_staging_id_generator_review.py -q` | Catalog-result cases classify serial/identity support, reject missing or ambiguous relations and absent generators, and flag enabled insert triggers for manual review. | Not run: test file is planned. |
| `V-4` | With libpq connection settings for a representative **read-only** SEAD role: `uv run python scripts/review_staging_id_generators.py resources/target_models/sead_superset_model.yml`; compare its rows with the review inventory. | Every candidate has a documented supported/unsupported/manual-review result and no target write or `nextval` occurs. A nonzero exit for an unsupported candidate is recorded, not treated as an incomplete audit. | Not run: script is planned; representative schema was not accessed during planning. |
| `V-5` | On an isolated disposable clone, use `psql -X -v ON_ERROR_STOP=1` to inspect a supported child's `MAX(public_id)` and associated sequence, deliberately set the sequence behind that maximum, run the planned synchronization SQL, then call `nextval` and compare with the original maximum. Repeat the explicit-insert check for any `GENERATED ALWAYS` candidate. | The allocated value is greater than the existing maximum; identity override works where claimed. Record actual relation, SQL, and results in the review. Never do this on a shared/source database. | Not run: disposable clone required; planning-only request. |
| `V-6` | `uv run pytest backend/tests/ingesters/test_sead_change_request_planning.py backend/tests/ingesters/test_sead_change_request_preflight.py -q` | Current direct-renderer planning, reservation routing, and tracked-root SIMS preflight behavior remain intact in Phase 1. | Not run: planning-only request. |
| `V-7` | `uv run ruff check src/target_model/effective_identity.py src/target_model/spec_validator.py tests/target_model/test_effective_identity.py tests/target_model/test_spec_validator.py tests/target_model/test_spec_files.py tests/target_model/test_staging_id_generator_review.py scripts/review_staging_id_generators.py`; `git diff --check -- src/target_model/effective_identity.py src/target_model/spec_validator.py tests/target_model/test_effective_identity.py tests/target_model/test_spec_validator.py tests/target_model/test_spec_files.py resources/target_models/sead_superset_model.yml` | Touched Python passes lint and the tracked-file diff has no whitespace errors; review new files separately. | Not run: planning-only request. |

## Deliverables

| Deliverable | Path | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Shared chain/root resolution | `src/target_model/effective_identity.py` | `T1.1` | `V-1` passes for valid and invalid chains. |
| Model graph diagnostics | `src/target_model/spec_validator.py` | `T1.2` | `V-1` preserves existing issues and detects cycles/bad roots. |
| Core tests | `tests/target_model/test_effective_identity.py`; `tests/target_model/test_spec_validator.py` | `T1.1`, `T1.2` | `V-1` passes. |
| Reviewed model and file assertions | `resources/target_models/sead_superset_model.yml`; `tests/target_model/test_spec_files.py` | `T2.1` | `V-2` passes; only confirmed ownership changes are made. |
| Ownership and schema inventory | `resources/target_models/TARGET_MODEL_REVIEW_20261013.md` | `T2.1`, `T3.2` | Derived chains, deployed generator results, and clone result are recorded. |
| Schema audit and focused tests | `scripts/review_staging_id_generators.py` (**NEW**); `tests/target_model/test_staging_id_generator_review.py` (**NEW**) | `T3.1` | `V-3` and `V-4` produce supported/unsupported results without mutation. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Derive and validate aggregate ownership | Not started | Settled proposal policy | Preserve existing immediate-parent diagnostics. |
| Area 2: Review model assignments and inventory | Not started | Area 1 | Preserve current uncommitted model/review work. |
| Area 3: Verify deployed ID generators | Not started | Area 2; representative schema and disposable clone | Required to complete Phase 1, not to start it. |

## Definition Of Done

- [ ] `PH1-AC-1` and `PH1-AC-2` have the mapped task results and `V-1`–`V-5` validation results.
- [ ] All areas and deliverables are complete; every MVP-relevant child has a reviewed chain, root, and deployed-generator disposition.
- [ ] `V-6` and `V-7` pass; existing SIMS and direct-renderer behavior remains intact during Phase 1.
- [ ] The model, file assertions, review inventory, and schema-audit output agree; the review records the schema/snapshot used and unsupported cases.
- [ ] Any deviation, unavailable schema input, or unresolved ownership issue is documented before Phase 2 uses the inventory. If current source or deployed schema contradicts this plan, stop and report the exact conflict rather than broadening scope or inventing a replacement design.

## Risks And Open Questions

- **Representative schema availability:** A model-only inventory cannot prove deployed ID defaults, sequence association, or schema uniqueness. Area 3 and `PH1-AC-2` remain incomplete until a representative deployed schema and disposable clone are available. Use a read-only role for catalog inspection and perform sequence mutation only on the clone.
- **Ongoing target-model review:** Other role, requiredness, and resubmission decisions remain open. Record only ownership questions that affect current MVP child chains as Phase 1 issues; keep unrelated decisions outside this plan.
