# Investigation findings: Arbodat fixed-entity validation failure

**Brief:** User report for project `rebecka-arbodat-2`
**Status:** Partially conclusive
**Environment / baseline:** Repository `HEAD` `4a4028eee88d6be456c7602a6a409354f67a6220`; checked 2026-10-28. The reported development deployment version was not available.

## Executive summary

The attached YAML is byte-for-byte identical to the repository's Arbodat fixture. A local API-to-Core conversion reproduced the reported exception for the `data_provider` entity: its single row has five values, while its declared `columns` list has three. Those five values are in the valid full positional order (`system_id`, `data_provider_id`, then the three data columns), which structural validation accepts. The fixed-entity type coercer was updated to accept both row formats, and a mapper regression test now covers the Arbodat row.

The loader's warning collection catches and discards this shape exception, explaining why project-load warnings can be empty. The endpoint error handler logs only the exception class, explaining the unhelpful log line. This mechanism explains the two reported failures. The claimed successful conformance response was not reproduced; the current conformance service also converts the project to Core before running conformance, so a successful response for the same saved YAML and code version would need separate investigation. The dev deployment version is unknown, so its behavior after the local fix remains unverified.

## Verified observations and reproduction

- Parsed YAML from the attachment and `tests/test_data/projects/arbodat/shapeshifter.yml` is equal, and the files are byte-for-byte identical.
- `data_provider.columns` contains three data columns, but `values[0]` contains five values: `[1, 1, arbodat-pilot, Arbodat Pilot, null]`.
- Running `ProjectMapper.to_core()` on the repository fixture raises:

  ```text
  FixedEntityShapeValidationError: Entity 'data_provider' row 0 has 5 values; expected 3 based on declared columns
  ```

