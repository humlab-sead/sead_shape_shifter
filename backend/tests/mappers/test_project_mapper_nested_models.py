"""Test that ProjectMapper handles all nested Pydantic models automatically.

This test ensures that the mapper is not brittle - adding new nested Pydantic
models to the Entity class should not require manual handling in the mapper.
"""

import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.entity import (
    AppendConfig,
    Entity,
    FilterConfig,
    ForeignKeyConfig,
    ForeignKeyConstraints,
    UnnestConfig,
)


class TestProjectMapperNestedModels:
    """Test that all nested Pydantic models are properly serialized."""

    def test_all_nested_models_become_dicts(self):
        """Verify that ALL nested Pydantic models are converted to plain dicts.
        
        This is critical for YAML serialization and ensures the mapper is not brittle.
        If someone adds a new nested Pydantic model field to Entity, this test
        will verify it's automatically handled without explicit code changes.
        """
        # Create an entity with ALL types of nested Pydantic models
        entity = Entity(
            name="test_entity",
            type="entity",
            source="source_table",
            # Nested Pydantic models
            foreign_keys=[
                ForeignKeyConfig(
                    entity="parent",
                    local_keys=["fk_id"],
                    remote_keys=["id"],
                    constraints=ForeignKeyConstraints(
                        cardinality="many_to_one",
                        allow_unmatched_left=False,
                    ),
                )
            ],
            unnest=UnnestConfig(
                id_vars=["id"],
                value_vars=["col1", "col2"],
                var_name="variable",
                value_name="value",
            ),
            filters=[
                FilterConfig(
                    type="exists_in",
                    entity="other",
                    column="key",
                    remote_column="key",
                )
            ],
            append=[
                AppendConfig(
                    type="fixed",
                    values=[[1, "a"], [2, "b"]],
                )
            ],
        )

        # Convert to dict
        entity_dict = ProjectMapper._api_entity_to_dict(entity)

        # CRITICAL: All nested structures must be plain dicts/lists, not Pydantic models
        # This ensures YAML serialization works and the code is not brittle
        
        # Check foreign_keys
        assert "foreign_keys" in entity_dict
        assert isinstance(entity_dict["foreign_keys"], list)
        assert len(entity_dict["foreign_keys"]) == 1
        fk = entity_dict["foreign_keys"][0]
        assert isinstance(fk, dict), f"ForeignKeyConfig should be dict, got {type(fk)}"
        assert fk["entity"] == "parent"
        
        # Check nested constraints
        assert "constraints" in fk
        constraints = fk["constraints"]
        assert isinstance(constraints, dict), f"ForeignKeyConstraints should be dict, got {type(constraints)}"
        assert constraints["cardinality"] == "many_to_one"
        assert constraints["allow_unmatched_left"] is False

        # Check unnest
        assert "unnest" in entity_dict
        unnest = entity_dict["unnest"]
        assert isinstance(unnest, dict), f"UnnestConfig should be dict, got {type(unnest)}"
        assert unnest["id_vars"] == ["id"]
        assert unnest["var_name"] == "variable"

        # Check filters
        assert "filters" in entity_dict
        assert isinstance(entity_dict["filters"], list)
        assert len(entity_dict["filters"]) == 1
        filter_cfg = entity_dict["filters"][0]
        assert isinstance(filter_cfg, dict), f"FilterConfig should be dict, got {type(filter_cfg)}"
        assert filter_cfg["type"] == "exists_in"

        # Check append
        assert "append" in entity_dict
        assert isinstance(entity_dict["append"], list)
        assert len(entity_dict["append"]) == 1
        append_cfg = entity_dict["append"][0]
        assert isinstance(append_cfg, dict), f"AppendConfig should be dict, got {type(append_cfg)}"
        assert append_cfg["type"] == "fixed"

    def test_dict_passthrough_preserves_all_fields(self):
        """When entity is already a dict (materialization case), all fields are preserved."""
        # Simulate a materialized entity with unknown fields
        entity_dict = {
            "name": "materialized_entity",
            "type": "fixed",
            "columns": ["a", "b"],
            "values": [[1, 2], [3, 4]],
            # Unknown field that might be added in the future
            "materialized": {
                "enabled": True,
                "source_state": {
                    "type": "openpyxl",
                    "options": {"filename": "data.xlsx"},
                },
                "materialized_at": "2026-02-14T10:00:00Z",
            },
            # Another unknown field
            "experimental_feature": {"setting": "value"},
        }

        result = ProjectMapper._api_entity_to_dict(entity_dict)

        # ALL fields must be preserved, including unknown ones
        assert result["type"] == "fixed"
        assert result["columns"] == ["a", "b"]
        assert result["values"] == [[1, 2], [3, 4]]
        assert "materialized" in result
        assert result["materialized"]["enabled"] is True
        assert "source_state" in result["materialized"]
        assert "experimental_feature" in result
        assert "name" not in result  # API-only field should be removed

    def test_sparse_yaml_defaults_removed(self):
        """Default values should not bloat YAML output."""
        entity = Entity(
            name="minimal_entity",
            type="entity",
            source="table",
            # These have defaults that should not appear in output
            check_column_names=True,  # Default, should be removed
            drop_duplicates=False,  # Default, should be removed
            drop_empty_rows=False,  # Default, should be removed
        )

        entity_dict = ProjectMapper._api_entity_to_dict(entity)

        # Default values should not appear (sparse YAML)
        assert "check_column_names" not in entity_dict
        assert "drop_duplicates" not in entity_dict
        assert "drop_empty_rows" not in entity_dict

    def test_non_default_values_included(self):
        """Non-default values should be included in output."""
        entity = Entity(
            name="custom_entity",
            type="entity",
            source="table",
            check_column_names=False,  # Non-default, should be included
            drop_duplicates=True,  # Non-default, should be included
            drop_empty_rows=["col1", "col2"],  # Non-default, should be included
        )

        entity_dict = ProjectMapper._api_entity_to_dict(entity)

        assert entity_dict["check_column_names"] is False
        assert entity_dict["drop_duplicates"] is True
        assert entity_dict["drop_empty_rows"] == ["col1", "col2"]
