"""Tests for entity API endpoints."""

from unittest.mock import MagicMock

import pandas as pd
import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.data_source import ColumnMetadata, TableSchema
from backend.app.services import project_service, validation_service, yaml_service
from backend.app.services.schema_service import SchemaIntrospectionService
from src.reconciliation.mapping_manager import MappingManager

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def sample_entity_data():
    """Sample entity data for tests."""
    return {"type": "entity", "keys": ["id"], "columns": ["name", "value"]}


@pytest.fixture
def reset_services():
    """Reset service singletons between tests."""
    # Clear service instances BEFORE each test

    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    yield

    # Clear again after test
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


class TestEntitiesList:
    """Tests for listing entities."""

    async def test_list_entities(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test listing entities in configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entities
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"entity1": sample_entity_data, "entity2": sample_entity_data},
            },
        )

        # List entities
        response = await authorized_client.get("/api/v1/projects/test_project/entities")
        assert response.status_code == 200
        entities = response.json()
        assert len(entities) == 2
        assert any(e["name"] == "entity1" for e in entities)
        assert any(e["name"] == "entity2" for e in entities)

    async def test_list_entities_empty(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test listing entities in empty configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty config
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": {}},
        )

        # List entities
        response = await authorized_client.get("/api/v1/projects/test_project/entities")
        assert response.status_code == 200
        entities = response.json()
        assert len(entities) == 0

    async def test_list_entities_nonexistent_config(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test listing entities in non-existent configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.get("/api/v1/projects/nonexistent/entities")
        assert response.status_code == 404


class TestEntitiesGet:
    """Tests for getting specific entity."""

    async def test_get_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test getting specific entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entity
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": sample_entity_data},
            },
        )

        # Get entity
        response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity")
        assert response.status_code == 200
        entity = response.json()
        assert entity["name"] == "test_entity"
        assert entity["entity_data"]["type"] == "entity"
        assert entity["entity_data"]["keys"] == ["id"]

    async def test_get_nonexistent_entity(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test getting non-existent entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty config
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": {}},
        )

        # Try to get non-existent entity
        response = await authorized_client.get("/api/v1/projects/test_project/entities/nonexistent")
        assert response.status_code == 404

    async def test_get_fixed_entity_includes_authoritative_fixed_schema(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Fixed entities should expose backend-owned schema metadata."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        entity_data = {
            "type": "fixed",
            "public_id": "location_id",
            "keys": ["name"],
            "columns": ["system_id", "location_id", "name", "country"],
            "values": [[1, 100, "Uppsala", "Sweden"]],
        }

        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"location": entity_data},
            },
        )

        response = await authorized_client.get("/api/v1/projects/test_project/entities/location")
        assert response.status_code == 200
        payload = response.json()
        assert payload["fixed_schema"] == {
            "full_columns": ["system_id", "location_id", "name", "country"],
            "editable_columns": ["country"],
            "identity_columns": ["system_id", "location_id"],
            "key_columns": ["name"],
            "order_source": "stored",
        }


class TestFixedSchemaDerivation:
    """Tests for derived fixed-schema metadata."""

    async def test_create_fixed_entity_persists_canonical_fixed_schema(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Created fixed entities should be normalized to canonical stored columns."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": {}},
        )

        entity_data = {
            "type": "fixed",
            "public_id": "feature_type_id",
            "keys": ["name"],
            "columns": ["name", "description"],
            "values": [],
        }

        response = await authorized_client.post(
            "/api/v1/projects/test_project/entities",
            json={"name": "feature_type", "entity_data": entity_data},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["fixed_schema"] == {
            "full_columns": ["system_id", "feature_type_id", "name", "description"],
            "editable_columns": ["description"],
            "identity_columns": ["system_id", "feature_type_id"],
            "key_columns": ["name"],
            "order_source": "derived",
        }
        assert payload["entity_data"]["columns"] == ["name", "description"]

    async def test_update_fixed_entity_returns_authoritative_fixed_schema(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Updated fixed entities should return normalized, canonical schema metadata."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": {}},
        )

        entity_data = {
            "type": "fixed",
            "public_id": "feature_type_id",
            "keys": ["name"],
            "columns": ["name", "description"],
            "values": [],
        }

        create = await authorized_client.post(
            "/api/v1/projects/test_project/entities",
            json={"name": "feature_type", "entity_data": entity_data},
        )
        assert create.status_code == 201

        update = await authorized_client.put(
            "/api/v1/projects/test_project/entities/feature_type",
            json={"entity_data": entity_data},
        )
        assert update.status_code == 200
        payload = update.json()
        assert payload["fixed_schema"] == {
            "full_columns": ["system_id", "feature_type_id", "name", "description"],
            "editable_columns": ["description"],
            "identity_columns": ["system_id", "feature_type_id"],
            "key_columns": ["name"],
            "order_source": "derived",
        }
        assert payload["entity_data"]["columns"] == ["name", "description"]

    async def test_non_fixed_entity_has_no_fixed_schema(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Non-fixed entities should not expose fixed-schema metadata."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": sample_entity_data},
            },
        )

        response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity")
        assert response.status_code == 200
        assert response.json()["fixed_schema"] is None


