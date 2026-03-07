"""Service for managing task list sidecar files (shapeshifter.tasks.yml).

Task list state is stored separately from the main project file to allow for
independent task tracking without affecting project structure. This enables:
- Task state persistence without modifying project entities
- Easy migration from in-file task_list to sidecar
- Backward compatibility with projects that still have task_list in main file
"""

from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.services.yaml_service import YamlService, get_yaml_service
from src.model import TaskList


class TaskListSidecarManager:
    """Manager for task list sidecar files (shapeshifter.tasks.yml)."""

    SIDECAR_FILENAME = "shapeshifter.tasks.yml"

    def __init__(self, yaml_service: YamlService | None = None) -> None:
        """Initialize the task list sidecar manager.

        Args:
            yaml_service: YAML service for file operations (default: get_yaml_service())
        """
        self.yaml_service = yaml_service or get_yaml_service()

    def get_sidecar_path(self, project_file_path: Path) -> Path:
        """Get the sidecar file path for a project file.

        Args:
            project_file_path: Path to shapeshifter.yml

        Returns:
            Path to shapeshifter.tasks.yml (in same directory as project file)
        """
        project_dir = project_file_path.parent
        return project_dir / self.SIDECAR_FILENAME

    def sidecar_exists(self, project_file_path: Path) -> bool:
        """Check if sidecar file exists for a project.

        Args:
            project_file_path: Path to shapeshifter.yml

        Returns:
            True if shapeshifter.tasks.yml exists
        """
        sidecar_path = self.get_sidecar_path(project_file_path)
        return sidecar_path.exists()

    def load_task_list(self, project_file_path: Path) -> dict[str, Any]:
        """Load task list from sidecar file if it exists.

        Implements backward compatibility:
        - If sidecar exists, load from sidecar
        - Otherwise, return empty dict (task_list will be loaded from main file if present)

        Args:
            project_file_path: Path to shapeshifter.yml

        Returns:
            Task list configuration dict (keys: required_entities, completed, ongoing, ignored, flagged)
            Returns empty dict if sidecar doesn't exist
        """
        sidecar_path = self.get_sidecar_path(project_file_path)

        if not sidecar_path.exists():
            logger.debug(f"Sidecar not found for {project_file_path.name}: {sidecar_path}")
            return {}

        try:
            data = self.yaml_service.load(sidecar_path)
            if data is None:
                logger.warning(f"Sidecar file is empty: {sidecar_path}")
                return {}

            # Extract task_list section or use root as task_list
            task_list_data = data.get("task_list", data if isinstance(data, dict) else {})

            logger.debug(f"Loaded task list from sidecar: {sidecar_path}")
            return task_list_data

        except Exception as e:
            logger.error(f"Failed to load task list sidecar {sidecar_path}: {e}")
            return {}

    def save_task_list(self, project_file_path: Path, task_list: TaskList) -> None:
        """Save task list to sidecar file.

        Args:
            project_file_path: Path to shapeshifter.yml
            task_list: TaskList object to save

        Raises:
            IOError: If write fails
        """
        sidecar_path = self.get_sidecar_path(project_file_path)

        try:
            # Create parent directory if needed
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert TaskList to dict
            task_list_dict = task_list.to_dict()

            # Write to sidecar
            self.yaml_service.save({"task_list": task_list_dict}, sidecar_path)

            logger.debug(f"Saved task list to sidecar: {sidecar_path}")

        except Exception as e:
            logger.error(f"Failed to save task list sidecar {sidecar_path}: {e}")
            raise

    def migrate_task_list(self, project_file_path: Path, project_data: dict[str, Any]) -> dict[str, Any]:
        """Migrate task_list from main project file to sidecar.

        One-time migration: if project has task_list in main file and no sidecar exists,
        copy task_list to sidecar and remove from main file.

        Args:
            project_file_path: Path to shapeshifter.yml
            project_data: Loaded project configuration

        Returns:
            Modified project_data with task_list removed (if migration occurred)
        """
        task_list_in_main = project_data.get("task_list")
        sidecar_path = self.get_sidecar_path(project_file_path)

        # Only migrate if task_list exists in main file and sidecar doesn't exist
        if task_list_in_main and not sidecar_path.exists():
            try:
                # Save task_list to sidecar
                self.yaml_service.save({"task_list": task_list_in_main}, sidecar_path)

                # Remove from main file
                project_data = dict(project_data)  # Copy to avoid mutating input
                del project_data["task_list"]

                logger.info(f"Migrated task_list to sidecar for {project_file_path.name}")

                return project_data

            except Exception as e:
                logger.error(f"Failed to migrate task_list: {e}")
                # Continue without migration - main file will be used

        return project_data

    def delete_sidecar(self, project_file_path: Path) -> bool:
        """Delete sidecar file if it exists.

        Args:
            project_file_path: Path to shapeshifter.yml

        Returns:
            True if file was deleted, False if it didn't exist
        """
        sidecar_path = self.get_sidecar_path(project_file_path)

        if sidecar_path.exists():
            try:
                sidecar_path.unlink()
                logger.info(f"Deleted sidecar: {sidecar_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete sidecar {sidecar_path}: {e}")
                return False

        return False
