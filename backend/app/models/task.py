"""Pydantic models for task-related API operations."""

from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration."""

    DONE = "done"
    TODO = "todo"
    ONGOING = "ongoing"
    IGNORED = "ignored"


class TaskPriority(str, Enum):
    """Task priority enumeration (derived from project state)."""

    CRITICAL = "critical"  # Required entity missing or has errors
    READY = "ready"  # All dependencies done, validation passes
    WAITING = "waiting"  # Has incomplete dependencies
    OPTIONAL = "optional"  # Not required, no blockers


class EntityTaskStatus(BaseModel):
    """Status information for a single entity task."""

    status: TaskStatus = Field(..., description="Current status (done, todo, ongoing, ignored)")
    priority: TaskPriority = Field(..., description="Derived priority level")
    required: bool = Field(..., description="Whether entity is required for project completion")
    exists: bool = Field(..., description="Whether entity exists in project")
    validation_passed: bool = Field(..., description="Whether entity passes validation")
    preview_available: bool = Field(..., description="Whether preview data can be generated")
    flagged: bool = Field(default=False, description="Whether entity is flagged for attention")
    has_note: bool = Field(default=False, description="Whether entity has a persisted task note")
    blocked_by: list[str] = Field(default_factory=list, description="Entity names blocking this entity")
    issues: list[str] = Field(default_factory=list, description="Validation error messages")


class ProjectTaskStatus(BaseModel):
    """Task status for all entities in a project."""

    entities: dict[str, EntityTaskStatus] = Field(..., description="Map of entity names to their task status")
    completion_stats: dict[str, int | float] = Field(
        ..., description="Completion statistics (total, done, required_done, completion_percentage, etc.)"
    )


class TaskUpdateRequest(BaseModel):
    """Request to update task status."""

    entity_name: str = Field(..., description="Name of entity to update")
    status: TaskStatus = Field(..., description="New status to set")


class TaskUpdateResponse(BaseModel):
    """Response after updating task status."""

    success: bool = Field(..., description="Whether update succeeded")
    entity_name: str = Field(..., description="Name of updated entity")
    new_status: TaskStatus = Field(..., description="New status after update")
    message: str | None = Field(None, description="Optional message or error")


class TaskNoteRequest(BaseModel):
    """Request body for setting an entity note."""

    note: str = Field(..., description="Multiline note text")


class TaskNoteResponse(BaseModel):
    """Response model for entity task notes."""

    success: bool = Field(..., description="Whether the note operation succeeded")
    entity_name: str = Field(..., description="Name of the entity")
    note: str | None = Field(None, description="Current note text, if any")
    has_note: bool = Field(..., description="Whether the entity currently has a note")
    message: str | None = Field(None, description="Optional message")
