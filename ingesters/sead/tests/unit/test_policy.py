from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from ingesters.sead.metadata import SeadSchema, Table
from ingesters.sead.policies import (
    AddIdentityMappingSystemIdToPublicIdPolicy,
    AddPrimaryKeyColumnIfMissingPolicy,
    IfForeignKeyValueIsMissingAddIdentityMappingToForeignKeyTable,
    IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId,
    IfSystemIdIsMissingSetSystemIdToPublicId,
    PolicyBase,
    UpdateMissingForeignKeyPolicy,
    UpdateTypesBasedOnSeadSchema,
)
from ingesters.sead.submission import Submission

from tests.builders import build_column, build_schema, build_table


def test_initialization(mock_service):
    schema = MagicMock(spec=SeadSchema)
    submission = MagicMock(spec=Submission)

    policy = PolicyBase(schema=schema, submission=submission, service=mock_service)

    assert policy.schema == schema
    assert policy.submission == submission


def test_get_policy_id(mock_service):
    schema = MagicMock(spec=SeadSchema)
    submission = MagicMock(spec=Submission)

    policy = PolicyBase(schema=schema, submission=submission, service=mock_service)
    assert policy.get_id() == "policy_base"


def test_add_primary_key_column_if_missing_policy(mock_service):
    """Test that missing PK column is added to table."""
    schema = build_schema(
        [
            build_table(
                "table1",
                "id",
                columns={
                    "id": build_column("table1", "id", is_pk=True),
                    "col1": build_column("table1", "col1"),
                },
            )
        ]
    )

    submission = Submission(data_tables={"table1": pd.DataFrame(columns=["col1", "col2"])}, schema=schema)

    policy = AddPrimaryKeyColumnIfMissingPolicy(schema=schema, submission=submission, service=mock_service)
    policy.apply()

    assert "id" in submission.data_tables["table1"].columns


def test_add_default_foreign_key_policy(mock_service):
    """Test that missing FK values are filled with defaults."""
    schema = MagicMock(spec=SeadSchema)
    submission = MagicMock(spec=Submission)
    table: pd.DataFrame = pd.DataFrame({"fk_col": [None, None]})
    submission.data_tables = {"table1": table}
    config_value = MagicMock()
    config_value.resolve.side_effect = [
        False,  # call to is_disabled()
        {"table1": {"fk_col": 2, "fk_col2": 3}},
    ]
    submission.__contains__.side_effect = lambda x: x in submission.data_tables
    submission.__getitem__.side_effect = lambda x: table

    with patch("importer.policies.ConfigValue", return_value=config_value):
        policy = UpdateMissingForeignKeyPolicy(schema=schema, submission=submission, service=mock_service)
        policy.apply()

    assert (table["fk_col"] == 2).all()
    assert (table["fk_col2"] == 3).all()


def test_if_lookup_table_is_missing_add_table_using_system_id_as_public_id(mock_service):
    """Test that referenced lookup table is auto-created with identity mapping."""
    schema = build_schema(
        [
            build_table("table1", "id", is_lookup=False),
        ]
    )

    submission = MagicMock(spec=Submission)
    submission.get_referenced_keyset.return_value = [1, 2, 3]
    submission.data_tables = {}

    # Mock ConfigValue to return enabled status and table inclusion
    config_value = MagicMock()

    def config_resolve(key=None):
        if "disabled" in str(key):
            return False  # Policy is enabled
        if "tables.include" in str(key):
            return {"table1"}  # Include table1
        return None

    config_value.resolve.side_effect = config_resolve

    with patch("importer.policies.ConfigValue", return_value=config_value):
        policy = AddIdentityMappingSystemIdToPublicIdPolicy(schema=schema, submission=submission, service=mock_service)
        policy.apply()

    assert "table1" in submission.data_tables
    assert list(submission.data_tables["table1"]["system_id"]) == [1, 2, 3]
    assert list(submission.data_tables["table1"]["id"]) == [1, 2, 3]


def test_update_types_based_on_sead_schema(mock_service):
    """Test that column data types are updated based on schema definitions."""
    schema = build_schema(
        [
            build_table(
                "table1",
                "id",
                columns={
                    "col1": build_column("table1", "col1", data_type="smallint"),
                    "col2": build_column("table1", "col2", data_type="integer"),
                    "col3": build_column("table1", "col3", data_type="bigint"),
                },
            )
        ]
    )

    submission = Submission(
        data_tables={
            "table1": pd.DataFrame(
                {
                    "col1": [1, 2, 3],
                    "col2": [4, 5, 6],
                    "col3": [7, 8, 9],
                }
            )
        },
        schema=schema,
    )

    policy = UpdateTypesBasedOnSeadSchema(schema=schema, submission=submission, service=mock_service)
    policy.apply()

    assert submission.data_tables["table1"]["col1"].dtype == "Int16"
    assert submission.data_tables["table1"]["col2"].dtype == "Int32"
    assert submission.data_tables["table1"]["col3"].dtype == "Int64"


