"""Pydantic models for project."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class ProjectFileInfo(BaseModel):
    """Metadata about a file stored under a project uploads directory."""

    name: str = Field(..., description="Filename")
    path: str = Field(..., description="Path relative to server root")
    size_bytes: int = Field(..., description="File size in bytes")
    modified_at: float = Field(..., description="Last modified timestamp (Unix timestamp)")

    @field_serializer("modified_at")
    def serialize_timestamp(self, value: float) -> str | None:
        """Convert Unix timestamp to ISO 8601 string for API responses."""
        if value <= 0:
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


class ProjectMetadata(BaseModel):
    """Metadata about a project."""

    name: str = Field(..., description="Project name")
    type: str | None = Field(default="shapeshifter-project", description="Project type identifier")
    description: str | None = Field(default=None, description="Project description")
    version: str | None = Field(default=None, description="Project version")
    file_path: str | None = Field(default=None, description="File path if loaded from file")
    entity_count: int = Field(..., description="Number of entities")
    created_at: float = Field(default=0, description="Creation timestamp (Unix timestamp)")
    modified_at: float = Field(default=0, description="Last modification timestamp (Unix timestamp)")
    is_valid: bool = Field(default=True, description="Whether project is valid")
    default_entity: str | None = Field(default=None, description="Default source entity name")

    @field_serializer("created_at", "modified_at")
    def serialize_timestamp(self, value: float) -> str | None:
        """Convert Unix timestamp to ISO 8601 string for API responses."""
        if value <= 0:
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


class Project(BaseModel):
    """Complete project containing all entities."""

    entities: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Map of entity name to entity (raw dicts)")
    options: dict[str, Any] = Field(default_factory=dict, description="Global options")
    task_list: dict[str, Any] | None = Field(default=None, description="Task list for entity progress tracking")
    metadata: ProjectMetadata | None = Field(default=None, description="Project metadata")

    @property
    def ingesters(self) -> dict[str, Any]:
        """Get ingester configurations from options."""
        return self.options.get("ingesters", {}) or {}

    def get_entity(self, name: str) -> dict[str, Any] | None:
        """Get entity by name."""
        return self.entities.get(name)  # pylint: disable=no-member

    def add_entity(self, name: str, entity_data: dict[str, Any]) -> None:
        """Add or update an entity."""
        self.entities[name] = entity_data

    def remove_entity(self, name: str) -> bool:
        """Remove an entity by name. Returns True if entity was removed."""
        if name in self.entities:
            del self.entities[name]
            return True
        return False

    @property
    def entity_names(self) -> list[str]:
        """Get list of entity names."""
        return list(self.entities.keys())  # pylint: disable=no-member

    @property
    def filename(self) -> str | None:
        """Get project filename from metadata."""
        return self.metadata.file_path if self.metadata else None  # pylint: disable=no-member

    def has_table(self, entity_name: str) -> bool:
        """Check if entity exists in project."""
        return entity_name in self.entities  # pylint: disable=no-member

    def is_resolved(self) -> bool:
        """Check if the project has any unresolved references."""
        return not self.unresolved_directives()

    def unresolved_directives(self) -> list[str]:
        """Check if the project has any unresolved references."""
        return Config.find_unresolved_directives(self.entities) + Config.find_unresolved_directives(self.options)
