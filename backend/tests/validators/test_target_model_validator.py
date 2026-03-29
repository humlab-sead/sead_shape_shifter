"""Tests for TargetModelValidator backend adapter."""

from unittest.mock import MagicMock

import pytest

from backend.app.models.validation import ValidationCategory, ValidationPriority
from backend.app.validators.target_model_validator import TargetModelValidator
from src.model import ShapeShiftProject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(entities: dict) -> ShapeShiftProject:
    """Build a minimal resolved ShapeShiftProject with the given entity configs."""
    cfg: dict = {
        "metadata": {"name": "test-project", "type": "shapeshifter-project"},
        "entities": entities,
    }
    return ShapeShiftProject(cfg=cfg, filename="test.yml")


def _minimal_entity(public_id: str | None = None, columns: list[str] | None = None) -> dict:
    entity: dict = {"system_id": "system_id", "data": {"type": "fixed", "values": []}}
    if public_id:
        entity["public_id"] = public_id
    if columns:
        entity["columns"] = columns
    return entity


def _minimal_target_model(entities: dict | None = None) -> dict:
    return {
        "model": {"name": "Test Model", "version": "1.0.0"},
        "entities": entities or {},
    }


# ---------------------------------------------------------------------------
# TargetModelValidator.validate – happy paths
# ---------------------------------------------------------------------------

class TestTargetModelValidatorHappyPaths:

    def test_empty_entities_returns_no_errors(self):
        """No entities in either project or target model → conformant."""
        project = _make_project({})
        target_model_data = _minimal_target_model()

        errors = TargetModelValidator().validate(target_model_data, project)

        assert errors == []

    def test_matching_public_id_returns_no_errors(self):
        """Entity with correct public_id → no conformance error."""
        project = _make_project(
            {"sample_group": _minimal_entity(public_id="sample_group_id")}
        )
        target_model_data = _minimal_target_model(
            entities={"sample_group": {"required": True, "public_id": "sample_group_id"}}
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert errors == []

    def test_optional_entity_missing_from_project_returns_no_errors(self):
        """Non-required entity absent from project → no error."""
        project = _make_project({})
        target_model_data = _minimal_target_model(
            entities={"sample_group": {"required": False, "public_id": "sample_group_id"}}
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert errors == []


# ---------------------------------------------------------------------------
# TargetModelValidator.validate – error paths
# ---------------------------------------------------------------------------

class TestTargetModelValidatorErrorPaths:

    def test_malformed_target_model_returns_parse_error(self):
        """Non-conformant target model dict → INVALID_TARGET_MODEL error."""
        project = _make_project({})
        bad_target_model = {"not_a_valid_key": True}  # missing required "model" key

        errors = TargetModelValidator().validate(bad_target_model, project)

        assert len(errors) == 1
        assert errors[0].code == "INVALID_TARGET_MODEL"
        assert errors[0].severity == "error"
        assert errors[0].field == "metadata.target_model"

    def test_missing_required_entity_returns_error(self):
        """Required entity absent from project → MISSING_REQUIRED_ENTITY error."""
        project = _make_project({})  # no entities
        target_model_data = _minimal_target_model(
            entities={"sample_group": {"required": True}}
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert any(e.code == "MISSING_REQUIRED_ENTITY" for e in errors)
        missing = [e for e in errors if e.code == "MISSING_REQUIRED_ENTITY"][0]
        assert missing.entity == "sample_group"

    def test_wrong_public_id_returns_unexpected_public_id_error(self):
        """Entity has wrong public_id → UNEXPECTED_PUBLIC_ID error."""
        project = _make_project(
            {"location": _minimal_entity(public_id="loc_id")}  # wrong
        )
        target_model_data = _minimal_target_model(
            entities={"location": {"public_id": "location_id"}}
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert any(e.code == "UNEXPECTED_PUBLIC_ID" for e in errors)

    def test_entity_missing_public_id_returns_missing_public_id_error(self):
        """Entity exists but has no public_id while spec requires one → MISSING_PUBLIC_ID."""
        project = _make_project(
            {"location": _minimal_entity(public_id=None)}
        )
        target_model_data = _minimal_target_model(
            entities={"location": {"public_id": "location_id"}}
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert any(e.code == "MISSING_PUBLIC_ID" for e in errors)

    def test_missing_required_column_returns_error(self):
        """Entity is missing a column marked required in spec → MISSING_REQUIRED_COLUMN."""
        project = _make_project(
            {"location": _minimal_entity(public_id="location_id", columns=["location_id"])}
        )
        target_model_data = _minimal_target_model(
            entities={
                "location": {
                    "public_id": "location_id",
                    "columns": {"location_name": {"required": True}},
                }
            }
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert any(e.code == "MISSING_REQUIRED_COLUMN" for e in errors)


# ---------------------------------------------------------------------------
# ValidationError shape produced by the adapter
# ---------------------------------------------------------------------------

class TestValidationErrorShape:

    def test_conformance_errors_have_correct_metadata(self):
        """Errors produced by the adapter must have expected severity, category, and priority."""
        project = _make_project({})
        target_model_data = _minimal_target_model(
            entities={"sample_group": {"required": True}}
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert errors, "Expected at least one conformance error"
        for err in errors:
            assert err.severity == "error"
            assert err.category == ValidationCategory.STRUCTURAL
            assert err.priority == ValidationPriority.HIGH
            assert err.auto_fixable is False
            assert err.suggestion is None