- `ProjectMapper.to_api_config()` returns an empty `load_warnings` list for that project. Its load-warning collector catches `FixedEntityShapeValidationError` and continues.
- Structural CLI validation of the repository fixture completes and reports one unrelated warning for `relative_ages.columns: [system_id]`; it reports no `data_provider` shape error.
- Structural CLI validation of the detached attachment could not complete because its `@include: reconciliation.yml` points to a file not present beside the attachment.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | Attachment compared with checked-in Arbodat fixture | Attachment and [`shapeshifter.yml`](../../tests/test_data/projects/arbodat/shapeshifter.yml) | Same bytes and parsed YAML; both declare 68 entities. | Verified |
| E2 | `data_provider` row width and order | [`shapeshifter.yml`](../../tests/test_data/projects/arbodat/shapeshifter.yml#L500) | Three data columns; row has five values, matching the generated full columns (`system_id`, `data_provider_id`, then data columns). | Verified |
| E3 | Structural fixed-entity validation accepts data-only or full identity rows | [`entity.py`](../../src/specifications/entity.py#L265) | Five values are accepted for the full five-column shape. CLI reported only the separate `relative_ages` warning. | Verified |
| E4 | Load-warning collection hides shape exceptions | [`project_mapper.py`](../../backend/app/mappers/project_mapper.py#L96) | The collector catches `FixedEntityShapeValidationError` and skips it, yielding no load warning. | Verified |
| E5 | API-to-Core coercion rejected this full row | [`entity_config_mapper.py`](../../backend/app/mappers/entity_config_mapper.py#L176), [`fixed_entity_types.py`](../../src/types/fixed_entity_types.py#L484) | Reproduced before the fix; the coercer now selects positional column names from the row width. | Verified |
| E6 | Data validation and task status fail before producing results | [`validation_service.py`](../../backend/app/services/validation_service.py#L87), [`task_service.py`](../../backend/app/services/task_service.py#L86) | Both flows call `ProjectMapper.to_core()` before validation completes; task status maps the project before calling data validation. | Verified |
| E7 | Error log omits the exception message and traceback | [`error_handlers.py`](../../backend/app/utils/error_handlers.py#L107) | The catch logs only the endpoint and exception class. | Verified |
| E8 | Conformance also converts to Core | [`validation_service.py`](../../backend/app/services/validation_service.py#L349) | A successful conformance result on the same file and current code was not reproduced. | Unverified |
| E9 | Mapper regression test covers the identity-inclusive Arbodat row | [`test_entity_config_mapper.py`](../../backend/tests/mappers/test_entity_config_mapper.py#L229) | The new test passes after the coercer change. | Verified |

## Root-cause assessment

**Confirmed mechanism:** The fixed-entity shape contract is inconsistent across two code paths. Structural validation accepts either data-only rows or rows with managed identity values. The API-to-Core fixed-entity mapper calls `FixedEntityTypeCoercer`, which requires every inline row to have exactly `len(columns)` values and does not account for the full identity-inclusive width. The valid five-value `data_provider` row therefore raises before data validation can start.

The log line is not enough to identify this on its own: `handle_endpoint_errors` catches the exception and records only `FixedEntityShapeValidationError`, without `str(e)` or an exception traceback. A local mapper reproduction supplies the missing message and entity.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| The attachment differs from the checked-in Arbodat YAML. | None. | Byte comparison and parsed comparison both match. | Ruled out |
| A fixed-entity full row is rejected during API-to-Core conversion. | Exact local reproduction points to `data_provider` row 0, five values versus three declared columns. | Structural validation accepts the full width. | Verified |
| The data-provider row is invalid under the project structural contract. | None. | `FixedEntityFieldsSpecification` allows full identity-inclusive rows; structural CLI reports no such error. | Ruled out |
| The reported successful conformance run used the same saved YAML and backend code. | None. | Current conformance service calls `ProjectMapper.to_core()` before conformance, which reproduces the failure. | Unverified |

## Impact and extent

**Confirmed affected case:** Data validation and task-status flows for the supplied Arbodat configuration fail during project conversion, before returning a normal validation result.

**Potential wider impact:** Other projects with fixed rows that use the accepted identity-inclusive format may hit the same mismatch. The affected project configurations have not been exhaustively searched.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Align fixed-value coercion with the structural contract by coercing rows using their effective positional columns, including managed identity columns when present. | Preserves the valid full-row format and resolves the underlying inconsistency. | Needs care to preserve type declarations and both accepted row formats. | Add tests for data-only and full identity-inclusive rows; validate data, task status, and conformance routes. |
| As a dev-only diagnostic workaround, add `system_id` and `data_provider_id` to `data_provider.columns` so the five declared columns match the existing five-value row. | Exercises the same row without discarding the configured SEAD ID. | May be normalized on project save; do not apply to a shared or production project without checking round-trip behavior. | Test on a copy, then confirm save/reload and all three validation flows. |

**Recommended next step:** Verify the fixed build against the actual development project and compare the deployed version. If conformance still returns successfully for that same file, confirm which route/workflow and project directory it used.

**Prevention / regression detection:** Test that the fixed-entity mapper accepts the same data-only and full identity-inclusive row widths that `FixedEntityFieldsSpecification` accepts. Also assert that unexpected endpoint exceptions include useful internal log details without returning sensitive traceback data to clients.

## Unresolved questions and blockers

- Which backend commit/version was running in the reported dev test?
- Did the conformance check use the API endpoint, a different CLI/workflow, or another project directory?
- Does the actual dev project directory contain sidecars or includes that differ from the checked-in fixture?

## Verification record

- Compared the attached YAML and repository fixture with `yaml.safe_load`; parsed objects matched.
- Compared source bytes; they matched.
- Ran `ProjectMapper.to_api_config()` followed by `ProjectMapper.to_core()` on `tests/test_data/projects/arbodat/shapeshifter.yml`; reproduced the exact `data_provider` exception and an empty `load_warnings` list.
- Added the mapper regression test and updated the coercer to accept identity-inclusive positional rows.
- Ran `uv run python scripts/validate_project.py tests/test_data/projects/arbodat/shapeshifter.yml --workflow structural --log-level ERROR`; validation completed with one `relative_ages` warning and no `data_provider` error.
- Ran `uv run pytest backend/tests/mappers/test_entity_config_mapper.py backend/tests/validators/test_data_validation_orchestrator.py tests/types/test_fixed_entity_types.py -q`; **77 passed**.
- Tried structural CLI validation on the detached attachment; it stopped because the referenced `reconciliation.yml` was not present beside the attachment.
- No project configuration was changed.

## References

- [`fixed_entity_types.py`](../../src/types/fixed_entity_types.py#L484)
- [`entity.py`](../../src/specifications/entity.py#L265)
- [`entity_config_mapper.py`](../../backend/app/mappers/entity_config_mapper.py#L176)
- [`project_mapper.py`](../../backend/app/mappers/project_mapper.py#L96)
- [`validation_service.py`](../../backend/app/services/validation_service.py#L130)
- [`task_service.py`](../../backend/app/services/task_service.py#L86)
- [`error_handlers.py`](../../backend/app/utils/error_handlers.py#L107)
