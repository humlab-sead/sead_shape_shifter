"""Tests for reusable fixtures module."""

import pandas as pd
from ingesters.sead.metadata import Column, SeadSchema
from ingesters.sead.submission import Submission

from ingesters.sead.tests.fixtures import (
    COMPLEX_SCHEMA,
    EMPTY_SUBMISSION,
    FK_DATAFRAME,
    LOOKUP_DATAFRAME,
    LOOKUP_SCHEMA,
    LOOKUP_SUBMISSION,
    SIMPLE_DATAFRAME,
    SIMPLE_SCHEMA,
    SIMPLE_SUBMISSION,
    TWO_TABLE_SCHEMA,
    TWO_TABLE_SUBMISSION,
)

# ============================================================================
# Schema Fixture Tests
# ============================================================================


def test_simple_schema():
    """Test SIMPLE_SCHEMA fixture."""
    schema = SIMPLE_SCHEMA()
    assert isinstance(schema, SeadSchema)
    assert "tbl_simple" in schema
    assert schema["tbl_simple"].pk_name == "simple_id"
    assert len(schema["tbl_simple"].columns) == 3


def test_lookup_schema():
    """Test LOOKUP_SCHEMA fixture."""
    schema = LOOKUP_SCHEMA()
    assert isinstance(schema, SeadSchema)
    assert "tbl_lookup" in schema
    assert schema["tbl_lookup"].is_lookup is True


def test_two_table_schema():
    """Test TWO_TABLE_SCHEMA fixture."""
    schema = TWO_TABLE_SCHEMA()
    assert isinstance(schema, SeadSchema)
    assert "tbl_main" in schema
    assert "tbl_lookup" in schema
    column: Column = schema["tbl_main"].columns["lookup_id"]
    assert column.is_fk is True


def test_complex_schema():
    """Test COMPLEX_SCHEMA fixture."""
    schema = COMPLEX_SCHEMA()
    assert len(schema) == 3
    assert "tbl_sites" in schema
    assert "tbl_locations" in schema
    assert "tbl_samples" in schema


# ============================================================================
# Submission Fixture Tests
# ============================================================================


def test_simple_submission():
    """Test SIMPLE_SUBMISSION fixture."""
    factory = SIMPLE_SUBMISSION()
    submission = factory()

    assert isinstance(submission, Submission)
    assert "tbl_simple" in submission.data_tables
    assert len(submission.data_tables["tbl_simple"]) == 3


def test_lookup_submission():
    """Test LOOKUP_SUBMISSION fixture."""
    factory = LOOKUP_SUBMISSION()
    submission = factory()

    assert isinstance(submission, Submission)
    assert "tbl_lookup" in submission.data_tables
    assert submission.schema["tbl_lookup"].is_lookup is True


def test_two_table_submission():
    """Test TWO_TABLE_SUBMISSION fixture."""
    factory = TWO_TABLE_SUBMISSION()
    submission = factory()

    assert len(submission.data_tables) == 2
    assert "tbl_main" in submission.data_tables
    assert "tbl_lookup" in submission.data_tables


def test_empty_submission():
    """Test EMPTY_SUBMISSION fixture."""
    factory = EMPTY_SUBMISSION()
    submission = factory()

    assert isinstance(submission, Submission)
    assert len(submission.data_tables) == 0


# ============================================================================
# Data Fixture Tests
# ============================================================================


def test_simple_dataframe():
    """Test SIMPLE_DATAFRAME fixture."""
    df = SIMPLE_DATAFRAME()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "system_id" in df.columns
    assert "simple_id" in df.columns


def test_lookup_dataframe():
    """Test LOOKUP_DATAFRAME fixture."""
    df = LOOKUP_DATAFRAME()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert all(df["lookup_id"] > 0)


def test_lookup_dataframe_with_nulls():
    """Test LOOKUP_DATAFRAME with nulls."""
    df = LOOKUP_DATAFRAME(with_nulls=True)
    assert df["lookup_id"].isnull().any()


def test_fk_dataframe():
    """Test FK_DATAFRAME fixture."""
    df = FK_DATAFRAME()
    assert isinstance(df, pd.DataFrame)
    assert "lookup_id" in df.columns
    assert all(df["lookup_id"] > 0)


# ============================================================================
# Fixture Reusability Tests
# ============================================================================


def test_fixtures_are_independent():
    """Test that multiple calls to fixtures return independent objects."""
    schema1 = SIMPLE_SCHEMA()
    schema2 = SIMPLE_SCHEMA()

    # Should be equal but not same object
    assert schema1["tbl_simple"].table_name == schema2["tbl_simple"].table_name
    assert schema1 is not schema2


def test_submission_factories_are_independent():
    """Test that submission factories create independent submissions."""
    factory = SIMPLE_SUBMISSION()
    sub1 = factory()
    sub2 = factory()

    # Modify one submission
    sub1.data_tables["tbl_simple"].loc[0, "value"] = 999

    # Other submission should be unaffected
    assert sub2.data_tables["tbl_simple"].loc[0, "value"] == 100
