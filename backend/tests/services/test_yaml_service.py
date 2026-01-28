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
