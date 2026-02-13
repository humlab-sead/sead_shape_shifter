"""Tests for raw YAML update sync with cached project state."""

from __future__ import annotations

import contextlib

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.state_manager import get_app_state
from backend.app.main import app
from backend.app.services import dependency_service, project_service, validation_service, yaml_service

client = TestClient(app)


@pytest.fixture
def reset_services_and_state():
    """Reset service singletons and in-memory project cache between tests."""

    project_service._project_service = None
    dependency_service._dependency_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    with contextlib.suppress(RuntimeError):
        app_state = get_app_state()
        app_state._active_projects.clear()
        app_state._project_versions.clear()
        app_state._project_dirty.clear()

    yield

    project_service._project_service = None
    dependency_service._dependency_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    with contextlib.suppress(RuntimeError):
        app_state = get_app_state()
        app_state._active_projects.clear()
        app_state._project_versions.clear()
        app_state._project_dirty.clear()


def test_update_raw_yaml_forces_reload(tmp_path, monkeypatch, reset_services_and_state):
    """PUT /raw-yaml must invalidate cache so subsequent reads see new entities."""

    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    # Create initial project with 3 entities
    entities_v1 = {
        "datasheet": {"type": "openpyxl", "columns": ["a"], "options": {"filename": "x.xlsx", "sheet_name": "s"}},
        "sample": {"type": "entity", "source": "datasheet", "columns": ["a"], "depends_on": ["datasheet"]},
        "site": {"type": "openpyxl", "columns": ["b"], "options": {"filename": "x.xlsx", "sheet_name": "t"}},
    }

    create_resp = client.post("/api/v1/projects", json={"name": "test_project", "entities": entities_v1})
    assert create_resp.status_code == 201

    # Prime ApplicationState cache (this is what used to cause staleness)
    list_resp_v1 = client.get("/api/v1/projects/test_project/entities")
    assert list_resp_v1.status_code == 200
    assert {e["name"] for e in list_resp_v1.json()} == {"datasheet", "sample", "site"}

    # Update YAML to include 2 more entities
    yaml_v2 = """
metadata:
  name: test_project
  type: shapeshifter-project
  description: test
  version: 1.0.0
entities:
  datasheet:
    type: openpyxl
    columns: [a]
    options:
      filename: x.xlsx
      sheet_name: s
  sample:
    type: entity
    source: datasheet
    columns: [a]
    depends_on: [datasheet]
  site:
    type: openpyxl
    columns: [b]
    options:
      filename: x.xlsx
      sheet_name: t
  location:
    type: openpyxl
    columns: [c]
    options:
      filename: x.xlsx
      sheet_name: u
  site_location:
    type: openpyxl
    columns: [d]
    foreign_keys:
      - entity: site
        local_keys: [site_id]
        remote_keys: [system_id]
    options:
      filename: x.xlsx
      sheet_name: v
""".lstrip()

    update_resp = client.put("/api/v1/projects/test_project/raw-yaml", json={"yaml_content": yaml_v2})
    assert update_resp.status_code == 200

    # Entity list should now reflect 5 entities (not stale 3)
    list_resp_v2 = client.get("/api/v1/projects/test_project/entities")
    assert list_resp_v2.status_code == 200
    assert {e["name"] for e in list_resp_v2.json()} == {"datasheet", "sample", "site", "location", "site_location"}

    # Dependency graph should include nodes for all entities
    deps_resp = client.get("/api/v1/projects/test_project/dependencies")
    assert deps_resp.status_code == 200
    graph = deps_resp.json()
    assert {n["name"] for n in graph["nodes"]} == {"datasheet", "sample", "site", "location", "site_location"}
