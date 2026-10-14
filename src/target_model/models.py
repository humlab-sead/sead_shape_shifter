from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SerializerFunctionWrapHandler, model_serializer

SeverityLevel = Literal["error", "warning", "info"]


class RequiredWhenSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_new_rows: str = Field(
        min_length=1,
        description=(
            "Source entity that owns this foreign key. The condition applies only after final reconciliation "
            "selects at least one row from this entity for insertion."
        ),
    )


class ForeignKeySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    required: bool = False
    via: str | None = None  # Bridge entity name for many-to-many relationships
    required_when: RequiredWhenSpec | None = Field(
        default=None,
        description="Condition that requires this foreign key after reconciliation.",
    )

    @model_serializer(mode="wrap")
    def serialize_foreign_key(self, handler: SerializerFunctionWrapHandler) -> Any:
        serialized = handler(self)
        if self.required_when is not None and "required" not in self.model_fields_set:
            serialized.pop("required", None)
        return serialized


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
    public_id_generation: Literal["database_sequence"] | None = Field(
        default=None,
        description=(
            "Reserve the public ID from the target table's database sequence before artifact generation. "
            "Use only when identity_tracking is explicitly set to a non-tracked value."
        ),
    )
    synchronize_sequence_after_insert: bool = Field(
        default=False,
        description=(
            "Advance the target column's PostgreSQL sequence after inserting rows with SIMS-assigned IDs, "
            "so later default-generated IDs do not reuse them."
        ),
    )
    columns: dict[str, ColumnSpec] = Field(default_factory=dict)
    unique_sets: list[list[str]] = Field(
        default_factory=list,
        description="Column groups declared unique for a target entity. Each group is an independent uniqueness rule.",
    )
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
