# Target Model Review: 2026-10-13

**Model under review:** [sead_superset_model.yml](sead_superset_model.yml)  
**Status:** In progress; review entities one at a time.

Whether SEAD needs both standard and superset target models remains undecided. This review examines the current superset model; it does not establish that both variants should continue to exist. The test specifications in `tests/test_data/specs` are symlinks to the resource files, so they use the shared models rather than independent copies.

## 1. `location`

### Question

Can the model support both direct-ID linking and reconciliation-based linking, including both within one project? Direct-ID rows supply an existing SEAD `location_id`; reconciliation rows use location name and type to identify a candidate and either associate an approved `location_id` or remain unmatched.

### Current specification

- `location` is a required `lookup` entity targeting `tbl_locations`.
- `location_type_id` is non-nullable and is included with `location_name` in the `unique_sets` declaration.
- `location` has a required FK to `location_type`.
- `location_type` is itself marked `required: true`.
- `location` omits an explicit `reconciliation` value. Its `lookup` role defaults to `reconcile-exact`.

### Review notes

- These are alternative paths for individual location references, not mutually exclusive project-wide modes:
	1. A fixed or materialized `location` entity can supply an existing SEAD `location_id`. In this path, `location_type_id` need not be supplied because the referenced SEAD row already has its type.
	2. Reconciliation can use `location_name` and `location_type_id` to find a candidate. A user can approve the resulting `location_id`, or no location may be found.
- The current target-model conformance rules require every project to include `location` and `location_type`, require the declared `location` entity to expose `location_name` and `location_type_id`, and require its FK relationship to `location_type`. A fixed or materialized `location` entity containing only `location_id` therefore does not conform as written.
- The Change Request Ingester's required/non-null column checks also apply to `location_name` and `location_type_id`. If direct-ID and reconciliation rows share one entity and direct-ID rows leave these values empty, the current column rules may reject those rows as well.
- Entity-level `required: true` means every conforming project must include that entity. FK-level `required: true` means every conforming project must declare the relationship. These are project conformance requirements, not statements that a SEAD row must be newly inserted.
- For the Change Request Ingester MVP, `foreign_keys` affect FK projection and required-FK checks. Required links must have their columns and values in output rows.
- `unique_sets` records target-side column groups declared unique, but it has no direct effect on Change Request Ingester reconciliation. Therefore, this metadata alone does not make reconciliation depend on `location_type_id`.
- For reconciliation-based rows, `(location_type_id, location_name)` can disambiguate locations that share a name. For direct-ID rows, the ID already identifies the target row.

### Next steps

- [ ] **Decision needed:** Define when projects must declare lookup entities and relationships: when referencing known IDs, reconciling records, or creating records.
- [ ] **Decision needed:** Define how one project can support both paths for an entity, including whether it needs conditional requirements or separate project entities.
- [ ] Update conformance requirements for `location` and related classifier/fact-to-lookup relationships to match those decisions. Preserve target-database FK constraints.

### References

- [Target Model Guide](../../docs/TARGET_MODEL_GUIDE.md)
- [Target Model Specification Format: Identity Columns](../../docs/proposals/done/TARGET_MODEL_SPECIFICATION_FORMAT.md)

## 2. `site` and `site_location`

### Observation

For a project that uses only existing, known SEAD `site_id` values, it does not need to include `site_location` just to restate each site's existing location relationship.

### Current specification

- `site` is marked `required: true` and declares a required relationship to `location` via `site_location`.
- `site_location` is separately marked `required: true` and has required FKs to both `site` and `location`.
- The bridge identity is `(site_id, location_id)`.

### Review notes

- The current conformance rules require every project to include `site_location` for the required bridge-mediated relationship, and require the bridge to declare its FK to `location`.
- This makes the project describe the full target-model relationship graph even when it only references existing sites whose site-location links already exist in SEAD.
- As with `location_type`, the target database may require site-location relationships for site records, but that does not mean every project must supply bridge rows when it is not creating or reconciling sites.

### Next steps

- [ ] **Decision needed:** Decide whether a project must declare `site_location` when it only references existing sites by `site_id`.
- [ ] Apply the policy from section 1 to the `site` and `site_location` requirements. Preserve the target database's relationship constraints.

## 3. `sample_group`

### Observation

