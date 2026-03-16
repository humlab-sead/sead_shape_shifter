"""Tests for preview endpoint error mapping."""

import pytest

from backend.app.api.v1.endpoints.preview import _raise_fk_constraint_validation_error
from backend.app.exceptions import ConstraintViolationError
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
    assert exc.message == "Validation failed for site_location -> location: null values found in remote key 'location_name'."
    assert exc.context["key_column"] == "location_name"
    assert exc.context["key_side"] == "remote"
    assert exc.recoverable is True
    assert any("Allow Null Keys" in tip for tip in exc.tips)


def test_raise_fk_constraint_validation_error_preserves_generic_fk_violation() -> None:
    """Generic FK constraint violations should still map without null-key-specific context."""
    error = ForeignKeyConstraintViolation("orders -> users: 2 duplicate right key(s) found (require_unique_right=True)")

    with pytest.raises(ConstraintViolationError) as exc_info:
        _raise_fk_constraint_validation_error(error, "orders")

    exc = exc_info.value
    assert exc.message == "orders -> users: 2 duplicate right key(s) found (require_unique_right=True)"
    assert exc.context["constraint"] == "foreign_key"
