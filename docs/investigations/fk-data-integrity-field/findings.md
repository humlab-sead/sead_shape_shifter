# Investigation findings: generic field for foreign-key integrity warnings

**Brief:** User report; no separate investigation brief was supplied  
**Status:** Conclusive for the reported CLI output; desired `field` semantics remain a product/API decision  
**Environment / baseline:** `dev` at `f071013dff23ec690007484f1969e82717545f59`; Linux; local worktree configuration `tests/test_data/projects/arbodat/shapeshifter.yml`

## Executive summary

The reported `foreign_keys[].entity` value is assigned literally by `ForeignKeyIntegrityValidator` when it creates an `FK_DATA_INTEGRITY` issue. It is not a failed substitution or a failure to resolve the remote entity. The validator reads the configured remote entity name, uses it in the warning message, and separately sets `field` to the generic configuration path `foreign_keys[].entity`. The CLI prints `issue.field` unchanged.

For the reported row, `ecocode` is the local entity, `ecocode_definition` is the configured remote entity, and `ecocode_definition_id` is the local FK column. The remote name is present in the message: `...not found in 'ecocode_definition'...`. The code and a test for the related `FK_REMOTE_EMPTY` issue use the same generic field path, which supports the interpretation that `field` identifies the configuration property rather than its value. No explicit documentation found in this investigation defines that contract.

The generic field assignment predates the recent CLI normalizer-findings change. Its current line traces to commit `6ce8e1eb` from 2026-02-09, so this is not caused by that change.

## Verified observations and reproduction

Ran the reported workflow with the repository interpreter:

```text
.venv/bin/python scripts/validate_project.py --workflow all --log-level warning tests/test_data/projects/arbodat/shapeshifter.yml
```

The command exited with status 0 and reproduced:

```text
data;warning;ecocode;foreign_keys[].entity;None;FK_DATA_INTEGRITY;1 foreign key value(s) not found in 'ecocode_definition' (20.0)
```

