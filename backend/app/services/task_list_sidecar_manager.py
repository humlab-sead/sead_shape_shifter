"""Service for managing task list sidecar files (shapeshifter.tasks.yml).

Task sidecar state is stored separately from the main project file to allow for
independent task tracking without affecting project structure. This enables:
- Task state persistence without modifying project entities
- Entity notes stored next to task state in the same sidecar file
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

    def _normalize_task_list_data(self, task_list_data: dict[str, Any]) -> dict[str, Any]:
        """Normalize task list data to the current server-side schema.

        This centralizes legacy migration at the file boundary so callers receive a
        consistent task list shape regardless of what is stored on disk.
        """
        return TaskList(task_list_data).to_dict()

    def _normalize_notes_data(self, notes_data: dict[str, Any]) -> dict[str, str]:
        """Normalize notes data to a canonical entity -> note mapping."""
        normalized: dict[str, str] = {}
        for entity_name, note in notes_data.items():
            if not isinstance(entity_name, str) or not isinstance(note, str):
                continue

            cleaned_note = note.rstrip()
            if cleaned_note.strip():
                normalized[entity_name] = cleaned_note

        return normalized

    def load_sidecar_data(self, project_file_path: Path) -> dict[str, Any]:
        """Load canonical sidecar content from disk.

        Returns a dictionary containing optional top-level keys:
        - task_list: normalized task list state
        - notes: normalized entity note mapping

        Older sidecar files with task state stored at the root are still supported.
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

            if not isinstance(data, dict):
                logger.warning(f"Unexpected sidecar structure in {sidecar_path}: {type(data).__name__}")
                return {}

            has_explicit_sections = any(key in data for key in ("task_list", "notes"))

            if has_explicit_sections:
                task_list_data = data.get("task_list", {}) if isinstance(data.get("task_list", {}), dict) else {}
                notes_data = data.get("notes", {}) if isinstance(data.get("notes", {}), dict) else {}
            else:
                task_list_data = data
                notes_data = {}

            normalized_task_list = self._normalize_task_list_data(task_list_data)
            normalized_notes = self._normalize_notes_data(notes_data)

            normalized_sidecar: dict[str, Any] = {}
            if normalized_task_list:
                normalized_sidecar["task_list"] = normalized_task_list
            if normalized_notes:
                normalized_sidecar["notes"] = normalized_notes

            if normalized_sidecar != data:
                self.yaml_service.save(normalized_sidecar, sidecar_path)
                logger.info(f"Normalized task sidecar: {sidecar_path}")

            logger.debug(f"Loaded task sidecar: {sidecar_path}")
            return normalized_sidecar

        except Exception as e:  # noqa: PERF203 ; pylint: disable=broad-exception-caught
            logger.error(f"Failed to load task sidecar {sidecar_path}: {e}")
            return {}

    def load_task_list(self, project_file_path: Path) -> dict[str, Any]:
        """Load task list from sidecar file if it exists.

        Implements backward compatibility:
        - If sidecar exists, load from sidecar
        - Otherwise, return empty dict (task_list will be loaded from main file if present)

        Args:
            project_file_path: Path to shapeshifter.yml

        Returns:
            Task list configuration dict (keys: todo, done, ongoing, ignored, flagged)
            Returns empty dict if sidecar doesn't exist
        """
        return self.load_sidecar_data(project_file_path).get("task_list", {})

    def load_notes(self, project_file_path: Path) -> dict[str, str]:
        """Load entity notes from the sidecar file if they exist."""
        return self.load_sidecar_data(project_file_path).get("notes", {})

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

            # Convert TaskList to dict and preserve other sidecar metadata.
            task_list_dict = task_list.to_dict()
            sidecar_data = self.load_sidecar_data(project_file_path)

            payload: dict[str, Any] = {}
            if task_list_dict:
                payload["task_list"] = task_list_dict
            if sidecar_data.get("notes"):
                payload["notes"] = sidecar_data["notes"]

            # Write to sidecar
            self.yaml_service.save(payload, sidecar_path)

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
                normalized_task_list = self._normalize_task_list_data(task_list_in_main)
                self.yaml_service.save({"task_list": normalized_task_list}, sidecar_path)

                # Remove from main file
                project_data = dict(project_data)  # Copy to avoid mutating input
                del project_data["task_list"]

                logger.info(f"Migrated task_list to sidecar for {project_file_path.name}")

                return project_data

            except Exception as e:  # noqa: PERF203 ; pylint: disable=broad-exception-caught
                logger.error(f"Failed to migrate task_list: {e}")
                # Continue without migration - main file will be used

        return project_data

    def get_note(self, project_file_path: Path, entity_name: str) -> str | None:
        """Return the note for an entity if one exists."""
        return self.load_notes(project_file_path).get(entity_name)

    def set_note(self, project_file_path: Path, entity_name: str, note: str) -> str | None:
        """Create or update a note for an entity.

        Empty or whitespace-only notes are removed instead of persisted.
        """
        sidecar_path = self.get_sidecar_path(project_file_path)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        normalized_note = note.rstrip()
        if not normalized_note.strip():
            self.remove_note(project_file_path, entity_name)
            return None

        sidecar_data = self.load_sidecar_data(project_file_path)
        notes = dict(sidecar_data.get("notes", {}))
        notes[entity_name] = normalized_note

        payload: dict[str, Any] = {}
        if sidecar_data.get("task_list"):
            payload["task_list"] = sidecar_data["task_list"]
        payload["notes"] = notes

        self.yaml_service.save(payload, sidecar_path)
        logger.debug(f"Saved note for '{entity_name}' to sidecar: {sidecar_path}")
        return normalized_note

    def remove_note(self, project_file_path: Path, entity_name: str) -> bool:
        """Remove a note for an entity if it exists."""
        sidecar_path = self.get_sidecar_path(project_file_path)
        sidecar_data = self.load_sidecar_data(project_file_path)
        notes = dict(sidecar_data.get("notes", {}))

        if entity_name not in notes:
            return False

        del notes[entity_name]

        payload: dict[str, Any] = {}
        if sidecar_data.get("task_list"):
            payload["task_list"] = sidecar_data["task_list"]
        if notes:
            payload["notes"] = notes

        self.yaml_service.save(payload, sidecar_path)
        logger.debug(f"Removed note for '{entity_name}' from sidecar: {sidecar_path}")
        return True

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
            except Exception as e:  # noqa: PERF203 ; pylint: disable=broad-exception-caught
                logger.error(f"Failed to delete sidecar {sidecar_path}: {e}")
                return False

        return False
