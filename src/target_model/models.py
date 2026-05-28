from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SeverityLevel = Literal["error", "warning", "info"]


class ForeignKeySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    required: bool = False
    via: str | None = None  # Bridge entity name for many-to-many relationships


class ColumnSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: bool = False
    generated: bool = False
    allowed_values: list[str | int | float | bool] = Field(default_factory=list)
    type: str | None = None
    nullable: bool | None = None
    description: str | None = None


class EntitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["fact", "lookup", "classifier", "bridge"] | None = None
    required: bool = False
    description: str | None = None
    domains: list[str] = Field(default_factory=list)
    target_table: str | None = None
    public_id: str | None = None
    identity_columns: list[str] = Field(default_factory=list)
    columns: dict[str, ColumnSpec] = Field(default_factory=dict)
    unique_sets: list[list[str]] = Field(default_factory=list)
    foreign_keys: list[ForeignKeySpec] = Field(default_factory=list)

    # SIMS identity properties (defaults derived from role when None)
    identity_tracking: Literal["tracked", "reconciled", "derived", "child"] | None = None
    reconciliation: Literal["allocate", "reconcile-exact", "reconcile-fuzzy", "lookup-only", "lookup-extensible", "derive"] | None = None
    aggregate_parent: str | None = None


class NamingConventions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_id_suffix: str | None = None


class GlobalConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    required: bool | Literal["strict"] | None = None


class ModelMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    format_version: str = "1"
    version: str
    description: str | None = None


class TargetModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: ModelMetadata
    entities: dict[str, EntitySpec] = Field(default_factory=dict)
    naming: NamingConventions | None = None
    constraints: list[GlobalConstraint] = Field(default_factory=list)
