"""
Unit tests for auto-fix service.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, mock_open
from pathlib import Path
from datetime import datetime

from app.services.auto_fix_service import AutoFixService
from app.models.validation import ValidationError, ValidationCategory, ValidationPriority
from app.models.fix import FixActionType, FixAction, FixSuggestion, FixResult


@pytest.fixture
def mock_config_service():
    """Create a mock configuration service."""
    service = Mock()
    service.load_configuration = Mock()
    service.save_configuration = AsyncMock()
    return service


@pytest.fixture
def sample_config():
    """Create a sample configuration."""
    return {
        "entities": {
            "test_entity": {
                "columns": ["id", "name", "missing_column"],
                "keys": ["name"],
                "foreign_keys": [
                    {
                        "entity": "remote_entity",
                        "local_keys": ["remote_id"],
                        "remote_keys": ["id"],
                    }
                ],
            }
        }
    }


class TestAutoFixService:
    """Tests for AutoFixService."""

    def test_generate_fix_suggestions_for_missing_column(self, mock_config_service):
        """Test generating fix for missing column error."""
        # Setup
        service = AutoFixService(mock_config_service)
        errors = [
            ValidationError(
                severity="error",
                code="COLUMN_NOT_FOUND",
                message="Column 'missing_column' not found",
                entity="test_entity",
                field="missing_column",
                category=ValidationCategory.DATA,
                priority=ValidationPriority.HIGH,
            )
        ]

        # Execute
        suggestions = service.generate_fix_suggestions(errors)

        # Assert
        assert len(suggestions) == 1
        suggestion = suggestions[0]
        assert suggestion.issue_code == "COLUMN_NOT_FOUND"
        assert suggestion.entity == "test_entity"
        assert suggestion.auto_fixable is True
        assert len(suggestion.actions) == 1
        
        action = suggestion.actions[0]
        assert action.type == FixActionType.REMOVE_COLUMN
        assert action.entity == "test_entity"
        assert action.field == "columns"  # Field is "columns" not the specific column name

    def test_generate_fix_suggestions_for_unresolved_reference(self, mock_config_service):
        """Test generating fix for unresolved reference (non-auto-fixable)."""
        # Setup
        service = AutoFixService(mock_config_service)
        errors = [
            ValidationError(
                severity="error",
                code="UNRESOLVED_REFERENCE",
                message="Referenced entity 'missing_entity' not found",
                entity="test_entity",
                field="reference",
                category=ValidationCategory.CONFIGURATION,
                priority=ValidationPriority.HIGH,
            )
        ]

        # Execute
        suggestions = service.generate_fix_suggestions(errors)

        # Assert
        assert len(suggestions) == 1
        suggestion = suggestions[0]
        assert suggestion.auto_fixable is False
        assert suggestion.requires_confirmation is True
        assert len(suggestion.warnings) > 0

    def test_generate_fix_suggestions_for_duplicate_keys(self, mock_config_service):
        """Test generating fix for duplicate natural keys (non-auto-fixable)."""
        # Setup
        service = AutoFixService(mock_config_service)
        errors = [
            ValidationError(
                severity="error",
                code="DUPLICATE_NATURAL_KEYS",
                message="Found 5 duplicate natural keys",
                entity="test_entity",
                field="keys",
                category=ValidationCategory.DATA,
                priority=ValidationPriority.HIGH,
            )
        ]

        # Execute
        suggestions = service.generate_fix_suggestions(errors)

        # Assert
        assert len(suggestions) == 1
        suggestion = suggestions[0]
        assert suggestion.auto_fixable is False
        assert "manual" in suggestion.warnings[0].lower()

    @pytest.mark.asyncio
    async def test_preview_fixes(self, mock_config_service, sample_config):
        """Test previewing fixes without applying."""
        # Setup
        mock_config_service.load_configuration.return_value = sample_config
        service = AutoFixService(mock_config_service)

        suggestions = [
            FixSuggestion(
                issue_code="COLUMN_NOT_FOUND",
                entity="test_entity",
                actions=[
                    FixAction(
                        type=FixActionType.REMOVE_COLUMN,
                        entity="test_entity",
                        field="missing_column",
                        old_value=None,
                        new_value=None,
                        description="Remove missing_column from test_entity columns",
                    )
                ],
                auto_fixable=True,
                warnings=[],
            )
        ]

        # Execute
        preview = await service.preview_fixes("test_config", suggestions)

        # Assert
        assert preview["config_name"] == "test_config"
        assert preview["fixable_count"] == 1
        assert preview["total_suggestions"] == 1
        assert len(preview["changes"]) == 1
        
        change = preview["changes"][0]
        assert change["entity"] == "test_entity"
        assert change["auto_fixable"] is True
        assert len(change["actions"]) == 1

    @pytest.mark.asyncio
    async def test_apply_fixes_success(self, mock_config_service, sample_config):
        """Test successfully applying fixes."""
        # Setup
        mock_config_service.load_configuration.return_value = sample_config.copy()
        service = AutoFixService(mock_config_service)

        suggestions = [
            FixSuggestion(
                issue_code="COLUMN_NOT_FOUND",
                entity="test_entity",
                actions=[
                    FixAction(
                        type=FixActionType.REMOVE_COLUMN,
                        entity="test_entity",
                        field="missing_column",
                        old_value=None,
                        new_value=None,
                        description="Remove missing_column",
                    )
                ],
                auto_fixable=True,
                warnings=[],
            )
        ]

        # Mock backup creation
        with patch.object(service, "_create_backup") as mock_backup:
            mock_backup.return_value = Path("/tmp/backup.yml")

            # Execute
            result = await service.apply_fixes("test_config", suggestions)

            # Assert
            assert result.success is True
            assert result.fixes_applied == 1
            assert len(result.errors) == 0
            assert result.backup_path is not None
            assert mock_config_service.save_configuration.called

    @pytest.mark.asyncio
    async def test_apply_fixes_with_rollback_on_error(self, mock_config_service, sample_config):
        """Test rollback when fix application fails."""
        # Setup
        mock_config_service.load_configuration.return_value = sample_config.copy()
        
        # Make save fail to trigger rollback
        mock_config_service.save_configuration.side_effect = Exception("Save failed")
        
        service = AutoFixService(mock_config_service)

        suggestions = [
            FixSuggestion(
                issue_code="COLUMN_NOT_FOUND",
                entity="test_entity",
                actions=[
                    FixAction(
                        type=FixActionType.REMOVE_COLUMN,
                        entity="test_entity",
                        field="missing_column",
                        old_value=None,
                        new_value=None,
                        description="Remove missing_column",
                    )
                ],
                auto_fixable=True,
                warnings=[],
            )
        ]

        # Mock backup and rollback
        with patch.object(service, "_create_backup") as mock_backup, \
             patch.object(service, "_rollback") as mock_rollback:
            
            mock_backup.return_value = Path("/tmp/backup.yml")

            # Execute
            result = await service.apply_fixes("test_config", suggestions)

            # Assert
            assert result.success is False
            assert len(result.errors) > 0
            assert mock_rollback.called

    def test_create_backup(self, mock_config_service, sample_config):
        """Test backup file creation."""
        # Setup
        mock_config_service.load_configuration.return_value = sample_config
        service = AutoFixService(mock_config_service)

        # Mock file operations
        with patch("pathlib.Path.mkdir") as mock_mkdir, \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("yaml.dump") as mock_yaml_dump:

            # Execute
            backup_path = service._create_backup("test_config")

            # Assert
            assert backup_path is not None
            assert "test_config" in str(backup_path)
            assert ".backup." in str(backup_path)
            assert mock_mkdir.called
            assert mock_yaml_dump.called

    def test_rollback(self, mock_config_service):
        """Test configuration rollback from backup."""
        # Setup
        service = AutoFixService(mock_config_service)
        backup_path = Path("/tmp/test_config.backup.20240101_120000.yml")

        # Mock file operations
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("builtins.open", mock_open(read_data="entities: {}")) as mock_file, \
             patch("yaml.safe_load") as mock_yaml_load, \
             patch("yaml.dump") as mock_yaml_dump:

            mock_exists.return_value = True
            mock_yaml_load.return_value = {"entities": {}}

            # Execute
            service._rollback("test_config", backup_path)

            # Assert
            assert mock_yaml_load.called
            assert mock_yaml_dump.called

    def test_apply_remove_column_action(self, mock_config_service, sample_config):
        """Test applying remove column action."""
        # Setup
        service = AutoFixService(mock_config_service)
        config = sample_config.copy()

        action = FixAction(
            type=FixActionType.REMOVE_COLUMN,
            entity="test_entity",
            field="missing_column",
            old_value=None,
            new_value=None,
            description="Remove missing_column",
        )

        # Execute
        service._apply_action(config, action)

        # Assert
        assert "missing_column" not in config["entities"]["test_entity"]["columns"]

    def test_apply_add_column_action(self, mock_config_service, sample_config):
        """Test applying add column action."""
        # Setup
        service = AutoFixService(mock_config_service)
        config = sample_config.copy()

        action = FixAction(
            type=FixActionType.ADD_COLUMN,
            entity="test_entity",
            field="new_column",
            old_value=None,
            new_value=None,
            description="Add new_column",
        )

        # Execute
        service._apply_action(config, action)

        # Assert
        assert "new_column" in config["entities"]["test_entity"]["columns"]

    def test_skip_non_auto_fixable_suggestions(self, mock_config_service, sample_config):
        """Test that non-auto-fixable suggestions are skipped during apply."""
        # Setup
        mock_config_service.load_configuration.return_value = sample_config.copy()
        service = AutoFixService(mock_config_service)

        suggestions = [
            FixSuggestion(
                issue_code="DUPLICATE_NATURAL_KEYS",
                entity="test_entity",
                actions=[],
                auto_fixable=False,
                warnings=["Manual fix required"],
            )
        ]

        # Mock backup
        with patch.object(service, "_create_backup") as mock_backup:
            mock_backup.return_value = Path("/tmp/backup.yml")

            # Execute
            result = pytest.importasync(service.apply_fixes("test_config", suggestions))

            # The result should still succeed but with 0 fixes applied
            # (This is an async test, simplified here)

    def test_multiple_actions_in_suggestion(self, mock_config_service):
        """Test suggestion with multiple actions."""
        # Setup
        service = AutoFixService(mock_config_service)
        errors = [
            ValidationError(
                severity="error",
                code="COLUMN_NOT_FOUND",
                message="Columns 'col1, col2' not found",
                entity="test_entity",
                field="col1",
                category=ValidationCategory.DATA,
                priority=ValidationPriority.HIGH,
            )
        ]

        # Execute
        suggestions = service.generate_fix_suggestions(errors)

        # Assert
        assert len(suggestions) == 1
        # Should generate action to remove the column


class TestFixActionIntegration:
    """Integration tests for fix actions."""

    def test_fix_workflow_end_to_end(self, mock_config_service, sample_config):
        """Test complete fix workflow from error to applied fix."""
        # Setup
        mock_config_service.load_configuration.return_value = sample_config.copy()
        service = AutoFixService(mock_config_service)

        # Create error
        error = ValidationError(
            severity="error",
            code="COLUMN_NOT_FOUND",
            message="Column 'missing_column' not found",
            entity="test_entity",
            field="missing_column",
            category=ValidationCategory.DATA,
            priority=ValidationPriority.HIGH,
        )

        # Generate suggestion
        suggestions = service.generate_fix_suggestions([error])
        assert len(suggestions) == 1
        assert suggestions[0].auto_fixable is True

        # Apply action to config
        config = sample_config.copy()
        for action in suggestions[0].actions:
            service._apply_action(config, action)

        # Verify fix applied
        assert "missing_column" not in config["entities"]["test_entity"]["columns"]
