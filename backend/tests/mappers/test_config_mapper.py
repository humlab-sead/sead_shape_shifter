"""Tests for ProjectMapper."""

from pathlib import Path

import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.entity import AppendConfig, Entity, FilterConfig, ForeignKeyConfig, ForeignKeyConstraints, UnnestConfig
from backend.app.models.project import Project, ProjectMetadata
from src.model import ShapeShiftProject

# pylint: disable=no-member


def create_valid_config_dict(entities: dict, options: dict | None = None, metadata: dict | None = None) -> dict:
    """Helper to create a valid config dict with all required sections."""
    return {
        "metadata": metadata
        or {
            "name": "Test Project",
            "description": "Test configuration description",
            "version": "1.0.0",
        },
        "entities": entities,
        "options": options or {},
    }


class TestProjectMapperToApiConfig:
    """Tests for to_api_config method."""

    def test_minimal_config(self):
        """Test converting minimal core config to API config."""
        core_dict = {
            "entities": {
                "sample": {
                    "type": "data",
                    "keys": ["id"],
                    "columns": ["name", "value"],
                }
            }
        }

        result: Project = ProjectMapper.to_api_config(core_dict, "test_project")

        assert isinstance(result, Project)
        assert result.metadata is not None
        assert result.metadata.name == "test_project"
        assert result.metadata.entity_count == 1
        assert "sample" in result.entities
        assert result.entities["sample"]["type"] == "data"
        assert result.entities["sample"]["keys"] == ["id"]
        assert result.entities["sample"]["columns"] == ["name", "value"]

    def test_project_with_options(self):
        """Test converting config with options."""
        core_dict = {
            "entities": {
                "sample": {"type": "data", "keys": ["id"]},
            },
            "options": {"some_option": "value", "another_option": 123},
        }

        result = ProjectMapper.to_api_config(core_dict, "test_project")

        assert result.options == {"some_option": "value", "another_option": 123}

    def test_empty_entities(self):
        """Test converting config with no entities."""
        core_dict = {"entities": {}}

        result: Project = ProjectMapper.to_api_config(core_dict, "test_project")

        assert isinstance(result, Project)
        assert result.metadata is not None

        assert result.metadata.entity_count == 0
        assert result.entities == {}

    def test_entity_with_all_primitive_fields(self):
        """Test entity with all primitive fields."""
        core_dict = {
            "entities": {
                "sample": {
                    "type": "data",
                    "source": "raw_sample",
                    "data_source": "postgres",
                    "query": "SELECT * FROM samples",
                    "surrogate_id": "sample_id",
                    "keys": ["natural_key"],
                    "columns": ["col1", "col2"],
                    "extra_columns": {"computed": "expression"},
                    "values": [["val1", "val2"]],
                    "depends_on": ["entity1"],
                    "drop_duplicates": True,
                    "drop_empty_rows": ["col1"],
                    "check_column_names": False,
                }
            }
        }

        result = ProjectMapper.to_api_config(core_dict, "test_project")
        entity = result.entities["sample"]

        assert entity["type"] == "data"
        assert entity["source"] == "raw_sample"
        assert entity["data_source"] == "postgres"
        assert entity["query"] == "SELECT * FROM samples"
        assert entity["surrogate_id"] == "sample_id"
        assert entity["keys"] == ["natural_key"]
        assert entity["columns"] == ["col1", "col2"]
        assert entity["extra_columns"] == {"computed": "expression"}
        assert entity["values"] == [["val1", "val2"]]
        assert entity["depends_on"] == ["entity1"]
        assert entity["drop_duplicates"] is True
        assert entity["drop_empty_rows"] == ["col1"]
        assert entity["check_column_names"] is False

    def test_entity_with_foreign_keys(self):
        """Test entity with foreign keys."""
        core_dict = {
            "entities": {
                "sample": {
                    "type": "data",
                    "keys": ["id"],
                    "foreign_keys": {
                        "site_fk": {"entity": "sites", "key": "site_id"},
                        "method_fk": {"entity": "methods", "key": "method_id"},
                    },
                }
            }
        }

        result = ProjectMapper.to_api_config(core_dict, "test_project")
        entity = result.entities["sample"]

        assert "foreign_keys" in entity
        assert len(entity["foreign_keys"]) == 2
        # Foreign keys should be plain dicts (not ForeignKeyConfig objects)
        assert all(isinstance(fk, dict) for fk in entity["foreign_keys"])
        assert entity["foreign_keys"][0]["entity"] in ["sites", "methods"]
        assert entity["foreign_keys"][1]["entity"] in ["sites", "methods"]


