"""Tests for YAML service."""

import time

import pytest

from backend.app.services.yaml_service import (
    YamlLoadError,
    YamlService,
    YamlServiceError,
)

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def yaml_service():
    """Create YamlService instance."""
    return YamlService()


@pytest.fixture
def temp_yaml_file(tmp_path):
    """Create a temporary YAML file."""
    file_path = tmp_path / "test.yml"
    content = """
# Test configuration
entities:
  sample:
    type: entity
    keys: [id]
    columns: [name, value]

  # Another entity
  site:
    type: entity
    keys: [site_id]
"""
    file_path.write_text(content)
    return file_path


class TestYamlServiceLoad:
    """Tests for YAML loading."""

    def test_load_valid_file(self, yaml_service, temp_yaml_file):
        """Test loading valid YAML file."""
        data = yaml_service.load(temp_yaml_file)
        assert "entities" in data
        assert "sample" in data["entities"]
        assert data["entities"]["sample"]["type"] == "entity"

    def test_load_nonexistent_file(self, yaml_service, tmp_path):
        """Test loading non-existent file raises error."""
        with pytest.raises(YamlLoadError, match="File not found"):
            yaml_service.load(tmp_path / "nonexistent.yml")

    def test_load_directory_raises_error(self, yaml_service, tmp_path):
        """Test loading directory raises error."""
        with pytest.raises(YamlLoadError, match="Not a file"):
            yaml_service.load(tmp_path)

    def test_load_empty_file(self, yaml_service, tmp_path):
        """Test loading empty file returns empty dict."""
        empty_file = tmp_path / "empty.yml"
        empty_file.write_text("")
        data = yaml_service.load(empty_file)
        assert data == {}

    def test_load_preserves_order(self, yaml_service, tmp_path):
        """Test that loading preserves key order."""
        file_path = tmp_path / "ordered.yml"
        content = """
first: 1
second: 2
third: 3
"""
        file_path.write_text(content)
        data = yaml_service.load(file_path)
        keys = list(data.keys())
        assert keys == ["first", "second", "third"]


class TestYamlServiceSave:
    """Tests for YAML saving."""

    def test_save_creates_file(self, yaml_service, tmp_path):
        """Test saving creates new file."""
        file_path = tmp_path / "new.yml"
        data = {"entities": {"sample": {"type": "entity"}}}

        result = yaml_service.save(data, file_path, create_backup=False)

        assert result == file_path
        assert file_path.exists()
        loaded = yaml_service.load(file_path)
        assert loaded == data

    def test_save_creates_parent_directory(self, yaml_service, tmp_path):
        """Test saving creates parent directories."""
        file_path = tmp_path / "nested" / "dir" / "file.yml"
        data = {"test": "value"}

        yaml_service.save(data, file_path, create_backup=False)

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_save_with_backup(self, yaml_service, temp_yaml_file):
        """Test saving creates backup of existing file."""
        _ = temp_yaml_file.read_text()
        new_data = {"modified": True}

        yaml_service.save(new_data, temp_yaml_file, create_backup=True)

        # Check new content
        loaded = yaml_service.load(temp_yaml_file)
        assert loaded == new_data

        # Check backup exists
        backups = yaml_service.list_backups("test.yml")
        assert len(backups) > 0

    def test_load_save_roundtrip(self, yaml_service, temp_yaml_file):
        """Test load-save-load preserves data."""
        original = yaml_service.load(temp_yaml_file)
        yaml_service.save(original, temp_yaml_file, create_backup=False)
        reloaded = yaml_service.load(temp_yaml_file)

        assert reloaded == original

    def test_save_atomic_write(self, yaml_service, tmp_path):
        """Test that save uses atomic write (temp file)."""
        file_path = tmp_path / "atomic.yml"
        data = {"test": "data"}

        # Save should not leave temp files behind
        yaml_service.save(data, file_path, create_backup=False)

        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0


class TestYamlServiceBackup:
    """Tests for backup functionality."""

    def test_create_backup(self, yaml_service, temp_yaml_file):
        """Test creating backup."""
        backup_path = yaml_service.create_backup(temp_yaml_file)

        assert backup_path.exists()
        assert "backup" in backup_path.name
        assert backup_path.suffix == temp_yaml_file.suffix

    def test_backup_nonexistent_file_raises_error(self, yaml_service, tmp_path):
        """Test backing up non-existent file raises error."""
        with pytest.raises(YamlServiceError, match="non-existent"):
            yaml_service.create_backup(tmp_path / "nonexistent.yml")

    def test_list_backups(self, yaml_service, temp_yaml_file):
        """Test listing backups."""

        # Create multiple backups with time separation to avoid same timestamp
        yaml_service.create_backup(temp_yaml_file)
        time.sleep(1.1)  # Ensure different second in timestamp
        yaml_service.create_backup(temp_yaml_file)

        backups = yaml_service.list_backups("test.yml")
        assert len(backups) >= 2

    def test_list_backups_empty(self, yaml_service):
        """Test listing backups when none exist."""
        backups = yaml_service.list_backups("nonexistent.yml")
        assert backups == []

    def test_restore_backup(self, yaml_service, temp_yaml_file, tmp_path):
        """Test restoring backup."""
        # Load and create backup
        original_content = yaml_service.load(temp_yaml_file)
        backup_path = yaml_service.create_backup(temp_yaml_file)

        # Verify backup contains original content
        backup_content = yaml_service.load(backup_path)
        assert backup_content == original_content

        # Modify file
        modified_data = {"modified": True}
        yaml_service.save(modified_data, temp_yaml_file, create_backup=False)

        # Verify modification worked
        modified_content = yaml_service.load(temp_yaml_file)
        assert modified_content == modified_data

        # Restore backup (don't create backup of modified file)
        restored_path = yaml_service.restore_backup(backup_path, temp_yaml_file, create_backup=False)

        # Check restoration
        restored_data = yaml_service.load(restored_path)
        assert restored_data == original_content


