# Handoff: PostgreSQL Contract Validation

## Purpose

Validate the submission-model schema, each historical `fn_migrate_submission_datasets` call, and generated submission artifacts against a disposable copy of the baseline database. This is the pre-deployment PostgreSQL gate for the [submission metadata task plan](../REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md); it does not define the SEAD release schedule.

**Status:** Historical calls validated; current artifact generation blocked on the SIMS identity contract

## Current State

- The submission-model DDL has been applied to a test database. That shared database is not the disposable validation target.
- The current DML script defines `fn_migrate_submission_datasets` and six calls to it inside `migrate_legacy_submission_date()`, but does not invoke the wrapper. The six calls can be tested individually without deciding when they run in the release cycle.
- The current DML verify script checks the date parser, but does not assert the individual migration calls or generated submission artifacts.
- The DDL adds `data_provider_code`, but the legacy provider copy does not populate it. The artifact test needs a provider code set on the disposable database.
- The six historical submission groups are confirmed as intended: MAL/provider 2, BugsCEP/provider 1, ceramics/provider 3, Dendrochronology pilot/provider 10, aDNA/provider 12, and Lund Living Trees/provider 10.
- A compressed baseline dump is available at [tmp/sead_staging_baseline.sql.gz](../../../../tmp/sead_staging_baseline.sql.gz). It was created from `sead_staging` in plain SQL format with `--create` and `--clean`; gzip integrity passes. The dump contains definitions of the migration functions but not the new submission tables or `tbl_datasets.submission_id`. Confirm the restored table and column state before using it as the pre-DDL baseline.
- Setup gate 1 completed on 2026-09-30: the dump was restored into `ss_contract_20260930_101335` in the network-isolated container `ss-pg-ss-contract-20260930-101335`. The restored database has 6 dataset masters, 143452 legacy dataset submissions, and 59052 datasets. The new submission tables and `tbl_datasets.submission_id` are absent. The initial attempt with `postgres:16-alpine` stopped at the missing PostGIS extension; that disposable container was removed before restoring with `postgis/postgis:16-3.4`. No migration calls were run.
- Setup gate 2 prepared `ss_contract_prepared_20260930_101335` from the restored baseline. The DDL and current DML function definitions load, six provider identities match the legacy masters, and there are no submissions, submission tasks, or linked datasets. Individual, combined, and artifact assertion scripts are available; no helper call or generated package has run. The verified baseline groups contain 2967, 13433, 11076, 27032, 10, and 4534 datasets (59052 total).
- Setup gate 3 uses the in-memory `test-project` submission input in the two ingester tests below. Both strategies generated packages with the same new dataset and a reference-only existing dataset. Their rows were checked against the prepared database's required columns and IDs before executing the packages on separate clones.
- On 2026-09-30, the six calls passed separately on `ss_contract_group_{1..6}_run_20260930`, and all six passed together on `ss_contract_group_0_run_20260930`. Before and after assertions checked dataset assignments, task rows (including bibliography and event dates), contact rows, submission metadata, and migrated submission/task sequences. The combined run linked all 59052 datasets and created 103091 tasks and 40356 new contacts. The DML date-parser verify passed.
- Provider code `SEAD` was assigned to provider 1 only on the disposable combined-run clone. The inline INSERT and copy-CSV packages each applied to their own `ss_contract_artifact_{inline,copy}_run_20260930` clone. Submission metadata, dataset-link, and strategy-parity checks passed; reference dataset 1 retained its historical submission link to submission 1. The full artifact after-check now rejects both packages on sequence safety.
- **Post-package sequence check failed:** both packages explicitly insert submission ID 7 and dataset ID 91924 without advancing their sequences. On each artifact clone, the submission sequence is `6` with `is_called = true`; the dataset sequence is `91924` with `is_called = false`. The next default-generated submission or dataset ID would collide. The strengthened assertion fails on each original clone and passes on `ss_contract_artifact_sequence_control_20260930` after advancing its sequences manually. That control proves the check works, not that the packages are fixed. Keep the original disposable databases for investigation.
- A temporary generated-ID implementation passed the full artifact after-check on `ss_contract_artifact_serial_{inline,copy}_20260930`, including sequence safety and dependent child references. That implementation was rolled back because it bypassed SIMS for submission and dataset rows and hard-coded entity names. These clones record a past experiment, not a passing result for current artifacts. The original fixed-ID clones still fail the sequence check.

