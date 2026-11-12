# Direct Target-ID Conditional FK Conformance — Phase 1 Task Plan

## Phase Summary

- **Phase:** Phase 1 — Correct conditional conformance
- **Readiness:** Validated and executed 2026-11-11. The source proposal was approved on 2026-11-11, removing the blocking decision. `T1.1`, `T1.2`, and `T1.3` are complete with passing validation (`V-1`, `V-2`, and `V-3` all pass).
- **Goal:** Suppress the reconciliation-pending result only for valid conditional direct target-ID FKs, preserving independent requirements and direct-ID validation.
- **Source proposal:** [Direct Target-ID Conditional FK Conformance](DIRECT_TARGET_ID_CONDITIONAL_FK_CONFORMANCE.md)
- **Source phase plan:** [Direct Target-ID Conditional FK Conformance Phase Plan](DIRECT_TARGET_ID_CONDITIONAL_FK_CONFORMANCE_PHASE_PLAN.md)
- **Dependency:** Approval of the source proposal. Received 2026-11-11.

Phase acceptance criteria:

- [x] `PH1-AC-1` (from `P-AC-1`): A valid conditional direct-ID FK retains the target-check status but has no reconciliation-pending status or lookup requirement from that relationship.
- [x] `PH1-AC-2` (from `P-AC-2`): Local/default conditional FKs still await reconciliation, and invalid direct-ID declarations retain their errors.
- [x] `PH1-AC-3` (from `P-AC-3`): A second FK to the same target retains its own conditional status, and globally required target entities remain required.
- [x] `PH1-AC-4` (from `P-AC-4`): Selected inserts still require conditional direct-ID values and reject IDs absent from the target database. (Demonstrated 2026-11-11 by `V-3`.)

## Repository Findings

**Repository basis:** Branch `add-copy-project-script`, commit `e545a374`, planning date 2026-11-10. The working tree has uncommitted changes, including `tests/model/test_target_model_conformance.py`; baseline checks below ran against the current worktree.

| Evidence | Finding | Planning implication |
|---|---|---|
| `src/target_model/conformance.py::ConditionalForeignKeyConformanceValidator.validate_global` | Reports `CONDITIONAL_FK_AWAITING_RECONCILIATION` for every conditional FK on a project entity, without checking its value source. | Suppress the issue per FK only when its direct-ID declaration is valid. |
| `src/target_model/conformance.py::is_valid_direct_public_id_foreign_key` | Validates `public_id` mode, target metadata, a direct relationship, absence of a conflicting Core link, and presence of the target-facing ID column. | Reuse this check; do not infer direct-ID mode from a missing lookup entity. |
| `tests/model/test_target_model_conformance.py::test_direct_public_id_fks_allow_missing_targets_and_report_pending_checks` | Covers conditional direct-ID configuration and currently expects `CONDITIONAL_FK_AWAITING_RECONCILIATION` alongside `DIRECT_FK_TARGET_CHECK_PENDING`. | Update the expectation and cover local, invalid, mixed-source, and independently required-target cases. |
| `ingesters/sead_change_request/direct_fk_validation.py::validate_direct_foreign_keys` | Requires a direct FK value for inserted rows when `required_when.has_new_rows` names the source entity, and checks supplied target IDs. | Keep ingester behavior unchanged; retain regression coverage for this contract. |
| `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py::test_direct_fk_uses_real_postgres_lookup_before_package_acceptance` | Exercises valid and nonexistent direct IDs through table validation and ingestion, but its FK uses static `required: true`. It creates and drops a schema in a loopback disposable PostgreSQL database. | Extend coverage for a conditional direct-ID FK, but run this test only when the disposable database is explicitly configured. |

## Scope

**In scope**

- Adjust project-only conditional FK conformance for valid direct `public_id` declarations.
- Update conformance tests and add regression coverage for conditional direct-ID inserts.
- Preserve existing direct-ID pending checks, insertion requirements, and target-database checks.

