"""Data-aware validators that check actual data for issues."""

import asyncio
from typing import Any

import pandas as pd
from loguru import logger

from app.models.validation import (
    ValidationCategory,
    ValidationError,
    ValidationPriority,
)
from app.services.preview_service import PreviewService


class ColumnExistsValidator:
    """Validate that configured columns actually exist in the data."""

    def __init__(self, preview_service: PreviewService):
        """Initialize validator with preview service for data sampling."""
        self.preview_service = preview_service

    async def validate(
        self, config_name: str, entity_name: str, entity_config: dict[str, Any]
    ) -> list[ValidationError]:
        """
        Check that all configured columns exist in actual data.

        Args:
            config_name: Configuration name
            entity_name: Entity name
            entity_config: Entity configuration dict

        Returns:
            List of validation errors for missing columns
        """
        errors = []

        # Only validate entities with column specifications
        columns = entity_config.get("columns")
        if not columns:
            return errors

        try:
            # Get sample data
            preview_result = await self.preview_service.preview_entity(
                config_name=config_name, entity_name=entity_name, limit=10
            )

            if not preview_result.rows:
                # Can't validate without data - not necessarily an error
                logger.debug(f"No data available to validate columns for {entity_name}")
                return errors

            # Get actual column names from data
            df = pd.DataFrame(preview_result.rows)
            actual_columns = set(df.columns)

            # Check each configured column
            configured_columns = set(columns)
            missing_columns = configured_columns - actual_columns

            for col in missing_columns:
                errors.append(
                    ValidationError(
                        severity="error",
                        entity=entity_name,
                        field="columns",
                        message=f"Column '{col}' is configured but does not exist in data",
                        code="COLUMN_NOT_FOUND",
                        suggestion=f"Remove '{col}' from columns list or fix the data source. "
                        f"Available columns: {', '.join(sorted(actual_columns))}",
                        category=ValidationCategory.DATA,
                        priority=ValidationPriority.HIGH,
                        auto_fixable=False,
                    )
                )

        except Exception as e:
            logger.warning(f"Could not validate columns for {entity_name}: {e}")
            errors.append(
                ValidationError(
                    severity="warning",
                    entity=entity_name,
                    field="columns",
                    message=f"Could not validate columns: {str(e)}",
                    code="VALIDATION_FAILED",
                    suggestion="Check data source configuration and connectivity",
                    category=ValidationCategory.DATA,
                    priority=ValidationPriority.LOW,
                    auto_fixable=False,
                )
            )

        return errors


class NaturalKeyUniquenessValidator:
    """Validate that natural keys are actually unique in the data."""

    def __init__(self, preview_service: PreviewService):
        """Initialize validator with preview service for data sampling."""
        self.preview_service = preview_service

    async def validate(
        self, config_name: str, entity_name: str, entity_config: dict[str, Any]
    ) -> list[ValidationError]:
        """
        Check that natural keys are unique in sample data.

        Args:
            config_name: Configuration name
            entity_name: Entity name
            entity_config: Entity configuration dict

        Returns:
            List of validation errors for non-unique keys
        """
        errors = []

        # Only validate entities with natural keys
        keys = entity_config.get("keys")
        if not keys:
            return errors

        try:
            # Get larger sample for better uniqueness check
            preview_result = await self.preview_service.preview_entity(
                config_name=config_name, entity_name=entity_name, limit=1000
            )

            if not preview_result.rows or len(preview_result.rows) < 2:
                # Need at least 2 rows to check uniqueness
                return errors

            df = pd.DataFrame(preview_result.rows)

            # Check if all key columns exist
            missing_keys = set(keys) - set(df.columns)
            if missing_keys:
                # Column existence is handled by ColumnExistsValidator
                return errors

            # Check for duplicates
            duplicates = df[df.duplicated(subset=keys, keep=False)]

            if not duplicates.empty:
                duplicate_count = len(duplicates)
                unique_duplicate_keys = len(duplicates.drop_duplicates(subset=keys))

                # Show example of duplicate
                example = duplicates[keys].iloc[0].to_dict()
                example_str = ", ".join([f"{k}={v}" for k, v in example.items()])

                errors.append(
                    ValidationError(
                        severity="error",
                        entity=entity_name,
                        field="keys",
                        message=f"Natural keys are not unique: {duplicate_count} duplicate rows found "
                        f"({unique_duplicate_keys} unique key combinations)",
                        code="NON_UNIQUE_KEYS",
                        suggestion=f"Natural keys must uniquely identify rows. "
                        f"Example duplicate: {example_str}. "
                        f"Consider using a different key combination or add surrogate_id.",
                        category=ValidationCategory.DATA,
                        priority=ValidationPriority.HIGH,
                        auto_fixable=False,
                    )
                )

        except Exception as e:
            logger.warning(f"Could not validate key uniqueness for {entity_name}: {e}")
            errors.append(
                ValidationError(
                    severity="warning",
                    entity=entity_name,
                    field="keys",
                    message=f"Could not validate key uniqueness: {str(e)}",
                    code="VALIDATION_FAILED",
                    suggestion="Check data source configuration and connectivity",
                    category=ValidationCategory.DATA,
                    priority=ValidationPriority.LOW,
                    auto_fixable=False,
                )
            )

        return errors


