"""Project utility functions for validation and existence checking.

This module provides core project validation utilities used by all project components.
"""

from pathlib import Path

from backend.app.exceptions import ResourceNotFoundError
from backend.app.mappers.project_name_mapper import ProjectNameMapper
from backend.app.utils.exceptions import BadRequestError
from src.path_resolution import resolve_contained_path


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

    def resolve_project_dir(self, name: str) -> Path:
        """Validate a project name and resolve its directory inside the projects root.

        Runs ``validate_project_name`` then resolves the mapped path through
        ``resolve_contained_path`` so the result is guaranteed to stay under
        ``projects_dir``. This blocks traversal (``../../x``), absolute names,
        and colon aliases (``up:../victim``) that would otherwise point at
        another project's file or write outside the managed root.

        Args:
            name: Project name (uses ':' for nested paths)

        Returns:
            Resolved project directory, guaranteed to be under ``projects_dir``

        Raises:
            BadRequestError: If the name is invalid or resolves outside the projects root
        """
        safe_name: str = self.validate_project_name(name)
        try:
            return resolve_contained_path(ProjectNameMapper.to_path(safe_name), self.projects_dir)
        except ValueError as exc:
            raise BadRequestError(f"Invalid project name: {name}") from exc

    def resolve_project_file(self, name: str) -> Path:
        """Validate a project name and resolve its ``shapeshifter.yml`` path.

        Containment is checked on the project directory, then the config file
        name is appended, so the returned path stays under ``projects_dir``.

        Args:
            name: Project name (uses ':' for nested paths)

        Returns:
            Resolved path to the project's ``shapeshifter.yml`` file

        Raises:
            BadRequestError: If the name is invalid or resolves outside the projects root
        """
        return self.resolve_project_dir(name) / "shapeshifter.yml"
