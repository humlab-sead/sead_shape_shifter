"""Pydantic models for entity configuration."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ForeignKeyConstraints(BaseModel):
    """Constraints for foreign key relationships."""

    cardinality: Literal["one_to_one", "many_to_one", "one_to_many", "many_to_many"] | None = None
    allow_unmatched_left: bool | None = None
    allow_unmatched_right: bool | None = None
    allow_row_decrease: bool | None = None
    require_unique_left: bool = False
    require_unique_right: bool = False
    allow_null_keys: bool = True

    @property
    def has_constraints(self) -> bool:
        """Check if any constraints are defined."""
        return any(
            [
                self.cardinality is not None,
                self.allow_unmatched_left is not None,
                self.allow_unmatched_right is not None,
                self.allow_row_decrease is not None,
                self.require_unique_left,
                self.require_unique_right,
                not self.allow_null_keys,
            ]
        )

    @property
    def has_match_constraints(self) -> bool:
        """Check if match constraints are defined."""
        return self.allow_unmatched_left is not None or self.allow_unmatched_right is not None


class ForeignKeyConfig(BaseModel):
    """Configuration for a foreign key relationship."""

    entity: str = Field(..., description="Remote entity name")
    local_keys: list[str] = Field(default_factory=list, description="Local key columns")
    remote_keys: list[str] = Field(default_factory=list, description="Remote key columns")
    how: Literal["left", "inner", "outer", "right", "cross"] = Field(default="inner", description="Join type")
    extra_columns: dict[str, str] | list[str] | str | None = Field(
        default=None, description="Additional columns to include from remote entity"
    )
    drop_remote_id: bool = Field(default=False, description="Drop remote surrogate ID after merge")
    constraints: ForeignKeyConstraints | None = Field(default=None, description="Foreign key constraints")

    @field_validator("local_keys", "remote_keys", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> list[str]:
        """Ensure keys are lists."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)


class UnnestConfig(BaseModel):
    """Configuration for unnesting (melting) wide data to long format."""

    id_vars: list[str] = Field(..., description="Identifier columns to keep")
    value_vars: list[str] = Field(..., description="Columns to melt")
    var_name: str = Field(..., description="Name for the variable column")
    value_name: str = Field(..., description="Name for the value column")


class FilterConfig(BaseModel):
    """Configuration for post-extraction filters."""

    type: str = Field(..., description="Filter type (e.g., 'exists_in')")
    entity: str | None = Field(default=None, description="Related entity for filter")
    column: str | None = Field(default=None, description="Column to filter on")
    remote_column: str | None = Field(default=None, description="Remote column for comparison")


class AppendConfig(BaseModel):
    """Configuration for appending data to an entity."""

    type: Literal["fixed", "sql"] = Field(..., description="Type of data to append")
    values: list[list[Any]] | None = Field(default=None, description="Fixed values to append")
    data_source: str | None = Field(default=None, description="Data source name for SQL")
    query: str | None = Field(default=None, description="SQL query for appending data")


class Entity(BaseModel):
    """Entity (table) configuration."""

    name: str = Field(..., description="Entity name (snake_case)")
    type: Literal["data", "sql", "fixed"] | None = Field(default=None, description="Data source type")
    source: str | None = Field(default=None, description="Source entity name")
    data_source: str | None = Field(default=None, description="Data source name for SQL type")
    query: str | None = Field(default=None, description="SQL query for SQL type")
    surrogate_id: str | None = Field(default=None, description="Surrogate ID column name")
    keys: list[str] = Field(default_factory=list, description="Natural key columns")
    columns: list[str] = Field(default_factory=list, description="Columns to extract")
    extra_columns: dict[str, Any] = Field(default_factory=dict, description="Additional computed columns")
    foreign_keys: list[ForeignKeyConfig] = Field(default_factory=list, description="Foreign key relationships")
    unnest: UnnestConfig | None = Field(default=None, description="Unnest configuration")
    filters: list[FilterConfig] = Field(default_factory=list, description="Post-extraction filters")
    append: list[AppendConfig] = Field(default_factory=list, description="Data to append")
    depends_on: list[str] = Field(default_factory=list, description="Processing dependencies")
    drop_duplicates: bool | list[str] = Field(default=False, description="Drop duplicate rows")
    drop_empty_rows: bool | list[str] = Field(default=False, description="Drop empty rows")
    check_column_names: bool = Field(default=True, description="Validate column names")
    values: list[list[Any]] | None = Field(default=None, description="Fixed values for 'fixed' type entities")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate entity name is snake_case."""
        if not v.islower() or " " in v:
            raise ValueError(f"Entity name must be snake_case: {v}")
        return v

    @field_validator("surrogate_id")
    @classmethod
    def validate_surrogate_id(cls, v: str | None) -> str | None:
        """Validate surrogate ID ends with _id."""
        if v and not v.endswith("_id"):
            raise ValueError(f"Surrogate ID must end with '_id': {v}")
        return v
