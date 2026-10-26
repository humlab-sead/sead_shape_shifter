# Deployment-Time Staging — Phase 1 Task Plan

## Phase Summary

**Phase:** 1 — Establish Aggregate And Target-ID Eligibility. **Readiness:** Validated for execution. The [phase plan](./DEPLOYMENT_TIME_STAGING_PHASE_PLAN.md) marks Phase 1 ready for a task plan and defines `VM-1` as its validation milestone. Its inputs are the [proposal](./DEPLOYMENT_TIME_STAGING.md), the current target model, and a representative deployed SEAD schema. Schema access and a disposable clone are needed to finish the phase.

**Goal:** Derive non-SIMS aggregate children from effective target-model identity, check their parent chains and root-row rules, and establish which deployed ID generators can support locked deployment-time allocation. This phase establishes the contract and inventory. Phase 2 implements staged ID/FK mapping, and Phase 3 promotes it.

**Acceptance criteria**

1. [x] `PH1-AC-1` (from `P-AC-10`): derive each candidate from effective `child` identity and a valid chain ending at a tracked or reconciled root, without an entity allowlist. Record the row rule: a tracked fact root is inserted by the same submission, or a reconciled root has a resolved target ID.
2. [x] `PH1-AC-2` (from `P-AC-3`, `P-AC-9`, `P-AC-10`): give explicit failure results for missing or unsupported generators, unsafe sequence cache behavior, ambiguous target relations, invalid parent chains, and dependency cycles. Specify stable-order table locking before synchronizing an out-of-date sequence or allocating IDs.

**Fixed constraints:** Preserve SIMS-assigned IDs for tracked roots. Do not attach new children to an existing tracked fact root or create a new `value_type` root. A child of an existing reconciled root is allowed when its target ID is resolved. Do not use `role`, FK shape, or `public_id_generation: database_sequence` as a child-eligibility shortcut. The semantic role of `value_type_item` remains outside this phase. The release workflow excludes concurrent writes and independent sequence allocation on affected tables. Keep the current direct-to-target renderer and generation-time reservation until the later staging work is ready.

## Repository Findings

**Repository basis:** `dev` at `7839c8b0`, planned 2026-10-17. Current uncommitted proposal and phase-plan changes, plus the current `sead_standard_model.yml`, were considered and left untouched. `TARGET_MODEL_REVIEW_20261013.md` is tracked and clean, but its `analysis_entity` section predates the current model and proposal. Graphify identified `resolve_effective_identity()` callers; current source confirmed them. A representative deployed schema was not accessed during planning.