**Out of scope**

- Changes to `required_when`, direct-ID ingestion, target projection, UI, or database contracts.
- Suppressing independent target-entity requirements or errors from invalid declarations.

**Affected files**

- `src/target_model/conformance.py`
- `tests/model/test_target_model_conformance.py`
- `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py`

## Work Breakdown

### Area 1: Correct conditional conformance and protect direct-ID behavior

**Objective:** Project conformance reports reconciliation as pending only for conditional relationships that still require it.

**Affected code:** `src/target_model/conformance.py::ConditionalForeignKeyConformanceValidator.validate_global` and the existing conformance and direct-ID integration test files listed above.

**Dependencies:** Proposal approval; received 2026-11-11.

**Tasks:**

* [x] `T1.1` **Change:** Skip `CONDITIONAL_FK_AWAITING_RECONCILIATION` for a conditional FK only when `is_valid_direct_public_id_foreign_key(...)` confirms that exact source-target relationship.
  * **Target:** `src/target_model/conformance.py::ConditionalForeignKeyConformanceValidator.validate_global`.
  * **Current → required:** Every conditional FK on a present source reports awaiting reconciliation; a valid direct-ID FK should not, while all other conditional FKs should.
  * **Implementation:** Evaluate the existing helper for each conditional FK before appending the issue. Keep the exception per FK. Do not suppress invalid declaration errors or checks for other target requirements.
  * **Constraints:** Keep `DIRECT_FK_TARGET_CHECK_PENDING`, `required_when` timing, and all change-request behavior unchanged.
  * **Validation:** `V-1`.
* [x] `T1.2` **Change:** Update and extend conformance regressions for conditional direct-ID relationships.
  * **Target:** `tests/model/test_target_model_conformance.py`.
  * **Current → required:** The direct-ID test currently expects both pending statuses; it should retain only the target-check status for that valid conditional FK.
  * **Implementation:** Cover a valid conditional direct ID, a local/default conditional FK, an invalid direct-ID declaration, two sources using different modes for the same target, and a globally required target.
  * **Constraints:** Keep tests constructed with the existing inline target-model and project helpers.
  * **Validation:** `V-1`.
* [x] `T1.3` **Change:** Add regression coverage that `required_when` still requires a direct-ID value on a selected insert and that a nonexistent supplied target ID is rejected. *(Completed 2026-11-11: `test_conditional_direct_fk_requires_value_on_selected_insert_and_checks_target_id` added with conditional helpers; validated by `V-3` against a disposable PostgreSQL container.)*
  * **Target:** `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py`.
  * **Current → required:** Its existing integration case checks direct IDs with static `required: true`; conditional direct-ID insert requirements must also remain covered.
  * **Implementation:** Add a conditional FK case using the existing disposable-database test setup and a row selected for insertion. Assert that a missing required value and a nonexistent target ID are rejected.
  * **Constraints:** Do not change ingester implementation. Run only with the test's configured loopback disposable PostgreSQL database.
  * **Validation:** `V-3`.

