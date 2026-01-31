"""YAML Service for loading and saving configuration files with format preservation.

Features:
- Preserves comments and formatting when loading/saving YAML files
- Applies flow style to short lists for compact formatting (e.g., [item1, item2])
- Special handling for 'values' key: formats as list of rows (each row flow-style)
- Orders entity configuration keys for better readability
- Atomic writes with backup support
- Converts ruamel.yaml types to POPO at I/O boundary

Entity Key Ordering:
    Entity configurations are saved with consistent key ordering:
    1. Core identity: type, source, system_id, public_id
    2. Business keys: keys
    3. Schema: columns
    4. Data: values
    5. Relationships: foreign_keys, depends_on
    6. Operations: drop_duplicates, drop_empty_rows, check_functional_dependency
    7. Transformations: filters, unnest, append, extra_columns
    8. Custom keys (alphabetically sorted at end)
"""

import json
import shutil
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from loguru import logger
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml.scalarstring import SingleQuotedScalarString

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
        self.yaml.default_flow_style = False  # Use block style by default
        self.yaml.width = 4096  # Prevent line wrapping
        self.yaml.indent(mapping=2, sequence=2, offset=0)

    def load(self, filename: str | Path) -> dict[str, Any]:
        """
        Load YAML file preserving format and comments.

        Converts ruamel.yaml wrapper types to POPO (Plain Old Python Objects) at the I/O boundary
        to prevent pollution of service layer code with framework-specific type wrappers.

        Args:
            filename: Path to YAML file

        Returns:
            Parsed YAML data as dictionary with POPO types (no ruamel wrappers)

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

            # Convert ruamel.yaml wrapper types to POPO at I/O boundary
            # This prevents ruamel type pollution in service layer code
            data = json.loads(json.dumps(data))

            logger.info(f"Successfully loaded YAML file: {path} ({len(str(data))} bytes)")
            return data

        except Exception as e:
            logger.error(f"Failed to load YAML file {path}: {e}")
            raise YamlLoadError(f"Failed to parse YAML file {path}: {e}") from e

    def save(
        self,
        data: dict[str, Any],
        filename: str | Path,
        create_backup: bool = True,
        flow_style_max_items: int = 5,
    ) -> Path:
        """
        Save data to YAML file with atomic write and optional backup.

        Uses atomic write pattern: write to temp file, then rename.
        This ensures the original file is never corrupted.

        Short lists (≤ flow_style_max_items) will be saved in compact flow style:
        keys: [item1, item2] instead of multi-line block style.

        Entity keys are ordered for better readability (type, source, system_id, etc.).

        Args:
            data: Data to save
            file_path: Target file path
            create_backup: Whether to create backup before saving
            flow_style_max_items: Maximum list length for flow style (default 5, 0 to disable)

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

            # Order entity keys for better readability
            data = self._order_entity_keys(data)

            # Apply flow style to short lists for compact formatting
            if flow_style_max_items > 0:
                self._apply_flow_style(data, flow_style_max_items)

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

    def _order_entity_keys(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Order entity configuration keys for better readability.

        Canonical order for entity keys:
        1. Core identity: type, source, system_id, public_id
        2. Business keys: keys
        3. Schema: columns
        4. Data: values
        5. Relationships: foreign_keys, depends_on
        6. Operations: drop_duplicates, drop_empty_rows, check_functional_dependency
        7. Transformations: filters, unnest, append, extra_columns
        8. All other keys (preserved in alphabetical order)

        Args:
            data: Configuration dictionary (may contain 'entities')

        Returns:
            New dictionary with ordered keys
        """
        # Canonical order for entity configuration keys
        ENTITY_KEY_ORDER = [
            # Core identity
            "type",
            "source",
            "system_id",
            "public_id",
            # Business keys
            "keys",
            # Schema
            "columns",
            # Data
            "values",
            # Relationships
            "foreign_keys",
            "depends_on",
            # Operations
            "drop_duplicates",
            "drop_empty_rows",
            "check_functional_dependency",
            # Transformations
            "filters",
            "unnest",
            "append",
            "extra_columns",
        ]

        def order_dict_keys(d: dict[str, Any], key_order: list[str] | None = None) -> dict[str, Any]:
            """
            Reorder dictionary keys according to specified order.

            Args:
                d: Dictionary to reorder
                key_order: Preferred key order (None = preserve original order)

            Returns:
                New dictionary with ordered keys
            """
            if key_order is None:
                return d

            # Start with ordered keys that exist in dict
            ordered = {k: d[k] for k in key_order if k in d}

            # Append remaining keys in alphabetical order
            remaining = {k: d[k] for k in sorted(d.keys()) if k not in ordered}

            return {**ordered, **remaining}

        # If root level has 'entities', order each entity config
        if "entities" in data and isinstance(data["entities"], dict):
            result = dict(data)  # Shallow copy root
            result["entities"] = {
                entity_name: order_dict_keys(entity_config, ENTITY_KEY_ORDER) for entity_name, entity_config in data["entities"].items()
            }
            return result

        return data

    def _apply_flow_style(self, obj: Any, max_items: int) -> None:
        """
            Recursively mark short lists to use flow style for compact formatting.

            Lists with ≤ max_items will be formatted as [item1, item2] instead of:
            - item1
            - item2

        Special handling for 'values' key: Always formats as list of rows where
        each row is a flow-style list on its own line, regardless of max_items.

            Args:
                obj: Object to process (dict, list, or other)
                max_items: Maximum list length for flow style
        """

        def needs_flow_quote(value: str) -> bool:
            special_chars: list[str] = [":", "?", ",", "[", "]", "{", "}"]
            if any(ch in value for ch in special_chars):
                return True
            if value.startswith(("-", "?", ":")):
                return True
            if value.endswith(":"):
                return True
            if value.strip() != value:
                return True
            return False

        if isinstance(obj, dict):
            for key, value in obj.items():
                # Special case: 'values' should always be formatted as list of rows
                if key == "values" and isinstance(value, list) and value and isinstance(value[0], list):
                    # Outer list: block style (each row on its own line)
                    if not isinstance(value, CommentedSeq):
                        block_seq = CommentedSeq(value)
                        obj[key] = block_seq
                    else:
                        block_seq = value
                    # Inner lists: flow style (columns compact on one line)
                    for i, row in enumerate(block_seq):
                        if isinstance(row, list):
                            # Quote scalars that are unsafe in flow style
                            for j, cell in enumerate(row):
                                if isinstance(cell, str) and needs_flow_quote(cell):
                                    row[j] = SingleQuotedScalarString(cell)
                            if not isinstance(row, CommentedSeq):
                                flow_seq = CommentedSeq(row)
                                block_seq[i] = flow_seq
                            else:
                                flow_seq = row
                            flow_seq.fa.set_flow_style()
                # Regular handling for other keys
                elif isinstance(value, list) and 0 < len(value) <= max_items:
                    # Convert to CommentedSeq and mark for flow style
                    if not isinstance(value, CommentedSeq):
                        flow_seq = CommentedSeq(value)
                        obj[key] = flow_seq
                    else:
                        flow_seq = value
                    flow_seq.fa.set_flow_style()
                elif isinstance(value, (dict, list)):
                    self._apply_flow_style(value, max_items)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    self._apply_flow_style(item, max_items)

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