The target model now records uniqueness groups only in `unique_sets`. For `sample_group`, the group is `[site_id, sample_group_name]`, and `sample_group_name` is declared `required: true`.

### Current specification

- `sample_group.unique_sets` includes `[site_id, sample_group_name]`.
- `site_id` is declared `required: true`.
- `sample_group_name` is declared `required: true` and remains `nullable: true`.
- `sampling_context_id` is currently not declared `required: true` and is marked `nullable: true`, while the database column is non-nullable.
- The FK from `sample_group` to `sample_group_sampling_context` is currently marked `required: false`.

The former `identity_columns` field and its field-specific required check have been removed. Membership in `unique_sets` does not set a column's `required` flag. Review `nullable` separately; it describes whether the target column may contain null.

### Next steps

- [ ] Set `sampling_context_id` to `required: true` and `nullable: false` to match the database column.
- [ ] **Decision needed:** Decide whether projects that provide an existing `sampling_context_id` must declare the `sample_group_sampling_context` entity and FK, using the policy from sections 1-2.
- [ ] Set the FK and entity requiredness to match that decision.

## 4. `sample_group_reference`

### Observation

This entity represents the association between a sample group and a citation. The current superset declares it as a `bridge`.

### Current specification

- The current role is `bridge`.
- The entity targets `tbl_sample_group_references` and declares `[sample_group_id, biblio_id]` in `unique_sets`.
- It has required FKs to `sample_group` and `citation`, and no other payload columns.
- `aggregate_parent` is `sample_group`.

### Next steps

- [x] Confirmed: `bridge` is the agreed role for this association-table entity.
- [x] Set `sample_group_reference.role` to `bridge`.
- [x] Confirmed: keep `aggregate_parent: sample_group`; it determines child identity behavior independently of the role.

## 5. `sample`

### Post-MVP consideration

A data provider may resubmit a previously submitted sample with new or updated analysis values. The post-MVP release needs to define how the system recognizes that sample across submissions and applies those analysis-value changes.

### Current specification

- `sample` is a required `fact` with `[sample_group_id, sample_name]` in `unique_sets`.
- No explicit `identity_tracking` or `reconciliation` policy is declared. Under current defaults, a `fact` is tracked and allocated an identity.

### Next steps

- ~~[ ]~~ Deferred: ~~Determine whether a provider UUID or another provider-scoped identifier stays stable across sample resubmissions.~~
- [x] Rejected: `(sample_group_id, sample_name)` is not sufficient to recognize a resubmitted sample.
- ~~[ ]~~ Deferred: ~~Define whether resubmissions add, update, or replace analysis values, or require review when values differ.~~
- ~~[ ]~~ Deferred: ~~Define how to retain submission provenance and record changes without creating duplicate samples or losing prior values.~~
- ~~[ ]~~ Deferred: ~~After those decisions, define the sample identity and tracking policy. Keep the current policy until then.~~

## 6. `value_type_item`

### Observation

`value_type` is the aggregate parent of `value_type_item`. A value type can define a categorical specification, such as `color`, whose items are `red`, `green`, and other allowed values. A value item is meaningful within its parent value type rather than as a standalone classifier.

### Current specification

- `value_type_item` has role `classifier` and now declares `aggregate_parent: value_type`.
- It has a required FK to `value_type` and declares `[value_type_id, name]` in `unique_sets`.

The aggregate-parent relationship is now represented in the model.

### Next steps

- [ ] **Decision needed:** Agree whether an existing role can represent a categorical item scoped to a value-type definition.
- [ ] After role semantics are agreed, select the role for `value_type_item`; add a role only if the existing roles do not express this relationship.

## 7. `sample_horizon`

### Observation

`sample_horizon` records a horizon assignment for a sample. It relates the `sample` fact to the `horizon` classifier and belongs to the sample aggregate.

### Current specification

- `sample_horizon` has `role: fact` and `aggregate_parent: sample`.
- It declares `[physical_sample_id, horizon_id]` in `unique_sets` and has required FKs to `sample` and `horizon`.
- The effective identity resolver infers `identity_tracking: child` from `aggregate_parent`; the `fact` role does not override that child identity.

### Review conclusion

Keep `role: fact` for `sample_horizon`: it represents sample-level metadata, while `aggregate_parent: sample` expresses that its identity is inherited from the sample. This differs from `site_location`, whose purpose is to bridge the `site` and `location` lookup entities. Classify these entities by what their records represent, not only by the presence of multiple foreign keys.

