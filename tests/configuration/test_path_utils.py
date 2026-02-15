"""Tests for src.configuration.path_utils module."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.configuration.path_utils import PathResolver


class TestPathResolverEnvVarExpansion:
    """Test environment variable expansion in paths."""

    def test_expand_env_vars_single_variable(self) -> None:
        """Test expansion of a single environment variable."""
        os.environ["TEST_VAR"] = "/some/path"
        result = PathResolver._expand_env_vars("${TEST_VAR}/file.txt")
        assert result == "/some/path/file.txt"

    def test_expand_env_vars_multiple_variables(self) -> None:
        """Test expansion of multiple environment variables in one path."""
        os.environ["TEST_DIR"] = "/base"
        os.environ["TEST_SUBDIR"] = "subdir"
        result = PathResolver._expand_env_vars("${TEST_DIR}/${TEST_SUBDIR}/file.txt")
        assert result == "/base/subdir/file.txt"

    def test_expand_env_vars_missing_variable(self) -> None:
        """Test that missing env vars are replaced with empty string."""
        # Ensure variable doesn't exist
        os.environ.pop("NONEXISTENT_VAR", None)
        result = PathResolver._expand_env_vars("${NONEXISTENT_VAR}/file.txt")
        assert result == "/file.txt"

    def test_expand_env_vars_no_variables(self) -> None:
        """Test that paths without variables are unchanged."""
        result = PathResolver._expand_env_vars("/plain/path/file.txt")
        assert result == "/plain/path/file.txt"

    def test_expand_env_vars_empty_string(self) -> None:
        """Test expansion with empty string."""
        result = PathResolver._expand_env_vars("")
        assert result == ""

    def test_expand_env_vars_only_variable(self) -> None:
        """Test expansion when entire string is just a variable."""
        os.environ["TEST_DIR"] = "/complete/path"
        result = PathResolver._expand_env_vars("${TEST_DIR}")
        assert result == "/complete/path"


class TestPathResolverResolveMethod:
    """Test PathResolver.resolve() method."""

    def test_resolve_absolute_path_unchanged(self) -> None:
        """Test that absolute paths are returned as-is."""
        result = PathResolver.resolve("/absolute/path/file.txt")
        assert result == "/absolute/path/file.txt"

    def test_resolve_with_env_var_and_absolute(self) -> None:
        """Test env var expansion resulting in absolute path."""
        os.environ["ABS_PATH"] = "/absolute/base"
        result = PathResolver.resolve("${ABS_PATH}/file.txt")
        assert result == "/absolute/base/file.txt"

    def test_resolve_relative_without_base_path(self) -> None:
        """Test relative path without base_path returns path as-is."""
        result = PathResolver.resolve("relative/path/file.txt")
        assert result == "relative/path/file.txt"

    def test_resolve_relative_with_base_path(self, tmp_path: Path) -> None:
        """Test relative path is resolved against base_path."""
        base = tmp_path / "project"
        result = PathResolver.resolve("data/file.txt", base_path=base)
        expected = str(base / "data/file.txt")
        assert result == expected

    def test_resolve_current_dir_relative(self, tmp_path: Path) -> None:
        """Test resolution of ./ relative paths."""
        base = tmp_path / "config"
        result = PathResolver.resolve("./local.yml", base_path=base)
        expected = str(base / "local.yml")
        assert result == expected

    def test_resolve_parent_dir_relative(self, tmp_path: Path) -> None:
        """Test resolution of ../ parent directory paths."""
        base = tmp_path / "project" / "config"
        result = PathResolver.resolve("../data/file.csv", base_path=base)
        expected = str(base / "../data/file.csv")
        assert result == expected

    def test_resolve_env_var_with_relative_and_base(self, tmp_path: Path) -> None:
        """Test env var expansion with relative path and base_path."""
        os.environ["REL_DIR"] = "shared"
        base = tmp_path / "project"
        result = PathResolver.resolve("${REL_DIR}/file.txt", base_path=base)
        expected = str(base / "shared/file.txt")
        assert result == expected

    def test_resolve_empty_string(self) -> None:
        """Test that empty string is returned as-is."""
        result = PathResolver.resolve("")
        assert result == ""

    def test_resolve_none_base_path(self) -> None:
        """Test that None base_path is handled correctly."""
        result = PathResolver.resolve("relative/path.txt", base_path=None)
        assert result == "relative/path.txt"

    def test_resolve_with_unresolved_vars_no_raise(self) -> None:
        """Test unresolved env vars with raise_if_missing=False."""
        os.environ.pop("MISSING_VAR", None)
        result = PathResolver.resolve("${MISSING_VAR}/file.txt", raise_if_missing=False)
        # Missing var replaced with empty string
        assert result == "/file.txt"

    def test_resolve_with_unresolved_vars_raise(self) -> None:
        """Test unresolved env vars with raise_if_missing=True raises error."""
        os.environ.pop("MISSING_VAR", None)
        with pytest.raises(ValueError, match="Unresolved environment variables"):
            PathResolver.resolve("${MISSING_VAR}/file.txt", raise_if_missing=True)

    def test_resolve_with_multiple_unresolved_vars_raise(self) -> None:
        """Test error message includes all unresolved variable names."""
        os.environ.pop("VAR1", None)
        os.environ.pop("VAR2", None)
        with pytest.raises(ValueError, match="VAR1.*VAR2"):
            PathResolver.resolve("${VAR1}/${VAR2}/file.txt", raise_if_missing=True)


class TestPathResolverIntegration:
    """Integration tests for common use cases."""

    def test_global_data_dir_pattern(self, tmp_path: Path) -> None:
        """Test typical GLOBAL_DATA_DIR usage pattern."""
        os.environ["GLOBAL_DATA_DIR"] = str(tmp_path / "shared" / "data")
        result = PathResolver.resolve("${GLOBAL_DATA_DIR}/lookup.csv")
        expected = str(tmp_path / "shared" / "data" / "lookup.csv")
        assert result == expected

    def test_include_directive_pattern(self, tmp_path: Path) -> None:
        """Test typical @include: directive usage pattern."""
        os.environ["GLOBAL_DATA_SOURCE_DIR"] = str(tmp_path / "shared" / "sources")
        config_dir = tmp_path / "project"
        result = PathResolver.resolve("${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml", base_path=config_dir)
        expected = str(tmp_path / "shared" / "sources" / "sead-options.yml")
        assert result == expected

    def test_local_relative_include(self, tmp_path: Path) -> None:
        """Test local relative @include: pattern."""
        project_dir = tmp_path / "project"
        result = PathResolver.resolve("./reconciliation.yml", base_path=project_dir)
        expected = str(project_dir / "reconciliation.yml")
        assert result == expected

    def test_shared_resource_pattern(self, tmp_path: Path) -> None:
        """Test accessing shared resources from nested project."""
        project_dir = tmp_path / "projects" / "arbodat" / "arbodat-test"
        result = PathResolver.resolve("../../../shared/data-sources/config.yml", base_path=project_dir)
        expected = str(project_dir / "../../../shared/data-sources/config.yml")
        assert result == expected

    def test_windows_style_path(self) -> None:
        """Test that Windows-style absolute paths are recognized."""
        # Note: Path.is_absolute() handles platform differences
        if os.name == "nt":
            result = PathResolver.resolve("C:\\Users\\data\\file.txt")
            assert result == "C:\\Users\\data\\file.txt"

    def test_mixed_env_vars_and_paths(self, tmp_path: Path) -> None:
        """Test complex pattern with multiple env vars and relative paths."""
        os.environ["BASE_DIR"] = str(tmp_path)
        os.environ["PROJECT_NAME"] = "myproject"
        result = PathResolver.resolve("${BASE_DIR}/${PROJECT_NAME}/data/file.csv")
        expected = str(tmp_path / "myproject" / "data" / "file.csv")
        assert result == expected


class TestPathResolverEdgeCases:
    """Test edge cases and error conditions."""

    def test_resolve_with_special_characters(self) -> None:
        """Test paths with special characters."""
        os.environ["SPECIAL_DIR"] = "/path/with spaces/and-dashes"
        result = PathResolver.resolve("${SPECIAL_DIR}/file (1).txt")
        assert result == "/path/with spaces/and-dashes/file (1).txt"

    def test_resolve_with_unicode(self) -> None:
        """Test paths with unicode characters."""
        os.environ["UNICODE_DIR"] = "/путь/路径/パス"
        result = PathResolver.resolve("${UNICODE_DIR}/файл.txt")
        assert result == "/путь/路径/パス/файл.txt"

    def test_resolve_empty_env_var_value(self) -> None:
        """Test behavior when env var exists but is empty."""
        os.environ["EMPTY_VAR"] = ""
        result = PathResolver.resolve("${EMPTY_VAR}/file.txt")
        assert result == "/file.txt"

    def test_resolve_nested_braces(self) -> None:
        """Test that nested ${} patterns are handled correctly."""
        # Only the outer pattern should be replaced
        os.environ["OUTER"] = "value"
        result = PathResolver._expand_env_vars("${OUTER}")
        assert result == "value"

    def test_resolve_partial_env_var_syntax(self) -> None:
        """Test incomplete env var syntax is left unchanged."""
        # Missing closing brace
        result = PathResolver._expand_env_vars("${INCOMPLETE/file.txt")
        assert result == "${INCOMPLETE/file.txt"

    def test_resolve_dollar_without_braces(self) -> None:
        """Test that $ without {} is left unchanged."""
        result = PathResolver._expand_env_vars("$HOME/file.txt")
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
        "GLOBAL_DATA_DIR",
        "GLOBAL_DATA_SOURCE_DIR",
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
