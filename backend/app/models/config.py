"""Pydantic models for configuration."""

from typing import Any

from pydantic import BaseModel, Field


class ConfigMetadata(BaseModel):
    """Metadata about a configuration."""

    name: str = Field(..., description="Configuration name")
    description: str | None = Field(default=None, description="Configuration description")
    version: str | None = Field(default=None, description="Configuration version")
    file_path: str | None = Field(default=None, description="File path if loaded from file")
    entity_count: int = Field(..., description="Number of entities")
    created_at: float = Field(default=0, description="Creation timestamp (Unix timestamp)")
    modified_at: float = Field(default=0, description="Last modification timestamp (Unix timestamp)")
    is_valid: bool = Field(default=True, description="Whether configuration is valid")
    default_entity: str | None = Field(default=None, description="Default source entity name")


class Configuration(BaseModel):
    """Complete configuration containing all entities."""

    entities: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Map of entity name to entity config (raw dicts)")
    options: dict[str, Any] = Field(default_factory=dict, description="Global options")
    metadata: ConfigMetadata | None = Field(default=None, description="Configuration metadata")

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
        """Get configuration filename from metadata."""
        return self.metadata.file_path if self.metadata else None  # pylint: disable=no-member
