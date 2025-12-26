"""Additional unit tests for utility functions in src/utility.py.

Tests cover functions that weren't previously tested:
- normalize_text
- recursive_update
- recursive_filter_dict
- dotset
- env2dict
- replace_env_vars
- Registry class
- create_db_uri
- get_connection_uri
- load_resource_yaml
- resolve_specification
"""

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.utility import (
    Registry,
    create_db_uri,
    dotset,
    env2dict,
    normalize_text,
    recursive_filter_dict,
    recursive_update,
    replace_env_vars,
    resolve_specification,
)


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_normalize_basic_text(self):
        """Test normalizing basic ASCII text."""
        result = normalize_text("Hello World")
        assert result == "hello world"

    def test_normalize_empty_string(self):
        """Test normalizing empty string."""
        result = normalize_text("")
        assert result == ""

    def test_normalize_none_returns_empty(self):
        """Test that None returns empty string."""
        result = normalize_text(None)  # type: ignore
        assert result == ""

    def test_normalize_removes_accents(self):
        """Test that accents are removed."""
        result = normalize_text("Café")
        assert result == "cafe"

        result = normalize_text("Naïve")
        assert result == "naive"

    def test_normalize_german_umlauts(self):
        """Test German umlauts are normalized."""
        result = normalize_text("Über")
        assert result == "uber"

        result = normalize_text("Schön")
        assert result == "schon"

    def test_normalize_scandinavian_characters(self):
        """Test Scandinavian characters."""
        result = normalize_text("Åsa")
        assert result == "asa"

        # Note: Ø is not fully decomposable using NFD, so it remains as ø
        result = normalize_text("Øresund")
        assert result == "øresund"

    def test_normalize_spanish_accents(self):
        """Test Spanish accented characters."""
        result = normalize_text("Señor")
        assert result == "senor"

        result = normalize_text("Niño")
        assert result == "nino"

    def test_normalize_french_accents(self):
        """Test French accented characters."""
        result = normalize_text("Élève")
        assert result == "eleve"

        result = normalize_text("Hôtel")
        assert result == "hotel"

    def test_normalize_mixed_case_and_accents(self):
        """Test mixed case with accents."""
        result = normalize_text("CAFÉ")
        assert result == "cafe"

        result = normalize_text("ÉlÈvE")
        assert result == "eleve"

    def test_normalize_preserves_spaces(self):
        """Test that spaces are preserved."""
        result = normalize_text("Hello World Test")
        assert result == "hello world test"

    def test_normalize_preserves_numbers(self):
        """Test that numbers are preserved."""
        result = normalize_text("Test123")
        assert result == "test123"

    def test_normalize_preserves_special_chars(self):
        """Test that special characters are preserved."""
        result = normalize_text("Test-Name_2024")
        assert result == "test-name_2024"


class TestRecursiveUpdate:
    """Tests for recursive_update function."""

    def test_basic_update(self):
        """Test basic dictionary update."""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}

        result = recursive_update(d1, d2)

        assert result == {"a": 1, "b": 3, "c": 4}
        assert result is d1  # Should modify in place

    def test_nested_dict_update(self):
        """Test updating nested dictionaries."""
        d1 = {"a": {"x": 1, "y": 2}, "b": 3}
        d2 = {"a": {"y": 20, "z": 30}}

        result = recursive_update(d1, d2)

        assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3}

    def test_deep_nested_update(self):
        """Test deeply nested dictionary update."""
        d1 = {"level1": {"level2": {"level3": {"value": 1}}}}
        d2 = {"level1": {"level2": {"level3": {"value": 2, "new": 3}}}}

        result = recursive_update(d1, d2)

        assert result["level1"]["level2"]["level3"]["value"] == 2
        assert result["level1"]["level2"]["level3"]["new"] == 3

    def test_update_with_non_dict_values(self):
        """Test update when values are not dicts."""
        d1 = {"a": {"x": 1}, "b": [1, 2, 3]}
        d2 = {"a": {"x": 2}, "b": [4, 5, 6]}

        result = recursive_update(d1, d2)

        # Non-dict values should be replaced, not merged
        assert result["b"] == [4, 5, 6]

    def test_empty_dict_update(self):
        """Test updating with empty dictionary."""
        d1 = {"a": 1, "b": 2}
        d2 = {}

        result = recursive_update(d1, d2)

        assert result == {"a": 1, "b": 2}

    def test_update_empty_dict(self):
        """Test updating empty dictionary."""
        d1 = {}
        d2 = {"a": 1, "b": 2}

        result = recursive_update(d1, d2)

        assert result == {"a": 1, "b": 2}


