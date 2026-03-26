from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ForeignKeySpec(BaseModel):
    entity: str
    required: bool = False


class EntitySpec(BaseModel):
    role: Literal["fact", "lookup", "classifier", "bridge"] | None = None
    required: bool = False
    description: str | None = None
    target_table: str | None = None
    public_id: str | None = None
    required_columns: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKeySpec] = Field(default_factory=list)


class NamingConventions(BaseModel):
    public_id_suffix: str | None = None


class GlobalConstraint(BaseModel):
    type: str


class ModelMetadata(BaseModel):
    name: str
    version: str
    description: str | None = None


class TargetModel(BaseModel):
    model: ModelMetadata
    entities: dict[str, EntitySpec] = Field(default_factory=dict)
    naming: NamingConventions | None = None
    constraints: list[GlobalConstraint] = Field(default_factory=list)