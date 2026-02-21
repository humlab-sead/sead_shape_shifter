"""File management operations: upload, list, and inspect files for projects."""

from pathlib import Path
from typing import Iterable

from fastapi import UploadFile

from backend.app.mappers.project_name_mapper import ProjectNameMapper
from backend.app.models.project import ProjectFileInfo
from backend.app.utils.excel_utils import get_excel_metadata as extract_excel_metadata
from backend.app.utils.exceptions import BadRequestError

DEFAULT_ALLOWED_UPLOAD_EXTENSIONS: set[str] = {".xlsx", ".xls"}
MAX_PROJECT_UPLOAD_SIZE_MB: int = 50


class FileManager:
    """Handles file operations for projects and data sources.

    This component manages file uploads, listings, and metadata extraction
    for both project-specific files and global data source files.
    """

    def __init__(
        self,
        projects_root: Path,
        global_data_dir: Path,
        application_root: Path,
        sanitize_project_name_callback,  # Callable[[str], str]
        ensure_project_exists_callback,  # Callable[[str], Path]
    ):
        """Initialize file manager.

        Args:
            projects_root: Base directory for all projects
            global_data_dir: Directory for global shared data files
            application_root: Application root directory for relative path display
            sanitize_project_name_callback: Function to sanitize project names
            ensure_project_exists_callback: Function to ensure project exists
        """
        self.projects_root: Path = projects_root
        self.global_data_dir: Path = global_data_dir
        self.application_root: Path = application_root
        self._sanitize_project_name = sanitize_project_name_callback
        self._ensure_project_exists = ensure_project_exists_callback

    # Helper methods

    def _get_project_upload_dir(self, project_name: str) -> Path:
        """Get upload directory for a project.

        Returns the project's directory where uploaded files are stored.
        Files are stored directly in the project directory alongside shapeshifter.yml.

        Args:
            project_name: Project name

        Returns:
            Path to project directory
        """

        safe_path = ProjectNameMapper.to_path(project_name)
        return self.projects_root / safe_path

    def _to_public_path(self, path: Path) -> str:
        """Convert absolute path to public relative path for API responses.

        This is for display/API purposes and differs from FilePathResolver.decompose()
        which returns (filename, location) tuples for entity configuration.

        Tries to make path relative to application_root, global_data_dir, or projects_dir,
        otherwise returns absolute path as string.

        Returns:
            Relative path string for API display (e.g., "shared/shared-data/file.xlsx")
        """
        try:
            return str(path.relative_to(self.application_root))
        except ValueError:
            try:
                # For global data files, make relative to global_data_dir to get just filename
                rel_path = path.relative_to(self.global_data_dir)
                # Return as "shared/shared-data/filename.xlsx" for portability
                return str(Path("shared/shared-data") / rel_path)
            except ValueError:
                try:
                    return str(path.relative_to(self.projects_root))
                except ValueError:
                    return str(path)

    def _resolve_path(self, path_str: str, location: str = "global") -> Path:
        """Resolve a file path for file browsing operations with existence validation.

        This method is for file browsing/inspection and differs from FilePathResolver.resolve()
        which is for entity file resolution within specific projects.

        Note: location="local" means base projects directory (for browsing), not a specific
        project directory. Use FilePathResolver for project-specific entity file resolution.

        Args:
            path_str: Filename or relative path
            location: File location - "global" (GLOBAL_DATA_DIR) or "local" (base projects_dir)

        Returns:
            Resolved absolute path

        Raises:
            BadRequestError: If file not found or invalid location
        """
        if location == "global":
            resolved = self.global_data_dir / path_str
        elif location == "local":
            # "local" here means base projects directory for file browsing,
            # not a specific project (that's what FilePathResolver handles)
            resolved = self.projects_root / path_str
        else:
            raise BadRequestError(f"Invalid location: {location}. Must be 'global' or 'local'")

        # Validate file existence
        if not resolved.exists():
            raise BadRequestError(f"File not found: {path_str} (location: {location})")

        return resolved

    def _sanitize_filename(self, filename: str | None) -> str:
        """Sanitize uploaded filename to prevent path traversal.

        Args:
            filename: User-supplied filename

        Returns:
            Safe filename (basename only)

        Raises:
            BadRequestError: If filename is empty or invalid
        """
        if not filename:
            raise BadRequestError("Filename is required")
        safe_name: str = Path(filename).name
        if not safe_name:
            raise BadRequestError("Invalid filename")
        return safe_name

    # Project-specific file operations

    def list_project_files(self, project_name: str, extensions: Iterable[str] | None = None) -> list[ProjectFileInfo]:
        """List files stored under a project's uploads directory.

        Args:
            project_name: Project name
            extensions: Optional file extensions to filter (e.g., ['xlsx', 'csv'])

        Returns:
            List of file information
        """
        self._ensure_project_exists(project_name)
        upload_dir: Path = self._get_project_upload_dir(project_name)

        if not upload_dir.exists():
            return []

        ext_set: set[str] | None = None
        if extensions:
            ext_set = {f".{ext.lstrip('.').lower()}" for ext in extensions if ext}

        files: list[ProjectFileInfo] = []
        for file_path in sorted(upload_dir.glob("*")):
            if not file_path.is_file():
                continue

            if file_path.name == "shapeshifter.yml":
                continue

            if ext_set and file_path.suffix.lower() not in ext_set:
                continue

            stat = file_path.stat()
            files.append(
                ProjectFileInfo(
                    name=file_path.name,
                    path=file_path.name,
                    location="local",
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )

        return files

    def save_project_file(
        self,
        project_name: str,
        upload: UploadFile,
        *,
        allowed_extensions: set[str] | None = None,
        max_size_mb: int = MAX_PROJECT_UPLOAD_SIZE_MB,
    ) -> ProjectFileInfo:
        """Save an uploaded file into the project's uploads directory.

        Args:
            project_name: Project name
            upload: Uploaded file
            allowed_extensions: Allowed file extensions (e.g., {'.xlsx', '.xls'})
            max_size_mb: Maximum file size in megabytes

        Returns:
            File information for the saved file

        Raises:
            BadRequestError: If file type or size is invalid
        """
        self._ensure_project_exists(project_name)
        allowed: set[str] = allowed_extensions or DEFAULT_ALLOWED_UPLOAD_EXTENSIONS

        filename: str = self._sanitize_filename(upload.filename)
        ext: str = Path(filename).suffix.lower()
        if allowed and ext not in allowed:
            allowed_list: str = ", ".join(sorted(allowed))
            raise BadRequestError(f"Unsupported file type '{ext}'. Allowed: {allowed_list}")

        upload_dir: Path = self._get_project_upload_dir(project_name)
        upload_dir.mkdir(parents=True, exist_ok=True)

        target_path: Path = upload_dir / filename
        counter = 1
        while target_path.exists():
            target_path = upload_dir / f"{Path(filename).stem}-{counter}{ext}"
            counter += 1

        max_bytes: int = max_size_mb * 1024 * 1024
        total_bytes = 0

        try:
            with target_path.open("wb") as buffer:
                while True:
                    chunk: bytes = upload.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if max_bytes and total_bytes > max_bytes:
                        raise BadRequestError(f"File is too large ({total_bytes} bytes). Maximum allowed is {max_bytes} bytes")
                    buffer.write(chunk)
        except Exception as exc:  # pylint: disable=broad-except
            target_path.unlink(missing_ok=True)
            raise exc
        finally:
            try:
                upload.file.close()
            except Exception:  # pylint: disable=broad-except
                pass

        stat = target_path.stat()

        return ProjectFileInfo(
            name=target_path.name,
            path=target_path.name,
            location="local",
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
        )

    # Global data source file operations

    def list_data_source_files(self, extensions: Iterable[str] | None = None, project_name: str | None = None) -> list[ProjectFileInfo]:
        """List files available for data source configuration.

        Args:
            extensions: Optional file extensions to filter
            project_name: Optional project name to also include project-specific files

        Returns:
            List of file information from global store (and local store if project_name provided)
        """
        files: list[ProjectFileInfo] = []

        # Always include global files
        upload_dir: Path = self.global_data_dir
        if upload_dir.exists():
            ext_set: set[str] | None = None
            if extensions:
                ext_set = {f".{ext.lstrip('.').lower()}" for ext in extensions if ext}

            for file_path in sorted(upload_dir.glob("*")):
                if not file_path.is_file():
                    continue

                if ext_set and file_path.suffix.lower() not in ext_set:
                    continue

                stat = file_path.stat()
                files.append(
                    ProjectFileInfo(
                        name=file_path.name,
                        path=file_path.name,
                        location="global",
                        size_bytes=stat.st_size,
                        modified_at=stat.st_mtime,
                    )
                )

        # Add project-specific files if project_name provided
        if project_name:
            try:
                local_files = self.list_project_files(project_name, extensions)
                files.extend(local_files)
            except FileNotFoundError:
                # Project doesn't exist yet, only return global files
                pass

        return files

    def save_data_source_file(
        self,
        upload: UploadFile,
        *,
        allowed_extensions: set[str] | None = None,
        max_size_mb: int = MAX_PROJECT_UPLOAD_SIZE_MB,
    ) -> ProjectFileInfo:
        """Save an uploaded file into the global data directory (global data source).

        Args:
            upload: Uploaded file
            allowed_extensions: Allowed file extensions
            max_size_mb: Maximum file size in megabytes

        Returns:
            File information for the saved file

        Raises:
            BadRequestError: If file type or size is invalid
        """
        allowed: set[str] = allowed_extensions or DEFAULT_ALLOWED_UPLOAD_EXTENSIONS

        filename: str = self._sanitize_filename(upload.filename)
        ext: str = Path(filename).suffix.lower()
        if allowed and ext not in allowed:
            allowed_list: str = ", ".join(sorted(allowed))
            raise BadRequestError(f"Unsupported file type '{ext}'. Allowed: {allowed_list}")

        upload_dir: Path = self.global_data_dir
        upload_dir.mkdir(parents=True, exist_ok=True)

        target_path: Path = upload_dir / filename
        counter = 1
        while target_path.exists():
            target_path = upload_dir / f"{Path(filename).stem}-{counter}{ext}"
            counter += 1

        max_bytes: int = max_size_mb * 1024 * 1024
        total_bytes = 0

        try:
            with target_path.open("wb") as buffer:
                while True:
                    chunk = upload.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if max_bytes and total_bytes > max_bytes:
                        raise BadRequestError(f"File is too large ({total_bytes} bytes). Maximum allowed is {max_bytes} bytes")
                    buffer.write(chunk)
        except Exception as exc:  # pylint: disable=broad-except
            target_path.unlink(missing_ok=True)
            raise exc
        finally:
            try:
                upload.file.close()
            except Exception:  # pylint: disable=broad-except
                pass

        stat = target_path.stat()

        return ProjectFileInfo(
            name=target_path.name,
            path=target_path.name,
            location="global",
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
        )

    # Excel metadata extraction

    def get_excel_metadata(
        self, file_path: str, location: str = "global", sheet_name: str | None = None, cell_range: str | None = None
    ) -> tuple[list[str], list[str]]:
        """Return available sheets and columns for an Excel file.

        Args:
            file_path: Filename or relative path to the Excel file
            location: File location - "global" (shared data) or "local" (project-specific)
            sheet_name: Optional sheet to inspect for columns
            cell_range: Optional cell range (e.g., 'A1:H30') to limit columns

        Returns:
            Tuple of (sheet_names, column_names)

        Raises:
            BadRequestError: If file is missing/unsupported or sheet is not found
        """
        resolved_path: Path = self._resolve_path(file_path, location=location)
        return extract_excel_metadata(resolved_path, sheet_name=sheet_name, cell_range=cell_range)
