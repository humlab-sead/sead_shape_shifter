\set ON_ERROR_STOP on
SELECT set_config('contract.group', :'submission_id', false);

\if :{?after}
DO $$
DECLARE
    selected_group integer := current_setting('contract.group')::integer;
BEGIN
    IF (SELECT count(*) FROM public.tbl_submissions) <>
       (SELECT count(DISTINCT submission_id) FROM contract_check.expected_datasets) THEN
        RAISE EXCEPTION 'Submission count differs from selected groups';
    END IF;

    IF EXISTS (
        SELECT 1 FROM contract_check.expected_datasets expected
        JOIN public.tbl_datasets actual USING (dataset_id)
        WHERE actual.submission_id IS DISTINCT FROM expected.submission_id
    ) OR EXISTS (
        SELECT 1 FROM public.tbl_datasets actual
        WHERE actual.submission_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM contract_check.expected_datasets expected WHERE expected.dataset_id = actual.dataset_id)
    ) THEN
        RAISE EXCEPTION 'Dataset links differ from selected groups';
    END IF;

    IF EXISTS (
        (SELECT submission_id, submission_task_type_id, contact_id, biblio_id, event_date, notes
         FROM contract_check.expected_tasks
         EXCEPT ALL
         SELECT submission_id, submission_task_type_id, contact_id, biblio_id, event_date, notes
         FROM public.tbl_submission_tasks)
        UNION ALL
        (SELECT submission_id, submission_task_type_id, contact_id, biblio_id, event_date, notes
         FROM public.tbl_submission_tasks
         EXCEPT ALL
         SELECT submission_id, submission_task_type_id, contact_id, biblio_id, event_date, notes
         FROM contract_check.expected_tasks)
    ) THEN
        RAISE EXCEPTION 'Submission tasks differ from legacy rows';
    END IF;

    IF EXISTS (
        (SELECT contact_id, contact_type_id, dataset_id, event_date FROM contract_check.before_contacts
         UNION ALL
         SELECT contact_id, contact_type_id, dataset_id, event_date FROM contract_check.expected_contacts
         EXCEPT ALL
         SELECT contact_id, contact_type_id, dataset_id, event_date FROM public.tbl_dataset_contacts)
        UNION ALL
        (SELECT contact_id, contact_type_id, dataset_id, event_date FROM public.tbl_dataset_contacts
         EXCEPT ALL
         (SELECT contact_id, contact_type_id, dataset_id, event_date FROM contract_check.before_contacts
          UNION ALL
          SELECT contact_id, contact_type_id, dataset_id, event_date FROM contract_check.expected_contacts))
    ) THEN
        RAISE EXCEPTION 'Dataset contacts differ from expected legacy event mapping';
    END IF;

    IF EXISTS (
        SELECT 1 FROM public.tbl_submissions actual
        JOIN contract_check.expected_submissions expected USING (submission_id)
        WHERE (actual.data_provider_id, actual.submission_name, actual.submission_state_id,
               actual.submission_identifier, actual.issue_identifier, actual.upload_date,
               actual.submission_date, actual.source_name, actual.data_types)
              IS DISTINCT FROM
              (expected.data_provider_id, expected.submission_name, 2,
               expected.submission_identifier, expected.issue_identifier, expected.upload_date,
               expected.submission_date, expected.source_name, expected.data_types)
           OR actual.submission_uuid IS NULL OR actual.biblio_id IS NOT NULL OR actual.author IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'Submission metadata differs from call parameters';
    END IF;

    IF (SELECT last_value FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'tbl_submissions_submission_id_seq')
       < (SELECT max(submission_id) FROM public.tbl_submissions)
       OR (SELECT last_value FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'tbl_submission_tasks_submission_task_id_seq')
       < (SELECT max(submission_task_id) FROM public.tbl_submission_tasks) THEN
        RAISE EXCEPTION 'Submission or task sequence trails migrated IDs';
    END IF;

    RAISE NOTICE 'Validated group %, % datasets, % tasks, % new contacts', selected_group,
        (SELECT count(*) FROM contract_check.expected_datasets),
        (SELECT count(*) FROM contract_check.expected_tasks),
        (SELECT count(*) FROM contract_check.expected_contacts);
END $$;
\else
CREATE SCHEMA contract_check;

CREATE TABLE contract_check.expected_submissions AS
SELECT * FROM (VALUES
    (1, 2, 'Environmental Archaeology Lab (Umeå)/MAL', '20100101_DML_SUBMISSION_MAL_000_COMMIT',
     'https://github.com/humlab-sead/sead_change_control/issues/221', NULL::date, DATE '2010-01-01', 'sead_master_9', 'archaeobotany,pollen'),
    (2, 1, 'BugsCEP submission (Shape Shifter)', '20231211_DML_SUBMISSION_BUGS_20231219_COMMIT',
     'https://github.com/humlab-sead/sead_change_control/issues/162', NULL::date, DATE '2023-12-19', 'bugsdata_20230705.mdb', 'palaeoentomology,entomology'),
    (3, 3, 'The Laboratory for Ceramic Research (Lund/KFL)', '20200109_DML_SUBMISSION_CERAMICS_COMMIT',
     'https://github.com/humlab-sead/sead_change_control/issues/205', NULL::date, NULL::date, 'ceramics_data_latest_20200107.xlsx', 'ceramics'),
    (4, 10, 'Dendrochronology pilot project (Lund)', '20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT',
     'https://github.com/humlab-sead/sead_change_control/issues/218', NULL::date, NULL::date, 'building_dendro_2023-12_import_v6.xlsx', 'dendrochronology'),
    (5, 12, 'SciLifelab Ancient DNA Pilot Project', '20250108_DML_SUBMISSION_ADNA_001_COMMIT',
     'https://github.com/humlab-sead/sead_change_control/issues/329', DATE '2025-02-17', DATE '2024-11-14',
     'https://github.com/user-attachments/files/18618551/SEAD_aDNA_data_20241114_RM.xlsx', 'adna'),
    (6, 10, 'Lund Living Trees', '20241213_DML_SUBMISSION_LUND_LIVING_TREES_COMMIT',
     'https://github.com/humlab-sead/sead_change_control/issues/348', DATE '2025-03-07', DATE '2023-12-31',
     'lund_living_trees_20241213_RM.xlsx', 'dendrochronology')
) AS rows(submission_id, data_provider_id, submission_name, submission_identifier, issue_identifier,
          upload_date, submission_date, source_name, data_types);

CREATE TABLE contract_check.expected_datasets AS
WITH pilot AS (
    SELECT DISTINCT ae.dataset_id
    FROM public.tbl_dendro d
    JOIN public.tbl_analysis_entities ae USING (analysis_entity_id)
    JOIN public.tbl_datasets ds USING (dataset_id)
    WHERE ds.master_set_id = 10
), groups AS (
    SELECT ds.dataset_id, CASE
        WHEN ds.master_set_id = 2 THEN 1
        WHEN ds.master_set_id = 1 THEN 2
        WHEN ds.master_set_id = 3 THEN 3
        WHEN ds.master_set_id = 10 AND pilot.dataset_id IS NOT NULL THEN 4
        WHEN ds.master_set_id = 12 THEN 5
        WHEN ds.master_set_id = 10 AND pilot.dataset_id IS NULL THEN 6
    END AS submission_id
    FROM public.tbl_datasets ds LEFT JOIN pilot USING (dataset_id)
)
SELECT dataset_id, submission_id FROM groups
WHERE current_setting('contract.group')::integer = 0 OR submission_id = current_setting('contract.group')::integer;

CREATE TABLE contract_check.expected_tasks AS
SELECT selected.submission_id, source.submission_type_id AS submission_task_type_id,
       source.contact_id, datasets.biblio_id,
       public.parse_legacy_submission_date(source.date_submitted) AS event_date, source.notes
FROM public.tbl_dataset_submissions source
JOIN contract_check.expected_datasets selected USING (dataset_id)
JOIN public.tbl_datasets datasets USING (dataset_id)
WHERE source.submission_type_id NOT IN (10, 11);

CREATE TABLE contract_check.before_contacts AS
SELECT contact_id, contact_type_id, dataset_id, event_date FROM public.tbl_dataset_contacts;

CREATE TABLE contract_check.expected_contacts AS
SELECT DISTINCT source.contact_id,
       CASE source.submission_type_id WHEN 10 THEN 4 WHEN 11 THEN 2 END AS contact_type_id,
       source.dataset_id, public.parse_legacy_submission_date(source.date_submitted) AS event_date
FROM public.tbl_dataset_submissions source
JOIN contract_check.expected_datasets selected USING (dataset_id)
WHERE source.submission_type_id IN (10, 11)
  AND NOT EXISTS (
      SELECT 1 FROM contract_check.before_contacts existing
      WHERE existing.dataset_id = source.dataset_id AND existing.contact_id = source.contact_id
        AND existing.contact_type_id = CASE source.submission_type_id WHEN 10 THEN 4 WHEN 11 THEN 2 END
        AND existing.event_date IS NOT DISTINCT FROM public.parse_legacy_submission_date(source.date_submitted)
  );

DO $$
BEGIN
    IF current_setting('contract.group')::integer NOT BETWEEN 0 AND 6
       OR NOT EXISTS (SELECT 1 FROM contract_check.expected_datasets)
       OR EXISTS (SELECT 1 FROM contract_check.expected_datasets WHERE submission_id IS NULL)
       OR (SELECT count(*) FROM public.tbl_submissions) <> 0
       OR (SELECT count(*) FROM public.tbl_submission_tasks) <> 0
       OR EXISTS (SELECT 1 FROM public.tbl_datasets WHERE submission_id IS NOT NULL)
       OR (SELECT count(*) FROM public.tbl_data_providers) <> (SELECT count(*) FROM public.tbl_dataset_masters) THEN
        RAISE EXCEPTION 'Prepared clone is not suitable for the selected migration group';
    END IF;
    RAISE NOTICE 'Before group %, % datasets, % tasks, % new contacts', current_setting('contract.group'),
        (SELECT count(*) FROM contract_check.expected_datasets),
        (SELECT count(*) FROM contract_check.expected_tasks),
        (SELECT count(*) FROM contract_check.expected_contacts);
END $$;
\endif