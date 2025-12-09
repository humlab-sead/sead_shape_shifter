"""Unit tests for arbodat utility functions."""

from typing import Any

import pandas as pd
import pytest

from src.extract import (
    SubsetService,
    _rename_last_occurence,
    add_surrogate_id,
    check_functional_dependency,
    extract_translation_map,
    translate,
)


def get_subset(
    source: pd.DataFrame,
    columns: list[str],
    *,
    entity_name: str | None = None,
    extra_columns: None | dict[str, Any] = None,
    drop_duplicates: bool | list[str] = False,
    fd_check: bool = False,
    raise_if_missing: bool = True,
    drop_empty_rows: bool | list[str] = False,
) -> pd.DataFrame:
    """Backward-compatible convenience function to get subset using SubsetService."""
    return SubsetService().get_subset(
        source=source,
        columns=columns,
        entity_name=entity_name,
        extra_columns=extra_columns,
        drop_duplicates=drop_duplicates,
        fd_check=fd_check,
        raise_if_missing=raise_if_missing,
        drop_empty=drop_empty_rows,
    )


class TestAddSurrogateId:
    """Tests for add_surrogate_id function."""

    def test_adds_surrogate_id_starting_at_1(self):
        """Test that surrogate ID starts at 1."""
        df = pd.DataFrame({"name": ["A", "B", "C"]})
        result = add_surrogate_id(df, "id")

        assert "id" in result.columns
        assert result["id"].tolist() == [1, 2, 3]

    def test_preserves_existing_data(self):
        """Test that existing data is preserved."""
        df = pd.DataFrame({"name": ["A", "B"], "value": [10, 20]})
        result = add_surrogate_id(df, "id")

        assert result["name"].tolist() == ["A", "B"]
        assert result["value"].tolist() == [10, 20]

    def test_resets_index(self):
        """Test that index is reset."""
        df = pd.DataFrame({"name": ["A", "B", "C"]}, index=[5, 10, 15])
        result = add_surrogate_id(df, "id")

        assert result["id"].tolist() == [1, 2, 3]
        assert result.index.tolist() == [0, 1, 2]

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame({"name": []})
        result = add_surrogate_id(df, "id")

        assert len(result) == 0
        assert "id" in result.columns


class TestCheckFunctionalDependency:
    """Tests for check_functional_dependency function."""

    def test_valid_functional_dependency(self):
        """Test with valid functional dependency."""
        df = pd.DataFrame({"key": ["A", "A", "B", "B"], "value": [1, 1, 2, 2]})

        result = check_functional_dependency(df, ["key"], raise_error=False)
        assert result is True

    def test_invalid_functional_dependency_raises(self):
        """Test that invalid dependency raises error."""
        df = pd.DataFrame({"key": ["A", "A", "B"], "value": [1, 2, 3]})

        with pytest.raises(ValueError, match="inconsistent non-subset values"):
            check_functional_dependency(df, ["key"], raise_error=True)

    def test_invalid_functional_dependency_warns(self):
        """Test that invalid dependency warns when raise_error=False."""
        df = pd.DataFrame({"key": ["A", "A"], "value": [1, 2]})

        result = check_functional_dependency(df, ["key"], raise_error=False)
        assert result is False

    def test_no_dependent_columns(self):
        """Test with only determinant columns."""
        df = pd.DataFrame({"key": ["A", "B", "C"]})

        result = check_functional_dependency(df, ["key"], raise_error=True)
        assert result is True

    def test_multiple_determinant_columns(self):
        """Test with multiple determinant columns."""
        df = pd.DataFrame({"key1": ["A", "A", "B", "B"], "key2": [1, 2, 1, 2], "value": [10, 20, 30, 40]})

        result = check_functional_dependency(df, ["key1", "key2"], raise_error=False)
        assert result is True


