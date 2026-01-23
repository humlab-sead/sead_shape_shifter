"""Unit tests for arbodat utility functions."""

import pandas as pd

from src.transforms.translate import extract_translation_map, translate

class TestTranslate:
    """Tests for translate function."""

    def test_extract_translation_map_missing_keys_warns(self):
        """Missing required keys yields empty translation map."""
        # keys missing -> empty result
        assert extract_translation_map([{"wrong": "v"}]) == {}

        # valid mapping
        fields = [{"arbodat_field": "Ort", "english_column_name": "location"}]
        assert extract_translation_map(fields) == {"Ort": "location"}

    def test_translate_skips_conflicting_columns(self):
        """Translation should avoid clobbering existing columns."""
        df = pd.DataFrame({"Ort": ["A"], "location": ["orig"]})
        data = {"entity": df}
        translated = translate(data, {"Ort": "location"})
        assert list(translated["entity"].columns) == ["Ort", "location"]

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