| Verified source | Finding and implementation implication |
| --- | --- |
| `src/target_model/effective_identity.py::resolve_effective_identity` | `aggregate_parent` implies effective `child` even for a `fact`; role defaults apply only without a parent. It resolves one entity, not a full parent chain. Extend this shared Core path for chain/root results and root identity type; do not create an entity-name list. |
| `src/target_model/spec_validator.py::TargetModelSpecValidator._validate_aggregate_parent` | Checks missing, unknown, self-referential, and conflicting immediate parents, plus the direct parent FK. It does not detect multi-entity parent cycles or a chain ending at an unsupported root. Preserve its existing issue behavior while adding chain checks. |
| `resources/target_models/sead_standard_model.yml`; `resources/target_models/TARGET_MODEL_REVIEW_20261013.md` | The model has `analysis_entity → dataset`, `analysis_value → analysis_entity`, `abundance_modification → abundance`, and `value_type_item → value_type`. `abundance_modification` is a child despite its `fact` role; `abundance_ident_level` is a derived bridge without `aggregate_parent`. The review still calls `analysis_entity` a tracked bridge and leaves its identity undecided. Update that review during inventory work; it has no deployed-generator results. |
| `ingesters/sead_change_request/planning.py::plan_table`; `ingesters/sead_change_request/orchestration.py::orchestrate_identity_assignments`; `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker.reserve_target_id` | `public_id_generation: database_sequence` currently selects `RESERVE_DATABASE_ID`, and the runtime consumes `nextval` during preparation. `SeadChangeRequestIngester._prepare_change_request` shares this path between validation and ingestion. Keep it as current behavior in Phase 1; replacement is later work. |
| `ingesters/sead_change_request/sql_builder.py::_add_sequence_synchronization` / `_render_sequence_synchronization` | Existing generated SQL locks SIMS target tables in sorted order with `SHARE ROW EXCLUSIVE`, then advances their sequences after explicit inserts. It does not inspect sequence cache settings or lock child tables for deployment-time allocation. Use its lock order and mode as the Phase 1 contract reference while keeping SIMS behavior intact. |
| `ingesters/sead_change_request/sql_builder.py::InlineInsertDeployStrategy.build_artifact` / `CopyCsvDeployStrategy.build_artifact` | Both render in package order and defer constraints; neither derives an insert dependency graph or rejects cycles. Phase 1 must define an acyclic graph result that Phase 2 can use for staged insertion. |
| `tests/target_model/test_effective_identity.py`, `tests/target_model/test_spec_validator.py`, `tests/target_model/test_spec_files.py`; `backend/tests/ingesters/test_sead_change_request_planning.py`, `backend/tests/ingesters/test_sead_change_request_preflight.py` | Existing tests cover single-entity defaults, immediate-parent errors, model loading, reservation routing, and SIMS preflight. They provide extension and regression targets. The target-model test fixture is a symlink to the resource YAML. Focused baseline runs passed during planning. |
| `backend/tests/ingesters/test_sead_change_request_runtime.py::test_target_sequence_reservation_uses_loopback_disposable_postgres` | Existing PostgreSQL integration convention uses `SEAD_DISPOSABLE_POSTGRES_*` and a loopback-only disposable database. No representative deployed-schema inventory or stale-child-sequence check exists in this path. |

## Scope

**In scope:** Pure Core aggregate-chain resolution, validation, and an insert-dependency graph check; review of relevant MVP aggregate-parent assignments and the tracked/reconciled root-row rule; a reproducible derived child/root inventory; read-only inspection of deployed relation, ID-column, sequence/identity, cache, default, and trigger metadata; a stable-order lock and synchronization contract; disposable-clone sequence and lock checks; focused tests and review documentation. The target model may be corrected where the review confirms an ownership error.

**Out of scope:** Staging tables, deployment SQL, row-level ID-map/FK resolution and enforcement of the root-row rule, changing `RESERVE_DATABASE_ID` or the default renderer, Sqitch promotion, new `value_type` roots, unrelated target-model role or requiredness decisions, and updates/resubmissions. A model candidate is not automatically enabled for insertion: Phase 2 must enforce its root-row rule and generator disposition before target inserts.

## Work Breakdown

### Area 1: Derive and validate aggregate ownership

**Objective:** Reusable model-based results identify each child's root and reject invalid chains or selected insert cycles before staging work uses them.

**Affected code:** `src/target_model/effective_identity.py::resolve_effective_identity`, `src/target_model/spec_validator.py::TargetModelSpecValidator._validate_aggregate_parent`, `src/target_model/insert_dependencies.py` (**NEW**), `tests/target_model/test_effective_identity.py`, `tests/target_model/test_spec_validator.py`, `tests/target_model/test_insert_dependencies.py` (**NEW**).

**Dependencies:** Settled tracked/reconciled root policy in the proposal.

**Tasks**

- [x] `T1.1` **Change:** Add full-chain resolution for effective children.
  - **Target:** `src/target_model/effective_identity.py`; `tests/target_model/test_effective_identity.py`.
  - **Current → required:** The resolver classifies one entity → a pure helper returns each child's ordered parent chain, root entity, and effective tracked or reconciled root identity.
  - **Implementation:** Walk effective `aggregate_parent` links. Report unknown or missing parents, multi-entity cycles, terminal roots that are neither tracked nor reconciled, and missing child or root `public_id` metadata.
  - **Constraints:** Treat a separately tracked entity as its own root and include children of reconciled roots. Do not infer ownership from role, ordinary FK shape, or `public_id_generation`.
  - **Validation:** `V-1` covers tracked, reconciled, multi-level, fact-role and bridge-role children, missing parents, bad roots, and cycles.