class TestRecursiveFilterDict:
    """Tests for recursive_filter_dict function."""

    def test_exclude_mode_basic(self):
        """Test basic exclude mode filtering."""
        data = {"a": 1, "b": 2, "c": 3}
        filter_keys = {"b"}

        result = recursive_filter_dict(data, filter_keys, filter_mode="exclude")

        assert result == {"a": 1, "c": 3}

    def test_keep_mode_basic(self):
        """Test basic keep mode filtering."""
        data = {"a": 1, "b": 2, "c": 3}
        filter_keys = {"a", "c"}

        result = recursive_filter_dict(data, filter_keys, filter_mode="keep")

        assert result == {"a": 1, "c": 3}

    def test_exclude_mode_nested(self):
        """Test exclude mode with nested dicts."""
        data = {"a": {"x": 1, "y": 2}, "b": {"x": 3, "z": 4}}
        filter_keys = {"y", "z"}

        result = recursive_filter_dict(data, filter_keys, filter_mode="exclude")

        assert result == {"a": {"x": 1}, "b": {"x": 3}}

    def test_keep_mode_nested(self):
        """Test keep mode with nested dicts."""
        data = {"a": {"x": 1, "y": 2}, "b": {"x": 3, "z": 4}}
        filter_keys = {"x", "a", "b"}  # Need to keep top-level keys too

        result = recursive_filter_dict(data, filter_keys, filter_mode="keep")

        assert result == {"a": {"x": 1}, "b": {"x": 3}}

    def test_non_dict_values_preserved(self):
        """Test that non-dict values are preserved."""
        data = {"a": [1, 2, 3], "b": "string", "c": 42}
        filter_keys = {"b"}

        result = recursive_filter_dict(data, filter_keys, filter_mode="exclude")

        assert result == {"a": [1, 2, 3], "c": 42}

    def test_deeply_nested_filtering(self):
        """Test filtering deeply nested structures."""
        data = {"level1": {"level2": {"level3": {"keep": 1, "remove": 2}}}}
        filter_keys = {"remove"}

        result = recursive_filter_dict(data, filter_keys, filter_mode="exclude")

        assert result == {"level1": {"level2": {"level3": {"keep": 1}}}}


class TestDotset:
    """Tests for dotset function."""

    def test_basic_dotset(self):
        """Test basic dot notation set."""
        data = {}
        dotset(data, "a.b.c", 42)

        assert data == {"a": {"b": {"c": 42}}}

    def test_dotset_existing_path(self):
        """Test setting value in existing path."""
        data = {"a": {"b": {"c": 1}}}
        dotset(data, "a.b.c", 2)

        assert data["a"]["b"]["c"] == 2

    def test_dotset_partial_path_exists(self):
        """Test setting when partial path exists."""
        data = {"a": {"x": 1}}
        dotset(data, "a.b.c", 42)

        assert data == {"a": {"x": 1, "b": {"c": 42}}}

    def test_dotset_with_colon_notation(self):
        """Test colon notation is converted to dots."""
        data = {}
        dotset(data, "a:b:c", 42)

        assert data == {"a": {"b": {"c": 42}}}

    def test_dotset_single_key(self):
        """Test setting single key."""
        data = {}
        dotset(data, "key", "value")

        assert data == {"key": "value"}

    def test_dotset_returns_dict(self):
        """Test that dotset returns the modified dict."""
        data = {}
        result = dotset(data, "a.b", 1)

        assert result is data
        assert result == {"a": {"b": 1}}

    def test_dotset_empty_path_segments(self):
        """Test that empty path segments are skipped."""
        data = {}
        dotset(data, "a..b", 42)

        assert data == {"a": {"b": 42}}


class TestEnv2dict:
    """Tests for env2dict function."""

    def test_env2dict_basic(self):
        """Test basic environment variable loading."""
        with patch.dict(os.environ, {"TEST_DB_HOST": "localhost", "TEST_DB_PORT": "5432"}):
            result = env2dict("TEST", lower_key=True)

            assert "db" in result
            assert result["db"]["host"] == "localhost"
            assert result["db"]["port"] == "5432"

    def test_env2dict_no_prefix_match(self):
        """Test when no environment variables match prefix."""
        with patch.dict(os.environ, {"OTHER_VAR": "value"}, clear=True):
            result = env2dict("TEST", lower_key=True)

            assert result == {}

    def test_env2dict_case_insensitive(self):
        """Test case insensitive prefix matching."""
        with patch.dict(os.environ, {"TEST_VAR": "value"}):
            result = env2dict("test", lower_key=True)

            assert "var" in result
            assert result["var"] == "value"

    def test_env2dict_without_lowercase(self):
        """Test without lowercasing keys."""
        with patch.dict(os.environ, {"TEST_DB_HOST": "localhost"}):
            result = env2dict("TEST", lower_key=False)

            assert "DB" in result

    def test_env2dict_existing_dict(self):
        """Test adding to existing dict."""
        existing = {"existing": "value"}
        with patch.dict(os.environ, {"TEST_NEW": "data"}):
            result = env2dict("TEST", data=existing, lower_key=True)

            assert result["existing"] == "value"
            assert result["new"] == "data"
            assert result is existing

    def test_env2dict_empty_prefix(self):
        """Test with empty prefix returns empty dict."""
        result = env2dict("", lower_key=True)
        assert result == {}

    def test_env2dict_nested_paths(self):
        """Test that underscores create nested paths."""
        with patch.dict(os.environ, {"CONFIG_DB_CONNECTION_HOST": "localhost"}):
            result = env2dict("CONFIG", lower_key=True)

            assert result == {"db": {"connection": {"host": "localhost"}}}


