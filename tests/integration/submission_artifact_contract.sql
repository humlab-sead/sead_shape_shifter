\set ON_ERROR_STOP on

\if :{?after}
SELECT set_config('contract.provider_code', :'provider_code', false);
SELECT set_config('contract.submission_name', :'submission_name', false);
SELECT set_config('contract.identifier', :'identifier', false);
SELECT set_config('contract.issue_identifier', :'issue_identifier', false);
SELECT set_config('contract.author', :'author', false);
SELECT set_config('contract.source_name', :'source_name', false);
SELECT set_config('contract.data_types', :'data_types', false);
SELECT set_config('contract.upload_date', :'upload_date', false);
SELECT set_config('contract.new_dataset_ids', :'new_dataset_ids', false);

DO $$
DECLARE
    new_submission_id integer;
    expected_provider_id integer;
BEGIN
    SELECT data_provider_id INTO STRICT expected_provider_id
    FROM public.tbl_data_providers
    WHERE data_provider_code = current_setting('contract.provider_code');

    IF (SELECT count(*) FROM public.tbl_submissions) <>
       (SELECT count(*) + 1 FROM contract_artifact_check.before_submissions) THEN
        RAISE EXCEPTION 'Expected exactly one new submission';
    END IF;

    SELECT submission_id INTO STRICT new_submission_id
    FROM public.tbl_submissions
    WHERE submission_id NOT IN (SELECT submission_id FROM contract_artifact_check.before_submissions);

    IF NOT EXISTS (
        SELECT 1 FROM public.tbl_submissions submission
        JOIN public.tbl_submission_states state USING (submission_state_id)
        WHERE submission.submission_id = new_submission_id
          AND state.submission_state_id = 1 AND state.submission_state = 'Pending'
          AND submission.data_provider_id = expected_provider_id
          AND pg_typeof(submission.submission_uuid) = 'uuid'::regtype
          AND submission.submission_uuid IS NOT NULL
          AND submission.submission_date IS NULL
          AND submission.submission_name = current_setting('contract.submission_name')
          AND submission.submission_identifier = current_setting('contract.identifier')
          AND submission.issue_identifier = current_setting('contract.issue_identifier')
          AND submission.author = current_setting('contract.author')
          AND submission.source_name = current_setting('contract.source_name')
          AND submission.data_types = current_setting('contract.data_types')
          AND submission.upload_date = current_setting('contract.upload_date')::date
    ) THEN
        RAISE EXCEPTION 'New submission metadata differs from expected values';
    END IF;

    IF EXISTS (
        SELECT 1 FROM public.tbl_datasets current_row
        JOIN contract_artifact_check.before_datasets previous USING (dataset_id)
        WHERE current_row.submission_id IS DISTINCT FROM previous.submission_id
    ) THEN
        RAISE EXCEPTION 'An existing or reference-only dataset was relinked';
    END IF;

    IF cardinality(current_setting('contract.new_dataset_ids')::integer[]) = 0 THEN
        RAISE EXCEPTION 'Expected at least one new dataset';
    END IF;

    IF EXISTS (
        (SELECT dataset_id FROM public.tbl_datasets
         WHERE dataset_id NOT IN (SELECT dataset_id FROM contract_artifact_check.before_datasets)
         EXCEPT ALL
         SELECT unnest(current_setting('contract.new_dataset_ids')::integer[]))
        UNION ALL
        (SELECT unnest(current_setting('contract.new_dataset_ids')::integer[])
         EXCEPT ALL
         SELECT dataset_id FROM public.tbl_datasets
         WHERE dataset_id NOT IN (SELECT dataset_id FROM contract_artifact_check.before_datasets))
    ) OR EXISTS (
        SELECT 1 FROM public.tbl_datasets
        WHERE dataset_id = ANY(current_setting('contract.new_dataset_ids')::integer[])
          AND submission_id IS DISTINCT FROM new_submission_id
    ) THEN
        RAISE EXCEPTION 'New dataset IDs or submission links differ from the package';
    END IF;

    IF EXISTS (
        SELECT 1 FROM public.tbl_submissions_submission_id_seq
        WHERE last_value < (SELECT max(submission_id) FROM public.tbl_submissions)
           OR (last_value = (SELECT max(submission_id) FROM public.tbl_submissions) AND NOT is_called)
    ) OR EXISTS (
        SELECT 1 FROM public.tbl_datasets_dataset_id_seq
        WHERE last_value < (SELECT max(dataset_id) FROM public.tbl_datasets)
           OR (last_value = (SELECT max(dataset_id) FROM public.tbl_datasets) AND NOT is_called)
    ) THEN
        RAISE EXCEPTION 'Submission or dataset sequence would reuse an inserted ID';
    END IF;

    RAISE NOTICE 'Validated submission % and % new datasets', new_submission_id,
        cardinality(current_setting('contract.new_dataset_ids')::integer[]);
END $$;

SELECT dataset_name, submission.submission_name, submission.submission_identifier,
       submission.data_types, submission.upload_date, state.submission_state
FROM public.tbl_datasets dataset
JOIN public.tbl_submissions submission USING (submission_id)
JOIN public.tbl_submission_states state USING (submission_state_id)
WHERE dataset.dataset_id = ANY(current_setting('contract.new_dataset_ids')::integer[])
ORDER BY dataset_name;
\else
CREATE SCHEMA contract_artifact_check;
CREATE TABLE contract_artifact_check.before_submissions AS
SELECT submission_id FROM public.tbl_submissions;
CREATE TABLE contract_artifact_check.before_datasets AS
SELECT dataset_id, submission_id FROM public.tbl_datasets;
\endif