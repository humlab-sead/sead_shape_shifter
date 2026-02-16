"""Tests for FileManager component."""

from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import UploadFile

from backend.app.exceptions import ResourceNotFoundError
from backend.app.models.project import ProjectFileInfo
from backend.app.services.project.file_manager import FileManager
from backend.app.utils.exceptions import BadRequestError

# pylint: disable=redefined-outer-name,unused-argument


class TestFileManager:
    """Test FileManager file operations."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path: Path) -> Path:
        """Create temporary configurations directory."""
        config_dir = tmp_path / "configurations"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def file_manager(self, temp_config_dir: Path) -> FileManager:
        """Create FileManager instance."""

        def validate_project_name(name: str) -> str:
            return name.strip()

        def ensure_project_exists(name: str) -> Path:
            project_file = temp_config_dir / name / "shapeshifter.yml"
            if not project_file.exists():
                raise ResourceNotFoundError(message="", resource_type="project", resource_id=name)
            return project_file

        return FileManager(
            projects_dir=temp_config_dir,
            validate_project_name_callback=validate_project_name,
            ensure_project_exists_callback=ensure_project_exists,
        )

    @pytest.fixture
    def sample_project(self, temp_config_dir: Path) -> Path:
        """Create a sample project."""
        project_dir = temp_config_dir / "test_project"
        project_dir.mkdir()
        (project_dir / "shapeshifter.yml").write_text("metadata:\n  name: test_project\n")
        return project_dir

    @pytest.fixture
    def sample_project_with_files(self, temp_config_dir: Path) -> Path:
        """Create a sample project with uploads."""
        project_dir = temp_config_dir / "test_project"
        project_dir.mkdir()
        (project_dir / "shapeshifter.yml").write_text("metadata:\n  name: test_project\n")

        # Files are stored in projects_dir root for backward compatibility
        # (not in project_dir/uploads/)
        (temp_config_dir / "data.xlsx").write_text("mock excel data")
        (temp_config_dir / "sheet.csv").write_text("col1,col2\n1,2\n")
        (temp_config_dir / "file.txt").write_text("text file")

        return project_dir

    def create_upload_file(self, filename: str, content: bytes) -> UploadFile:
        """Create a mock UploadFile."""
        file_obj = BytesIO(content)
        upload = UploadFile(filename=filename, file=file_obj)
        return upload

    # list_project_files tests

    def test_list_project_files_empty_project(self, file_manager: FileManager, sample_project: Path):
        """Test listing files for project without uploads directory."""
        files = file_manager.list_project_files("test_project")
        assert files == []

    def test_list_project_files_all(self, file_manager: FileManager, sample_project_with_files: Path):
        """Test listing all files without filter."""
        files = file_manager.list_project_files("test_project")
        assert len(files) == 3
        names = {f.name for f in files}
        assert names == {"data.xlsx", "sheet.csv", "file.txt"}
        # Verify file info
        for file in files:
            assert isinstance(file, ProjectFileInfo)
            assert file.size_bytes > 0
            assert file.modified_at > 0

    def test_list_project_files_with_single_extension(self, file_manager: FileManager, sample_project_with_files: Path):
        """Test listing files filtered by single extension."""
        files = file_manager.list_project_files("test_project", extensions=[".xlsx"])
        assert len(files) == 1
        assert files[0].name == "data.xlsx"

    def test_list_project_files_with_multiple_extensions(self, file_manager: FileManager, sample_project_with_files: Path):
        """Test listing files filtered by multiple extensions."""
        files = file_manager.list_project_files("test_project", extensions=["xlsx", ".csv"])
        assert len(files) == 2
        names = {f.name for f in files}
        assert names == {"data.xlsx", "sheet.csv"}

    def test_list_project_files_case_insensitive(self, file_manager: FileManager, sample_project_with_files: Path):
        """Test extension filtering is case-insensitive."""
        files = file_manager.list_project_files("test_project", extensions=[".XLSX"])
        assert len(files) == 1
        assert files[0].name == "data.xlsx"

    # save_project_file tests

    def test_save_project_file_success(self, file_manager: FileManager, sample_project: Path, temp_config_dir: Path):
        """Test saving project file successfully."""
        upload = self.create_upload_file("test.xlsx", b"test content")

        result = file_manager.save_project_file("test_project", upload)

        assert isinstance(result, ProjectFileInfo)
        assert result.name == "test.xlsx"
        assert result.size_bytes == 12  # len(b"test content")

        # Verify file was created (files stored in projects_dir root for backward compatibility)
        saved_file = temp_config_dir / "test.xlsx"
        assert saved_file.exists()
        assert saved_file.read_bytes() == b"test content"

    def test_save_project_file_uses_default_extensions(self, file_manager: FileManager, sample_project: Path, temp_config_dir: Path):
        """Test file is saved with default extension validation (.xlsx, .xls)."""
        # .xlsx should be allowed
        upload = self.create_upload_file("data.xlsx", b"excel data")
        file_manager.save_project_file("test_project", upload)
        assert (temp_config_dir / "data.xlsx").exists()

        # .csv should be rejected (not in defaults)
        csv_upload = self.create_upload_file("data.csv", b"a,b,c")
        with pytest.raises(BadRequestError, match="Unsupported file type"):
            file_manager.save_project_file("test_project", csv_upload)

    def test_save_project_file_invalid_extension(self, file_manager: FileManager, sample_project: Path):
        """Test saving file with disallowed extension raises error."""
        upload = self.create_upload_file("script.py", b"print('hello')")

        with pytest.raises(BadRequestError, match="Unsupported file type"):
            file_manager.save_project_file("test_project", upload, allowed_extensions={".xlsx", ".csv"})

    def test_save_project_file_no_extension_restriction(self, file_manager: FileManager, sample_project: Path, temp_config_dir: Path):
        """Test that CSV files work when explicitly allowed."""
        upload = self.create_upload_file("data.csv", b"a,b,c")

        # Pass CSV extension explicitly
        result = file_manager.save_project_file("test_project", upload, allowed_extensions={".csv"})

        assert result.name == "data.csv"
        assert (temp_config_dir / "data.csv").exists()

    def test_save_project_file_duplicate_renames(self, file_manager: FileManager, sample_project: Path, temp_config_dir: Path):
        """Test duplicate filenames are renamed with counter."""
        upload1 = self.create_upload_file("data.xlsx", b"content1")
        upload2 = self.create_upload_file("data.xlsx", b"content2")
        upload3 = self.create_upload_file("data.xlsx", b"content3")

        result1 = file_manager.save_project_file("test_project", upload1)
        result2 = file_manager.save_project_file("test_project", upload2)
        result3 = file_manager.save_project_file("test_project", upload3)

        assert result1.name == "data.xlsx"
        assert result2.name == "data-1.xlsx"
        assert result3.name == "data-2.xlsx"

        # Files stored in projects_dir root
        assert (temp_config_dir / "data.xlsx").read_bytes() == b"content1"
        assert (temp_config_dir / "data-1.xlsx").read_bytes() == b"content2"
        assert (temp_config_dir / "data-2.xlsx").read_bytes() == b"content3"

    def test_save_project_file_size_limit_ok(self, file_manager: FileManager, sample_project: Path):
        """Test file within size limit is saved."""
        content = b"x" * 100  # 100 bytes
        upload = self.create_upload_file("small.xlsx", content)

        result = file_manager.save_project_file("test_project", upload, max_size_mb=1)

        assert result.size_bytes == 100

    def test_save_project_file_exceeds_size_limit(self, file_manager: FileManager, sample_project: Path, temp_config_dir: Path):
        """Test file exceeding size limit raises error."""
        # Create 2MB file, limit is 1MB
        content = b"x" * (2 * 1024 * 1024)
        upload = self.create_upload_file("large.xlsx", content)

        with pytest.raises(BadRequestError, match="too large"):
            file_manager.save_project_file("test_project", upload, max_size_mb=1)

        # Verify file was not saved
        assert not (temp_config_dir / "large.xlsx").exists()

    def test_save_project_file_chunked_upload(self, file_manager: FileManager, sample_project: Path, temp_config_dir: Path):
        """Test large file uploaded in chunks."""
        # Create 3MB content (will be read in 1MB chunks)
        content = b"a" * (3 * 1024 * 1024)
        upload = self.create_upload_file("chunked.xlsx", content)

        result = file_manager.save_project_file("test_project", upload, max_size_mb=5)

        assert result.size_bytes == 3 * 1024 * 1024
        saved_file = temp_config_dir / "chunked.xlsx"
        assert saved_file.read_bytes() == content

    # save_data_source_file tests

    def test_save_data_source_file_success(self, file_manager: FileManager, temp_config_dir: Path):
        """Test saving global data source file."""
        upload = self.create_upload_file("test_datasource_unique.xlsx", b"global data")

        result = file_manager.save_data_source_file(upload)

        # File may be renamed if duplicates exist, so check it was saved with the returned name
        assert result.size_bytes == 11
        assert result.name.startswith("test_datasource_unique")
        assert result.name.endswith(".xlsx")

        saved_file = temp_config_dir / result.name
        assert saved_file.exists()
        assert saved_file.read_bytes() == b"global data"

    def test_save_data_source_file_invalid_extension(self, file_manager: FileManager):
        """Test saving global file with invalid extension."""
        upload = self.create_upload_file("data.csv", b"text")

        with pytest.raises(BadRequestError, match="Unsupported file type"):
            # Default extensions only allow .xlsx, .xls
            file_manager.save_data_source_file(upload)

    def test_save_data_source_file_duplicate_renames(self, file_manager: FileManager, temp_config_dir: Path):
        """Test duplicate global filenames are renamed."""
        # Use unique base name to avoid conflicts with other tests
        upload1 = self.create_upload_file("test_shared_dup.xlsx", b"v1")
        upload2 = self.create_upload_file("test_shared_dup.xlsx", b"v2")

        result1 = file_manager.save_data_source_file(upload1)
        result2 = file_manager.save_data_source_file(upload2)

        # First file might be renamed if it already exists from another test
        assert result1.name.startswith("test_shared_dup")
        assert result1.name.endswith(".xlsx")

        # Second file should have a higher counter than first
        assert result2.name.startswith("test_shared_dup")
        assert result2.name.endswith(".xlsx")
        assert result2.name != result1.name  # Must be different

        # Verify both files exist with correct content
        assert (temp_config_dir / result1.name).read_bytes() == b"v1"
        assert (temp_config_dir / result2.name).read_bytes() == b"v2"

    def test_save_data_source_file_size_limit(self, file_manager: FileManager):
        """Test global file size limit."""
        content = b"x" * (2 * 1024 * 1024)
        upload = self.create_upload_file("test_big_datasource.xlsx", content)

        with pytest.raises(BadRequestError, match="too large"):
            file_manager.save_data_source_file(upload, max_size_mb=1)

    # list_data_source_files tests

    def test_list_data_source_files_empty(self, temp_config_dir: Path):
        """Test listing data source files when only directories exist."""
        # Create a clean temp directory for this specific test
        clean_dir = temp_config_dir.parent / "list_empty_test"
        clean_dir.mkdir(exist_ok=True)

        def sanitize(name: str) -> str:
            return name.strip()

        def ensure_exists(name: str) -> Path:
            return clean_dir / name / "shapeshifter.yml"

        clean_manager = FileManager(
            projects_dir=clean_dir,
            validate_project_name_callback=sanitize,
            ensure_project_exists_callback=ensure_exists,
        )

        # Create only project directory, no files
        (clean_dir / "project1").mkdir(exist_ok=True)

        files = clean_manager.list_data_source_files()
        assert not files

    def test_list_data_source_files_all(self, temp_config_dir: Path):
        """Test listing all data source files."""
        # Create isolated directory to avoid interference
        test_dir = temp_config_dir.parent / "list_all_test"
        test_dir.mkdir(exist_ok=True)

        def sanitize(name: str) -> str:
            return name.strip()

        def ensure_exists(name: str) -> Path:
            return test_dir / name / "shapeshifter.yml"

        test_manager = FileManager(
            projects_dir=test_dir,
            validate_project_name_callback=sanitize,
            ensure_project_exists_callback=ensure_exists,
        )

        # Create test files
        (test_dir / "list_all1.xlsx").write_text("data1")
        (test_dir / "list_all2.csv").write_text("data2")
        (test_dir / "list_all3.txt").write_text("readme")

        files = test_manager.list_data_source_files()
        assert len(files) == 3
        names = {f.name for f in files}
        assert names == {"list_all1.xlsx", "list_all2.csv", "list_all3.txt"}

    def test_list_data_source_files_with_extensions(self, temp_config_dir: Path):
        """Test filtering data source files by extension."""
        # Create isolated directory
        test_dir = temp_config_dir.parent / "list_ext_test"
        test_dir.mkdir(exist_ok=True)

        def sanitize(name: str) -> str:
            return name.strip()

        def ensure_exists(name: str) -> Path:
            return test_dir / name / "shapeshifter.yml"

        test_manager = FileManager(
            projects_dir=test_dir,
            validate_project_name_callback=sanitize,
            ensure_project_exists_callback=ensure_exists,
        )

        (test_dir / "filter_ext1.xlsx").write_text("excel")
        (test_dir / "filter_ext2.csv").write_text("csv")
        (test_dir / "filter_ext3.txt").write_text("text")

        xlsx_files = test_manager.list_data_source_files(extensions=[".xlsx"])
        assert len(xlsx_files) == 1
        assert xlsx_files[0].name == "filter_ext1.xlsx"

        data_files = test_manager.list_data_source_files(extensions=["xlsx", "csv"])
        assert len(data_files) == 2
        names = {f.name for f in data_files}
        assert names == {"filter_ext1.xlsx", "filter_ext2.csv"}

    def test_list_data_source_files_skips_directories(self, temp_config_dir: Path):
        """Test directories are not included in list."""
        # Create isolated directory
        test_dir = temp_config_dir.parent / "list_skip_test"
        test_dir.mkdir(exist_ok=True)

        def sanitize(name: str) -> str:
            return name.strip()

        def ensure_exists(name: str) -> Path:
            return test_dir / name / "shapeshifter.yml"

        test_manager = FileManager(
            projects_dir=test_dir,
            validate_project_name_callback=sanitize,
            ensure_project_exists_callback=ensure_exists,
        )

        (test_dir / "skip_dirs1.xlsx").write_text("file")
        (test_dir / "project_dir").mkdir()

        files = test_manager.list_data_source_files()
        assert len(files) == 1
        assert files[0].name == "skip_dirs1.xlsx"

    # get_excel_metadata tests

    def test_get_excel_metadata_sheets_only(self, file_manager: FileManager, temp_config_dir: Path):
        """Test getting sheet names from Excel file."""
        excel_file = temp_config_dir / "test.xlsx"
        excel_file.write_text("dummy")  # Will be mocked

        with patch("backend.app.services.project.file_manager.extract_excel_metadata") as mock_extract:
            mock_extract.return_value = (["Sheet1", "Sheet2"], [])

            sheets, columns = file_manager.get_excel_metadata(str(excel_file))

            assert sheets == ["Sheet1", "Sheet2"]
            assert columns == []
            mock_extract.assert_called_once_with(excel_file, sheet_name=None, cell_range=None)

    def test_get_excel_metadata_with_columns(self, file_manager: FileManager, temp_config_dir: Path):
        """Test getting columns from specific sheet."""
        excel_file = temp_config_dir / "test.xlsx"
        excel_file.write_text("dummy")

        with patch("backend.app.services.project.file_manager.extract_excel_metadata") as mock_extract:
            mock_extract.return_value = (["Sheet1"], ["col1", "col2", "col3"])

            sheets, columns = file_manager.get_excel_metadata(str(excel_file), sheet_name="Sheet1")

            assert sheets == ["Sheet1"]
            assert columns == ["col1", "col2", "col3"]
            mock_extract.assert_called_once_with(excel_file, sheet_name="Sheet1", cell_range=None)

    def test_get_excel_metadata_with_cell_range(self, file_manager: FileManager, temp_config_dir: Path):
        """Test getting columns from cell range."""
        excel_file = temp_config_dir / "test.xlsx"
        excel_file.write_text("dummy")

        with patch("backend.app.services.project.file_manager.extract_excel_metadata") as mock_extract:
            mock_extract.return_value = (["Data"], ["A", "B", "C"])

            _, columns = file_manager.get_excel_metadata(str(excel_file), sheet_name="Data", cell_range="A1:C10")

            assert columns == ["A", "B", "C"]
            mock_extract.assert_called_once_with(excel_file, sheet_name="Data", cell_range="A1:C10")

    def test_get_excel_metadata_file_not_found(self, file_manager: FileManager):
        """Test error when Excel file doesn't exist."""
        with pytest.raises(BadRequestError, match="File not found"):
            file_manager.get_excel_metadata("nonexistent.xlsx")

    def test_get_excel_metadata_relative_path(self, file_manager: FileManager, temp_config_dir: Path):
        """Test resolving relative path to Excel file."""
        excel_file = temp_config_dir / "data.xlsx"
        excel_file.write_text("dummy")

        # Use relative path from projects_dir
        with patch("backend.app.services.project.file_manager.extract_excel_metadata") as mock_extract:
            mock_extract.return_value = (["Sheet1"], ["col1"])

            # Relative path should be resolved
            sheets, _ = file_manager.get_excel_metadata("data.xlsx")

            assert sheets == ["Sheet1"]
            # Verify it resolved the path correctly
            call_args = mock_extract.call_args[0][0]
            assert call_args == excel_file

    # Helper method tests

    def test_get_project_upload_dir(self, file_manager: FileManager, temp_config_dir: Path):
        """Test getting project upload directory (currently returns projects_dir for backward compatibility)."""
        upload_dir = file_manager._get_project_upload_dir("test_project")
        # Currently returns projects_dir root (backward compatibility)
        assert upload_dir == temp_config_dir

    def test_sanitize_filename_valid(self, file_manager: FileManager):
        """Test sanitizing valid filenames."""
        assert file_manager._sanitize_filename("test.xlsx") == "test.xlsx"
        assert file_manager._sanitize_filename("data_file.csv") == "data_file.csv"
        assert file_manager._sanitize_filename("my-file.123.txt") == "my-file.123.txt"

    def test_sanitize_filename_removes_path_separators(self, file_manager: FileManager):
        """Test path separators are removed (extracts basename)."""
        assert file_manager._sanitize_filename("folder/file.xlsx") == "file.xlsx"
        assert file_manager._sanitize_filename("../hidden.csv") == "hidden.csv"
        assert file_manager._sanitize_filename("path/../file.txt") == "file.txt"
        assert file_manager._sanitize_filename("../../../etc/passwd") == "passwd"

    def test_sanitize_filename_none(self, file_manager: FileManager):
        """Test sanitizing None filename raises error."""
        with pytest.raises(BadRequestError, match="Filename is required"):
            file_manager._sanitize_filename(None)

    def test_sanitize_filename_empty(self, file_manager: FileManager):
        """Test sanitizing empty filename raises error."""
        # Empty string is falsy, triggers "Filename is required"
        with pytest.raises(BadRequestError, match="Filename is required"):
            file_manager._sanitize_filename("")

        # Whitespace-only is allowed (Path().name preserves it)
        # This is technically valid, though unusual
        assert file_manager._sanitize_filename("   ") == "   "

    def test_to_public_path(self, file_manager: FileManager, temp_config_dir: Path):
        """Test converting absolute path to public relative path."""
        upload_file = temp_config_dir / "data.xlsx"
        public_path = file_manager._to_public_path(upload_file)

        # Should be relative to projects directory
        assert "data.xlsx" in public_path

    def test_to_public_path_outside_projects_dir(self, file_manager: FileManager, tmp_path: Path):
        """Test path outside projects directory."""
        external_file = tmp_path / "external" / "file.txt"
        external_file.parent.mkdir()
        external_file.write_text("content")

        # Should still work, just return the path
        public_path = file_manager._to_public_path(external_file)
        assert public_path  # Should return something, even if not relative

    def test_resolve_path_absolute(self, file_manager: FileManager, temp_config_dir: Path):
        """Test resolving absolute path."""
        test_file = temp_config_dir / "test.xlsx"
        test_file.write_text("content")

        resolved = file_manager._resolve_path(str(test_file))
        assert resolved == test_file
        assert resolved.exists()

    def test_resolve_path_relative_to_projects_dir(self, file_manager: FileManager, temp_config_dir: Path):
        """Test resolving relative path from projects directory."""
        test_file = temp_config_dir / "data.xlsx"
        test_file.write_text("content")

        resolved = file_manager._resolve_path("data.xlsx")
        assert resolved == test_file

    def test_resolve_path_not_found(self, file_manager: FileManager):
        """Test resolving non-existent file raises error."""
        with pytest.raises(BadRequestError, match="File not found"):
            file_manager._resolve_path("nonexistent.xlsx")
