"""Tests for derived SEAD submission metadata tables."""

from datetime import datetime
from uuid import UUID

import pandas as pd
import pytest

from ingesters.sead_change_request.contracts import SourceTableBundle, SubmissionContext
from ingesters.sead_change_request.submission_tables import build_submission_source_bundle


def submission_context() -> SubmissionContext:
    """Return complete submission metadata for derived-table tests."""
    return SubmissionContext(
        submission_name="pilot_bugs",
        project_name="pilot",
        timestamp=datetime.fromisoformat("2026-08-30T14:00:00"),
        datatype="bugs",
        identifier="PILOT_BUGS",
        description="Pilot submission",
        issue_identifier="440",
        author="SEAD Lab",
        data_provider_code="SEAD",
    )


def test_builds_submission_metadata_and_links_only_new_datasets() -> None:
    bundle = SourceTableBundle(
        tables={
            "dataset": pd.DataFrame(
                {
                    "system_id": [10, 11],
                    "dataset_id": [None, 901],
                    "dataset_name": ["New", "Existing"],
                }
            )
        }
    )

    result = build_submission_source_bundle(bundle, submission_context(), data_provider_id=51)

    assert list(result.tables) == ["submission_state", "data_provider", "submission", "dataset"]
    assert result.tables["submission_state"].iloc[0]["submission_state_id"] == 1
    assert result.tables["data_provider"].iloc[0]["data_provider_id"] == 51
    submission = result.tables["submission"].iloc[0]
    assert submission["upload_date"].isoformat() == "2026-08-30"
    assert submission["submission_date"] is None
    assert submission["submission_identifier"] == "PILOT_BUGS"
    assert submission["data_provider_id"] == 1
    assert submission["submission_state_id"] == 1
    assert UUID(submission["submission_uuid"])
    assert result.tables["dataset"]["submission_id"].isna().tolist() == [False, True]
    assert result.tables["dataset"].iloc[0]["submission_id"] == 1


def test_rejects_source_owned_submission_tables() -> None:
    bundle = SourceTableBundle(tables={"submission": pd.DataFrame()})

    with pytest.raises(ValueError, match="reserved submission table"):
        build_submission_source_bundle(bundle, submission_context(), data_provider_id=51)
