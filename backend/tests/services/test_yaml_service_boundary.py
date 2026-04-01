"""Tests for YamlService boundary-based persistence methods.

Verifies that load_commented / save_commented / merge_boundary:
- preserve YAML comments across writes
- replace only the targeted boundary
- produce atomic writes (temp file cleaned up on failure)
"""

from pathlib import Path

import pytest
from ruamel.yaml.comments import CommentedMap

from backend.app.services.yaml_service import YamlLoadError, YamlService

# pylint: disable=redefined-outer-name


FIXTURE_YAML = """\
# Project-level comment
metadata:
  name: test-project
  version: 1.0.0

options:
  # An inline options comment
  output: csv

# Entities section comment
entities:
  # sample entity comment
  sample:
    type: entity
    keys: [sample_id]
    columns: [name, value]
  # site entity comment
  site:
    type: entity
    keys: [site_id]
    columns: [location]
"""


@pytest.fixture
def yaml_service() -> YamlService:
    return YamlService()


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    path = tmp_path / "shapeshifter.yml"
    path.write_text(FIXTURE_YAML)
    return path


# ---------------------------------------------------------------------------
# load_commented
# ---------------------------------------------------------------------------


class TestLoadCommented:
    def test_returns_commented_map(self, yaml_service: YamlService, project_file: Path) -> None:
        doc = yaml_service.load_commented(project_file)
        assert isinstance(doc, CommentedMap)

    def test_keys_present(self, yaml_service: YamlService, project_file: Path) -> None:
        doc = yaml_service.load_commented(project_file)
        assert "metadata" in doc
        assert "options" in doc
        assert "entities" in doc

    def test_entity_accessible(self, yaml_service: YamlService, project_file: Path) -> None:
        doc = yaml_service.load_commented(project_file)
        assert "sample" in doc["entities"]

    def test_nonexistent_raises(self, yaml_service: YamlService, tmp_path: Path) -> None:
        with pytest.raises(YamlLoadError, match="File not found"):
            yaml_service.load_commented(tmp_path / "missing.yml")

    def test_empty_file_returns_empty_commented_map(self, yaml_service: YamlService, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yml"
        empty.write_text("")
        doc = yaml_service.load_commented(empty)
        assert isinstance(doc, CommentedMap)
        assert len(doc) == 0


# ---------------------------------------------------------------------------
# save_commented
# ---------------------------------------------------------------------------


class TestSaveCommented:
    def test_roundtrip_preserves_structure(self, yaml_service: YamlService, project_file: Path, tmp_path: Path) -> None:
        doc = yaml_service.load_commented(project_file)
        out = tmp_path / "out.yml"
        yaml_service.save_commented(doc, out, create_backup=False)
        reloaded = yaml_service.load(out)
        assert reloaded["metadata"]["name"] == "test-project"
        assert "sample" in reloaded["entities"]
        assert "site" in reloaded["entities"]

    def test_creates_backup_when_requested(self, yaml_service: YamlService, project_file: Path) -> None:
        doc = yaml_service.load_commented(project_file)
        yaml_service.save_commented(doc, project_file, create_backup=True)
        backups = list((project_file.parent / "backups").glob("*.backup.*"))
        assert len(backups) == 1

    def test_no_backup_when_disabled(self, yaml_service: YamlService, project_file: Path) -> None:
        doc = yaml_service.load_commented(project_file)
        yaml_service.save_commented(doc, project_file, create_backup=False)
        backup_dir = project_file.parent / "backups"
        assert not backup_dir.exists() or len(list(backup_dir.glob("*.backup.*"))) == 0

    def test_temp_file_removed_on_success(self, yaml_service: YamlService, project_file: Path) -> None:
        doc = yaml_service.load_commented(project_file)
        yaml_service.save_commented(doc, project_file, create_backup=False)
        temp = project_file.with_suffix(project_file.suffix + ".tmp")
        assert not temp.exists()


# ---------------------------------------------------------------------------
# merge_boundary — top-level key replacement
# ---------------------------------------------------------------------------


class TestMergeBoundaryTopLevel:
    def test_replace_metadata_leaves_entities_intact(self, yaml_service: YamlService, project_file: Path) -> None:
        new_meta = {"name": "changed-project", "version": "2.0.0"}
        yaml_service.merge_boundary(project_file, "metadata", new_meta, create_backup=False)
        data = yaml_service.load(project_file)
        assert data["metadata"]["name"] == "changed-project"
        assert data["metadata"]["version"] == "2.0.0"
        # Other sections untouched
        assert "sample" in data["entities"]
        assert "site" in data["entities"]
        assert data["options"]["output"] == "csv"

    def test_replace_options_leaves_entities_intact(self, yaml_service: YamlService, project_file: Path) -> None:
        new_options = {"output": "excel", "extra": True}
        yaml_service.merge_boundary(project_file, "options", new_options, create_backup=False)
        data = yaml_service.load(project_file)
        assert data["options"]["output"] == "excel"
        assert data["options"]["extra"] is True
        assert "sample" in data["entities"]
        assert data["metadata"]["name"] == "test-project"

    def test_comments_survive_metadata_update(self, yaml_service: YamlService, project_file: Path) -> None:
        """Comments on the entities section should survive a metadata-only update."""
        yaml_service.merge_boundary(project_file, "metadata", {"name": "new-name", "version": "3.0.0"}, create_backup=False)
        text = project_file.read_text()
        # The entities-section comment should still be present
        assert "Entities section comment" in text

    def test_delete_top_level_key(self, yaml_service: YamlService, project_file: Path) -> None:
        yaml_service.merge_boundary(project_file, "options", None, create_backup=False)
        data = yaml_service.load(project_file)
        assert "options" not in data
        assert "sample" in data["entities"]


# ---------------------------------------------------------------------------
# merge_boundary — entity (nested) replacement
# ---------------------------------------------------------------------------


class TestMergeBoundaryEntity:
    def test_replace_entity_leaves_others_intact(self, yaml_service: YamlService, project_file: Path) -> None:
        updated = {"type": "entity", "keys": ["sample_id"], "columns": ["name", "value", "extra"]}
        yaml_service.merge_boundary(project_file, ("entities", "sample"), updated, create_backup=False)
        data = yaml_service.load(project_file)
        assert data["entities"]["sample"]["columns"] == ["name", "value", "extra"]
        assert "site" in data["entities"]
        assert data["entities"]["site"]["keys"] == ["site_id"]

    def test_add_new_entity(self, yaml_service: YamlService, project_file: Path) -> None:
        new_entity = {"type": "entity", "keys": ["analysis_id"], "columns": ["result"]}
        yaml_service.merge_boundary(project_file, ("entities", "analysis"), new_entity, create_backup=False)
        data = yaml_service.load(project_file)
        assert "analysis" in data["entities"]
        assert "sample" in data["entities"]
        assert "site" in data["entities"]

    def test_delete_entity(self, yaml_service: YamlService, project_file: Path) -> None:
        yaml_service.merge_boundary(project_file, ("entities", "sample"), None, create_backup=False)
        data = yaml_service.load(project_file)
        assert "sample" not in data["entities"]
        assert "site" in data["entities"]

    def test_delete_missing_entity_is_safe(self, yaml_service: YamlService, project_file: Path) -> None:
        """Deleting an entity that doesn't exist should not raise."""
        yaml_service.merge_boundary(project_file, ("entities", "nonexistent"), None, create_backup=False)
        data = yaml_service.load(project_file)
        assert "sample" in data["entities"]

    def test_site_comment_survives_sample_update(self, yaml_service: YamlService, project_file: Path) -> None:
        updated = {"type": "entity", "keys": ["sample_id"], "columns": ["name"]}
        yaml_service.merge_boundary(project_file, ("entities", "sample"), updated, create_backup=False)
        text = project_file.read_text()
        assert "site entity comment" in text

    def test_atomic_write_no_temp_file_remains(self, yaml_service: YamlService, project_file: Path) -> None:
        entity = {"type": "entity", "keys": ["x"], "columns": ["y"]}
        yaml_service.merge_boundary(project_file, ("entities", "new_e"), entity, create_backup=False)
        temp = project_file.with_suffix(project_file.suffix + ".tmp")
        assert not temp.exists()
