"""
Service for applying automatic fixes to configurations.
"""

import abc
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.core.config import settings
from backend.app.models.fix import FixAction, FixActionType, FixResult, FixSuggestion
from backend.app.models.project import Project
from backend.app.models.validation import ValidationError
from backend.app.services.project_service import ProjectService
from backend.app.services.yaml_service import YamlService


class AutoFixStrategy(abc.ABC):
    """Abstract base class for auto-fix strategies."""

    @abc.abstractmethod
    def resolve(self, error: ValidationError) -> FixSuggestion | None:
        """Generate a fix suggestion for a given validation error."""


class ColumnNotFoundAutoFixStrategy(AutoFixStrategy):

    def resolve(self, error: ValidationError) -> FixSuggestion | None:
        """Generate fix for missing column error."""
        if not error.field or not error.entity:
            return None

        match = re.search(r"Column '([^']+)' not found", error.message)
        if not match:
            return None

        column_name: str | Any = match.group(1)

        # Check if it's a reference that needs resolution
        if "@value:" in column_name:
            return None  # Handle separately as unresolved reference

        return FixSuggestion(
            issue_code=error.code or "",
            entity=error.entity,
            field=error.field,
            suggestion=f"Remove column '{column_name}' from project as it doesn't exist in the data",
            actions=[
                FixAction(
                    type=FixActionType.REMOVE_COLUMN,
                    entity=error.entity,
                    field="columns",
                    old_value=column_name,
                    new_value=None,
                    description=f"Remove non-existent column '{column_name}'",
                )
            ],
            auto_fixable=True,
            requires_confirmation=True,
            warnings=["This will remove the column from your project"],
        )


class UnresolvedReferenceAutoFixStrategy(AutoFixStrategy):

    def resolve(self, error: ValidationError) -> FixSuggestion | None:
        """Generate fix for unresolved @value reference."""
        if not error.entity:
            return None

        # These typically need manual intervention
        return FixSuggestion(
            issue_code=error.code or "UNRESOLVED_REFERENCE",
            entity=error.entity,
            field=error.field,
            suggestion="Unresolved references require manual intervention - verify referenced entity name and fields",
            actions=[],
            auto_fixable=False,
            requires_confirmation=False,
            warnings=["This cannot be fixed automatically"],
        )


class DuplicateKeysAutoFixStrategy(AutoFixStrategy):

    def resolve(self, error: ValidationError) -> FixSuggestion | None:
        """Generate fix for duplicate natural keys."""
        if not error.entity:
            return None

        # Duplicate keys typically require manual data cleaning
        return FixSuggestion(
            issue_code=error.code or "DUPLICATE_KEYS",
            entity=error.entity,
            field=error.field,
            suggestion="Duplicate natural keys require data cleaning or adjusting the key project",
            actions=[],
            auto_fixable=False,
            requires_confirmation=False,
            warnings=["This requires reviewing your data or changing the natural key definition"],
        )


class SystemIdNullValuesAutoFixStrategy(AutoFixStrategy):
    """Auto-fix strategy for null system_id values in fixed entities."""

    def resolve(self, error: ValidationError) -> FixSuggestion | None:
        """Generate fix for null system_id values."""
        if not error.entity or error.code != "SYSTEM_ID_NULL_VALUES":
            return None

        return FixSuggestion(
            issue_code="SYSTEM_ID_NULL_VALUES",
            entity=error.entity,
            field="values",
            suggestion="Fill null system_id values with sequential numbers starting from max(system_id) + 1",
            actions=[
                FixAction(
                    type=FixActionType.UPDATE_VALUES,
                    entity=error.entity,
                    field="values",
                    old_value=None,
                    new_value="fill_null_system_ids",  # Signal for special handling
                    description="Fill null system_id values with sequential IDs",
                )
            ],
            auto_fixable=True,
            requires_confirmation=True,
            warnings=["This will assign new system_id values to rows with null values"],
        )


class SystemIdDuplicateValuesAutoFixStrategy(AutoFixStrategy):
    """Auto-fix strategy for duplicate system_id values in fixed entities."""

    def resolve(self, error: ValidationError) -> FixSuggestion | None:
        """Generate fix for duplicate system_id values."""
        if not error.entity or error.code != "SYSTEM_ID_DUPLICATE_VALUES":
            return None

        return FixSuggestion(
            issue_code="SYSTEM_ID_DUPLICATE_VALUES",
            entity=error.entity,
            field="values",
            suggestion="Reassign duplicate system_id values to make them unique (preserving first occurrence, updating duplicates)",
            actions=[
                FixAction(
                    type=FixActionType.UPDATE_VALUES,
                    entity=error.entity,
                    field="values",
                    old_value=None,
                    new_value="fix_duplicate_system_ids",  # Signal for special handling
                    description="Reassign duplicate system_id values",
                )
            ],
            auto_fixable=True,
            requires_confirmation=True,
            warnings=["This will reassign system_id values for duplicate rows, which may affect FK relationships"],
        )