## Key References

- [Task plan](../REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md)
- [Submission-model DDL](../../../../../sead_change_control/sead_model/deploy/20260830_DDL_SUBMISSION_MODEL_REFACTOR.sql)
- [Submission-model DML](../../../../../sead_change_control/sead_model/deploy/20260830_DML_SUBMISSION_MODEL_MIGRATE.sql)
- [DML verification script](../../../../../sead_change_control/sead_model/verify/20260830_DML_SUBMISSION_MODEL_MIGRATE.sql)

## Next Actions

**Setup gate (complete before running the validation calls)**

1. Completed: inspect and run the isolated baseline restore procedure below. Keep the source and shared servers out of the container workflow.
2. Completed: cloned the disposable migration template for each group and the combined run, then passed the [historical-call assertions](../../../../tests/integration/submission_model_contract.sql) before and after each execution. The [artifact assertions](../../../../tests/integration/submission_artifact_contract.sql) fail on current fixed-ID packages at the sequence check.
3. Blocked: define how SIMS tracking and target integer IDs interact before repeating artifact validation. The prior generated-ID packages used a rolled-back implementation.

Current fixed-ID packages fail the sequence check. Do not deploy them as a solution to this contract gap.

**Execution results (2026-09-30)**

| Group | Datasets | Tasks | New contacts | Before/after result |
|---|---:|---:|---:|---|
| 1 MAL | 2967 | 2967 | 0 | Pass |
| 2 BugsCEP | 13433 | 14820 | 0 | Pass |
| 3 ceramics | 11076 | 22152 | 11996 | Pass |
| 4 Dendrochronology pilot | 27032 | 54064 | 24345 | Pass |
| 5 aDNA | 10 | 20 | 15 | Pass |
| 6 Lund Living Trees | 4534 | 9068 | 4000 | Pass |
| Combined | 59052 | 103091 | 40356 | Pass |

The rolled-back strategies inserted one Pending submission (ID 7) and one dataset (ID 91924) without stale ID sequences. Their comparable values agreed: `Pilot dataset`, type 8, `test-submission`, `TEST_SUBMISSION`, `mal`, upload date `2026-05-23`, provider 1, and unchanged reference dataset 1 linked to submission 1. These results do not validate the current package generator. No shared or source database was used.

**Restore procedure (inspected and run on 2026-09-30)**

The dump requires PostGIS, so use `postgis/postgis:16-3.4`, not the plain PostgreSQL image. The dump was generated by `pg_dump` 18 from a PostgreSQL 16 server: it contains one `DROP DATABASE`, one `CREATE DATABASE`, one `\connect`, four `\restrict`/`\unrestrict` lines, and two `SET transaction_timeout = 0;` lines. The PostgreSQL 16 client cannot process the PostgreSQL 18 client commands or timeout setting. Check these counts and the exact statements again before repeating the procedure. It removes only those lines from the stream; it does not change the baseline dump on disk.

1. In one shell, inspect the control statements and confirm the expected counts. Stop if they differ:

   ```bash
   set -o pipefail
   dump=/data/roger/source/sead_shape_shifter/tmp/sead_staging_baseline.sql.gz
   gzip -t "$dump"
   gzip -cd "$dump" | rg -n '^(DROP DATABASE|CREATE DATABASE|\\connect|\\restrict |\\unrestrict |SET transaction_timeout)'
   # Expect exactly the nine lines described above; inspect the full text of each line.
   ```

2. Start an isolated rootless container, with no port mapping or network, and create a database whose name cannot match the source. Do not mount `tests/.env`, `.pgpass`, the source database, or a host PostgreSQL socket. Run `pg_isready` after initialization completes; if it is not ready, inspect `podman logs "$container"` before proceeding.

   ```bash
   db="ss_contract_$(date +%Y%m%d_%H%M%S)"
   container="ss-pg-${db//_/-}"
   podman run -d --rm --network none --name "$container" \
     -e POSTGRES_HOST_AUTH_METHOD=trust \
     -e POSTGRES_INITDB_ARGS='--locale=en_US.utf8' \
       docker.io/postgis/postgis:16-3.4
   podman inspect --format '{{.HostConfig.NetworkMode}}' "$container"  # Must print none.
   podman exec "$container" pg_isready -U postgres
    podman exec "$container" psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -Atqc \
       "SELECT name FROM pg_available_extensions WHERE name = 'postgis';"  # Must print postgis.
   podman exec "$container" createdb -U postgres --template=template0 --locale=en_US.utf8 "$db"
   ```

