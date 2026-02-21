"""
Reusable test fixtures for common test scenarios.

This module provides pre-built test data patterns to avoid duplicating
schema/submission setup across test files. Use these instead of loading
large CSV fixtures for simple unit tests.

Usage:
    from tests.fixtures import SIMPLE_SCHEMA, TWO_TABLE_SUBMISSION

    def test_something():
        submission = TWO_TABLE_SUBMISSION()
        # Test logic here
"""

# pylint: disable=invalid-name  # UPPER_CASE is intentional for fixture constants

from typing import Callable

import pandas as pd

from ingesters.sead.metadata import SeadSchema
from ingesters.sead.submission import Submission
from ingesters.sead.tests.builders import build_column, build_schema, build_table

# ============================================================================
# Schema Fixtures
# ============================================================================


def SIMPLE_SCHEMA() -> SeadSchema:
    """Single table schema with PK and two data columns."""
    return build_schema(
        [
            build_table(
                "tbl_simple",
                "simple_id",
                columns={
                    "simple_id": build_column("tbl_simple", "simple_id", is_pk=True),
                    "name": build_column("tbl_simple", "name", data_type="varchar"),
                    "value": build_column("tbl_simple", "value", data_type="integer"),
                },
            )
        ]
    )


def LOOKUP_SCHEMA() -> SeadSchema:
    """Schema with a lookup table."""
    return build_schema(
        [
            build_table(
                "tbl_lookup",
                "lookup_id",
                is_lookup=True,
                columns={
                    "lookup_id": build_column("tbl_lookup", "lookup_id", is_pk=True),
                    "name": build_column("tbl_lookup", "name", data_type="varchar"),
                },
            )
        ]
    )


def TWO_TABLE_SCHEMA() -> SeadSchema:
    """Schema with two tables: main table and lookup table with FK relationship."""
    return build_schema(
        [
            build_table(
                "tbl_main",
                "main_id",
                columns={
                    "main_id": build_column("tbl_main", "main_id", is_pk=True),
                    "lookup_id": build_column("tbl_main", "lookup_id", is_fk=True, fk_table_name="tbl_lookup", fk_column_name="lookup_id"),
                    "description": build_column("tbl_main", "description", data_type="varchar"),
                },
            ),
            build_table(
                "tbl_lookup",
                "lookup_id",
                is_lookup=True,
                columns={
                    "lookup_id": build_column("tbl_lookup", "lookup_id", is_pk=True),
                    "name": build_column("tbl_lookup", "name", data_type="varchar"),
                },
            ),
        ]
    )


def COMPLEX_SCHEMA() -> SeadSchema:
    """Schema with multiple tables and FK relationships."""
    return build_schema(
        [
            build_table(
                "tbl_sites",
                "site_id",
                columns={
                    "site_id": build_column("tbl_sites", "site_id", is_pk=True),
                    "location_id": build_column(
                        "tbl_sites",
                        "location_id",
                        is_fk=True,
                        fk_table_name="tbl_locations",
                        fk_column_name="location_id",
                    ),
                    "site_name": build_column("tbl_sites", "site_name", data_type="varchar"),
                },
            ),
            build_table(
                "tbl_locations",
                "location_id",
                is_lookup=True,
                columns={
                    "location_id": build_column("tbl_locations", "location_id", is_pk=True),
                    "name": build_column("tbl_locations", "name", data_type="varchar"),
                },
            ),
            build_table(
                "tbl_samples",
                "sample_id",
                columns={
                    "sample_id": build_column("tbl_samples", "sample_id", is_pk=True),
                    "site_id": build_column("tbl_samples", "site_id", is_fk=True, fk_table_name="tbl_sites", fk_column_name="site_id"),
                    "sample_name": build_column("tbl_samples", "sample_name", data_type="varchar"),
                },
            ),
        ]
    )


# ============================================================================
# Submission Fixtures (return factory functions)
# ============================================================================


