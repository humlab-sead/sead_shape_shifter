"""Models for the curated data provider registry.

A provider record lists the provider schemas a data provider delivers. Each schema
carries the stable scope name that Shape Shifter and SIMS use to identify one
provider-schema pair.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _require_text(value: str, field_name: str) -> str:
    """Return trimmed text, rejecting a blank value."""
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must not be blank")
    return text


class DataProviderSchema(BaseModel):
    """One provider schema and its scope name."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_schema: str = Field(..., description="Stable provider schema code")
    scope_name: str = Field(..., description="Stable scope name derived from the provider code and schema code")

    @field_validator("provider_schema", "scope_name")
    @classmethod
    def validate_text(cls, value: str, info: Any) -> str:
        """Reject blank schema codes and scope names."""
        return _require_text(value, info.field_name)


class DataProvider(BaseModel):
    """One provider and the schemas it delivers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(..., description="Stable provider code")
    name: str = Field(..., description="Provider display name")
    schemas: list[DataProviderSchema] = Field(..., min_length=1, description="Provider schemas, at least one")

    @field_validator("code", "name")
    @classmethod
    def validate_text(cls, value: str, info: Any) -> str:
        """Reject blank provider codes and display names."""
        return _require_text(value, info.field_name)

    @model_validator(mode="after")
    def validate_schema_identities(self) -> "DataProvider":
        """Require each scope name to match its pair and schema codes to be unique."""
        schema_codes: set[str] = set()
        for schema in self.schemas:
            expected_scope = f"provider://{self.code}/{schema.provider_schema}"
            if schema.scope_name != expected_scope:
                raise ValueError(f"scope_name '{schema.scope_name}' must equal '{expected_scope}'")
            if schema.provider_schema in schema_codes:
                raise ValueError(f"duplicate provider_schema '{schema.provider_schema}' for provider '{self.code}'")
            schema_codes.add(schema.provider_schema)
        return self
