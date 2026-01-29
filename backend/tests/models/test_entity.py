"""Tests for entity models."""

import pytest
from pydantic import ValidationError

from backend.app.models.entity import (
    Entity,
    ForeignKeyConfig,
    ForeignKeyConstraints,
    UnnestConfig,
)


class TestForeignKeyConstraints:
    """Tests for ForeignKeyConstraints model."""

    def test_default_values(self):
        """Test default constraint values."""
        constraints = ForeignKeyConstraints()
        assert constraints.allow_null_keys is True
        assert constraints.require_unique_left is False
        assert constraints.require_unique_right is False

    def test_has_constraints(self):
        """Test has_constraints property."""
        empty_constraints = ForeignKeyConstraints()
        assert empty_constraints.has_constraints is False

        with_cardinality = ForeignKeyConstraints(cardinality="one_to_one")
        assert with_cardinality.has_constraints is True

    def test_has_match_constraints(self):
        """Test has_match_constraints property."""
        no_match = ForeignKeyConstraints()
        assert no_match.has_match_constraints is False

        with_match = ForeignKeyConstraints(allow_unmatched_left=False)
        assert with_match.has_match_constraints is True


class TestForeignKeyConfig:
    """Tests for ForeignKeyConfig model."""

    def test_valid_config(self):
        """Test valid foreign key configuration."""
        fk = ForeignKeyConfig(
            entity="remote_table",
            local_keys=["id"],
            remote_keys=["remote_id"],
            how="inner",
        )
        assert fk.entity == "remote_table"
        assert fk.local_keys == ["id"]
        assert fk.how == "inner"

    def test_keys_as_string(self):
        """Test that string keys are converted to lists."""
        fk = ForeignKeyConfig(entity="remote", local_keys="id", remote_keys="remote_id")  # type: ignore
        assert fk.local_keys == ["id"]
        assert fk.remote_keys == ["remote_id"]

    def test_default_how(self):
        """Test default join type is inner."""
        fk = ForeignKeyConfig(entity="remote", local_keys=["id"], remote_keys=["remote_id"])
        assert fk.how == "inner"


class TestUnnestConfig:
    """Tests for UnnestConfig model."""

    def test_valid_config(self):
        """Test valid unnest configuration."""
        unnest = UnnestConfig(
            id_vars=["sample_id"],
            value_vars=["col1", "col2"],
            var_name="variable",
            value_name="value",
        )
        assert unnest.id_vars == ["sample_id"]
        assert unnest.value_vars == ["col1", "col2"]


class TestEntity:
    """Tests for Entity model."""

    def test_valid_entity(self):
        """Test valid entity creation with new identity model."""
        entity = Entity(
            name="sample",
            type="entity",
            public_id="sample_id",
            keys=["natural_key"],
            columns=["col1", "col2"],
        )
        assert entity.name == "sample"
        assert entity.type == "entity"
        assert entity.system_id == "system_id"  # Always standardized
        assert entity.public_id == "sample_id"

    def test_name_validation(self):
        """Test entity name must be snake_case."""
        with pytest.raises(ValidationError):
            Entity(name="CamelCase")

        with pytest.raises(ValidationError):
            Entity(name="has space")

    def test_public_id_validation(self):
        """Test public_id must end with _id."""
        with pytest.raises(ValidationError):
            Entity(name="sample", public_id="sample_key")

        # Valid
        entity = Entity(name="sample", public_id="sample_id")
        assert entity.public_id == "sample_id"

    def test_surrogate_id_migration(self):
        """Test backward compatibility: surrogate_id migrates to public_id."""
        entity = Entity(name="sample", surrogate_id="sample_id")
        assert entity.public_id == "sample_id"  # Automatically migrated
        assert entity.surrogate_id == "sample_id"  # Still accessible for compat

    def test_default_values(self):
        """Test default values for optional fields."""
        entity = Entity(name="simple")
        assert entity.keys == []
        assert entity.columns == []
        assert entity.foreign_keys == []
        assert entity.check_column_names is True

    def test_with_foreign_keys(self):
        """Test entity with foreign keys."""
        entity = Entity(
            name="sample",
            foreign_keys=[
                ForeignKeyConfig(
                    entity="site",
                    local_keys=["site_id"],
                    remote_keys=["site_id"],
                )
            ],
        )
        assert len(entity.foreign_keys) == 1
        assert entity.foreign_keys[0].entity == "site"

    def test_with_unnest(self):
        """Test entity with unnest configuration."""
        entity: Entity = Entity(
            name="sample",
            unnest=UnnestConfig(
                id_vars=["id"],
                value_vars=["val1", "val2"],
                var_name="variable",
                value_name="value",
            ),
        )
        assert entity.unnest is not None
        assert entity.unnest.var_name == "variable"  # pylint: disable=no-member