class NonEmptyResultValidator:
    """Validate that data source returns at least one row."""

    def __init__(self, preview_service: PreviewService):
        """Initialize validator with preview service for data sampling."""
        self.preview_service = preview_service

    async def validate(
        self, config_name: str, entity_name: str, entity_config: dict[str, Any]
    ) -> list[ValidationError]:
        """
        Check that entity returns at least one row of data.

        Args:
            config_name: Configuration name
            entity_name: Entity name
            entity_config: Entity configuration dict

        Returns:
            List of validation errors if no data found
        """
        errors = []

        entity_type = entity_config.get("type", "data")

        # Skip fixed entities - they don't have data sources
        if entity_type == "fixed":
            return errors

        try:
            # Try to get at least 1 row
            preview_result = await self.preview_service.preview_entity(
                config_name=config_name, entity_name=entity_name, limit=1
            )

            if not preview_result.rows or len(preview_result.rows) == 0:
                errors.append(
                    ValidationError(
                        severity="warning",
                        entity=entity_name,
                        field="query" if entity_type == "sql" else "source",
                        message=f"Entity returns no data (0 rows)",
                        code="EMPTY_RESULT",
                        suggestion="Check your SQL query or data source. "
                        "Entity should return at least one row. "
                        "If this is intentional, you can ignore this warning.",
                        category=ValidationCategory.DATA,
                        priority=ValidationPriority.MEDIUM,
                        auto_fixable=False,
                    )
                )

        except Exception as e:
            logger.warning(f"Could not validate data for {entity_name}: {e}")
            errors.append(
                ValidationError(
                    severity="warning",
                    entity=entity_name,
                    field="source",
                    message=f"Could not load data: {str(e)}",
                    code="DATA_LOAD_FAILED",
                    suggestion="Check data source configuration, connectivity, and query syntax",
                    category=ValidationCategory.DATA,
                    priority=ValidationPriority.HIGH,
                    auto_fixable=False,
                )
            )

        return errors


class DataValidationService:
    """Service to run all data validators."""

    def __init__(self, preview_service: PreviewService):
        """Initialize data validation service."""
        self.preview_service = preview_service
        self.validators = [
            ColumnExistsValidator(preview_service),
            NaturalKeyUniquenessValidator(preview_service),
            NonEmptyResultValidator(preview_service),
        ]

    async def validate_entity(
        self, config_name: str, entity_name: str, entity_config: dict[str, Any]
    ) -> list[ValidationError]:
        """
        Run all data validators on an entity.

        Args:
            config_name: Configuration name
            entity_name: Entity name
            entity_config: Entity configuration dict

        Returns:
            List of all validation errors found
        """
        all_errors = []

        # Run all validators concurrently
        results = await asyncio.gather(
            *[
                validator.validate(config_name, entity_name, entity_config)
                for validator in self.validators
            ],
            return_exceptions=True,
        )

        # Collect errors from all validators
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Validator failed for {entity_name}: {result}")
                all_errors.append(
                    ValidationError(
                        severity="error",
                        entity=entity_name,
                        message=f"Data validation failed: {str(result)}",
                        code="VALIDATOR_ERROR",
                        category=ValidationCategory.DATA,
                        priority=ValidationPriority.LOW,
                    )
                )
            else:
                all_errors.extend(result)

        return all_errors

    async def validate_configuration(
        self, config_name: str, entity_names: list[str] | None = None
    ) -> list[ValidationError]:
        """
        Run data validators on multiple entities.

        Args:
            config_name: Configuration name
            entity_names: Optional list of entity names to validate (None = all)

        Returns:
            List of all validation errors found
        """
        from app.services.config_service import ConfigurationService

        config_service = ConfigurationService()
        config = config_service.load_configuration(config_name)

        if not config:
            return [
                ValidationError(
                    severity="error",
                    message=f"Configuration '{config_name}' not found",
                    code="CONFIG_NOT_FOUND",
                    category=ValidationCategory.STRUCTURAL,
                    priority=ValidationPriority.CRITICAL,
                )
            ]

        # Determine which entities to validate
        entities_to_validate = entity_names or list(config.entities.keys())

        # Run validators on each entity concurrently
        results = await asyncio.gather(
            *[
                self.validate_entity(config_name, entity_name, config.entities[entity_name])
                for entity_name in entities_to_validate
                if entity_name in config.entities
            ],
            return_exceptions=True,
        )

        # Collect all errors
        all_errors = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Entity validation failed: {result}")
            else:
                all_errors.extend(result)

        return all_errors
