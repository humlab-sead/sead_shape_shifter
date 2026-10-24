"""Tests for ProjectService boundary-based persistence methods.

Verifies that save_metadata_boundary / save_options_boundary /
save_entity_boundary write only the targeted section and do not
disturb other sections or their comments.
"""

from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from backend.app.core.config import settings
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.project_provider_binding_service import ProjectProviderBindingError
from backend.app.services.project_service import ProjectService
from backend.app.services.yaml_service import YamlService

# pylint: disable=redefined-outer-name

FIXTURE_YAML = """\
# Top-level comment preserved
metadata:
  name: test-project
  version: 1.0.0
  description: A test project

options:
  # options comment preserved
  output: csv

# Entities comment preserved
entities:
  # sample comment preserved
  sample:
    type: entity
    keys: [sample_id]
    columns: [name, value]
  site:
    type: entity
    keys: [site_id]
    columns: [location]
"""


@pytest.fixture
def projects_dir(tmp_path: Path) -> Path:
    p = tmp_path / "projects"
    p.mkdir()
    return p


@pytest.fixture
def project_file(projects_dir: Path) -> Path:
    """Write fixture YAML into the expected path for project 'test-project'."""
    proj_dir = projects_dir / "test-project"
    proj_dir.mkdir(parents=True)
    path = proj_dir / "shapeshifter.yml"
    path.write_text(FIXTURE_YAML)
    return path


@pytest.fixture
def service(projects_dir: Path, monkeypatch) -> ProjectService:
    monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
    mock_state = MagicMock()
    mock_state.get = MagicMock(return_value=None)
    mock_state.activate = MagicMock()
    mock_state.update = MagicMock()
    mock_state.invalidate = MagicMock()
    mock_state.mark_active = MagicMock()
    mock_state.get_active_metadata = MagicMock(return_value=MagicMock(version="1.0.0"))
    with patch("backend.app.services.project_service.settings") as mock_cfg:
        mock_cfg.PROJECTS_DIR = projects_dir
        mock_cfg.global_data_dir = projects_dir / "shared"
        mock_cfg.application_root = projects_dir.parent
        svc = ProjectService(projects_dir=projects_dir, state=mock_state)
    return svc


# ---------------------------------------------------------------------------
# save_metadata_boundary
# ---------------------------------------------------------------------------


class TestSaveMetadataBoundary:
    def test_updates_metadata(self, service: ProjectService, project_file: Path) -> None:
        new_meta: dict[str, Any] = {"name": "test-project", "version": "2.0.0", "description": "Updated"}
        service.save_metadata_boundary("test-project", new_meta)

        data = YamlService().load(project_file)
        assert data["metadata"]["version"] == "2.0.0"
        assert data["metadata"]["description"] == "Updated"

    def test_entities_unchanged(self, service: ProjectService, project_file: Path) -> None:
        service.save_metadata_boundary("test-project", {"name": "test-project", "version": "9.9.9"})

        data = YamlService().load(project_file)
        assert "sample" in data["entities"]
        assert "site" in data["entities"]

    def test_options_unchanged(self, service: ProjectService, project_file: Path) -> None:
        service.save_metadata_boundary("test-project", {"name": "test-project"})

        data = YamlService().load(project_file)
        assert data["options"]["output"] == "csv"

    def test_invalidates_state_cache(self, service: ProjectService, project_file: Path) -> None:  # pylint: disable=unused-argument
        service.save_metadata_boundary("test-project", {"name": "test-project"})
        cast(MagicMock, service.state.invalidate).assert_called_once_with("test-project")

    def test_preserves_pair_and_rejects_pair_changes(self, service: ProjectService, project_file: Path) -> None:
        bound_yaml = FIXTURE_YAML.replace(
            "  version: 1.0.0\n",
            "  version: 1.0.0\n  data_provider_code: test-provider\n  provider_schema: schema-one\n",
        )
        project_file.write_text(bound_yaml, encoding="utf-8")
        metadata = {
            "name": "test-project",
            "version": "2.0.0",
            "description": "Updated",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
        }

        service.save_metadata_boundary("test-project", metadata)
        data = YamlService().load(project_file)
        assert data["metadata"]["data_provider_code"] == "test-provider"
        assert data["metadata"]["provider_schema"] == "schema-one"

        original = project_file.read_bytes()
        metadata["provider_schema"] = "schema-two"
        with pytest.raises(ProjectProviderBindingError):
            service.save_metadata_boundary("test-project", metadata)
        assert project_file.read_bytes() == original


# ---------------------------------------------------------------------------
# save_options_boundary
# ---------------------------------------------------------------------------


