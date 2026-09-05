"""Build submission metadata tables for SEAD change requests."""

from uuid import uuid4

import pandas as pd

from ingesters.sead_change_request.contracts import SourceTableBundle, SubmissionContext

PENDING_SUBMISSION_STATE_ID = 1
DERIVED_SUBMISSION_TABLES = frozenset({"submission_state", "data_provider", "submission"})


def build_submission_source_bundle(
    bundle: SourceTableBundle,
    submission_context: SubmissionContext,
    data_provider_id: int,
) -> SourceTableBundle:
    """Prepend derived submission tables and link new datasets to the submission."""
    reserved_tables = sorted(DERIVED_SUBMISSION_TABLES.intersection(bundle.tables))
    if reserved_tables:
        raise ValueError("Source bundle contains reserved submission table(s): " + ", ".join(reserved_tables))
    if not submission_context.data_provider_code:
        raise ValueError("Submission context requires data_provider_code")

    submission_system_id = 1
    derived_tables: dict[str, pd.DataFrame] = {
        "submission_state": pd.DataFrame(
            {
                "system_id": [PENDING_SUBMISSION_STATE_ID],
                "submission_state_id": [PENDING_SUBMISSION_STATE_ID],
                "submission_state": ["Pending"],
            }
        ),
        "data_provider": pd.DataFrame(
            {
                "system_id": [1],
                "data_provider_id": [data_provider_id],
                "data_provider_code": [submission_context.data_provider_code],
            }
        ),
        "submission": pd.DataFrame(
            {
                "system_id": [submission_system_id],
                "submission_id": [None],
                "submission_state_id": [PENDING_SUBMISSION_STATE_ID],
                "biblio_id": [None],
                "upload_date": [submission_context.timestamp.date()],
                "submission_date": [None],
                "submission_identifier": [submission_context.identifier],
                "issue_identifier": [submission_context.issue_identifier],
                "author": [submission_context.author],
                "notes": [submission_context.description],
                "data_provider_id": [1],
                "submission_name": [submission_context.submission_name],
                "source_name": [submission_context.project_name],
                "data_types": [submission_context.datatype],
                "submission_uuid": [str(uuid4())],
            }
        ),
    }

    source_tables: dict[str, pd.DataFrame] = {}
    for entity_name, source_frame in bundle.tables.items():
        frame = source_frame.copy()
        if entity_name == "dataset":
            if "dataset_id" not in frame.columns:
                raise ValueError("Dataset table requires dataset_id before submission links can be derived")
            if "submission_id" not in frame.columns:
                frame["submission_id"] = pd.NA
            new_dataset_mask = frame["dataset_id"].isna()
            frame.loc[new_dataset_mask, "submission_id"] = submission_system_id
        source_tables[entity_name] = frame

    return SourceTableBundle(
        tables={**derived_tables, **source_tables},
        source_name=bundle.source_name,
        warnings=list(bundle.warnings),
    )
