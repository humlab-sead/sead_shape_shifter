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
            suggestion=f"Remove column '{column_name}' from configuration as it doesn't exist in the data",
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
            warnings=["This will remove the column from your configuration"],
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
            suggestion="Duplicate natural keys require data cleaning or adjusting the key configuration",
            actions=[],
            auto_fixable=False,
            requires_confirmation=False,
            warnings=["This requires reviewing your data or changing the natural key definition"],
        )


AutoFixStrategies: dict[str, AutoFixStrategy] = {  # pylint: disable=invalid-name
    "COLUMN_NOT_FOUND": ColumnNotFoundAutoFixStrategy(),
    "UNRESOLVED_REFERENCE": UnresolvedReferenceAutoFixStrategy(),
    "DUPLICATE_NATURAL_KEYS": DuplicateKeysAutoFixStrategy(),
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
        config = self.project_service.load_project(project_name)
        if not config:
            return {"error": f"Configuration '{project_name}' not found"}

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
        Apply fixes to configuration.

        Args:
            project_name: Project name
            suggestions: List of fix suggestions to apply

        Returns:
            Result of applying fixes
        """
        try:
            config: Project = self.project_service.load_project(project_name)
            if not config:
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
                        self._apply_action(config, action)
                        fixes_applied += 1
                    except Exception as e:  # pylint: disable=broad-except
                        logger.error(f"Failed to apply fix: {e}")
                        errors.append(f"Failed to apply fix for {action.entity}: {str(e)}")

            if not errors:
                # Save updated configuration
                # Config is already a dict, no need to call model_dump
                config_dict = config if isinstance(config, dict) else config.model_dump(exclude_none=True, by_alias=True)

                self.project_service.save_project(config, create_backup=True)

                return FixResult(
                    success=True,
                    fixes_applied=fixes_applied,
                    warnings=warnings,
                    backup_path=str(backup_path),
                    updated_config=config_dict,
                )
            # Rollback on error
            self._rollback(project_name, backup_path)
            return FixResult(success=False, fixes_applied=0, errors=errors, warnings=warnings)

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Auto-fix failed: {e}")
            return FixResult(success=False, fixes_applied=0, errors=[str(e)])

    def _create_backup(self, project_name: str) -> Path:
        """Create backup of configuration before applying fixes."""

        config_dir = settings.PROJECTS_DIR
        config_path = config_dir / f"{project_name}.yml"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = config_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        backup_path = backup_dir / f"{project_name}.backup.{timestamp}.yml"
        shutil.copy2(config_path, backup_path)

        logger.info(f"Created backup at {backup_path}")
        return backup_path

    def _rollback(self, project_name: str, backup_path: Path):
        """Rollback configuration to backup."""

        config_dir = settings.PROJECTS_DIR
        config_path = config_dir / f"{project_name}.yml"

        shutil.copy2(backup_path, config_path)
        logger.info(f"Rolled back configuration from {backup_path}")

    def _apply_action(self, config: Any, action: FixAction):
        """Apply a single fix action to configuration."""
        if action.type == FixActionType.REMOVE_COLUMN:
            self._remove_column(config, action)
        elif action.type == FixActionType.ADD_COLUMN:
            self._add_column(config, action)
        elif action.type == FixActionType.UPDATE_REFERENCE:
            self._update_reference(config, action)
        else:
            raise ValueError(f"Unsupported action type: {action.type}")

    def _remove_column(self, config: Any, action: FixAction):
        """Remove a column from entity configuration."""
        # Handle both dict and object config
        entities = config.get("entities") if isinstance(config, dict) else config.entities
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

    def _add_column(self, config: Any, action: FixAction):
        """Add a column to entity configuration."""
        # Handle both dict and object config
        entities = config.get("entities") if isinstance(config, dict) else config.entities
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
        """Update a @value reference in entity configuration."""
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