class TestSaveOptionsBoundary:
    def test_updates_options(self, service: ProjectService, project_file: Path) -> None:
        service.save_options_boundary("test-project", {"output": "excel", "mode": "append"})

        data = YamlService().load(project_file)
        assert data["options"]["output"] == "excel"
        assert data["options"]["mode"] == "append"

    def test_entities_unchanged(self, service: ProjectService, project_file: Path) -> None:
        service.save_options_boundary("test-project", {"output": "excel"})

        data = YamlService().load(project_file)
        assert "sample" in data["entities"]
        assert data["entities"]["sample"]["keys"] == ["sample_id"]

    def test_metadata_unchanged(self, service: ProjectService, project_file: Path) -> None:
        service.save_options_boundary("test-project", {"output": "tsv"})

        data = YamlService().load(project_file)
        assert data["metadata"]["name"] == "test-project"
        assert data["metadata"]["version"] == "1.0.0"

    def test_invalidates_state_cache(self, service: ProjectService, project_file: Path) -> None:  # pylint: disable=unused-argument
        service.save_options_boundary("test-project", {})
        cast(MagicMock, service.state.invalidate).assert_called_once_with("test-project")

    def test_preserves_provider_pair(self, service: ProjectService, project_file: Path) -> None:
        project_file.write_text(
            FIXTURE_YAML.replace(
                "  version: 1.0.0\n",
                "  version: 1.0.0\n  data_provider_code: test-provider\n  provider_schema: schema-one\n",
            ),
            encoding="utf-8",
        )

        service.save_options_boundary("test-project", {"output": "tsv"})

        metadata = YamlService().load(project_file)["metadata"]
        assert metadata["data_provider_code"] == "test-provider"
        assert metadata["provider_schema"] == "schema-one"


# ---------------------------------------------------------------------------
# save_entity_boundary
# ---------------------------------------------------------------------------


class TestSaveEntityBoundary:
    def test_updates_entity(self, service: ProjectService, project_file: Path) -> None:
        updated = {"type": "entity", "keys": ["sample_id"], "columns": ["name", "value", "extra"]}
        service.save_entity_boundary("test-project", "sample", updated)

        data = YamlService().load(project_file)
        assert data["entities"]["sample"]["columns"] == ["name", "value", "extra"]

    def test_sibling_entity_unchanged(self, service: ProjectService, project_file: Path) -> None:
        updated = {"type": "entity", "keys": ["sample_id"], "columns": ["name"]}
        service.save_entity_boundary("test-project", "sample", updated)

        data = YamlService().load(project_file)
        assert "site" in data["entities"]
        assert data["entities"]["site"]["keys"] == ["site_id"]

    def test_adds_new_entity(self, service: ProjectService, project_file: Path) -> None:
        new_entity = {"type": "entity", "keys": ["analysis_id"], "columns": ["result"]}
        service.save_entity_boundary("test-project", "analysis", new_entity)

        data = YamlService().load(project_file)
        assert "analysis" in data["entities"]
        assert "sample" in data["entities"]

    def test_deletes_entity(self, service: ProjectService, project_file: Path) -> None:
        service.save_entity_boundary("test-project", "sample", None)

        data = YamlService().load(project_file)
        assert "sample" not in data["entities"]
        assert "site" in data["entities"]

    def test_metadata_unchanged_after_entity_update(self, service: ProjectService, project_file: Path) -> None:
        service.save_entity_boundary("test-project", "sample", {"type": "entity", "keys": ["x"]})

        data = YamlService().load(project_file)
        assert data["metadata"]["name"] == "test-project"
        assert data["options"]["output"] == "csv"

    def test_invalidates_state_cache(self, service: ProjectService, project_file: Path) -> None:  # pylint: disable=unused-argument
        service.save_entity_boundary("test-project", "sample", {"type": "entity", "keys": ["x"]})
        cast(MagicMock, service.state.invalidate).assert_called_once_with("test-project")

    def test_preserves_provider_pair(self, service: ProjectService, project_file: Path) -> None:
        project_file.write_text(
            FIXTURE_YAML.replace(
                "  version: 1.0.0\n",
                "  version: 1.0.0\n  data_provider_code: test-provider\n  provider_schema: schema-one\n",
            ),
            encoding="utf-8",
        )

        service.save_entity_boundary("test-project", "sample", {"type": "entity", "keys": ["sample_id"]})

        metadata = YamlService().load(project_file)["metadata"]
        assert metadata["data_provider_code"] == "test-provider"
        assert metadata["provider_schema"] == "schema-one"


