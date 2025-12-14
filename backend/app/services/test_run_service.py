"""Service for running configuration tests with sample data."""

import time
import uuid
from datetime import datetime
from typing import Dict, Optional

from loguru import logger

from backend.app.models.test_run import (
    EntityTestResult,
    OutputFormat,
    TestProgress,
    TestRunOptions,
    TestRunResult,
    TestRunStatus,
    ValidationIssue,
)
from backend.app.services.config_service import ConfigurationService


class TestRunService:
    """Service for running configuration tests."""

    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self._active_runs: Dict[str, TestRunResult] = {}
        self._cancel_flags: Dict[str, bool] = {}

    def init_test_run(self, config_name: str, options: TestRunOptions) -> TestRunResult:
        """
        Initialize a test run (returns immediately with PENDING status).

        Args:
            config_name: Name of the configuration to test
            options: Test run options

        Returns:
            TestRunResult with PENDING status
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        # Initialize result with PENDING status
        result = TestRunResult(
            run_id=run_id,
            config_name=config_name,
            status=TestRunStatus.PENDING,
            started_at=started_at,
            total_time_ms=0,
            options=options,
        )

        # Store active run
        self._active_runs[run_id] = result
        self._cancel_flags[run_id] = False

        return result

    async def execute_test_run(self, run_id: str) -> None:
        """
        Execute a test run in the background.

        Args:
            run_id: ID of the test run to execute
        """
        logger.info(f"[BACKGROUND] Starting execution for test run {run_id}")
        result = self._active_runs.get(run_id)
        if not result:
            logger.error(f"[BACKGROUND] Test run {run_id} not found in active runs")
            return

        started_at = result.started_at  # Preserve original start time

        try:
            logger.info(f"[BACKGROUND] Updating status to RUNNING for {run_id}")
            # Update status to running
            result.status = TestRunStatus.RUNNING
            self._active_runs[run_id] = result
            logger.info("[BACKGROUND] Status updated, stored back to active_runs")

            # Load configuration
            config = self.config_service.load_configuration(result.config_name)
            if not config:
                raise ValueError(f"Configuration '{result.config_name}' not found")

            # Get entities from configuration
            entities_data = config.entities

            # Determine entities to process
            if result.options.entities:
                # Validate entity names
                invalid_entities = [e for e in result.options.entities if e not in entities_data]
                if invalid_entities:
                    raise ValueError(f"Invalid entities: {', '.join(invalid_entities)}")
                entity_names = result.options.entities
            else:
                # Process all entities
                entity_names = list(entities_data.keys())

            # Process entities
            result.entities_total = len(entity_names)

            for idx, entity_name in enumerate(entity_names):
                # Check for cancellation
                if self._cancel_flags.get(run_id, False):
                    result.status = TestRunStatus.CANCELLED
                    logger.info(f"Test run {run_id} cancelled")
                    break

                # Update progress
                result.current_entity = entity_name
                result.entities_completed = idx

                logger.info(f"Processing entity {idx + 1}/{len(entity_names)}: {entity_name}")

                entity_start = time.time()
                entity_result = await self._process_entity(entity_name, entities_data[entity_name], result.options)
                entity_result.execution_time_ms = int((time.time() - entity_start) * 1000)

                result.entities_processed.append(entity_result)

                # Update counters
                if entity_result.status == "success":
                    result.entities_succeeded += 1
                elif entity_result.status == "failed":
                    result.entities_failed += 1
                    if result.options.stop_on_error:
                        logger.warning(f"Stopping test run due to error in {entity_name}")
                        break
                else:
                    result.entities_skipped += 1

                # Collect validation issues
                result.validation_issues.extend(entity_result.validation_issues)

            # Mark as completed if not cancelled
            if result.status == TestRunStatus.RUNNING:
                result.status = TestRunStatus.COMPLETED

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Test run failed: {e}", exc_info=True)
            result.status = TestRunStatus.FAILED
            result.error_message = str(e)

        finally:
            # Calculate total time
            completed_at = datetime.utcnow()
            result.completed_at = completed_at
            result.total_time_ms = int((completed_at - started_at).total_seconds() * 1000)

            # Store final result
            self._active_runs[run_id] = result
            logger.info(
                f"[BACKGROUND] Test run {run_id} completed with status: {result.status}, "
                f"stored in active_runs (total runs: {len(self._active_runs)})"
            )

            # Update stored result
            self._active_runs[run_id] = result

            # Clean up cancel flag
            self._cancel_flags.pop(run_id, None)

        logger.info(f"Test run {run_id} completed with status: {result.status}")

    async def _process_entity(
        self,
        entity_name: str,
        entity_config: dict,
        options: TestRunOptions,
    ) -> EntityTestResult:
        """
        Process a single entity.

        Args:
            entity_name: Name of entity to process
            entity_config: Entity configuration dict
            options: Test run options

        Returns:
            EntityTestResult with processing details
        """
        result = EntityTestResult(
            entity_name=entity_name,
            status="success",
            rows_in=0,
            rows_out=0,
            execution_time_ms=0,
        )

        try:
            # Get entity type
            entity_type = entity_config.get("type", "data")

            # For now, just analyze configuration
            # Full implementation would actually run the transformation pipeline

            if entity_type == "fixed":
                # Fixed entity - use fixed values
                values = entity_config.get("values", [])
                if values:
                    result.rows_in = len(values)
                    result.rows_out = len(values)

                    if options.output_format == OutputFormat.PREVIEW:
                        # Convert values to dict format
                        columns = entity_config.get("columns", [])
                        if columns:
                            preview = []
                            for row_vals in values[:10]:
                                if isinstance(row_vals, list):
                                    row_dict = {col: val for col, val in zip(columns, row_vals)}
                                    preview.append(row_dict)
                            result.preview_rows = preview
                else:
                    result.warnings.append("Fixed entity has no values defined")
            else:
                # Data or SQL entity - would need actual data source
                result.status = "skipped"
                result.warnings.append("Entity skipped - full processing pipeline not yet implemented in test run")

            # Basic validation
            if options.validate_foreign_keys:
                foreign_keys = entity_config.get("foreign_keys", [])
                for fk in foreign_keys:
                    # Just check that FK is properly configured
                    if not fk.get("entity"):
                        issue = ValidationIssue(
                            entity_name=entity_name,
                            severity="error",
                            message="Foreign key missing remote entity name",
                            suggestion="Add 'entity' field to foreign key configuration",
                        )
                        result.validation_issues.append(issue)

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Error processing entity {entity_name}: {e}", exc_info=True)
            result.status = "failed"
            result.error_message = str(e)

        return result

    def get_test_progress(self, run_id: str) -> Optional[TestProgress]:
        """
        Get progress information for a running test.

        Args:
            run_id: Test run ID

        Returns:
            TestProgress with current status, or None if not found
        """
        result = self._active_runs.get(run_id)
        if not result:
            return None

        entities_completed = len(result.entities_processed)
        entities_total = len(result.entities_processed) + (
            len(result.options.entities or []) - entities_completed if result.options.entities else 0
        )

        progress_percentage = (entities_completed / entities_total * 100) if entities_total > 0 else 0

        elapsed_time_ms = (
            int((datetime.utcnow() - result.started_at).total_seconds() * 1000)
            if result.status == TestRunStatus.RUNNING
            else result.total_time_ms
        )

        # Estimate remaining time
        estimated_time_remaining_ms = None
        if result.status == TestRunStatus.RUNNING and entities_completed > 0 and progress_percentage > 0:
            avg_time_per_entity = elapsed_time_ms / entities_completed
            remaining_entities = entities_total - entities_completed
            estimated_time_remaining_ms = int(avg_time_per_entity * remaining_entities)

        return TestProgress(
            run_id=run_id,
            status=result.status,
            current_entity=result.current_entity if hasattr(result, "current_entity") else None,
            entities_completed=entities_completed,
            entities_total=entities_total,
            progress_percentage=progress_percentage,
            elapsed_time_ms=elapsed_time_ms,
            estimated_time_remaining_ms=estimated_time_remaining_ms,
        )

    def cancel_test(self, run_id: str) -> bool:
        """
        Cancel a running test.

        Args:
            run_id: Test run ID

        Returns:
            True if test was cancelled, False if not found or already completed
        """
        result = self._active_runs.get(run_id)
        if not result:
            return False

        if result.status not in [TestRunStatus.RUNNING, TestRunStatus.PENDING]:
            return False

        logger.info(f"Cancelling test run {run_id}")
        self._cancel_flags[run_id] = True
        return True

    def get_test_result(self, run_id: str) -> Optional[TestRunResult]:
        """
        Get test run result.

        Args:
            run_id: Test run ID

        Returns:
            TestRunResult if found, None otherwise
        """
        logger.info(
            f"[RETRIEVE] Getting test run {run_id}, "
            f"active_runs contains {len(self._active_runs)} runs: {list(self._active_runs.keys())}"
        )
        result = self._active_runs.get(run_id)
        if result:
            logger.info(f"[RETRIEVE] Found run {run_id}, status: {result.status}")
        else:
            logger.warning(f"[RETRIEVE] Run {run_id} not found in active_runs")
        return result

    def list_test_runs(self) -> list[TestRunResult]:
        """
        List all test runs.

        Returns:
            List of test run results
        """
        return list(self._active_runs.values())

    def delete_test_result(self, run_id: str) -> bool:
        """
        Delete a test run result.

        Args:
            run_id: Test run ID

        Returns:
            True if deleted, False if not found
        """
        if run_id in self._active_runs:
            del self._active_runs[run_id]
            return True
        return False