3. Only after confirming the nine control lines and `none` network mode, stream the dump to `psql` *inside* that container. The filter drops exact database commands, the PostgreSQL 18 client markers, and its unsupported timeout setting. It never runs the dump against the host or shared server. If `psql` fails, stop and investigate; do not treat a partial restore as a baseline.

   ```bash
   gzip -cd "$dump" | awk '
     $0 == "DROP DATABASE sead_staging;" { next }
     $0 == "CREATE DATABASE sead_staging WITH TEMPLATE = template0 ENCODING = '\''UTF8'\'' LOCALE_PROVIDER = libc LOCALE = '\''en_US.utf8'\'';" { next }
     $0 == "\\connect sead_staging" { next }
     /^\\(un)?restrict [A-Za-z0-9]+$/ { next }
     $0 == "SET transaction_timeout = 0;" { next }
     { print }
   ' | podman exec -i "$container" psql -X -v ON_ERROR_STOP=1 -U postgres -d "$db"
   ```

4. Query the restored database before applying the DDL. The three legacy table names must be non-null, the two new table names must be null, and `has_submission_id` must be false. Record the row counts and compare them with the expected baseline; stop if tables or data are missing. The pre-existing migration function definitions are not a reason to reject this baseline.

    ```bash
    podman exec "$container" psql -X -v ON_ERROR_STOP=1 -U postgres -d "$db" -c \
       "SELECT to_regclass('public.tbl_dataset_masters') AS masters,
                   to_regclass('public.tbl_dataset_submissions') AS legacy_submissions,
                   to_regclass('public.tbl_datasets') AS datasets,
                   to_regclass('public.tbl_submissions') AS new_submissions,
                   to_regclass('public.tbl_data_providers') AS new_providers,
                   EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_schema = 'public' AND table_name = 'tbl_datasets'
                                  AND column_name = 'submission_id') AS has_submission_id;"
    podman exec "$container" psql -X -v ON_ERROR_STOP=1 -U postgres -d "$db" -c \
       "SELECT (SELECT count(*) FROM public.tbl_dataset_masters) AS masters,
                   (SELECT count(*) FROM public.tbl_dataset_submissions) AS legacy_submissions,
                   (SELECT count(*) FROM public.tbl_datasets) AS datasets;"
    ```

    Keep the container available for setup gate 2; when validation is finished, stop only this container with `podman stop "$container"` (its database is disposable).

**Setup gate 2: local clones and assertions**

Clone only databases within the network-isolated container. Start with a separate copy of the restored baseline for DDL and provider-fixture setup; leave the restored baseline unchanged. After preparing that copy, use it as the template for the six independent calls, the combined run, and the artifact checks. Do not use `bin/copy-database` or a shared server as the clone source.

```bash
container=ss-pg-ss-contract-20260930-101335
baseline=ss_contract_20260930_101335
prepared=ss_contract_prepared_20260930_101335
[[ "$(podman inspect --format '{{.HostConfig.NetworkMode}}' "$container")" == none ]]
podman exec "$container" createdb -U postgres --template="$baseline" "$prepared"
podman exec "$container" psql -X -v ON_ERROR_STOP=1 -U postgres -d "$prepared" -c \
   'SELECT count(*) AS datasets FROM public.tbl_datasets;'
```

The first clone was prepared on 2026-09-30 by applying the DDL and current DML function definitions, then copying all six provider identities from `tbl_dataset_masters`. No wrapper or helper was invoked. Confirm that `prepared` has zero submissions, tasks, and linked datasets before making further clones. Before-call snapshots exist for groups 1 through 6 and the combined run (group 0); the template remains unchanged.

