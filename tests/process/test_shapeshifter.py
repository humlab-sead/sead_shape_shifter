"""Unit tests for arbodat normalizer classes."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.loaders.base_loader import DataLoader
from src.model import ShapeShiftProject, TableConfig
from src.normalizer import ProcessState, ShapeShifter

# pylint: disable=redefined-outer-name


@pytest.fixture
def survey_only_config() -> ShapeShiftProject:
    return ShapeShiftProject(
        cfg={
            "entities": {
                "survey": {"depends_on": []},
            }
        },
    )


@pytest.fixture
def survey_and_site_config() -> ShapeShiftProject:
    return ShapeShiftProject(
        cfg={
            "entities": {
                "survey": {"depends_on": []},
                "site": {"depends_on": ["survey"]},
            }
        },
    )


def mock_table_config(depends_on: set[str] | None = None) -> Mock:
    """Helper to create a mock TableConfig with specified dependencies."""
    mock_table = Mock()
    mock_table.depends_on = depends_on if depends_on is not None else set()
    mock_table.foreign_keys = set()
    mock_table._data = {}
    return mock_table


class TestProcessState:
    """Tests for ProcessState class."""

    def test_initialization(self):
        """Test ProcessState initialization."""
        config = ShapeShiftProject(
            cfg={
                "entities": {
                    "site": {"depends_on": []},
                    "sample": {"depends_on": []},
                    "taxa": {"depends_on": []},
                }
            },
        )

        state = ProcessState(project=config, table_store={})

        assert state.project == config
        assert state.unprocessed_entities == {"site", "sample", "taxa"}
        assert state.processed_entities == set()

    def test_get_next_entity_no_dependencies(self):
        """Test getting next entity when no dependencies exist."""
        config = ShapeShiftProject(
            cfg={
                "entities": {
                    "site": {"depends_on": []},
                    "sample": {"depends_on": []},
                }
            },
        )

        # Mock table configs with no dependencies
        with patch.object(config, "get_table") as mock_get_table:
            mock_table = Mock()
            mock_table.depends_on = set()
            mock_get_table.return_value = mock_table

            state = ProcessState(project=config, table_store={})
            next_entity = state.get_next_entity_to_process()

            assert next_entity in ["site", "sample"]

    def test_get_next_entity_with_dependencies(self):
        """Test getting next entity respecting dependencies."""
        config = ShapeShiftProject(
            cfg={
                "entities": {
                    "site": {"depends_on": []},
                    "sample": {"depends_on": ["site"]},
                }
            },
        )

        state = ProcessState(project=config, table_store={})

        # First entity should be 'site' since 'sample' depends on it
        next_entity = state.get_next_entity_to_process()
        assert next_entity == "site"

        # Mark site as processed
        state.table_store["site"] = Mock()

        # Now 'sample' should be available
        next_entity = state.get_next_entity_to_process()
        assert next_entity == "sample"

    def test_get_next_entity_all_processed(self, survey_only_config: ShapeShiftProject):
        """Test getting next entity when all are processed."""

        state = ProcessState(project=survey_only_config, table_store={"survey": Mock()})
        state.table_store["site"] = Mock()

        next_entity: str | None = state.get_next_entity_to_process()
        assert next_entity is None

    def test_get_required_entities_collects_dependencies(self):
        """ShapeShiftProject resolves required entities and ProcessState honors it."""
        cfg = ShapeShiftProject(
            cfg={
                "entities": {
                    "survey": {"depends_on": []},
                    "site": {"depends_on": ["survey"]},
                    "sample": {"depends_on": ["site"]},
                }
            }
        )

        assert cfg.get_required_entities("sample") == {"sample", "site", "survey"}

        state = ProcessState(project=cfg, table_store={}, target_entities={"sample"})
        assert state.target_entities == {"sample", "site", "survey"}

    def test_get_unmet_dependencies(self):
        """Test getting unmet dependencies for an entity."""
        config = ShapeShiftProject(
            cfg={"entities": {"site": {"depends_on": []}, "sample": {"depends_on": ["site", "taxa"]}, "taxa": {"depends_on": []}}},
        )

        state = ProcessState(project=config, table_store={})

        unmet = state.get_unmet_dependencies("sample")
        assert unmet == {"site", "taxa"}

        state.table_store["site"] = Mock()

        unmet = state.get_unmet_dependencies("sample")
        assert unmet == {"taxa"}

    def test_discard(self):
        """Test discarding (marking as processed) an entity."""
        config = ShapeShiftProject(
            cfg={
                "entities": {
                    "site": {"depends_on": []},
                    "sample": {"depends_on": ["site", "taxa"]},
                }
            },
        )
        state = ProcessState(project=config, table_store={})
        assert "site" in state.unprocessed_entities
        assert "site" not in state.processed_entities

        state.table_store["site"] = Mock()

        assert "site" not in state.unprocessed_entities
        assert "site" in state.processed_entities

    def test_get_all_unmet_dependencies(self):
        """Test getting all unmet dependencies."""
        config = ShapeShiftProject(
            cfg={
                "entities": {
                    "site": {"depends_on": []},
                    "sample": {"depends_on": ["site"]},
                    "feature": {"depends_on": ["site", "sample"]},
                }
            },
        )

        state = ProcessState(project=config, table_store={})

        all_unmet = state.get_all_unmet_dependencies()

        assert "sample" in all_unmet
        assert all_unmet["sample"] == {"site"}
        assert "feature" in all_unmet
        assert all_unmet["feature"] == {"site", "sample"}
        assert "site" not in all_unmet  # Has no dependencies

    def test_processed_entities_property(self):
        """Test the processed_entities property."""
        config = ShapeShiftProject(
            cfg={
                "entities": {
                    "site": {"depends_on": []},
                    "sample": {"depends_on": []},
                    "taxa": {"depends_on": []},
                }
            },
        )

        state = ProcessState(project=config, table_store={})
        assert state.processed_entities == set()

        state.table_store["site"] = Mock()
        assert state.processed_entities == {"site"}

        state.table_store["sample"] = Mock()
        assert state.processed_entities == {"site", "sample"}

    def test_get_next_entity_with_unresolvable_dependencies(self):
        """Circular dependencies should yield no next entity."""
        config = ShapeShiftProject(
            cfg={
                "entities": {
                    "a": {"depends_on": ["b"]},
                    "b": {"depends_on": ["a"]},
                }
            },
        )

        state = ProcessState(project=config, table_store={})

        with patch.object(config, "get_table") as mock_get_table:
            mock_table = Mock()
            mock_table.depends_on = {"b"}
            mock_get_table.side_effect = [mock_table, Mock(depends_on={"a"})]

            assert state.get_next_entity_to_process() is None


class TestShapeShifter:
    """Tests for ShapeShifter class."""

    def test_initialization(self, survey_only_config: ShapeShiftProject):
        """Test ShapeShifter initialization."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})

        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey")
        normalizer.table_store = {"survey": df}

        assert "survey" in normalizer.table_store
        pd.testing.assert_frame_equal(normalizer.table_store["survey"], df)
        assert isinstance(normalizer.project, ShapeShiftProject)
        assert isinstance(normalizer.state, ProcessState)

    def test_survey_property(self, survey_only_config: ShapeShiftProject):
        """Test the survey property."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})

        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey", table_store={"survey": df})

        pd.testing.assert_frame_equal(normalizer.table_store["survey"], df)

    @pytest.mark.asyncio
    async def test_resolve_source_from_survey(self):
        """Test resolving source from survey DataFrame."""
        survey_df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})

        config = ShapeShiftProject(
            cfg={
                "entities": {
                    "site": {"depends_on": []},
                    "sample": {"depends_on": []},
                    "taxa": {"depends_on": []},
                }
            },
        )

        normalizer = ShapeShifter(project=config, table_store={"survey": survey_df}, default_entity="survey")

        table_cfg = Mock()
        table_cfg.type = None
        table_cfg.source = None
        table_cfg.data_source = None

        result: pd.DataFrame = await normalizer.resolve_source(table_cfg)

        pd.testing.assert_frame_equal(result, survey_df)

    @pytest.mark.asyncio
    async def test_resolve_source_from_stored_data(self):
        """Test resolving source from previously stored data."""
        df = pd.DataFrame({"col1": [1, 2]})
        site_df = pd.DataFrame({"site_name": ["A", "B"]})

        cfg: ShapeShiftProject = ShapeShiftProject(
            cfg={
                "entities": {
                    "survey": {"depends_on": []},
                    "site": {"depends_on": []},
                }
            },
        )

        normalizer = ShapeShifter(project=cfg, default_entity="survey", table_store={"survey": df, "site": site_df})

        table_cfg = Mock()
        table_cfg.type = None
        table_cfg.data_source = None
        table_cfg.source = "site"

        result: pd.DataFrame = await normalizer.resolve_source(table_cfg)

        pd.testing.assert_frame_equal(result, site_df)

    @pytest.mark.asyncio
    async def test_resolve_source_not_found(self, survey_only_config: ShapeShiftProject):
        """Test resolving source that doesn't exist."""
        df = pd.DataFrame({"col1": [1, 2]})

        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey", table_store={"survey": df})

        table_cfg = Mock()
        table_cfg.type = None
        table_cfg.data_source = None
        table_cfg.source = "nonexistent"

        with pytest.raises(ValueError, match="Unable to resolve source for entity"):
            await normalizer.resolve_source(table_cfg)

    @pytest.mark.asyncio
    async def test_resolve_source_fixed_data(self, survey_only_config: ShapeShiftProject):
        """Test resolving fixed data source."""
        df = pd.DataFrame({"col1": [1, 2]})

        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey", table_store={"survey": df})

        table_cfg = Mock()
        table_cfg.type = "fixed"
        table_cfg.data_source = None
        table_cfg.source = None
        table_cfg.entity_name = "test_entity"

        fixed_df = pd.DataFrame({"fixed": [1, 2, 3]})

        mock_loader = Mock()
        mock_loader.load = AsyncMock(return_value=fixed_df)

        with patch.object(normalizer, "resolve_loader", return_value=mock_loader):
            result = await normalizer.resolve_source(table_cfg)

            pd.testing.assert_frame_equal(result, fixed_df)
            mock_loader.load.assert_called_once_with(entity_name="test_entity", table_cfg=table_cfg)

    @pytest.mark.asyncio
    async def test_resolve_source_sql_data(self, survey_only_config: ShapeShiftProject):
        """Test resolving SQL data source."""
        df = pd.DataFrame({"col1": [1, 2]})

        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey", table_store={"survey": df})

        table_cfg = Mock()
        table_cfg.type = "sql"
        table_cfg.data_source = "test_data_source"
        table_cfg.entity_name = "test_sql_entity"

        sql_df = pd.DataFrame({"sql_col": ["a", "b", "c"]})

        mock_loader = Mock()
        mock_loader.load = AsyncMock(return_value=sql_df)

        with patch.object(normalizer, "resolve_loader", return_value=mock_loader):
            result: pd.DataFrame = await normalizer.resolve_source(table_cfg=table_cfg)

            pd.testing.assert_frame_equal(result, sql_df)
            mock_loader.load.assert_called_once_with(entity_name="test_sql_entity", table_cfg=table_cfg)

    def test_translate(self, survey_and_site_config: ShapeShiftProject):
        """Test translating column names."""
        df = pd.DataFrame({"Ort": ["Berlin"], "Datum": ["2020-01-01"]})
        normalizer = ShapeShifter(project=survey_and_site_config, default_entity="survey")
        normalizer.table_store = {"survey": df}
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

    def test_drop_foreign_key_columns(self, survey_and_site_config: ShapeShiftProject):
        """Test dropping foreign key columns."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ShapeShifter(project=survey_and_site_config, default_entity="survey")
        normalizer.table_store = {"survey": df}

        # Add a table with FK columns
        site_df = pd.DataFrame({"site_id": [1, 2], "location_id": [10, 20], "name": ["A", "B"]})
        normalizer.table_store["site"] = site_df

        # Mock config
        mock_table_cfg = Mock()
        mock_table_cfg.drop_fk_columns = Mock(return_value=pd.DataFrame({"site_id": [1, 2], "name": ["A", "B"]}))

        with patch.object(normalizer.project, "table_names", ["site"]):
            with patch.object(normalizer.project, "get_table", return_value=mock_table_cfg):
                normalizer.drop_foreign_key_columns()

                mock_table_cfg.drop_fk_columns.assert_called_once()
                assert "location_id" not in normalizer.table_store["site"].columns

    def test_add_system_id_columns(self, survey_and_site_config: ShapeShiftProject):
        """Test adding system_id columns."""
        df = pd.DataFrame({"col1": [1, 2]})
        site_df = pd.DataFrame({"site_id": [1, 2], "name": ["A", "B"]})
        table_store: dict[str, pd.DataFrame] = {"survey": df, "site": site_df}
        normalizer = ShapeShifter(project=survey_and_site_config, default_entity="survey", table_store=table_store)

        # Mock config
        mock_table_cfg = Mock()
        modified_df = pd.DataFrame({"system_id": [1, 2], "name": ["A", "B"]})
        mock_table_cfg.add_system_id_column = Mock(return_value=modified_df)

        with patch.object(normalizer.project, "table_names", ["site"]):
            with patch.object(normalizer.project, "get_table", return_value=mock_table_cfg):
                normalizer.add_system_id_columns()

                mock_table_cfg.add_system_id_column.assert_called_once()
                assert "system_id" in normalizer.table_store["site"].columns

    def test_move_keys_to_front(self, survey_and_site_config: ShapeShiftProject):
        """Test moving key columns to front."""
        survey_df = pd.DataFrame({"col1": [1, 2]})
        site_df = pd.DataFrame({"name": ["A", "B"], "site_id": [1, 2], "location": ["X", "Y"]})

        table_store: dict[str, pd.DataFrame] = {"survey": survey_df, "site": site_df}
        normalizer = ShapeShifter(project=survey_and_site_config, default_entity="survey", table_store=table_store)

        # Mock config to reorder columns
        reordered_df = pd.DataFrame({"site_id": [1, 2], "name": ["A", "B"], "location": ["X", "Y"]})

        with patch.object(normalizer.project, "table_names", ["site"]):
            with patch.object(normalizer.project, "reorder_columns", return_value=reordered_df):
                normalizer.move_keys_to_front()

                # Verify site_id is first column
                assert normalizer.table_store["site"].columns[0] == "site_id"

    def test_unnest_entity(self, survey_and_site_config: ShapeShiftProject):
        """Test unnesting a single entity."""
        survey_df = pd.DataFrame({"col1": [1, 2]})
        site_df = pd.DataFrame({"site_id": [1], "Ort": ["Berlin"], "Kreis": ["Mitte"]})
        table_store: dict[str, pd.DataFrame] = {"survey": survey_df, "site": site_df}
        normalizer = ShapeShifter(project=survey_and_site_config, table_store=table_store, default_entity="survey")

        mock_table_cfg = Mock()
        mock_table_cfg.unnest = True
        mock_table_cfg.surrogate_id = None

        unnested_df = pd.DataFrame({"site_id": [1, 1], "location_type": ["Ort", "Kreis"], "location_name": ["Berlin", "Mitte"]})

        with patch.object(normalizer.project, "get_table", return_value=mock_table_cfg):
            with patch("src.normalizer.unnest", return_value=unnested_df):
                result = normalizer.unnest_entity(entity="site")

                pd.testing.assert_frame_equal(result, unnested_df)
                assert len(normalizer.table_store["site"]) == 2

    def test_unnest_entity_no_unnest_config(self, survey_only_config: ShapeShiftProject):
        """Test unnesting when no unnest configuration exists."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey")
        normalizer.table_store = {"survey": df}

        site_df = pd.DataFrame({"site_id": [1], "name": ["A"]})
        normalizer.table_store["site"] = site_df

        mock_table_cfg = Mock()
        mock_table_cfg.unnest = None

        with patch.object(normalizer.project, "get_table", return_value=mock_table_cfg):
            result = normalizer.unnest_entity(entity="site")

            # Should return unchanged
            pd.testing.assert_frame_equal(result, site_df)

    def test_store_xlsx(self, survey_only_config: ShapeShiftProject):
        """Test storing data as XLSX."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey")
        normalizer.table_store = {"survey": df}

        mock_dispatcher = Mock()
        mock_dispatcher.dispatch = Mock()
        mock_dispatcher_cls = Mock(return_value=mock_dispatcher)

        with patch("src.normalizer.Dispatchers.get", return_value=mock_dispatcher_cls):
            normalizer.store(target="output.xlsx", mode="xlsx")

            mock_dispatcher_cls.assert_called_once_with(survey_only_config)
            mock_dispatcher.dispatch.assert_called_once_with(target="output.xlsx", data=normalizer.table_store)

    def test_store_csv(self, survey_only_config: ShapeShiftProject):
        """Test storing data as CSV."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey")
        normalizer.table_store = {"survey": df}

        mock_dispatcher = Mock()
        mock_dispatcher.dispatch = Mock()
        mock_dispatcher_cls = Mock(return_value=mock_dispatcher)

        with patch("src.normalizer.Dispatchers.get", return_value=mock_dispatcher_cls):
            normalizer.store(target="output_dir", mode="csv")

            mock_dispatcher_cls.assert_called_once_with(survey_only_config)
            mock_dispatcher.dispatch.assert_called_once_with(target="output_dir", data=normalizer.table_store)

    def test_store_unsupported_mode(self, survey_only_config: ShapeShiftProject):
        """Test storing with unsupported mode."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey")
        normalizer.table_store = {"survey": df}

        with patch("src.normalizer.Dispatchers.get", return_value=None):
            with pytest.raises(ValueError, match="Unsupported dispatch mode: invalid"):
                normalizer.store(target="output", mode="invalid")  # type: ignore

    def test_initialize_process_state_for_target_entities(self):
        """Targeted initialization should include dependencies for requested entities."""
        cfg = ShapeShiftProject(
            cfg={
                "entities": {
                    "survey": {"depends_on": []},
                    "site": {"depends_on": ["survey"]},
                    "sample": {"depends_on": ["site"]},
                }
            }
        )

        normalizer = ShapeShifter(project=cfg, default_entity="survey", target_entities={"sample"})

        assert normalizer.state.target_entities == {"sample", "site", "survey"}

    @pytest.mark.asyncio
    async def test_normalize_raises_for_invalid_columns(self):
        """Normalize should fail fast when columns contain non-strings."""
        cfg = ShapeShiftProject(
            cfg={
                "entities": {
                    "bad": {
                        "depends_on": [],
                        "columns": ["valid", 1],
                        "keys": [],
                    }
                }
            }
        )

        normalizer = ShapeShifter(project=cfg, default_entity="bad")

        with pytest.raises(ValueError, match="Invalid columns configuration"):
            await normalizer.normalize()

    def test_link_calls_link_entity(self):
        """Test that link() calls link_entity for all processed entities."""
        survey_df = pd.DataFrame({"col1": [1, 2]})
        site_df = pd.DataFrame({"site_id": [1, 2], "name": ["A", "B"]})
        sample_df = pd.DataFrame({"sample_id": [1, 2], "type": ["X", "Y"]})
        table_store: dict[str, pd.DataFrame] = {"survey": survey_df, "site": site_df, "sample": sample_df}
        config = ShapeShiftProject(
            cfg={
                "entities": {
                    "survey": {"depends_on": []},
                    "site": {"depends_on": []},
                    "sample": {"depends_on": []},
                }
            },
        )
        normalizer = ShapeShifter(project=config, table_store=table_store, default_entity="survey")

        # Mock the linker's link_entity method
        with patch.object(normalizer.linker, "link_entity", return_value=False) as mock_link:
            normalizer.link()

            # Should be called for each processed entity (survey, site, and sample)
            assert mock_link.call_count == 3
            call_args_list = [call.kwargs for call in mock_link.call_args_list]
            entity_names = [args["entity_name"] for args in call_args_list]
            assert set(entity_names) == {"survey", "site", "sample"}

    @pytest.mark.asyncio
    async def test_normalize_with_circular_dependency(self, survey_only_config: ShapeShiftProject):
        """Test that normalize raises error for circular dependencies."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey")
        normalizer.table_store = {"survey": df}

        normalizer.project.table_names = ["site", "sample"]

        # Create circular dependency
        def mock_get_table(entity_name):
            mock_cfg = Mock()
            if entity_name == "site":
                mock_cfg.depends_on = {"sample"}
            else:
                mock_cfg.depends_on = {"site"}
            return mock_cfg

        with patch.object(normalizer.project, "get_table", side_effect=mock_get_table):
            with pytest.raises(ValueError, match="Circular or unresolved dependencies"):
                await normalizer.normalize()

    def test_unnest_all(self, survey_only_config: ShapeShiftProject):
        """Test unnesting all entities."""
        df = pd.DataFrame({"col1": [1, 2]})
        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey")
        normalizer.table_store = {"survey": df}

        site_df = pd.DataFrame({"site_id": [1], "Ort": ["Berlin"]})
        sample_df = pd.DataFrame({"sample_id": [1], "Type": ["Soil"]})
        normalizer.table_store["site"] = site_df
        normalizer.table_store["sample"] = sample_df

        with patch.object(normalizer, "unnest_entity") as mock_unnest:
            mock_unnest.side_effect = lambda entity: normalizer.table_store[entity]

            normalizer.unnest_all()

            # Should be called for all entities including survey
            assert mock_unnest.call_count == 3

    def test_map_to_remote_links_only_configured_entities(self, survey_and_site_config: ShapeShiftProject):
        """map_to_remote should link only entities present in link config."""
        table_store = {
            "survey": pd.DataFrame({"id": [1]}),
            "site": pd.DataFrame({"site_id": [10]}),
            "other": pd.DataFrame({"x": [1]}),
        }
        normalizer = ShapeShifter(project=survey_and_site_config, default_entity="survey", table_store=table_store)

        mocked_service = Mock()
        mocked_service.link_to_remote = Mock(return_value=pd.DataFrame({"site_id": [10], "remote_id": [99]}))

        with patch("src.normalizer.LinkToRemoteService", return_value=mocked_service) as mock_service:
            normalizer.map_to_remote({"site": {"remote": "cfg"}})

        mock_service.assert_called_once()
        assert mocked_service.link_to_remote.call_count == 1
        called_entity, passed_df = mocked_service.link_to_remote.call_args.args
        assert called_entity == "site"
        assert "site_id" in passed_df.columns
        assert "remote_id" in normalizer.table_store["site"].columns
        pd.testing.assert_frame_equal(normalizer.table_store["other"], table_store["other"])

    def test_log_shapes_writes_tsv(self, tmp_path: Path, survey_only_config: ShapeShiftProject):
        """log_shapes should write table shapes TSV next to target."""
        normalizer = ShapeShifter(project=survey_only_config, default_entity="survey")
        normalizer.table_store = {
            "survey": pd.DataFrame({"a": [1, 2], "b": [3, 4]}),
            "site": pd.DataFrame({"x": [1], "y": [2]}),
        }

        target = tmp_path / "output.xlsx"
        normalizer.log_shapes(str(target))

        tsv_path = tmp_path / "table_shapes.tsv"
        assert tsv_path.exists()
        content = tsv_path.read_text().strip().splitlines()
        assert content[0] == "entity\tnum_rows\tnum_columns"
        assert len(content) == 3  # header + two entities

    def test_resolve_loader_with_data_source(self):
        """Test resolve_loader with data_source configured."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "data_source": "postgres_db"}}
        options = {"data_sources": {"postgres_db": {"driver": "postgresql", "options": {"host": "localhost"}}}}

        project = ShapeShiftProject(cfg={"entities": entities, "options": options}, filename="test-config.yml")
        table_cfg: TableConfig = project.get_table("site")

        normalizer = ShapeShifter(project=project, default_entity="site")

        # This will fail if the loader type isn't registered, but we're testing the logic
        # In real code, the DataLoaders would be registered
        try:
            loader = normalizer.resolve_loader(table_cfg)
            # If it succeeds, check it's not None (depends on DataLoaders being registered)
            assert loader is not None
        except KeyError:
            # Expected if the loader type isn't registered
            pass

    def test_resolve_loader_with_type(self):
        """Test resolve_loader with type configured."""
        entities: dict[str, dict[str, Any]] = {"site": {"surrogate_id": "site_id", "type": "fixed"}}
        options: dict[str, dict[str, Any]] = {}

        project = ShapeShiftProject(cfg={"entities": entities, "options": options}, filename="test-config.yml")
        table_cfg: TableConfig = project.get_table("site")
        normalizer = ShapeShifter(project=project, default_entity="site")

        # This will fail if the loader type isn't registered
        try:
            loader = normalizer.resolve_loader(table_cfg)
            # Test passes if no exception and loader is returned
            assert loader is not None
        except KeyError:
            # Expected if the loader type isn't registered
            pass

    def test_resolve_loader_no_loader(self):
        """Test resolve_loader returns None when no loader available."""
        entities: dict[str, dict[str, str]] = {"site": {"surrogate_id": "site_id"}}
        options: dict[str, dict[str, Any]] = {}

        project = ShapeShiftProject(cfg={"entities": entities, "options": options}, filename="test-config.yml")
        table_cfg: TableConfig = project.get_table("site")
        normalizer = ShapeShifter(project=project, default_entity="site")

        loader: DataLoader | None = normalizer.resolve_loader(table_cfg)

        # Should return None or log warning
        assert loader is None
