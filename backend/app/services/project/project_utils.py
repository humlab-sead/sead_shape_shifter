"""Project utility functions for validation and existence checking.

This module provides core project validation utilities used by all project components.
"""

from pathlib import Path

from backend.app.exceptions import ResourceNotFoundError
from backend.app.mappers.project_name_mapper import ProjectNameMapper
from backend.app.utils.exceptions import BadRequestError


class ProjectUtils:
    """Utility functions for project name validation and existence checking."""

    def __init__(self, projects_dir: Path) -> None:
        """Initialize project utilities.

        Args:
            projects_dir: Root directory containing all projects
        """
        self.projects_dir = projects_dir

    def validate_project_name(self, name: str) -> str:
        """Validate project name for new directory structure.

        Allows nested relative paths like 'arbodat:arbodat-test' or 'arbodat/arbodat-test'
        but prevents directory traversal and absolute paths.
        Returns API-safe format using ':' separators.

        Args:
            name: Project name (can be nested path like 'parent:child')

        Returns:
            Validated project name

        Raises:
            BadRequestError: If name is invalid or contains directory traversal
        """
        safe_name: str = name.strip()
        if not safe_name:
            raise BadRequestError("Project name cannot be empty")

        # Prevent directory traversal attacks
        if ".." in safe_name:
            raise BadRequestError("Invalid project name: directory traversal not allowed")

        if safe_name.startswith("/"):
            raise BadRequestError("Project name cannot be an absolute path")

        if "\\" in safe_name:
            raise BadRequestError("Invalid project name: backslashes are not allowed")

        normalized_name = safe_name.replace("/", ":")

        # Reject empty segments like ':foo', 'foo:', 'foo::bar', 'foo//bar'
        if normalized_name.startswith(":") or normalized_name.endswith(":") or "::" in normalized_name:
            raise BadRequestError("Invalid project name: empty path segments are not allowed")

        if Path(normalized_name.replace(":", "/")).is_absolute():
            raise BadRequestError("Project name cannot be an absolute path")

        return normalized_name

    def ensure_project_exists(self, name: str) -> Path:
        """Ensure project exists in new directory structure.

        Args:
            name: Project name to validate (uses ':' for nested paths)

        Returns:
            Path to the project's shapeshifter.yml file

        Raises:
            BadRequestError: If project name is invalid
            ResourceNotFoundError: If project does not exist
        """
        safe_name: str = self.validate_project_name(name)
        # Convert API name to filesystem path (: -> /)
        project_file: Path = self.projects_dir / ProjectNameMapper.to_path(safe_name) / "shapeshifter.yml"

        if not project_file.exists():
            raise ResourceNotFoundError(
                resource_type="project", resource_id=name, message=f"Project not found: {name} (expected: {project_file})"
            )

        return project_file