class SystemIdInvalidValueAutoFixStrategy(AutoFixStrategy):
    """Auto-fix strategy for invalid system_id values (non-integer, negative, zero)."""

    def resolve(self, error: ValidationError) -> FixSuggestion | None:
        """Generate fix for invalid system_id values."""
        if not error.entity or error.code not in ("SYSTEM_ID_INVALID_TYPE", "SYSTEM_ID_INVALID_VALUE"):
            return None

        return FixSuggestion(
            issue_code=error.code,
            entity=error.entity,
            field="values",
            suggestion="Replace invalid system_id values with sequential positive integers",
            actions=[
                FixAction(
                    type=FixActionType.UPDATE_VALUES,
                    entity=error.entity,
                    field="values",
                    old_value=None,
                    new_value="fix_invalid_system_ids",  # Signal for special handling
                    description="Replace invalid system_id values",
                )
            ],
            auto_fixable=True,
            requires_confirmation=True,
            warnings=["This will replace invalid system_id values, which may affect FK relationships"],
        )


AutoFixStrategies: dict[str, AutoFixStrategy] = {  # pylint: disable=invalid-name
    "COLUMN_NOT_FOUND": ColumnNotFoundAutoFixStrategy(),
    "UNRESOLVED_REFERENCE": UnresolvedReferenceAutoFixStrategy(),
    "DUPLICATE_NATURAL_KEYS": DuplicateKeysAutoFixStrategy(),
    "SYSTEM_ID_NULL_VALUES": SystemIdNullValuesAutoFixStrategy(),
    "SYSTEM_ID_DUPLICATE_VALUES": SystemIdDuplicateValuesAutoFixStrategy(),
    "SYSTEM_ID_INVALID_TYPE": SystemIdInvalidValueAutoFixStrategy(),
    "SYSTEM_ID_INVALID_VALUE": SystemIdInvalidValueAutoFixStrategy(),
}