**Completion evidence:** The conformance result is omitted only for a valid conditional direct-ID relationship; other conditional statuses and target requirements remain; conditional direct-ID inserts retain their value and target-existence checks.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` | `T1.1`, `T1.2` | `V-1` | Valid conditional direct-ID FK retains target-check pending status but has no reconciliation-pending issue or relationship-derived lookup error. |
| `PH1-AC-2` | `T1.1`, `T1.2` | `V-1` | Local/default conditional FK still awaits reconciliation; invalid direct-ID declarations retain conformance errors. |
| `PH1-AC-3` | `T1.2` | `V-1` | A separate source's local FK remains conditional, and a globally required target remains required. |
| `PH1-AC-4` | `T1.3` | `V-3` | Conditional direct-ID inserts reject missing values and nonexistent target IDs. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Focused project conformance regressions in `tests/model/test_target_model_conformance.py`, including the existing conditional and direct-public-ID tests and new cases from `T1.2`. | `rtk uv run pytest tests/model/test_target_model_conformance.py -q -k 'conditional_foreign_key or direct_public_id_fk'` | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-3` | Tests pass with the revised direct-ID expectation and retained independent errors. | **Pass:** 2026-11-11 run: 17 passed with the `-k` filter (13 baseline + 4 new cases); full file 57 passed; broader run of `tests/model/` plus the projection suite: 300 passed, exit 0. Planning baseline was 13 passed. |
| `V-2` | Projection regressions in `backend/tests/ingesters/test_sead_change_request_target_projection.py`, including `test_direct_foreign_key_keeps_the_target_id_without_a_parent_table` and `test_direct_conditional_fk_skips_projection_diagnostics_for_unselected_malformed_rows`. | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_target_projection.py -q` | Preserved direct-ID projection behavior | Tests pass; direct IDs remain unchanged by the conformance-only change. | **Pass:** 2026-11-11 run: 22 passed, exit 0. Matches planning baseline. |
| `V-3` | Direct-ID validation and packaging in `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py`, including the conditional insert case added by `T1.3`. | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py -q` with the test's `SEAD_DISPOSABLE_POSTGRES_*` loopback settings | `PH1-AC-4` | A selected conditional insert without a required value and an ID absent from the target table are rejected; valid IDs remain accepted. | **Pass:** 2026-11-11 run against a disposable PostgreSQL container (`make pg-disposable-up`, loopback only): 2 passed, exit 0. Planning baseline was 2 skipped. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Conformance behavior | `src/target_model/conformance.py::ConditionalForeignKeyConformanceValidator.validate_global` | `T1.1` | Valid direct-ID conditional FKs do not report awaiting reconciliation. |
| Conformance regressions | `tests/model/test_target_model_conformance.py` | `T1.2` | All specified direct-ID, local-link, invalid-declaration, mixed-source, and required-target cases pass. |
| Conditional direct-ID validation regression | `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py` | `T1.3` | Conditional selected-insert values are checked without changing ingester code. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1 | Complete | None | `T1.1`, `T1.2`, and `T1.3` complete and validated 2026-11-11 (`V-1`, `V-2`, `V-3` pass; pylint 10/10; Black/isort clean). `V-3` ran against a podman disposable PostgreSQL container (`make pg-disposable-up`/`pg-disposable-down`). |

## Definition Of Done

- [x] The source proposal is approved and the plan is no longer blocked. (Approved 2026-11-11.)
- [x] Every phase acceptance criterion has implementation and validation evidence. (`PH1-AC-1`..`PH1-AC-4` demonstrated by `V-1`, `V-2`, and `V-3` on 2026-11-11.)
- [x] All work areas and deliverables are complete. (`T1.1`, `T1.2`, and `T1.3` complete 2026-11-11.)
- [x] Required tests pass, including the conditional direct-ID PostgreSQL regression when the disposable database is available. (`V-1`, `V-2`, and `V-3` pass 2026-11-11.)
- [x] Existing local-link, global-target, and direct-ID behavior is regression-tested. (2026-11-11: `V-1` retained cases plus 300-test broader run pass.)
- [x] No unresolved decision affects implementation, correctness, or validation. (`V-3` ran 2026-11-11 against a disposable database provisioned with `make pg-disposable-up`.)

## Risks And Open Questions

- ~~**Blocking decision:** The source proposal is still marked proposed.~~ Resolved: the proposal was approved on 2026-11-11.
- ~~**Disposable database:** `V-3` requires loopback `SEAD_DISPOSABLE_POSTGRES_*` settings and creates then drops a schema. Run it only against the intended disposable database.~~ Resolved: `scripts/spinup_disposable_postgres.py` (with `make pg-disposable-up`/`pg-disposable-env`/`pg-disposable-status`/`pg-disposable-down`) provisions a loopback-only podman PostgreSQL container; `V-3` ran against it on 2026-11-11 and passed.
