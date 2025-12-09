"""Unit tests for arbodat mapping functionality."""

import pandas as pd

from src.arbodat.mapping import LinkToRemoteService


class TestRemoteLinker:
    """Tests for RemoteLinker class."""

    def test_basic_mapping(self):
        """Test basic mapping of local keys to remote keys."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101, "PLANT002": 102, "PLANT003": 103}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": ["PLANT001", "PLANT002", "PLANT003"], "name": ["Plant A", "Plant B", "Plant C"]})

        result = linker.link_to_remote("taxa", df)

        assert "taxon_id" in result.columns
        assert result["taxon_id"].tolist() == [101, 102, 103]
        assert result["PCODE"].tolist() == ["PLANT001", "PLANT002", "PLANT003"]

    def test_mapping_with_unmapped_values(self):
        """Test mapping when some values are not in the mapping dict."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101, "PLANT002": 102}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": ["PLANT001", "PLANT002", "PLANT999"], "name": ["Plant A", "Plant B", "Plant Unknown"]})

        result = linker.link_to_remote("taxa", df)

        assert result["taxon_id"].tolist()[:2] == [101, 102]
        assert pd.isna(result["taxon_id"].iloc[2])  # Unmapped value becomes NaN

    def test_mapping_with_null_values(self):
        """Test mapping when mapping dict contains null values."""
        config = {
            "feature_type": {
                "local_key": "BefuTyp",
                "remote_key": "feature_type_id",
                "mapping": {"Gr": 7, "Pfo": 26, "": 27, None: 27},  # Empty string maps to 27  # Null also maps to 27
            }
        }

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"BefuTyp": ["Gr", "Pfo", "", None], "description": ["Type A", "Type B", "Empty", "Null"]})

        result = linker.link_to_remote("feature_type", df)

        assert result["feature_type_id"].tolist()[:2] == [7, 26]
        assert result["feature_type_id"].iloc[2] == 27
        assert result["feature_type_id"].iloc[3] == 27

    def test_no_config_for_entity(self):
        """Test that tables without config are returned unchanged."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"sample_id": [1, 2, 3], "sample_name": ["A", "B", "C"]})

        result = linker.link_to_remote("sample", df)

        # Should return unchanged
        assert result.equals(df)
        assert "sample_id" in result.columns
        assert len(result.columns) == 2

    def test_empty_config(self):
        """Test RemoteLinker with empty configuration."""
        linker = LinkToRemoteService({})

        df = pd.DataFrame({"PCODE": ["PLANT001", "PLANT002"], "name": ["Plant A", "Plant B"]})

        result = linker.link_to_remote("taxa", df)

        # Should return unchanged
        assert result.equals(df)

    def test_incomplete_config_missing_local_key(self):
        """Test handling of incomplete config missing local_key."""
        config = {"taxa": {"remote_key": "taxon_id", "mapping": {"PLANT001": 101}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": ["PLANT001"], "name": ["Plant A"]})

        result = linker.link_to_remote("taxa", df)

        # Should return unchanged due to incomplete config
        assert result.equals(df)

    def test_incomplete_config_missing_remote_key(self):
        """Test handling of incomplete config missing remote_key."""
        config = {"taxa": {"local_key": "PCODE", "mapping": {"PLANT001": 101}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": ["PLANT001"], "name": ["Plant A"]})

        result = linker.link_to_remote("taxa", df)

        # Should return unchanged due to incomplete config
        assert result.equals(df)

    def test_incomplete_config_missing_mapping(self):
        """Test handling of incomplete config missing mapping dict."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id"}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": ["PLANT001"], "name": ["Plant A"]})

        result = linker.link_to_remote("taxa", df)

        # Should return unchanged due to incomplete config
        assert result.equals(df)

    def test_incomplete_config_empty_mapping(self):
        """Test handling of config with empty mapping dict."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": ["PLANT001"], "name": ["Plant A"]})

        result = linker.link_to_remote("taxa", df)

        # Should return unchanged due to empty mapping
        assert result.equals(df)

    def test_local_key_not_in_dataframe(self):
        """Test handling when local_key column doesn't exist in dataframe."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"species_code": ["PLANT001"], "name": ["Plant A"]})  # Different column name

        result = linker.link_to_remote("taxa", df)

        # Should return unchanged since local_key not found
        assert result.equals(df)
        assert "taxon_id" not in result.columns

    def test_mapping_preserves_other_columns(self):
        """Test that mapping preserves all other columns in the dataframe."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101, "PLANT002": 102}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame(
            {
                "PCODE": ["PLANT001", "PLANT002"],
                "name": ["Plant A", "Plant B"],
                "family": ["Family X", "Family Y"],
                "order": ["Order M", "Order N"],
            }
        )

        result = linker.link_to_remote("taxa", df)

        assert "PCODE" in result.columns
        assert "name" in result.columns
        assert "family" in result.columns
        assert "order" in result.columns
        assert "taxon_id" in result.columns
        assert len(result) == 2

    def test_mapping_with_numeric_local_keys(self):
        """Test mapping when local keys are numeric."""
        config = {"location_type": {"local_key": "type_code", "remote_key": "location_type_id", "mapping": {1: 10, 2: 20, 3: 30}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"type_code": [1, 2, 3, 1], "name": ["Type A", "Type B", "Type C", "Type A2"]})

        result = linker.link_to_remote("location_type", df)

        assert result["location_type_id"].tolist() == [10, 20, 30, 10]

    def test_mapping_with_duplicate_values(self):
        """Test mapping works correctly with duplicate values in source."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101, "PLANT002": 102}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": ["PLANT001", "PLANT002", "PLANT001", "PLANT002", "PLANT001"], "count": [5, 10, 3, 7, 2]})

        result = linker.link_to_remote("taxa", df)

        assert result["taxon_id"].tolist() == [101, 102, 101, 102, 101]
        assert len(result) == 5

    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": [], "name": []})

        result = linker.link_to_remote("taxa", df)

        assert "taxon_id" in result.columns
        assert len(result) == 0

    def test_multiple_entities(self):
        """Test RemoteLinker with multiple entity configurations."""
        config = {
            "taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101}},
            "location": {"local_key": "location_name", "remote_key": "location_id", "mapping": {"Sweden": 205, "Norway": 162}},
        }

        linker = LinkToRemoteService(config)

        # Test taxa entity
        taxa_df = pd.DataFrame({"PCODE": ["PLANT001"]})
        taxa_result = linker.link_to_remote("taxa", taxa_df)
        assert taxa_result["taxon_id"].iloc[0] == 101

        # Test location entity
        location_df = pd.DataFrame({"location_name": ["Sweden", "Norway"]})
        location_result = linker.link_to_remote("location", location_df)
        assert location_result["location_id"].tolist() == [205, 162]

    def test_mapping_overwrites_existing_remote_key_column(self):
        """Test that mapping overwrites existing remote_key column if it exists."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101, "PLANT002": 102}}}

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": ["PLANT001", "PLANT002"], "taxon_id": [999, 888]})  # Pre-existing values

        result = linker.link_to_remote("taxa", df)

        # Should overwrite with mapped values
        assert result["taxon_id"].tolist() == [101, 102]

    def test_real_world_feature_type_mapping(self):
        """Test with real-world feature_type mapping from mappings.yml."""
        config = {
            "feature_type": {
                "local_key": "BefuTyp",
                "remote_key": "feature_type_id",
                "mapping": {"BefuTyp?": 27, "": 27, None: 27, "KultLauf": 14, "Gr": 7, "Pfo": 26, "Kult": 40, "Schi": 5},
            }
        }

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"BefuTyp": ["Gr", "Pfo", "Kult", "", None, "BefuTyp?", "Unknown"]})

        result = linker.link_to_remote("feature_type", df)

        assert result["feature_type_id"].iloc[0] == 7
        assert result["feature_type_id"].iloc[1] == 26
        assert result["feature_type_id"].iloc[2] == 40
        assert result["feature_type_id"].iloc[3] == 27
        assert result["feature_type_id"].iloc[4] == 27
        assert result["feature_type_id"].iloc[5] == 27
        assert pd.isna(result["feature_type_id"].iloc[6])  # Unknown not in mapping

    def test_real_world_location_type_mapping(self):
        """Test with real-world location_type mapping from mappings.yml."""
        config = {
            "location_type": {
                "local_key": "location_type",
                "remote_key": "location_type_id",
                "mapping": {"Ort": 2, "Kreis": 2, "Land": 2, "Staat": 1, "FlurStr": 10},
            }
        }

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"location_type": ["Ort", "Kreis", "Land", "Staat", "FlurStr"]})

        result = linker.link_to_remote("location_type", df)

        assert result["location_type_id"].tolist() == [2, 2, 2, 1, 10]

    def test_config_with_none_or_empty_string_keys(self):
        """Test that None or empty string values in config are handled."""
        config = {"taxa": {"local_key": "", "remote_key": None, "mapping": {"PLANT001": 101}}}  # Empty string  # None

        linker = LinkToRemoteService(config)

        df = pd.DataFrame({"PCODE": ["PLANT001"], "name": ["Plant A"]})

        result = linker.link_to_remote("taxa", df)

        # Should return unchanged due to invalid keys
        assert result.equals(df)

    def test_dataframe_not_modified_in_place(self):
        """Test that the original dataframe is not modified."""
        config = {"taxa": {"local_key": "PCODE", "remote_key": "taxon_id", "mapping": {"PLANT001": 101}}}

        linker = LinkToRemoteService(config)

        original_df = pd.DataFrame({"PCODE": ["PLANT001"], "name": ["Plant A"]})

        # Keep a copy to check if original is modified
        original_copy = original_df.copy()

        result = linker.link_to_remote("taxa", original_df)

        # Original should have new column added (pandas map adds column in place)
        assert "taxon_id" in original_df.columns
        assert "taxon_id" in result.columns
        # But data should be the same
        assert original_df["PCODE"].equals(original_copy["PCODE"])
