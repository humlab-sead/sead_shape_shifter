# Sead Change Request Submission Metadata

## Status

- Implementation in progress
- Scope: `sead_change_request` submission metadata — persisted defaults plus SEAD submission storage
- Upstream baseline: [Initial submission-model DDL](20260830_DDL_SUBMISSION_MODEL_REFACTOR.sql)
- Task plan: [REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md](REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md)
- Goal: persist stable submission metadata and map each change request into the initial upstream SEAD submission model

## Summary

The `sead_change_request` ingester previously collected submission metadata for every run, but that metadata was transient and had no durable home. Two gaps followed.

First, stable values such as datatype, deploy strategy, and author must be re-entered or re-derived on each run, so reruns can drift. Second, the current SEAD database has no submission container that the ingester can populate: `tbl_dataset_submissions` records tasks or events associated with individual datasets, and the target model has no `submission` entity.

This CR closes both gaps. It persists stable submission defaults in project YAML under an ingester-specific subsection and adopts `tbl_submissions` from the revised upstream DDL as the submission container. Each submission references `tbl_data_providers`; each new dataset references the submission through `tbl_datasets.submission_id`. The implementation derives one submission row from project metadata and per-run context rather than requiring operators to author a new source entity.

The revised upstream DDL includes dedicated `submission_identifier`, `issue_identifier`, and `author` columns. These values describe the submission as a whole and are not encoded in `notes` or kept only in change-package metadata.

The revised upstream migration cannot reconstruct true logical submissions from legacy data. It therefore seeds one manually reviewable historical submission per data provider. Legacy `date_submitted` values remain attached to the migrated event rows as `tbl_submission_tasks.event_date` or `tbl_dataset_contacts.event_date`, and task rows retain the originating dataset bibliography through `tbl_submission_tasks.biblio_id`.

## Problem

The ingester's submission metadata currently exists only as per-run operator input in the frontend form. That input is used for bundle naming and headers, then discarded. Nothing persists it.

This causes two concrete problems.

1. Reruns drift. Fields such as `datatype`, `deploy_strategy`, and `author` are stable project facts, but they are entered again on every run or inferred from a hard-coded default. A project that always submits `datatype: bird` or `deploy_strategy: copy_csv` must re-enter that context each time, and inconsistent entries are easy.

2. The current deployed SEAD database has no submission container for the change request. Before this implementation, Shape Shifter did not represent the `tbl_submissions` and `tbl_submission_tasks` tables proposed to replace the overloaded `tbl_dataset_submissions` table. A change package therefore could not emit a submission row that references a data provider and groups the delivered datasets.

## Scope

This proposal covers:

- persisting stable `sead_change_request` submission defaults in project YAML
- mapping ingester submission metadata to the proposed `tbl_submissions` columns
- resolving the data provider through the proposed `tbl_data_providers` table
- linking each delivered dataset through `tbl_datasets.submission_id`
- representing the submission-related parts of the accepted redesign in the target model
- representing submission tasks, task types, and dated dataset contacts in the conformance models
- the frontend, backend model, target-model, and ingester changes needed to support both parts

## Non-Goals

- redefining ingester identity or SQL logic
- implementing rollback, change detection, or other next-delivery candidates
- implementing the database migration from `tbl_dataset_masters`, `tbl_dataset_submissions`, and `tbl_dataset_submission_types`
- migrating legacy task types 10 and 11 to `tbl_dataset_contacts`
- generating or maintaining legacy compatibility views
- designing detailed frontend screens
- defining submission visibility rules based on submission state

## Current Behavior

- Project YAML preserves `metadata.data_provider_code` and `options.ingesters.sead_change_request.defaults` for `datatype`, `deploy_strategy`, and `author`.
- The frontend applies persisted defaults once when the project and ingester are opened. Operators can still override them for a run.
- The ingester resolves an existing provider by `data_provider_code`, creates one Pending submission row, and links each new dataset to that submission.
- Provider and submission-state rows are references only. The change package does not insert or allocate them.
- Both inline INSERT and copy-CSV output include submission and linked dataset rows. They do not emit submission tasks.
- The bundled minimal, standard, and superset target models include providers, submissions, submission states, submission tasks, and submission task types, and retain legacy master-dataset entities for compatibility.
- The target models represent `tbl_submission_tasks.biblio_id`, both new nullable `event_date` columns, and dated dataset-contact identity.

The initial upstream database redesign introduces:

- `tbl_submissions`, containing submission state, dates, notes, provider, name, source, data types, and UUID
- `tbl_data_providers`, replacing `tbl_dataset_masters`
- `tbl_submission_tasks`, replacing the task-like rows in `tbl_dataset_submissions` and preserving their event dates and dataset bibliography references
- `tbl_submission_states` and `tbl_submission_task_types`
- `tbl_datasets.submission_id`, linking each dataset to its submission
- `tbl_dataset_contacts.event_date`, preserving dates for legacy task types 10 and 11