class TestSaveEntityRenameBoundary:
    @staticmethod
    def _renamed_project(project_file: Path) -> Project:
        return Project(
            metadata=ProjectMetadata(
                name="test-project",
                description="Test",
                version="1.0.0",
                file_path=str(project_file),
                entity_count=2,
                default_entity="specimen",
            ),
            entities={
                "specimen": {"type": "entity", "keys": ["sample_id"], "columns": ["name", "value"]},
                "site": {"type": "entity", "keys": ["site_id"], "columns": ["location"]},
            },
            options={"output": "csv"},
        )

    def test_renames_project_and_moves_note_without_changing_task_state(self, service: ProjectService, project_file: Path) -> None:
        project_data = service.yaml_service.load(project_file)
        project_data["metadata"]["default_entity"] = "sample"
        service.yaml_service.save(project_data, project_file, create_backup=False)
        sidecar_path = service.sidecar_manager.get_sidecar_path(project_file)
        service.yaml_service.save(
            {"task_list": {"todo": ["sample"], "flagged": {"sample": True}}, "notes": {"sample": "Check rows"}},
            sidecar_path,
        )

        warnings = service.save_entity_rename_boundary("test-project", "sample", "specimen", self._renamed_project(project_file))

        project_data = YamlService().load(project_file)
        sidecar_data = YamlService().load(sidecar_path)
        assert "sample" not in project_data["entities"]
        assert project_data["entities"]["specimen"]["keys"] == ["sample_id"]
        assert project_data["metadata"]["default_entity"] == "specimen"
        assert sidecar_data == {
            "task_list": {"todo": ["sample"], "flagged": {"sample": True}},
            "notes": {"specimen": "Check rows"},
        }
        assert warnings == []

    def test_sidecar_save_failure_keeps_project_rename_and_returns_warning(
        self, service: ProjectService, project_file: Path, monkeypatch
    ) -> None:
        sidecar_path = service.sidecar_manager.get_sidecar_path(project_file)
        service.yaml_service.save({"task_list": {"done": ["sample"]}, "notes": {"sample": "Check rows"}}, sidecar_path)
        sidecar_before = sidecar_path.read_bytes()
        original_save = service.yaml_service.save

        def fail_sidecar_save(data, filename, *args, **kwargs):
            if Path(filename) == sidecar_path:
                raise OSError("simulated sidecar save failure")
            return original_save(data, filename, *args, **kwargs)

        monkeypatch.setattr(service.yaml_service, "save", fail_sidecar_save)

        warnings = service.save_entity_rename_boundary("test-project", "sample", "specimen", self._renamed_project(project_file))

        project_data = YamlService().load(project_file)
        assert "specimen" in project_data["entities"]
        assert "sample" not in project_data["entities"]
        assert sidecar_path.read_bytes() == sidecar_before

        assert warnings == [
            "Entity 'specimen' was saved, but its note could not be moved from 'sample'. The note remains under the old name."
        ]

    def test_existing_destination_note_returns_warning_without_overwriting(self, service: ProjectService, project_file: Path) -> None:
        sidecar_path = service.sidecar_manager.get_sidecar_path(project_file)
        service.yaml_service.save({"notes": {"sample": "Original note", "specimen": "Existing note"}}, sidecar_path)

        warnings = service.save_entity_rename_boundary("test-project", "sample", "specimen", self._renamed_project(project_file))

        saved_project = YamlService().load(project_file)
        saved_sidecar = YamlService().load(sidecar_path)
        assert "specimen" in saved_project["entities"]
        assert saved_sidecar["notes"] == {"sample": "Original note", "specimen": "Existing note"}
        assert warnings and "note could not be moved" in warnings[0]


# ---------------------------------------------------------------------------
# Tracked business keys on a bound project
# ---------------------------------------------------------------------------


