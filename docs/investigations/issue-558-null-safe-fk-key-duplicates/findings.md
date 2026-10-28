# Investigation findings: issue #558 duplicate FK keys from nonmatching-null merges

- **Brief:** [Issue #558](https://github.com/humlab-sead/sead_shape_shifter/issues/558); no separate investigation brief was supplied
- **Status:** Root cause confirmed; fix implemented in the working tree, pending commit and merge
- **Environment / baseline:** The original reproduction was checked on `dev` at `22a1c2c4` (`v2.5.0-1-g22a1c2c4`) on 2026-10-27. The current working tree includes the terminology rename and the fix described below.

## Executive summary

At the original baseline, a focused `ForeignKeyLinker` reproduction created the reported suffixed copy of a join key when a lookup-style left join had a null key. The fix now coalesces same-named join keys after the temporary-key merge, so the result has one key column and right/outer joins retain remote-only key values. Regression tests cover the merge helper and linker output.

Issue #558 remains open. The fix is local and is not committed or merged. `drop_fk_columns()` still drops a local FK key only when that key is not listed in the entity's configured `columns`; the linker regression also verifies that a configured local key remains and no suffixed duplicate survives that step.

The original reproduction used synthetic in-memory data, not the Arbodat or ecocode datasets. It verifies the baseline code mechanism and output, but does not independently re-run those datasets.

## Verified observations and reproduction

At the original baseline, the linker automatically enabled null-key match prevention for lookup-style left joins unless the FK explicitly set its null-key policy. Its remote projection included the remote join keys, and its merge suffix was `_<remote-entity>`. When the nonmatching-null merge used temporary join keys, pandas treated the original same-named keys as ordinary overlapping columns. The merge retained both copies, and cleanup removed only the temporary columns.

The current fix restores one same-named join-key column after temporary columns are removed. Left and inner joins keep the local key, right joins keep the remote key, and outer joins combine both values so remote-only rows retain their key.

I ran a minimal `ForeignKeyLinker` reproduction with:

- local entity `ecocode` and remote entity `ecocode_definition`
- `left_on=["Ökogruppe"]` and `right_on=["Ökogruppe"]`
- a local `None` key and a matching non-null key
- a lookup-style left join with no explicit null-key constraint

Before the fix, the output included both `Ökogruppe` and `Ökogruppe_ecocode_definition`; the latter contained `"A"` for the matched row and `NaN` for the unmatched row. The linker regression now asserts that the suffixed column is absent.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | Issue status and reproduction reports | [Issue #558](https://github.com/humlab-sead/sead_shape_shifter/issues/558) | GitHub reports the issue as open; its October 24 comment records a second affected entity. | Verified as GitHub issue state and report |
| E2 | Lookup-style left joins prevent null-key matches by default | `src/transforms/link.py:14-33` | `_resolve_fk_runtime_options()` sets `prevent_null_key_matches=True` for lookup-style left joins without an explicit null-key policy. | Verified |
| E3 | Linker passes the runtime option and uses a remote-entity suffix | `src/transforms/link.py:121-122,145-148` | The resolved option reaches `merge_with_nonmatching_null_keys()`; the suffix is `_<remote_entity>`. | Verified |
| E4 | Remote join keys are included in the selected remote columns | `src/model.py:202-210,218-253` | `get_valid_remote_columns()` includes `remote_keys`; `generate_link_setup()` retains those join columns for the merge. | Verified |
| E5 | Baseline nonmatching-null merge used temporary keys but left suffixed source key columns | `src/transforms/utility.py` at the original baseline | The baseline helper removed only temporary columns, leaving same-named source key copies. The current helper coalesces those copies after the merge. | Verified at baseline; fixed in the working tree |
| E6 | Baseline `ForeignKeyLinker` reproduction | In-memory `ShapeShiftProject` / `TableStore` using the inputs above | Baseline output included `Ökogruppe_ecocode_definition` alongside `Ökogruppe`. Current linker regression asserts the suffixed copy is absent. | Verified at baseline and covered by regression |
| E7 | FK-key removal is conditional; normalization does not call it by default | `src/model.py:693-703`; `src/normalizer.py:184,495-503,601-604`; `src/workflow.py:61-64` | `drop_fk_columns()` removes local keys absent from configured `columns`; workflow calls it only when `drop_foreign_keys` is enabled. | Verified |
| E8 | Added regression coverage | `tests/process/test_merge_with_nonmatching_null_keys.py`; `tests/transforms/test_link.py` | Tests cover left, inner, right, and outer joins; default and custom suffixes; composite same-named keys; and linker output after configured FK-column dropping. | Verified |
| E9 | Focused regression tests | `rtk uv run pytest tests/process/test_merge_with_nonmatching_null_keys.py tests/transforms/test_link.py tests/specifications/test_constraints.py -q` | All tests passed with the duplicate-key regression coverage in place. | Verified |
| E10 | Core process suite | `rtk uv run pytest tests/process -q` | All tests passed. | Verified |

## Root-cause assessment

**Confirmed baseline mechanism:** When the helper prevented null-key matches, it joined on temporary left and right key columns. The original source key columns remained in both input frames. If those names overlapped, pandas applied the configured suffix to the remote copy. The helper removed its temporary columns but left the suffixed source column in the result.

The defect requires null-key match prevention to be active, at least one merge key to contain a null, and an overlapping source-column name that pandas will suffix. It does not occur on the ordinary-merge fast path when all merge keys are non-null. It is not limited to entities configured with unnesting.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| The baseline merge helper emitted suffixed join-key copies | The in-memory baseline `ForeignKeyLinker` reproduction produced the suffixed column. | Current regression tests confirm that the working-tree helper removes the duplicate while preserving join-type key values. | Confirmed at baseline; fixed in the working tree |
| The issue only affects explicitly configured `allow_null_keys: true` FKs | The issue's first reproduction used that setting. | `_resolve_fk_runtime_options()` also prevents null-key matches by default for lookup-style left joins without an explicit null-key policy. | Ruled out |
| `drop_foreign_key_columns()` always removes the original key and leaves only the duplicate | At the original baseline, this occurred when a local FK key was not listed in configured `columns`. | It keeps configured local keys; the current linker regression verifies that a configured key remains without a suffixed duplicate. | Baseline behavior was configuration-dependent; duplicate is fixed before this step |

## Impact and extent

**Confirmed affected case at baseline:** A null-containing lookup-style left join with matching local and remote key names produced both original and suffixed key columns in the linked DataFrame. The current regression tests confirm that this output no longer occurs in the working tree.

**Potential wider impact at baseline:** Any entity meeting those conditions could retain an unintended suffixed column in `table_store`, including direct `normalize()` callers. The reproduction does not establish how many real project datasets met the conditions. The issue's reports name `site_location` and `ecocode`, but those source datasets were not independently loaded during this investigation.

## Implemented resolution

After the temporary-key merge, the helper coalesces each pair of same-named join-key columns back to one column. Left and inner joins retain the local value; right joins retain the remote value; outer joins combine both. This fixes the duplicate at the merge source, including for direct `normalize()` callers and workflows that retain FK columns.

Regression tests cover all four join types, default and custom suffixes, composite keys, and a real linker case where the configured local key remains after `drop_fk_columns()`. The issue should remain open until the fix is committed and merged.

## Unresolved questions and blockers

- The original Arbodat and ecocode input datasets were not loaded in this environment, so their current row-level outputs were not independently reproduced.
- No production or staging data was inspected.

## Verification record

- `rtk gh issue view 558 --repo humlab-sead/sead_shape_shifter ...` — issue is open; October 24 comment reports the ecocode case.
- `rtk gh pr list --repo humlab-sead/sead_shape_shifter --state all --search "558" ...` — no matching pull request returned.
- `rtk uv run pytest tests/process/test_merge_with_nonmatching_null_keys.py tests/transforms/test_link.py tests/specifications/test_constraints.py -q` — focused tests passed.
- `rtk uv run pytest tests/process -q` — core process suite passed.
- `rtk uv run black --check ...`, `rtk uv run isort --check-only ...`, and `rtk git diff --check` — passed for the changed Python files.
- `GRAPHIFY_VIZ_NODE_LIMIT=0 ~/.local/bin/graphify update .` — code graph refreshed.
- `rtk uv run python -c '<minimal ShapeShiftProject and ForeignKeyLinker reproduction>'` — reproduced the suffixed column before the fix.
- The fix is implemented locally but not committed or merged; no project data or production state was changed.

## References

- [Issue #558](https://github.com/humlab-sead/sead_shape_shifter/issues/558)
- [`src/transforms/utility.py`](../../../src/transforms/utility.py)
- [`src/transforms/link.py`](../../../src/transforms/link.py)
- [`src/model.py`](../../../src/model.py)
- [`src/normalizer.py`](../../../src/normalizer.py)
- [`src/workflow.py`](../../../src/workflow.py)
- [`tests/process/test_merge_with_nonmatching_null_keys.py`](../../../tests/process/test_merge_with_nonmatching_null_keys.py)
- [`tests/transforms/test_link.py`](../../../tests/transforms/test_link.py)
