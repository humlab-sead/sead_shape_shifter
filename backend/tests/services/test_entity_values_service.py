"""Tests for entity values service."""

import time
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from backend.app.services.entity_values_service import EntityValuesService, get_entity_values_service


class TestEntityValuesService:
    """Test entity values service."""

    @pytest.fixture
    def mock_project_service(self):
        """Create mock project service."""
        service = Mock()
        return service

    @pytest.fixture
    def service(self, mock_project_service):
        """Create entity values service with mocked dependencies."""
        return EntityValuesService(project_service=mock_project_service)

    def test_parse_load_directive_with_valid_directive(self, service):
        """Test parsing @load: directive."""
        result = service._parse_load_directive("@load:materialized/feature_type.parquet")
        assert result == "materialized/feature_type.parquet"

    def test_parse_load_directive_with_array_values(self, service):
        """Test parsing returns None for array values."""
        result = service._parse_load_directive([[1, 2], [3, 4]])
        assert result is None

    def test_parse_load_directive_with_non_load_string(self, service):
        """Test parsing returns None for non-@load strings."""
        result = service._parse_load_directive("some_other_string")
        assert result is None

    def test_resolve_values_path(self, service, mock_project_service):
        """Test resolving values file path."""
        # Mock project with file_path
        mock_project = Mock()
        mock_project.folder = Path("/projects/test_project")
        mock_project_service.load_project.return_value = mock_project

        result = service._resolve_values_path("test_project", "materialized/feature_type.parquet")

        assert result == Path("/projects/test_project/materialized/feature_type.parquet")
        mock_project_service.load_project.assert_called_once_with("test_project")

    def test_read_values_file_parquet(self, service, tmp_path):
        """Test reading parquet file."""
        # Create test parquet file
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        file_path = tmp_path / "test.parquet"
        df.to_parquet(file_path, index=False)

        columns, values, format_type, etag = service._read_values_file(file_path)

        assert columns == ["col1", "col2"]
        assert values == [[1, "a"], [2, "b"], [3, "c"]]
        assert format_type == "parquet"
        assert isinstance(etag, str)
        assert len(etag) == 32  # MD5 hex

    def test_read_values_file_csv(self, service, tmp_path):
        """Test reading CSV file."""
        # Create test CSV file
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        file_path = tmp_path / "test.csv"
        df.to_csv(file_path, index=False)

        columns, values, format_type, etag = service._read_values_file(file_path)

        assert columns == ["col1", "col2"]
        assert values == [[1, "a"], [2, "b"], [3, "c"]]
        assert format_type == "csv"
        assert isinstance(etag, str)
        assert len(etag) == 32  # MD5 hex

    def test_read_values_file_not_found(self, service, tmp_path):
        """Test reading non-existent file raises FileNotFoundError."""
        file_path = tmp_path / "nonexistent.parquet"

        with pytest.raises(FileNotFoundError, match="Values file not found"):
            service._read_values_file(file_path)

    def test_read_values_file_unsupported_format(self, service, tmp_path):
        """Test reading unsupported file format raises ValueError."""
        file_path = tmp_path / "test.txt"
        file_path.touch()

        with pytest.raises(ValueError, match="Unsupported file format"):
            service._read_values_file(file_path)

    def test_write_values_file_parquet(self, service, tmp_path):
        """Test writing parquet file."""
        file_path = tmp_path / "output.parquet"
        columns = ["col1", "col2"]
        values = [[1, "a"], [2, "b"], [3, "c"]]

        format_type = service._write_values_file(file_path, columns, values, "parquet")

        assert format_type == "parquet"
        assert file_path.exists()

        # Verify content
        df = pd.read_parquet(file_path)
        assert df.columns.tolist() == columns
        assert df.values.tolist() == values

    def test_write_values_file_csv(self, service, tmp_path):
        """Test writing CSV file."""
        file_path = tmp_path / "output.csv"
        columns = ["col1", "col2"]
        values = [[1, "a"], [2, "b"], [3, "c"]]

        format_type = service._write_values_file(file_path, columns, values, "csv")

        assert format_type == "csv"
        assert file_path.exists()

        # Verify content
        df = pd.read_csv(file_path)
        assert df.columns.tolist() == columns
        assert df.values.tolist() == values

    def test_write_values_file_infers_format_from_extension(self, service, tmp_path):
        """Test format inference from file extension."""
        file_path = tmp_path / "output.parquet"
        columns = ["col1"]
        values = [[1], [2]]

        format_type = service._write_values_file(file_path, columns, values, None)

        assert format_type == "parquet"
        assert file_path.exists()

    def test_write_values_file_creates_parent_directory(self, service, tmp_path):
        """Test that parent directories are created if they don't exist."""
        file_path = tmp_path / "nested" / "folder" / "output.parquet"
        columns = ["col1"]
        values = [[1]]

        service._write_values_file(file_path, columns, values, "parquet")

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_write_values_file_column_value_mismatch_raises_clear_error(self, service, tmp_path):
        """Test clear validation error when row width differs from columns."""
        file_path = tmp_path / "output.parquet"
        columns = ["a", "b", "c", "d"]
        values = [[1, 2, 3, 4, 5, 6]]  # 6 values, 4 columns

        with pytest.raises(ValueError, match="Column/value width mismatch"):
            service._write_values_file(file_path, columns, values, "parquet")

    def test_write_values_file_non_list_row_raises_clear_error(self, service, tmp_path):
        """Test clear validation error for malformed rows."""
        file_path = tmp_path / "output.parquet"
        columns = ["a"]
        values = [123]  # type: ignore[list-item]

        with pytest.raises(ValueError, match="expected list"):
            service._write_values_file(file_path, columns, values, "parquet")

    def test_get_values_success(self, service, mock_project_service, tmp_path):
        """Test getting values for entity with @load: directive."""
        # Setup mocks
        mock_project = Mock()
        mock_project.folder = tmp_path
        mock_project_service.load_project.return_value = mock_project

        entity_data = {"values": "@load:materialized/test.parquet"}
        mock_project_service.get_entity_by_name.return_value = entity_data

        # Create test file
        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        file_path = tmp_path / "materialized" / "test.parquet"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(file_path, index=False)

        # Execute
        result = service.get_values("test_project", "test_entity")

        # Verify
        assert result.columns == ["col1", "col2"]
        assert result.values == [[1, "a"], [2, "b"]]
        assert result.format == "parquet"
        assert result.row_count == 2
        mock_project_service.get_entity_by_name.assert_called_once_with("test_project", "test_entity")

    def test_get_values_no_load_directive(self, service, mock_project_service):
        """Test getting values for entity without @load: directive raises ValueError."""
        entity_data = {"values": [[1, 2], [3, 4]]}
        mock_project_service.get_entity_by_name.return_value = entity_data

        with pytest.raises(ValueError, match="does not have @load: directive"):
            service.get_values("test_project", "test_entity")

    def test_get_values_file_not_found(self, service, mock_project_service, tmp_path):
        """Test getting values for non-existent file raises FileNotFoundError."""
        # Setup mocks
        mock_project = Mock()
        mock_project.folder = tmp_path
        mock_project_service.load_project.return_value = mock_project

        entity_data = {"values": "@load:materialized/nonexistent.parquet"}
        mock_project_service.get_entity_by_name.return_value = entity_data

        with pytest.raises(FileNotFoundError):
            service.get_values("test_project", "test_entity")

    def test_update_values_success(self, service, mock_project_service, tmp_path):
        """Test updating values for entity with @load: directive."""
        # Setup mocks
        mock_project = Mock()
        mock_project.folder = tmp_path
        mock_project_service.load_project.return_value = mock_project

        entity_data = {"values": "@load:materialized/test.parquet"}
        mock_project_service.get_entity_by_name.return_value = entity_data

        columns = ["col1", "col2"]
        values = [[1, "a"], [2, "b"], [3, "c"]]

        # Execute
        result = service.update_values("test_project", "test_entity", columns, values, "parquet")

        # Verify
        assert result.columns == columns
        assert result.values == values
        assert result.format == "parquet"
        assert result.row_count == 3

        # Verify file was created
        file_path = tmp_path / "materialized" / "test.parquet"
        assert file_path.exists()

    def test_update_values_no_load_directive(self, service, mock_project_service):
        """Test updating values for entity without @load: directive raises ValueError."""
        entity_data = {"values": [[1, 2], [3, 4]]}
        mock_project_service.get_entity_by_name.return_value = entity_data

        with pytest.raises(ValueError, match="does not have @load: directive"):
            service.update_values("test_project", "test_entity", ["col1"], [[1]])

    def test_update_values_preserves_format(self, service, mock_project_service, tmp_path):
        """Test updating values preserves existing format when not specified."""
        # Setup mocks
        mock_project = Mock()
        mock_project.folder = tmp_path
        mock_project_service.load_project.return_value = mock_project

        entity_data = {"values": "@load:materialized/test.csv"}
        mock_project_service.get_entity_by_name.return_value = entity_data

        columns = ["col1"]
        values = [[1], [2]]

        # Execute (format=None should infer from file extension)
        result = service.update_values("test_project", "test_entity", columns, values, None)

        # Verify CSV format was used
        assert result.format == "csv"
        file_path = tmp_path / "materialized" / "test.csv"
        assert file_path.exists()

    def test_update_values_rejects_non_authoritative_fixed_columns(self, service, mock_project_service, tmp_path):
        """Fixed entity updates must use backend-authoritative full column order."""
        mock_project = Mock()
        mock_project.folder = tmp_path
        mock_project_service.load_project.return_value = mock_project

        entity_data = {
            "type": "fixed",
            "public_id": "location_id",
            "keys": ["name"],
            "columns": ["system_id", "location_id", "name", "country"],
            "values": "@load:materialized/test.parquet",
        }
        mock_project_service.get_entity_by_name.return_value = entity_data

        with pytest.raises(ValueError, match="authoritative columns"):
            service.update_values("test_project", "location", ["country"], [["Sweden"]], "parquet")

    def test_get_entity_values_service_factory(self):
        """Test factory function returns service instance."""

        service = get_entity_values_service()
        assert isinstance(service, EntityValuesService)

    def test_generate_etag(self, service, tmp_path):
        """Test etag generation from file metadata."""
        # Create test file
        test_file = tmp_path / "test.parquet"
        test_file.write_text("test content")

        # Generate etag
        etag = service._generate_etag(test_file)

        # Verify etag is hex string
        assert isinstance(etag, str)
        assert len(etag) == 32  # MD5 hex digest
        assert all(c in "0123456789abcdef" for c in etag)

    def test_generate_etag_changes_on_modification(self, service, tmp_path):
        """Test etag changes when file is modified."""
        # Create test file
        test_file = tmp_path / "test.parquet"
        test_file.write_text("original content")
        etag1 = service._generate_etag(test_file)

        # Modify file

        time.sleep(0.01)  # Ensure mtime difference
        test_file.write_text("modified content")
        etag2 = service._generate_etag(test_file)

        # Verify etag changed
        assert etag1 != etag2

    def test_validate_etag_match(self, service, tmp_path):
        """Test etag validation succeeds with matching etag."""
        # Create test file
        test_file = tmp_path / "test.parquet"
        test_file.write_text("test content")

        # Generate etag
        etag = service._generate_etag(test_file)

        # Validate with same etag
        assert service._validate_etag(test_file, etag) is True

    def test_validate_etag_mismatch(self, service, tmp_path):
        """Test etag validation fails with non-matching etag."""
        # Create test file
        test_file = tmp_path / "test.parquet"
        test_file.write_text("test content")

        # Validate with wrong etag
        assert service._validate_etag(test_file, "wrong_etag") is False

    def test_get_values_returns_etag(self, service, mock_project_service, tmp_path):
        """Test get_values returns etag in response."""
        # Setup mocks
        mock_project = Mock()
        mock_project.folder = tmp_path
        mock_project_service.load_project.return_value = mock_project

        entity_data = {"values": "@load:test.parquet"}
        mock_project_service.get_entity_by_name.return_value = entity_data

        # Create test parquet file
        test_file = tmp_path / "test.parquet"
        df = pd.DataFrame({"col1": [1, 2]})
        df.to_parquet(test_file, index=False)

        # Execute
        result = service.get_values("test_project", "test_entity")

        # Verify etag included
        assert result.etag is not None
        assert isinstance(result.etag, str)
        assert len(result.etag) == 32

    def test_update_values_with_matching_etag(self, service, mock_project_service, tmp_path):
        """Test update_values succeeds with matching etag."""
        # Setup mocks
        mock_project = Mock()
        mock_project.folder = tmp_path
        mock_project_service.load_project.return_value = mock_project

        entity_data = {"values": "@load:test.parquet"}
        mock_project_service.get_entity_by_name.return_value = entity_data

        # Create test parquet file
        test_file = tmp_path / "test.parquet"
        df = pd.DataFrame({"col1": [1, 2]})
        df.to_parquet(test_file, index=False)

        # Get current etag
        current_etag = service._generate_etag(test_file)

        # Update with matching etag
        columns = ["col1"]
        values = [[10], [20]]
        result = service.update_values("test_project", "test_entity", columns, values, None, if_match=current_etag)

        # Verify success
        assert result.row_count == 2
        # Etag should exist (may or may not change depending on filesystem time resolution)
        assert result.etag is not None
        assert isinstance(result.etag, str)
        assert len(result.etag) == 32

    def test_update_values_with_mismatched_etag(self, service, mock_project_service, tmp_path):
        """Test update_values fails with mismatched etag (409 Conflict)."""
        # Setup mocks
        mock_project = Mock()
        mock_project.folder = tmp_path
        mock_project_service.load_project.return_value = mock_project

        entity_data = {"values": "@load:test.parquet"}
        mock_project_service.get_entity_by_name.return_value = entity_data

        # Create test parquet file
        test_file = tmp_path / "test.parquet"
        df = pd.DataFrame({"col1": [1, 2]})
        df.to_parquet(test_file, index=False)

        # Update with wrong etag
        columns = ["col1"]
        values = [[10], [20]]

        with pytest.raises(ValueError, match="409 Conflict"):
            service.update_values("test_project", "test_entity", columns, values, None, if_match="wrong_etag")

    def test_update_values_without_etag_allows_update(self, service, mock_project_service, tmp_path):
        """Test update_values succeeds without etag (no optimistic locking)."""
        # Setup mocks
        mock_project = Mock()
        mock_project.folder = tmp_path
        mock_project_service.load_project.return_value = mock_project

        entity_data = {"values": "@load:test.parquet"}
        mock_project_service.get_entity_by_name.return_value = entity_data

        # Create test parquet file
        test_file = tmp_path / "test.parquet"
        df = pd.DataFrame({"col1": [1, 2]})
        df.to_parquet(test_file, index=False)

        # Update without etag
        columns = ["col1"]
        values = [[10], [20]]
        result = service.update_values("test_project", "test_entity", columns, values, None, if_match=None)

        # Verify success (no etag check performed)
        assert result.row_count == 2