class TestBoundProjectBusinessKeys:
    """A bound project keeps its resolved ordered business keys."""

    @staticmethod
    def _bind(project_file: Path) -> None:
        project_file.write_text(
            FIXTURE_YAML.replace(
                "  version: 1.0.0\n",
                "  version: 1.0.0\n  type: shapeshifter-project\n  data_provider_code: test-provider\n  provider_schema: schema-one\n",
            ),
            encoding="utf-8",
        )

    def test_rejects_a_key_change_before_writing(self, service: ProjectService, project_file: Path) -> None:
        self._bind(project_file)
        original = project_file.read_bytes()

        with pytest.raises(ProjectProviderBindingError):
            service.save_entity_boundary(
                "test-project",
                "sample",
                {"type": "entity", "keys": ["name"], "columns": ["name", "value"]},
            )

        assert project_file.read_bytes() == original

    def test_rejects_removing_a_key_on_a_bound_project(self, service: ProjectService, project_file: Path) -> None:
        self._bind(project_file)
        original = project_file.read_bytes()

        with pytest.raises(ProjectProviderBindingError):
            service.save_entity_boundary("test-project", "sample", {"type": "entity", "columns": ["name", "value"]})

        assert project_file.read_bytes() == original

    def test_allows_a_non_key_change_on_a_bound_project(self, service: ProjectService, project_file: Path) -> None:
        self._bind(project_file)

        service.save_entity_boundary(
            "test-project",
            "sample",
            {"type": "entity", "keys": ["sample_id"], "columns": ["name", "value", "extra"]},
        )

        assert YamlService().load(project_file)["entities"]["sample"]["columns"] == ["name", "value", "extra"]

    def test_allows_replacing_keys_with_the_same_resolved_order(self, service: ProjectService, project_file: Path) -> None:
        self._bind(project_file)
        project_file.write_text(
            project_file.read_text(encoding="utf-8").replace("keys: [sample_id]", 'keys: "@value: entities.site.keys"'),
            encoding="utf-8",
        )

        service.save_entity_boundary(
            "test-project",
            "sample",
            {"type": "entity", "keys": ["site_id"], "columns": ["name", "value"]},
        )

        assert YamlService().load(project_file)["entities"]["sample"]["keys"] == ["site_id"]

    def test_rejects_replacing_unresolved_keys_with_literals(self, service: ProjectService, project_file: Path) -> None:
        self._bind(project_file)
        project_file.write_text(
            project_file.read_text(encoding="utf-8").replace("keys: [sample_id]", 'keys: "@value: entities.missing.keys"'),
            encoding="utf-8",
        )
        original = project_file.read_bytes()

        with pytest.raises(ProjectProviderBindingError):
            service.save_entity_boundary(
                "test-project",
                "sample",
                {"type": "entity", "keys": ["site_id"], "columns": ["name", "value"]},
            )

        assert project_file.read_bytes() == original

    def test_rejects_reordering_resolved_business_keys(self, service: ProjectService, project_file: Path) -> None:
        self._bind(project_file)
        config = YamlService().load(project_file)
        config["entities"]["sample"]["keys"] = "@value: entities.site.keys"
        config["entities"]["site"]["keys"] = ["site_id", "region_id"]
        YamlService().save(config, project_file, create_backup=False)
        original = project_file.read_bytes()

        with pytest.raises(ProjectProviderBindingError):
            service.save_entity_boundary(
                "test-project",
                "sample",
                {"type": "entity", "keys": ["region_id", "site_id"], "columns": ["name", "value"]},
            )

        assert project_file.read_bytes() == original

    def test_allows_same_resolved_keys_across_a_shared_provider_pair(
        self, service: ProjectService, project_file: Path, projects_dir: Path
    ) -> None:
        self._bind(project_file)
        project_file.write_text(
            project_file.read_text(encoding="utf-8").replace("keys: [sample_id]", 'keys: "@value: entities.site.keys"'),
            encoding="utf-8",
        )
        sibling_dir = projects_dir / "sibling"
        sibling_dir.mkdir()
        sibling_file = sibling_dir / "shapeshifter.yml"
        self._bind(sibling_file)
        sibling_file.write_text(
            sibling_file.read_text(encoding="utf-8").replace("keys: [sample_id]", "keys: [site_id]"),
            encoding="utf-8",
        )

        service.save_entity_boundary(
            "test-project",
            "sample",
            {"type": "entity", "keys": "@value: entities.site.keys", "columns": ["name", "value", "extra"]},
        )

        assert YamlService().load(project_file)["entities"]["sample"]["columns"] == ["name", "value", "extra"]

    def test_rejects_different_resolved_keys_across_a_shared_provider_pair(
        self, service: ProjectService, project_file: Path, projects_dir: Path
    ) -> None:
        self._bind(project_file)
        project_file.write_text(
            project_file.read_text(encoding="utf-8").replace("keys: [sample_id]", 'keys: "@value: entities.site.keys"'),
            encoding="utf-8",
        )
        sibling_dir = projects_dir / "sibling"
        sibling_dir.mkdir()
        sibling_file = sibling_dir / "shapeshifter.yml"
        self._bind(sibling_file)
        sibling_file.write_text(
            sibling_file.read_text(encoding="utf-8").replace("keys: [sample_id]", "keys: [other_id]"),
            encoding="utf-8",
        )
        original = project_file.read_bytes()
        listed_projects = {project.name: project for project in service.list_projects()}
        assert set(listed_projects) == {"test-project", "sibling"}
        assert listed_projects["sibling"].data_provider_code == "test-provider"

        with pytest.raises(ProjectProviderBindingError):
            service.save_entity_boundary(
                "test-project",
                "sample",
                {"type": "entity", "keys": "@value: entities.site.keys", "columns": ["name", "value", "extra"]},
            )

        assert project_file.read_bytes() == original

    def test_allows_a_key_change_on_an_unbound_project(self, service: ProjectService, project_file: Path) -> None:
        service.save_entity_boundary(
            "test-project",
            "sample",
            {"type": "entity", "keys": ["name"], "columns": ["name", "value"]},
        )

        assert YamlService().load(project_file)["entities"]["sample"]["keys"] == ["name"]