class TestEntitiesCreate:
    """Tests for creating entities."""

    async def test_create_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test creating new entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": {}},
        )

        # Add entity
        response = await authorized_client.post(
            "/api/v1/projects/test_project/entities",
            json={"name": "new_entity", "entity_data": sample_entity_data},
        )
        assert response.status_code == 201
        entity = response.json()
        assert entity["name"] == "new_entity"
        assert entity["entity_data"]["type"] == "entity"

        # Verify entity was added
        get_response = await authorized_client.get("/api/v1/projects/test_project/entities/new_entity")
        assert get_response.status_code == 200

    async def test_generate_entity_from_shared_data_source_persists_entity(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """The table-generation endpoint resolves shared includes and persists the generated entity."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        shared_data_source_dir = tmp_path / "shared" / "data-sources"
        shared_data_source_dir.mkdir(parents=True)
        source_config = {
            "driver": "sqlite",
            "options": {"filename": str(tmp_path / "database.sqlite")},
        }
        (shared_data_source_dir / "sead-options.yml").write_text(yaml.safe_dump(source_config), encoding="utf-8")
        monkeypatch.setattr(settings, "GLOBAL_DATA_SOURCE_DIR", shared_data_source_dir)
        monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR", str(shared_data_source_dir))

        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": {}},
        )
        assert create_response.status_code == 201

        project_service.get_project_service().save_options_boundary(
            "test_project",
            {"data_sources": {"sead": "@include: ${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml"}},
        )

        schema_service_init = SchemaIntrospectionService.__init__
        initialized_source_dirs = []

        def track_schema_service_init(schema_service, data_source_dir):
            initialized_source_dirs.append(data_source_dir)
            schema_service_init(schema_service, data_source_dir)

        async def get_table_schema(schema_service, data_source, table_name, schema=None):
            assert data_source == source_config
            assert table_name == "tbl_locations"
            return TableSchema(
                table_name=table_name,
                schema_name=schema,
                columns=[
                    ColumnMetadata(
                        name="location_id",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                        default=None,
                        max_length=None,
                    ),
                    ColumnMetadata(
                        name="location_name",
                        data_type="varchar",
                        nullable=False,
                        is_primary_key=False,
                        default=None,
                        max_length=255,
                    ),
                ],
                row_count=1,
            )

        loader = MagicMock()
        loader.quote_name.side_effect = lambda name: name
        loader.qualify_name.side_effect = lambda *, schema, table: f"{schema}.{table}" if schema else table
        monkeypatch.setattr(SchemaIntrospectionService, "__init__", track_schema_service_init)
        monkeypatch.setattr(SchemaIntrospectionService, "get_table_schema", get_table_schema)
        monkeypatch.setattr(SchemaIntrospectionService, "create_loader_for_data_source", lambda service, config: loader)

        response = await authorized_client.post(
            "/api/v1/projects/test_project/entities/generate-from-table",
            json={"data_source": "sead", "table_name": "tbl_locations"},
        )

        assert response.status_code == 201, response.text
        assert shared_data_source_dir in initialized_source_dirs
        generated_entity = response.json()["entity_data"]
        assert generated_entity["data_source"] == "sead"
        assert generated_entity["query"] == "SELECT location_id, location_name FROM tbl_locations"

        persisted_response = await authorized_client.get("/api/v1/projects/test_project/entities/tbl_locations")
        assert persisted_response.status_code == 200
        persisted_entity = persisted_response.json()["entity_data"]
        assert {key: persisted_entity[key] for key in generated_entity} == generated_entity

    async def test_create_entity_rejects_invalid_name(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": {}},
        )

        response = await authorized_client.post(
            "/api/v1/projects/test_project/entities",
            json={"name": "_invalid", "entity_data": sample_entity_data},
        )

        assert response.status_code == 422
        entities_response = await authorized_client.get("/api/v1/projects/test_project/entities")
        assert entities_response.json() == []

    async def test_create_duplicate_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test creating duplicate entity returns 409 Conflict."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entity
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"existing": sample_entity_data},
            },
        )

        # Try to add duplicate entity
        response = await authorized_client.post(
            "/api/v1/projects/test_project/entities",
            json={"name": "existing", "entity_data": sample_entity_data},
        )
        assert response.status_code == 409

    async def test_create_entity_nonexistent_config(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test creating entity in non-existent configuration fails."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.post(
            "/api/v1/projects/nonexistent/entities",
            json={"name": "entity", "entity_data": sample_entity_data},
        )
        assert response.status_code == 404


class TestEntitiesUpdate:
    """Tests for updating entities."""

    async def test_update_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test updating existing entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entity
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": sample_entity_data},
            },
        )

        # Update entity
        updated_data = {"type": "entity", "keys": ["id"], "columns": ["updated", "fields"]}
        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/test_entity",
            json={"entity_data": updated_data},
        )
        assert response.status_code == 200
        entity = response.json()
        assert entity["entity_data"]["columns"] == ["updated", "fields"]

        # Verify update
        get_response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity")
        assert get_response.json()["entity_data"]["columns"] == ["updated", "fields"]

    async def test_rename_entity_updates_project_and_sidecar(
        self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": sample_entity_data},
            },
        )

        project_file = tmp_path / "test_project" / "shapeshifter.yml"
        project_data = yaml.safe_load(project_file.read_text(encoding="utf-8"))
        project_data["metadata"]["default_entity"] = "sample"
        project_file.write_text(yaml.safe_dump(project_data), encoding="utf-8")
        sidecar_path = project_file.parent / "shapeshifter.tasks.yml"
        sidecar_path.write_text(
            yaml.safe_dump({"task_list": {"todo": ["sample"], "flagged": {"sample": True}}, "notes": {"sample": "Check rows"}}),
            encoding="utf-8",
        )

        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/sample",
            json={"new_name": "specimen", "entity_data": sample_entity_data},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "specimen"
        assert response.json()["warnings"] == []
        assert (await authorized_client.get("/api/v1/projects/test_project/entities/sample")).status_code == 404
        assert (await authorized_client.get("/api/v1/projects/test_project/entities/specimen")).status_code == 200
        saved_project = yaml.safe_load(project_file.read_text(encoding="utf-8"))
        saved_sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        assert saved_project["metadata"]["default_entity"] == "specimen"
        assert saved_sidecar == {
            "task_list": {"todo": ["sample"], "flagged": {"sample": True}},
            "notes": {"specimen": "Check rows"},
        }

    async def test_rename_succeeds_and_returns_warning_when_note_update_fails(
        self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": sample_entity_data},
            },
        )

        def fail_note_rename(*args, **kwargs):
            raise OSError("simulated note sidecar failure")

        monkeypatch.setattr(
            "backend.app.services.task_list_sidecar_manager.TaskListSidecarManager.prepare_entity_note_rename",
            fail_note_rename,
        )
        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/sample",
            json={"new_name": "specimen", "entity_data": sample_entity_data},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "specimen"
        assert response.json()["warnings"] == [
            "Entity 'specimen' was saved, but its note could not be moved from 'sample'. The note remains under the old name."
        ]
        project_data = yaml.safe_load((tmp_path / "test_project" / "shapeshifter.yml").read_text(encoding="utf-8"))
        assert "specimen" in project_data["entities"]
        assert "sample" not in project_data["entities"]

    async def test_rename_rejects_entity_with_mapping_entry(
        self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": sample_entity_data},
            },
        )

        project_dir = tmp_path / "test_project"
        project_file = project_dir / "shapeshifter.yml"
        sidecar_file = project_dir / "test_project-mapping.yml"
        sidecar_file.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0",
                    "metadata": {"project": "test_project"},
                    "entities": {"sample": {"local_key": "id", "public_id": "sample_id", "links": {}}},
                }
            ),
            encoding="utf-8",
        )
        project_before = project_file.read_bytes()
        sidecar_before = sidecar_file.read_bytes()

        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/sample",
            json={"new_name": "specimen", "entity_data": sample_entity_data},
        )

        assert response.status_code == 409
        assert response.json()["detail"]["context"]["conflict_type"] == "entity_has_mapping"
        assert project_file.read_bytes() == project_before
        assert sidecar_file.read_bytes() == sidecar_before

    async def test_rename_entity_conflict_returns_dependent_names(
        self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        dependent = {"type": "entity", "foreign_keys": [{"entity": "sample", "defer_dependency": True}]}
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": sample_entity_data, "dependent": dependent},
            },
        )

        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/sample",
            json={"new_name": "specimen", "entity_data": sample_entity_data},
        )

        assert response.status_code == 409
        assert response.json()["detail"]["context"]["dependent_entities"] == ["dependent"]
        assert "sample" in yaml.safe_load((tmp_path / "test_project" / "shapeshifter.yml").read_text())["entities"]

    async def test_update_nonexistent_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test updating non-existent entity fails."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty config
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": {}},
        )

        # Try to update non-existent entity
        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/nonexistent",
            json={"entity_data": sample_entity_data},
        )
        assert response.status_code == 404


class TestEntitiesDelete:
    """Tests for deleting entities."""

    async def test_delete_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test deleting entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entity
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": sample_entity_data},
            },
        )

        # Delete entity
        response = await authorized_client.delete("/api/v1/projects/test_project/entities/test_entity")
        assert response.status_code == 204

        # Verify deletion
        get_response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity")
        assert get_response.status_code == 404

    async def test_delete_nonexistent_entity(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test deleting non-existent entity fails."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty config
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": {}},
        )

        # Try to delete non-existent entity
        response = await authorized_client.delete("/api/v1/projects/test_project/entities/nonexistent")
        assert response.status_code == 404


class TestEntityValues:
    """Tests for entity external values endpoints."""

    async def test_get_entity_values_parquet(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test getting entity values from parquet file."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project folder structure
        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        # Create parquet file with test data
        df = pd.DataFrame({"system_id": [1, 2, 3], "id": [101, 102, 103], "name": ["A", "B", "C"], "value": [10, 20, 30]})
        parquet_file = materialized_folder / "test_entity.parquet"
        df.to_parquet(parquet_file, index=False)

        # Create project with entity that has @load: directive
        entity_data = {
            "type": "fixed",
            "columns": ["id", "name", "value"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "id",
            "keys": ["id"],
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        # Get entity values
        response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 200

        data = response.json()
        assert data["columns"] == ["system_id", "id", "name", "value"]
        assert data["row_count"] == 3
        assert data["format"] == "parquet"
        assert data["values"] == [[1, 101, "A", 10], [2, 102, "B", 20], [3, 103, "C", 30]]

    async def test_get_entity_values_csv(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test getting entity values from CSV file."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project folder structure
        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        # Create CSV file with test data
        df = pd.DataFrame({"system_id": [1, 2], "id": [201, 202], "name": ["X", "Y"]})
        csv_file = materialized_folder / "test_entity.csv"
        df.to_csv(csv_file, index=False)

        # Create project with entity that has @load: directive
        entity_data = {
            "type": "fixed",
            "columns": ["id", "name"],
            "values": "@load:materialized/test_entity.csv",
            "public_id": "id",
            "keys": ["id"],
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        # Get entity values
        response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 200

        data = response.json()
        assert data["columns"] == ["system_id", "id", "name"]
        assert data["row_count"] == 2
        assert data["format"] == "csv"

    async def test_get_entity_values_no_load_directive(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test error when entity has no @load: directive."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with entity that has inline values
        entity_data = {"type": "fixed", "columns": ["id", "name"], "values": [[1, "A"], [2, "B"]], "public_id": "id", "keys": ["id"]}
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        # Try to get entity values
        response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 422
        assert "does not have @load: directive" in response.json()["detail"]

    async def test_update_entity_values(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test updating fixed entity values with authoritative columns."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project folder structure
        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        # Create project with entity that has @load: directive
        entity_data = {
            "type": "fixed",
            "columns": ["id", "name"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "id",
            "keys": ["id"],
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        # Update entity values
        update_data = {"columns": ["system_id", "id", "name"], "values": [[1, 10, "A"], [2, 20, "B"], [3, 30, "C"]]}
        response = await authorized_client.put("/api/v1/projects/test_project/entities/test_entity/values", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["columns"] == ["system_id", "id", "name"]
        assert data["row_count"] == 3
        assert data["format"] == "parquet"

        # Verify file was created
        parquet_file = materialized_folder / "test_entity.parquet"
        assert parquet_file.exists()

        # Verify we can read it back

        df = pd.read_parquet(parquet_file)
        assert df.columns.tolist() == ["system_id", "id", "name"]
        assert len(df) == 3

    async def test_update_entity_values_syncs_manual_mapping_sidecar_for_materialized_entity(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """Saving materialized rows should apply only their affected mapping links."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        entity_data = {
            "type": "fixed",
            "columns": ["system_id", "site_id", "name"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "site_id",
            "keys": ["name"],
            "materialized": {
                "enabled": True,
                "source_state": {"type": "csv", "public_id": "site_id", "keys": ["name"]},
                "materialized_at": "2026-06-15T00:00:00Z",
            },
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        sidecar_path = project_folder / "test_project-mapping.yml"
        sidecar_path.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0",
                    "metadata": {
                        "project": "test_project",
                        "created_at": "2026-06-15T00:00:00Z",
                        "updated_at": "2026-06-15T00:00:00Z",
                    },
                    "entities": {
                        "test_entity": {
                            "local_key": "name",
                            "public_id": "site_id",
                            "entity_type": "primary",
                            "links": {
                                "Legacy": {
                                    "target_id": 999,
                                    "source": "reconciliation",
                                    "created_at": "2026-06-15T00:00:00Z",
                                    "committed_at": "2026-06-15T00:00:00Z",
                                    "created_by": "system",
                                }
                            },
                        }
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        update_data = {
            "columns": ["system_id", "site_id", "name"],
            "values": [[1, 10, "A"], [2, None, "B"], [3, 30, "C"]],
        }
        response = await authorized_client.put("/api/v1/projects/test_project/entities/test_entity/values", json=update_data)
        assert response.status_code == 200

        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        links = sidecar["entities"]["test_entity"]["links"]
        assert set(links) == {"Legacy", "A", "C"}
        assert links["Legacy"]["source"] == "reconciliation"
        assert links["A"]["source"] == "manual"
        assert links["A"]["target_id"] == 10
        assert links["C"]["target_id"] == 30

    async def test_update_entity_values_remaps_legacy_order_and_syncs_mapping(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """PUT should remap the recognized legacy order before writing and mapping sync."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        entity_data = {
            "type": "fixed",
            "columns": ["name", "country"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "site_id",
            "keys": ["country"],
            "materialized": {
                "enabled": True,
                "source_state": {"type": "csv", "public_id": "site_id", "keys": ["country"]},
                "materialized_at": "2026-06-15T00:00:00Z",
            },
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        sidecar_path = project_folder / "test_project-mapping.yml"
        sidecar_path.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0",
                    "metadata": {
                        "project": "test_project",
                        "created_at": "2026-06-15T00:00:00Z",
                        "updated_at": "2026-06-15T00:00:00Z",
                    },
                    "entities": {
                        "test_entity": {
                            "local_key": "country",
                            "public_id": "site_id",
                            "entity_type": "primary",
                            "links": {},
                        }
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        update_data = {
            "columns": ["system_id", "site_id", "country", "name"],
            "values": [[1, 10, "SE", "A"], [2, 20, "NO", "B"]],
        }
        response = await authorized_client.put("/api/v1/projects/test_project/entities/test_entity/values", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["columns"] == ["system_id", "site_id", "name", "country"]
        assert data["values"] == [[1, 10, "A", "SE"], [2, 20, "B", "NO"]]

        saved = pd.read_parquet(materialized_folder / "test_entity.parquet")
        assert saved.columns.tolist() == ["system_id", "site_id", "name", "country"]
        assert saved.values.tolist() == [[1, 10, "A", "SE"], [2, 20, "B", "NO"]]

        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        links = sidecar["entities"]["test_entity"]["links"]
        assert set(links) == {"SE", "NO"}
        assert links["SE"]["target_id"] == 10
        assert links["NO"]["target_id"] == 20

    async def test_update_entity_values_rejects_invalid_columns_without_writing(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """PUT should reject unmappable column orders with 422 and leave values files untouched."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        entity_data = {
            "type": "fixed",
            "columns": ["name", "country"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "site_id",
            "keys": ["name"],
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        update_data = {"columns": ["country"], "values": [["SE"]]}
        response = await authorized_client.put("/api/v1/projects/test_project/entities/test_entity/values", json=update_data)
        assert response.status_code == 422
        assert not (materialized_folder / "test_entity.parquet").exists()

    async def test_patch_from_materialized_replaces_manual_mapping_links(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """PATCH from-materialized should replace manual links from the current saved materialized rows."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        pd.DataFrame(
            {
                "system_id": [1, 2, 3],
                "site_id": pd.Series([10, None, 30], dtype="Int64"),
                "name": ["A", "B", "C"],
            }
        ).to_parquet(materialized_folder / "test_entity.parquet", index=False)

        entity_data = {
            "type": "fixed",
            "columns": ["system_id", "site_id", "name"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "site_id",
            "keys": ["name"],
            "materialized": {
                "enabled": True,
                "source_state": {"type": "csv", "public_id": "site_id", "keys": ["name"]},
                "materialized_at": "2026-06-15T00:00:00Z",
            },
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        sidecar_path = project_folder / "test_project-mapping.yml"
        sidecar_path.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0",
                    "metadata": {
                        "project": "test_project",
                        "created_at": "2026-06-15T00:00:00Z",
                        "updated_at": "2026-06-15T00:00:00Z",
                    },
                    "entities": {
                        "test_entity": {
                            "local_key": "name",
                            "public_id": "site_id",
                            "entity_type": "primary",
                            "links": {
                                "Legacy": {
                                    "target_id": 999,
                                    "source": "import",
                                    "created_at": "2026-06-15T00:00:00Z",
                                    "committed_at": "2026-06-15T00:00:00Z",
                                    "created_by": "system",
                                },
                                "A": {
                                    "target_id": 8,
                                    "source": "import",
                                    "created_at": "2026-06-15T00:00:00Z",
                                    "committed_at": "2026-06-15T00:00:00Z",
                                    "created_by": "importer",
                                },
                                "OldManual": {
                                    "target_id": 5,
                                    "source": "manual",
                                    "created_at": "2026-06-15T00:00:00Z",
                                    "committed_at": "2026-06-15T00:00:00Z",
                                    "created_by": "user",
                                },
                            },
                        }
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        response = await authorized_client.patch(
            "/api/v1/projects/test_project/mapping/from-materialized/test_entity",
            json={"replace_manual_links": True},
        )
        assert response.status_code == 200
        assert response.json()["manual_links_replaced"] == 2
        assert response.json()["manual_links_added"] == 0

        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        links = sidecar["entities"]["test_entity"]["links"]
        assert set(links) == {"Legacy", "A", "C"}
        assert links["Legacy"]["source"] == "import"
        assert links["A"]["source"] == "manual"
        assert links["A"]["target_id"] == 10
        assert links["C"]["target_id"] == 30

    async def test_patch_from_materialized_is_additive_by_default_and_noops_on_repeat(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """A bodyless rebuild should preserve occupied keys and add each missing key once."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        entity_data = {
            "type": "fixed",
            "columns": ["system_id", "site_id", "name"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "site_id",
            "keys": ["name"],
            "materialized": {"enabled": True, "source_state": {"type": "csv"}},
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        project_folder = tmp_path / "test_project"
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()
        pd.DataFrame(
            {
                "system_id": [1, 2, 3],
                "site_id": pd.Series([11, None, 30], dtype="Int64"),
                "name": ["A", "B", "C"],
            }
        ).to_parquet(materialized_folder / "test_entity.parquet", index=False)

        sidecar_path = project_folder / "test_project-mapping.yml"
        sidecar_path.write_text(
            yaml.safe_dump(
                {
                    "version": "2.0",
                    "metadata": {
                        "project": "test_project",
                        "created_at": "2026-06-15T00:00:00Z",
                        "updated_at": "2026-06-15T00:00:00Z",
                    },
                    "entities": {
                        "test_entity": {
                            "local_key": "name",
                            "public_id": "site_id",
                            "entity_type": "primary",
                            "links": {
                                "A": {
                                    "target_id": 10,
                                    "source": "manual",
                                    "created_at": "2026-06-15T00:00:00Z",
                                    "committed_at": "2026-06-15T00:00:00Z",
                                    "created_by": "original-user",
                                    "notes": "keep this link",
                                },
                                "B": {
                                    "target_id": 20,
                                    "source": "import",
                                    "created_at": "2026-06-15T00:00:00Z",
                                    "committed_at": "2026-06-15T00:00:00Z",
                                    "created_by": "importer",
                                },
                                "OldManual": {
                                    "target_id": 5,
                                    "source": "manual",
                                    "created_at": "2026-06-15T00:00:00Z",
                                    "committed_at": "2026-06-15T00:00:00Z",
                                    "created_by": "user",
                                },
                            },
                        }
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        url = "/api/v1/projects/test_project/mapping/from-materialized/test_entity"
        response = await authorized_client.patch(url)
        assert response.status_code == 200, response.text
        assert response.json()["manual_links_added"] == 1
        assert response.json()["manual_links_replaced"] == 0

        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        links = sidecar["entities"]["test_entity"]["links"]
        assert set(links) == {"A", "B", "OldManual", "C"}
        assert links["A"]["target_id"] == 10
        assert links["A"]["created_by"] == "original-user"
        assert links["A"]["notes"] == "keep this link"
        assert links["B"]["source"] == "import"
        assert links["B"]["target_id"] == 20
        assert links["C"]["source"] == "manual"
        assert links["C"]["target_id"] == 30

        written_bytes = sidecar_path.read_bytes()
        repeated = await authorized_client.patch(url, json={})
        assert repeated.status_code == 200, repeated.text
        assert repeated.json()["manual_links_added"] == 0
        assert repeated.json()["manual_links_replaced"] == 0
        assert sidecar_path.read_bytes() == written_bytes

        repeated_false = await authorized_client.patch(url, json={"replace_manual_links": False})
        assert repeated_false.status_code == 200, repeated_false.text
        assert repeated_false.json()["manual_links_added"] == 0
        assert sidecar_path.read_bytes() == written_bytes

        malformed = await authorized_client.patch(url, json={"replace_manual_links": "not-a-bool"})
        assert malformed.status_code == 422
        assert sidecar_path.read_bytes() == written_bytes

    async def test_patch_from_materialized_creates_entry_with_ordered_compound_keys(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """A missing mapping entry should use the declared safe_keys order."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        entity_data = {
            "type": "fixed",
            "columns": ["system_id", "site_id", "country_code", "site_code"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "site_id",
            "keys": ["country_code", "site_code"],
            "materialized": {"enabled": True, "source_state": {"type": "csv"}},
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )
        project_folder = tmp_path / "test_project"
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()
        pd.DataFrame({"system_id": [1], "site_id": [12], "country_code": ["SE"], "site_code": ["S1"]}).to_parquet(
            materialized_folder / "test_entity.parquet", index=False
        )

        response = await authorized_client.patch("/api/v1/projects/test_project/mapping/from-materialized/test_entity")

        assert response.status_code == 200, response.text
        assert response.json()["manual_links_added"] == 1
        sidecar = yaml.safe_load((project_folder / "test_project-mapping.yml").read_text(encoding="utf-8"))
        entry = sidecar["entities"]["test_entity"]
        assert entry["local_key"] == ["country_code", "site_code"]
        assert entry["links"]["SE|S1"]["target_id"] == 12

    async def test_patch_from_materialized_rejects_duplicate_keys_without_sidecar_write(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """Invalid saved materialized keys should not produce mapping links."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        entity_data = {
            "type": "fixed",
            "columns": ["system_id", "site_id", "name"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "site_id",
            "keys": ["name"],
            "materialized": {"enabled": True, "source_state": {"type": "csv"}},
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )
        project_folder = tmp_path / "test_project"
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()
        pd.DataFrame({"system_id": [1, 2], "site_id": [10, 11], "name": ["Duplicate", "Duplicate"]}).to_parquet(
            materialized_folder / "test_entity.parquet", index=False
        )

        response = await authorized_client.patch("/api/v1/projects/test_project/mapping/from-materialized/test_entity")

        assert response.status_code == 400
        assert "share the same encoded key" in response.json()["detail"]
        assert not (project_folder / "test_project-mapping.yml").exists()

    async def test_patch_from_materialized_requires_authentication(self, tmp_path, monkeypatch):
        """The rebuild route rejects unauthenticated requests."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        async def anonymous_app(scope, receive, send) -> None:
            await app(scope, receive, send)

        async with AsyncClient(transport=ASGITransport(app=anonymous_app), base_url="http://testserver") as client:
            response = await client.patch("/api/v1/projects/test_project/mapping/from-materialized/test_entity")

        assert response.status_code == 401

    async def test_patch_from_materialized_rejects_nonmaterialized_entity(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """The administrative rebuild remains limited to materialized entities."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        entity_data = {
            "type": "fixed",
            "columns": ["system_id", "site_id", "name"],
            "values": [[1, 10, "A"]],
            "public_id": "site_id",
            "keys": ["name"],
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        response = await authorized_client.patch("/api/v1/projects/test_project/mapping/from-materialized/test_entity")

        assert response.status_code == 400
        assert "not materialized" in response.json()["detail"]
        assert not (tmp_path / "test_project" / "test_project-mapping.yml").exists()

    async def test_update_entity_values_no_load_directive(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test error when trying to update entity without @load: directive."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with entity that has inline values
        entity_data = {"type": "fixed", "columns": ["id", "name"], "values": [[1, "A"]], "public_id": "id", "keys": ["id"]}
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        # Try to update entity values
        update_data = {"columns": ["id", "name"], "values": [[1, "X"], [2, "Y"]]}
        response = await authorized_client.put("/api/v1/projects/test_project/entities/test_entity/values", json=update_data)
        assert response.status_code == 422
        assert "does not have @load: directive" in response.json()["detail"]

    async def test_get_entity_values_returns_etag(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test GET returns etag for optimistic locking."""

        # Setup temp data directory
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with external values
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        values_dir = project_dir / "materialized"
        values_dir.mkdir()

        # Create parquet file
        df = pd.DataFrame({"system_id": [1, 2], "col1": [10, 20]})
        values_file = values_dir / "test.parquet"
        df.to_parquet(values_file, index=False)

        # Create project
        entity_data = {
            "type": "fixed",
            "columns": ["col1"],
            "values": "@load:materialized/test.parquet",
            "public_id": "col1",
            "keys": ["col1"],
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        # Get values
        response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 200

        data = response.json()
        assert "etag" in data
        assert isinstance(data["etag"], str)
        assert len(data["etag"]) == 32  # MD5 hex

    async def test_update_entity_values_with_matching_etag(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test PUT succeeds with matching If-Match etag."""

        # Setup temp data directory
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with external values
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        values_dir = project_dir / "materialized"
        values_dir.mkdir()

        # Create parquet file
        df = pd.DataFrame({"system_id": [1, 2], "col1": [10, 20]})
        values_file = values_dir / "test.parquet"
        df.to_parquet(values_file, index=False)

        # Create project
        entity_data = {
            "type": "fixed",
            "columns": ["col1"],
            "values": "@load:materialized/test.parquet",
            "public_id": "col1",
            "keys": ["col1"],
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        # Get current etag
        get_response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity/values")
        current_etag = get_response.json()["etag"]

        # Update with matching etag
        update_data = {"columns": ["system_id", "col1"], "values": [[1, 10], [2, 20]]}
        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/test_entity/values", json=update_data, headers={"If-Match": current_etag}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["row_count"] == 2
        assert data["etag"] != current_etag  # New etag after update

    async def test_update_entity_values_with_mismatched_etag(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test PUT fails with 409 when If-Match etag doesn't match."""

        # Setup temp data directory
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with external values
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        values_dir = project_dir / "materialized"
        values_dir.mkdir()

        # Create parquet file
        df = pd.DataFrame({"col1": [1, 2]})
        values_file = values_dir / "test.parquet"
        df.to_parquet(values_file, index=False)

        # Create project
        entity_data = {
            "type": "fixed",
            "columns": ["col1"],
            "values": "@load:materialized/test.parquet",
            "public_id": "col1",
            "keys": ["col1"],
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        # Update with wrong etag
        update_data = {"columns": ["system_id", "col1"], "values": [[1, 10], [2, 20]]}
        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/test_entity/values",
            json=update_data,
            headers={"If-Match": "wrong_etag_12345678901234567890"},
        )
        assert response.status_code == 409
        assert "409 Conflict" in response.json()["detail"]

    async def test_get_entity_values_with_format_negotiation(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test GET with format query parameter (format negotiation)."""

        # Setup temp data directory
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with external values
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        values_dir = project_dir / "materialized"
        values_dir.mkdir()

        # Create parquet file
        df = pd.DataFrame({"system_id": [1, 2], "col1": [10, 20]})
        values_file = values_dir / "test.parquet"
        df.to_parquet(values_file, index=False)

        # Create project
        entity_data = {
            "type": "fixed",
            "columns": ["col1"],
            "values": "@load:materialized/test.parquet",
            "public_id": "col1",
            "keys": ["col1"],
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"test_entity": entity_data},
            },
        )

        # Get values without format param (should return parquet)
        response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 200
        assert response.json()["format"] == "parquet"

        # Get values with format=csv (should return csv in format field)
        response = await authorized_client.get("/api/v1/projects/test_project/entities/test_entity/values?format=csv")
        assert response.status_code == 200
        assert response.json()["format"] == "csv"
        assert response.json()["columns"] == ["system_id", "col1"]  # Data unchanged


# ---------------------------------------------------------------------------
# Partial fixed-row saves: pending mapping_sync response
# ---------------------------------------------------------------------------


def _fail_mapping_save(self, catalog, project_path, expected_version=None):
    """Raise a sidecar write failure after the row write succeeded."""
    raise OSError("sidecar write failed")


def _write_sidecar_entry(project_folder, entity_name: str, *, local_key: str, public_id: str) -> None:
    """Write a bare sidecar entry so a fixed entity is eligible for save-time sync."""
    sidecar_path = project_folder / f"{project_folder.name}-mapping.yml"
    sidecar_path.write_text(
        yaml.safe_dump(
            {
                "version": "2.0",
                "metadata": {
                    "project": project_folder.name,
                    "created_at": "2026-06-15T00:00:00Z",
                    "updated_at": "2026-06-15T00:00:00Z",
                },
                "entities": {
                    entity_name: {
                        "local_key": local_key,
                        "public_id": public_id,
                        "entity_type": "primary",
                        "links": {},
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


class TestPartialMappingSave:
    """Both fixed-row save routes return a pending mapping_sync result."""

    _SITE_ENTITY = {
        "type": "fixed",
        "public_id": "site_id",
        "keys": ["site_code"],
        "columns": ["system_id", "site_id", "site_code"],
        "values": [[1, 10, "A"], [2, 20, "B"]],
    }

    async def test_inline_save_returns_pending_mapping(self, tmp_path, monkeypatch, reset_services, authorized_client):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_folder = tmp_path / "test_project"
        project_folder.mkdir()

        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"site": self._SITE_ENTITY},
            },
        )
        _write_sidecar_entry(project_folder, "site", local_key="site_code", public_id="site_id")

        monkeypatch.setattr(MappingManager, "save", _fail_mapping_save)

        changed = dict(self._SITE_ENTITY)
        changed["values"] = [[1, 11, "A"], [2, 20, "B"]]
        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/site",
            json={"entity_data": changed},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["name"] == "site"
        assert body["etag"]
        assert body["mapping_sync"] is not None
        assert body["mapping_sync"]["status"] == "pending"
        assert body["mapping_sync"]["rows_saved"] is True
        assert body["mapping_sync"]["storage_kind"] == "inline"
        assert body["mapping_sync"]["project"] == "test_project"
        assert body["mapping_sync"]["entity"] == "site"
        assert body["mapping_sync"]["operations"][0]["op"] == "upsert"
        assert body["mapping_sync"]["operations"][0]["target_id"] == 11

    async def test_external_save_returns_pending_mapping(self, tmp_path, monkeypatch, reset_services, authorized_client):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        (project_folder / "materialized").mkdir()

        entity_data = {
            "type": "fixed",
            "public_id": "site_id",
            "keys": ["site_code"],
            "columns": ["system_id", "site_id", "site_code"],
            "values": "@load:materialized/site.parquet",
            "materialized": {"enabled": True},
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"site": entity_data},
            },
        )
        _write_sidecar_entry(project_folder, "site", local_key="site_code", public_id="site_id")

        monkeypatch.setattr(MappingManager, "save", _fail_mapping_save)

        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/site/values",
            json={"columns": ["system_id", "site_id", "site_code"], "values": [[1, 10, "A"]]},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["columns"] == ["system_id", "site_id", "site_code"]
        assert body["row_count"] == 1
        assert body["format"] == "parquet"
        assert body["etag"]
        assert body["mapping_sync"] is not None
        assert body["mapping_sync"]["storage_kind"] == "external"
        assert body["mapping_sync"]["rows_saved"] is True
        assert body["mapping_sync"]["expected_row_version"] == body["etag"]
        assert (project_folder / "materialized" / "site.parquet").exists()

    async def test_pre_write_error_is_not_a_partial_save(self, tmp_path, monkeypatch, reset_services, authorized_client):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_folder = tmp_path / "test_project"
        project_folder.mkdir()

        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"site": self._SITE_ENTITY},
            },
        )
        _write_sidecar_entry(project_folder, "site", local_key="legacy_code", public_id="site_id")

        monkeypatch.setattr(MappingManager, "save", _fail_mapping_save)

        changed = dict(self._SITE_ENTITY)
        changed["values"] = [[1, 11, "A"], [2, 20, "B"]]
        response = await authorized_client.put(
            "/api/v1/projects/test_project/entities/site",
            json={"entity_data": changed},
        )

        assert response.status_code in (400, 422)
