"""YAML Service for loading and saving configuration files with format preservation."""

import shutil
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from loguru import logger
from ruamel.yaml import YAML

from backend.app.core.config import settings


class YamlServiceError(Exception):
    """Base exception for YAML service errors."""


class YamlLoadError(YamlServiceError):
    """Raised when YAML file cannot be loaded."""


class YamlSaveError(YamlServiceError):
    """Raised when YAML file cannot be saved."""


class YamlService:
    """Service for loading and saving YAML files with format preservation."""

    def __init__(self) -> None:
        """Initialize YAML service with ruamel.yaml."""
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False
        self.yaml.width = 4096  # Prevent line wrapping
        self.yaml.indent(mapping=2, sequence=2, offset=0)

    def load(self, filename: str | Path) -> dict[str, Any]:
        """
        Load YAML file preserving format and comments.

        Args:
            filename: Path to YAML file

        Returns:
            Parsed YAML data as dictionary

        Raises:
            YamlLoadError: If file cannot be loaded or parsed
        """
        path = Path(filename)

        if not path.exists():
            raise YamlLoadError(f"File not found: {path}")

        if not path.is_file():
            raise YamlLoadError(f"Not a file: {path}")

        try:
            logger.debug(f"Loading YAML file: {path}")
            with path.open("r", encoding="utf-8") as f:
                data = self.yaml.load(f)

            if data is None:
                logger.warning(f"Empty YAML file: {path}")
                return {}

            if not isinstance(data, dict):
                raise YamlLoadError(f"YAML root must be a dictionary, got {type(data).__name__}")

            logger.info(f"Successfully loaded YAML file: {path} ({len(str(data))} bytes)")
            return dict(data)

        except Exception as e:
            logger.error(f"Failed to load YAML file {path}: {e}")
            raise YamlLoadError(f"Failed to parse YAML file {path}: {e}") from e

    def save(
        self,
        data: dict[str, Any],
        filename: str | Path,
        create_backup: bool = True,
    ) -> Path:
        """
        Save data to YAML file with atomic write and optional backup.

        Uses atomic write pattern: write to temp file, then rename.
        This ensures the original file is never corrupted.

        Args:
            data: Data to save
            file_path: Target file path
            create_backup: Whether to create backup before saving

        Returns:
            Path to saved file

        Raises:
            YamlSaveError: If file cannot be saved
        """
        path = Path(filename)
        temp_path: Path = path.with_suffix(path.suffix + ".tmp")

        try:
            if create_backup and path.exists():
                backup_path = self.create_backup(path)
                logger.info(f"Created backup: {backup_path}")

            path.parent.mkdir(parents=True, exist_ok=True)

            logger.debug(f"Writing to temporary file: {temp_path}")

            with temp_path.open("w", encoding="utf-8") as f:
                self.yaml.dump(data, f)

            temp_path.replace(path)
            logger.info(f"Successfully saved YAML file: {path}")

            return path

        except Exception as e:
            logger.error(f"Failed to save YAML file {path}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise YamlSaveError(f"Failed to save YAML file {path}: {e}") from e

    def create_backup(self, file_path: str | Path) -> Path:
        """
        Create timestamped backup of file.

        Args:
            file_path: File to backup

        Returns:
            Path to backup file

        Raises:
            YamlServiceError: If backup cannot be created
        """
        path = Path(file_path)

        if not path.exists():
            raise YamlServiceError(f"Cannot backup non-existent file: {path}")

        # Create backup directory
        backup_dir = settings.BACKUPS_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp with microseconds to avoid collisions
        timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name: str = f"{path.stem}.backup.{timestamp}{path.suffix}"
        backup_path: Path = backup_dir / backup_name

        try:
            logger.debug(f"Creating backup: {path} -> {backup_path}")
            shutil.copy2(path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup of {path}: {e}")
            raise YamlServiceError(f"Failed to create backup: {e}") from e

    def validate_yaml(self, content: str) -> tuple[bool, str | None]:
        """
        Validate YAML content without loading.

        Args:
            content: YAML content as string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:

            self.yaml.load(StringIO(content))
            return True, None
        except Exception as e:  # pylint: disable=broad-except
            return False, str(e)

    def list_backups(self, original_name: str | None = None) -> list[Path]:
        """
        List all backup files, optionally filtered by original filename.

        Args:
            original_name: Optional original filename to filter by (e.g., "arbodat.yml")

        Returns:
            List of backup file paths, sorted by modification time (newest first)
        """
        backup_dir = settings.BACKUPS_DIR

        if not backup_dir.exists():
            return []

        pattern = "*.backup.*"
        if original_name:
            stem = Path(original_name).stem
            pattern = f"{stem}.backup.*"

        backups = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

        logger.debug(f"Found {len(backups)} backup(s) for pattern '{pattern}'")
        return list(backups)

    def restore_backup(self, backup_path: str | Path, target_path: str | Path, create_backup: bool = True) -> Path:
        """
        Restore a backup file to target location.

        Args:
            backup_path: Path to backup file
            target_path: Target path for restoration
            create_backup: Whether to backup current file before restoring

        Returns:
            Path to restored file

        Raises:
            YamlServiceError: If restoration fails
        """
        backup = Path(backup_path)
        target = Path(target_path)

        if not backup.exists():
            raise YamlServiceError(f"Backup file not found: {backup}")

        try:
            # Create backup of current file before restoring
            if create_backup and target.exists():
                self.create_backup(target)

            # Copy backup to target
            shutil.copy2(backup, target)
            logger.info(f"Restored backup: {backup} -> {target}")
            return target

        except Exception as e:
            logger.error(f"Failed to restore backup {backup}: {e}")
            raise YamlServiceError(f"Failed to restore backup: {e}") from e


# Singleton instance
_yaml_service: YamlService | None = None  # pylint: disable=invalid-name


def get_yaml_service() -> YamlService:
    """Get singleton YamlService instance."""
    global _yaml_service  # pylint: disable=global-statement
    if _yaml_service is None:
        _yaml_service = YamlService()
    return _yaml_service
