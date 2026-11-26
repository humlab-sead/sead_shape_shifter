# Investigation findings: #767 — Appended data overwritten by extra columns

**Brief:** [Issue #767](https://github.com/humlab-sead/sead_shape_shifter/issues/767)  
**Status:** Conclusive on cause and local fix; deployment history unknown

**Environment / baseline:** Initial in-memory reproduction on `dev` at `851d01f4`; actual project and local Access database failed before the fix and passed afterward on `dev` at `e2833142` (uncommitted worktree changes)

## Executive summary

The reported value change is reproducible. When entity A has `extra_columns: {C: 5}` and appends entity B, A's `extra_columns` configuration is inherited by the generated append configuration. During extraction, Shape Shifter omits B's `C` (whether it was explicitly listed on the append item or not), then creates `C` using A's value. B's existing value `4` is therefore lost in A's appended rows.

The cause is confirmed for the configuration described in the issue. Before the fix, the actual [`dummy-append` project](../../../data/projects/dummy-append/shapeshifter.yml) was run against its local Access database: B had `extra_col_from_entity_b`, but the appended row in A had `Extra value from entity a`. The local fix now retains B's value in the appended row while preserving A's value on its five original rows. This has been verified locally, not deployed.

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
    public_id: b_id
    keys: [id]
    columns: [id]
    extra_columns:
      C: 4

  A:
    type: fixed
    values:
      - [1]
    public_id: a_id
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

### Actual `dummy-append` project

The project file at [`data/projects/dummy-append/shapeshifter.yml`](../../../data/projects/dummy-append/shapeshifter.yml) uses a SQL query against the local `ArchBotStrukDat.mdb` Access database for `entity_a`, a fixed row for `entity_b`, and `append: [{source: entity_b}]` with no explicit append columns. With the two local data directories supplied for its directives, normalization completed and returned five SQL base rows plus one appended row in A. B's `extra_col` is `extra_col_from_entity_b`; the appended row in A instead has `Extra value from entity a`. All five base rows in A have A's configured value.

Run from the repository root to reproduce the failing assertion without printing database records:

```bash
GLOBAL_DATA_SOURCE_DIR="$PWD/data/shared/data-sources" \
GLOBAL_DATA_DIR="$PWD/data/shared/shared-data" \
uv run python - <<'PY'
import asyncio
from pathlib import Path

from loguru import logger
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.table_store import TableStore

logger.remove()
project = ShapeShiftProject.from_file(
    filename=str(Path("data/projects/dummy-append/shapeshifter.yml").resolve()), env_file=None
)
assert project.data_sources["arbodat-lookup"]["driver"] == "ucanaccess"
assert Path(project.data_sources["arbodat-lookup"]["options"]["filename"]).is_file()

async def check():
    shifter = ShapeShifter(project=project, table_store=TableStore({}), default_entity=project.metadata.default_entity)
    await shifter.normalize()
    b = shifter.table_store["entity_b"]
    a = shifter.table_store["entity_a"]
    source_row = "beschreibung from entity_b"
    assert b.loc[b["Beschreibung"] == source_row, "extra_col"].tolist() == ["extra_col_from_entity_b"]
    actual = a.loc[a["Beschreibung"] == source_row, "extra_col"].tolist()
    print("Appended extra_col:", actual)
    assert actual == ["extra_col_from_entity_b"]

asyncio.run(check())
PY
```

Before the fix, the final assertion failed with `Appended extra_col: ['Extra value from entity a']`. After the fix, the same project and local database return `['extra_col_from_entity_b']` and the assertion passes. This is a run of the supplied SQL project, not just an in-memory approximation.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | The issue reports A's `C: 5` replacing B's `C: 4` after append. | [Issue #767](https://github.com/humlab-sead/sead_shape_shifter/issues/767) | Matches the isolated reproduction. | Verified as the reported symptom |
| E2 | Append configurations inherit parent properties unless overridden. `extra_columns` is not excluded; the merge uses the append value when present and otherwise the parent's value. | [`TableConfig.create_append_config()`](../../../src/model.py#L870) | A's `extra_columns: {C: 5}` is present on the generated append configuration. | Verified |
| E3 | `keys_columns_and_fks` starts with the append item's configured columns, which do not automatically include extra-column outputs. Before the fix, `get_subset_columns()` also removed any configured column whose name matched an extra-column output. | [`keys_columns_and_fks`](../../../src/model.py#L713), [`get_subset_columns()`](../../../src/extract.py#L24) | In `dummy-append`, inherited `columns: [Beschreibung]` never selected B's `extra_col`; in the explicit-column reproduction, the matching field was removed. | Verified before the fix |
| E4 | Extraction evaluates `extra_columns`; constant evaluation assigns the configured value. The evaluator skips an output only if it is already present in the extracted DataFrame. | [`get_subset2()`](../../../src/extract.py#L92), [`src/transforms/extra_columns.py:135-138`](../../../src/transforms/extra_columns.py#L135-L138), [`evaluate_extra_columns()`](../../../src/transforms/extra_columns.py#L542) | Before the fix, extraction removed `C`, so the append branch added it as `5`. | Verified before the fix |
| E5 | Temporary reproduction and workaround tests. | `rtk uv run pytest -q tests/integration/test_issue_767_repro_tmp.py` | Both tests passed; the temporary test file was removed afterward. | Verified |
| E6 | Existing append integration tests. | `rtk uv run pytest -q tests/integration/test_append_processing.py` | Passed; one test was skipped. These tests do not cover the colliding `extra_columns` case. | Verified |
| E7 | Before the fix, the configuration guide's append inheritance list did not mention `extra_columns`. | [`docs/CONFIGURATION_GUIDE.md:2783-2825`](../../../docs/CONFIGURATION_GUIDE.md#L2783-L2825) | The inheritance and source-precedence rules are now documented in the configuration guide. | Verified before the fix; corrected locally |
| E8 | In-memory equivalent of the supplied `dummy_append` excerpt, with fixed A instead of its SQL source and `append: [{source: B}]` without `columns`. | `uv run python -` on `dev` at `e2833142`, using fixed B `[system_id, public_id, extra_col, Beschreibung]` and fixed A `[system_id, public_id, Beschreibung]` | B's `extra_col` was `from B`; A's base and appended rows were both `from A`. The assertion expecting `["from A", "from B"]` failed. | Verified for the equivalent fixed-source configuration; not a run of the SQL project |
| E9 | Run of the actual project and its local Access source. | [`data/projects/dummy-append/shapeshifter.yml`](../../../data/projects/dummy-append/shapeshifter.yml), local `data/shared/data-sources/arbodat-lookup-options.yml`, local `data/shared/shared-data/ArchBotStrukDat.mdb`; reproduction command above | Five A base rows had A's value; B had `extra_col_from_entity_b`; A's appended row had `Extra value from entity a`. The expected-value assertion failed. | Verified for this local project and database |
| E10 | Source-append selection fix and regression tests in the local worktree. | [`src/model.py`](../../../src/model.py), [`src/extract.py`](../../../src/extract.py), [`tests/integration/test_append_integration.py`](../../../tests/integration/test_append_integration.py) | Seven new cases pass: present, null and missing source fields, explicit and empty append mappings, explicit column selection, and unchanged fixed append behavior. | Verified locally; not deployed |
| E11 | Rerun of the actual project with the local fix. | Same project and Access database as E9 | B and A's appended row both have `extra_col_from_entity_b`; five A base rows retain `Extra value from entity a`. | Verified locally; not deployed |

## Timeline or causal chain

1. On 2025-12-07, commit [`2c186d97`](https://github.com/humlab-sead/sead_shape_shifter/commit/2c186d97) added append support and defaulted an append item's `extra_columns` to an empty mapping when it was not specified.
2. Also on 2025-12-07, commit [`1147e38a`](https://github.com/humlab-sead/sead_shape_shifter/commit/1147e38a) changed append configuration to merge parent and append keys generically. The parent value is used unless the append item overrides it; `extra_columns` was not excluded. This is the earliest source-history change found that makes the parent's `extra_columns` apply to append branches.
3. Issue #767 was opened on 2026-11-20.
4. The behavior reproduces on `dev` at `851d01f4` and again at `e2833142` on 2026-11-26, including the case where the append item does not specify `columns`.
5. The supplied `dummy-append` project and local Access database also reproduce the bug at `e2833142`.
6. With the local fix applied at the same commit, the source-append regression cases and actual project pass.

This identifies when the behavior entered the source history, not when a particular deployed environment first received it; deployment history was not available.

## Root-cause assessment

**Confirmed mechanism:** `TableConfig.create_append_config()` inherits A's `extra_columns` into the append configuration for B. `SubsetService` either never requests `C` (when the append item's columns do not include it) or excludes it because it is an extra-column output, then evaluates the inherited constant. The overwrite happens during append-branch extraction, before concatenation.

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
| **Change source-append extraction (implemented locally):** when B already provides a column named `C` and A's `C: 5` was inherited, select B's `C` and do not generate a replacement for that append branch. Keep explicit append-level `extra_columns` mappings authoritative. | Produces A values `[5, 4]` while leaving A's base row at `5`. | Projects relying on an inherited expression to replace B's field must declare that expression explicitly on the append item. | Covered by the focused regression cases and actual-project run. |
| **Configuration workaround:** set `extra_columns: {}` on A's append item and include `C` in that item's `columns`. | Avoids a code change; this exact configuration was tested and produces A values `[5, 4]`. | Must be repeated for each affected append item. If B's output does not contain `C`, this does not supply a replacement value. | Example: `append: [{source: B, columns: [id, C], extra_columns: {}}]`. Verify that B's output contains `C`. |

### Implemented code fix (local worktree)

**Accepted rule (2026-11-26; implemented locally):** For a source-based append, a column already present in the processed source entity wins over a same-named `extra_columns` expression inherited from the destination, even when its value is null. When the source lacks the column, the inherited expression supplies it. An `extra_columns` mapping declared on the append item remains an intentional override, including when the source has that column; `{}` opts out of inheritance. This rule works when the append item has no `columns` list: in `dummy_append`, A inherits only `columns: [Beschreibung]`, while `extra_col` exists in B and in A's `extra_columns`.

1. [`TableConfig.get_sub_table_configs()`](../../../src/model.py#L1017) records which extra-column names on each source-based append item were inherited from its parent. [`create_append_config()`](../../../src/model.py#L870) still merges the mappings, while the generated append `TableConfig` carries the inherited names as typed, runtime-only information, not a new project YAML field. If the item declares `extra_columns`, including `{}`, it has **no inherited names** for this rule; its existing whole-mapping override behavior stays unchanged.
2. [`SubsetService.get_subset_columns()`](../../../src/extract.py#L24) uses the available source DataFrame column names to retain each inherited extra-column output that the source already has. It selects these names even if they are absent from the append item's (possibly inherited) `columns` list. Explicit append-level extra columns, unrelated source columns, and source identity fields are not added. Ordinary entities and fixed/SQL append items keep their existing selection rules.
3. [`get_subset2()`](../../../src/extract.py#L92) then selects the incoming column before evaluating extra columns. [`ExtraColumnEvaluator.evaluate_extra_columns()`](../../../src/transforms/extra_columns.py#L542) skips outputs already present, so the inherited expression does not replace B's value. With an absent source column, selection remains unchanged and the inherited expression creates the column on that append branch. Concatenation and A's post-concatenation evaluation require no new overwrite or per-row fill step: the base branch already has A's generated value and the evaluator skips a column that exists.

Implemented behavior covered by regression tests:

| Source B / append configuration | Expected appended `C` | Reason |
| --- | --- | --- |
| B has `C = 4`; append has no `columns` or `extra_columns` | `4` | Preserve an existing source field, including when `C` is not in A's `columns`. |
| B has `C = 4`; append explicitly lists `columns: [id, C]` | `4` | Explicit column selection must not lose the incoming field. |
| B has a `C` column containing null | null | A present source column wins; filling nulls is a separate rule, not an implicit overwrite. |
| B has no `C` column | `5` | Apply A's inherited expression to this branch when no source field exists. |
| Append explicitly declares `extra_columns: {C: 9}` | `9` | An explicit append-level expression takes precedence over B's field. |
| Append declares `extra_columns: {}` and selects `C` | B's `C` | Preserve the existing configuration workaround and opt-out behavior. |

This changes only implicit inheritance when it collides with an incoming field. A project that intentionally used A's inherited expression to replace B's `C` would need to declare that expression on the append item explicitly. No saved-YAML migration is required. Reverting the code change would restore the old behavior; the tested `extra_columns: {}` workaround remains available in the meantime.

**Validation:** The integration test uses the supplied example's shape (A has only its base field in `columns`, B also has the extra field, and the append item has only `source: B`) and covers explicit append `columns`, missing and null incoming columns, explicit append-level overrides, the empty-mapping workaround, and a fixed append. The existing append tests and actual project also pass. [`docs/CONFIGURATION_GUIDE.md`](../../../docs/CONFIGURATION_GUIDE.md#L2783) now documents the inheritance and precedence rules.

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

The empty append-level mapping overrides the inherited `C: 5`; the listed `C` is then read from B. A's own `extra_columns` remains unchanged, so A's base row still gets `C = 5`. If the append item instead explicitly declares `extra_columns: {C: 5}`, that intentional override produces `5`.

**Referenced Project**

This YAML excerpt matches the local [`dummy-append` project](../../../data/projects/dummy-append/shapeshifter.yml), which was run with its SQL source as described above. B's fixed-value row includes `system_id`, `entity_b_id`, `extra_col`, and `Beschreibung` in that order. A's append item has no explicit `columns`, so the proposed fix must retain B's `extra_col` without requiring a project change.

```yaml
metadata:
  name: dummy-append
  type: shapeshifter-project
  description: Project for dummy-append
  version: 1.0.0
  data_provider_code: arbodat-pilot
  provider_schema: archeobotany/arbodat-pilot
  default_entity:
entities:
  entity_a:
    type: sql
    keys: []
    columns: [Beschreibung]
    public_id: entity_a_id
    data_source: arbodat-lookup
    query: select [Beschreibung] from [FundUrsprung]
    append:
    - source: entity_b
    extra_columns:
      extra_col: Extra value from entity a
  entity_b:
    type: fixed
    keys: []
    columns: [extra_col, Beschreibung]
    public_id: entity_b_id
    values:
    - [1, null, extra_col_from_entity_b, beschreibung from entity_b]
options:
  data_sources:
    arbodat-lookup: '@include: ${GLOBAL_DATA_SOURCE_DIR}/arbodat-lookup-options.yml'
```

**Recommended next step:** Review and merge the locally verified fix. The issue establishes the expected result when B has `C = 4`; the missing, null, and explicit-override rules were agreed separately on 2026-11-26 and are covered by regression tests.

**Prevention / regression detection:** The new test asserts that the base A row keeps `C = 5` while the appended B row keeps `C = 4`, including the no-append-columns case from `dummy_append`.

## Remaining historical uncertainty (non-blocking)

- The first affected deployed version cannot be established from source history alone. This does not block the fix or its validation; it matters only for release-impact or backport decisions.

## Verification record

- `rtk uv run pytest -q tests/integration/test_issue_767_repro_tmp.py` — passed, 2 temporary diagnostic tests. The file was removed after the run.
- `rtk uv run pytest -q tests/integration/test_append_processing.py` — passed, with one skipped test.
- `uv run python -` — equivalent in-memory `dummy_append` configuration on `dev` at `e2833142`: B returned `["from B"]`, A returned `["from A", "from A"]`; the assertion expecting `["from A", "from B"]` failed.
- `GLOBAL_DATA_SOURCE_DIR=... GLOBAL_DATA_DIR=... uv run python -` — actual project and local Access database on `dev` at `e2833142`, using the full command above: B returned `["extra_col_from_entity_b"]`; A's appended row returned `["Extra value from entity a"]`; all five A base rows retained A's value. The assertion expecting B's value in the appended row failed.
- `rtk uv run pytest -q -n 0 tests/integration/test_append_integration.py -k 'source_append_extra_column_precedence or fixed_append_still_applies_inherited_extra_column'` — seven new cases passed after the fix; three failed as expected before it.
- `rtk uv run pytest -q -n 0 tests/integration/test_append_integration.py tests/integration/test_append_processing.py tests/model/test_append.py` — passed with one existing skip.
- `rtk uv run pytest -q -n 0 tests/model tests/integration tests/process` — passed with one existing skip after updating the subset-service test double for the new runtime-only field.
- `GLOBAL_DATA_SOURCE_DIR=... GLOBAL_DATA_DIR=... uv run python -` — actual project rerun after the fix: B and A's appended row both returned `["extra_col_from_entity_b"]`; all five A base rows retained A's value.
- `rtk uv run black --check src/model.py src/extract.py tests/integration/test_append_integration.py` — passed.
- `rtk uv run black --check src/model.py src/extract.py tests/integration/test_append_integration.py tests/process/test_subset_service2.py` — passed.
- `rtk uv run ruff check src/model.py src/extract.py tests/integration/test_append_integration.py tests/process/test_subset_service2.py` — passed.
- `rtk uv run pyright --threads 2 src/model.py src/extract.py` — 0 errors, 0 warnings.
- `rtk uv run pylint src/model.py src/extract.py tests/integration/test_append_integration.py tests/process/test_subset_service2.py` — passed, 10.00/10.
- No production database, project YAML, or deployment changes were made; the fix is in the local source worktree.

## References

- [Issue #767](https://github.com/humlab-sead/sead_shape_shifter/issues/767)
- [`src/model.py`](../../../src/model.py)
- [`src/extract.py`](../../../src/extract.py)
- [`src/transforms/extra_columns.py`](../../../src/transforms/extra_columns.py)
- [`docs/CONFIGURATION_GUIDE.md`](../../../docs/CONFIGURATION_GUIDE.md)
- [`data/projects/dummy-append/shapeshifter.yml`](../../../data/projects/dummy-append/shapeshifter.yml)