class TestReplaceEnvVars:
    """Tests for replace_env_vars function."""

    def test_replace_env_var_in_string(self):
        """Test replacing environment variable in string."""
        with patch.dict(os.environ, {"TEST_VAR": "replaced_value"}):
            result = replace_env_vars("${TEST_VAR}")

            assert result == "replaced_value"

    def test_replace_env_var_not_set(self):
        """Test replacing environment variable that is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = replace_env_vars("${NONEXISTENT}")

            assert result == ""

    def test_replace_in_dict(self):
        """Test replacing environment variables in dict."""
        with patch.dict(os.environ, {"DB_HOST": "localhost", "DB_PORT": "5432"}):
            data = {"host": "${DB_HOST}", "port": "${DB_PORT}", "name": "testdb"}

            result = replace_env_vars(data)

            assert result == {"host": "localhost", "port": "5432", "name": "testdb"}

    def test_replace_in_nested_dict(self):
        """Test replacing in nested dict."""
        with patch.dict(os.environ, {"API_KEY": "secret123"}):
            data = {"config": {"api": {"key": "${API_KEY}"}}}

            result = replace_env_vars(data)

            assert result["config"]["api"]["key"] == "secret123"

    def test_replace_in_list(self):
        """Test replacing environment variables in list."""
        with patch.dict(os.environ, {"VAR1": "value1", "VAR2": "value2"}):
            data = ["${VAR1}", "${VAR2}", "static"]

            result = replace_env_vars(data)

            assert result == ["value1", "value2", "static"]

    def test_replace_mixed_structure(self):
        """Test replacing in mixed dict/list structure."""
        with patch.dict(os.environ, {"HOST": "localhost"}):
            data = {"servers": [{"host": "${HOST}", "port": 8080}]}

            result = replace_env_vars(data)

            assert result["servers"][0]["host"] == "localhost"

    def test_non_env_var_strings_unchanged(self):
        """Test that regular strings are not modified."""
        data = {"key": "normal_value", "another": "value${incomplete"}

        result = replace_env_vars(data)

        assert result == data

    def test_partial_env_var_syntax_unchanged(self):
        """Test that partial env var syntax is not replaced."""
        data = "${incomplete"

        result = replace_env_vars(data)

        assert result == "${incomplete"


class TestRegistry:
    """Tests for Registry class."""

    def test_registry_register_with_string_key(self):
        """Test registering with string key."""

        class TestRegistry(Registry):
            items: dict[str, Any] = {}

        @TestRegistry.register(key="test_key")
        class TestClass:
            pass

        assert "test_key" in TestRegistry.items
        assert TestRegistry.items["test_key"] == TestClass

    def test_registry_register_with_list_keys(self):
        """Test registering with multiple keys."""

        class TestRegistry(Registry):
            items: dict[str, Any] = {}

        @TestRegistry.register(key=["key1", "key2", "key3"])
        class TestClass:
            pass

        assert "key1" in TestRegistry.items
        assert "key2" in TestRegistry.items
        assert "key3" in TestRegistry.items
        assert TestRegistry.items["key1"] == TestClass

    def test_registry_get(self):
        """Test getting registered item."""

        class TestRegistry(Registry):
            items: dict[str, Any] = {}

        @TestRegistry.register(key="fetch_me")
        class TestClass:
            value = 42

        retrieved = TestRegistry.get("fetch_me")
        assert retrieved.value == 42

    def test_registry_get_raises_for_unknown_key(self):
        """Test that get raises KeyError for unknown key."""

        class TestRegistry(Registry):
            items: dict[str, Any] = {}

        with pytest.raises(KeyError, match="preprocessor .* is not registered"):
            TestRegistry.get("nonexistent")

    def test_registry_is_registered(self):
        """Test is_registered method."""

        class TestRegistry(Registry):
            items: dict[str, Any] = {}

        @TestRegistry.register(key="exists")
        class TestClass:
            pass

        assert TestRegistry.is_registered("exists") is True
        assert TestRegistry.is_registered("does_not_exist") is False

    def test_registry_raises_on_duplicate_key(self):
        """Test that duplicate key raises KeyError."""

        class TestRegistry(Registry):
            items: dict[str, Any] = {}

        @TestRegistry.register(key="duplicate")
        class TestClass1:
            pass

        with pytest.raises(KeyError, match="Overriding existing registration"):

            @TestRegistry.register(key="duplicate")
            class TestClass2:
                pass

    def test_registry_key_property_added(self):
        """Test that _registry_key property is added to class."""

        class TestRegistry(Registry):
            items: dict[str, Any] = {}

        @TestRegistry.register(key="test")
        class TestClass:
            pass

        instance = TestClass()
        assert instance.key == "test"


class TestCreateDbUri:
    """Tests for create_db_uri function."""

    def test_create_db_uri_basic(self):
        """Test creating basic database URI."""
        uri = create_db_uri(host="localhost", port=5432, user="testuser", dbname="testdb")

        assert uri == "postgresql+psycopg://testuser@localhost:5432/testdb"

    def test_create_db_uri_custom_driver(self):
        """Test creating URI with custom driver."""
        uri = create_db_uri(host="localhost", port=3306, user="root", dbname="mydb", driver="mysql+pymysql")

        assert uri == "mysql+pymysql://root@localhost:3306/mydb"

    def test_create_db_uri_port_as_string(self):
        """Test that port can be provided as string."""
        uri = create_db_uri(host="db.example.com", port="5433", user="admin", dbname="proddb")

        assert uri == "postgresql+psycopg://admin@db.example.com:5433/proddb"

    def test_create_db_uri_different_hosts(self):
        """Test URIs with different host names."""
        uri1 = create_db_uri(host="127.0.0.1", port=5432, user="user", dbname="db1")
        uri2 = create_db_uri(host="remote.server.com", port=5432, user="user", dbname="db2")

        assert "127.0.0.1" in uri1
        assert "remote.server.com" in uri2


class TestResolveSpecification:
    """Tests for resolve_specification function."""

    def test_resolve_specification_dict(self):
        """Test resolving specification when already a dict."""
        spec = {"key": "test", "id_field": "id", "label_field": "name"}

        result = resolve_specification(spec)

        assert result == spec
        assert result is spec

    def test_resolve_specification_none(self):
        """Test resolving None returns default specification."""
        result = resolve_specification(None)

        assert result["key"] == "unknown"
        assert result["id_field"] == "id"
        assert result["label_field"] == "name"
        assert result["properties"] == []

    def test_resolve_specification_string_resource(self):
        """Test resolving string resource key."""
        mock_yaml_data = {"key": "loaded", "id_field": "resource_id"}

        with patch("builtins.open", mock_open(read_data="key: loaded\nid_field: resource_id")):
            with patch("yaml.safe_load", return_value=mock_yaml_data):
                with patch("os.path.exists", return_value=True):
                    result = resolve_specification("resource_key")

                    assert result == mock_yaml_data

    def test_resolve_specification_string_not_found(self):
        """Test resolving non-existent resource returns None."""
        with patch("os.path.exists", return_value=False):
            result = resolve_specification("nonexistent")

            # When resource is not found, load_resource_yaml returns None
            # which then gets passed through resolve_specification's None branch
            assert result is None or result["key"] == "unknown"


class TestGetConnectionUri:
    """Tests for get_connection_uri function (requires mock connection)."""

    def test_get_connection_uri(self):
        """Test getting connection URI from connection object."""
        # Mock a psycopg connection
        mock_conn = MagicMock()
        mock_conn.get_dsn_parameters.return_value = {
            "user": "testuser",
            "host": "localhost",
            "port": "5432",
            "dbname": "testdb",
        }

        from src.utility import get_connection_uri

        uri = get_connection_uri(mock_conn)

        assert uri == "postgresql://testuser@localhost:5432/testdb"

    def test_get_connection_uri_different_values(self):
        """Test with different connection parameters."""
        mock_conn = MagicMock()
        mock_conn.get_dsn_parameters.return_value = {
            "user": "admin",
            "host": "db.example.com",
            "port": "5433",
            "dbname": "production",
        }

        from src.utility import get_connection_uri

        uri = get_connection_uri(mock_conn)

        assert uri == "postgresql://admin@db.example.com:5433/production"
