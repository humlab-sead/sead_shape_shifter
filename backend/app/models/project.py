"""Pydantic models for project."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Type

from pydantic import BaseModel, Field, field_serializer
from pydantic.json_schema import GenerateJsonSchema

from src.configuration.config import Config


class ExcelMetadataResponse(BaseModel):
    """Metadata for an Excel file (sheets + columns for a selected sheet)."""

    sheets: list[str] = Field(default_factory=list, description="Available worksheet names")
    columns: list[str] = Field(default_factory=list, description="Column names for the selected sheet (empty if none)")


class ProjectFileInfo(BaseModel):
    """Metadata about a file stored under a project uploads directory."""

    name: str = Field(..., description="Filename")
    path: str = Field(..., description="Path relative to server root")
    location: Literal["global", "local"] = Field(..., description="File location: 'global' (shared) or 'local' (project-specific)")
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
    entity_count: int = Field(
        ...,
        description="Number of entities (computed)",
        json_schema_extra={"exclude_from_schema": True},
    )
    created_at: float = Field(default=0, description="Creation timestamp (Unix timestamp)")
    modified_at: float = Field(default=0, description="Last modification timestamp (Unix timestamp)")
    is_valid: bool = Field(default=True, description="Whether project is valid")
    default_entity: str | None = Field(default=None, description="Default source entity name")
    target_model: str | dict[str, Any] | None = Field(default=None, description="Target model spec: inline dict or @include: path string")

    @field_serializer("created_at", "modified_at")
    def serialize_timestamp(self, value: float) -> str | None:
        """Convert Unix timestamp to ISO 8601 string for API responses."""
        if value <= 0:
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()

    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = "{model}",
        schema_generator: Type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: Literal["validation", "serialization"] = "validation",
        *,
        union_format: Literal["any_of", "primitive_type_array"] = "any_of",
    ) -> dict[str, Any]:
        """Customize JSON schema to exclude fields marked with exclude_from_schema."""
        schema = super().model_json_schema(
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=schema_generator,
            mode=mode,
            union_format=union_format,
        )

        # Remove fields marked with exclude_from_schema=True
        if "properties" in schema:
            fields_to_remove: list[str] = [
                field_name
                for field_name, field_info in cls.model_fields.items()
                if isinstance(field_info.json_schema_extra, dict) and field_info.json_schema_extra.get("exclude_from_schema")
            ]

            for field_name in fields_to_remove:
                schema["properties"].pop(field_name, None)
                if "required" in schema and field_name in schema["required"]:
                    schema["required"].remove(field_name)

        return schema


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

    @property
    def folder(self) -> Path:
        """Get project folder from metadata."""
        if self.metadata and self.metadata.file_path:  # pylint: disable=no-member
            return Path(self.metadata.file_path).parent  # pylint: disable=no-member
        return Path(".")

    def has_table(self, entity_name: str) -> bool:
        """Check if entity exists in project."""
        return entity_name in self.entities  # pylint: disable=no-member

    def is_resolved(self) -> bool:
        """Check if the project has any unresolved references."""
        return not self.unresolved_directives()

    def unresolved_directives(self) -> list[str]:
        """Check if the project has any unresolved references."""
        return Config.find_unresolved_directives(self.entities) + Config.find_unresolved_directives(self.options)

    @property
    def data_sources(self) -> dict[str, Any]:
        """Get data source configurations from options."""
        return self.options.get("data_sources", {}) or {}