| Submission group | Datasets | Expected tasks | New dataset contacts |
|---|---:|---:|---:|
| 1 (MAL) | 2967 | 2967 | 0 |
| 2 (BugsCEP) | 13433 | 14820 | 0 |
| 3 (ceramics) | 11076 | 22152 | 11996 |
| 4 (Dendrochronology pilot) | 27032 | 54064 | 24345 |
| 5 (aDNA) | 10 | 20 | 15 |
| 6 (Lund Living Trees) | 4534 | 9068 | 4000 |
| Combined | 59052 | 103091 | 40356 |

These are before-call counts from independent clones. New contact counts exclude pre-existing matching contacts and duplicate legacy events; they are not the raw count of legacy type 10/11 rows.

For each call, make a fresh clone from `prepared` and run the historical-call assertion script with `submission_id` set to 1 through 6. Use 0 for a separate combined-run clone. The first invocation stores expected dataset IDs, task rows (including bibliography and parsed dates), and the pre-existing and expected new contact rows. Only after setup gate 3, execute the matching call(s) from the DML on that clone and rerun the script with `after=1`. It fails on mismatched submissions, dataset links, task or contact rows, metadata, and sequence positions. Do not repeat a fixed-ID call on a partially migrated clone.

```bash
container=ss-pg-ss-contract-20260930-101335
prepared=ss_contract_prepared_20260930_101335
group=2
clone="ss_contract_group_${group}_$(date +%Y%m%d_%H%M%S)"
[[ "$(podman inspect --format '{{.HostConfig.NetworkMode}}' "$container")" == none ]]
podman exec "$container" createdb -U postgres --template="$prepared" "$clone"
podman exec -i "$container" psql -X -v ON_ERROR_STOP=1 -v "submission_id=$group" \
   -U postgres -d "$clone" < /data/roger/source/sead_shape_shifter/tests/integration/submission_model_contract.sql
# After running only the matching DML call(s) on this clone:
podman exec -i "$container" psql -X -v ON_ERROR_STOP=1 -v "submission_id=$group" -v after=1 \
   -U postgres -d "$clone" < /data/roger/source/sead_shape_shifter/tests/integration/submission_model_contract.sql
```

For artifact validation, clone the completed six-call database twice *after* adding the disposable provider-code fixture. Run the [artifact assertion script](../../../../tests/integration/submission_artifact_contract.sql) without `after` on each clone before applying its package. After applying inline INSERT to one clone and copy-CSV to the other, rerun it with `after=1` and gate 3's actual values as shown below. `new_dataset_ids` must be a PostgreSQL integer-array literal of the package's new dataset IDs (for example `{100,101}`), not IDs from the legacy baseline. It checks that exactly one Pending submission with a native UUID and null submission date was added, that every new dataset references it, and that all pre-existing dataset links are unchanged. Compare the final ordered, ID-free dataset/submission rows printed by each strategy; do not compare generated UUIDs or allocated IDs. The project and concrete parameter values belong to setup gate 3.

```bash
artifact_db="ss_contract_inline_$(date +%Y%m%d_%H%M%S)"
podman exec "$container" createdb -U postgres --template="$combined_db" "$artifact_db"
podman exec -i "$container" psql -X -v ON_ERROR_STOP=1 -U postgres -d "$artifact_db" \
   < /data/roger/source/sead_shape_shifter/tests/integration/submission_artifact_contract.sql
podman exec -i "$container" psql -X -v ON_ERROR_STOP=1 -v after=1 \
   -v "provider_code=$provider_code" -v "submission_name=$submission_name" \
   -v "identifier=$identifier" -v "issue_identifier=$issue_identifier" \
   -v "author=$author" -v "source_name=$source_name" -v "data_types=$data_types" \
   -v "upload_date=$upload_date" -v "new_dataset_ids=$new_dataset_ids" \
   -U postgres -d "$artifact_db" \
   < /data/roger/source/sead_shape_shifter/tests/integration/submission_artifact_contract.sql
```

**Setup gate 3: representative artifact input**

The runnable project context is `test-project` in the submission/dataset tests in [the ingester test file](../../../../backend/tests/ingesters/test_sead_change_request_ingester.py). The `submission.xlsx` argument names an in-memory normalized input supplied through `IngesterConfig.extra["tables"]`; no workbook or on-disk project YAML is required. These tests use a fake SIMS client and do not validate target-ID allocation against the live service. Regenerate both strategy bundles for inspection only; do not deploy them while the identity contract is unresolved:

