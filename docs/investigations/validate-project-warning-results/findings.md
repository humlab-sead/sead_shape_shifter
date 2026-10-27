# Investigation findings: CLI validation omits normalizer findings

**Brief:** User report; no separate investigation brief was supplied  
**Status:** Conclusive; structured normalizer findings are now surfaced by the CLI. The intended treatment of log-only warnings remains open.  
**Environment / baseline:** `dev` at merge commit `4b67c87831ba6f7b581aab76deb5777be5533f39`, including `ac5694c9` (`fix(validation): surface normalizer findings`); Linux; `tests/test_data/projects/arbodat/shapeshifter.yml`

## Executive summary

The reported behavior reproduced after the merge. The CLI logged normalizer warnings but printed only issues returned by its validation workflows. In the data workflow, `DataValidationExecutor` normalized the project and passed only `normalizer.table_store` to `TableStoreDataFetchStrategy`. That strategy did not expose the normalizer's structured findings, so the orchestrator could not return them as validation results.

The merge added collection of structured linker findings to backend preview and full-data validation paths, but did not change `scripts/validate_project.py`, which used a separate path. The approved fix now shares normalization-issue collection with the CLI's table-store strategy. A fresh run prints seven `ROW_COUNT_MISMATCH` rows corresponding to the seven logged join row-count changes. Empty output from `citation`, `dating`, and `site_natural_region` continues to produce `EMPTY_RESULT` rows. The JVM startup notice and SQL loader's “NOT IMPLEMENTED VALIDATION” warning remain log-only; this change does not convert arbitrary Loguru messages into validation issues.

## Verified observations and reproduction

Before the fix, ran the reported arguments with the repository interpreter:

```text
.venv/bin/python scripts/validate_project.py --workflow all --log-level warning tests/test_data/projects/arbodat/shapeshifter.yml
```

The command exited successfully and reproduced the reported distinction: warning logs included multiple linker row-count changes, while the CSV result contained no `ROW_COUNT_MISMATCH` rows. The CSV did contain `EMPTY_RESULT` warnings for `citation`, `dating`, and `site_natural_region`, along with the other structural, data, and conformance results shown in the report.

