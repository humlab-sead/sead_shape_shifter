# Investigation findings: #539

**Brief:** [Issue #539](https://github.com/humlab-sead/sead_shape_shifter/issues/539)  
**Status:** Conclusive  
**Environment / baseline:** Repository `HEAD` `22a1c2c` (`v2.5.0`), checked 2026-10-27.

## Executive summary

Issue #539 is **not fixed** at the checked revision and remains relevant as a cleanup task. The values-update service still accepts the exact legacy fixed-column order, remaps rows by column name, and has unit and integration tests that require this behavior.

The bundled frontend derives fixed-value order from `fixed_schema.full_columns` and submits those columns. The declarative-business-keys phase plan also records retirement as deferred to #539. Removing request-side legacy acceptance does not require rewriting stored files. Keep the separate read-side stored-column normalization, which allows existing files with a compatible column permutation to be read.

## Verified observations and reproduction

- The GitHub issue is still open, has no comments, and has no pull request linked as its closure.
- `_normalize_fixed_request_columns` accepts either `full_columns` or `legacy_columns`; the legacy list is built through `build_legacy_fixed_full_columns` and `build_fixed_entity_legacy_columns`. The request update path then uses the normalized order.
- The frontend selects `fixed_schema.full_columns` when available and uses its fixed grid columns for values-update requests.
- The phase plan explicitly defers retirement to #539 and describes the code and test changes still needed.
- Both existing tests that exercise legacy-order acceptance passed:
  - `TestEntityValuesService.test_update_values_remaps_recognized_legacy_order`
  - `test_materialized_values_accepts_exact_legacy_order_and_keeps_authoritative_file_order`

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | Issue remains open and has no closure PR reference. | GitHub issue #539, checked 2026-10-27 | No resolution is recorded in GitHub. | Verified |
| E2 | Request normalization accepts the authoritative or exact legacy order. | [`entity_values_service.py`](../../../backend/app/services/entity_values_service.py#L276), [`fixed_schema.py`](../../../backend/app/utils/fixed_schema.py#L30), [`fixed_entity_types.py`](../../../src/types/fixed_entity_types.py#L58) | The compatibility implementation is still present. | Verified |
| E3 | Service and API integration tests expect legacy-order requests to succeed and be remapped. | [`test_entity_values_service.py`](../../../backend/tests/services/test_entity_values_service.py#L350), [`test_declarative_business_keys_integration.py`](../../../backend/tests/api/v1/test_declarative_business_keys_integration.py#L162) | Both tests passed on the checked revision. | Verified |
| E4 | The frontend uses the backend's full fixed schema and submits its fixed grid columns. | [`EntityFormDialog.vue`](../../../frontend/src/components/entities/EntityFormDialog.vue#L3333), [`EntityFormDialog.vue`](../../../frontend/src/components/entities/EntityFormDialog.vue#L3061), [`entityFormMaterialization.ts`](../../../frontend/src/components/entities/entityFormMaterialization.ts#L176) | The bundled frontend follows the authoritative request order. | Verified |
| E5 | Read-side normalization still reorders compatible stored permutations without writing them. | [`entity_values_service.py`](../../../backend/app/services/entity_values_service.py#L337), [`test_entity_values_service.py`](../../../backend/tests/services/test_entity_values_service.py#L428) | This is separate from request compatibility and should remain. | Verified |
| E6 | Retirement is explicitly deferred to #539 in the phase plan. | [`DECLARATIVE_BUSINESS_KEYS_PHASE_PLAN.md`](../../../docs/proposals/done/DECLARATIVE_BUSINESS_KEYS/DECLARATIVE_BUSINESS_KEYS_PHASE_PLAN.md#L195) | The plan identifies this as cleanup, not a delivery dependency. | Verified |

## Root-cause assessment

**Confirmed mechanism:** The compatibility feature remains because the backend still recognizes a legacy positional column list. Current tests affirm that behavior. This is an intentionally retained compatibility path, not evidence that the new frontend still needs it.

The repository's plan and proposal state that the bundled frontend is the only client sending fixed-values requests and that it already sends the authoritative order. That supports the removal rationale. This investigation did not independently inventory external API consumers, so any clients outside this repository remain unverified.

## Impact and extent

**Confirmed affected cases:** A fixed-values request using the exact historical identity/keys/data order is accepted and remapped before saving.

**Potential wider impact:** Removing request-side acceptance would reject such legacy API requests. The bundled frontend uses the authoritative order. External consumers, if any, would need to switch to `fixed_schema.full_columns` before that input is removed.

Read-side normalization is a separate behavior: stored files with the same set of columns in another order are still returned in the authoritative order. Do not remove that logic as part of #539.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Complete #539 as described: reject legacy request order, remove the now-unused helpers, and replace acceptance tests with rejection tests. | Removes dead request compatibility code and makes the API contract match the authoritative order. | Legacy external callers, if present, would need to change their requests. | Confirm external consumers if the API is used outside the bundled application; run service and API integration tests. Keep stored-value read normalization. |
| Keep the compatibility path. | Avoids breaking any unknown legacy callers. | Continues accepting an obsolete input shape and leaves the follow-up unresolved. | Reassess if external clients are identified and require the old order. |

**Recommended next step:** Keep #539 open and implement its stated cleanup. Before removal, verify whether any external client depends on legacy order. Update the phase plan as requested by the issue; preserve `_normalize_fixed_stored_values`.

**Prevention / regression detection:** Assert that legacy-order PUT requests fail with an error naming the authoritative order, while a compatible stored column permutation remains readable and is not rewritten.

## Unresolved questions and blockers

- Are there external clients beyond the bundled frontend that send fixed-values updates? Repository documentation says there are none, but this was not independently verified.

## Verification record

- `./.venv/bin/python -m pytest -q backend/tests/services/test_entity_values_service.py backend/tests/api/v1/test_declarative_business_keys_integration.py -k 'remaps_recognized_legacy_order or materialized_values_accepts_exact_legacy_order'` — **2 passed**.
- Read-only inspection of the current service, helper functions, frontend request construction, tests, phase plan, and GitHub issue state.
- No application code or issue state was changed.
