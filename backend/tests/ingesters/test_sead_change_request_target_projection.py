"""Tests for SEAD change request PK/FK target projection."""

import pandas as pd

from ingesters.sead_change_request import ChangeRowState, project_target_ids
from ingesters.sead_change_request.contracts import IdentityResolutionResult, ResolvedIdentityTable
from src.target_model.models import TargetModel


def minimal_target_model(**extra_entities: dict) -> TargetModel:
    """Build a minimal TargetModel for target projection tests."""
    return TargetModel.model_validate(
        {
            "model": {"name": "SEAD Test Model", "version": "0.1.0"},
            "entities": extra_entities,
            "constraints": [],
        }
    )


class TestProjectTargetIds:
    """Tests for PK/FK target projection from resolved identities."""

    def test_projects_entity_public_id_from_resolved_target_ids(self):
        """A table's own public_id column should be rewritten from resolved target IDs."""
        frame = pd.DataFrame({"system_id": [1, 2], "sample_id": [None, None], "sample_name": ["A", "B"]})
        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=frame,
                    row_states=pd.Series(
                        [ChangeRowState.NEWLY_ALLOCATED_ENTITY, ChangeRowState.NEWLY_ALLOCATED_ENTITY],
                        index=frame.index,
                        name="_row_state",
                    ),
                    resolved_target_ids=pd.Series([101, 102], index=frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )

        result = project_target_ids(identity_result, minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}))

        assert result.tables["sample"].frame["sample_id"].tolist() == [101, 102]
        assert not result.diagnostics

    def test_projects_foreign_keys_from_parent_system_id_mapping(self):
        """FK columns should be rewritten from parent local system_id values to parent resolved target IDs."""
        parent_frame = pd.DataFrame({"system_id": [1, 2], "site_id": [None, None], "site_name": ["A", "B"]})
        child_frame = pd.DataFrame({"system_id": [10, 11], "sample_id": [None, None], "site_id": [1, 2]})
        identity_result = IdentityResolutionResult(
            tables={
                "site": ResolvedIdentityTable(
                    entity_name="site",
                    frame=parent_frame,
                    row_states=pd.Series(
                        [ChangeRowState.NEWLY_ALLOCATED_ENTITY, ChangeRowState.NEWLY_ALLOCATED_ENTITY],
                        index=parent_frame.index,
                        name="_row_state",
                    ),
                    resolved_target_ids=pd.Series([501, 502], index=parent_frame.index, dtype="Int64", name="_target_id"),
                ),
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=child_frame,
                    row_states=pd.Series(
                        [ChangeRowState.NEWLY_ALLOCATED_ENTITY, ChangeRowState.NEWLY_ALLOCATED_ENTITY],
                        index=child_frame.index,
                        name="_row_state",
                    ),
                    resolved_target_ids=pd.Series([601, 602], index=child_frame.index, dtype="Int64", name="_target_id"),
                ),
            }
        )
        target_model = minimal_target_model(
            site={"role": "lookup", "public_id": "site_id"},
            sample={"role": "fact", "public_id": "sample_id", "foreign_keys": [{"entity": "site"}]},
        )

        result = project_target_ids(identity_result, target_model)

        assert result.tables["sample"].frame["sample_id"].tolist() == [601, 602]
        assert result.tables["sample"].frame["site_id"].tolist() == [501, 502]
        assert not result.diagnostics

    def test_reports_unresolved_foreign_keys_when_parent_mapping_missing(self):
        """Unmapped FK values should become null and produce a diagnostic."""
        parent_frame = pd.DataFrame({"system_id": [1], "site_id": [None]})
        child_frame = pd.DataFrame({"system_id": [10], "sample_id": [None], "site_id": [99]})
        identity_result = IdentityResolutionResult(
            tables={
                "site": ResolvedIdentityTable(
                    entity_name="site",
                    frame=parent_frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=parent_frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([501], index=parent_frame.index, dtype="Int64", name="_target_id"),
                ),
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=child_frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=child_frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([601], index=child_frame.index, dtype="Int64", name="_target_id"),
                ),
            }
        )
        target_model = minimal_target_model(
            site={"role": "lookup", "public_id": "site_id"},
            sample={"role": "fact", "public_id": "sample_id", "foreign_keys": [{"entity": "site"}]},
        )

        result = project_target_ids(identity_result, target_model)

        assert result.tables["sample"].frame["site_id"].isna().tolist() == [True]
        assert result.diagnostics == ["Entity 'sample' has 1 unresolved FK value(s) for 'site_id'"]

    def test_skips_parent_resolution_for_entirely_null_foreign_key(self):
        """A nullable FK with no values should not require its parent table in the bundle."""
        submission_frame = pd.DataFrame({"system_id": [1], "submission_id": [None], "biblio_id": [None]})
        identity_result = IdentityResolutionResult(
            tables={
                "submission": ResolvedIdentityTable(
                    entity_name="submission",
                    frame=submission_frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=submission_frame.index),
                    resolved_target_ids=pd.Series([701], index=submission_frame.index, dtype="Int64"),
                )
            }
        )
        target_model = minimal_target_model(
            citation={"role": "lookup", "public_id": "biblio_id"},
            submission={"role": "fact", "public_id": "submission_id", "foreign_keys": [{"entity": "citation"}]},
        )

        result = project_target_ids(identity_result, target_model)

        assert result.tables["submission"].frame["submission_id"].tolist() == [701]
        assert not result.diagnostics
