"""Tests for SEAD change request PK/FK target projection."""

import pandas as pd

from ingesters.sead_change_request import ChangeRowState, project_target_ids
from ingesters.sead_change_request.contracts import (
    IdentityResolutionResult,
    PlannedRowAction,
    PlannedTable,
    ResolvedIdentityTable,
)
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


def conditional_location_target_model() -> TargetModel:
    """Build a target model with a conditional location -> location_type foreign key."""
    return minimal_target_model(
        location_type={"role": "lookup", "public_id": "location_type_id"},
        location={
            "role": "fact",
            "public_id": "location_id",
            "columns": {"location_type_id": {"type": "integer", "nullable": False}},
            "foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "location"}}],
        },
    )


def make_resolved_table(
    entity_name: str,
    frame: pd.DataFrame,
    row_states: list[ChangeRowState],
    resolved_target_ids: list[int | None],
) -> ResolvedIdentityTable:
    """Build a resolved identity table with aligned row states and target IDs."""
    return ResolvedIdentityTable(
        entity_name=entity_name,
        frame=frame,
        row_states=pd.Series(row_states, index=frame.index, name="_row_state"),
        resolved_target_ids=pd.Series(resolved_target_ids, index=frame.index, dtype="Int64", name="_target_id"),
    )


def make_planned_table(entity_name: str, frame: pd.DataFrame, planned_actions: list[PlannedRowAction]) -> PlannedTable:
    """Build a planned table with the given planned row actions."""
    return PlannedTable(
        entity_name=entity_name,
        frame=frame,
        planned_actions=pd.Series(planned_actions, index=frame.index, name="_planned_action"),
    )


def make_location_type_table(system_id: int = 1, resolved_target_id: int = 901) -> ResolvedIdentityTable:
    """Build a resolved location_type lookup table used by the conditional FK."""
    frame = pd.DataFrame({"system_id": [system_id], "location_type_id": [None]})
    return make_resolved_table("location_type", frame, [ChangeRowState.NEWLY_ALLOCATED_ENTITY], [resolved_target_id])


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

    def test_reports_missing_required_sample_foreign_keys(self):
        """Required sample group and type references must not project as null."""
        frame = pd.DataFrame(
            {
                "system_id": [10],
                "physical_sample_id": [None],
                "sample_group_id": [None],
                "sample_type_id": [None],
            }
        )
        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([601], index=frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )
        target_model = minimal_target_model(
            sample_group={"role": "fact", "public_id": "sample_group_id"},
            sample_type={"role": "lookup", "public_id": "sample_type_id"},
            sample={
                "role": "fact",
                "public_id": "physical_sample_id",
                "foreign_keys": [
                    {"entity": "sample_group", "required": True},
                    {"entity": "sample_type", "required": True},
                ],
            },
        )

        result = project_target_ids(identity_result, target_model)

        assert result.diagnostics == [
            "Entity 'sample' has 1 missing required FK value(s) for 'sample_group_id'",
            "Entity 'sample' has 1 missing required FK value(s) for 'sample_type_id'",
        ]

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