- [x] `T1.2` **Change:** Expose chain errors through model validation.
  - **Target:** `src/target_model/spec_validator.py::TargetModelSpecValidator.validate` / `_validate_aggregate_parent`; `tests/target_model/test_spec_validator.py`.
  - **Current → required:** Only immediate-parent errors are reported → full-chain failures also produce entity-specific `SpecValidationIssue` results before a candidate is accepted.
  - **Implementation:** Consume `T1.1` results and report two- and three-entity cycles and unsupported terminal roots.
  - **Constraints:** Keep existing immediate-parent issue codes and direct-parent-FK checks stable; avoid duplicate diagnostics for the same broken chain.
  - **Validation:** `V-1`, `V-2` cover new graph failures and existing immediate-parent cases.
- [x] `T1.3` **Change:** Check dependencies among staged insert entities.
  - **Target:** `src/target_model/insert_dependencies.py` (**NEW**); `tests/target_model/test_insert_dependencies.py` (**NEW**).
  - **Current → required:** Both artifact strategies use package order → a pure helper returns dependency order for selected insert entities or reports a cycle before target insertion.
  - **Implementation:** Include aggregate-parent and other required FK edges when both entities are inserted; include optional FK edges supplied as present by the caller. Reference-only target rows create no insert edge.
  - **Constraints:** Do not reject an entire model for a cycle that selected rows do not use. Phase 2 supplies the actual insert set and optional edges.
  - **Validation:** `V-1` covers a valid chain, a two-entity required-FK cycle, a conditional optional-FK cycle, and an existing reconciled parent supplied as a reference-only row.

**Completion evidence:** Tests identify the same root for each valid chain, reject invalid chains and selected insert cycles, and preserve current target-model validation unless a reviewed ownership correction is required.

### Area 2: Review relevant model assignments and record the candidate inventory

**Objective:** The MVP-relevant child/root relationships and per-row root prerequisites are recorded without waiting for unrelated target-model decisions.

**Affected data and tests:** `resources/target_models/sead_standard_model.yml`, `resources/target_models/TARGET_MODEL_REVIEW_20261013.md` (tracked review needing an updated `analysis_entity` section), `tests/target_model/test_spec_files.py`.

**Dependencies:** `T1.1`–`T1.3` for reproducible chain and dependency results.

**Tasks**

- [x] `T2.1` **Change:** Confirm ownership and document derived candidates.
  - **Target:** `resources/target_models/TARGET_MODEL_REVIEW_20261013.md`; `resources/target_models/sead_standard_model.yml`; `tests/target_model/test_spec_files.py`.
  - **Current → required:** The review calls `analysis_entity` a tracked bridge and leaves its identity undecided → align it with the model's `analysis_entity → dataset` child relationship and record a derived child/root inventory.
  - **Implementation:** Record each candidate's entity, parent chain, effective root identity, target table, and `public_id`. Check analysis-value and abundance descendants, `sample_dimension → sample`, `sample_group_reference → sample_group`, and `value_type_item → value_type`. Record `abundance_modification` as a child fact and `abundance_ident_level` as a separate derived bridge. Confirm direct parent FKs, correct only proven MVP ownership mistakes in YAML, and add file-level assertions for settled cases.
  - **Constraints:** Document the row rule: an effective tracked root, including `dataset` despite its `lookup` role, must be newly inserted with its child; a reconciled root must have a resolved target ID; an existing tracked root or unresolved root blocks a new child. Phase 2 enforces this per row. Keep new `value_type` roots, the `value_type_item` role decision, and wider requiredness review separate.
  - **Validation:** `V-1`, `V-2`, `V-4` confirm chain results, model assertions, and the review inventory.

**Completion evidence:** The review inventory and root-row decision table match the model and file assertions; its `analysis_entity` description is current. No hard-coded runtime entity list or role-based exclusion is introduced.

### Area 3: Verify deployed ID generators and stale-sequence behavior

**Objective:** Each candidate has a recorded generator and cache disposition, plus a locking and synchronization rule checked on a disposable clone.

**Affected code and documentation:** `scripts/review_staging_id_generators.py` (**NEW**), `tests/target_model/test_staging_id_generator_review.py` (**NEW**), `resources/target_models/TARGET_MODEL_REVIEW_20261013.md`.