def test_if_system_id_is_missing_set_system_id_to_public_id(mock_service):
    """Test that NaN system_ids are populated from public PK values."""
    schema = build_schema(
        [
            build_table(
                "table1",
                "id",
                columns={
                    "id": build_column("table1", "id", is_pk=True),
                },
            )
        ]
    )

    submission = Submission(
        data_tables={
            "table1": pd.DataFrame(
                {
                    "id": [1, 2, 3],
                    "system_id": [np.nan, np.nan, np.nan],
                }
            )
        },
        schema=schema,
    )

    policy = IfSystemIdIsMissingSetSystemIdToPublicId(schema=schema, submission=submission, service=mock_service)
    policy.apply()

    assert list(submission.data_tables["table1"]["system_id"]) == [1.0, 2.0, 3.0]


def test_if_foreign_key_value_is_missing_add_identity_mapping_to_foreign_key_table(mock_service):
    """Test that missing FK references trigger creation of lookup records."""
    # Create schema with lookup table
    schema = build_schema(
        [
            build_table(
                "tbl_table",
                "public_id",
                is_lookup=True,
                columns={
                    "public_id": build_column("tbl_table", "public_id", is_pk=True),
                    "value": build_column("tbl_table", "value", data_type="varchar", is_nullable=True),
                },
            )
        ]
    )

    submission = MagicMock(spec=Submission)
    submission.get_referenced_keyset.return_value = [1, 2, 3]
    submission.data_tables = {"tbl_table": pd.DataFrame({"system_id": [1], "public_id": [1], "value": [None]})}
    submission.__contains__.side_effect = lambda x: x in submission.data_tables
    submission.schema = schema

    # Mock service to return empty set for get_primary_key_values
    mock_service.get_primary_key_values.return_value = set()

    policy = IfForeignKeyValueIsMissingAddIdentityMappingToForeignKeyTable(schema=schema, submission=submission, service=mock_service)
    policy.apply()

    # Should have added rows for system_ids 2 and 3
    assert len(submission.data_tables["tbl_table"]) == 3
    assert set(submission.data_tables["tbl_table"]["system_id"]) == {1, 2, 3}


def test_if_lookup_with_no_new_data_then_keep_only_system_id_public_id__not_lookup(mock_service):
    """Test that non-lookup tables are not modified by this policy."""
    schema = MagicMock(spec=SeadSchema)
    submission = MagicMock(spec=Submission)
    table = MagicMock(spec=Table)
    table.is_lookup = False
    schema.__getitem__.return_value = table
    submission.data_tables = {"table1": pd.DataFrame(columns=["system_id", "public_id", "col1", "col2"])}
    policy: PolicyBase = IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId(schema=schema, submission=submission, service=mock_service)
    policy.update()

    assert "col1" in submission.data_tables["table1"].columns
    assert "col2" in submission.data_tables["table1"].columns


def test_if_lookup_with_no_new_data_then_keep_only_system_id_public_id__pk_not_in_data_table(mock_service):
    schema = MagicMock(spec=SeadSchema)
    submission = MagicMock(spec=Submission)
    table = MagicMock(spec=Table)
    table.is_lookup = True
    table.pk_name = "public_id"
    schema.__getitem__.return_value = table
    submission.data_tables = {"table1": pd.DataFrame(columns=["system_id", "col1", "col2"])}

    policy: PolicyBase = IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId(schema=schema, submission=submission, service=mock_service)
    policy.update()

    assert "col1" in submission.data_tables["table1"].columns
    assert "col2" in submission.data_tables["table1"].columns


def test_if_lookup_with_no_new_data_then_keep_only_system_id_public_id__all_pk_values_null(mock_service):
    schema = MagicMock(spec=SeadSchema)
    submission = MagicMock(spec=Submission)
    table = MagicMock(spec=Table)
    table.is_lookup = True
    table.pk_name = "public_id"
    schema.__getitem__.return_value = table
    submission.data_tables = {
        "table1": pd.DataFrame({"system_id": [1, 2, 3], "public_id": [None, None, None], "col1": [4, 5, 6], "col2": [7, 8, 9]})
    }

    policy: PolicyBase = IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId(schema=schema, submission=submission, service=mock_service)
    policy.update()

    assert "col1" in submission.data_tables["table1"].columns
    assert "col2" in submission.data_tables["table1"].columns


def test_not_all_pk_values_null(mock_service):
    schema = MagicMock(spec=SeadSchema)
    submission = MagicMock(spec=Submission)
    table = MagicMock(spec=Table)
    table.is_lookup = True
    table.pk_name = "public_id"
    schema.__getitem__.return_value = table
    submission.data_tables = {
        "table1": pd.DataFrame({"system_id": [1, 2, 3], "public_id": [None, 2, None], "col1": [4, 5, 6], "col2": [7, 8, 9]})
    }

    policy: PolicyBase = IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId(schema=schema, submission=submission, service=mock_service)
    policy.update()

    assert "col1" in submission.data_tables["table1"].columns
    assert "col2" in submission.data_tables["table1"].columns