class TestGetSubset:
    """Tests for get_subset function."""

    def test_basic_column_extraction(self):
        """Test extracting basic columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = get_subset(df, ["A", "B"])

        assert list(result.columns) == ["A", "B"]
        assert len(result) == 2

    def test_raises_on_none_source(self):
        """Test that None source raises ValueError."""
        with pytest.raises(ValueError, match="Source DataFrame must be provided"):
            get_subset(None, ["A"])  # type: ignore

    def test_missing_columns_raises_error(self):
        """Test that missing columns raise error by default."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        with pytest.raises(ValueError, match="Columns not found"):
            get_subset(df, ["A", "C"])

    def test_missing_columns_warns_when_not_raising(self):
        """Test that missing columns warn when raise_if_missing=False."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A", "C"], raise_if_missing=False)

        assert list(result.columns) == ["A"]
        assert len(result) == 2

    def test_extra_columns_rename_source_column(self):
        """Test add new source column via extra_columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})

        result = get_subset(df, ["A"], extra_columns={"D": "C"})

        assert list(result.columns) == ["A", "C", "D"]
        assert result["D"].tolist() == [5, 6]

    def test_extra_columns_add_constant(self):
        """Test adding constant column via extra_columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"constant": "fixed_value"})

        assert "constant" in result.columns
        assert result["constant"].tolist() == ["fixed_value", "fixed_value"]

    def test_extra_columns_add_numeric_constant(self):
        """Test adding numeric constant column."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"num": 42})

        assert result["num"].tolist() == [42, 42]

    def test_extra_columns_add_null_constant(self):
        """Test adding null constant column."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"nullable": None})

        assert result["nullable"].isna().all()

    def test_extra_columns_mixed_reference_and_constant(self):
        """Test mixing extra column with reference and constant addition."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})

        result = get_subset(df, ["A"], extra_columns={"extra_B": "B", "constant": 100})

        assert list(result.columns) == ["A", "B", "extra_B", "constant"]
        assert result["extra_B"].tolist() == [3, 4]
        assert result["constant"].tolist() == [100, 100]

    def test_extra_columns_nonexistent_source_as_constant(self):
        """Test that non-existent source column name is treated as constant."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"new_col": "NonExistent"})

        assert "new_col" in result.columns
        assert result["new_col"].tolist() == ["NonExistent", "NonExistent"]

    def test_drop_duplicates_true(self):
        """Test dropping all duplicates."""
        df = pd.DataFrame({"A": [1, 1, 2], "B": [3, 3, 4]})

        result = get_subset(df, ["A", "B"], drop_duplicates=True)

        assert len(result) == 2

    def test_drop_duplicates_by_subset(self):
        """Test dropping duplicates by subset of columns."""
        df = pd.DataFrame({"A": [1, 1, 2], "B": [3, 4, 5]})

        result = get_subset(df, ["A", "B"], drop_duplicates=["A"])

        assert len(result) == 2
        assert result["A"].tolist() == [1, 2]

    def test_drop_duplicates_false(self):
        """Test keeping duplicates when drop_duplicates=False."""
        df = pd.DataFrame({"A": [1, 1, 2], "B": [3, 3, 4]})

        result = get_subset(df, ["A", "B"], drop_duplicates=False)

        assert len(result) == 3

    def test_functional_dependency_check_passes(self):
        """Test functional dependency check with valid data."""
        df = pd.DataFrame({"key": [1, 1, 2, 2], "value": [10, 10, 20, 20]})

        result = get_subset(df, ["key", "value"], drop_duplicates=["key"], fd_check=True)

        assert len(result) == 2

    def test_functional_dependency_check_fails(self):
        """Test functional dependency check with invalid data."""
        df = pd.DataFrame({"key": [1, 1, 2], "value": [10, 20, 30]})

        with pytest.raises(ValueError, match="inconsistent"):
            get_subset(df, ["key", "value"], drop_duplicates=["key"], fd_check=True)

    def test_complex_workflow(self):
        """Test complex workflow with all features."""
        df = pd.DataFrame({"site_name": ["Site A", "Site A", "Site B"], "location": ["Loc1", "Loc1", "Loc2"], "value": [100, 100, 200]})

        result = get_subset(
            df,
            ["site_name", "location"],
            extra_columns={"renamed_val": "value", "type": "survey"},
            drop_duplicates=["site_name", "location"],
        )

        assert len(result) == 2
        assert set(result.columns) == {"site_name", "location", "renamed_val", "type", "value"}
        assert result["renamed_val"].tolist() == [100, 200]
        assert result["type"].tolist() == ["survey", "survey"]

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame({"A": [], "B": []})

        result = get_subset(df, ["A"], extra_columns={"C": 1})

        assert len(result) == 0
        assert "A" in result.columns
        assert "C" in result.columns

    def test_single_row(self):
        """Test with single row DataFrame."""
        df = pd.DataFrame({"A": [1], "B": [2]})

        result = get_subset(df, ["A"], extra_columns={"renamed": "B"})

        assert len(result) == 1
        assert result["renamed"].tolist() == [2]

    def test_preserves_data_types(self):
        """Test that data types are preserved."""
        df = pd.DataFrame({"int_col": [1, 2], "float_col": [1.5, 2.5], "str_col": ["a", "b"]})

        result = get_subset(df, ["int_col", "float_col", "str_col"])

        assert result["int_col"].dtype == df["int_col"].dtype
        assert result["float_col"].dtype == df["float_col"].dtype
        assert result["str_col"].dtype == df["str_col"].dtype

    def test_column_order_preserved(self):
        """Test that column order matches specification."""
        df = pd.DataFrame({"C": [1, 2], "B": [3, 4], "A": [5, 6]})

        result = get_subset(df, ["A", "B", "C"])

        # Order should be A, B, C as requested (not source order)
        assert list(result.columns) == ["A", "B", "C"]

    def test_extra_columns_empty_dict(self):
        """Test that empty extra_columns dict works."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={})

        assert list(result.columns) == ["A"]

    def test_rename_to_same_name(self):
        """Test renaming column to itself (no-op)."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"B": "B"})

        assert list(result.columns) == ["A", "B"]
        assert result["B"].tolist() == [3, 4]

    def test_boolean_column_values(self):
        """Test with boolean column values."""
        df = pd.DataFrame({"A": [True, False, True], "B": [1, 2, 3]})

        result = get_subset(df, ["A", "B"], drop_duplicates=False)

        assert result["A"].tolist() == [True, False, True]

    def test_with_null_values(self):
        """Test handling of null values."""
        df = pd.DataFrame({"A": [1, None, 3], "B": [4, 5, None]})

        result = get_subset(df, ["A", "B"])

        assert pd.isna(result.iloc[1]["A"])
        assert pd.isna(result.iloc[2]["B"])


class TestRenameLastOccurrence:
    """Test suite for _rename_last_occurence helper function."""

    def test_basic_rename_single_occurrence(self):
        """Test renaming a column that appears once."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = _rename_last_occurence(data, {"B": "B_renamed"})
        expected = ["A", "B_renamed", "C"]
        assert result == expected

    def test_rename_last_when_multiple_occurrences(self):
        """Test that only the LAST occurrence is renamed when column appears multiple times."""
        # Create DataFrame with duplicate column names
        data = pd.DataFrame([[1, 2, 3, 4]], columns=["A", "B", "A", "C"])
        result = _rename_last_occurence(data, {"A": "A_last"})
        expected = ["A", "B", "A_last", "C"]
        assert result == expected

    def test_skip_when_source_not_in_columns(self):
        """Test that rename is skipped when source column doesn't exist."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = _rename_last_occurence(data, {"C": "C_renamed"})
        expected = ["A", "B"]
        assert result == expected

    def test_skip_when_target_already_exists(self):
        """Test that rename is skipped when target name already exists in columns."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = _rename_last_occurence(data, {"A": "C"})
        expected = ["A", "B", "C"]
        assert result == expected

    def test_multiple_renames_in_single_call(self):
        """Test renaming multiple columns in a single call."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6], "D": [7, 8]})
        result = _rename_last_occurence(data, {"A": "A_new", "C": "C_new"})
        expected = ["A_new", "B", "C_new", "D"]
        assert result == expected

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        data = pd.DataFrame()
        result = _rename_last_occurence(data, {"A": "A_renamed"})
        expected = []
        assert result == expected

    def test_empty_rename_map(self):
        """Test with empty rename map."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = _rename_last_occurence(data, {})
        expected = ["A", "B"]
        assert result == expected

    def test_rename_with_duplicate_occurrences_multiple_sources(self):
        """Test renaming when multiple columns have duplicates."""
        # DataFrame with multiple duplicate columns
        data = pd.DataFrame([[1, 2, 3, 4, 5, 6]], columns=["A", "B", "A", "C", "B", "D"])
        result = _rename_last_occurence(data, {"A": "A_last", "B": "B_last"})
        expected = ["A", "B", "A_last", "C", "B_last", "D"]
        assert result == expected

    def test_rename_does_not_modify_dataframe(self):
        """Test that the original DataFrame columns are not modified."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        original_columns = data.columns.tolist()
        _rename_last_occurence(data, {"B": "B_renamed"})
        assert data.columns.tolist() == original_columns

    def test_rename_first_occurrence_not_affected(self):
        """Test that earlier occurrences of duplicate columns remain unchanged."""
        data = pd.DataFrame([[1, 2, 3, 4, 5]], columns=["A", "B", "A", "A", "C"])
        result = _rename_last_occurence(data, {"A": "A_final"})
        expected = ["A", "B", "A", "A_final", "C"]
        assert result == expected

    def test_rename_with_special_characters_in_names(self):
        """Test renaming columns with special characters."""
        data = pd.DataFrame({"col.1": [1, 2], "col-2": [3, 4], "col_3": [5, 6]})
        result = _rename_last_occurence(data, {"col.1": "column_1", "col-2": "column-2"})
        expected = ["column_1", "column-2", "col_3"]
        assert result == expected


class TestTranslate:
    """Tests for translate function."""

    def test_translate_with_valid_translations(self):
        """Test translating column names with valid translation configuration."""
        # Mock translation config
        fields_metadata: list[dict[str, str]] = [
            {"arbodat_field": "Ort", "english_column_name": "location"},
            {"arbodat_field": "Datum", "english_column_name": "date"},
            {"arbodat_field": "Art", "english_column_name": "species"},
        ]
        translations: dict[str, str] = extract_translation_map(fields_metadata=fields_metadata)

        # Create test data
        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin", "Munich"], "Datum": ["2020-01-01", "2020-01-02"]}),
            "species": pd.DataFrame({"Art": ["Oak", "Pine"], "Count": [5, 10]}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map=translations)

        # Verify translations
        assert "location" in result["sites"].columns
        assert "date" in result["sites"].columns
        assert "Ort" not in result["sites"].columns
        assert "Datum" not in result["sites"].columns

        assert "species" in result["species"].columns
        assert "Count" in result["species"].columns
        assert "Art" not in result["species"].columns

    def test_translate_preserves_untranslated_columns(self):
        """Test that columns without translations are fields_metadata."""
        translations: list[dict[str, str]] = [
            {"arbodat_field": "Ort", "english_column_name": "location"},
        ]
        translations_map: dict[str, str] = extract_translation_map(fields_metadata=translations)

        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin"], "untranslated_col": ["value"]}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map=translations_map)

        assert "location" in result["sites"].columns
        assert "untranslated_col" in result["sites"].columns

    def test_translate_with_no_translations_config(self):
        """Test translate when no translation configuration is available."""

        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin"], "Datum": ["2020-01-01"]}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map=None)

        # Columns should remain unchanged
        assert "Ort" in result["sites"].columns
        assert "Datum" in result["sites"].columns

    def test_translate_with_empty_translations(self):
        """Test translate with empty translations list."""

        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin"]}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map={})

        # Columns should remain unchanged
        assert "Ort" in result["sites"].columns

    def test_translate_with_missing_required_fields(self):
        """Test translate when translation config is missing required fields."""
        # Translation missing 'english_column_name' field
        fields_metadata: list[dict[str, str]] = [
            {"arbodat_field": "Ort", "wrong_field": "location"},
        ]
        translations: dict[str, str] = extract_translation_map(fields_metadata=fields_metadata)

        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin"]}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map=translations)

        # Should skip translation and keep original columns
        assert "Ort" in result["sites"].columns

    def test_translate_with_duplicate_target_names(self):
        """Test translate when target column name already exists."""
        fields_metadata: list[dict[str, str]] = [
            {"arbodat_field": "Ort", "english_column_name": "location"},
        ]
        translations: dict[str, str] = extract_translation_map(fields_metadata=fields_metadata)

        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin"], "location": ["existing"]}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map=translations)
        # Should not translate 'Ort' because 'location' already exists
        assert "Ort" in result["sites"].columns
        assert "location" in result["sites"].columns
        assert result["sites"]["location"].tolist() == ["existing"]

    def test_translate_multiple_tables(self):
        """Test translating multiple tables."""
        fields_metadata: list[dict[str, str]] = [
            {"arbodat_field": "Ort", "english_column_name": "location"},
            {"arbodat_field": "Art", "english_column_name": "species"},
            {"arbodat_field": "Anzahl", "english_column_name": "count"},
        ]
        translations: dict[str, str] = extract_translation_map(fields_metadata=fields_metadata)

        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin"], "id": [1]}),
            "species": pd.DataFrame({"Art": ["Oak"], "Anzahl": [5]}),
            "other": pd.DataFrame({"name": ["test"]}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map=translations)

        # Check all tables translated correctly
        assert "location" in result["sites"].columns
        assert "id" in result["sites"].columns
        assert "species" in result["species"].columns
        assert "count" in result["species"].columns
        assert "name" in result["other"].columns

    def test_translate_with_custom_field_names(self):
        """Test translate with custom from_field and to_field parameters."""
        fields_metadata: list[dict[str, str]] = [
            {"german": "Ort", "swedish": "plats"},
            {"german": "Art", "swedish": "art"},
        ]
        translations: dict[str, str] = extract_translation_map(fields_metadata=fields_metadata, from_field="german", to_field="swedish")

        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin"], "Art": ["Oak"]}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map=translations)

        assert "plats" in result["sites"].columns
        assert "art" in result["sites"].columns
        assert "Ort" not in result["sites"].columns
        assert "Art" not in result["sites"].columns

    def test_translate_preserves_data_values(self):
        """Test that translate only changes column names, not data values."""
        fields_metadata: list[dict[str, str]] = [
            {"arbodat_field": "Ort", "english_column_name": "location"},
            {"arbodat_field": "Wert", "english_column_name": "value"},
        ]
        translations: dict[str, str] = extract_translation_map(fields_metadata=fields_metadata)

        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin", "Munich"], "Wert": [10, 20]}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map=translations)

        # Verify data values are preserved
        assert result["sites"]["location"].tolist() == ["Berlin", "Munich"]
        assert result["sites"]["value"].tolist() == [10, 20]

    def test_translate_empty_dataframe(self):
        """Test translate with empty DataFrame."""
        fields_metadata: list[dict[str, str]] = [
            {"arbodat_field": "Ort", "english_column_name": "location"},
        ]
        translations: dict[str, str] = extract_translation_map(fields_metadata=fields_metadata)

        data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": [], "Datum": []}),
        }

        result: dict[str, pd.DataFrame] = translate(data, translations_map=translations)

        assert "location" in result["sites"].columns
        assert "Datum" in result["sites"].columns
        assert len(result["sites"]) == 0

    def test_translate_returns_modified_dict(self):
        """Test that translate returns the modified data dictionary."""
        fields_metadata: list[dict[str, str]] = [
            {"arbodat_field": "Ort", "english_column_name": "location"},
        ]
        translations: dict[str, str] = extract_translation_map(fields_metadata=fields_metadata)

        original_data: dict[str, pd.DataFrame] = {
            "sites": pd.DataFrame({"Ort": ["Berlin"]}),
        }

        result: dict[str, pd.DataFrame] = translate(original_data, translations_map=translations)

        # Verify it returns a dict
        assert isinstance(result, dict)
        assert "sites" in result
        assert isinstance(result["sites"], pd.DataFrame)
