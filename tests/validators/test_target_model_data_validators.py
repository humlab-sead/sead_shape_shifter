"""Tests for target-model-aware data conformance validators."""

import pandas as pd
import pytest

from src.target_model.models import ColumnSpec, EntitySpec, ForeignKeySpec
from src.target_model.data_validators import (
    FKReferentialIntegrityConformanceValidator,
    NullabilityConformanceValidator,
    TypeCompatibilityConformanceValidator,
)


def make_entity_spec(**kwargs) -> EntitySpec:
    from src.target_model.models import ModelMetadata, TargetModel

    return EntitySpec(**kwargs)


# ---------------------------------------------------------------------------
# NullabilityConformanceValidator
# ---------------------------------------------------------------------------


class TestNullabilityConformanceValidator:
    def test_passes_when_no_nulls(self):
        spec = make_entity_spec(columns={"name": ColumnSpec(required=True, nullable=False)})
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        assert NullabilityConformanceValidator.validate(df, spec, "person") == []

    def test_reports_nulls_in_required_non_nullable_column(self):
        spec = make_entity_spec(columns={"name": ColumnSpec(required=True, nullable=False)})
        df = pd.DataFrame({"name": ["Alice", None]})
        issues = NullabilityConformanceValidator.validate(df, spec, "person")
        assert len(issues) == 1
        assert issues[0].code == "NULL_IN_REQUIRED_COLUMN"
        assert issues[0].entity == "person"
        assert issues[0].field == "name"
        assert issues[0].severity == "error"
        assert "1 null" in issues[0].message

    def test_reports_nulls_when_nullable_unspecified(self):
        """nullable=None (unspecified) + required=True → treat as not nullable."""
        spec = make_entity_spec(columns={"name": ColumnSpec(required=True, nullable=None)})
        df = pd.DataFrame({"name": [None, None]})
        issues = NullabilityConformanceValidator.validate(df, spec, "person")
        assert len(issues) == 1
        assert "2 null" in issues[0].message

    def test_skips_explicitly_nullable_column(self):
        spec = make_entity_spec(columns={"note": ColumnSpec(required=True, nullable=True)})
        df = pd.DataFrame({"note": [None, None]})
        assert NullabilityConformanceValidator.validate(df, spec, "person") == []

    def test_skips_non_required_column(self):
        spec = make_entity_spec(columns={"note": ColumnSpec(required=False, nullable=False)})
        df = pd.DataFrame({"note": [None]})
        assert NullabilityConformanceValidator.validate(df, spec, "person") == []

    def test_skips_column_absent_from_dataframe(self):
        """Missing columns are a structural conformance issue, not data conformance."""
        spec = make_entity_spec(columns={"name": ColumnSpec(required=True, nullable=False)})
        df = pd.DataFrame({"other": [1, 2]})
        assert NullabilityConformanceValidator.validate(df, spec, "person") == []

    def test_empty_dataframe_returns_no_issues(self):
        spec = make_entity_spec(columns={"name": ColumnSpec(required=True, nullable=False)})
        assert NullabilityConformanceValidator.validate(pd.DataFrame(), spec, "person") == []

    def test_multiple_columns_with_nulls(self):
        spec = make_entity_spec(
            columns={
                "first": ColumnSpec(required=True),
                "last": ColumnSpec(required=True),
            }
        )
        df = pd.DataFrame({"first": [None], "last": [None]})
        issues = NullabilityConformanceValidator.validate(df, spec, "person")
        codes = [i.code for i in issues]
        assert codes.count("NULL_IN_REQUIRED_COLUMN") == 2


# ---------------------------------------------------------------------------
# TypeCompatibilityConformanceValidator
# ---------------------------------------------------------------------------


class TestTypeCompatibilityConformanceValidator:
    def test_passes_integer_column_with_int_dtype(self):
        spec = make_entity_spec(columns={"count": ColumnSpec(type="integer")})
        df = pd.DataFrame({"count": [1, 2, 3]})
        assert TypeCompatibilityConformanceValidator.validate(df, spec, "entity") == []

    def test_reports_integer_column_with_object_dtype(self):
        spec = make_entity_spec(columns={"count": ColumnSpec(type="integer")})
        df = pd.DataFrame({"count": ["a", "b"]})
        issues = TypeCompatibilityConformanceValidator.validate(df, spec, "entity")
        assert len(issues) == 1
        assert issues[0].code == "TYPE_INCOMPATIBLE"
        assert issues[0].severity == "warning"
        assert "integer" in issues[0].message
        assert "object" in issues[0].message

    def test_passes_string_column_with_object_dtype(self):
        spec = make_entity_spec(columns={"name": ColumnSpec(type="string")})
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        assert TypeCompatibilityConformanceValidator.validate(df, spec, "entity") == []

    def test_passes_float_column_for_number_type(self):
        spec = make_entity_spec(columns={"ratio": ColumnSpec(type="float")})
        df = pd.DataFrame({"ratio": [1.0, 2.5]})
        assert TypeCompatibilityConformanceValidator.validate(df, spec, "entity") == []

    def test_passes_integer_column_for_float_type(self):
        """Integers are compatible with float type."""
        spec = make_entity_spec(columns={"ratio": ColumnSpec(type="float")})
        df = pd.DataFrame({"ratio": [1, 2]})
        assert TypeCompatibilityConformanceValidator.validate(df, spec, "entity") == []

    def test_reports_string_column_for_integer_type(self):
        spec = make_entity_spec(columns={"id": ColumnSpec(type="integer")})
        df = pd.DataFrame({"id": ["x", "y"]})
        issues = TypeCompatibilityConformanceValidator.validate(df, spec, "entity")
        assert len(issues) == 1
        assert issues[0].code == "TYPE_INCOMPATIBLE"

    def test_skips_unknown_type(self):
        spec = make_entity_spec(columns={"val": ColumnSpec(type="uuid")})
        df = pd.DataFrame({"val": ["abc-def"]})
        assert TypeCompatibilityConformanceValidator.validate(df, spec, "entity") == []

    def test_skips_column_with_no_declared_type(self):
        spec = make_entity_spec(columns={"val": ColumnSpec()})
        df = pd.DataFrame({"val": [1]})
        assert TypeCompatibilityConformanceValidator.validate(df, spec, "entity") == []

    def test_skips_column_absent_from_dataframe(self):
        spec = make_entity_spec(columns={"count": ColumnSpec(type="integer")})
        df = pd.DataFrame({"other": [1]})
        assert TypeCompatibilityConformanceValidator.validate(df, spec, "entity") == []

    def test_empty_dataframe_returns_no_issues(self):
        spec = make_entity_spec(columns={"count": ColumnSpec(type="integer")})
        assert TypeCompatibilityConformanceValidator.validate(pd.DataFrame(), spec, "entity") == []

    def test_datetime_column_for_date_type(self):
        spec = make_entity_spec(columns={"created": ColumnSpec(type="date")})
        df = pd.DataFrame({"created": pd.to_datetime(["2024-01-01", "2024-06-15"])})
        assert TypeCompatibilityConformanceValidator.validate(df, spec, "entity") == []