class TestProjectMapperToCoreDict:
    """Tests for to_core_dict method."""

    def test_minimal_config(self):
        """Test converting minimal API config to core dict."""
        api_config = Project(
            metadata=ProjectMetadata(
                name="test_project",
                file_path="/path/to/file.yml",
                entity_count=1,
                created_at=1234567890,
                modified_at=1234567890,
                is_valid=True,
            ),
            entities={
                "sample": {
                    "type": "data",
                    "keys": ["id"],
                    "columns": ["name", "value"],
                }
            },
            options={},
        )

        result = ProjectMapper.to_core_dict(api_config)

        assert "metadata" in result
        assert result["metadata"]["name"] == "test_project"
        assert "sample" in result["entities"]
        assert result["entities"]["sample"]["type"] == "data"

    def test_project_with_options(self):
        """Test converting config with options."""
        api_config = Project(
            metadata=ProjectMetadata(name="test", entity_count=0),
            entities={},
            options={"option1": "value1", "option2": 42},
        )

        result = ProjectMapper.to_core_dict(api_config)

        assert result["options"] == {"option1": "value1", "option2": 42}

    def test_project_without_options(self):
        """Test config without options doesn't include options key."""
        api_config = Project(
            metadata=ProjectMetadata(name="test", entity_count=0),
            entities={},
            options={},
        )

        result = ProjectMapper.to_core_dict(api_config)

        # Empty options should not be included
        assert "options" not in result or result["options"] == {}

    def test_entities_as_dicts(self):
        """Test that dict entities are passed through correctly."""
        api_config = Project(
            metadata=ProjectMetadata(name="test", entity_count=1),
            entities={
                "sample": {
                    "type": "data",
                    "keys": ["id"],
                    "columns": ["name"],
                    "surrogate_id": "sample_id",
                }
            },
            options={},
        )

        result = ProjectMapper.to_core_dict(api_config)

        assert result["entities"]["sample"]["type"] == "data"
        assert result["entities"]["sample"]["keys"] == ["id"]
        assert result["entities"]["sample"]["columns"] == ["name"]
        assert result["entities"]["sample"]["surrogate_id"] == "sample_id"


