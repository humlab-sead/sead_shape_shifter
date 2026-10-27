# Investigation findings: issue #558 duplicate FK keys from nonmatching-null merges

- **Brief:** [Issue #558](https://github.com/humlab-sead/sead_shape_shifter/issues/558); no separate investigation brief was supplied
- **Status:** Conclusive for the current code path
**Environment / baseline:** `dev` at `22a1c2c4` (`v2.5.0-1-g22a1c2c4`), checked 2026-10-27. A later terminology-only rename in this worktree does not change the reported behavior.

## Executive summary

Issue #558 is still relevant and is not fixed in the checked-out code. The issue remains open. A focused reproduction through `ForeignKeyLinker` creates the reported suffixed copy of a join key when a lookup-style left join has a null key. No pull request mentioning `558` appeared in the repository PR search.

The reported `drop_foreign_key_columns()` behavior is conditional: it drops a local FK key only when that key is not listed in the entity's configured `columns`. It does not remove the suffixed remote-key copy. The duplicate itself remains even when the local key is configured as an output column, and `normalize()` does not drop FK columns automatically.

The reproduction used synthetic in-memory data, not the original Arbodat or ecocode datasets. It verifies the current code mechanism and output, but does not independently re-run those datasets.

## Verified observations and reproduction

The current linker automatically enables null-key match prevention for lookup-style left joins unless the FK explicitly sets its null-key policy. Its remote projection includes the remote join keys, and its merge suffix is `_<remote-entity>`. When the nonmatching-null merge uses temporary join keys, pandas treats the original same-named keys as ordinary overlapping columns. The merge therefore retains both copies, and cleanup removes only the temporary columns.

I ran a minimal `ForeignKeyLinker` reproduction with:

- local entity `ecocode` and remote entity `ecocode_definition`
- `left_on=["Ökogruppe"]` and `right_on=["Ökogruppe"]`
- a local `None` key and a matching non-null key
- a lookup-style left join with no explicit null-key constraint

The output included both `Ökogruppe` and `Ökogruppe_ecocode_definition`; the latter contained `"A"` for the matched row and `NaN` for the unmatched row.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | Issue status and reproduction reports | [Issue #558](https://github.com/humlab-sead/sead_shape_shifter/issues/558) | GitHub reports the issue as open; its October 24 comment records a second affected entity. | Verified as GitHub issue state and report |
| E2 | Lookup-style left joins prevent null-key matches by default | `src/transforms/link.py:14-33` | `_resolve_fk_runtime_options()` sets `prevent_null_key_matches=True` for lookup-style left joins without an explicit null-key policy. | Verified |
| E3 | Linker passes the runtime option and uses a remote-entity suffix | `src/transforms/link.py:121-122,145-148` | The resolved option reaches `merge_with_nonmatching_null_keys()`; the suffix is `_<remote_entity>`. | Verified |
| E4 | Remote join keys are included in the selected remote columns | `src/model.py:202-210,218-253` | `get_valid_remote_columns()` includes `remote_keys`; `generate_link_setup()` retains those join columns for the merge. | Verified |
| E5 | Nonmatching-null merge uses temporary keys and removes only those temporary columns | `src/transforms/utility.py:101-118` | When a key contains nulls, the merge uses temporary keys and drops the temporary columns, not same-named source key columns. | Verified |
| E6 | Current `ForeignKeyLinker` reproduction | In-memory `ShapeShiftProject` / `TableStore` using the inputs above | Output columns include `Ökogruppe_ecocode_definition` alongside the original `Ökogruppe`. | Verified |
| E7 | FK-key removal is conditional; normalization does not call it by default | `src/model.py:693-703`; `src/normalizer.py:184,495-503,601-604`; `src/workflow.py:61-64` | `drop_fk_columns()` removes local keys absent from configured `columns`; workflow calls it only when `drop_foreign_keys` is enabled. | Verified |
| E8 | Existing focused tests | `tests/transforms/test_link.py:155-200`; `tests/process/test_merge_with_nonmatching_null_keys.py:136-154` | The linker test checks that null-key match prevention is enabled using a mocked merge; the utility test checks temporary-column cleanup. Neither checks that suffixed join-key duplicates are absent. | Verified |
| E9 | Targeted merge tests | `rtk uv run pytest tests/process/test_merge_with_nonmatching_null_keys.py -q` | All collected tests passed; the suite does not cover the issue's duplicate-column result. | Verified |

## Root-cause assessment

**Confirmed mechanism:** When the helper prevents null-key matches, it joins on temporary left and right key columns. The original source key columns remain in both input frames. If those names overlap, pandas applies the configured suffix to the remote copy. The helper removes its temporary columns but leaves the suffixed source column in the result.

The defect requires null-key match prevention to be active, at least one merge key to contain a null, and an overlapping source-column name that pandas will suffix. It does not occur on the ordinary-merge fast path when all merge keys are non-null. It is not limited to entities configured with unnesting.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| The current merge helper still emits suffixed join-key copies | The in-memory `ForeignKeyLinker` reproduction produces the suffixed column; current source retains the described merge and cleanup behavior. | No contrary code or test evidence found. | Verified |
| The issue only affects explicitly configured `allow_null_keys: true` FKs | The issue's first reproduction used that setting. | `_resolve_fk_runtime_options()` also prevents null-key matches by default for lookup-style left joins without an explicit null-key policy. | Ruled out |
| `drop_foreign_key_columns()` always removes the original key and leaves only the duplicate | This occurs when a local FK key is not listed in configured `columns`. | It keeps local keys that are configured output columns; in either case, it does not remove the suffixed duplicate. | Supported with a configuration-dependent condition |

## Impact and extent

**Confirmed affected case:** A null-containing lookup-style left join with matching local and remote key names produces both original and suffixed key columns in the linked DataFrame.

**Potential wider impact:** Any entity meeting those conditions can retain an unintended suffixed column in `table_store`, including direct `normalize()` callers. The reproduction does not establish how many real project datasets currently meet the conditions. The issue's reports name `site_location` and `ecocode`, but those source datasets were not independently loaded during this investigation.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Remove the remote copy of a join key from the merged output when it duplicates a local key | Prevents an unintended output column at the merge source. | Must preserve configured extra-column behavior and distinct-key joins. | Test same-name and different-name joins, null and non-null key paths, and left-join unmatched rows. |
| Keep the merge output but explicitly remove redundant remote join-key columns | Makes the output cleanup rule visible at the link stage. | Needs care where remote join keys are intentionally requested as extra output data. | Add focused linker regressions for configured and unconfigured FK keys. |
| Change FK-column dropping to remove the suffixed copy | Can clean up output in workflows that enable FK dropping. | Does not fix direct `normalize()` callers or workflows that retain FK columns. | Treat only as supplementary cleanup, not as the complete fix. |

**Recommended next step:** Keep issue #558 open and implement a merge/link-stage fix with a regression test covering lookup joins that prevent null-key matches and have overlapping join-key names. Verify that local configured keys remain intact and that the suffixed remote copy is absent.

**Prevention / regression detection:** Add an assertion to a real `ForeignKeyLinker` test that a null-containing lookup left join does not emit a `_<remote-entity>` copy of a same-named join key. Keep the existing temporary-key cleanup test.

## Unresolved questions and blockers

- The original Arbodat and ecocode input datasets were not loaded in this environment, so their current row-level outputs were not independently reproduced.
- No production or staging data was inspected.
- The appropriate treatment of a remote join key intentionally requested as an extra output column should be preserved or explicitly decided during implementation.

## Verification record

- `rtk gh issue view 558 --repo humlab-sead/sead_shape_shifter ...` — issue is open; October 24 comment reports the ecocode case.
- `rtk gh pr list --repo humlab-sead/sead_shape_shifter --state all --search "558" ...` — no matching pull request returned.
- `rtk uv run pytest tests/process/test_merge_with_nonmatching_null_keys.py -q` — targeted tests passed.
- `rtk uv run python -c '<minimal ShapeShiftProject and ForeignKeyLinker reproduction>'` — reproduced the suffixed column in the current code.
- No source code, project data, or production state was changed.

## References

- [Issue #558](https://github.com/humlab-sead/sead_shape_shifter/issues/558)
- [`src/transforms/utility.py`](../../../src/transforms/utility.py)
- [`src/transforms/link.py`](../../../src/transforms/link.py)
- [`src/model.py`](../../../src/model.py)
- [`src/normalizer.py`](../../../src/normalizer.py)
- [`src/workflow.py`](../../../src/workflow.py)
- [`tests/process/test_merge_with_nonmatching_null_keys.py`](../../../tests/process/test_merge_with_nonmatching_null_keys.py)
- [`tests/transforms/test_link.py`](../../../tests/transforms/test_link.py)