class AutoFixService:
    """Service to apply automatic fixes to configurations."""

    def __init__(self, project_service: ProjectService):
        self.project_service: ProjectService = project_service
        self.yaml_service = YamlService()

    def generate_fix_suggestions(self, errors: list[ValidationError]) -> list[FixSuggestion]:
        """Generate fix suggestions from validation errors."""
        suggestions = []
        for error in errors:
            if not error.entity:
                continue
            strategy: AutoFixStrategy | None = AutoFixStrategies.get(error.code or "")
            if strategy:
                suggestion: FixSuggestion | None = strategy.resolve(error)
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions

    async def preview_fixes(self, project_name: str, suggestions: list[FixSuggestion]) -> dict[str, Any]:
        """
        Preview what fixes would be applied without actually applying them.

        Args:
            project_name: Project name
            suggestions: List of fix suggestions to preview

        Returns:
            Preview of changes that would be made
        """
        project: Project = self.project_service.load_project(project_name)
        if not project:
            return {"error": f"Project '{project_name}' not found"}

        changes = []

        for suggestion in suggestions:
            if not suggestion.auto_fixable:
                continue

            for action in suggestion.actions:
                change_desc = {
                    "entity": action.entity,
                    "field": action.field,
                    "action_type": action.type,
                    "description": action.description,
                    "old_value": action.old_value,
                    "new_value": action.new_value,
                }
                changes.append(change_desc)

        return {
            "project_name": project_name,
            "fixable_count": len([s for s in suggestions if s.auto_fixable]),
            "total_suggestions": len(suggestions),
            "changes": changes,
        }

    async def apply_fixes(self, project_name: str, suggestions: list[FixSuggestion]) -> FixResult:
        """
        Apply fixes to project.

        Args:
            project_name: Project name
            suggestions: List of fix suggestions to apply

        Returns:
            Result of applying fixes
        """
        try:
            project: Project = self.project_service.load_project(project_name)
            if not project:
                return FixResult(success=False, fixes_applied=0, errors=[f"Configuration '{project_name}' not found"])

            # Create backup before applying fixes
            backup_path: Path = self._create_backup(project_name)

            # Track applied fixes
            fixes_applied: int = 0
            errors = []
            warnings = []

            # Apply each fix
            for suggestion in suggestions:
                if not suggestion.auto_fixable:
                    warnings.append(f"Skipping non-auto-fixable issue in entity '{suggestion.entity}'")
                    continue
                for action in suggestion.actions:
                    try:
                        self._apply_action(project, action)
                        fixes_applied += 1
                    except Exception as e:  # pylint: disable=broad-except
                        logger.error(f"Failed to apply fix: {e}")
                        errors.append(f"Failed to apply fix for {action.entity}: {str(e)}")

            if not errors:
                # Save updated project
                # Project is already a dict, no need to call model_dump
                project_dict = project if isinstance(project, dict) else project.model_dump(exclude_none=True, by_alias=True)

                self.project_service.save_project(project, create_backup=True)

                return FixResult(
                    success=True,
                    fixes_applied=fixes_applied,
                    warnings=warnings,
                    backup_path=str(backup_path),
                    updated_config=project_dict,
                )
            # Rollback on error
            self._rollback(project_name, backup_path)
            return FixResult(success=False, fixes_applied=0, errors=errors, warnings=warnings)

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Auto-fix failed: {e}")
            return FixResult(success=False, fixes_applied=0, errors=[str(e)])

    def _create_backup(self, project_name: str) -> Path:
        """Create backup of project before applying fixes."""

        # New structure: projects_dir/project_name/shapeshifter.yml
        project_dir = settings.PROJECTS_DIR / project_name
        project_path = project_dir / "shapeshifter.yml"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = project_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        backup_path = backup_dir / f"shapeshifter.backup.{timestamp}.yml"
        shutil.copy2(project_path, backup_path)

        logger.info(f"Created backup at {backup_path}")
        return backup_path

    def _rollback(self, project_name: str, backup_path: Path):
        """Rollback project to backup."""

        # New structure: projects_dir/project_name/shapeshifter.yml
        project_dir = settings.PROJECTS_DIR / project_name
        project_path = project_dir / "shapeshifter.yml"

        shutil.copy2(backup_path, project_path)
        logger.info(f"Rolled back project from {backup_path}")

    def _apply_action(self, project: Any, action: FixAction):
        """Apply a single fix action to project."""
        if action.type == FixActionType.REMOVE_COLUMN:
            self._remove_column(project, action)
        elif action.type == FixActionType.ADD_COLUMN:
            self._add_column(project, action)
        elif action.type == FixActionType.UPDATE_REFERENCE:
            self._update_reference(project, action)
        elif action.type == FixActionType.UPDATE_VALUES:
            self._update_values(project, action)
        else:
            raise ValueError(f"Unsupported action type: {action.type}")

    def _remove_column(self, project: Any, action: FixAction):
        """Remove a column from entity project."""
        # Handle both dict and object project
        entities = project.get("entities") if isinstance(project, dict) else project.entities
        if not entities:
            return

        entity = entities.get(action.entity)
        if not entity:
            return

        # Handle both dict and object entity
        columns = entity.get("columns") if isinstance(entity, dict) else getattr(entity, "columns", None)
        if not columns or action.old_value not in columns:
            return

        columns.remove(action.old_value)
        logger.info(f"Removed column '{action.old_value}' from entity '{action.entity}'")

    def _add_column(self, project: Any, action: FixAction):
        """Add a column to entity project."""
        # Handle both dict and object config
        entities = project.get("entities") if isinstance(project, dict) else project.entities
        if not entities:
            return

        entity = entities.get(action.entity)
        if not entity:
            return

        # Handle both dict and object entity
        if isinstance(entity, dict):
            if "columns" not in entity:
                entity["columns"] = []
            columns = entity["columns"]
        else:
            if not hasattr(entity, "columns") or entity.columns is None:
                entity.columns = []
            columns = entity.columns

        if action.new_value and action.new_value not in columns:
            columns.append(action.new_value)
            logger.info(f"Added column '{action.new_value}' to entity '{action.entity}'")

    def _update_reference(self, config: Any, action: FixAction):
        """Update a @value reference in entity project."""
        # Handle both dict and object config
        entities = config.get("entities") if isinstance(config, dict) else config.entities
        if not entities:
            return

        entity = entities.get(action.entity)
        if not entity:
            return

        # This is complex and may require deep inspection of config
        # For now, just log it
        logger.warning(f"Reference update not yet implemented for entity '{action.entity}'")

    def _update_values(self, project: Any, action: FixAction):
        """Update values array for fixed entity (system_id repair)."""
        # Handle both dict and object config
        entities = project.get("entities") if isinstance(project, dict) else project.entities
        if not entities:
            return

        entity = entities.get(action.entity)
        if not entity:
            return

        # Get entity data
        entity_type = entity.get("type") if isinstance(entity, dict) else getattr(entity, "type", None)
        if entity_type != "fixed":
            logger.warning(f"Entity '{action.entity}' is not a fixed entity, cannot update values")
            return

        columns = entity.get("columns") if isinstance(entity, dict) else getattr(entity, "columns", None)
        values = entity.get("values") if isinstance(entity, dict) else getattr(entity, "values", None)

        if not columns or not isinstance(values, list):
            logger.warning(f"Entity '{action.entity}' has invalid columns or values structure")
            return

        # Find system_id column index
        try:
            system_id_index = columns.index("system_id")
        except ValueError:
            logger.warning(f"Entity '{action.entity}' does not have a system_id column")
            return

        # Apply the appropriate fix based on new_value signal
        if action.new_value == "fill_null_system_ids":
            self._fill_null_system_ids(values, system_id_index, action.entity)
        elif action.new_value == "fix_duplicate_system_ids":
            self._fix_duplicate_system_ids(values, system_id_index, action.entity)
        elif action.new_value == "fix_invalid_system_ids":
            self._fix_invalid_system_ids(values, system_id_index, action.entity)

    def _fill_null_system_ids(self, values: list[list[Any]], system_id_index: int, entity_name: str):
        """Fill null system_id values with sequential numbers."""
        # Find max existing system_id
        max_id = 0
        for row in values:
            if len(row) > system_id_index:
                val = row[system_id_index]
                if val is not None:
                    try:
                        max_id = max(max_id, int(val))
                    except (ValueError, TypeError):
                        pass

        # Fill nulls
        next_id = max_id + 1
        filled_count = 0
        for row in values:
            if len(row) > system_id_index:
                if row[system_id_index] is None:
                    row[system_id_index] = next_id
                    next_id += 1
                    filled_count += 1

        logger.info(f"Filled {filled_count} null system_id values in entity '{entity_name}'")

    def _fix_duplicate_system_ids(self, values: list[list[Any]], system_id_index: int, entity_name: str):
        """Fix duplicate system_id values by reassigning duplicates."""
        # Find max existing system_id and track seen IDs
        max_id = 0
        seen_ids = set()

        for row in values:
            if len(row) > system_id_index:
                val = row[system_id_index]
                if val is not None:
                    try:
                        id_num = int(val)
                        seen_ids.add(id_num)
                        max_id = max(max_id, id_num)
                    except (ValueError, TypeError):
                        pass

        # Reassign duplicates
        next_id = max_id + 1
        seen_in_pass = set()
        fixed_count = 0

        for row in values:
            if len(row) > system_id_index:
                val = row[system_id_index]
                if val is not None:
                    try:
                        id_num = int(val)
                        # If we've seen this ID in this pass, it's a duplicate - reassign
                        if id_num in seen_in_pass:
                            # Find next unused ID
                            while next_id in seen_ids:
                                next_id += 1
                            row[system_id_index] = next_id
                            seen_ids.add(next_id)
                            next_id += 1
                            fixed_count += 1
                        else:
                            seen_in_pass.add(id_num)
                    except (ValueError, TypeError):
                        pass

        logger.info(f"Fixed {fixed_count} duplicate system_id values in entity '{entity_name}'")

    def _fix_invalid_system_ids(self, values: list[list[Any]], system_id_index: int, entity_name: str):
        """Fix invalid system_id values (non-integer, negative, zero)."""
        # Find max valid system_id
        max_id = 0
        for row in values:
            if len(row) > system_id_index:
                val = row[system_id_index]
                if val is not None:
                    try:
                        id_num = int(val)
                        if id_num > 0 and id_num > max_id:
                            max_id = id_num
                    except (ValueError, TypeError):
                        pass

        # Fix invalid values
        next_id = max_id + 1
        fixed_count = 0
        for row in values:
            if len(row) > system_id_index:
                val = row[system_id_index]
                is_invalid = False

                if val is None:
                    is_invalid = True
                else:
                    try:
                        id_num = int(val)
                        if id_num <= 0:
                            is_invalid = True
                    except (ValueError, TypeError):
                        is_invalid = True

                if is_invalid:
                    row[system_id_index] = next_id
                    next_id += 1
                    fixed_count += 1

        logger.info(f"Fixed {fixed_count} invalid system_id values in entity '{entity_name}'")