## 8. `method` and `method_group`

### Observation

`method.method_group_id` is a required, non-nullable column, while the FK declaration to `method_group` has `required: false`. This can look contradictory, but the two settings describe different project requirements.

### Current specification

- `method` is a required `classifier` entity with `reconciliation: lookup-extensible`.
- `method_group_id` is marked `required: true` and `nullable: false`.
- The FK from `method` to `method_group` is marked `required: false`; `method_group` itself is also marked `required: false`.

### Review notes

- A required column means each project `method` must provide `method_group_id`.
- An optional FK means a project is not required to declare `method_group` as a related entity. It may still provide a known group ID directly.
- This is consistent if projects may reference established method groups by ID without supplying or reconciling the group entity. If projects must always model the relationship through `method_group`, the FK should be required.
- A destination-table default could be another reason a project need not provide the value, but the target-model `ColumnSpec` has no `default` field. The current `required: true` declaration still says the project must provide the column; confirm whether `tbl_methods.method_group_id` has a database default and whether this specification should support expressing defaults.

### Next steps

- [ ] **Decision needed:** Decide whether a project may provide a known `method_group_id` without declaring the `method_group` entity.
- [ ] **Decision needed:** Confirm whether the target table supplies a default for `method_group_id`.
- [ ] Based on those decisions, align the column, FK, and entity `required` settings with the intended project workflow.
- [ ] If a database default should satisfy a missing value, decide how to represent that behavior in the target-model format.

## 9. `dataset`

### Observation

A dataset groups analytical records. It can be viewed as a `fact` describing an analytical collection, and it may be the aggregate parent of the analyses it contains.

### Current specification

- `dataset` has `role: lookup`, with explicit `identity_tracking: tracked` and `reconciliation: allocate`.
- `analysis_entity` is a tracked `bridge` between `sample` and `dataset`, with required FKs to both.
- `analysis_value` declares `aggregate_parent: analysis_entity`.

### Review notes

- The required lookup entities are `master_dataset`, `data_provider`, `citation`, and `contact`. Entity requiredness does not make every FK to those lookups required.
- Changing `dataset.role` from `lookup` to `fact` alone would not change its identity behavior because `identity_tracking` and `reconciliation` are explicitly set.
- A dataset must require foreign-key relationships to `master_dataset`, `project`, `submission`, and `data_type`, and require the corresponding `master_set_id`, `project_id`, `submission_id`, and `data_type_id` fields.
- The current spec marks the `master_dataset`, `project`, and `submission` FKs optional and omits the `data_type` FK entirely. `master_set_id`, `project_id`, and `submission_id` also lack `required: true`; `data_type_id` is already required and non-nullable.
- Keep project requiredness distinct from destination nullability. Confirm the destination nullability of `master_set_id` and `project_id` separately; their current `nullable: true` values do not satisfy the requirement that projects provide those fields.
- `analysis_entity` should not use SIMS tracked identity. Its current explicit `identity_tracking: tracked` and `reconciliation: allocate` settings conflict with this decision.
- Without an `aggregate_parent`, a `bridge` defaults to `identity_tracking: derived` and `reconciliation: derive`. Declaring `aggregate_parent: dataset` instead would make `analysis_entity` a child of the dataset, with no reconciliation strategy.
- `analysis_entity` links both `sample` and `dataset`, so choosing derived identity or dataset-child identity must account for both relationships.
- Since `analysis_value` is already a child of `analysis_entity`, making `analysis_entity` a child of `dataset` would place analysis values under the dataset indirectly.

### Review decision

`analysis_entity` must not be a SIMS tracked entity.

### Next steps

- [ ] **Decision needed:** Choose whether `analysis_entity` uses derived identity from its sample-dataset relationship or child identity from `dataset`.
- [ ] If it is a dataset child, define how its separate sample relationship affects uniqueness and resubmission handling.
- [ ] **Decision needed:** Decide whether `dataset` should use the `fact` or `lookup` role.

## 10. `data_provider` YAML style

### Observation

The `data_provider.columns` entries now use block mappings, consistent with most column specs in this target model.

### Next steps

- [x] Rewrite these column specs as block mappings for consistency and easier scanning. This is a readability change and does not alter the model's meaning.

## 11. Aggregate-child relationships in the supplied model