Deployment of this upstream DDL and legacy compatibility remain outside this repository.

Legacy submission types 10 (`Samples collected`) and 11 (`Samples analysed`) do not become submission tasks. The redesign migrates them to `tbl_dataset_contacts` with contact types 4 and 2 respectively.

Historical `date_submitted` values vary within what can only be approximated as one logical submission. The migration therefore does not derive submission-level dates from those values. It creates one historical submission per provider with fields exposed for manual correction, links each legacy dataset and task through its provider, and keeps each date on the event row where it originated. No submission-date column is added to `tbl_datasets`; dated dataset-contact activity remains available through `tbl_dataset_contacts`.

## Proposed Design

### 1. Persist stable submission defaults in project YAML

Add an ingester-specific defaults subsection to the project YAML under the existing per-ingester configuration:

```yaml
options:
  ingesters:
    sead_change_request:
      defaults:
        datatype: bird
        deploy_strategy: copy_csv
        author: "SEAD Lab"
```

- Backend: extend the project model so `options.ingesters.sead_change_request.defaults` round-trips through the mapper without being treated as flat generic metadata.
- Frontend: read the persisted defaults on form open in `applyIngesterDefaults()`, prefill the corresponding fields, and keep the existing per-run override behavior and "project-derived" indicators.
- Stable defaults are limited to `datatype`, `deploy_strategy`, and `author`. `timestamp`, `identifier`, and `issue_identifier` remain per-run values.

### 2. Adopt the proposed SEAD submission container

Use the database redesign as the storage contract:

1. Emit one `tbl_submissions` row for the project run.
2. Resolve `data_provider_id` against `tbl_data_providers`.
3. Set every delivered dataset's `submission_id` to that submission.
4. Set `submission_state_id` to 1 (`Pending`), as defined by the revised upstream DDL.

This is a target-schema contract change, mirrored in the target model and the ingester:

- target model: add the required `data_provider`, `submission_state`, and `submission` entities, and add the submission foreign key to `dataset`
- ingester: project `submission_context` into the submission row and emit the row before the datasets that reference it
- upstream database: create and initialize the redesigned tables before applying a change package that uses them

`tbl_submission_tasks` and `tbl_submission_task_types` belong to the wider database redesign. They are represented as optional conformance-model entities, but this change does not emit task rows.

The revised task schema contains nullable `biblio_id` and `event_date` columns. The bibliography is copied from the originating `tbl_datasets` row because the legacy task table has no bibliography column and provider-level historical submissions span many dataset bibliographies.

### 3. Map project and run metadata to `tbl_submissions`

Use project-metadata correspondence rather than a mandatory source `submission` entity. Derive one submission row from project metadata, persisted defaults, and per-run values.

The initial mapping is:

| Ingester or project value | SEAD column                             | Implemented mapping                          |
| ------------------------- | --------------------------------------- | -------------------------------------------- |
| `submission_name`         | `tbl_submissions.submission_name`       | Direct                                       |
| `datatype`                | `tbl_submissions.data_types`            | One value per run                            |
| `timestamp`               | `tbl_submissions.upload_date`           | Date component; `submission_date` stays null |
| `description`             | `tbl_submissions.notes`                 | Direct                                       |
| `project_name`            | `tbl_submissions.source_name`           | Direct                                       |
| `identifier`              | `tbl_submissions.submission_identifier` | Direct                                       |
| `issue_identifier`        | `tbl_submissions.issue_identifier`      | Direct                                       |
| `author`                  | `tbl_submissions.author`                | Direct                                       |
| generated submission UUID | `tbl_submissions.submission_uuid`       | Native UUID                                  |
| resolved provider         | `tbl_submissions.data_provider_id`      | Existing target ID                           |
| initial state             | `tbl_submissions.submission_state_id`   | 1 (`Pending`)                                |

`deploy_strategy` controls change-package delivery and is not submission metadata stored in `tbl_submissions`.

The revised upstream DDL defines these columns as nullable text fields:

```sql
alter table tbl_submissions
add column submission_identifier text,
add column issue_identifier text,
add column author text;
```

`submission_identifier` is the ingester's stable, human-readable identifier used in bundle naming. It is distinct from the generated `submission_uuid`. `issue_identifier` remains text because the current ingester contract accepts a string and the value identifies an external change-control issue. `author` remains free text because the current ingester captures a display name, not a resolved `tbl_contacts` reference.

### 4. Resolve the data provider and dataset ownership

The redesign replaces the contact-type interpretation of a provider with a dedicated `tbl_data_providers` row. Project metadata must supply `metadata.data_provider_code`. The ingester resolves that code through the reconciliation client before planning allocations. Missing and unknown codes are validation errors; the ingester never allocates a provider.

