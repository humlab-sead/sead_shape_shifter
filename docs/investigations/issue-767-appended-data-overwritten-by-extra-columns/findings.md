# Investigation findings: #767 — Appended data overwritten by extra columns

**Brief:** [Issue #767](https://github.com/humlab-sead/sead_shape_shifter/issues/767)  
**Status:** Partially conclusive  
**Environment / baseline:** `dev` at `851d01f4`; isolated in-memory DataFrames; no database

## Executive summary

The reported value change is reproducible. When entity A has `extra_columns: {C: 5}` and appends entity B, A's `extra_columns` configuration is inherited by the generated append configuration. During extraction, Shape Shifter removes `C` from the source columns because it treats `C` as a column to generate, then creates `C` using A's value. B's existing value `4` is therefore lost in A's appended rows.

The cause is confirmed for the configuration described in the issue. The referenced `dummy_append` project was not available in this repository, so it could not be checked directly. No application code was changed.

## Verified observations and reproduction

A temporary integration test used an in-memory input with one row and this configuration:

- B adds `C: 4` through `extra_columns`.
- A adds `C: 5` through `extra_columns`.
- A appends B with `columns: [id, C]`.

The equivalent project YAML is:

```yaml
entities:
  B:
    type: fixed
    values:
      - [2]
    keys: [id]
    columns: [id]
    extra_columns:
      C: 4

  A:
    type: fixed
    values:
      - [1]
    keys: [id]
    columns: [id]
    extra_columns:
      C: 5
    append_mode: all
    append:
      - source: B
        columns: [id, C]
```

With this configuration, B has `C = 4`, but A has `C = 5` on both its base row and its appended row.

After normalization, B contains `C = [4]`, while A contains `C = [5, 5]`: the base row has the expected value `5`, but the appended row does not retain B's `4`.

The test also checked a configuration workaround: explicitly setting `extra_columns: {}` on A's append item and listing `C` in its columns produced A's values `[5, 4]`. This workaround is not a code fix and depends on naming the incoming column in the append configuration.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | The issue reports A's `C: 5` replacing B's `C: 4` after append. | [Issue #767](https://github.com/humlab-sead/sead_shape_shifter/issues/767) | Matches the isolated reproduction. | Verified as the reported symptom |
| E2 | Append configurations inherit parent properties unless overridden. `extra_columns` is not excluded; the merge uses the append value when present and otherwise the parent's value. | [`src/model.py:862-918`](../../../src/model.py#L862-L918) | A's `extra_columns: {C: 5}` is present on the generated append configuration. | Verified |
| E3 | `keys_columns_and_fks` includes configured extra-column names; `SubsetService.get_subset_columns()` then removes those names from the source projection. | [`src/model.py:705-731`](../../../src/model.py#L705-L731), [`src/extract.py:24-45`](../../../src/extract.py#L24-L45) | The append extraction does not select B's `C` when A's inherited config also declares `C` as an extra column. | Verified |
| E4 | Extraction evaluates `extra_columns`; constant evaluation assigns the configured value. The evaluator skips an output only if it is already present in the extracted DataFrame. | [`src/extract.py:147-189`](../../../src/extract.py#L147-L189), [`src/transforms/extra_columns.py:135-138`](../../../src/transforms/extra_columns.py#L135-L138), [`src/transforms/extra_columns.py:563-567`](../../../src/transforms/extra_columns.py#L563-L567) | Since extraction removed `C`, the append branch adds it as `5`. | Verified |
| E5 | Temporary reproduction and workaround tests. | `rtk uv run pytest -q tests/integration/test_issue_767_repro_tmp.py` | Both tests passed; the temporary test file was removed afterward. | Verified |
| E6 | Existing append integration tests. | `rtk uv run pytest -q tests/integration/test_append_processing.py` | Passed; one test was skipped. These tests do not cover the colliding `extra_columns` case. | Verified |
| E7 | The configuration guide's append inheritance list does not mention `extra_columns`. | [`docs/CONFIGURATION_GUIDE.md:2783-2825`](../../../docs/CONFIGURATION_GUIDE.md#L2783-L2825) | The documented inheritance contract does not explain the current behavior. | Verified documentation gap |

## Timeline or causal chain

1. On 2025-12-07, commit [`2c186d97`](https://github.com/humlab-sead/sead_shape_shifter/commit/2c186d97) added append support and defaulted an append item's `extra_columns` to an empty mapping when it was not specified.
2. Also on 2025-12-07, commit [`1147e38a`](https://github.com/humlab-sead/sead_shape_shifter/commit/1147e38a) changed append configuration to merge parent and append keys generically. The parent value is used unless the append item overrides it; `extra_columns` was not excluded. This is the earliest source-history change found that makes the parent's `extra_columns` apply to append branches.
3. Issue #767 was opened on 2026-11-20.
4. The behavior reproduces on `dev` at `851d01f4`.

This identifies when the behavior entered the source history, not when a particular deployed environment first received it; deployment history was not available.

## Root-cause assessment

**Confirmed mechanism:** `TableConfig.create_append_config()` inherits A's `extra_columns` into the append configuration for B. `SubsetService` then excludes `C` from the selected source columns and evaluates the inherited constant. The overwrite happens during append-branch extraction, before concatenation.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| A's inherited `extra_columns` replaces B's matching field during append extraction. | Current source behavior and the isolated reproduction produce B `C = 4` and appended A `C = 5`. | None found for the configuration described in the issue. | Verified |
| The parent's post-concatenation `extra_columns` pass changes a value that was already present. | `_process_entity()` evaluates parent extra columns after collecting append branches. | The evaluator skips an output column that already exists. In this case, extraction has already created `C = 5`; the post-concatenation pass is not the first overwrite. | Ruled out as the overwrite point |
| A recent change to preserve explicitly declared append columns introduced this behavior. | Commit `802df2cd` changed handling of inherited `public_id` columns. | Parent `extra_columns` inheritance was introduced in the 2025-12-07 generic merge, well before that change. | Ruled out |

## Impact and extent

**Confirmed affected case:** A source-based append loses an incoming field when its name is also declared in the destination entity's inherited `extra_columns`. The destination's expression is used for the append rows instead.

**Potential wider impact:** The generic merge applies to append configurations beyond source-based appends. Other append types with an incoming field that collides with an inherited extra-column name may follow the same extraction path; that broader case was not separately reproduced.

## Remediation options

For the example above, the intended result is to keep A's generated value on its own row and B's value on the appended row:

| Row in A | Current `C` | Expected `C` |
| --- | ---: | ---: |
| A's base row | 5 | 5 |
| Row appended from B, where B has `C = 4` | 5 | 4 |

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| **Change source-append extraction:** when B already provides a column named `C` and A's `C: 5` was inherited, select B's `C` and do not generate a replacement for that append branch. Keep explicit append-level `extra_columns` mappings authoritative. | Produces A values `[5, 4]` while leaving A's base row at `5`. | Decide how to handle a missing source column and whether a null value in an existing source column should be preserved or filled. | Identify source-append configs and inherited extra-column entries; test the base row, present/missing/null source values, and an explicit append-level override. |
| **Configuration workaround:** set `extra_columns: {}` on A's append item and include `C` in that item's `columns`. | Avoids a code change; this exact configuration was tested and produces A values `[5, 4]`. | Must be repeated for each affected append item. If B's output does not contain `C`, this does not supply a replacement value. | Example: `append: [{source: B, columns: [id, C], extra_columns: {}}]`. Verify that B's output contains `C`. |

The narrow code change is in [`SubsetService.get_subset_columns()`](../../../src/extract.py#L24): for a generated source-append config, keep an incoming source column when its name matches an inherited `extra_columns` output. The append config needs to identify both that it is a source append and which extra-column entries came from A rather than being explicitly declared on the append item. This keeps ordinary extraction unchanged and preserves explicit append-level overrides. Once `C` is selected, the existing [`ExtraColumnEvaluator`](../../../src/transforms/extra_columns.py#L542) skips it because it is already present; the evaluator and concatenation do not need changes.

With that rule, B's `C = 4` is retained. If B has no `C` column, the inherited expression can still add `C = 5`. If B has a `C` column with a null value, this rule preserves the null; filling it instead would require a separate fallback rule.

The tested workaround is the smallest change for this A/B configuration. In the full example above, change A's append entry to:

```yaml
entities:
  A:
    extra_columns:
      C: 5
    append:
      - source: B
        columns: [id, C]
        extra_columns: {}
```

The empty append-level mapping overrides the inherited `C: 5`; the listed `C` is then read from B. A's own `extra_columns` remains unchanged, so A's base row still gets `C = 5`. If the append item instead explicitly declares `extra_columns: {C: 5}`, that explicit rule should continue to produce `5` if explicit append-level mappings are meant to be authoritative.

**Recommended next step:** For a code fix, make a present source value win over the destination's inherited extra-column expression, while leaving A's base-row behavior unchanged. Decide whether an absent source column should stay missing or receive A's value; decide separately whether a null value in an existing source column should be preserved or filled. The issue establishes the expected result when B has `C = 4`, but not those fallback rules.

**Prevention / regression detection:** Add an integration test asserting that the base A row keeps `C = 5` while the appended B row keeps `C = 4`. Include a case for the agreed behavior when B has no `C`, and a case for an explicit append-level override.

## Unresolved questions and blockers

- The referenced `dummy_append` project was not available in this repository; its exact YAML configuration remains unverified.
- The issue does not specify whether a missing or null incoming `C` should remain missing or receive A's configured value.
- The first affected deployed version cannot be established from the available source history.

## Verification record

- `rtk uv run pytest -q tests/integration/test_issue_767_repro_tmp.py` — passed, 2 temporary diagnostic tests. The file was removed after the run.
- `rtk uv run pytest -q tests/integration/test_append_processing.py` — passed, with one skipped test.
- No production or application source changes were made.

## References

- [Issue #767](https://github.com/humlab-sead/sead_shape_shifter/issues/767)
- [`src/model.py`](../../../src/model.py)
- [`src/extract.py`](../../../src/extract.py)
- [`src/transforms/extra_columns.py`](../../../src/transforms/extra_columns.py)
- [`docs/CONFIGURATION_GUIDE.md`](../../../docs/CONFIGURATION_GUIDE.md)
