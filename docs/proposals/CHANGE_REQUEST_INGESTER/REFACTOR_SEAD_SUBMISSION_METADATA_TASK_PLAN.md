# Task Plan: SEAD Change Request Submission Metadata

## Phase Summary

- Status: In progress
- Proposal: [REFACTOR_SEAD_SUBMISSION_METADATA.md](REFACTOR_SEAD_SUBMISSION_METADATA.md)
- Upstream schema baseline: [20260830_DDL_SUBMISSION_MODEL_REFACTOR.sql](20260830_DDL_SUBMISSION_MODEL_REFACTOR.sql)
- Goal: persist stable change-request defaults and emit one SEAD submission that groups every new dataset delivered by the run

**Acceptance Criteria**

- [x] Stable `datatype`, `deploy_strategy`, and `author` defaults round-trip under `options.ingesters.sead_change_request.defaults`.
- [x] The frontend applies persisted defaults and sends project `data_provider_code` without exposing it as a per-run field.
- [x] The bundled SEAD target models represent providers, submission states, submissions, and dataset submission links.
- [x] The bundled target models represent submission tasks, task types, task bibliography, and dated dataset contacts.
- [x] The ingester resolves an existing provider, emits one Pending submission, and links new datasets to it.
- [x] Both deploy strategies are covered by focused integration tests.
- [ ] The upstream PostgreSQL contract is validated against a disposable migrated database.
- [x] The proposal describes the implemented contract and remaining upstream work.

## Work Breakdown

### 1. Persist Project Metadata And Defaults

**Objective**

Store stable provider identity and change-request defaults in project YAML.

**Tasks**

- [x] Add optional `metadata.data_provider_code` to the backend project model.
- [x] Preserve `data_provider_code` through `ProjectMapper.to_api_config()` and `ProjectMapper.to_core_dict()`.
- [x] Preserve the typed defaults subsection without replacing the generic project `options` mapping.
- [x] Add mapper round-trip coverage for provider code and defaults.

**Completion Criteria**

Project load and save preserve provider code and the three accepted defaults without changing unrelated options.

### 2. Apply Defaults In The Frontend

**Objective**

Prefill stable values while retaining per-run operator control.

**Tasks**

- [x] Add frontend types for project provider code and `sead_change_request` defaults.
- [x] Apply defaults once when a project and ingester are opened.
- [x] Reapply defaults only after an explicit form reset or project change.
- [x] Include `data_provider_code` in submission context without adding an editable control.
- [x] Extend the focused component test for datatype, deploy strategy, author, and provider code.

**Completion Criteria**

Persisted defaults initialize the form, later operator edits are not overwritten, and requests carry stable provider identity.

### 3. Align Target Models

**Objective**

Represent the initial upstream submission schema in every bundled SEAD target model.

**Tasks**

- [x] Add optional `data_provider`, `submission_state`, and `submission` entities to minimal, standard, and superset models.
- [x] Add `dataset.submission_id` and its foreign key to `submission`.
- [x] Update maintained target-model test copies and structural assertions.
- [x] Retain `master_dataset` and `master_set_id` while the upstream SQL retains legacy tables.
- [x] Add optional `submission_task_type` and `submission_task` entities with nullable task `biblio_id` and `event_date`.
- [x] Add nullable `dataset_contact.event_date` and include it in dated contact identity.

**Completion Criteria**

All target-model specifications load and pass structural validation with the implemented SQL names, data types, and event-level identity fields.

### 4. Derive And Emit Submission Rows

**Objective**

Build submission rows from project and run metadata without requiring a source submission entity.

**Tasks**

- [x] Extend `SubmissionContext` with `data_provider_code`.
- [x] Resolve the provider by code through the existing reconciliation client.
- [x] Reject missing or unknown provider codes instead of allocating providers.
- [x] Prepend reference rows for Pending state and the resolved provider.
- [x] Build one submission with a generated native UUID and `upload_date` derived from the run timestamp.
- [x] Leave `submission_date` null and exclude `deploy_strategy` from stored metadata.
- [x] Attach the submission's local ID only to new dataset rows.
- [x] Reject source-owned `submission`, `submission_state`, or `data_provider` tables.
- [x] Skip parent resolution for nullable FK columns whose values are all null.
- [x] Verify copy-CSV output alongside inline INSERT output.

**Completion Criteria**

The package emits one Pending submission, does not emit provider or state inserts, and projects the allocated submission ID into every new dataset insert or copy-CSV payload.

