"""Tests for TargetModelValidator backend adapter."""

from backend.app.models.validation import ValidationCategory, ValidationPriority
from backend.app.validators.target_model_validator import TargetModelValidator
from src.model import ShapeShiftProject

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(entities: dict, options: dict | None = None) -> ShapeShiftProject:
    """Build a minimal resolved ShapeShiftProject with the given entity configs."""
    cfg: dict = {
        "metadata": {"name": "test-project", "type": "shapeshifter-project"},
        "entities": entities,
        "options": options or {},
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
        project = _make_project({"sample_group": _minimal_entity(public_id="sample_group_id")})
        target_model_data = _minimal_target_model(entities={"sample_group": {"required": True, "public_id": "sample_group_id"}})

        errors = TargetModelValidator().validate(target_model_data, project)

        assert errors == []

    def test_optional_entity_missing_from_project_returns_no_errors(self):
        """Non-required entity absent from project → no error."""
        project = _make_project({})
        target_model_data = _minimal_target_model(entities={"sample_group": {"required": False, "public_id": "sample_group_id"}})

        errors = TargetModelValidator().validate(target_model_data, project)

        assert errors == []

    def test_transitive_foreign_key_path_returns_no_errors(self):
        """A required FK satisfied through an intermediate project entity should not raise a direct-FK error."""
        project = _make_project(
            {
                "site": {"public_id": "site_id", "columns": ["site_name"]},
                "sample_group": {
                    "public_id": "sample_group_id",
                    "columns": ["sample_group_name"],
                    "foreign_keys": [{"entity": "site", "local_keys": ["site_id"], "remote_keys": ["site_id"]}],
                },
                "sample": {
                    "public_id": "sample_id",
                    "columns": ["sample_name"],
                    "foreign_keys": [
                        {"entity": "sample_group", "local_keys": ["sample_group_id"], "remote_keys": ["sample_group_id"]}
                    ],
                },
            }
        )
        target_model_data = _minimal_target_model(
            entities={
                "site": {"required": True, "public_id": "site_id"},
                "sample_group": {"required": True, "public_id": "sample_group_id", "foreign_keys": [{"entity": "site", "required": True}]},
                "sample": {"required": True, "public_id": "sample_id", "foreign_keys": [{"entity": "site", "required": True}]},
            }
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
        target_model_data = _minimal_target_model(entities={"sample_group": {"required": True}})

        errors = TargetModelValidator().validate(target_model_data, project)

        assert any(e.code == "MISSING_REQUIRED_ENTITY" for e in errors)
        missing = [e for e in errors if e.code == "MISSING_REQUIRED_ENTITY"][0]
        assert missing.entity == "sample_group"

    def test_wrong_public_id_returns_unexpected_public_id_error(self):
        """Entity has wrong public_id → UNEXPECTED_PUBLIC_ID error."""
        project = _make_project({"location": _minimal_entity(public_id="loc_id")})  # wrong
        target_model_data = _minimal_target_model(entities={"location": {"public_id": "location_id"}})

        errors = TargetModelValidator().validate(target_model_data, project)

        assert any(e.code == "UNEXPECTED_PUBLIC_ID" for e in errors)

    def test_entity_missing_public_id_returns_missing_public_id_error(self):
        """Entity exists but has no public_id while spec requires one → MISSING_PUBLIC_ID."""
        project = _make_project({"location": _minimal_entity(public_id=None)})
        target_model_data = _minimal_target_model(entities={"location": {"public_id": "location_id"}})

        errors = TargetModelValidator().validate(target_model_data, project)

        assert any(e.code == "MISSING_PUBLIC_ID" for e in errors)

    def test_missing_required_column_returns_error(self):
        """Entity is missing a column marked required in spec → MISSING_REQUIRED_COLUMN."""
        project = _make_project({"location": _minimal_entity(public_id="location_id", columns=["location_id"])})
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

    def test_generated_required_column_does_not_return_missing_required_column(self):
        """Required generated columns should not produce missing-column conformance errors."""
        project = _make_project({"location": _minimal_entity(public_id="location_id", columns=["location_name"])})
        target_model_data = _minimal_target_model(
            entities={
                "location": {
                    "public_id": "location_id",
                    "columns": {
                        "location_name": {"required": True},
                        "location_slug": {"required": True, "generated": True},
                    },
                }
            }
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert all(e.code != "MISSING_REQUIRED_COLUMN" for e in errors)

    def test_unknown_foreign_key_entity_returns_specific_spec_issue(self):
        """Spec self-consistency issues should surface their specific code, not INVALID_TARGET_MODEL."""
        project = _make_project({})
        target_model_data = _minimal_target_model(
            entities={
                "site": {
                    "public_id": "site_id",
                    "foreign_keys": [{"entity": "location", "required": True}],
                }
            }
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert [error.code for error in errors] == ["UNKNOWN_FOREIGN_KEY_ENTITY"]
        assert errors[0].entity == "site"
        assert errors[0].field is None
        assert errors[0].suggestion == "Fix the target model specification and rerun validation."

    def test_aggregate_parent_spec_issue_blocks_conformance_and_surfaces_specific_code(self):
        """Aggregate-parent self-consistency issues should be returned directly before project conformance runs."""
        project = _make_project({"sample": _minimal_entity(public_id="sample_id")})
        target_model_data = _minimal_target_model(
            entities={
                "sample": {"public_id": "sample_id"},
                "sample_description": {
                    "public_id": "sample_description_id",
                    "aggregate_parent": "sample",
                },
            }
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert [error.code for error in errors] == ["MISSING_AGGREGATE_PARENT_FOREIGN_KEY"]
        assert errors[0].entity == "sample_description"

    def test_unknown_disabled_rule_returns_warning(self):
        """Unknown disabled rule keys should surface as warnings instead of being silently ignored."""
        project = _make_project({}, options={"validation": {"disabled_rules": ["not_a_real_rule"]}})

        errors = TargetModelValidator().validate(_minimal_target_model(), project)

        assert [error.code for error in errors] == ["UNKNOWN_DISABLED_CONFORMANCE_RULE"]
        assert errors[0].severity == "warning"
        assert errors[0].field == "options.validation.disabled_rules"

    def test_unknown_severity_override_returns_warning(self):
        """Unknown severity override keys should surface as warnings instead of being silently ignored."""
        project = _make_project({}, options={"validation": {"severity_overrides": {"not_a_real_rule": "warning"}}})

        errors = TargetModelValidator().validate(_minimal_target_model(), project)

        assert [error.code for error in errors] == ["UNKNOWN_CONFORMANCE_SEVERITY_OVERRIDE"]
        assert errors[0].severity == "warning"
        assert errors[0].field == "options.validation.severity_overrides"

    def test_invalid_severity_override_returns_warning(self):
        """Invalid severity override values should surface as warnings instead of being silently ignored."""
        project = _make_project({}, options={"validation": {"severity_overrides": {"required_entity": "fatal"}}})

        errors = TargetModelValidator().validate(_minimal_target_model(), project)

        assert [error.code for error in errors] == ["INVALID_CONFORMANCE_SEVERITY_OVERRIDE"]
        assert errors[0].severity == "warning"
        assert errors[0].field == "options.validation.severity_overrides.required_entity"

    def test_orphan_fact_constraint_returns_warning_by_default(self):
        """Declared orphan-fact constraints should surface as conformance warnings unless marked strict."""
        project = _make_project(
            {
                "analysis_entity": {"public_id": "analysis_entity_id", "columns": ["analysis_name"]},
                "dataset": {"public_id": "dataset_id", "columns": ["dataset_name"]},
            }
        )
        target_model_data = {
            "model": {"name": "Test Model", "version": "1.0.0"},
            "constraints": [{"type": "no_orphan_facts"}],
            "entities": {
                "dataset": {"role": "lookup", "required": True, "public_id": "dataset_id"},
                "analysis_entity": {"role": "fact", "required": True, "public_id": "analysis_entity_id"},
            },
        }

        errors = TargetModelValidator().validate(target_model_data, project)

        orphan_fact_error = next(error for error in errors if error.code == "ORPHAN_FACT_ENTITY")
        assert orphan_fact_error.severity == "warning"

    def test_orphan_fact_constraint_returns_error_when_strict(self):
        """Strict orphan-fact constraints should surface as conformance errors through the adapter."""
        project = _make_project(
            {
                "analysis_entity": {"public_id": "analysis_entity_id", "columns": ["analysis_name"]},
                "dataset": {"public_id": "dataset_id", "columns": ["dataset_name"]},
            }
        )
        target_model_data = {
            "model": {"name": "Test Model", "version": "1.0.0"},
            "constraints": [{"type": "no_orphan_facts", "required": "strict"}],
            "entities": {
                "dataset": {"role": "lookup", "required": True, "public_id": "dataset_id"},
                "analysis_entity": {"role": "fact", "required": True, "public_id": "analysis_entity_id"},
            },
        }

        errors = TargetModelValidator().validate(target_model_data, project)

        orphan_fact_error = next(error for error in errors if error.code == "ORPHAN_FACT_ENTITY")
        assert orphan_fact_error.severity == "error"

    def test_source_type_appropriateness_returns_warning_by_default(self):
        """Classifier source-type mismatches should surface as warnings through the adapter."""
        project = _make_project(
            {
                "taxon": {"type": "entity", "public_id": "taxon_id", "columns": ["taxon_name"]},
            }
        )
        target_model_data = _minimal_target_model(
            entities={
                "taxon": {"role": "classifier", "required": True, "public_id": "taxon_id"},
            }
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        source_type_error = next(error for error in errors if error.code == "CLASSIFIER_WRONG_SOURCE_TYPE")
        assert source_type_error.severity == "warning"

    def test_schema_aware_append_returns_missing_required_column_error(self):
        """Append branches missing required target columns should surface through the adapter."""
        project = _make_project(
            {
                "site": {
                    "public_id": "site_id",
                    "columns": ["site_name", "site_type"],
                    "append": [{"type": "fixed", "columns": ["site_name"], "values": [["Append Site"]]}],
                }
            }
        )
        target_model_data = _minimal_target_model(
            entities={
                "site": {
                    "required": True,
                    "public_id": "site_id",
                    "columns": {"site_name": {"required": True}, "site_type": {"required": True}},
                }
            }
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert any(error.code == "APPEND_MISSING_REQUIRED_COLUMN" for error in errors)


# ---------------------------------------------------------------------------
# ValidationError shape produced by the adapter
# ---------------------------------------------------------------------------


class TestValidationErrorShape:

    def test_conformance_errors_have_correct_metadata(self):
        """Errors produced by the adapter must have expected severity, category, and priority."""
        project = _make_project({})
        target_model_data = _minimal_target_model(entities={"sample_group": {"required": True}})

        errors = TargetModelValidator().validate(target_model_data, project)

        assert errors, "Expected at least one conformance error"
        for err in errors:
            assert err.severity == "error"
            assert err.category == ValidationCategory.CONFORMANCE
            assert err.priority == ValidationPriority.HIGH
            assert err.auto_fixable is False
            assert err.suggestion is None

    def test_spec_errors_have_correct_metadata(self):
        """Spec validation errors should use conformance metadata and keep their specific code."""
        project = _make_project({})
        target_model_data = _minimal_target_model(
            entities={
                "site": {
                    "public_id": "site_id",
                    "foreign_keys": [{"entity": "location", "required": True}],
                }
            }
        )

        errors = TargetModelValidator().validate(target_model_data, project)

        assert errors, "Expected at least one target-model spec error"
        for err in errors:
            assert err.severity == "error"
            assert err.category == ValidationCategory.CONFORMANCE
            assert err.priority == ValidationPriority.HIGH
            assert err.auto_fixable is False
            assert err.suggestion == "Fix the target model specification and rerun validation."
