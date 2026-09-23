"""ProjectMapper integration tests that load the real arbodat project files.

These tests need the arbodat data source configuration to be available: the
project file includes `${GLOBAL_DATA_SOURCE_DIR}/*.yml` options and reads from
the arbodat Access database.
"""

from pathlib import Path
from typing import Any

import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from src.model import ShapeShiftProject

# pylint: disable=no-member

# backend/tests/test_data is a symlink to the repository level tests/test_data.
BACKEND_TESTS_DIR = Path(__file__).resolve().parents[2]
PROJECT_PATH = Path("data/projects/arbodat/shapeshifter.yml")


class TestProjectMapperIntegration:
    """Integration tests using real project files."""

    def test_arbodat_project_round_trip(self):
        """Test round-trip conversion with real arbodat-database.yml project.

        This test verifies that:
        1. A real ShapeShiftProject can be loaded from file
        2. It can be converted to API Project format
        3. The API Project can be converted back to core dict format
        4. The result matches the original project
        """
        # Load real project file
        project_path = PROJECT_PATH
        assert project_path.exists(), f"Test project file not found: {project_path}"

        # Load as ShapeShiftProject (core model)
        original_shape_config = ShapeShiftProject.from_file(str(project_path), env_file="data/test.env")
        original_cfg_dict = original_shape_config.cfg

        # Get config name from file
        project_name = project_path.stem

        # Convert to API Project
        api_project: Project = ProjectMapper.to_api_config(original_cfg_dict, project_name)

        # Verify API config has expected structure
        assert isinstance(api_project, Project)
        assert api_project.metadata is not None
        # Name comes from metadata section in YAML, not filename
        assert api_project.metadata.entity_count == len(original_cfg_dict.get("entities", {}))

        # Convert back to core dict
        restored_cfg_dict = ProjectMapper.to_core_dict(api_project)

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

    def test_arbodat_project_entity_details(self):
        """Test detailed entity conversion for complex arbodat entities."""
        project_path: Path = PROJECT_PATH

        assert project_path.exists(), f"Test project file not found: {project_path}"

        original_shape_config: ShapeShiftProject = ShapeShiftProject.from_file(str(project_path), env_file="data/test.env")
        original_cfg_dict: dict[str, dict[str, Any]] = original_shape_config.cfg

        # Convert to API and back
        api_project: Project = ProjectMapper.to_api_config(original_cfg_dict, "arbodat")
        restored_cfg_dict: dict[str, Any] = ProjectMapper.to_core_dict(api_project)

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

    def test_arbodat_project_metadata_preservation(self):
        """Test that metadata fields are correctly set during conversion."""
        project_path: Path = PROJECT_PATH
        original_shape_config: ShapeShiftProject = ShapeShiftProject.from_file(str(project_path), env_file="data/test.env")
        original_cfg_dict = original_shape_config.cfg

        project_name = "arbodat"
        api_project: Project = ProjectMapper.to_api_config(original_cfg_dict, project_name)

        original_metadata = original_cfg_dict["metadata"] if "metadata" in original_cfg_dict else {}

        # Check metadata
        assert api_project.metadata is not None
        # Check that metadata from YAML is preserved
        # Change: name comes from filename parameter
        assert api_project.metadata.name == project_name
        assert api_project.metadata.description == original_metadata.get("description")
        assert api_project.metadata.version == original_metadata.get("version")

        assert api_project.metadata.entity_count == len(original_cfg_dict.get("entities", {}))
        assert api_project.metadata.is_valid is True

        # Convert back and check metadata fields are in core dict
        restored_cfg_dict = ProjectMapper.to_core_dict(api_project)

        assert "metadata" in restored_cfg_dict

        assert restored_cfg_dict["metadata"]["name"] == project_name  # original_metadata.get("name")
        assert restored_cfg_dict["metadata"]["description"] == original_metadata.get("description")
        assert restored_cfg_dict["metadata"]["version"] == original_metadata.get("version")