**Dependencies:** Area 2 candidate inventory and access to a representative deployed SEAD schema with a read-only connection; a disposable clone for sequence mutation.

**Tasks**

- [x] `T3.1` **Change:** Implement a read-only schema audit.
  - **Target:** `scripts/review_staging_id_generators.py` (**NEW**); `tests/target_model/test_staging_id_generator_review.py` (**NEW**).
  - **Current → required:** No model-derived deployed-schema audit exists → a command reports supported or unsupported generators for Area 1's derived candidates.
  - **Implementation:** Load the target-model YAML, inspect PostgreSQL catalogs, and resolve each `target_table` to exactly one schema-qualified relation. Report zero or multiple matches; `public_id` column presence/type; serial or identity mode and default; sequence association via `pg_get_serial_sequence`; `pg_sequence` increment, cycle, and cache settings; and enabled insert triggers. Return entity/table reasons and a nonzero status for unsupported or manual-review cases.
  - **Constraints:** Support only positive, noncycling sequences with `CACHE 1` and a usable default or identity behavior. Flag insert triggers for manual review because catalog metadata cannot prove whether they rewrite IDs. Do not consume sequence values or hard-code candidate names.
  - **Validation:** `V-3`, `V-4` cover both identity modes, serial IDs, cache settings, missing or ambiguous relations, missing columns/sequences, nonpositive or cycling sequences, and insert triggers.
- [x] `T3.2` **Change:** Record generator results and verify lock and synchronization behavior.
  - **Target:** `resources/target_models/TARGET_MODEL_REVIEW_20261013.md`.
  - **Current → required:** No deployed-schema result exists → each candidate has a recorded schema result and a checked lock/synchronization contract.
  - **Implementation:** Run the audit against a representative deployed schema. Record database/schema version or snapshot identifier, each qualified relation, generator, cache, status, and reason. Review enabled insert-trigger definitions and verify their effect on a disposable clone before declaring support. On the clone, put a supported sequence behind its table's highest ID, then confirm synchronization produces an unused ID and blocks a competing writer.
  - **Constraints:** Record that Phase 2 locks the union of child-allocation and SIMS sequence-sync tables by qualified name with `SHARE ROW EXCLUSIVE` before inspecting table maxima or changing sequences, and holds locks through insertion. The release workflow excludes concurrent writes and independent `nextval` calls; table locks alone do not serialize `nextval`. Record the `GENERATED ALWAYS` explicit-insert override and unsupported defaults/triggers as Phase 2/3 inputs. Never mutate the representative/source database.
  - **Validation:** `V-4`, `V-5` provide the audit results and disposable-clone lock/sequence results.