class TestDictToApiEntity:
    """Tests for _dict_to_api_entity method."""

    def test_minimal_entity(self):
        """Test minimal entity conversion."""
        entity_dict = {
            "type": "data",
            "keys": ["id"],
        }

        result = ProjectMapper._dict_to_api_entity("sample", entity_dict)

        assert result["name"] == "sample"
        assert result["type"] == "data"
        assert result["keys"] == ["id"]

    def test_default_type(self):
        """Test type is only included if explicitly set."""
        entity_dict = {"keys": ["id"]}

        result = ProjectMapper._dict_to_api_entity("sample", entity_dict)

        # Type should not be added if not in original
        assert "type" not in result
        assert result["name"] == "sample"

    def test_none_fields_excluded(self):
        """Test that None values are preserved (not excluded)."""
        entity_dict = {
            "type": "data",
            "keys": ["id"],
            "source": None,
            "columns": ["name"],
        }

        result = ProjectMapper._dict_to_api_entity("sample", entity_dict)

        # None values should now be preserved for fields like source
        assert "source" in result
        assert result["source"] is None
        assert "columns" in result

    def test_foreign_keys_converted_to_list(self):
        """Test foreign keys dict is converted to list of plain dicts."""
        entity_dict = {
            "type": "data",
            "keys": ["id"],
            "foreign_keys": {
                "site_fk": {"entity": "sites", "key": "site_id"},
            },
        }

        result = ProjectMapper._dict_to_api_entity("sample", entity_dict)

        assert "foreign_keys" in result
        assert len(result["foreign_keys"]) == 1
        # Foreign keys are now plain dicts (not ForeignKeyConfig objects)
        assert isinstance(result["foreign_keys"][0], dict)
        assert result["foreign_keys"][0]["entity"] == "sites"

    def test_foreign_keys_with_key_field(self):
        """Test foreign key dict uses key field for local and remote keys."""
        entity_dict = {
            "type": "data",
            "keys": ["id"],
            "foreign_keys": {"sample_fk": {"entity": "targets", "key": ["target_id"]}},
        }

        result = ProjectMapper._dict_to_api_entity("sample", entity_dict)

        assert "foreign_keys" in result
        foreign_key = result["foreign_keys"][0]
        assert foreign_key["entity"] == "targets"
        assert foreign_key["local_keys"] == ["target_id"]
        assert foreign_key["remote_keys"] == ["target_id"]

    def test_all_fields_preserved(self):
        """Test all supported fields are preserved."""
        entity_dict = {
            "type": "sql",
            "source": "raw_data",
            "data_source": "postgres",
            "query": "SELECT * FROM table",
            "surrogate_id": "id",
            "keys": ["natural_key"],
            "columns": ["col1", "col2"],
            "extra_columns": {"computed": "expr"},
            "values": [["a", "b"]],
            "depends_on": ["entity1"],
            "drop_duplicates": True,
            "drop_empty_rows": False,
            "check_column_names": True,
        }

        result = ProjectMapper._dict_to_api_entity("test", entity_dict)

        for key in entity_dict:
            assert key in result or key == "type"  # type is always included
        assert result["type"] == "sql"


class TestApiEntityToDict:
    """Tests for _api_entity_to_dict method."""

    def test_dict_passthrough(self):
        """Test that dict input is copied (to remove 'name' field)."""
        entity_dict = {
            "type": "data",
            "keys": ["id"],
            "columns": ["name"],
        }

        result = ProjectMapper._api_entity_to_dict(entity_dict)

        # Should be a copy (not same object) since we remove 'name'
        assert result is not entity_dict
        assert result == entity_dict  # But values should match

    def test_minimal_entity_dict_output(self):
        """Test minimal entity produces minimal dict."""
        entity_dict = {
            "type": "data",
            "keys": ["id"],
        }

        result = ProjectMapper._api_entity_to_dict(entity_dict)

        assert result["type"] == "data"
        assert result["keys"] == ["id"]

    def test_pydantic_entity_conversion_strips_defaults(self):
        """Test conversion strips API-only name and default flags while dumping nested models."""
        entity = Entity(
            name="sample_entity",
            type="data",
            keys=["id"],
            columns=["name"],
            foreign_keys=[
                ForeignKeyConfig(
                    entity="sites",
                    local_keys=["site_id"],
                    remote_keys=["site_id"],
                    constraints=ForeignKeyConstraints(require_unique_left=True),
                )
            ],
            filters=[FilterConfig(type="exists_in", entity="sites", column="site_id", remote_column="site_id")],
            unnest=UnnestConfig(id_vars=["id"], value_vars=["name"], var_name="field", value_name="value"),
            append=[AppendConfig(type="fixed", values=[["value"]])],
            drop_duplicates=False,
            drop_empty_rows=False,
            check_column_names=True,
        )

        result = ProjectMapper._api_entity_to_dict(entity)

        assert "name" not in result
        assert isinstance(result["foreign_keys"][0], dict)
        assert result["foreign_keys"][0]["constraints"]["require_unique_left"] is True
        assert isinstance(result["filters"][0], dict)
        assert isinstance(result["unnest"], dict)
        assert isinstance(result["append"][0], dict)
        assert "drop_duplicates" not in result
        assert "drop_empty_rows" not in result
        assert "check_column_names" not in result

    def test_flags_preserved_when_truthy(self):
        """Test conversion keeps explicit True/False flags for drop and column checks."""
        entity = Entity(
            name="another_entity",
            type="data",
            keys=["id"],
            drop_duplicates=True,
            drop_empty_rows=["col1"],
            check_column_names=False,
        )

        result = ProjectMapper._api_entity_to_dict(entity)

        assert result["drop_duplicates"] is True
        assert result["drop_empty_rows"] == ["col1"]
        assert result["check_column_names"] is False


