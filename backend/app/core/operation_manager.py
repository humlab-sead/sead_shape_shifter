"""Manager for long-running operations with progress tracking and cancellation."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger


class OperationStatus(str, Enum):
    """Status of a long-running operation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OperationProgress:
    """Progress information for an operation."""

    operation_id: str
    operation_type: str
    status: OperationStatus
    current: int = 0
    total: int = 0
    message: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds."""
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    @property
    def estimated_remaining_seconds(self) -> float | None:
        """Estimate remaining time in seconds based on current progress."""
        if self.current == 0 or self.total == 0:
            return None

        elapsed = self.elapsed_seconds
        rate = self.current / elapsed  # items per second
        remaining_items = self.total - self.current

        if rate > 0:
            return remaining_items / rate
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "status": self.status.value,
            "current": self.current,
            "total": self.total,
            "progress_percent": round(self.progress_percent, 2),
            "message": self.message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "estimated_remaining_seconds": (
                round(self.estimated_remaining_seconds, 2) if self.estimated_remaining_seconds is not None else None
            ),
            "error": self.error,
            "metadata": self.metadata,
        }


class OperationManager:
    """
    Singleton manager for tracking long-running operations.

    Provides progress tracking, cancellation support, and event streaming.
    """

    _instance: "OperationManager | None" = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize operation manager."""
        if getattr(self, "_initialized", False):
            return

        self._operations: dict[str, OperationProgress] = {}
        self._cancellation_flags: dict[str, asyncio.Event] = {}
        self._initialized = True
        logger.debug("OperationManager initialized")

    def create_operation(
        self,
        operation_type: str,
        total: int = 0,
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new operation and return its ID.

        Args:
            operation_type: Type of operation (e.g., "auto_reconcile")
            total: Total number of items to process
            message: Initial status message
            metadata: Additional metadata

        Returns:
            Unique operation ID
        """
        operation_id = str(uuid.uuid4())

        progress = OperationProgress(
            operation_id=operation_id,
            operation_type=operation_type,
            status=OperationStatus.PENDING,
            total=total,
            message=message,
            metadata=metadata or {},
        )

        self._operations[operation_id] = progress
        self._cancellation_flags[operation_id] = asyncio.Event()

        logger.info(f"Created operation {operation_id} ({operation_type}): {message}")
        return operation_id

    def update_progress(
        self,
        operation_id: str,
        current: int | None = None,
        total: int | None = None,
        message: str | None = None,
        status: OperationStatus | None = None,
    ) -> None:
        """
        Update operation progress.

        Args:
            operation_id: Operation ID
            current: Current progress value
            total: Total items (if changed)
            message: Status message
            status: Operation status
        """
        if operation_id not in self._operations:
            logger.warning(f"Attempted to update unknown operation {operation_id}")
            return

        progress = self._operations[operation_id]

        if current is not None:
            progress.current = current
        if total is not None:
            progress.total = total
        if message is not None:
            progress.message = message
        if status is not None:
            progress.status = status

            # Set completion timestamp for terminal states
            if status in (OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED):
                progress.completed_at = datetime.now()

        logger.debug(
            f"Operation {operation_id}: {progress.current}/{progress.total} " f"({progress.progress_percent:.1f}%) - {progress.message}"
        )

    def complete_operation(self, operation_id: str, message: str = "Completed successfully") -> None:
        """Mark operation as completed."""
        self.update_progress(operation_id, status=OperationStatus.COMPLETED, message=message)
        logger.info(f"Operation {operation_id} completed: {message}")

    def fail_operation(self, operation_id: str, error: str) -> None:
        """Mark operation as failed."""
        if operation_id in self._operations:
            self._operations[operation_id].error = error
        self.update_progress(operation_id, status=OperationStatus.FAILED, message=f"Failed: {error}")
        logger.error(f"Operation {operation_id} failed: {error}")

    def cancel_operation(self, operation_id: str) -> bool:
        """
        Request cancellation of an operation.

        Args:
            operation_id: Operation ID

        Returns:
            True if cancellation was requested, False if operation not found
        """
        if operation_id not in self._cancellation_flags:
            logger.warning(f"Attempted to cancel unknown operation {operation_id}")
            return False

        self._cancellation_flags[operation_id].set()
        self.update_progress(operation_id, status=OperationStatus.CANCELLED, message="Cancellation requested")
        logger.info(f"Cancellation requested for operation {operation_id}")
        return True

    def is_cancelled(self, operation_id: str) -> bool:
        """Check if operation has been cancelled."""
        if operation_id not in self._cancellation_flags:
            return False
        return self._cancellation_flags[operation_id].is_set()

    def get_progress(self, operation_id: str) -> OperationProgress | None:
        """Get current progress for an operation."""
        return self._operations.get(operation_id)

    def cleanup_operation(self, operation_id: str) -> None:
        """Remove operation from tracking (typically after completion)."""
        if operation_id in self._operations:
            del self._operations[operation_id]
        if operation_id in self._cancellation_flags:
            del self._cancellation_flags[operation_id]
        logger.debug(f"Cleaned up operation {operation_id}")

    def list_operations(self, operation_type: str | None = None) -> list[OperationProgress]:
        """
        List all tracked operations, optionally filtered by type.

        Args:
            operation_type: Filter by operation type (optional)

        Returns:
            List of operation progress objects
        """
        operations = list(self._operations.values())
        if operation_type:
            operations = [op for op in operations if op.operation_type == operation_type]
        return operations


# Singleton instance
operation_manager = OperationManager()