**Completion evidence:** The review has a reproducible inventory, root-row rule, generator/cache results, and stable-order lock contract. Missing, ambiguous, and unsupported cases are explicit; the disposable clone confirms stale-sequence recovery and writer blocking.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-10`) | `T1.1`, `T1.2`, `T2.1` | `V-1`, `V-2`, `V-4` | Every effective child has a valid tracked/reconciled root or a named model error. The inventory records the tracked-root insert and reconciled-root resolved-ID rules. |
| `PH1-AC-2` (from `P-AC-3`, `P-AC-9`, `P-AC-10`) | `T1.2`, `T1.3`, `T3.1`, `T3.2` | `V-1`, `V-3`, `V-4`, `V-5` | Invalid chains, selected insert cycles, generator/cache failures, and ambiguous relations have explicit results. A stale sequence advances safely under stable-order table locking on a clone. |

## Validation And Testing

Execution used the repository virtualenv at `/data/roger/source/sead_shape_shifter/.venv/bin/python` because the worktree has no local `.venv`. All planned checks ran on 2026-10-17. `V-4` inspected the deployed catalogs in a read-only session; `V-5` ran on a disposable database that was dropped afterwards.

| ID | Command or manual method | Expected result | Baseline |
| --- | --- | --- | --- |
| `V-1` | `uv run pytest tests/target_model/test_effective_identity.py tests/target_model/test_spec_validator.py tests/target_model/test_insert_dependencies.py -q` | Chain/root and effective root-type cases pass, including a fact-role child, reconciled root, missing parent, invalid terminal root, parent cycles, selected required/optional FK cycles, and a reference-only reconciled parent; prior issue codes remain stable. | Pass: the full command ran on 2026-10-17 (part of a 91-test target-model run that also covered `V-2` and `V-3`). |
| `V-2` | `uv run pytest tests/target_model/test_spec_files.py -q` | The linked SEAD model fixture and direct superset test validate; assertions match `analysis_entity → dataset`, child-fact `abundance_modification`, derived `abundance_ident_level`, and `value_type_item → value_type`. | Pass: ran on 2026-10-17 with the new ownership and insert-order assertions. |
| `V-3` | `uv run pytest tests/target_model/test_staging_id_generator_review.py -q` | Controlled catalog cases classify serial and identity modes, accept safe cache metadata, reject `CACHE >1`, missing/ambiguous relations, absent generators, nonpositive or cycling sequences, and flag enabled insert triggers for review. | Pass: 21 tests ran on 2026-10-17. |
| `V-4` | With libpq connection settings for a representative **read-only** SEAD role: `uv run python scripts/review_staging_id_generators.py resources/target_models/sead_standard_model.yml`; compare its rows with the review inventory and root-row decision table. | Every candidate has a documented qualified relation, generator/cache disposition, and reason. No write or `nextval` occurs. A nonzero exit for an unsupported candidate is recorded as an audit result. | Run on 2026-10-17 against `sead_staging` (PostgreSQL 18.6) with `--schema public`: exit status 1, 39 supported and `value_type_item` unsupported (`missing_id_generator`). An unscoped run reports `ambiguous_relation` for all 40 because `public` and `clearing_house` both contain the table names. Catalog-only; no write or `nextval`. Results are recorded in section 13 of the review. |
| `V-5` | On an isolated disposable clone, use two `psql -X -v ON_ERROR_STOP=1` sessions. Session A locks a supported candidate's qualified table in `SHARE ROW EXCLUSIVE`, reads `MAX(public_id)`, sets its sequence behind that value, synchronizes it, allocates with `nextval`, and holds the transaction. Session B sets a short `lock_timeout` and requests `ROW EXCLUSIVE` on the same table. Repeat explicit ID insertion with the required override for any `GENERATED ALWAYS` candidate. | Session A's allocated ID exceeds the old maximum; Session B times out while A holds the lock and succeeds after A commits. Identity override works where claimed. Record actual relation, SQL, and results in the review. Never mutate a shared/source database. | Pass on disposable database `shifter_phase1_clone_20261017`, created and dropped on 2026-10-17. Session A read old maximum 100, synchronized, and allocated 101; session B timed out with `lock_timeout`. After the commit, B inserted successfully and the next default ID was 102. `GENERATED ALWAYS` rejected an explicit ID without `OVERRIDING SYSTEM VALUE` and accepted it with the override. The source database was not changed. |
| `V-6` | `uv run pytest backend/tests/ingesters/test_sead_change_request_planning.py backend/tests/ingesters/test_sead_change_request_preflight.py -q` | Current direct-renderer planning, reservation routing, and tracked-root SIMS preflight behavior remain intact in Phase 1. | Pass: 36 tests ran on 2026-10-17. |
| `V-7` | `uv run ruff check src/target_model/effective_identity.py src/target_model/insert_dependencies.py src/target_model/spec_validator.py tests/target_model/test_effective_identity.py tests/target_model/test_insert_dependencies.py tests/target_model/test_spec_validator.py tests/target_model/test_spec_files.py tests/target_model/test_staging_id_generator_review.py scripts/review_staging_id_generators.py`; `git diff --check` | Touched Python passes lint and the final diff has no whitespace errors. | Pass: Ruff reports no findings on the listed files and `git diff --check` is clean (2026-10-17). |

## Deliverables

| Deliverable | Path | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Shared chain/root resolution | `src/target_model/effective_identity.py` | `T1.1` | `V-1` passes for valid and invalid chains. |
| Model graph diagnostics | `src/target_model/spec_validator.py` | `T1.2` | `V-1` preserves existing issues and detects cycles/bad roots. |
| Insert dependency check | `src/target_model/insert_dependencies.py` (**NEW**); `tests/target_model/test_insert_dependencies.py` (**NEW**) | `T1.3` | `V-1` rejects cycles for selected inserted rows and accepts reference-only parents. |
| Core tests | `tests/target_model/test_effective_identity.py`; `tests/target_model/test_spec_validator.py` | `T1.1`, `T1.2` | `V-1` passes. |
| Reviewed model and file assertions | `resources/target_models/sead_standard_model.yml`; `tests/target_model/test_spec_files.py` | `T2.1` | `V-2` passes; only confirmed ownership changes are made. |
| Ownership and schema inventory | `resources/target_models/TARGET_MODEL_REVIEW_20261013.md` | `T2.1`, `T3.2` | Derived chains, root-row rules, deployed generator/cache results, lock contract, and clone result are recorded. |
| Schema audit and focused tests | `scripts/review_staging_id_generators.py` (**NEW**); `tests/target_model/test_staging_id_generator_review.py` (**NEW**) | `T3.1` | `V-3` and `V-4` produce supported/unsupported results without mutation. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Derive and validate aggregate ownership | Done | Settled proposal policy | Chain resolver, validator diagnostics, and insert plan implemented; `V-1` passes. Immediate-parent diagnostics are unchanged. |
| Area 2: Review model assignments and inventory | Done | Area 1 | Review `analysis_entity` text corrected; derived inventory and root-row rules recorded; file assertions added. The model YAML needed no ownership correction. |
| Area 3: Verify deployed ID generators | Done | Area 2; representative schema and disposable clone | 39 candidates supported, `value_type_item` unsupported, schema ambiguity recorded, and clone lock/identity checks passed. |

Execution note: HEAD was `8dfca103` (branch `deployment-time-staging`) when implementation started. The three uncommitted proposal documents were pre-existing and were preserved. `scripts/review_staging_id_generators.py` was linted with `# noqa: E402` on its two `src` imports to match the existing script pattern that inserts the project root on `sys.path`.

