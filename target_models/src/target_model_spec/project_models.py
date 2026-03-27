from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProjectForeignKeySpec(BaseModel):
    entity: str


class ProjectUnnestSpec(BaseModel):
    id_vars: list[str] | str = Field(default_factory=list)
    value_vars: list[str] | str = Field(default_factory=list)
    var_name: str | None = None
    value_name: str | None = None


class ProjectEntitySpec(BaseModel):
    type: str | None = None
    public_id: str | None = None
    keys: list[str] | str = Field(default_factory=list)
    columns: list[str] | str = Field(default_factory=list)
    foreign_keys: list[ProjectForeignKeySpec] = Field(default_factory=list)
    extra_columns: dict[str, Any] = Field(default_factory=dict)
    unnest: ProjectUnnestSpec | None = None


class ProjectMetadata(BaseModel):
    name: str
    type: str
    version: str | None = None
    description: str | None = None


class ConformanceProjectModel(BaseModel):
    metadata: ProjectMetadata
    entities: dict[str, ProjectEntitySpec] = Field(default_factory=dict)