This section records aggregate-parent relationships declared in the reviewed model. It does not establish whether the deployed target tables have sequence or identity defaults. The deployment-time ID-resolution design and its validation requirements are covered by the [Deployment-Time Staging proposal](../../docs/proposals/CHANGE_REQUEST_INGESTER/DEPLOYMENT_TIME_STAGING/DEPLOYMENT_TIME_STAGING.md).

| Entity | Declared aggregate parent | Model entities that reference its ID |
| --- | --- | --- |
| `sample_dimension` | `sample` | None identified in this model |
| `analysis_value` | `analysis_entity` | `analysis_note`, typed analysis-value entities, and other analysis-value children |
| `abundance` | `analysis_entity` | `abundance_property`, `abundance_modification`, and `abundance_ident_level` |
| `geochronology` | `analysis_entity` | None identified in this model |

The supplied model does not include the legacy `dendro` or `measured_value` entities. Review their aggregate-parent relationships in a model that includes them before deciding how their IDs should be handled.

## 12. Provider-supplied UUIDs as an identity signal

### Observation

Some entities carry UUID columns. This model declares `data_provider_uuid` and `submission_uuid` with `type: uuid`, and both are represented in `unique_sets`. A provider-supplied UUID may help recognize a resubmission or update, but target-side uniqueness metadata does not itself define provider matching behavior.

This is a general rule for any entity that can receive a data-provider UUID, not a special case for `sample`.

### Current specification

- `data_provider.data_provider_uuid` is `required: true`, `type: uuid`, `nullable: false`. Its unique sets include `[data_provider_code]` and `[data_provider_uuid]`.
- `submission.submission_uuid` is `required: true`, `type: uuid`, `nullable: false`, and appears in `unique_sets`.
- `sample` has no UUID column. Its unique set is `[sample_group_id, sample_name]`, and it declares no explicit `identity_tracking` or `reconciliation` value.
- Four other columns are named as UUIDs but declare `type: string`: `synonym_uuid` (required), `rdb_system_uuid` (required), `ecocode_system_uuid`, and `taxonomic_order_system_uuid`.

### Review notes

- SIMS records a provider-supplied UUID as a Source Identity value for the entity's Source Scope. It does not adopt the provider UUID as the SIMS tracked UUID; SIMS mints its own tracked UUID. See FR-6 and FR-7 in the SIMS requirements and the UUID intake rule in the SIMS design.
- SIMS keeps provider keys independently of whether the consuming system stores them (FR-9), and it distinguishes provider keys from business keys and authority keys (FR-5). A provider UUID is a provider key. Target-side `unique_sets` do not describe a provider's source business key.
- The `accept_uuid` field in the SIMS `config/identity_policy.yml` is described in the SIMS design as legacy behavior and is not part of the target identity contract. Do not use it to decide whether a provider UUID can be recorded.
- A provider UUID is not a SEAD `public_id`. The `public_id` names the target column and holds the SEAD ID; the provider UUID identifies the provider's own record. Keep the two separate.
- A provider UUID can be a source identity when the provider guarantees that it remains stable across resubmissions. The project's Business Key and SIMS source identity policy describe that use; a target unique set does not.

### Next steps

- [ ] **Decision needed:** Identify which entities receive provider UUIDs and whether each value stays stable across resubmissions.
- [ ] **Decision needed:** Define which key governs when a provider UUID and natural key disagree.
- [ ] Define how stable provider UUIDs are represented in the project's Business Key and SIMS source identity policy. Keep provider matching separate from target `unique_sets`.
- [ ] **Decision needed:** Confirm whether the four UUID-named columns typed as `string` hold UUIDs or provider text identifiers; align their types with that decision.
- [ ] Resolve sample resubmission behavior as part of the post-MVP work in section 5. Keep `sample.unique_sets` and its tracking policy unchanged until that behavior is agreed.

### References

- [Target Model Guide](../../docs/TARGET_MODEL_GUIDE.md)
- SIMS requirements FR-5 to FR-11, and the Identity Intake Rules in the SIMS design (`sead_authority_service/docs/SIMS/DESIGN.md`).

The target-model review is still in progress. Confirm the aggregate ownership and parent assignments, including bridge entities, before treating this list as the final set of eligible aggregate children. This model inventory alone does not confirm target-database ID-generation behavior.
