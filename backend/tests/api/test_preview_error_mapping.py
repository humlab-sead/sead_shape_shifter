"""Tests for preview and column-availability error mapping."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from backend.app.api.v1.endpoints import columns as columns_endpoint
from backend.app.api.v1.endpoints.preview import _raise_fk_constraint_validation_error, preview_entity
from backend.app.exceptions import ConstraintViolationError, ValidationError
from src.specifications.constraints import ForeignKeyConstraintViolation, ForeignKeyNullConstraintViolation


def test_raise_fk_constraint_validation_error_formats_null_key_violation() -> None:
    """Null-key FK violations should be converted into friendly structured validation errors."""
    error = ForeignKeyNullConstraintViolation(
        local_entity="site_location",
        remote_entity="location",
        key_side="remote",
        key_column="location_name",
    )

    with pytest.raises(ConstraintViolationError) as exc_info:
        _raise_fk_constraint_validation_error(error, "site_location")

    exc = exc_info.value
    assert exc.message == "Validation failed for site_location -> location: missing values found in remote key 'location_name'."
    assert exc.context["key_column"] == "location_name"
    assert exc.context["key_side"] == "remote"
    assert exc.recoverable is True
    assert any("Allow missing Join Keys" in tip for tip in exc.tips)


def test_raise_fk_constraint_validation_error_preserves_generic_fk_violation() -> None:
    """Generic FK constraint violations should still map without null-key-specific context."""
    error = ForeignKeyConstraintViolation("orders -> users: 2 duplicate right key(s) found (require_unique_right=True)")

    with pytest.raises(ConstraintViolationError) as exc_info:
        _raise_fk_constraint_validation_error(error, "orders")

    exc = exc_info.value
    assert exc.message == "orders -> users: 2 duplicate right key(s) found (require_unique_right=True)"
    assert exc.context["constraint"] == "foreign_key"


def _fixed_entity_shape_error() -> ValidationError:
    return ValidationError(
        message="Entity 'data_provider' row 0 has an invalid number of values.",
        error_code="FIXED_ENTITY_SHAPE_INVALID",
        tips=["Check the fixed entity's columns and values."],
        context={"entity": "data_provider", "validation": "fixed_entity_shape"},
        recoverable=True,
    )


def _error_detail(exc: HTTPException) -> dict[str, Any]:
    """Return the structured error payload carried by the exception detail."""
    assert isinstance(exc.detail, dict)
    return exc.detail


@pytest.mark.asyncio
async def test_preview_returns_structured_fixed_entity_validation_error() -> None:
    preview_service = Mock()
    preview_service.preview_entity = AsyncMock(side_effect=_fixed_entity_shape_error())
    authorized_project = SimpleNamespace(resource=SimpleNamespace(locator="test_project"))

    with pytest.raises(HTTPException) as exc_info:
        await preview_entity(
            authorized_project=authorized_project,
            project_name="test_project",
            entity_name="data_provider",
            body=None,
            limit=50,
            preview_service=preview_service,
        )

    assert exc_info.value.status_code == 400
    detail = _error_detail(exc_info.value)
    assert detail["error_code"] == "FIXED_ENTITY_SHAPE_INVALID"
    assert detail["message"] == "Entity 'data_provider' row 0 has an invalid number of values."


@pytest.mark.asyncio
async def test_column_availability_returns_structured_fixed_entity_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service = Mock()
    service.get_column_availability.side_effect = _fixed_entity_shape_error()
    monkeypatch.setattr(columns_endpoint, "StageAwareColumnService", lambda: service)
    authorized_project = SimpleNamespace(resource=SimpleNamespace(locator="test_project"))
    request = SimpleNamespace(entity_draft={"type": "entity"}, source_columns=None)

    with pytest.raises(HTTPException) as exc_info:
        await columns_endpoint.get_stage_aware_column_availability(
            project_name="test_project",
            entity_name="child",
            request=request,
            authorized_project=authorized_project,
        )

    assert exc_info.value.status_code == 400
    detail = _error_detail(exc_info.value)
    assert detail["error_code"] == "FIXED_ENTITY_SHAPE_INVALID"
    assert detail["context"]["entity"] == "data_provider"
