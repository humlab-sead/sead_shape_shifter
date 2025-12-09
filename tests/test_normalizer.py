"""Unit tests for arbodat normalizer classes."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.config_model import TablesConfig
from src.configuration.setup import setup_config_store
from src.normalizer import ArbodatSurveyNormalizer, ProcessState


@pytest.fixture(scope="session", autouse=True)
def setup_config():
    """Initialize the config store before running tests."""
    config_file = "./input/arbodat.yml"
    asyncio.run(
        setup_config_store(
            config_file,
            env_prefix="SEAD_NORMALIZER",
            env_filename="./input/.env",
            db_opts_path=None,
        )
    )


class TestProcessState:
    """Tests for ProcessState class."""

    def test_initialization(self):
        """Test ProcessState initialization."""
        config = TablesConfig()
        # Mock the config to have some table names
        config.table_names = ["site", "sample", "taxa"]

        state = ProcessState(config=config)

        assert state.config == config
        assert state.unprocessed == {"site", "sample", "taxa"}
        assert state.processed_entities == set()

    def test_get_next_entity_no_dependencies(self):
        """Test getting next entity when no dependencies exist."""
        config = TablesConfig()
        config.table_names = ["site", "sample"]

        # Mock table configs with no dependencies
        with patch.object(config, "get_table") as mock_get_table:
            mock_table = Mock()
            mock_table.depends_on = set()
            mock_get_table.return_value = mock_table

            state = ProcessState(config=config)
            next_entity = state.get_next_entity_to_process()

            assert next_entity in ["site", "sample"]

    def test_get_next_entity_with_dependencies(self):
        """Test getting next entity respecting dependencies."""
        config = TablesConfig()
        config.table_names = ["site", "sample"]

        def mock_get_table(entity_name):
            mock_table = Mock()
            if entity_name == "sample":
                mock_table.depends_on = {"site"}
            else:
                mock_table.depends_on = set()
            return mock_table

        with patch.object(config, "get_table", side_effect=mock_get_table):
            state = ProcessState(config=config)

            # First entity should be 'site' since 'sample' depends on it
            next_entity = state.get_next_entity_to_process()
            assert next_entity == "site"

            # Mark site as processed
            state.discard("site")

            # Now 'sample' should be available
            next_entity = state.get_next_entity_to_process()
            assert next_entity == "sample"

    def test_get_next_entity_all_processed(self):
        """Test getting next entity when all are processed."""
        config = TablesConfig()
        config.table_names = ["site"]

        with patch.object(config, "get_table") as mock_get_table:
            mock_table = Mock()
            mock_table.depends_on = set()
            mock_get_table.return_value = mock_table

            state = ProcessState(config=config)
            state.discard("site")

            next_entity = state.get_next_entity_to_process()
            assert next_entity is None

    def test_get_unmet_dependencies(self):
        """Test getting unmet dependencies for an entity."""
        config = TablesConfig()
        config.table_names = ["site", "sample", "taxa"]

        def mock_get_table(entity_name):
            mock_table = Mock()
            if entity_name == "sample":
                mock_table.depends_on = {"site", "taxa"}
            else:
                mock_table.depends_on = set()
            return mock_table

        with patch.object(config, "get_table", side_effect=mock_get_table):
            state = ProcessState(config=config)

            unmet = state.get_unmet_dependencies("sample")
            assert unmet == {"site", "taxa"}

            # Mark site as processed
            state.discard("site")

            unmet = state.get_unmet_dependencies("sample")
            assert unmet == {"taxa"}

    def test_discard(self):
        """Test discarding (marking as processed) an entity."""
        config = TablesConfig()
        config.table_names = ["site", "sample"]

        state = ProcessState(config=config)
        assert "site" in state.unprocessed
        assert "site" not in state.processed_entities

        state.discard("site")

        assert "site" not in state.unprocessed
        assert "site" in state.processed_entities

    def test_get_all_unmet_dependencies(self):
        """Test getting all unmet dependencies."""
        config = TablesConfig()
        config.table_names = ["site", "sample", "feature"]

        def mock_get_table(entity_name):
            mock_table = Mock()
            if entity_name == "sample":
                mock_table.depends_on = {"site"}
            elif entity_name == "feature":
                mock_table.depends_on = {"site", "sample"}
            else:
                mock_table.depends_on = set()
            return mock_table

        with patch.object(config, "get_table", side_effect=mock_get_table):
            state = ProcessState(config=config)

            all_unmet = state.get_all_unmet_dependencies()

            assert "sample" in all_unmet
            assert all_unmet["sample"] == {"site"}
            assert "feature" in all_unmet
            assert all_unmet["feature"] == {"site", "sample"}
            assert "site" not in all_unmet  # Has no dependencies

    def test_processed_entities_property(self):
        """Test the processed_entities property."""
        config = TablesConfig()
        config.table_names = ["site", "sample", "taxa"]

        state = ProcessState(config=config)
        assert state.processed_entities == set()

        state.discard("site")
        assert state.processed_entities == {"site"}

        state.discard("sample")
        assert state.processed_entities == {"site", "sample"}


class TestArbodatSurveyNormalizer:
    """Tests for ArbodatSurveyNormalizer class."""

    def test_initialization(self):
        """Test ArbodatSurveyNormalizer initialization."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})

        normalizer = ArbodatSurveyNormalizer(df)

        assert "survey" in normalizer.table_store
        pd.testing.assert_frame_equal(normalizer.table_store["survey"], df)
        assert isinstance(normalizer.config, TablesConfig)
        assert isinstance(normalizer.state, ProcessState)

    def test_survey_property(self):
        """Test the survey property."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        normalizer = ArbodatSurveyNormalizer(df)

        pd.testing.assert_frame_equal(normalizer.survey, df)

    @pytest.mark.asyncio
    async def test_resolve_source_from_survey(self):
        """Test resolving source from survey DataFrame."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        normalizer = ArbodatSurveyNormalizer(df)

        table_cfg = Mock()
        table_cfg.is_fixed_data = False
        table_cfg.is_sql_data = False
        table_cfg.source = None

        result = await normalizer.resolve_source(table_cfg)

        pd.testing.assert_frame_equal(result, df)

    @pytest.mark.asyncio
    async def test_resolve_source_from_stored_data(self):
        """Test resolving source from previously stored data."""
        df = pd.DataFrame({"col1": [1, 2]})
        site_df = pd.DataFrame({"site_name": ["A", "B"]})

        normalizer = ArbodatSurveyNormalizer(df)
        normalizer.table_store["site"] = site_df

        table_cfg = Mock()
        table_cfg.is_fixed_data = False
        table_cfg.is_sql_data = False
        table_cfg.source = "site"

        result = await normalizer.resolve_source(table_cfg)

        pd.testing.assert_frame_equal(result, site_df)

    @pytest.mark.asyncio
    async def test_resolve_source_not_found(self):
        """Test resolving source that doesn't exist."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        table_cfg = Mock()
        table_cfg.is_fixed_data = False
        table_cfg.is_sql_data = False
        table_cfg.source = "nonexistent"

        with pytest.raises(ValueError, match="Source table 'nonexistent' not found"):
            await normalizer.resolve_source(table_cfg)

    @pytest.mark.asyncio
    async def test_resolve_source_fixed_data(self):
        """Test resolving fixed data source."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        table_cfg = Mock()
        table_cfg.is_fixed_data = True
        table_cfg.is_sql_data = False
        table_cfg.entity_name = "test_entity"

        fixed_df = pd.DataFrame({"fixed": [1, 2, 3]})

        with patch("src.normalizer.FixedLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load = AsyncMock(return_value=fixed_df)
            mock_loader_class.return_value = mock_loader

            result = await normalizer.resolve_source(table_cfg)

            pd.testing.assert_frame_equal(result, fixed_df)
            mock_loader.load.assert_called_once_with(entity_name="test_entity", table_cfg=table_cfg)

    @pytest.mark.asyncio
    async def test_resolve_source_sql_data(self):
        """Test resolving SQL data source."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)
        normalizer.config.data_sources = {
            "test_data_source": {
                "driver": "postgres",
                "options": {"host": "localhost", "port": 5432, "user": "test_user", "dbname": "test_db"},
            }
        }
        table_cfg = Mock()
        table_cfg.is_fixed_data = False
        table_cfg.is_sql_data = True
        table_cfg.data_source = "test_data_source"
        table_cfg.entity_name = "test_sql_entity"

        sql_df = pd.DataFrame({"sql_col": ["a", "b", "c"]})

        with patch("src.loaders.database_loaders.PostgresSqlLoader") as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load = AsyncMock(return_value=sql_df)
            mock_loader_class.return_value = mock_loader

            result: pd.DataFrame = await normalizer.resolve_source(table_cfg=table_cfg)

            pd.testing.assert_frame_equal(result, sql_df)
            mock_loader.load.assert_called_once_with(entity_name="test_sql_entity", table_cfg=table_cfg)

    def test_register(self):
        """Test registering a DataFrame."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        new_df = pd.DataFrame({"site_name": ["A", "B"]})
        result = normalizer.register("site", new_df)

        assert "site" in normalizer.table_store
        pd.testing.assert_frame_equal(normalizer.table_store["site"], new_df)
        pd.testing.assert_frame_equal(result, new_df)

    def test_load_from_file(self, tmp_path):
        """Test loading from CSV file."""
        # Create a test CSV file
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({"col1": ["a", "b"], "col2": ["c", "d"]})
        df.to_csv(csv_file, sep="\t", index=False)

        normalizer = ArbodatSurveyNormalizer.load(csv_file, sep="\t")

        assert "survey" in normalizer.table_store
        assert list(normalizer.survey.columns) == ["col1", "col2"]
        assert len(normalizer.survey) == 2

    def test_load_from_path_object(self, tmp_path):
        """Test loading from Path object."""
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({"col1": ["a", "b"], "col2": ["c", "d"]})
        df.to_csv(csv_file, sep=";", index=False)

        normalizer = ArbodatSurveyNormalizer.load(Path(csv_file), sep=";")

        assert len(normalizer.survey) == 2

    def test_translate(self):
        """Test translating column names."""
        df = pd.DataFrame({"Ort": ["Berlin"], "Datum": ["2020-01-01"]})
        normalizer = ArbodatSurveyNormalizer(df)
        normalizer.table_store["site"] = pd.DataFrame({"Ort": ["Munich"]})

        translations_map = {"Ort": "location", "Datum": "date"}

        with patch("src.normalizer.translate") as mock_translate:
            mock_translate.return_value = {
                "survey": pd.DataFrame({"location": ["Berlin"], "date": ["2020-01-01"]}),
                "site": pd.DataFrame({"location": ["Munich"]}),
            }

            normalizer.translate(translations_map=translations_map)

            # Check that translate was called (without comparing DataFrames directly)
            assert mock_translate.call_count == 1
            call_args = mock_translate.call_args
            assert call_args.kwargs.get("translations_map") == translations_map
            assert list(normalizer.table_store["survey"].columns) == ["location", "date"]
            assert list(normalizer.table_store["site"].columns) == ["location"]

    def test_drop_foreign_key_columns(self):
        """Test dropping foreign key columns."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        # Add a table with FK columns
        site_df = pd.DataFrame({"site_id": [1, 2], "location_id": [10, 20], "name": ["A", "B"]})
        normalizer.table_store["site"] = site_df

        # Mock config
        mock_table_cfg = Mock()
        mock_table_cfg.drop_fk_columns = Mock(return_value=pd.DataFrame({"site_id": [1, 2], "name": ["A", "B"]}))

        with patch.object(normalizer.config, "table_names", ["site"]):
            with patch.object(normalizer.config, "get_table", return_value=mock_table_cfg):
                normalizer.drop_foreign_key_columns()

                mock_table_cfg.drop_fk_columns.assert_called_once()
                assert "location_id" not in normalizer.table_store["site"].columns

    def test_add_system_id_columns(self):
        """Test adding system_id columns."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        site_df = pd.DataFrame({"site_id": [1, 2], "name": ["A", "B"]})
        normalizer.table_store["site"] = site_df

        # Mock config
        mock_table_cfg = Mock()
        modified_df = pd.DataFrame({"system_id": [1, 2], "name": ["A", "B"]})
        mock_table_cfg.add_system_id_column = Mock(return_value=modified_df)

        with patch.object(normalizer.config, "table_names", ["site"]):
            with patch.object(normalizer.config, "get_table", return_value=mock_table_cfg):
                normalizer.add_system_id_columns()

                mock_table_cfg.add_system_id_column.assert_called_once()
                assert "system_id" in normalizer.table_store["site"].columns

    def test_move_keys_to_front(self):
        """Test moving key columns to front."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        site_df = pd.DataFrame({"name": ["A", "B"], "site_id": [1, 2], "location": ["X", "Y"]})
        normalizer.table_store["site"] = site_df

        # Mock config to reorder columns
        reordered_df = pd.DataFrame({"site_id": [1, 2], "name": ["A", "B"], "location": ["X", "Y"]})

        with patch.object(normalizer.config, "table_names", ["site"]):
            with patch.object(normalizer.config, "reorder_columns", return_value=reordered_df):
                normalizer.move_keys_to_front()

                # Verify site_id is first column
                assert normalizer.table_store["site"].columns[0] == "site_id"

    def test_unnest_entity(self):
        """Test unnesting a single entity."""
        survey = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(survey)

        site_df = pd.DataFrame({"site_id": [1], "Ort": ["Berlin"], "Kreis": ["Mitte"]})
        normalizer.table_store["site"] = site_df

        mock_table_cfg = Mock()
        mock_table_cfg.unnest = True
        mock_table_cfg.surrogate_id = None

        unnested_df = pd.DataFrame({"site_id": [1, 1], "location_type": ["Ort", "Kreis"], "location_name": ["Berlin", "Mitte"]})

        with patch.object(normalizer.config, "get_table", return_value=mock_table_cfg):
            with patch("src.normalizer.unnest", return_value=unnested_df):
                result = normalizer.unnest_entity(entity="site")

                pd.testing.assert_frame_equal(result, unnested_df)
                assert len(normalizer.table_store["site"]) == 2

    def test_unnest_entity_no_unnest_config(self):
        """Test unnesting when no unnest configuration exists."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        site_df = pd.DataFrame({"site_id": [1], "name": ["A"]})
        normalizer.table_store["site"] = site_df

        mock_table_cfg = Mock()
        mock_table_cfg.unnest = None

        with patch.object(normalizer.config, "get_table", return_value=mock_table_cfg):
            result = normalizer.unnest_entity(entity="site")

            # Should return unchanged
            pd.testing.assert_frame_equal(result, site_df)

    def test_store_xlsx(self):
        """Test storing data as XLSX."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        mock_dispatcher = Mock()
        mock_dispatcher.dispatch = Mock()

        with patch("src.normalizer.Dispatchers.get", return_value=lambda: mock_dispatcher):
            normalizer.store(target="output.xlsx", mode="xlsx")

            mock_dispatcher.dispatch.assert_called_once_with(target="output.xlsx", data=normalizer.table_store)

    def test_store_csv(self):
        """Test storing data as CSV."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        mock_dispatcher = Mock()
        mock_dispatcher.dispatch = Mock()

        with patch("src.normalizer.Dispatchers.get", return_value=lambda: mock_dispatcher):
            normalizer.store(target="output_dir", mode="csv")

            mock_dispatcher.dispatch.assert_called_once_with(target="output_dir", data=normalizer.table_store)

    def test_store_unsupported_mode(self):
        """Test storing with unsupported mode."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        with patch("src.normalizer.Dispatchers.get", return_value=None):
            with pytest.raises(ValueError, match="Unsupported dispatch mode: invalid"):
                normalizer.store(target="output", mode="invalid")  # type: ignore

    def test_link_calls_link_entity(self):
        """Test that link() calls link_entity for all processed entities."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        # Modify the state to simulate processed entities
        # processed_entities is computed as (table_names - unprocessed)
        # So we need to clear unprocessed and set table_names
        normalizer.state.config.table_names = ["site", "sample"]
        normalizer.state.unprocessed = set()  # Everything processed

        with patch("src.normalizer.link_entity") as mock_link:
            normalizer.link()

            # Should be called for each processed entity
            assert mock_link.call_count == 2
            call_args_list = [call[1] for call in mock_link.call_args_list]
            entity_names = [args["entity_name"] for args in call_args_list]
            assert set(entity_names) == {"site", "sample"}

    @pytest.mark.asyncio
    async def test_normalize_with_circular_dependency(self):
        """Test that normalize raises error for circular dependencies."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        normalizer.config.table_names = ["site", "sample"]

        # Create circular dependency
        def mock_get_table(entity_name):
            mock_cfg = Mock()
            if entity_name == "site":
                mock_cfg.depends_on = {"sample"}
            else:
                mock_cfg.depends_on = {"site"}
            return mock_cfg

        with patch.object(normalizer.config, "get_table", side_effect=mock_get_table):
            with pytest.raises(ValueError, match="Circular or unresolved dependencies"):
                await normalizer.normalize()

    def test_unnest_all(self):
        """Test unnesting all entities."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ArbodatSurveyNormalizer(df)

        site_df = pd.DataFrame({"site_id": [1], "Ort": ["Berlin"]})
        sample_df = pd.DataFrame({"sample_id": [1], "Type": ["Soil"]})
        normalizer.table_store["site"] = site_df
        normalizer.table_store["sample"] = sample_df

        with patch.object(normalizer, "unnest_entity") as mock_unnest:
            mock_unnest.side_effect = lambda entity: normalizer.table_store[entity]

            normalizer.unnest_all()

            # Should be called for all entities including survey
            assert mock_unnest.call_count == 3