class TestProjectConditionalForeignKeys:
    """Tests for conditional foreign keys evaluated from final reconciled row states."""

    def test_conditional_foreign_key_adds_no_error_for_matched_rows(self):
        """A matched row must not trigger the condition, even when its FK value cannot be resolved."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None], "location_type_id": [99]})
        identity_result = IdentityResolutionResult(
            tables={"location": make_resolved_table("location", frame, [ChangeRowState.EXISTING_ENTITY], [501])}
        )

        result = project_target_ids(identity_result, conditional_location_target_model())

        assert result.diagnostics == []
        assert result.tables["location"].frame["location_type_id"].tolist() == [99]

    def test_conditional_foreign_key_adds_no_error_for_matched_rows_with_null_value(self):
        """A matched row with a null FK value must not trigger the missing-value check."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None], "location_type_id": [None]})
        identity_result = IdentityResolutionResult(
            tables={
                "location": make_resolved_table("location", frame, [ChangeRowState.EXISTING_ENTITY], [501]),
                "location_type": make_location_type_table(),
            }
        )

        result = project_target_ids(identity_result, conditional_location_target_model())

        assert result.diagnostics == []

    def test_conditional_foreign_key_adds_no_error_for_matched_rows_without_fk_column(self):
        """A matched-only submission must not fail when the conditional FK column is absent."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None]})
        identity_result = IdentityResolutionResult(
            tables={
                "location": make_resolved_table("location", frame, [ChangeRowState.EXISTING_ENTITY], [501]),
                "location_type": make_location_type_table(),
            }
        )

        result = project_target_ids(identity_result, conditional_location_target_model())

        assert result.diagnostics == []

    def test_conditional_foreign_key_adds_no_error_for_reference_only_planned_rows(self):
        """A reference-only planned row must not trigger the condition when planned actions are supplied."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None], "location_type_id": [99]})
        identity_result = IdentityResolutionResult(
            tables={
                "location": make_resolved_table("location", frame, [ChangeRowState.EXISTING_ENTITY], [501]),
                "location_type": make_location_type_table(),
            }
        )
        planned_tables = [make_planned_table("location", frame, [PlannedRowAction.REFERENCE_EXISTING])]

        result = project_target_ids(identity_result, conditional_location_target_model(), planned_tables)

        assert result.diagnostics == []

    def test_reports_missing_conditional_foreign_key_column_for_inserted_rows(self):
        """An inserted row without the target-facing FK column must report the missing project link."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None]})
        identity_result = IdentityResolutionResult(
            tables={"location": make_resolved_table("location", frame, [ChangeRowState.NEWLY_ALLOCATED_ENTITY], [601])}
        )

        result = project_target_ids(identity_result, conditional_location_target_model())

        assert result.diagnostics == ["Entity 'location' is missing conditional FK column 'location_type_id' for 'location_type'"]
        assert result.tables["location"].frame["location_id"].tolist() == [601]

    def test_reports_missing_conditional_foreign_key_lookup_for_inserted_rows(self):
        """An inserted row whose FK value cannot be projected must report the missing lookup table."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None], "location_type_id": [1]})
        identity_result = IdentityResolutionResult(
            tables={"location": make_resolved_table("location", frame, [ChangeRowState.NEWLY_ALLOCATED_ENTITY], [601])}
        )

        result = project_target_ids(identity_result, conditional_location_target_model())

        assert result.diagnostics == [
            "Entity 'location' cannot project conditional foreign key 'location_type_id' because resolved table 'location_type' is missing"
        ]

    def test_reports_null_conditional_foreign_key_value_for_inserted_rows(self):
        """An inserted row must report a null conditional FK value."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None], "location_type_id": [None]})
        identity_result = IdentityResolutionResult(
            tables={
                "location": make_resolved_table("location", frame, [ChangeRowState.NEWLY_ALLOCATED_ENTITY], [601]),
                "location_type": make_location_type_table(),
            }
        )

        result = project_target_ids(identity_result, conditional_location_target_model())

        assert result.diagnostics == ["Entity 'location' has 1 missing conditional FK value(s) for 'location_type_id'"]

    def test_reports_unresolved_conditional_foreign_key_value_for_inserted_rows(self):
        """An inserted row whose FK value has no target mapping must report the unresolved value."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None], "location_type_id": [99]})
        identity_result = IdentityResolutionResult(
            tables={
                "location": make_resolved_table("location", frame, [ChangeRowState.NEWLY_ALLOCATED_ENTITY], [601]),
                "location_type": make_location_type_table(),
            }
        )

        result = project_target_ids(identity_result, conditional_location_target_model())

        assert result.diagnostics == ["Entity 'location' has 1 unresolved conditional FK value(s) for 'location_type_id'"]
        assert result.tables["location"].frame["location_type_id"].isna().tolist() == [True]

    def test_conditional_foreign_key_evaluates_inserted_rows_only_in_mixed_tables(self):
        """Only inserted rows should count for the condition when matched and inserted rows are mixed."""
        frame = pd.DataFrame({"system_id": [10, 11], "location_id": [None, None], "location_type_id": [99, 1]})
        identity_result = IdentityResolutionResult(
            tables={
                "location": make_resolved_table(
                    "location",
                    frame,
                    [ChangeRowState.EXISTING_ENTITY, ChangeRowState.NEWLY_ALLOCATED_ENTITY],
                    [501, 601],
                ),
                "location_type": make_location_type_table(),
            }
        )

        result = project_target_ids(identity_result, conditional_location_target_model())

        assert result.diagnostics == []
        assert result.tables["location"].frame.loc[1, "location_type_id"] == 901

    def test_does_not_activate_condition_for_blocked_rows(self):
        """A blocked row must not activate the condition; its existing resolution error remains separate."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None], "location_type_id": [None]})
        identity_result = IdentityResolutionResult(
            tables={"location": make_resolved_table("location", frame, [ChangeRowState.BLOCKED_UNRESOLVED], [None])}
        )

        result = project_target_ids(identity_result, conditional_location_target_model())

        assert result.diagnostics == ["Entity 'location' has 1 row(s) without a resolved target ID for 'location_id'"]

    def test_projects_conditional_foreign_key_for_update_candidate(self):
        """An accepted update candidate keeps its projected FK value without failing the condition."""
        frame = pd.DataFrame({"system_id": [10, 11], "location_id": [None, None], "location_type_id": [99, 1]})
        identity_result = IdentityResolutionResult(
            tables={
                "location": make_resolved_table(
                    "location",
                    frame,
                    [ChangeRowState.EXISTING_ENTITY, ChangeRowState.EXISTING_ENTITY],
                    [501, 502],
                ),
                "location_type": make_location_type_table(),
            }
        )
        planned_tables = [
            make_planned_table("location", frame, [PlannedRowAction.REFERENCE_EXISTING, PlannedRowAction.UPDATE_EXISTING_CANDIDATE])
        ]

        result = project_target_ids(identity_result, conditional_location_target_model(), planned_tables)

        assert result.diagnostics == []
        assert result.tables["location"].frame.loc[1, "location_type_id"] == 901

    def test_reports_unresolved_conditional_foreign_key_value_used_by_update_candidate(self):
        """An update candidate whose FK value has no target mapping must still report the unresolved value."""
        frame = pd.DataFrame({"system_id": [10], "location_id": [None], "location_type_id": [99]})
        identity_result = IdentityResolutionResult(
            tables={
                "location": make_resolved_table("location", frame, [ChangeRowState.EXISTING_ENTITY], [501]),
                "location_type": make_location_type_table(),
            }
        )
        planned_tables = [make_planned_table("location", frame, [PlannedRowAction.UPDATE_EXISTING_CANDIDATE])]

        result = project_target_ids(identity_result, conditional_location_target_model(), planned_tables)

        assert result.diagnostics == ["Entity 'location' has 1 unresolved conditional FK value(s) for 'location_type_id'"]
