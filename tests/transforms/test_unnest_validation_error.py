"""Tests to verify unnest raises errors for missing columns instead of silently failing."""

import pandas as pd
import pytest

from src.model import TableConfig
from src.transforms.unnest import unnest


class TestUnnestValidationErrors:
    """Test that unnest raises clear errors when columns are missing."""

    def test_unnest_error_includes_available_columns(self):
        """Test that error message includes list of available columns for debugging."""
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2], "name": ["A", "B"], "amount": [10, 20]})
        config = {
            "test_entity": {
                "columns": ["id", "name", "amount"],
                "unnest": {
                    "id_vars": ["id"],
                    "value_vars": ["name", "missing_col"],  # missing_col doesn't exist
                    "var_name": "variable",
                    "value_name": "value",
                },
            }
        }
        table_cfg = TableConfig(entities_cfg=config, entity_name=entity)

        with pytest.raises(ValueError) as exc_info:
            unnest(entity, table, table_cfg)

        error_msg = str(exc_info.value)
        assert "Cannot unnest entity" in error_msg
        assert "missing_col" in error_msg
        assert "Available columns:" in error_msg
        # Check that available columns are listed
        assert "id" in error_msg
        assert "name" in error_msg

    def test_unnest_error_suggests_fix(self):
        """Test that error message suggests where to define missing columns."""
        entity = "site_property"
        table = pd.DataFrame({"site_id": [1], "socken": ["ABC"], "raanr": ["123"]})
        config = {
            "site_property": {
                "columns": ["site_id", "socken", "raanr"],
                "unnest": {
                    "id_vars": ["site_id"],
                    "value_vars": ["lamningsnummer"],  # Not in columns or extra_columns
                    "var_name": "property_type",
                    "value_name": "property_value",
                },
            }
        }
        table_cfg = TableConfig(entities_cfg=config, entity_name=entity)

        with pytest.raises(ValueError) as exc_info:
            unnest(entity, table, table_cfg)

        error_msg = str(exc_info.value)
        assert "Check that value_vars columns are defined" in error_msg
        assert "'columns'" in error_msg
        assert "'keys'" in error_msg
        assert "'extra_columns'" in error_msg
        assert "foreign keys" in error_msg

    def test_unnest_multiple_missing_columns_lists_all(self):
        """Test that error lists all missing columns, not just the first one."""
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2]})
        config = {
            "test_entity": {
                "columns": ["id"],
                "unnest": {
                    "id_vars": ["id"],
                    "value_vars": ["col1", "col2", "col3"],  # All missing
                    "var_name": "variable",
                    "value_name": "value",
                },
            }
        }
        table_cfg = TableConfig(entities_cfg=config, entity_name=entity)

        with pytest.raises(ValueError) as exc_info:
            unnest(entity, table, table_cfg)

        error_msg = str(exc_info.value)
        assert "col1" in error_msg
        assert "col2" in error_msg
        assert "col3" in error_msg

    def test_unnest_with_extra_columns_in_table_succeeds(self):
        """Test that unnest succeeds when extra_columns are present in table."""
        entity = "site_property"
        # Simulate table AFTER extra_columns have been evaluated
        table = pd.DataFrame(
            {
                "site_id": [1, 2],
                "socken": ["ABC", "DEF"],
                "raanr": ["123", "456"],
                "raa_number": ["ABC 123", "DEF 456"],  # Created by extra_columns
                "lamningsnummer": ["L001", "L002"],
            }
        )
        config = {
            "site_property": {
                "columns": ["site_id", "socken", "raanr", "lamningsnummer"],
                "extra_columns": {"raa_number": "{socken} {raanr}"},
                "unnest": {
                    "id_vars": ["site_id"],
                    "value_vars": ["raa_number", "lamningsnummer"],
                    "var_name": "property_type",
                    "value_name": "property_value",
                },
            }
        }
        table_cfg = TableConfig(entities_cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        # Verify unnest succeeded
        assert "property_type" in result.columns
        assert "property_value" in result.columns
        assert len(result) == 4  # 2 sites * 2 value_vars
        assert set(result["property_type"].unique()) == {"raa_number", "lamningsnummer"}