The emitted submission row uses the resolved `data_provider_id`. Each dataset emitted in the same change package uses the submission's local `submission_id` through the new `tbl_datasets.submission_id` foreign key. This models one provider per submission and one submission per dataset, as proposed by the redesign.

## Alternatives Considered

- Keep metadata transient and only add defaults. This closes the drift gap but leaves submission identity and ownership unrepresented in the stored result, so the second gap remains open.
- Require a new source `submission` entity. This is more explicit and supports multiple submissions per project, but adds mandatory boilerplate for the expected one-submission-per-run workflow.
- Store submission metadata only in the project YAML without a SEAD table. Loses the database-side container and provider reference, so the submission is not visible to SEAD consumers.
- Continue representing providers as typed contacts. This conflicts with the proposed `tbl_data_providers` replacement for `tbl_dataset_masters`.

## Risks And Tradeoffs

- The SEAD schema is owned upstream. The five new tables, the `tbl_datasets.submission_id` foreign key, data migration, and any legacy views must be deployed before generated artifacts can run.
- Project-metadata correspondence is simple, but it assumes one submission per project run. Multiple submissions per project or multiple providers per submission are not served by the recommended option.
- The redesign changes the meaning of legacy submission data. Most `tbl_dataset_submissions` rows become `tbl_submission_tasks`; types 10 and 11 become dataset contacts. Existing consumers may require compatibility views.
- Historical rows are grouped into one seed submission per provider because existing data cannot identify true logical submissions. Those seed values require manual review before upstream deployment.
- Task bibliography is inherited from the originating dataset. This preserves the available reference but does not assert that the bibliography describes the task independently of that dataset.
- The initial DDL is the implementation baseline, but it may still change upstream. Shape Shifter target models must be updated if table names, column types, or initial state identifiers change.
- The new metadata columns are specific to the current change-request workflow. Their names and meanings must remain useful to other submission sources rather than encoding GitHub-specific behavior in the database schema.
- `author` is free text and does not enforce a relationship with `tbl_contacts`. Converting it to a contact foreign key would require a separate identity-resolution rule.
- `data_types` is text in the initial schema. This implementation emits one datatype per run; multiple-value serialization remains out of scope.
- Provider resolution can fail if the project does not carry a stable `data_provider_uuid` or `data_provider_code` recognized by SEAD.
- A narrow defaults set is safer, but it may leave some wanted defaults unsupported until metadata improves.

## Testing And Validation

- Backend mapper, target-model, derived-row, target-projection, provider-resolution, and artifact tests cover the implemented contract.
- The focused frontend component test covers persisted defaults, provider handoff, and per-run request construction.
- Inline INSERT and copy-CSV integration tests verify submission and dataset output and confirm that provider, state, and task rows are not emitted.
- Target-model tests verify the optional task entities, nullable task bibliography and event date, and dated dataset-contact identity.
- Database execution remains required against a disposable PostgreSQL database containing the revised upstream DDL.

## Acceptance Criteria

- Stable `sead_change_request` submission defaults persist in project YAML under an ingester-specific subsection and round-trip through the mapper.
- The frontend honors persisted defaults on form open, and per-run overrides are preserved.
- Every ingester metadata field is mapped to a named column or explicitly documented as change-package-only metadata.
- The change package emits one `tbl_submissions` row with a resolved `data_provider_id`, generated UUID, and agreed initial state.
- Every delivered dataset references that submission through `tbl_datasets.submission_id`.
- The ingester does not depend on legacy `tbl_dataset_submissions` or treat task types 10 and 11 as submission tasks.
- Maintained target models represent submission tasks and dated dataset contacts without requiring the ingester to emit task rows.
- The historical migration seeds one editable submission per provider and preserves legacy event dates on task or dataset-contact rows.
- The target model, ingester, and docs stay consistent with the accepted mapping option.

## Recommended Delivery Order

1. Complete the focused and broader repository checks.
2. Apply the revised upstream DDL to a disposable SEAD PostgreSQL database.
3. Execute inline INSERT and copy-CSV artifacts against that database.
4. Resolve any contract differences found by database execution.
5. Deploy the accepted upstream migration and document operational compatibility requirements.

## Open Questions

- Which upstream release will deploy the migration?
- Which upstream component owns legacy compatibility views and their removal schedule?

## Final Recommendation

Proceed with the implemented project-metadata option and narrow defaults field set (`datatype`, `deploy_strategy`, `author`). Use `metadata.data_provider_code` for lookup-only provider resolution. Emit one Pending submission per run and link each new dataset to it.

Keep database migration and legacy compatibility work in the upstream handoff. Before deployment, execute both artifact strategies against a disposable database containing the revised upstream DDL and resolve any differences found there.
