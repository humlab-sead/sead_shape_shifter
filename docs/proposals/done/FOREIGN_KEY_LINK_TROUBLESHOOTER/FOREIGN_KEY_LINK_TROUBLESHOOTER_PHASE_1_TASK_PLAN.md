# Foreign-Key Link Troubleshooter — Phase 1 Task Plan

Source proposal: [Foreign-Key Link Troubleshooter](FOREIGN_KEY_LINK_TROUBLESHOOTER.md). Source phase plan: [Phase 1: Identify an eligible saved link](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_PLAN.md).

## Phase Summary

**Phase:** Phase 1 — Identify an eligible saved link.

**Goal:** Make each offered troubleshooting action refer to one supported saved FK.

**Plan readiness:** Validated. The phase is marked "Ready for a task plan" in the phase plan. Every target below was verified in the repository, and no open decision can change the implementation.

**Dependencies:** None.

**Constraints (fixed by the phase plan):**

- The action targets a saved FK and must not guess from the A and B entities alone.
- An issue identifies its FK by `fk_index` (position in the owning entity's saved `foreign_keys` list) and a `fk_signature` over `remote_entity`, `local_keys`, `remote_keys`, `how`, `defer_dependency`, and the full constraints block.
- Set the index where `TableConfig.foreign_keys` builds each `ForeignKeyConfig`. Do not change the `ForeignKeyLinker.link_foreign_key` signature or the call signature of `ForeignKeyLinker.link_entity` (tests replace `link_entity` with one-argument functions).
- Record which linking pass raised the issue. Membership of an entity in `DeferredLinkingTracker.deferred` alone does not show this.
- Only `row_count_mismatch` is in scope. `column_count_mismatch` is out of scope.
- No API model change. Issue `metadata` already reaches the browser unchanged.

**Acceptance criteria**

1. [x] `PH1-AC-1` (from `P-AC-1`) A supported inner or left linking warning resolves to exactly one saved FK, including when several FKs share the same entity pair.
2. [x] `PH1-AC-2` (from `P-AC-1`) A warning with no usable FK identity offers no troubleshoot action. That covers missing metadata, an index outside the entity's saved FK list, a signature that no longer matches the saved FK at that index, and right and outer joins. A resolved link that no longer reproduces its warning is Phase 2's state.

## Repository Findings

**Repository basis:** branch `reconciliation-mvp`, commit `9a24a7ec`, planned 2026-10-31. Uncommitted changes were considered: the working tree modifies only `docs/proposals/` files and `tests/test_generate_whats_new.py`, none of which touch the files below. Graphify (`graphify query`) was used for navigation; all findings below were verified in source.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `src/specifications/constraints.py::ForeignKeyConstraintValidator.validate_after_merge` | Returns early when `not self.fk.has_constraints`. Appends `ValidationIssue(issue_type="row_count_mismatch")` when `how != "cross"` and the row count changed. Metadata holds only `row_count_before`, `row_count_after`, `join_type`. | This is the single place to add `fk_index`, `fk_signature`, and `link_pass`. Only FKs with a non-empty `constraints` block can raise the warning. |
| `src/model.py::TableConfig.foreign_keys` | `cached_property` that builds `ForeignKeyConfig(local_entity=..., fk_cfg=fk_data)` for each item in `entity_cfg["foreign_keys"]`, in list order. | Add `enumerate` here and pass the index. The index is the position in the project file list. |
| `src/model.py::ForeignKeyConfig` | `__init__(self, *, local_entity, fk_cfg)`. Properties: `local_keys`, `remote_keys` (both `unique(...)`), `remote_entity` (from key `entity`), `how` (default `"inner"`, may be `None` if the YAML says `how: null`), `defer_dependency`, `constraints` (`ForeignKeyConstraints` wrapping `fk_cfg["constraints"]`, raw dict in `.data`). | Add an optional `fk_index` argument and a signature property. Other constructors (`backend/app/services/validate_fk_service.py` for unsaved edits, tests) keep working because the argument is optional. |
| `src/transforms/link.py::ForeignKeyLinker.link_foreign_key` / `link_entity` | `link_foreign_key` builds the validator through `_build_fk_validator`, which falls back to older test-double constructors. `link_entity` loops `table_cfg.foreign_keys`, skips deferred, unsatisfied, and already-linked FKs. Linking uses `fk.how or "inner"`. | Keep both signatures. Pass the linking pass through a linker attribute and a validator attribute. |
| `src/normalizer.py::ShapeShifter._process_entity`, `retry_linking`, `_link_deferred_foreign_keys` | `link_entity` is called at three sites: after extract (line ~259), after unnest (~282), and in `retry_linking` (~458), which is also what `_link_deferred_foreign_keys` and the post-entity retry call. | Three linking passes exist: `initial`, `after_unnest`, `deferred_retry`. Tracker membership cannot tell them apart. A deferred-then-satisfied FK and an unnest-enabled FK can both be linked in a later `link_entity` call. |
| `tests/process/test_column_availability.py` (`record_link(entity_name)`) and `tests/process/test_shapeshifter.py::test_retry_linking_calls_link_entity` (asserts `call.kwargs["entity_name"]`, linker is a `Mock`) | Test doubles replace `link_entity` with a one-argument function or a `Mock`. | Do not add parameters to `link_entity`. Setting an attribute on the linker works with both doubles. |
| `backend/app/services/shapeshift_service.py::_collect_validation_issues` and `backend/app/validators/data_validation_orchestrator.py::_get_normalizer_additional_issues` | Both copy `issue.metadata` unchanged (`ValidationMapper.from_linker_issue` copies it and adds `issue_type` and `remote_entity` with `setdefault`). `_deduplicate_validation_issues` compares whole dicts. | New metadata reaches the API and browser without code change. Two identical FKs now produce different issues (different `fk_index`), so deduplication no longer merges them. This is intended. |
| `backend/app/mappers/project_mapper.py` (foreign_keys dict-to-list conversion at the entity mapping step) | The mapper keeps list order; a legacy dict form is converted to a list in dict order. | The index refers to the core entity config list produced by `ProjectMapper.to_core*`. The resolver must run on the same `ShapeShiftProject` source as the warning run. |
| `backend/app/services/validate_fk_service.py` | Builds `CoreForeignKeyConfig` from an unsaved edit, or takes `entity_cfg.foreign_keys[index]`. | Unsaved FK configs have `fk_index=None`. The quick Test Join is not changed. |
| `ForeignKeyLinker._resolve_fk_runtime_options` | The null policy also depends on the remote entity's identity columns (`_is_lookup_fk_enrichment`). The signature fixed by the phase plan does not include these. | Phase 1 follows the fixed signature. Phase 2 reproduces the link with the production helper, so this does not affect Phase 1. See Risks. |
| `tests/specifications/test_constraints.py`, `tests/transforms/test_link.py`, `tests/integration/test_circular_dependency.py` | Existing patterns for building projects, FKs, linkers, and a `defer_dependency` circular project. | Reuse these patterns for new tests. |
| `pyproject.toml` pytest `addopts` | `-qq -rfEx --strict-markers --durations=10 -n auto`: no pass-count summary is printed. | Treat exit code 0 as pass. |

## Scope

**In scope**

- `fk_index` on `ForeignKeyConfig` and a deterministic `identity_signature`.
- `fk_index`, `fk_signature`, and `link_pass` in `row_count_mismatch` issue metadata.
- A pure resolver in `src/` that turns a `row_count_mismatch` issue plus a project into a resolved saved FK or a named "no action" result.
- Tests at the core, linker, normalizer, and backend collection levels.

**Out of scope**

- Baseline reproduction, trial keys, row diagnostics, endpoints, and UI (Phases 2–4).
- `column_count_mismatch` metadata.
- Changes to API models, `ValidationMapper`, `_collect_validation_issues`, the frontend, or the quick Test Join.
- User-facing documentation (the troubleshooter is not exposed until Phase 4).

**Affected layers:** core model (`src/model.py`), core constraints (`src/specifications/constraints.py`), core linker and normalizer (`src/transforms/link.py`, `src/normalizer.py`), a new core resolver module, and tests. The backend is only covered by tests.

## Work Breakdown

### Area 1: Saved-FK identity on `ForeignKeyConfig`

**Objective:** Each FK built from a project entity knows its list position and has a stable signature.

**Affected code:** `src/model.py::ForeignKeyConfig`, `src/model.py::TableConfig.foreign_keys`; `tests/model/test_foreign_key_identity.py` (`NEW`).

**Dependencies:** None.

**Tasks:**

* [x] `T1.1` **Change:** Add an optional `fk_index` to `ForeignKeyConfig` and set it from `TableConfig.foreign_keys`.
  * **Target:** `src/model.py::ForeignKeyConfig.__init__`, `src/model.py::TableConfig.foreign_keys`.
  * **Current → required:** The FK has no index → `ForeignKeyConfig.__init__(self, *, local_entity, fk_cfg, fk_index: int | None = None)` stores `self.fk_index`. `TableConfig.foreign_keys` uses `enumerate` and passes `fk_index=index`.
  * **Implementation:** Keep the keyword-only style. Update the docstring `Args` to describe `fk_index` as the position in the owning entity's saved `foreign_keys` list, or `None` when the FK was not built from a saved list.
  * **Constraints:** Do not change `ForeignKeyLinker` or `link_foreign_key`. Existing direct constructions stay valid.
  * **Validation:** `V-1`.
* [x] `T1.2` **Change:** Add `ForeignKeyConfig.identity_signature`.
  * **Target:** `src/model.py::ForeignKeyConfig` (new property next to `has_constraints`).
  * **Current → required:** No signature → a property returning the SHA-256 hex digest of `json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)`, where `payload = {"remote_entity": self.remote_entity, "local_keys": self.local_keys, "remote_keys": self.remote_keys, "how": self.how or "inner", "defer_dependency": self.defer_dependency, "constraints": self.constraints.data}`.
  * **Implementation:** Add `import hashlib` and `import json` if missing. Use `self.constraints.data` so the full constraints block is included (all keys, not a subset). `how or "inner"` matches how the linker treats a missing join type.
  * **Constraints:** The signature must not include `extra_columns`, `drop_remote_id`, or the index; the phase plan fixes the field list. Equal entries must give equal signatures; any change to a listed field, including one constraints key, must change it.
  * **Validation:** `V-1`.
* [x] `T1.3` **Test:** Add model-level tests.
  * **Target:** `tests/model/test_foreign_key_identity.py` (`NEW`).
  * **Current → required:** No tests → build a `ShapeShiftProject` (as in `tests/specifications/test_constraints.py::build_project`) with an entity that has three FKs: two to the same remote entity with different `local_keys`, and one exact duplicate of the first.
  * **Implementation:** Assert `[fk.fk_index for fk in table.foreign_keys] == [0, 1, 2]`; assert a `ForeignKeyConfig(local_entity=..., fk_cfg=...)` built directly has `fk_index is None`; assert the exact duplicate has the same signature but a different index; assert the signature changes when each of `entity`, `local_keys`, `remote_keys`, `how`, `defer_dependency`, and a single constraints key (for example `allow_row_decrease`) changes; assert it is unchanged when only `extra_columns` changes; assert a missing `how` and `how: "inner"` give the same signature.
  * **Constraints:** No I/O; no database.
  * **Validation:** `V-1`.

**Completion evidence:** `V-1` passes.

### Area 2: Record FK identity and linking pass in the warning

**Objective:** Every `row_count_mismatch` issue carries `fk_index`, `fk_signature`, and `link_pass`.

**Affected code:** `src/specifications/constraints.py::ForeignKeyConstraintValidator`, `src/transforms/link.py::ForeignKeyLinker`, `src/normalizer.py::ShapeShifter`; `tests/specifications/test_constraints.py`, `tests/transforms/test_link.py`, `tests/process/test_shapeshifter.py`, `tests/integration/test_circular_dependency.py`.

**Dependencies:** Area 1.

**Tasks:**

* [x] `T2.1` **Change:** Add the three keys to the `row_count_mismatch` metadata.
  * **Target:** `src/specifications/constraints.py::ForeignKeyConstraintValidator.__init__` and `.validate_after_merge`.
  * **Current → required:** Metadata has `row_count_before`, `row_count_after`, `join_type` → it also has `"fk_index": self.fk.fk_index`, `"fk_signature": self.fk.identity_signature`, `"link_pass": self.link_pass`. `__init__` sets `self.link_pass: str = "initial"`.
  * **Implementation:** Leave `column_count_mismatch` metadata unchanged. Leave the early return for FKs without constraints unchanged.
  * **Constraints:** Existing keys and message text stay the same. `fk_index` is `None` for FKs built without an index.
  * **Validation:** `V-2`.
* [x] `T2.2` **Change:** Define the linking-pass values and pass the current value to each validator.
  * **Target:** `src/transforms/link.py` (module-level `LinkPass = Literal["initial", "after_unnest", "deferred_retry"]`; `ForeignKeyLinker.__init__`; `ForeignKeyLinker.link_foreign_key`).
  * **Current → required:** No pass information → `ForeignKeyLinker.__init__` sets `self.link_pass: LinkPass = "initial"`. `link_foreign_key` currently chains `_build_fk_validator(...).validate_before_merge(local_df, remote_df)` in one expression. Split it: build the validator, set `validator.link_pass = self.link_pass`, then call `validator.validate_before_merge(local_df, remote_df)` (it returns the validator) and keep appending the result to `self.validators`.
  * **Implementation:** Attribute assignment works for the real validator and for simple test doubles. Do not add parameters to `link_foreign_key` or `link_entity`.
  * **Constraints:** `ForeignKeyLinker.link_foreign_key(local_df, fk, remote_df)` signature and return value stay unchanged. `_build_fk_validator` fallback behavior stays.
  * **Validation:** `V-3`, `V-8`.
* [x] `T2.3` **Change:** Set the linking pass at each normalizer call site.
  * **Target:** `src/normalizer.py::ShapeShifter._process_entity` (the two `self.linker.link_entity(entity_name=entity)` calls) and `ShapeShifter.retry_linking`.
  * **Current → required:** All calls look the same → each call sets `self.linker.link_pass` before the call and restores `"initial"` in a `finally` block: `"initial"` for the call after extract, `"after_unnest"` for the call after `unnest_entity`, `"deferred_retry"` for every call inside `retry_linking`. Add a private helper `_link_entity(self, entity_name: str, link_pass: LinkPass) -> None` that wraps the try/finally and calls `self.linker.link_entity(entity_name=entity_name)`, then use it at all three sites.
  * **Implementation:** The helper must call `link_entity` with the keyword `entity_name=` so existing assertions on `call.kwargs["entity_name"]` still hold. Import `LinkPass` from `src.transforms.link` (absolute import; the module is already imported there).
  * **Constraints:** Do not change processing order. `retry_linking` keeps iterating over `list(self.linker.deferred_tracker.deferred)`. Tests that replace `linker` with a `Mock` or `link_entity` with a one-argument function must still pass.
  * **Validation:** `V-4`, `V-8`.
* [x] `T2.4` **Test:** Cover the metadata at validator and linker level.
  * **Target:** `tests/specifications/test_constraints.py` (existing) and `tests/transforms/test_link.py` (existing).
  * **Current → required:** No assertions on identity metadata → add tests as follows.
  * **Implementation:** In `test_constraints.py`, reuse `build_project(constraints={"allow_row_decrease": False})`, run `validate_before_merge` then `validate_after_merge` with a left frame of three rows and a linked frame of two rows, and assert the single `row_count_mismatch` issue metadata contains `fk_index == 0`, `fk_signature == fk.identity_signature`, and `link_pass == "initial"`; repeat with `validator.link_pass = "deferred_retry"`. In `test_link.py`, use a real `ForeignKeyLinker` with an inner join that drops a row, a non-empty `constraints` block, and the second FK of an entity with two FKs to the same remote entity; assert `linker.validators[-1].issues[0].metadata["fk_index"] == 1` and that setting `linker.link_pass = "after_unnest"` before `link_foreign_key` gives `link_pass == "after_unnest"`. Add a negative case: an FK without a `constraints` block produces no issue (existing behavior preserved).
  * **Constraints:** Use data that matches existing test fixtures in each file.
  * **Validation:** `V-2`, `V-3`.
* [x] `T2.5` **Test:** Cover the three linking passes at normalizer level.
  * **Target:** `tests/process/test_shapeshifter.py` (existing) and `tests/integration/test_circular_dependency.py` (existing).
  * **Current → required:** No pass assertions → add tests as follows.
  * **Implementation:** In `test_shapeshifter.py`, add `test_retry_linking_marks_deferred_retry_pass`: use the setup from `test_retry_linking_calls_link_entity` with a `Mock` linker whose `link_entity` side effect records `normalizer.linker.link_pass`; assert every recorded value is `"deferred_retry"` and that `link_pass` is `"initial"` after `retry_linking()` returns, also when `link_entity` raises. Add `test_process_entity_marks_after_unnest_pass`, modeled on `tests/process/test_column_availability.py` (the `measurement` entity with `unnest`): wrap `normalizer.linker.link_entity` in a function that records `normalizer.linker.link_pass`, and assert the order `["initial", "after_unnest"]` for the entity's two linking calls. In `test_circular_dependency.py`, add a test that reuses the `test_circular_dependency_with_defer_flag_should_succeed` config, wraps `normalizer.linker.link_entity` with a recorder, runs `normalize()`, and asserts `"deferred_retry"` appears for `abundance` and `"initial"` appears for the first call.
  * **Constraints:** Tests must not depend on the number of retries.
  * **Validation:** `V-4`.

**Completion evidence:** `V-2`, `V-3`, and `V-4` pass; existing link and normalizer tests (`V-8`) still pass.

### Area 3: Resolve a warning to one saved FK

**Objective:** A pure function returns the single saved FK for a supported warning, or a named reason for offering no action.

**Affected code:** `src/transforms/link_resolution.py` (`NEW`); `tests/transforms/test_link_resolution.py` (`NEW`).

**Dependencies:** Areas 1 and 2.

**Tasks:**

* [x] `T3.1` **Change:** Create the resolver module.
  * **Target:** `src/transforms/link_resolution.py` (`NEW`).
  * **Current → required:** No resolver → add:
    * `SUPPORTED_JOIN_TYPES: tuple[str, ...] = ("inner", "left")`.
    * `ResolutionStatus = Literal["resolved", "not_row_count_issue", "entity_not_found", "missing_metadata", "index_out_of_range", "signature_mismatch", "unsupported_join"]`.
    * `@dataclass(frozen=True) class LinkIssueResolution` with fields `status: ResolutionStatus`, `entity_name: str`, `fk_index: int | None = None`, `fk: ForeignKeyConfig | None = None`, `link_pass: str | None = None`, and a property `is_eligible` that is `True` only for `"resolved"`.
    * `def resolve_row_count_issue(project: ShapeShiftProject, *, issue_type: str, local_entity: str, metadata: Mapping[str, Any]) -> LinkIssueResolution`.
  * **Implementation:** Check in this order and return at the first failure: (1) `issue_type != "row_count_mismatch"` → `not_row_count_issue`; (2) `not project.has_table(local_entity)` → `entity_not_found`; (3) `fk_index` is missing, not an `int`, or a `bool`, or `fk_signature` is missing or not a `str` → `missing_metadata`; (4) `fk_index` outside `range(len(table.foreign_keys))` (negative included) → `index_out_of_range`; (5) `table.foreign_keys[fk_index].identity_signature != fk_signature` → `signature_mismatch`; (6) the saved FK's `how or "inner"` is not in `SUPPORTED_JOIN_TYPES` → `unsupported_join`; otherwise `resolved` with `fk`, `fk_index`, and `link_pass` copied from the metadata when it is a `str`, otherwise `None`. Do not scan other FKs: the index identifies one entry, and entries with identical signatures behave the same for count diagnostics, so a duplicate does not cause rejection. The function reads only its arguments and never raises for bad metadata.
  * **Constraints:** Absolute imports only (`from src.model import ForeignKeyConfig, ShapeShiftProject`). No import from `backend`. Use `TYPE_CHECKING` only if a circular import appears. Do not infer the FK from `remote_entity` or `join_type` in the metadata. The module does not read data frames or files. Docstring wording follows the repository vocabulary rules (behavior first, no abstract terms).
  * **Validation:** `V-5`.
* [x] `T3.2` **Test:** Cover every resolver status and the repeated-pair cases.
  * **Target:** `tests/transforms/test_link_resolution.py` (`NEW`).
  * **Current → required:** No tests → build projects with `ShapeShiftProject(cfg=...)` and issue metadata built from `fk.fk_index` and `fk.identity_signature`.
  * **Implementation:** Cases: (a) inner FK resolves to its index with `is_eligible` true and `link_pass` copied; (b) left FK resolves; (c) two FKs to the same remote entity with different keys: each issue resolves to its own index; (d) two identical FKs (same signature): each issue resolves to its own index and neither is rejected; (e) metadata without `fk_index`, with `fk_index=None`, with a `bool`, with a string index, and without `fk_signature` → `missing_metadata`; (f) `fk_index` equal to the list length and `-1` → `index_out_of_range`; (g) the saved entry at that index was edited (changed `remote_keys`, changed `how` from `left` to `inner`, changed one constraints key) → `signature_mismatch`; (h) FKs inserted before the target FK shift the index → `signature_mismatch` rather than a wrong match; (i) `how: "right"` and `how: "outer"` with matching metadata → `unsupported_join`, and `how: "cross"` → `unsupported_join`; (j) `issue_type="column_count_mismatch"` → `not_row_count_issue`; (k) unknown `local_entity` → `entity_not_found`. Add one end-to-end case: run a real `ForeignKeyLinker` (pattern from `tests/transforms/test_link.py`) over two same-pair FKs with data that drops rows in each, take `linker.validators` issue metadata, and resolve each issue against the project; assert each resolves to the FK that raised it.
  * **Constraints:** Tests only call public functions and attributes.
  * **Validation:** `V-5`.

**Completion evidence:** `V-5` passes.

### Area 4: Confirm the metadata reaches API issue payloads

**Objective:** The new metadata survives the existing backend collection and mapping paths unchanged.

**Affected code:** `backend/tests/services/test_shapeshift_service.py` (existing), `backend/tests/mappers/test_validation_mapper.py` (existing). No backend production code changes.

**Dependencies:** Area 2.

**Tasks:**

* [x] `T4.1` **Test:** Assert that identity metadata is preserved.
  * **Target:** `backend/tests/services/test_shapeshift_service.py::TestShapeShiftService` (add `test_collect_validation_issues_preserves_fk_identity_metadata`) and `backend/tests/mappers/test_validation_mapper.py` (add `test_from_linker_issue_preserves_fk_identity_metadata`).
  * **Current → required:** Tests use metadata with row counts only → add tests with `fk_index`, `fk_signature`, `link_pass` in the metadata.
  * **Implementation:** Service test: a `MagicMock` linker whose `validators` is `[MagicMock(issues=[LinkerValidationIssue(...)])]` (pattern at the `row_count_mismatch` preview test and `test_collect_validation_issues_includes_unresolved_extra_columns`); assert `_collect_validation_issues(...)[0]["metadata"]` keeps the three keys. Also assert `_deduplicate_validation_issues` keeps two issues that differ only in `fk_index`. Mapper test: `ValidationMapper.from_linker_issue(...)` result `.metadata` contains the three keys plus `issue_type` and `remote_entity`.
  * **Constraints:** Do not change production backend code. If either test fails, stop and report; do not widen scope.
  * **Validation:** `V-6`.

**Completion evidence:** `V-6` passes.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-1`) | `T1.1`, `T1.2`, `T1.3`, `T2.1`, `T2.2`, `T2.3`, `T2.4`, `T2.5`, `T3.1`, `T3.2`, `T4.1` | `V-1`, `V-2`, `V-3`, `V-4`, `V-5`, `V-6` | An inner or left `row_count_mismatch` carries `fk_index`, `fk_signature`, and `link_pass`; the resolver returns `resolved` with the FK that raised it, including for two FKs with the same entity pair (different keys, or identical signatures), and for a deferred retry. |
| `PH1-AC-2` (from `P-AC-1`) | `T3.1`, `T3.2`, `T1.2`, `T1.3` | `V-5`, `V-1` | Resolver returns `missing_metadata`, `index_out_of_range`, `signature_mismatch`, or `unsupported_join` (right, outer, and cross) and `is_eligible` is false in each case. |

Validation milestone `VM-1` of the phase plan is covered by `V-1`, `V-4`, and `V-5` together.

## Validation And Testing

Pytest runs with `-n auto -qq`, which prints no pass count. A passing run exits with code 0; read failures from the `-rfEx` section.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | FK index and signature tests | `uv run pytest tests/model/test_foreign_key_identity.py tests/model/test_model.py` | `PH1-AC-1`, `PH1-AC-2` | Exit 0 | `tests/model/test_model.py` Pass (exit 0, 2026-10-31); new file Not run: `NEW` |
| `V-2` | Validator metadata tests | `uv run pytest tests/specifications/test_constraints.py` | `PH1-AC-1` | Exit 0; metadata has the three keys; FK without constraints raises no issue | Pass (exit 0, 2026-10-31) |
| `V-3` | Linker tests | `uv run pytest tests/transforms/test_link.py tests/transforms/test_link_extra_columns_chain.py tests/transforms/test_link_duplicate_column_bug.py tests/test_fk_extra_columns_linking.py` | `PH1-AC-1` | Exit 0 | `test_link.py` Pass (exit 0, 2026-10-31); the other three Not run: not part of the baseline run |
| `V-4` | Normalizer linking-pass tests | `uv run pytest tests/process/test_shapeshifter.py tests/process/test_deferred_linking_tracker.py tests/process/test_column_availability.py tests/integration/test_circular_dependency.py` | `PH1-AC-1` | Exit 0; recorded passes are `initial`, `after_unnest`, `deferred_retry` as specified | `test_shapeshifter.py` and `test_deferred_linking_tracker.py` Pass (exit 0, 2026-10-31); the other two Not run: not part of the baseline run |
| `V-5` | Resolver tests | `uv run pytest tests/transforms/test_link_resolution.py` | `PH1-AC-1`, `PH1-AC-2` | Exit 0; every status in `T3.2` covered | Not run: `NEW` |
| `V-6` | Backend collection and mapper tests | `uv run pytest backend/tests/services/test_shapeshift_service.py backend/tests/mappers/test_validation_mapper.py backend/tests/validators/test_data_validation_orchestrator.py` | `PH1-AC-1` | Exit 0; metadata preserved; no production backend change | Pass (exit 0, 2026-10-31) for `test_shapeshift_service.py`, `test_data_validation_orchestrator.py`, and `test_validation_mapper.py` |
| `V-7` | Formatting and lint on changed files | `uv run black --check <changed .py files>` and `uv run isort --check-only <changed .py files>` and `make pylint-changed` | Code quality | Exit 0 for each | Not run: no code changed during planning |
| `V-8` | Regression run for existing behavior | `uv run pytest tests/transforms tests/process tests/specifications tests/model tests/integration backend/tests/services backend/tests/validators backend/tests/mappers` | Existing behavior | Exit 0; no regressions in test doubles that replace `link_entity` | Not run: the full set was not run during planning. The subsets marked Pass in `V-1` to `V-6` passed. |
| `V-9` | Import-boundary and link checks | `! grep -rnE "^\s*(from\|import) backend" src` and `scripts/check_doc_links.sh` | Architecture rules, document links | Both exit 0: no `backend` import in `src/`; "Documentation links are valid." (`make check-imports` is not usable: `scripts/check_imports.py` does not exist) | Pass (exit 0, 2026-10-31, with this plan file present) |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| FK index and signature | `src/model.py::ForeignKeyConfig`, `src/model.py::TableConfig.foreign_keys` | `T1.1`, `T1.2` | `V-1` |
| Model identity tests | `tests/model/test_foreign_key_identity.py` (`NEW`) | `T1.3` | `V-1` |
| Warning metadata | `src/specifications/constraints.py::ForeignKeyConstraintValidator` | `T2.1` | `V-2` |
| Linking-pass attribute | `src/transforms/link.py::ForeignKeyLinker`, `LinkPass` | `T2.2` | `V-3` |
| Linking-pass call sites | `src/normalizer.py::ShapeShifter._link_entity`, `_process_entity`, `retry_linking` | `T2.3` | `V-4` |
| Validator and linker tests | `tests/specifications/test_constraints.py`, `tests/transforms/test_link.py` | `T2.4` | `V-2`, `V-3` |
| Normalizer and circular tests | `tests/process/test_shapeshifter.py`, `tests/integration/test_circular_dependency.py` | `T2.5` | `V-4` |
| Resolver | `src/transforms/link_resolution.py` (`NEW`) | `T3.1` | `V-5` |
| Resolver tests | `tests/transforms/test_link_resolution.py` (`NEW`) | `T3.2` | `V-5` |
| Backend pass-through tests | `backend/tests/services/test_shapeshift_service.py`, `backend/tests/mappers/test_validation_mapper.py` | `T4.1` | `V-6` |

No documentation or generated-artifact change is part of this phase. After code changes, refresh the knowledge graph as the repository instructions require: `GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .`.

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Saved-FK identity on `ForeignKeyConfig` | Done | None | `V-1` passed |
| Area 2: Record FK identity and linking pass | Done | Area 1 | `V-2`, `V-3`, `V-4` passed |
| Area 3: Resolve a warning to one saved FK | Done | Areas 1, 2 | `V-5` passed |
| Area 4: Confirm the metadata reaches API payloads | Done | Area 2 | Tests only; `V-6` passed |

## Definition Of Done

* [x] `PH1-AC-1` and `PH1-AC-2` each have implementation and passing validation evidence (`V-1` to `V-6`).
* [x] All four work areas and the deliverables table are complete.
* [x] `V-7`, `V-8`, and `V-9` pass. `V-7` keeps the 38 pre-existing pylint findings that the unmodified `tests/transforms/test_link.py` already has; every changed and new file is clean.
* [x] Existing tests that replace `link_entity` or use a `Mock` linker still pass without changes to their signatures.
* [x] `row_count_mismatch` messages and existing metadata keys are unchanged; `column_count_mismatch` is unchanged.
* [x] No production change in `backend/`, `frontend/`, or API models.
* [x] The Progress Tracker in this plan shows each area as Done.
* [x] Deviations and follow-up work are documented here.
* [x] No unresolved question affects implementation, correctness, or validation.

## Execution Evidence

Implemented 2026-11-02 on branch `feature/foreign-key-link-troubleshooter` at commit `ed42bd5b`. The plan recorded `reconciliation-mvp` / `9a24a7ec`; every symbol named in Repository Findings was re-verified in the current branch before editing, and no finding differed.

| Check | Result |
| --- | --- |
| `V-1` | Pass, exit 0. `tests/model/test_foreign_key_identity.py` adds 14 cases; `tests/model/test_model.py` still passes. |
| `V-2` | Pass, exit 0. Metadata carries `fk_index`, `fk_signature`, and `link_pass`; a foreign key without constraints raises no issue. |
| `V-3` | Pass, exit 0. Linker records index 1 for the second FK of a repeated entity pair and the pass set on the linker. |
| `V-4` | Pass, exit 0. Recorded passes are `initial`, `after_unnest`, and `deferred_retry`; a failing retry restores `initial`. |
| `V-5` | Pass, exit 0. 25 cases cover every resolver status, repeated pairs, identical entries, and a real linker run. |
| `V-6` | Pass, exit 0. Preview payload, deduplication, and the mapper keep the three keys; no production backend change. |
| `V-7` | `black --check` and `isort --check-only` pass on all 13 changed or new files. `make pylint-changed` exits 2 with 38 findings, all inside lines 234–842 of `tests/transforms/test_link.py`, which are unchanged by this work; the same findings exist for that file at `HEAD`. New and changed code adds no finding. |
| `V-8` | Pass, exit 0 for `tests/transforms`, `tests/process`, `tests/specifications`, `tests/model`, `tests/integration`, and the three backend test folders. |
| `V-9` | Pass. No `backend` import under `src/`; `scripts/check_doc_links.sh` reports "Documentation links are valid." |

**Deviations**

- The validator-level metadata test (`tests/specifications/test_constraints.py`) builds `ForeignKeyConstraintValidator` with `raise_on_violation=False`. `allow_row_decrease: False` otherwise raises `ForeignKeyConstraintViolation` before the row-count issue is recorded. The linker-level test therefore uses `allow_row_decrease: True`, because `ForeignKeyLinker` always builds its validator with the default raising behavior.
- `ShapeShift._link_entity` restores `link_pass` to `"initial"` rather than to a saved previous value. Linking passes do not nest, so the behavior matches the plan.
- The workspace `.venv/` was missing the test extras, so `uv pip install -e ".[all]"` was run before the validation commands. No project file was changed by that step.

**Remaining work:** None in Phase 1. Phase 2 needs its named link-input decision before a task plan can be Validated.

## Risks And Open Questions

**Implementation handoff:** If verified repository state conflicts with this plan (for example `link_entity` call sites or `ForeignKeyConfig` differ from the findings), stop and report the evidence. Do not invent a replacement design or broaden scope.

**Risks**

- **Index meaning depends on the project source.** `fk_index` is the position in the core entity config built by `ProjectMapper.to_core*`. A resolver caller must use the same source as the warning run. Phase 2 and Phase 4 callers must load the saved project the same way the preview and validation runs do. The signature check catches edits made after the run.
- **Signature does not cover the remote entity's identity columns.** The null-key policy in `_resolve_fk_runtime_options` also depends on the remote entity's `system_id` and `public_id`. This follows the phase plan's fixed signature. Phase 2 reproduces the link with the production helper, so a changed remote identity shows up there as a non-reproduced baseline. Recommended resolution: keep as planned.
- **Cross joins.** The phase plan says eligibility rejects only right and outer joins because cross joins never raise `row_count_mismatch`. The resolver allows only inner and left, so cross joins are also rejected. This is a stricter, safe superset and matches `P-AC-1`.
- **Deduplication behavior changes.** `_deduplicate_validation_issues` compares whole dicts. Two identical FKs with the same warning now produce two issues, one per index. This is intended because each has its own saved entry. `T4.1` documents it with a test.
- **Legacy dict-form `foreign_keys`.** `ProjectMapper` converts a dict-form `foreign_keys` into a list in dict order. The index refers to that list order. No change needed in Phase 1.

**Open questions:** None.