class TestYamlServiceEntityKeyOrdering:
    """Tests for entity key ordering (defensive programming)."""

    def test_order_entity_keys_preserves_all_keys(self, yaml_service, tmp_path):
        """
        Test that _order_entity_keys preserves ALL keys, including unknown ones.
        
        This is critical defensive programming - adding new entity configuration
        keys in the future should never result in data loss.
        """
        # Create entity with mix of known and unknown keys
        data = {
            "entities": {
                "test_entity": {
                    # Known keys (should be ordered)
                    "type": "entity",
                    "source": "table",
                    "system_id": "system_id",
                    "public_id": "test_id",
                    "keys": ["id"],
                    "columns": ["name", "value"],
                    "values": [[1, "a"], [2, "b"]],
                    "materialized": {"enabled": True},
                    "foreign_keys": [{"entity": "other"}],
                    "filters": [{"type": "exists_in"}],
                    # Unknown keys (should be preserved at end, alphabetically)
                    "z_future_key": "should be preserved",
                    "a_new_feature": "also preserved",
                    "experimental_config": {"nested": "data"},
                }
            }
        }

        # Save and reload to trigger key ordering
        file_path = tmp_path / "test_ordering.yml"
        yaml_service.save(data, file_path, create_backup=False)
        reloaded = yaml_service.load(file_path)

        entity = reloaded["entities"]["test_entity"]

        # CRITICAL: ALL keys must be preserved (defensive programming)
        assert "type" in entity
        assert "source" in entity
        assert "system_id" in entity
        assert "public_id" in entity
        assert "keys" in entity
        assert "columns" in entity
        assert "values" in entity
        assert "materialized" in entity
        assert "foreign_keys" in entity
        assert "filters" in entity
        # Unknown keys MUST be preserved
        assert "z_future_key" in entity
        assert "a_new_feature" in entity
        assert "experimental_config" in entity

        # Verify values are correct
        assert entity["z_future_key"] == "should be preserved"
        assert entity["a_new_feature"] == "also preserved"
        assert entity["experimental_config"] == {"nested": "data"}

        # Verify key count - no data loss
        assert len(entity) == 13

    def test_order_entity_keys_correct_order(self, yaml_service, tmp_path):
        """Test that known keys appear in correct canonical order."""
        data = {
            "entities": {
                "test_entity": {
                    # Add keys in random order
                    "filters": [],
                    "type": "entity",
                    "values": [[1, 2]],
                    "keys": ["id"],
                    "system_id": "system_id",
                    "foreign_keys": [],
                    "columns": ["a", "b"],
                    "source": "table",
                    "public_id": "test_id",
                    "materialized": {"enabled": True},
                }
            }
        }

        # Save and reload
        file_path = tmp_path / "test_order.yml"
        yaml_service.save(data, file_path, create_backup=False)
        
        # Read raw YAML to check actual ordering
        content = file_path.read_text()
        
        # Known keys should appear in canonical order
        # Find indices of each key in the file content
        type_idx = content.index("type:")
        source_idx = content.index("source:")
        system_id_idx = content.index("system_id:")
        public_id_idx = content.index("public_id:")
        keys_idx = content.index("keys:")
        columns_idx = content.index("columns:")
        values_idx = content.index("values:")
        materialized_idx = content.index("materialized:")
        foreign_keys_idx = content.index("foreign_keys:")
        
        # Verify ordering: type < source < system_id < public_id < keys < columns < values < materialized < foreign_keys
        assert type_idx < source_idx < system_id_idx < public_id_idx
        assert public_id_idx < keys_idx < columns_idx < values_idx
        assert values_idx < materialized_idx < foreign_keys_idx

    def test_order_entity_keys_unknown_alphabetical(self, yaml_service, tmp_path):
        """Test that unknown keys are appended alphabetically."""
        data = {
            "entities": {
                "test_entity": {
                    "type": "entity",
                    # Unknown keys in non-alphabetical order
                    "zebra": "z",
                    "alpha": "a",
                    "beta": "b",
                }
            }
        }

        file_path = tmp_path / "test_alpha.yml"
        yaml_service.save(data, file_path, create_backup=False)
        content = file_path.read_text()

        # Unknown keys should be alphabetically ordered
        alpha_idx = content.index("alpha:")
        beta_idx = content.index("beta:")
        zebra_idx = content.index("zebra:")

        assert alpha_idx < beta_idx < zebra_idx


class TestYamlServiceValidation:
    """Tests for YAML validation."""

    def test_validate_valid_yaml(self, yaml_service):
        """Test validating valid YAML."""
        content = "key: value\nlist:\n  - item1\n  - item2"
        is_valid, error = yaml_service.validate_yaml(content)
        assert is_valid is True
        assert error is None

    def test_validate_invalid_yaml(self, yaml_service):
        """Test validating invalid YAML."""
        # Use truly invalid YAML syntax that ruamel.yaml will reject
        content = "key: value\n\t\tinvalid: [unclosed"
        is_valid, error = yaml_service.validate_yaml(content)
        assert is_valid is False
        assert error is not None

    def test_validate_empty_yaml(self, yaml_service):
        """Test validating empty YAML."""
        is_valid, error = yaml_service.validate_yaml("")
        assert is_valid is True
        assert error is None