```bash
.venv/bin/pytest backend/tests/ingesters/test_sead_change_request_ingester.py -q \
   -k 'test_ingest_emits_submission_and_links_new_dataset or test_ingest_copy_csv_emits_submission_and_dataset_payloads' \
   --basetemp=tmp/contract_serial_ids
```

Both bundles are under their respective `tmp/contract_serial_ids/test_ingest_*0/20260523_DML_mal_TEST_SUBMISSION/deploy/` directories. The current packages explicitly insert IDs; the copy-CSV strategy emits sidecars. Regeneration replaces these temporary bundles and changes the generated UUID. Do not run these packages against shared or production databases.

| Input | Baseline / expected package result |
|---|---|
| Provider | `data_provider_code = 'SEAD'` resolves to `data_provider_id = 1` (Bugs database). The prepared database has provider 1 with a null code. After the combined migration calls, set `SEAD` on provider 1 **only on the disposable combined-run database**, then clone it for each artifact strategy. Do not change the source or shared database. |
| Submission | Pending state `1`, name `test-submission`, identifier `TEST_SUBMISSION`, issue `NNN`, author `SEAD Expert`, source `test-project`, data types `mal`, upload date `2026-05-23`, null submission date, and a generated UUID. The rolled-back package test used ID `7`; the current fake SIMS client supplies a fixed test ID. |
| New dataset | Name `Pilot dataset`, linked to the submission ID. The rolled-back package test used `data_type_id = 8` and database-assigned ID `91924`; current test fixtures do not supply a production target ID. |
| Reference-only dataset | No reference-only dataset is present in the current submission/dataset test fixtures. |

After the six calls have passed on the combined-run clone, set the provider code there before making the two artifact clones:

```sql
UPDATE public.tbl_data_providers
SET data_provider_code = 'SEAD'
WHERE data_provider_id = 1 AND data_provider_code IS NULL;
-- Require one updated row and confirm no other provider has code SEAD.
```

The old artifact after-check inputs (`provider_code=SEAD`, `submission_name=test-submission`, `identifier=TEST_SUBMISSION`, `issue_identifier=NNN`, `author=SEAD Expert`, `source_name=test-project`, `data_types=mal`, `upload_date=2026-05-23`, `new_dataset_ids='{91924}'`) apply to the rolled-back test fixture only. Update the fixture and validation parameters after the SIMS identity contract is decided. The full after-check does not pass for current fixed-ID packages.

**Execution**

1. Record the baseline dump identifier as `sead_staging_baseline.sql.gz`, the source database as `sead_staging`, and the snapshot's schema state. Read connection settings locally from `tests/.env`; keep passwords in `.pgpass`. Do not copy credentials into commands, logs, or this handoff.
2. Use the checked restore procedure to load the baseline into the disposable database in the network-isolated container. Never run the unmodified dump against the shared or source server.
3. Confirm the disposable database has the expected legacy tables and data and does not yet contain the submission-model tables or `tbl_datasets.submission_id`. If the dump already includes these schema changes, it cannot validate their application to the baseline.
4. Apply the submission-model DDL and load the DML function definitions on the disposable database, without invoking `migrate_legacy_submission_date()`. Confirm the new tables, columns, keys, indexes, lookup rows, and required contact types. This prepares the test schema; Sqitch scheduling is not under test.
5. On the disposable database, copy provider identities from `tbl_dataset_masters` into `tbl_data_providers` as the wrapper would. Confirm the count and copied identities match. Record this as test setup, not as proof that a deploy script performs the copy.
6. For each of the six calls shown in the DML script, use the prepared assertions to calculate the selected dataset IDs from the baseline using that call's query. Run the call explicitly with its stated parameters on a separate fresh clone of the prepared database, and record the before/after results:
   - Submission 1: MAL, provider 2; datasets with `master_set_id = 2`.
   - Submission 2: BugsCEP, provider 1; datasets with `master_set_id = 1`.
   - Submission 3: ceramics, provider 3; datasets with `master_set_id = 3`.
   - Submission 4: Dendrochronology pilot, provider 10; datasets selected through `tbl_dendro` and `tbl_analysis_entities`.
   - Submission 5: aDNA, provider 12; datasets with `master_set_id = 12`.
   - Submission 6: Lund Living Trees, provider 10; provider 10 datasets not selected by the Dendrochronology pilot query.