The shell did not have a `python` executable on `PATH`; using `.venv/bin/python` ran the same script and arguments in the repository's configured environment.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | Re-ran the reported validation command before implementing the fix | `.venv/bin/python scripts/validate_project.py --workflow all --log-level warning tests/test_data/projects/arbodat/shapeshifter.yml` | Linker warnings were logged; the CSV did not include `ROW_COUNT_MISMATCH`. Three empty-entity results were present. | Verified |
| E2 | CLI data workflow normalizes directly, then constructs a table-store strategy | [`scripts/validate_project.py`](../../../scripts/validate_project.py#L109-L119) | The strategy receives `normalizer.table_store`, not the normalizer or its issues. The printer outputs only each workflow's `result.issues` ([lines 200–214](../../../scripts/validate_project.py#L200)). | Verified |
| E3 | Orchestrator requests strategy-specific issues, but the base implementation returns an empty list; before the fix, the table-store strategy did not override it | [`data_validation_orchestrator.py`](../../../backend/app/validators/data_validation_orchestrator.py#L57-L59), [table-store strategy](../../../backend/app/validators/data_validation_orchestrator.py#L176-L193), [issue collection](../../../backend/app/validators/data_validation_orchestrator.py#L387-L391) | The original CLI strategy provided no normalization findings. It now returns them when given the normalizer. | Verified |
| E4 | Full-data and table-store validation share a helper that collects unresolved extra-column and linker issues | [`data_validation_orchestrator.py`](../../../backend/app/validators/data_validation_orchestrator.py#L96-L108), [full-data strategy](../../../backend/app/validators/data_validation_orchestrator.py#L167-L174) | The CLI now uses the same structured issue conversion as backend full-data validation. | Verified |
| E5 | A row-count change is both logged and appended as a structured linker issue | [`constraints.py`](../../../src/specifications/constraints.py#L433-L449) | The issue exists before output formatting; the CLI omission is downstream of its creation. | Verified |
| E6 | Empty DataFrames independently produce `EMPTY_RESULT` warnings | [`data_validators.py`](../../../src/validators/data_validators.py#L237-L261), invoked by [`data_validation_orchestrator.py`](../../../backend/app/validators/data_validation_orchestrator.py#L378) | This explains why some empty-result log warnings also appear in the CSV without any general log capture. | Verified |
| E7 | The merged commit changed backend services, mappers, orchestrator, tests, and frontend validation types; it did not include `scripts/validate_project.py` | Merge `4b67c878`; fix commit `ac5694c9` | The fix added structured finding collection to other validation paths, not this CLI path. | Verified |
| E8 | Focused CLI and orchestrator tests | `.venv/bin/pytest -q tests/test_validate_project_script.py backend/tests/validators/test_data_validation_orchestrator.py` | 23 tests passed. Existing tests verify backend full-data linker findings, but this run did not test that the CLI emits those findings. | Verified |

## Timeline or causal chain

1. Commit `ac5694c9` added structured normalizer-finding collection to backend preview and full-data validation.
2. Merge commit `4b67c878` brought that change into `dev`.
3. The CLI's data executor continued to run `ShapeShifter` itself and pass only its `table_store` into `TableStoreDataFetchStrategy`.
4. The orchestrator asked the strategy for additional issues. The table-store strategy inherited the base method, which returned no issues. It then ran ordinary data validators, including the empty-result check.
5. After the reported gap was reproduced and diagnosed, the user approved a structured-findings-only fix. The table-store strategy now accepts the normalizer and returns its structured issues through a shared helper also used by full-data validation.
6. The CLI was rerun. Its CSV included all seven row-count mismatch issues; log-only operational and unsupported-check warnings remained logs.

The evidence establishes the current path and its cause. It does not establish that the omission began with the merge; no pre-merge reproduction was performed, and the CLI file was not part of the fix commit.

## Root-cause assessment

**Confirmed mechanism:** Before the fix, the CLI did not pass structured findings from the `ShapeShifter` instance into the validation orchestrator. Although the linker stored a `row_count_mismatch` issue alongside logging its warning, the CLI's `TableStoreDataFetchStrategy` held only the table store. The backend `FullDataFetchStrategy` already read linker findings and unresolved extra columns, but the CLI did not use that path.

**Implemented fix:** A shared helper now converts the normalizer's linker and unresolved-extra-column findings into domain validation issues. `TableStoreDataFetchStrategy` accepts an optional normalizer and returns those findings when supplied; the CLI passes its existing normalizer. Existing callers that pass only a table store retain the prior behavior.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| The CLI captures Loguru warning records and converts them to results | Warning text appears beside the CSV output. | The printer iterates `WorkflowResult.issues`; the empty-result match is produced by a data validator, not logger interception. | Ruled out |
| The merged fix covered every workflow that runs normalization | Commit subject refers to normalizer findings. | The CLI executor still uses the table-store strategy; the changed commit files do not include the CLI script. | Ruled out |
| Every logged warning should be a validation result | Some warnings describe data problems. | The output includes operational/performance and unimplemented-check messages that do not currently have structured issue definitions. | Unverified requirement; do not capture all warning logs indiscriminately |

## Impact and extent

**Confirmed affected cases:** Before the fix, the CLI logged seven join row-count changes but returned no `ROW_COUNT_MISMATCH` results. After the fix, the same run returned seven matching rows. Empty entities continue to appear as `EMPTY_RESULT` rows.

**Potential wider impact:** Other structured issues collected from the normalizer, including unresolved extra columns, can be missing from this CLI workflow for the same reason. The investigation did not determine whether every other warning in the supplied logs is intended to become a validation result. SQL loader capability notices, JVM startup/performance notices, missing requested input columns, and delayed transforms need explicit classification before promotion.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Pass structured findings from the CLI's existing normalizer to its data-validation strategy | Reuses the normalization already performed; can surface linker issues and unresolved extra columns without parsing log text. | Requires keeping the strategy's issue ownership and entity association clear, and avoiding duplicates when dependencies are checked. | Implemented; a CLI regression test checks that a linker warning becomes one CSV result. |
| Route CLI validation through the backend full-data strategy | Reuses backend issue collection. | May reload and normalize the project through service dependencies, changing CLI behavior or doing duplicate work. | Confirm CLI service setup and parity before adopting. |
| Convert selected log-only warnings to structured issues | Makes chosen diagnostics visible in result output. | Warning strings are not a stable issue contract; some messages describe performance or unsupported checks rather than invalid data. | Decide categories and severity first, then emit typed issues at the source and test each one. |

**Recommended next step:** The structured-finding fix is implemented. Do not treat all Loguru warning records as validation results. Decide separately whether specific log-only categories should become structured `info`, `warning`, or unsupported-check results.

**Prevention / regression detection:** The new `DataValidationExecutor` test supplies a recorded linker issue and asserts the resulting CSV contains exactly one matching validation row. The focused suite also retains existing empty-result checks.

## Unresolved questions and blockers

- Should selected log-only warnings also become results in addition to the structured findings now exposed?
- If log-only warnings are in scope, which categories are intended validation outcomes? The SQL unnesting limitation, skipped input columns, delayed duplicate-row transform, and JVM initialization notice have different meanings and should not share a severity by default.
- The investigation is conclusive about the current CLI data path, but it does not establish when the behavior first appeared or whether an earlier CLI contract promised log-to-result conversion.

## Verification record

- **Before fix:** `.venv/bin/python scripts/validate_project.py --workflow all --log-level warning tests/test_data/projects/arbodat/shapeshifter.yml` — exit code 0; reproduced the missing row-count results.
- **After fix:** The same command exited 0 and printed seven `ROW_COUNT_MISMATCH` rows, alongside the existing three `EMPTY_RESULT` rows. Log-only notices remained outside the CSV.
- **Attempted exact interpreter name:** `python ...` — unavailable on this shell's `PATH`; no project command ran from that attempt.
- **Focused tests:** `.venv/bin/pytest -q tests/test_validate_project_script.py backend/tests/validators/test_data_validation_orchestrator.py` — 24 passed.
- **Formatting:** Black and isort checks passed for the three changed Python files.
- **Lint:** Ruff passed for the changed backend and test files, and for the CLI with its existing `E402` import-order warning excluded. Pylint passed with its existing `R1711` warning excluded; unfiltered checks still report those unrelated existing warnings.
- **Graph:** `GRAPHIFY_VIZ_NODE_LIMIT=0 ~/.local/bin/graphify update .` completed.
- **Source changes:** Updated the orchestrator strategy, CLI wiring, regression test, and this report. Other pre-existing worktree changes were left untouched.

## References

- Merge commit `4b67c87831ba6f7b581aab76deb5777be5533f39`
- Fix commit `ac5694c993d73fef2ed364e0539400771ba6b29b`
- [`scripts/validate_project.py`](../../../scripts/validate_project.py)
- [`backend/app/validators/data_validation_orchestrator.py`](../../../backend/app/validators/data_validation_orchestrator.py)
- [`backend/app/services/shapeshift_service.py`](../../../backend/app/services/shapeshift_service.py)
- [`tests/test_validate_project_script.py`](../../../tests/test_validate_project_script.py)
- [`src/specifications/constraints.py`](../../../src/specifications/constraints.py)
- [`src/validators/data_validators.py`](../../../src/validators/data_validators.py)