def SIMPLE_SUBMISSION() -> Callable[[], Submission]:
    """Factory for simple single-table submission with new records."""

    def _factory():
        schema = SIMPLE_SCHEMA()
        data_tables = {
            "tbl_simple": pd.DataFrame(
                {
                    "system_id": [1, 2, 3],
                    "simple_id": [None, None, None],  # New records
                    "name": ["Alice", "Bob", "Charlie"],
                    "value": [100, 200, 300],
                }
            )
        }
        return Submission(data_tables=data_tables, schema=schema)

    return _factory


def LOOKUP_SUBMISSION() -> Callable[[], Submission]:
    """Factory for lookup table submission with existing records."""

    def _factory():
        schema = LOOKUP_SCHEMA()
        data_tables = {
            "tbl_lookup": pd.DataFrame(
                {
                    "system_id": [1, 2, 3],
                    "lookup_id": [10, 20, 30],  # Existing records
                    "name": ["Type A", "Type B", "Type C"],
                }
            )
        }
        return Submission(data_tables=data_tables, schema=schema)

    return _factory


def TWO_TABLE_SUBMISSION() -> Callable[[], Submission]:
    """Factory for submission with main table and lookup table."""

    def _factory():
        schema = TWO_TABLE_SCHEMA()
        data_tables = {
            "tbl_main": pd.DataFrame(
                {
                    "system_id": [1, 2],
                    "main_id": [None, None],  # New records
                    "lookup_id": [1, 2],  # References to lookup table
                    "description": ["Main record 1", "Main record 2"],
                }
            ),
            "tbl_lookup": pd.DataFrame(
                {"system_id": [1, 2], "lookup_id": [10, 20], "name": ["Category A", "Category B"]}  # Existing records
            ),
        }
        return Submission(data_tables=data_tables, schema=schema)

    return _factory


def EMPTY_SUBMISSION() -> Callable[[], Submission]:
    """Factory for empty submission (useful for policy testing)."""

    def _factory():
        schema = SIMPLE_SCHEMA()
        return Submission(data_tables={}, schema=schema)

    return _factory


# ============================================================================
# Data Fixtures (raw DataFrames)
# ============================================================================


def SIMPLE_DATAFRAME() -> pd.DataFrame:
    """Simple DataFrame with system_id and PK."""
    return pd.DataFrame({"system_id": [1, 2, 3], "simple_id": [None, None, None], "name": ["A", "B", "C"], "value": [10, 20, 30]})


def LOOKUP_DATAFRAME(with_nulls: bool = False) -> pd.DataFrame:
    """Lookup table DataFrame."""
    data = {
        "system_id": [1, 2, 3],
        "lookup_id": [10, 20, 30] if not with_nulls else [10, None, 30],
        "name": ["Type 1", "Type 2", "Type 3"],
    }
    return pd.DataFrame(data)


def FK_DATAFRAME() -> pd.DataFrame:
    """DataFrame with foreign key references."""
    return pd.DataFrame(
        {
            "system_id": [1, 2, 3],
            "main_id": [None, None, None],
            "lookup_id": [10, 20, 30],  # FK to lookup table
            "description": ["Row 1", "Row 2", "Row 3"],
        }
    )


# ============================================================================
# Fixture Catalog
# ============================================================================

SCHEMA_FIXTURES = {
    "simple": SIMPLE_SCHEMA,
    "lookup": LOOKUP_SCHEMA,
    "two_table": TWO_TABLE_SCHEMA,
    "complex": COMPLEX_SCHEMA,
}

SUBMISSION_FIXTURES = {
    "simple": SIMPLE_SUBMISSION,
    "lookup": LOOKUP_SUBMISSION,
    "two_table": TWO_TABLE_SUBMISSION,
    "empty": EMPTY_SUBMISSION,
}

DATA_FIXTURES = {
    "simple": SIMPLE_DATAFRAME,
    "lookup": LOOKUP_DATAFRAME,
    "fk": FK_DATAFRAME,
}