The current Arbodat configuration declares `ecocode` with a foreign key whose `entity` is `ecocode_definition`, whose local key is `ecocode_definition_id`, and whose remote key is `system_id`.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | Reproduced the reported CLI output | `.venv/bin/python scripts/validate_project.py --workflow all --log-level warning tests/test_data/projects/arbodat/shapeshifter.yml` | The output row contains the generic field and the configured remote name in the message. | Verified |
| E2 | Validator reads the remote entity from `fk_config` | [`data_validators.py`](../../../src/validators/data_validators.py#L401-L404) | `remote_entity` is set from `fk_config["entity"]` and used in the issue message. | Verified |
| E3 | `FK_DATA_INTEGRITY` assigns a fixed field string | [`data_validators.py`](../../../src/validators/data_validators.py#L503-L509) | The issue sets `field="foreign_keys[].entity"` regardless of the configured target; the message interpolates `remote_entity`. | Verified |
| E4 | CLI prints the issue's field directly | [`validate_project.py`](../../../scripts/validate_project.py#L204-L214) | No formatting step substitutes the target entity into the `field` column. | Verified |
| E5 | Arbodat config distinguishes local entity, remote entity, and local FK column | [`shapeshifter.yml`](../../../tests/test_data/projects/arbodat/shapeshifter.yml#L1752-L1760) | `ecocode` references `ecocode_definition`; `ecocode_definition_id` is its local key. | Verified in the current worktree |
| E6 | Related remote-empty warning uses the same field path; the orphan warning test does not assert a field value | [`test_data_validators.py`](../../../tests/validators/test_data_validators.py#L360-L400) | The generic path is also asserted for `FK_REMOTE_EMPTY`; no test currently specifies the intended field for `FK_DATA_INTEGRITY`. | Verified |
| E7 | Field assignment history | Commit `6ce8e1ebbd960c14d8c1322c109dcc42449afc9a` (`feat(validators): refactor and bug fix data validators (#224)`) | The literal field assignment traces to this 2026-02-09 commit, not the recent CLI fix. | Verified |
| E8 | Data-validator unit tests | `.venv/bin/pytest -q tests/validators/test_data_validators.py` | 40 tests passed. | Verified |

## Timeline or causal chain

1. The Arbodat `ecocode` FK configuration sets the remote entity to `ecocode_definition`.
2. `ForeignKeyIntegrityValidator.validate()` reads that value into `remote_entity`.
3. If it finds orphaned local values, it builds an `FK_DATA_INTEGRITY` issue with the fixed field path `foreign_keys[].entity` and a message containing the actual remote name.
4. `scripts/validate_project.py` serializes the issue's `field` member into the CSV `field` column without modification.

The field assignment dates to `6ce8e1eb` in February 2026. The exact point at which a consumer began treating `field` as a place to display the remote target was not established.

## Root-cause assessment

**Confirmed mechanism:** The validator deliberately assigns the generic string `foreign_keys[].entity` to the issue's `field` property. The remote target is stored in the warning message, not substituted into `field`. The CLI preserves both values in their respective columns.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| The remote entity name failed to resolve | The field is generic. | The warning message contains `ecocode_definition`, sourced from `fk_config["entity"]`; the Arbodat config declares that exact name. | Ruled out |
| The CLI replaces the remote entity name with a placeholder | The placeholder appears in CSV output. | The validator has already assigned the literal value; the CLI prints `issue.field` unchanged. | Ruled out |
| `field` represents the YAML configuration path | The static value names a path within the `foreign_keys` array, related issues use similar paths, and a related test asserts it. | No explicit field-path contract was found. | Supported hypothesis |

## Impact and extent

**Confirmed affected cases:** Every orphaned-FK warning produced by this validator receives the same generic `field` value, irrespective of its remote entity. The current CLI reproduction demonstrates this for `ecocode` → `ecocode_definition`.

**Potential wider impact:** `FK_REMOTE_EMPTY` also reports the generic `foreign_keys[].entity` path when the remote entity has no rows. Other FK validations use generic paths such as `foreign_keys[].local_keys` and `foreign_keys[].remote_keys`. This may affect consumers that expect `field` to identify a specific FK target rather than a configuration property.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Keep `field` as the generic configuration path | Preserves a consistent pointer to the YAML property and existing output shape. | The remote target remains visible only in the message, which consumers may need to parse. | Document the meaning of `field`; no behavior change. |
| Put the remote name into `field`, for example `foreign_keys[entity=ecocode_definition].entity` | Makes each warning easier to distinguish in the CSV. | Changes the meaning and format of `field`; array indexing or duplicate FKs to the same target need a defined representation. Consumers may depend on the current value. | Define a stable path format and add validator, CLI, API, and UX tests. |
| Keep the field path and expose the remote entity as structured data | Preserves the configuration location while giving consumers a machine-readable target. | Requires a contract change to issue metadata/API output and, if desired, the CLI CSV columns. | Decide the output shape and update API/CLI consumers and tests together. |

**Recommended next step:** Decide whether `field` means a configuration path or a target identifier. If the goal is to expose the remote target, prefer a separate structured `remote_entity` value and retain `foreign_keys[].entity` as the field path, rather than overloading the `field` property.

**Prevention / regression detection:** Add an assertion for the intended `field` value and remote-entity metadata to `test_reports_orphaned_fk_values`, plus a CLI output assertion for the chosen CSV contract.

## Unresolved questions and blockers

- Should the CSV `field` column identify the YAML property, or should it identify the configured target entity?
- If a contextual path is preferred, how should it identify repeated FK entries or multiple FKs to the same target?
- The current project YAML is marked modified in the worktree. This investigation reproduced against that local file and did not edit it; a clean-branch comparison was not performed.

## Verification record

- **Reproduction:** `.venv/bin/python scripts/validate_project.py --workflow all --log-level warning tests/test_data/projects/arbodat/shapeshifter.yml` — exit status 0; reproduced the exact field and message.
- **Unit tests:** `.venv/bin/pytest -q tests/validators/test_data_validators.py` — 40 passed.
- **History:** `git blame -L 500,512 -- src/validators/data_validators.py` — the fixed field assignment traces to `6ce8e1eb` on 2026-02-09.
- **Source changes:** None. The modified project YAML and other pre-existing worktree changes were left untouched.

## References

- [`src/validators/data_validators.py`](../../../src/validators/data_validators.py)
- [`scripts/validate_project.py`](../../../scripts/validate_project.py)
- [`tests/validators/test_data_validators.py`](../../../tests/validators/test_data_validators.py)
- [`tests/test_data/projects/arbodat/shapeshifter.yml`](../../../tests/test_data/projects/arbodat/shapeshifter.yml)
- Commit `6ce8e1ebbd960c14d8c1322c109dcc42449afc9a` (`feat(validators): refactor and bug fix data validators (#224)`)
