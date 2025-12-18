"""Tests for driver schema API endpoint."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_list_drivers(client):
    """Test listing available drivers and their schemas."""
    response = client.get("/api/v1/data-sources/drivers")

    assert response.status_code == 200
    data = response.json()

    # Should return dictionary of drivers
    assert isinstance(data, dict)
    assert len(data) > 0

    # Check PostgreSQL driver
    assert "postgresql" in data
    pg = data["postgresql"]
    assert pg["driver"] == "postgresql"
    assert pg["display_name"] == "PostgreSQL"
    assert pg["category"] == "database"
    assert isinstance(pg["fields"], list)
    assert len(pg["fields"]) > 0

    # Check fields
    field_names = [f["name"] for f in pg["fields"]]
    assert "host" in field_names
    assert "port" in field_names
    assert "database" in field_names
    assert "username" in field_names
    assert "password" in field_names

    # Check field metadata
    host_field = next(f for f in pg["fields"] if f["name"] == "host")
    assert host_field["type"] == "string"
    assert host_field["required"] is True
    assert host_field["default"] == "localhost"

    port_field = next(f for f in pg["fields"] if f["name"] == "port")
    assert port_field["type"] == "integer"
    assert port_field["min_value"] == 1
    assert port_field["max_value"] == 65535


def test_ucanaccess_driver_schema(client):
    """Test MS Access driver schema."""
    response = client.get("/api/v1/data-sources/drivers")

    assert response.status_code == 200
    data = response.json()

    assert "ucanaccess" in data
    access = data["ucanaccess"]
    assert access["driver"] == "ucanaccess"
    assert access["display_name"] == "MS Access"
    assert access["category"] == "file"

    field_names = [f["name"] for f in access["fields"]]
    assert "filename" in field_names
    assert "ucanaccess_dir" in field_names

    # Check filename field
    filename_field = next(f for f in access["fields"] if f["name"] == "filename")
    assert filename_field["type"] == "file_path"
    assert filename_field["required"] is True

    # Check ucanaccess_dir field
    ucan_field = next(f for f in access["fields"] if f["name"] == "ucanaccess_dir")
    assert ucan_field["required"] is False
    assert ucan_field["default"] == "lib/ucanaccess"


def test_all_drivers_have_required_metadata(client):
    """Test that all drivers have required metadata."""
    response = client.get("/api/v1/data-sources/drivers")

    assert response.status_code == 200
    data = response.json()

    for driver_name, driver_schema in data.items():
        # Required fields in schema
        assert "driver" in driver_schema
        assert "display_name" in driver_schema
        assert "description" in driver_schema
        assert "category" in driver_schema
        assert "fields" in driver_schema

        # Category must be valid
        assert driver_schema["category"] in ["database", "file"]

        # Each field must have required metadata
        for field in driver_schema["fields"]:
            assert "name" in field
            assert "type" in field
            assert "required" in field
            assert field["type"] in ["string", "integer", "boolean", "password", "file_path"]