class TestRoundTripConversion:
    """Tests for round-trip conversion (API -> Core -> API)."""

    def test_simple_config_round_trip(self):
        """Test simple config survives round-trip."""
        original_config = Project(
            metadata=ProjectMetadata(name="test", entity_count=1),
            entities={
                "sample": {
                    "type": "data",
                    "keys": ["id"],
                    "columns": ["name", "value"],
                }
            },
            options={"option1": "value1"},
        )
        assert original_config.metadata is not None

        # API -> Core
        core_dict = ProjectMapper.to_core_dict(original_config)

        # Core -> API
        restored_config = ProjectMapper.to_api_config(core_dict, "test")
        assert isinstance(restored_config, Project)
        assert restored_config.metadata is not None

        assert restored_config.metadata.name == original_config.metadata.name
        assert len(restored_config.entities) == len(original_config.entities)
        assert restored_config.entities["sample"]["type"] == original_config.entities["sample"]["type"]
        assert restored_config.entities["sample"]["keys"] == original_config.entities["sample"]["keys"]
        assert restored_config.options == original_config.options


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_missing_metadata_raises_assertion(self):
        """Test that missing metadata raises AssertionError."""
        api_config = Project(
            metadata=None,
            entities={},
            options={},
        )

        with pytest.raises(AssertionError):
            ProjectMapper.to_core_dict(api_config)

    def test_empty_config(self):
        """Test empty configuration."""
        core_dict = {"entities": {}}

        result = ProjectMapper.to_api_config(core_dict, "empty")
        assert isinstance(result, Project)
        assert result.metadata is not None

        assert result.metadata.entity_count == 0
        assert result.entities == {}

    def test_entity_with_empty_lists(self):
        """Test entity with empty lists."""
        entity_dict = {
            "type": "data",
            "keys": [],
            "columns": [],
            "depends_on": [],
        }

        result = ProjectMapper._dict_to_api_entity("test", entity_dict)

        # Empty lists should still be included
        assert result["keys"] == []
        assert result["columns"] == []
        assert result["depends_on"] == []

    def test_entity_with_empty_dict(self):
        """Test entity with empty dict for extra_columns."""
        entity_dict = {
            "type": "data",
            "keys": ["id"],
            "extra_columns": {},
        }

        result = ProjectMapper._dict_to_api_entity("test", entity_dict)

        assert result["extra_columns"] == {}

    def test_fixed_type_entity_with_values(self):
        """Test that fixed type entity with values is handled correctly."""
        entity_dict = {
            "type": "fixed",
            "keys": ["id"],
            "columns": ["name", "value"],
            "values": [
                ["row1", "value1"],
                ["row2", "value2"],
                ["row3", "value3"],
            ],
        }

        result = ProjectMapper._dict_to_api_entity("fixed_entity", entity_dict)

        assert result["type"] == "fixed"
        assert result["values"] == [["row1", "value1"], ["row2", "value2"], ["row3", "value3"]]
        assert len(result["values"]) == 3

    def test_fixed_entity_round_trip_with_values(self):
        """Test round-trip conversion preserves values for fixed entities."""
        original_config = Project(
            metadata=ProjectMetadata(name="test", entity_count=1),
            entities={
                "contact_type": {
                    "type": "fixed",
                    "keys": ["contact_type_id"],
                    "columns": ["contact_type_name", "description"],
                    "values": [
                        ["Archaeologist", "Responsible for archaeological material"],
                        ["Botanist", "Responsible for botanical analysis"],
                    ],
                }
            },
            options={},
        )

        # API -> Core
        core_dict = ProjectMapper.to_core_dict(original_config)
        assert "values" in core_dict["entities"]["contact_type"]
        assert core_dict["entities"]["contact_type"]["values"] == [
            ["Archaeologist", "Responsible for archaeological material"],
            ["Botanist", "Responsible for botanical analysis"],
        ]

        # Core -> API
        restored_config = ProjectMapper.to_api_config(core_dict, "test")
        assert restored_config.entities["contact_type"]["values"] == original_config.entities["contact_type"]["values"]


