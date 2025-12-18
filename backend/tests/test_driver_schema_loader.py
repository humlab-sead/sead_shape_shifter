"""Tests for driver schema YAML loading."""

import tempfile
from pathlib import Path

import pytest

from src.loaders.driver_metadata import DriverSchema, DriverSchemaRegistry, FieldMetadata


def test_load_from_default_yaml():
    """Test loading schemas from default YAML file."""
    # Clear registry
    DriverSchemaRegistry._schemas.clear()
    DriverSchemaRegistry._loaded = False

    # Load from default location
    DriverSchemaRegistry.load_from_yaml()

    # Check schemas loaded
    schemas = DriverSchemaRegistry.all()
    assert len(schemas) > 0

    # Check specific drivers
    assert "postgresql" in schemas
    assert "access" in schemas
    assert "ucanaccess" in schemas
    assert "sqlite" in schemas
    assert "csv" in schemas


def test_load_from_custom_yaml():
    """Test loading schemas from custom YAML file."""
    yaml_content = """
test_driver:
  display_name: Test Driver
  description: A test driver
  category: database
  fields:
    - name: host
      type: string
      required: true
      default: localhost
      description: Host name
      placeholder: localhost
    
    - name: port
      type: integer
      required: false
      default: 9999
      min_value: 1
      max_value: 65535
"""

    # Save original state
    original_schemas = DriverSchemaRegistry._schemas.copy()
    original_loaded = DriverSchemaRegistry._loaded

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        # Clear registry
        DriverSchemaRegistry._schemas.clear()
        DriverSchemaRegistry._loaded = False

        # Load from custom path
        DriverSchemaRegistry.load_from_yaml(yaml_path)

        # Verify loaded
        schema = DriverSchemaRegistry.get("test_driver")
        assert schema is not None
        assert schema.driver == "test_driver"
        assert schema.display_name == "Test Driver"
        assert schema.category == "database"

        # Verify fields
        assert len(schema.fields) == 2
        host_field = schema.fields[0]
        assert host_field.name == "host"
        assert host_field.type == "string"
        assert host_field.required is True
        assert host_field.default == "localhost"

        port_field = schema.fields[1]
        assert port_field.name == "port"
        assert port_field.type == "integer"
        assert port_field.default == 9999
        assert port_field.min_value == 1
        assert port_field.max_value == 65535
    finally:
        Path(yaml_path).unlink()
        # Restore original state
        DriverSchemaRegistry._schemas = original_schemas
        DriverSchemaRegistry._loaded = original_loaded


def test_postgresql_schema_structure():
    """Test that PostgreSQL schema has correct structure."""
    # Ensure loaded
    DriverSchemaRegistry._ensure_loaded()
    schema = DriverSchemaRegistry.get("postgresql")

    assert schema is not None
    assert schema.driver == "postgresql"
    assert schema.display_name == "PostgreSQL"
    assert schema.category == "database"

    field_names = [f.name for f in schema.fields]
    assert "host" in field_names
    assert "port" in field_names
    assert "database" in field_names
    assert "username" in field_names
    assert "password" in field_names

    # Check port field details
    port_field = next(f for f in schema.fields if f.name == "port")
    assert port_field.type == "integer"
    assert port_field.default == 5432
    assert port_field.min_value == 1
    assert port_field.max_value == 65535


def test_access_schema_structure():
    """Test that Access schema has correct structure."""
    # Ensure loaded
    DriverSchemaRegistry._ensure_loaded()
    schema = DriverSchemaRegistry.get("access")

    assert schema is not None
    assert schema.driver == "access"
    assert schema.display_name == "MS Access"
    assert schema.category == "file"

    field_names = [f.name for f in schema.fields]
    assert "filename" in field_names
    assert "ucanaccess_dir" in field_names

    # Check ucanaccess_dir field
    ucan_field = next(f for f in schema.fields if f.name == "ucanaccess_dir")
    assert ucan_field.required is False
    assert ucan_field.default == "lib/ucanaccess"


def test_lazy_loading():
    """Test that schemas are loaded lazily on first access."""
    # Clear registry
    DriverSchemaRegistry._schemas.clear()
    DriverSchemaRegistry._loaded = False

    # Verify not loaded yet
    assert not DriverSchemaRegistry._loaded

    # Access triggers loading
    schema = DriverSchemaRegistry.get("postgresql")

    # Verify loaded
    assert DriverSchemaRegistry._loaded
    assert schema is not None


def test_reload_schemas():
    """Test reloading schemas from YAML."""
    # Load once
    DriverSchemaRegistry.load_from_yaml()
    first_count = len(DriverSchemaRegistry.all())

    # Load again
    DriverSchemaRegistry.load_from_yaml()
    second_count = len(DriverSchemaRegistry.all())

    # Should have same count
    assert first_count == second_count


def test_missing_yaml_file():
    """Test error when YAML file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        DriverSchemaRegistry.load_from_yaml("/nonexistent/path/schemas.yml")


def test_empty_yaml_file():
    """Test error with empty YAML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("")
        yaml_path = f.name

    try:
        with pytest.raises(ValueError, match="Empty or invalid"):
            DriverSchemaRegistry.load_from_yaml(yaml_path)
    finally:
        Path(yaml_path).unlink()
