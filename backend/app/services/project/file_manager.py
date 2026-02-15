"""File management operations: upload, list, and inspect files for projects."""

from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from fastapi import UploadFile

from backend.app.core.config import settings
from backend.app.models.project import ProjectFileInfo
from backend.app.utils.exceptions import BadRequestError
from backend.app.utils.excel_utils import get_excel_metadata as extract_excel_metadata

if TYPE_CHECKING:
    pass


DEFAULT_ALLOWED_UPLOAD_EXTENSIONS: set[str] = {".xlsx", ".xls"}
MAX_PROJECT_UPLOAD_SIZE_MB: int = 50


class FileManager:
    """Handles file operations for projects and data sources.
    
    This component manages file uploads, listings, and metadata extraction
    for both project-specific files and global data source files.
    """

    def __init__(
        self,
        projects_dir: Path,
        sanitize_project_name_callback,  # Callable[[str], str]
        ensure_project_exists_callback,  # Callable[[str], Path]
    ):
        """Initialize file manager.
        
        Args:
            projects_dir: Base directory for all projects
            sanitize_project_name_callback: Function to sanitize project names
            ensure_project_exists_callback: Function to ensure project exists
        """
        self.projects_dir = projects_dir
        self._sanitize_project_name = sanitize_project_name_callback
        self._ensure_project_exists = ensure_project_exists_callback

    # Helper methods

    def _get_project_upload_dir(self, project_name: str) -> Path:  # pylint: disable=unused-argument
        """Get upload directory for a project.
        
        Currently returns projects_dir for backward compatibility.
        Future: could return projects_dir/project_name/uploads/
        """
        # safe_name = self._sanitize_project_name(project_name)
        return self.projects_dir

    def _to_public_path(self, path: Path) -> str:
        """Convert absolute path to public relative path.
        
        Tries to make path relative to PROJECT_ROOT, then PROJECTS_DIR parent,
        otherwise returns absolute path as string.
        """
        try:
            return str(path.relative_to(settings.PROJECT_ROOT))
        except ValueError:
            try:
                return str(path.relative_to(settings.PROJECTS_DIR.parent))
            except ValueError:
                return str(path)

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a user-supplied path relative to project root (or projects dir) and validate existence.
        
        Args:
            path_str: Path string (absolute or relative)
            
        Returns:
            Resolved absolute path
            
        Raises:
            BadRequestError: If file not found
        """
        raw = Path(path_str)
        candidates: list[Path] = []

        # Absolute path as-is
        if raw.is_absolute():
            candidates.append(raw)
        else:
            # Relative to repo root
            candidates.append((settings.PROJECT_ROOT / raw).resolve())
            # Relative to projects dir
            candidates.append((settings.PROJECTS_DIR / raw.name).resolve())

        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise BadRequestError(f"File not found: {path_str}")

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

            if ext_set and file_path.suffix.lower() not in ext_set:
                continue

            stat = file_path.stat()
            files.append(
                ProjectFileInfo(
                    name=file_path.name,
                    path=self._to_public_path(file_path),
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
            path=self._to_public_path(target_path),
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
        )

    # Global data source file operations

    def list_data_source_files(self, extensions: Iterable[str] | None = None) -> list[ProjectFileInfo]:
        """List files available for data source configuration in the projects directory.
        
        Args:
            extensions: Optional file extensions to filter
            
        Returns:
            List of file information
        """
        upload_dir: Path = settings.PROJECTS_DIR

        if not upload_dir.exists():
            return []

        ext_set: set[str] | None = None
        if extensions:
            ext_set = {f".{ext.lstrip('.').lower()}" for ext in extensions if ext}

        files: list[ProjectFileInfo] = []
        for file_path in sorted(upload_dir.glob("*")):
            if not file_path.is_file():
                continue

            if ext_set and file_path.suffix.lower() not in ext_set:
                continue

            stat = file_path.stat()
            files.append(
                ProjectFileInfo(
                    name=file_path.name,
                    path=self._to_public_path(file_path),
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )

        return files

    def save_data_source_file(
        self,
        upload: UploadFile,
        *,
        allowed_extensions: set[str] | None = None,
        max_size_mb: int = MAX_PROJECT_UPLOAD_SIZE_MB,
    ) -> ProjectFileInfo:
        """Save an uploaded file into the projects directory (global data source).
        
        Args:
            upload: Uploaded file
            allowed_extensions: Allowed file extensions
            max_size_mb: Maximum file size in megabytes
            
        Returns:
            File information for the saved file
            
        Raises:
            BadRequestError: If file type or size is invalid
        """
        allowed: set[str] = allowed_extensions or set()

        filename: str = self._sanitize_filename(upload.filename)
        ext: str = Path(filename).suffix.lower()
        if allowed and ext not in allowed:
            allowed_list: str = ", ".join(sorted(allowed))
            raise BadRequestError(f"Unsupported file type '{ext}'. Allowed: {allowed_list}")

        upload_dir: Path = settings.PROJECTS_DIR
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
            path=self._to_public_path(target_path),
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
        )

    # Excel metadata extraction

    def get_excel_metadata(
        self, file_path: str, sheet_name: str | None = None, cell_range: str | None = None
    ) -> tuple[list[str], list[str]]:
        """Return available sheets and columns for an Excel file.

        Args:
            file_path: Path (absolute or relative to project root) to the Excel file
            sheet_name: Optional sheet to inspect for columns
            cell_range: Optional cell range (e.g., 'A1:H30') to limit columns

        Returns:
            Tuple of (sheet_names, column_names)

        Raises:
            BadRequestError: If file is missing/unsupported or sheet is not found
        """
        resolved_path: Path = self._resolve_path(file_path)
        return extract_excel_metadata(resolved_path, sheet_name=sheet_name, cell_range=cell_range)