## Definition Of Done

- [x] `PH1-AC-1` and `PH1-AC-2` have the mapped task results and `V-1`–`V-5` validation results, satisfying phase milestone `VM-1`.
- [x] All areas and deliverables are complete; every MVP-relevant child has a reviewed chain, root-row rule, and deployed-generator/cache disposition.
- [x] `V-6` and `V-7` pass; existing SIMS and direct-renderer behavior remains intact during Phase 1.
- [x] The model, file assertions, review inventory, and schema-audit output agree; the review records the schema/snapshot, unsupported cases, stable lock order and mode, and clone results.
- [x] Any deviation, unavailable schema input, or unresolved ownership issue is documented before Phase 2 uses the inventory. If current source or deployed schema contradicts this plan, stop and report the exact conflict rather than broadening scope or inventing a replacement design.

## Risks And Open Questions

- **Representative schema availability:** A model-only inventory cannot prove deployed ID defaults, sequence association, cache configuration, or schema uniqueness. Area 3 and `PH1-AC-2` required a representative deployed schema and a disposable clone to be complete. Use a read-only role for catalog inspection and perform sequence mutation only on the clone. Resolved for this execution: the representative `sead_staging` schema and a disposable database were available, and the results are recorded in section 13 of the review. The schema ambiguity between `public` and `clearing_house` remains a Phase 2 input.
- **Cached sequence values:** Table locks stop competing table inserts but do not stop independent `nextval` calls. The Phase 1 contract requires `CACHE 1` and an exclusive release workflow for affected sequences. Classify any candidate that fails this contract as unsupported; do not silently fall back to generation-time reservation. PostgreSQL documents the [lock conflicts](https://www.postgresql.org/docs/17/explicit-locking.html) and [cached sequence behavior](https://www.postgresql.org/docs/17/sql-createsequence.html).
- **Ongoing target-model review:** Other role, requiredness, and resubmission decisions remain open. Record only ownership questions that affect current MVP child chains as Phase 1 issues; keep unrelated decisions outside this plan.