# ---------------------------------------------------------------------------
# FKReferentialIntegrityConformanceValidator
# ---------------------------------------------------------------------------


class TestFKReferentialIntegrityConformanceValidator:
    def _fk_spec(self, entity: str) -> ForeignKeySpec:
        return ForeignKeySpec(entity=entity, required=True)

    def _target_spec(self, public_id: str) -> EntitySpec:
        return make_entity_spec(public_id=public_id)

    def test_passes_when_all_fk_values_present(self):
        fk_spec = self._fk_spec("location")
        target_spec = self._target_spec("location_id")
        df = pd.DataFrame({"location_id": [1, 2, 3]})
        target_df = pd.DataFrame({"location_id": [1, 2, 3, 4]})
        assert FKReferentialIntegrityConformanceValidator.validate(df, fk_spec, target_df, target_spec, "site") == []

    def test_reports_orphaned_fk_values(self):
        fk_spec = self._fk_spec("location")
        target_spec = self._target_spec("location_id")
        df = pd.DataFrame({"location_id": [1, 2, 99]})
        target_df = pd.DataFrame({"location_id": [1, 2, 3]})
        issues = FKReferentialIntegrityConformanceValidator.validate(df, fk_spec, target_df, target_spec, "site")
        assert len(issues) == 1
        assert issues[0].code == "FK_REFERENTIAL_INTEGRITY"
        assert issues[0].entity == "site"
        assert issues[0].field == "location_id"
        assert issues[0].severity == "warning"
        assert "1 value" in issues[0].message
        assert "99" in issues[0].suggestion

    def test_reports_multiple_orphaned_values(self):
        fk_spec = self._fk_spec("location")
        target_spec = self._target_spec("location_id")
        df = pd.DataFrame({"location_id": [10, 20, 30]})
        target_df = pd.DataFrame({"location_id": [1, 2]})
        issues = FKReferentialIntegrityConformanceValidator.validate(df, fk_spec, target_df, target_spec, "site")
        assert len(issues) == 1
        assert "3 value" in issues[0].message

    def test_skips_when_no_public_id_on_target(self):
        fk_spec = self._fk_spec("location")
        target_spec = make_entity_spec()  # no public_id
        df = pd.DataFrame({"location_id": [1]})
        target_df = pd.DataFrame({"location_id": [2]})
        assert FKReferentialIntegrityConformanceValidator.validate(df, fk_spec, target_df, target_spec, "site") == []

    def test_skips_when_fk_col_absent_from_source(self):
        fk_spec = self._fk_spec("location")
        target_spec = self._target_spec("location_id")
        df = pd.DataFrame({"other_col": [1]})
        target_df = pd.DataFrame({"location_id": [1]})
        assert FKReferentialIntegrityConformanceValidator.validate(df, fk_spec, target_df, target_spec, "site") == []

    def test_skips_when_fk_col_absent_from_target(self):
        fk_spec = self._fk_spec("location")
        target_spec = self._target_spec("location_id")
        df = pd.DataFrame({"location_id": [1]})
        target_df = pd.DataFrame({"other_col": [1]})
        assert FKReferentialIntegrityConformanceValidator.validate(df, fk_spec, target_df, target_spec, "site") == []

    def test_empty_source_returns_no_issues(self):
        fk_spec = self._fk_spec("location")
        target_spec = self._target_spec("location_id")
        assert FKReferentialIntegrityConformanceValidator.validate(pd.DataFrame(), fk_spec, pd.DataFrame({"location_id": [1]}), target_spec, "site") == []

    def test_empty_target_returns_no_issues(self):
        """Empty target — not our concern here (orphaned-values check can't run)."""
        fk_spec = self._fk_spec("location")
        target_spec = self._target_spec("location_id")
        assert FKReferentialIntegrityConformanceValidator.validate(pd.DataFrame({"location_id": [1]}), fk_spec, pd.DataFrame(), target_spec, "site") == []

    def test_nulls_in_source_are_excluded(self):
        """Null FK values should not be counted as orphaned."""
        fk_spec = self._fk_spec("location")
        target_spec = self._target_spec("location_id")
        df = pd.DataFrame({"location_id": [1, None]})
        target_df = pd.DataFrame({"location_id": [1, 2]})
        assert FKReferentialIntegrityConformanceValidator.validate(df, fk_spec, target_df, target_spec, "site") == []