### 5. Validate The Database Contract And Synchronize Documentation

**Objective**

Confirm generated artifacts execute against the initial upstream schema and close documentation gaps.

**Tasks**

- [x] Run focused mapper, frontend, target-model, derived-table, projection, and inline SQL tests.
- [x] Run the complete relevant backend and frontend regression checks and record unrelated failures.
- [ ] Apply the upstream DDL to a disposable PostgreSQL database.
- [ ] Execute inline INSERT and copy-CSV artifacts against that database.
- [ ] Verify one Pending submission, native UUID storage, provider linkage, null `submission_date`, and dataset links.
- [ ] Verify historical provider-level submission seeds, task bibliography, and task/contact event-date migration.
- [x] Update the proposal status, resolved decisions, and remaining upstream dependencies.
- [x] Confirm no maintained generated target-model artifact requires regeneration.

**Completion Criteria**

Focused and broader checks pass, generated artifacts execute against the upstream schema, and maintained documentation matches shipped behavior.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Project metadata and defaults | Done | Mapper tests pass. |
| Frontend defaults and request handoff | Done | Focused Vitest file passes. |
| Target-model alignment | Done | Structural spec tests cover task entities and dated contacts. |
| Derived submission output | Done | Inline INSERT, copy-CSV, and provider failure contracts pass. |
| Database contract and documentation | Blocked | Proposal is current; no disposable migrated PostgreSQL harness exists in the repository. |

## Definition Of Done

- [x] Project YAML preserves stable defaults and provider identity.
- [x] Frontend request construction uses those persisted values correctly.
- [x] All bundled SEAD target models match the initial upstream submission schema.
- [x] Conformance models match the revised task bibliography and event-date schema.
- [x] Missing or unknown providers stop validation before artifact generation.
- [x] Inline SQL emits one submission and links new datasets.
- [x] Copy-CSV output provides the same rows and relationships.
- [ ] Generated artifacts execute successfully against the upstream schema.
- [x] Relevant regression suites pass or unrelated existing failures are recorded.
- [x] No maintained generated target-model reference requires synchronization.

## Validation And Testing

- `rtk .venv/bin/pytest backend/tests/mappers/test_config_mapper.py backend/tests/test_metadata.py -q`
- `rtk .venv/bin/pytest tests/target_model/test_spec_files.py tests/model/test_target_model_conformance.py -q`
- `rtk .venv/bin/pytest backend/tests/ingesters/test_sead_change_request_*.py -q`
- From `frontend/`: `rtk pnpm exec vitest run src/components/ingester/__tests__/IngesterForm.test.ts`
- From `frontend/`: `rtk pnpm build`
- PostgreSQL contract harness: `TBD`

## Deliverables

| Deliverable | Description | Status |
|---|---|---|
| Project configuration contract | Provider code and stable ingester defaults | Done |
| Frontend defaults handoff | Persisted defaults plus provider context | Done |
| Target-model contract | Provider, state, submission, and dataset relationship | Done |
| Derived submission output | Provider resolution and generated submission row | Done |
| Contract validation record | Executable PostgreSQL validation against upstream DDL | Blocked |
| Updated proposal and reference docs | Final behavior and remaining dependencies | Done |

## Scope

**In scope**

- one provider and one submission per ingester run
- lookup-only provider resolution by `metadata.data_provider_code`
- Pending (`submission_state_id = 1`) for new submissions
- `timestamp` mapped to `upload_date` only
- one `datatype` stored in `data_types`
- inline INSERT and copy-CSV deploy strategies
- optional conformance entities for submission tasks and task types
- dated dataset-contact identity in the conformance models

**Out of scope**

- upstream migration or compatibility-view ownership
- ingester emission of submission task rows
- automatic provider creation
- multiple providers, submissions, or datatypes per run
- retroactive links for reference-only existing datasets
- rollback or submission visibility rules

## Risks And Mitigations

- **Contract drift:** the upstream SQL remains subject to review. Keep database execution as a required completion check and update target models when that contract changes.
- **Missing provider identity:** projects created before this change may lack `data_provider_code`. Return a direct validation error and require metadata correction.
- **Unexpected source ownership:** source workbooks may introduce names reserved for derived submission tables. Reject those tables rather than replacing data silently.
- **Legacy compatibility:** legacy master tables remain in the upstream schema. Keep their target-model definitions until upstream removal is agreed.
