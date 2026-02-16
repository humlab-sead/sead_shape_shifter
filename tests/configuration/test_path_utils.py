"""Tests for path resolution in BaseResolver class."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.configuration.config import SubConfigResolver


# Use SubConfigResolver as a concrete implementation to test BaseResolver._resolve_path
class TestBaseResolverPathResolution:
    """Test BaseResolver._resolve_path() method via SubConfigResolver."""

    @pytest.fixture
    def resolver(self) -> SubConfigResolver:
        """Create a SubConfigResolver instance for testing path resolution."""
        return SubConfigResolver()

    def test_resolve_absolute_path_unchanged(self, resolver: SubConfigResolver) -> None:
        """Test that absolute paths are returned as-is."""
        result = resolver._resolve_path("/absolute/path/file.txt")
        assert result == "/absolute/path/file.txt"

    def test_resolve_with_env_var_and_absolute(self, resolver: SubConfigResolver) -> None:
        """Test env var expansion resulting in absolute path."""
        os.environ["ABS_PATH"] = "/absolute/base"
        result = resolver._resolve_path("${ABS_PATH}/file.txt")
        assert result == "/absolute/base/file.txt"

    def test_resolve_relative_without_base_path(self, resolver: SubConfigResolver) -> None:
        """Test relative path without base_path returns path as-is."""
        result = resolver._resolve_path("relative/path/file.txt")
        assert result == "relative/path/file.txt"

    def test_resolve_relative_with_base_path(self, resolver: SubConfigResolver, tmp_path: Path) -> None:
        """Test relative path is resolved against base_path."""
        base = tmp_path / "project"
        result = resolver._resolve_path("data/file.txt", base_path=base)
        expected = str(base / "data/file.txt")
        assert result == expected

    def test_resolve_current_dir_relative(self, resolver: SubConfigResolver, tmp_path: Path) -> None:
        """Test resolution of ./ relative paths."""
        base = tmp_path / "config"
        result = resolver._resolve_path("./local.yml", base_path=base)
        expected = str(base / "local.yml")
        assert result == expected

    def test_resolve_parent_dir_relative(self, resolver: SubConfigResolver, tmp_path: Path) -> None:
        """Test resolution of ../ parent directory paths."""
        base = tmp_path / "project" / "config"
        result = resolver._resolve_path("../data/file.csv", base_path=base)
        expected = str(base / "../data/file.csv")
        assert result == expected

    def test_resolve_env_var_with_relative_and_base(self, resolver: SubConfigResolver, tmp_path: Path) -> None:
        """Test env var expansion with absolute path from base context."""
        os.environ["REL_DIR"] = str(tmp_path / "project" / "shared")
        base = tmp_path / "project"
        result = resolver._resolve_path("${REL_DIR}/file.txt", base_path=base)
        expected = str(tmp_path / "project" / "shared" / "file.txt")
        assert result == expected

    def test_resolve_empty_string(self, resolver: SubConfigResolver) -> None:
        """Test that empty string is returned as-is."""
        result = resolver._resolve_path("")
        assert result == ""

    def test_resolve_none_base_path(self, resolver: SubConfigResolver) -> None:
        """Test that None base_path is handled correctly."""
        result = resolver._resolve_path("relative/path.txt", base_path=None)
        assert result == "relative/path.txt"

    def test_resolve_with_unresolved_vars_no_raise(self, resolver: SubConfigResolver) -> None:
        """Test unresolved env vars with raise_if_missing=False."""
        os.environ.pop("MISSING_VAR", None)
        result = resolver._resolve_path("${MISSING_VAR}/file.txt", raise_if_missing=False)
        # Missing var replaced with empty string
        assert result == "/file.txt"

    def test_resolve_with_unresolved_vars_raise(self, resolver: SubConfigResolver) -> None:
        """Test unresolved env vars with raise_if_missing=True raises error."""
        os.environ.pop("MISSING_VAR", None)
        with pytest.raises(ValueError, match="Unresolved environment variables"):
            resolver._resolve_path("${MISSING_VAR}/file.txt", raise_if_missing=True)

    def test_resolve_with_multiple_unresolved_vars_raise(self, resolver: SubConfigResolver) -> None:
        """Test error message includes all unresolved variable names."""
        os.environ.pop("VAR1", None)
        os.environ.pop("VAR2", None)
        with pytest.raises(ValueError, match="VAR1.*VAR2"):
            resolver._resolve_path("${VAR1}/${VAR2}/file.txt", raise_if_missing=True)


class TestPathResolverIntegration:
    """Integration tests for common use cases."""

    @pytest.fixture
    def resolver(self) -> SubConfigResolver:
        """Create a SubConfigResolver instance for testing path resolution."""
        return SubConfigResolver()

    def test_global_data_dir_pattern(self, resolver: SubConfigResolver, tmp_path: Path) -> None:
        """Test typical DATA_DIR usage pattern."""
        os.environ["DATA_DIR"] = str(tmp_path / "shared" / "data")
        result = resolver._resolve_path("${DATA_DIR}/lookup.csv")
        expected = str(tmp_path / "shared" / "data" / "lookup.csv")
        assert result == expected

    def test_include_directive_pattern(self, resolver: SubConfigResolver, tmp_path: Path) -> None:
        """Test typical @include: directive usage pattern."""
        os.environ["DATA_SOURCE_DIR"] = str(tmp_path / "shared" / "sources")
        config_dir = tmp_path / "project"
        result = resolver._resolve_path("${DATA_SOURCE_DIR}/sead-options.yml", base_path=config_dir)
        expected = str(tmp_path / "shared" / "sources" / "sead-options.yml")
        assert result == expected

    def test_local_relative_include(self, resolver: SubConfigResolver, tmp_path: Path) -> None:
        """Test local relative @include: pattern."""
        project_dir = tmp_path / "project"
        result = resolver._resolve_path("./reconciliation.yml", base_path=project_dir)
        expected = str(project_dir / "reconciliation.yml")
        assert result == expected

    def test_shared_resource_pattern(self, resolver: SubConfigResolver, tmp_path: Path) -> None:
        """Test accessing shared resources from nested project."""
        project_dir = tmp_path / "projects" / "arbodat" / "arbodat-test"
        result = resolver._resolve_path("../../../shared/data-sources/config.yml", base_path=project_dir)
        expected = str(project_dir / "../../../shared/data-sources/config.yml")
        assert result == expected

    def test_windows_style_path(self, resolver: SubConfigResolver) -> None:
        """Test that Windows-style absolute paths are recognized."""
        # Note: Path.is_absolute() handles platform differences
        if os.name == "nt":
            result = resolver._resolve_path("C:\\Users\\data\\file.txt")
            assert result == "C:\\Users\\data\\file.txt"

    def test_mixed_env_vars_and_paths(self, resolver: SubConfigResolver, tmp_path: Path) -> None:
        """Test complex pattern with multiple env vars and relative paths."""
        os.environ["BASE_DIR"] = str(tmp_path)
        os.environ["PROJECT_NAME"] = "myproject"
        result = resolver._resolve_path("${BASE_DIR}/${PROJECT_NAME}/data/file.csv")
        expected = str(tmp_path / "myproject" / "data" / "file.csv")
        assert result == expected


class TestPathResolverEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def resolver(self) -> SubConfigResolver:
        """Create a SubConfigResolver instance for testing path resolution."""
        return SubConfigResolver()

    def test_resolve_with_special_characters(self, resolver: SubConfigResolver) -> None:
        """Test paths with special characters."""
        os.environ["SPECIAL_DIR"] = "/path/with spaces/and-dashes"
        result = resolver._resolve_path("${SPECIAL_DIR}/file (1).txt")
        assert result == "/path/with spaces/and-dashes/file (1).txt"

    def test_resolve_with_unicode(self, resolver: SubConfigResolver) -> None:
        """Test paths with unicode characters."""
        os.environ["UNICODE_DIR"] = "/путь/路径/パス"
        result = resolver._resolve_path("${UNICODE_DIR}/файл.txt")
        assert result == "/путь/路径/パス/файл.txt"

    def test_resolve_empty_env_var_value(self, resolver: SubConfigResolver) -> None:
        """Test behavior when env var exists but is empty."""
        os.environ["EMPTY_VAR"] = ""
        result = resolver._resolve_path("${EMPTY_VAR}/file.txt")
        assert result == "/file.txt"

    def test_resolve_partial_env_var_syntax(self, resolver: SubConfigResolver) -> None:
        """Test incomplete env var syntax is left unchanged."""
        # Missing closing brace - should be left as-is
        result = resolver._resolve_path("${INCOMPLETE/file.txt")
        assert result == "${INCOMPLETE/file.txt"

    def test_resolve_dollar_without_braces(self, resolver: SubConfigResolver) -> None:
        """Test that $ without {} is left unchanged."""
        result = resolver._resolve_path("$HOME/file.txt")
        assert result == "$HOME/file.txt"


# Cleanup after tests
@pytest.fixture(autouse=True)
def cleanup_env_vars():
    """Clean up test environment variables after each test."""
    # Store original env vars
    original_env = os.environ.copy()

    yield

    # Restore original env vars
    test_vars = [
        "TEST_VAR",
        "TEST_DIR",
        "TEST_SUBDIR",
        "NONEXISTENT_VAR",
        "ABS_PATH",
        "REL_DIR",
        "MISSING_VAR",
        "VAR1",
        "VAR2",
        "DATA_DIR",
        "DATA_SOURCE_DIR",
        "BASE_DIR",
        "PROJECT_NAME",
        "SPECIAL_DIR",
        "UNICODE_DIR",
        "EMPTY_VAR",
        "OUTER",
        "INCOMPLETE",
    ]
    for var in test_vars:
        os.environ.pop(var, None)

    # Restore any original values
    for key, value in original_env.items():
        os.environ[key] = value