7. For each call, assert that exactly one submission has the specified ID, provider, state, and metadata; only the selected datasets acquire its `submission_id`; and unrelated datasets and submissions are unchanged. Compare migrated task rows with legacy types other than 10 and 11 for those datasets, including contact, originating dataset bibliography, notes, and parsed event date. Compare types 10 and 11 with dataset contacts of types 4 and 2, including parsed dates and pre-existing matching contacts; they must not become submission tasks. Record discrepancies per call rather than treating the six calls as one opaque migration.
8. Run the six calls in sequence on one clean prepared clone to check their combined behavior. Confirm each selected dataset has the expected submission, no dataset is assigned to two groups, and any unassigned baseline datasets are reported explicitly. Check that submission and task sequences allocate IDs above the migrated rows. Do not require all baseline datasets to be linked unless the six selection queries cover them all.
9. On the disposable database only, assign a known test `data_provider_code` to a migrated provider (or add a test provider) so the Shape Shifter provider lookup can resolve it. Record the test code; do not copy this fixture change back to the source database.
10. Generate a change-request package from the selected project and input data for each deploy strategy: inline INSERT and copy-CSV. Execute each package against its own clean clone of the database after the six calls.
11. For each strategy, verify one new submission has Pending state, a native UUID, the expected provider, expected submission metadata, and null `submission_date`. Verify newly inserted datasets reference that submission and existing/reference-only datasets were not relinked. Compare the resulting submission and dataset relationships across the two strategies, allowing generated UUIDs or allocated local IDs to differ.
12. Run the existing date-parser verify and the per-call and generated-artifact assertions above. Preserve results without credentials; distinguish individual-call results from the combined run. Drop disposable databases and remove temporary dumps after retaining the validation results.

## Risks

- **Wrong baseline:** A snapshot that already contains the submission-model schema cannot validate application to the legacy schema. Check for the legacy tables and absence of the new tables and `tbl_datasets.submission_id` before applying the DDL; stop and obtain a pre-DDL snapshot if those checks fail.
- **Destructive restore:** The dump's `--clean --create` commands target `sead_staging`. Use an isolated PostgreSQL instance, inspect and retarget every database-level `DROP DATABASE`, `CREATE DATABASE`, and `\connect` command (or create a dump without them), and confirm the connection target and disposable database name before restoring. Never execute the unmodified dump against the source or shared server.
- **Shared-source disruption:** `bin/copy-database` terminates connections to its source. Make independent clones by dump/restore or another snapshot method that does not interrupt the shared source; create them from the prepared disposable database, not from the shared test database.
- **Incomplete setup mistaken for a passed migration:** Loading the DML creates functions but executes no migration; the helper also needs provider rows copied from `tbl_dataset_masters`. Record provider-copy counts and identities, invoke each call explicitly, and verify changed rows. Do not count function creation or fixture setup as migration results.
- **Repeated calls or overlapping groups:** Each call inserts a fixed submission ID and cannot be repeated on the same database; the two provider-10 queries must select distinct datasets. Use one fresh clone per call and a separate clone for the six-call run; compare selected dataset IDs before execution, then check assignments and report unassigned datasets rather than assuming complete coverage.
- **Verification gaps:** The existing DML verify checks only date parsing. Record the per-call task and contact comparisons, combined assignments and sequences, and both artifact-strategy assertions separately; a passing parser verify alone does not satisfy this handoff.
- **Release timing mistaken for validation:** These checks do not establish when provider initialization or the calls will run. Report helper behavior and database prerequisites only; leave change-request placement to a separate decision.

## Outside This Validation

- Decide where provider initialization and each of the six calls belong in the SEAD change-request sequence. Individual calls may run near the Sqitch change request that imports their corresponding submission. This validation does not choose or verify that timing.

## Suggested Follow-Up Documents

- Record the database baseline, per-call and combined-run results, artifact assertions, and any deviations in the task plan's Progress Tracker and Deliverables sections. Mark the acceptance criterion complete only after the individual calls, combined behavior, and both artifact strategies pass.