class TestProjectMapperIntegration:
    """Integration tests using real configuration files."""

    def test_arbodat_config_round_trip(self):
        """Test round-trip conversion with real arbodat-database.yml configuration.

        This test verifies that:
        1. A real ShapeShiftProject can be loaded from file
        2. It can be converted to API Project format
        3. The API Project can be converted back to core dict format
        4. The result matches the original configuration
        """
        # Load real configuration file
        config_path = Path(__file__).parent.parent / "test_data" / "configurations" / "arbodat-database.yml"
        assert config_path.exists(), f"Test config file not found: {config_path}"

        # Load as ShapeShiftProject (core model)
        original_shape_config = ShapeShiftProject.from_file(str(config_path))
        original_cfg_dict = original_shape_config.cfg

        # Get config name from file
        project_name = config_path.stem

        # Convert to API Project
        api_config = ProjectMapper.to_api_config(original_cfg_dict, project_name)

        # Verify API config has expected structure
        assert isinstance(api_config, Project)
        assert api_config.metadata is not None
        # Name comes from metadata section in YAML, not filename
        assert api_config.metadata.entity_count == len(original_cfg_dict.get("entities", {}))

        # Convert back to core dict
        restored_cfg_dict = ProjectMapper.to_core_dict(api_config)

        # Compare entity count
        original_entities = original_cfg_dict.get("entities", {})
        restored_entities = restored_cfg_dict.get("entities", {})
        assert len(restored_entities) == len(
            original_entities
        ), f"Entity count mismatch: {len(restored_entities)} vs {len(original_entities)}"

        # Compare entity names
        assert set(restored_entities.keys()) == set(
            original_entities.keys()
        ), f"Entity names mismatch: {set(restored_entities.keys())} vs {set(original_entities.keys())}"

        # Deep recursive comparison of all entities
        def find_differences(obj1, obj2, path=""):
            """Recursively find differences between two objects."""
            differences = []

            if type(obj1) is not type(obj2):
                differences.append(f"{path}: type mismatch ({type(obj1).__name__} vs {type(obj2).__name__})")
                return differences

            if isinstance(obj1, dict):
                # Check for missing/extra keys
                keys1, keys2 = set(obj1.keys()), set(obj2.keys())
                for key in keys1 - keys2:
                    differences.append(f"{path}.{key}: missing in restored (value: {obj1[key]})")
                for key in keys2 - keys1:
                    differences.append(f"{path}.{key}: extra in restored (value: {obj2[key]})")

                # Recursively compare common keys
                for key in keys1 & keys2:
                    new_path = f"{path}.{key}" if path else key
                    differences.extend(find_differences(obj1[key], obj2[key], new_path))

            elif isinstance(obj1, (list, tuple)):
                if len(obj1) != len(obj2):
                    differences.append(f"{path}: length mismatch ({len(obj1)} vs {len(obj2)})")
                else:
                    for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                        differences.extend(find_differences(item1, item2, f"{path}[{i}]"))

            elif obj1 != obj2:
                differences.append(f"{path}: {obj1!r} != {obj2!r}")

            return differences

        # Compare each entity
        for entity_name in original_entities:
            original_entity = original_entities[entity_name]
            restored_entity = restored_entities[entity_name]

            diffs = find_differences(original_entity, restored_entity, f"entities.{entity_name}")

            if diffs:
                diff_report = "\n".join(diffs)
                pytest.fail(f"Entity '{entity_name}' differs after round-trip:\n{diff_report}")

        # Compare options if present
        if "options" in original_cfg_dict:
            assert "options" in restored_cfg_dict, "Options missing in restored config"
            # Deep compare options
            diffs = find_differences(original_cfg_dict["options"], restored_cfg_dict["options"], "options")
            if diffs:
                diff_report = "\n".join(diffs)
                pytest.fail(f"Options differ after round-trip:\n{diff_report}")

    def test_arbodat_config_entity_details(self):
        """Test detailed entity conversion for complex arbodat entities."""
        config_path = Path(__file__).parent.parent / "test_data" / "configurations" / "arbodat-database.yml"
        original_shape_config = ShapeShiftProject.from_file(str(config_path))
        original_cfg_dict = original_shape_config.cfg

        # Convert to API and back
        api_config = ProjectMapper.to_api_config(original_cfg_dict, "arbodat-database")
        restored_cfg_dict = ProjectMapper.to_core_dict(api_config)

        # Test specific complex entities

        # 1. Test 'abundance' - has foreign keys, depends_on, extra_columns
        if "abundance" in original_cfg_dict["entities"]:
            original_abundance = original_cfg_dict["entities"]["abundance"]
            restored_abundance = restored_cfg_dict["entities"]["abundance"]

            # Check extra_columns are preserved
            if "extra_columns" in original_abundance:
                assert "extra_columns" in restored_abundance
                assert restored_abundance["extra_columns"] == original_abundance["extra_columns"]

            # Check depends_on is preserved
            if "depends_on" in original_abundance:
                assert "depends_on" in restored_abundance
                assert set(restored_abundance["depends_on"]) == set(original_abundance["depends_on"])

        # 2. Test 'abundance_property' - has unnest configuration
        if "abundance_property" in original_cfg_dict["entities"]:
            original_prop = original_cfg_dict["entities"]["abundance_property"]
            restored_prop = restored_cfg_dict["entities"]["abundance_property"]

            # Check unnest is preserved
            if "unnest" in original_prop:
                assert "unnest" in restored_prop
                assert restored_prop["unnest"]["id_vars"] == original_prop["unnest"]["id_vars"]
                assert restored_prop["unnest"]["value_name"] == original_prop["unnest"]["value_name"]

            # Check drop_empty_rows is preserved
            if "drop_empty_rows" in original_prop:
                assert "drop_empty_rows" in restored_prop

        # 3. Test 'method' - fixed type with values
        if "method" in original_cfg_dict["entities"]:
            original_method = original_cfg_dict["entities"]["method"]
            restored_method = restored_cfg_dict["entities"]["method"]

            if original_method.get("type") == "fixed":
                assert restored_method["type"] == "fixed"
                if "values" in original_method:
                    assert "values" in restored_method
                    assert len(restored_method["values"]) == len(original_method["values"])

        # 4. Test 'sample_coordinate' - has drop_duplicates and drop_empty_rows
        if "sample_coordinate" in original_cfg_dict["entities"]:
            original_coord = original_cfg_dict["entities"]["sample_coordinate"]
            restored_coord = restored_cfg_dict["entities"]["sample_coordinate"]

            for field in ["drop_duplicates", "drop_empty_rows"]:
                if field in original_coord:
                    assert field in restored_coord
                    assert restored_coord[field] == original_coord[field]

    def test_arbodat_config_metadata_preservation(self):
        """Test that metadata fields are correctly set during conversion."""
        config_path: Path = Path(__file__).parent.parent / "test_data" / "configurations" / "arbodat-database.yml"
        original_shape_config: ShapeShiftProject = ShapeShiftProject.from_file(str(config_path))
        original_cfg_dict = original_shape_config.cfg

        project_name = "arbodat-database"
        api_config: Project = ProjectMapper.to_api_config(original_cfg_dict, project_name)

        original_metadata = original_cfg_dict["metadata"] if "metadata" in original_cfg_dict else {}

        # Check metadata
        assert api_config.metadata is not None
        # Check that metadata from YAML is preserved
        # Change: name comes from filename parameter
        assert api_config.metadata.name == project_name
        assert api_config.metadata.description == original_metadata.get("description")
        assert api_config.metadata.version == original_metadata.get("version")

        assert api_config.metadata.entity_count == len(original_cfg_dict.get("entities", {}))
        assert api_config.metadata.is_valid is True

        # Convert back and check metadata fields are in core dict
        restored_cfg_dict = ProjectMapper.to_core_dict(api_config)

        assert "metadata" in restored_cfg_dict

        assert restored_cfg_dict["metadata"]["name"] == project_name  # original_metadata.get("name")
        assert restored_cfg_dict["metadata"]["description"] == original_metadata.get("description")
        assert restored_cfg_dict["metadata"]["version"] == original_metadata.get("version")
