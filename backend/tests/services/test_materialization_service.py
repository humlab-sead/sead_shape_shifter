"""Tests for materialization service."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.services.materialization_service import (
    CSVMaterializationStorage,
    MaterializationError,
    MaterializationService,
    MaterializationStorage,
    ParquetMaterializationStorage,
)
from backend.app.services.project_service import ProjectService
from src.model import MaterializationConfig, ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter
from src.specifications.materialize import CanMaterializeSpecification

# pylint: disable=redefined-outer-name, unused-argument, protected-access


@pytest.fixture
def mock_project_service():
    """Create mock ProjectService."""
    return MagicMock(spec=ProjectService)


@pytest.fixture
def mock_api_project():
    """Create mock API Project."""
    project = MagicMock(spec=Project)
    project.entities = {
        "location": {
            "type": "source",
            "source": "locations.csv",
            "public_id": "location_id",
            "keys": ["location_name"],
        }
    }
    return project


@pytest.fixture
def mock_table_config():
    """Create mock TableConfig."""
    table = MagicMock(spec=TableConfig)
    table.entity_name = "location"
    table.public_id = "location_id"
    table.keys = ["location_name"]
    table.is_materialized = False
    table.entity_cfg = {
        "type": "source",
        "source": "locations.csv",
        "public_id": "location_id",
        "keys": ["location_name"],
    }
    table.dependent_entities = Mock(return_value=[])
    return table


@pytest.fixture
def mock_materialized_table_config():
    """Create mock materialized TableConfig."""
    table = MagicMock(spec=TableConfig)
    table.entity_name = "location"
    table.public_id = "location_id"
    table.keys = ["location_name"]
    table.is_materialized = True
    table.materialized = MaterializationConfig(
        data={
            "enabled": True,
            "source_state": {
                "type": "source",
                "source": "locations.csv",
                "public_id": "location_id",
                "keys": ["location_name"],
            },
            "materialized_at": "2026-03-05T12:00:00",
        }
    )
    table.dependent_entities = Mock(return_value=[])
    return table


@pytest.fixture
def mock_core_project(mock_table_config):
    """Create mock ShapeShiftProject."""
    project = MagicMock(spec=ShapeShiftProject)
    project.get_table = Mock(return_value=mock_table_config)
    return project


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "location_id": [1, 2, 3],
            "location_name": ["Norway", "Sweden", "Denmark"],
            "country_code": ["NO", "SE", "DK"],
        }
    )


@pytest.fixture
def small_dataframe():
    """Create small DataFrame (below threshold)."""
    return pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})


@pytest.fixture
def materialization_service(mock_project_service):
    """Create MaterializationService with mocked dependencies."""
    return MaterializationService(project_service=mock_project_service)


class TestMaterializeEntity:
    """Tests for materialize_entity method."""

    @pytest.mark.asyncio
    async def test_materialize_validation_failure(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_table_config
    ):
        """Test materialization when validation fails."""
        mock_project_service.load_project.return_value = mock_api_project

        mock_spec = MagicMock(spec=CanMaterializeSpecification)
        mock_spec.is_satisfied_by.return_value = False
        mock_spec.errors = ["Cannot materialize: entity has circular dependencies"]

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            with patch("backend.app.services.materialization_service.CanMaterializeSpecification", return_value=mock_spec):
                result = await materialization_service.materialize_entity("test-project", "location", "parquet")

                assert not result.success
                assert result.entity_name == "location"
                assert len(result.errors) == 1
                assert "circular dependencies" in result.errors[0]

    @pytest.mark.asyncio
    async def test_materialize_inline_explicit(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_table_config, sample_dataframe
    ):
        """Test materialization with explicit inline storage."""
        mock_project_service.load_project.return_value = mock_api_project
        mock_project_service.save_project = Mock()

        mock_spec = MagicMock(spec=CanMaterializeSpecification)
        mock_spec.is_satisfied_by.return_value = True

        mock_shapeshifter = MagicMock(spec=ShapeShifter)
        mock_shapeshifter.table_store = {"location": sample_dataframe}

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            with patch("backend.app.services.materialization_service.CanMaterializeSpecification", return_value=mock_spec):
                with patch("backend.app.services.materialization_service.ShapeShifter", return_value=mock_shapeshifter):
                    result = await materialization_service.materialize_entity("test-project", "location", "inline")

                    assert result.success
                    assert result.entity_name == "location"
                    assert result.rows_materialized == 3
                    assert result.storage_format == "inline"
                    assert result.storage_file is None
                    mock_project_service.save_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_materialize_auto_inline_small_dataset(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_table_config, small_dataframe
    ):
        """Test materialization auto-switches to inline for small datasets."""
        mock_project_service.load_project.return_value = mock_api_project
        mock_project_service.save_project = Mock()

        mock_spec = MagicMock(spec=CanMaterializeSpecification)
        mock_spec.is_satisfied_by.return_value = True

        mock_shapeshifter = MagicMock(spec=ShapeShifter)
        mock_shapeshifter.table_store = {"location": small_dataframe}

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            with patch("backend.app.services.materialization_service.CanMaterializeSpecification", return_value=mock_spec):
                with patch("backend.app.services.materialization_service.ShapeShifter", return_value=mock_shapeshifter):
                    # Request parquet but get inline due to small size
                    result = await materialization_service.materialize_entity("test-project", "location", "parquet")

                    assert result.success
                    assert result.storage_format == "inline"  # Auto-optimized
                    assert result.storage_file is None

    @pytest.mark.asyncio
    async def test_materialize_parquet_storage(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_table_config, sample_dataframe
    ):
        """Test materialization with parquet storage."""
        mock_project_service.load_project.return_value = mock_api_project
        mock_project_service.save_project = Mock()

        mock_spec = MagicMock(spec=CanMaterializeSpecification)
        mock_spec.is_satisfied_by.return_value = True

        mock_shapeshifter = MagicMock(spec=ShapeShifter)
        # Use larger dataset to avoid auto-inline
        large_df = pd.concat([sample_dataframe] * 10, ignore_index=True)
        mock_shapeshifter.table_store = {"location": large_df}

        mock_storage = MagicMock(spec=ParquetMaterializationStorage)
        mock_storage.store.return_value = True
        mock_storage.get_relative_filename.return_value = Path("test-project/materialized/location.parquet")

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            with patch("backend.app.services.materialization_service.CanMaterializeSpecification", return_value=mock_spec):
                with patch("backend.app.services.materialization_service.ShapeShifter", return_value=mock_shapeshifter):
                    with patch.object(MaterializationStorage, "create", return_value=mock_storage):
                        result = await materialization_service.materialize_entity("test-project", "location", "parquet")

                        assert result.success
                        assert result.entity_name == "location"
                        assert result.rows_materialized == 30
                        assert result.storage_format == "parquet"
                        assert result.storage_file == "test-project/materialized/location.parquet"
                        mock_storage.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_materialize_csv_storage(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_table_config, sample_dataframe
    ):
        """Test materialization with CSV storage."""
        mock_project_service.load_project.return_value = mock_api_project
        mock_project_service.save_project = Mock()

        mock_spec = MagicMock(spec=CanMaterializeSpecification)
        mock_spec.is_satisfied_by.return_value = True

        mock_shapeshifter = MagicMock(spec=ShapeShifter)
        large_df = pd.concat([sample_dataframe] * 10, ignore_index=True)
        mock_shapeshifter.table_store = {"location": large_df}

        mock_storage = MagicMock(spec=CSVMaterializationStorage)
        mock_storage.store.return_value = True
        mock_storage.get_relative_filename.return_value = Path("test-project/materialized/location.csv")

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            with patch("backend.app.services.materialization_service.CanMaterializeSpecification", return_value=mock_spec):
                with patch("backend.app.services.materialization_service.ShapeShifter", return_value=mock_shapeshifter):
                    with patch.object(MaterializationStorage, "create", return_value=mock_storage):
                        result = await materialization_service.materialize_entity("test-project", "location", "csv")

                        assert result.success
                        assert result.storage_format == "csv"
                        mock_storage.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_materialize_entity_not_in_results(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_table_config
    ):
        """Test materialization when entity not found in normalization results."""
        mock_project_service.load_project.return_value = mock_api_project

        mock_spec = MagicMock(spec=CanMaterializeSpecification)
        mock_spec.is_satisfied_by.return_value = True

        mock_shapeshifter = MagicMock(spec=ShapeShifter)
        mock_shapeshifter.table_store = {}  # Empty results

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            with patch("backend.app.services.materialization_service.CanMaterializeSpecification", return_value=mock_spec):
                with patch("backend.app.services.materialization_service.ShapeShifter", return_value=mock_shapeshifter):
                    result = await materialization_service.materialize_entity("test-project", "location", "parquet")

                    assert not result.success
                    assert "not found in normalization results" in result.errors[0]

    @pytest.mark.asyncio
    async def test_materialize_storage_failure(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_table_config, sample_dataframe
    ):
        """Test materialization when storage fails."""
        mock_project_service.load_project.return_value = mock_api_project

        mock_spec = MagicMock(spec=CanMaterializeSpecification)
        mock_spec.is_satisfied_by.return_value = True

        mock_shapeshifter = MagicMock(spec=ShapeShifter)
        large_df = pd.concat([sample_dataframe] * 10, ignore_index=True)
        mock_shapeshifter.table_store = {"location": large_df}

        mock_storage = MagicMock(spec=ParquetMaterializationStorage)
        mock_storage.store.return_value = False  # Storage failure

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            with patch("backend.app.services.materialization_service.CanMaterializeSpecification", return_value=mock_spec):
                with patch("backend.app.services.materialization_service.ShapeShifter", return_value=mock_shapeshifter):
                    with patch.object(MaterializationStorage, "create", return_value=mock_storage):
                        result = await materialization_service.materialize_entity("test-project", "location", "parquet")

                        assert not result.success
                        assert "Failed to store data" in result.errors[0]


class TestUnmaterializeEntity:
    """Tests for unmaterialize_entity method."""

    @pytest.mark.asyncio
    async def test_unmaterialize_not_materialized(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_table_config
    ):
        """Test unmaterialization when entity is not materialized."""
        mock_project_service.load_project.return_value = mock_api_project
        mock_table_config.is_materialized = False

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await materialization_service.unmaterialize_entity("test-project", "location")

            assert not result.success
            assert "not materialized" in result.errors[0]

    @pytest.mark.asyncio
    async def test_unmaterialize_success(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_materialized_table_config
    ):
        """Test successful unmaterialization."""
        mock_project_service.load_project.return_value = mock_api_project
        mock_project_service.save_project = Mock()
        mock_core_project.get_table = Mock(return_value=mock_materialized_table_config)

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await materialization_service.unmaterialize_entity("test-project", "location")

            assert result.success
            assert result.entity_name == "location"
            assert result.unmaterialized_entities == ["location"]
            mock_project_service.save_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_unmaterialize_requires_cascade(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_materialized_table_config
    ):
        """Test unmaterialization fails when dependents exist without cascade."""
        mock_project_service.load_project.return_value = mock_api_project
        mock_core_project.get_table = Mock(return_value=mock_materialized_table_config)

        # Mock dependent entities
        mock_materialized_table_config.dependent_entities.return_value = ["site", "sample"]

        # Mock dependent tables as materialized
        dependent_table = MagicMock(spec=TableConfig)
        dependent_table.is_materialized = True

        def get_table_side_effect(name):
            if name == "location":
                return mock_materialized_table_config
            return dependent_table

        mock_core_project.get_table.side_effect = get_table_side_effect

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await materialization_service.unmaterialize_entity("test-project", "location", cascade=False)

            assert not result.success
            assert result.requires_cascade
            assert "site" in result.affected_entities
            assert "sample" in result.affected_entities

    @pytest.mark.asyncio
    async def test_unmaterialize_cascade_success(
        self, materialization_service, mock_project_service, mock_api_project, mock_core_project, mock_materialized_table_config
    ):
        """Test successful cascade unmaterialization."""
        mock_project_service.load_project.return_value = mock_api_project
        mock_project_service.save_project = Mock()

        # Setup dependent entity
        dependent_table = MagicMock(spec=TableConfig)
        dependent_table.entity_name = "site"
        dependent_table.is_materialized = True
        dependent_table.materialized = MaterializationConfig(
            data={
                "enabled": True,
                "source_state": {"type": "source", "source": "sites.csv"},
                "materialized_at": "2026-03-05T12:00:00",
            }
        )
        dependent_table.dependent_entities.return_value = []

        mock_materialized_table_config.dependent_entities.return_value = ["site"]

        def get_table_side_effect(name):
            if name == "location":
                return mock_materialized_table_config
            if name == "site":
                return dependent_table
            return None

        mock_core_project.get_table.side_effect = get_table_side_effect

        with patch.object(ProjectMapper, "to_core", return_value=mock_core_project):
            result = await materialization_service.unmaterialize_entity("test-project", "location", cascade=True)

            assert result.success
            assert result.entity_name == "location"
            assert "location" in result.unmaterialized_entities
            assert "site" in result.unmaterialized_entities
            # Should be called twice: once for dependent, once for main entity
            assert mock_project_service.save_project.call_count == 2


class TestCreateMaterializedEntity:
    """Tests for _create_materialized_entity method."""

    def test_create_materialized_entity_normal(self, materialization_service, mock_table_config, sample_dataframe):
        """Test creating materialized entity config."""
        values_inline = [[1, "Norway", "NO"], [2, "Sweden", "SE"]]

        with patch("backend.app.services.materialization_service.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2026-03-05T12:00:00"

            result = materialization_service._create_materialized_entity(mock_table_config, sample_dataframe, values_inline)

            assert result["type"] == "fixed"
            assert result["public_id"] == "location_id"
            assert result["keys"] == ["location_name"]
            assert result["columns"] == ["location_id", "location_name", "country_code"]
            assert result["values"] == values_inline
            assert result["materialized"]["enabled"] is True
            assert "source_state" in result["materialized"]
            assert result["materialized"]["materialized_at"] == "2026-03-05T12:00:00"

    def test_create_materialized_entity_with_load_directive(self, materialization_service, mock_table_config, sample_dataframe):
        """Test creating materialized entity with @load: directive."""
        values_inline = "@load:test-project/materialized/location.parquet"

        result = materialization_service._create_materialized_entity(mock_table_config, sample_dataframe, values_inline)

        assert result["values"] == "@load:test-project/materialized/location.parquet"

    def test_create_materialized_entity_empty_saved_state(self, materialization_service, sample_dataframe):
        """Test creating materialized entity when saved_state is empty."""
        mock_table = MagicMock(spec=TableConfig)
        mock_table.entity_name = "empty_entity"
        mock_table.public_id = "empty_id"
        mock_table.keys = []
        mock_table.entity_cfg = {}  # Empty config

        with patch("backend.app.services.materialization_service.logger") as mock_logger:
            result = materialization_service._create_materialized_entity(mock_table, sample_dataframe, [[]])

            assert result["materialized"]["source_state"] == {}
            mock_logger.warning.assert_called_once()
            assert "no config to save" in mock_logger.warning.call_args[0][0]


class TestFindMaterializedDependents:
    """Tests for _find_materialized_dependents method."""

    def test_find_materialized_dependents_none(self, materialization_service, mock_core_project, mock_table_config):
        """Test finding dependents when none exist."""
        mock_table_config.dependent_entities.return_value = []

        dependents = materialization_service._find_materialized_dependents(mock_core_project, mock_table_config)

        assert dependents == []

    def test_find_materialized_dependents_mixed(self, materialization_service, mock_core_project, mock_table_config):
        """Test finding dependents with mixed materialization status."""
        mock_table_config.dependent_entities.return_value = ["site", "sample", "analysis"]

        # Setup different tables with different materialization status
        def get_table_side_effect(name):
            table = MagicMock(spec=TableConfig)
            if name == "site":
                table.is_materialized = True
            elif name == "sample":
                table.is_materialized = False
            elif name == "analysis":
                table.is_materialized = True
            return table

        mock_core_project.get_table.side_effect = get_table_side_effect

        dependents = materialization_service._find_materialized_dependents(mock_core_project, mock_table_config)

        assert len(dependents) == 2
        assert "site" in dependents
        assert "analysis" in dependents
        assert "sample" not in dependents

    def test_find_materialized_dependents_none_returned(self, materialization_service, mock_core_project, mock_table_config):
        """Test finding dependents handles None from get_table."""
        mock_table_config.dependent_entities.return_value = ["missing_entity"]
        mock_core_project.get_table.return_value = None

        dependents = materialization_service._find_materialized_dependents(mock_core_project, mock_table_config)

        assert dependents == []


class TestStoreProject:
    """Tests for _store_project method."""

    def test_store_project_success(self, materialization_service, mock_project_service, mock_api_project):
        """Test successful project save."""
        materialization_service.project_service.save_project = Mock()

        materialization_service._store_project(mock_api_project)

        materialization_service.project_service.save_project.assert_called_once_with(mock_api_project)

    def test_store_project_raises_materialization_error(self, materialization_service, mock_api_project):
        """Test _store_project raises MaterializationError on failure."""
        materialization_service.project_service.save_project = Mock(side_effect=Exception("Save failed"))

        with pytest.raises(MaterializationError) as exc_info:
            materialization_service._store_project(mock_api_project)

        assert "Failed to save project configuration" in str(exc_info.value)


class TestMaterializationStorage:
    """Tests for MaterializationStorage classes."""

    @patch("backend.app.services.materialization_service.Settings")
    @patch("backend.app.services.materialization_service.ProjectNameMapper")
    def test_csv_storage_initialization(self, mock_name_mapper, mock_settings, tmp_path):
        """Test CSV storage initialization."""
        mock_settings.return_value.PROJECTS_DIR = tmp_path
        mock_name_mapper.to_path.return_value = "test-project"

        storage = CSVMaterializationStorage("test-project")

        assert storage.project_name == "test-project"
        assert storage.extension == "csv"
        assert storage.data_dir.exists()

    @patch("backend.app.services.materialization_service.Settings")
    @patch("backend.app.services.materialization_service.ProjectNameMapper")
    def test_parquet_storage_initialization(self, mock_name_mapper, mock_settings, tmp_path):
        """Test Parquet storage initialization."""
        mock_settings.return_value.PROJECTS_DIR = tmp_path
        mock_name_mapper.to_path.return_value = "test-project"

        storage = ParquetMaterializationStorage("test-project")

        assert storage.project_name == "test-project"
        assert storage.extension == "parquet"
        assert storage.data_dir.exists()

    @patch("backend.app.services.materialization_service.Settings")
    @patch("backend.app.services.materialization_service.ProjectNameMapper")
    def test_storage_get_filename(self, mock_name_mapper, mock_settings, tmp_path):
        """Test filename generation."""
        mock_settings.return_value.PROJECTS_DIR = tmp_path
        mock_name_mapper.to_path.return_value = "test-project"

        csv_storage = CSVMaterializationStorage("test-project")
        parquet_storage = ParquetMaterializationStorage("test-project")

        assert csv_storage.get_filename("location") == "location.csv"
        assert parquet_storage.get_filename("location") == "location.parquet"

    @patch("backend.app.services.materialization_service.Settings")
    @patch("backend.app.services.materialization_service.ProjectNameMapper")
    def test_storage_get_relative_filename(self, mock_name_mapper, mock_settings, tmp_path):
        """Test relative filename generation."""
        mock_settings.return_value.PROJECTS_DIR = tmp_path
        mock_name_mapper.to_path.return_value = "test-project"

        storage = CSVMaterializationStorage("test-project")
        relative = storage.get_relative_filename("location")

        assert str(relative) == "test-project/materialized/location.csv"

    @patch("backend.app.services.materialization_service.Settings")
    @patch("backend.app.services.materialization_service.ProjectNameMapper")
    def test_csv_storage_store_success(self, mock_name_mapper, mock_settings, tmp_path, sample_dataframe):
        """Test CSV storage stores data correctly."""
        mock_settings.return_value.PROJECTS_DIR = tmp_path
        mock_name_mapper.to_path.return_value = "test-project"

        storage = CSVMaterializationStorage("test-project")
        success = storage.store("location", sample_dataframe)

        assert success
        csv_file = storage.get_absolute_file_path("location")
        assert csv_file.exists()

        # Verify data
        loaded_df = pd.read_csv(csv_file)
        assert len(loaded_df) == 3
        assert list(loaded_df.columns) == ["location_id", "location_name", "country_code"]

    @patch("backend.app.services.materialization_service.Settings")
    @patch("backend.app.services.materialization_service.ProjectNameMapper")
    def test_parquet_storage_store_success(self, mock_name_mapper, mock_settings, tmp_path, sample_dataframe):
        """Test Parquet storage stores data correctly."""
        mock_settings.return_value.PROJECTS_DIR = tmp_path
        mock_name_mapper.to_path.return_value = "test-project"

        storage = ParquetMaterializationStorage("test-project")
        success = storage.store("location", sample_dataframe)

        assert success
        parquet_file = storage.get_absolute_file_path("location")
        assert parquet_file.exists()

        # Verify data
        loaded_df = pd.read_parquet(parquet_file)
        assert len(loaded_df) == 3
        assert list(loaded_df.columns) == ["location_id", "location_name", "country_code"]

    def test_storage_factory_parquet(self):
        """Test factory creates Parquet storage."""
        with patch("backend.app.services.materialization_service.Settings"):
            with patch("backend.app.services.materialization_service.ProjectNameMapper"):
                storage = MaterializationStorage.create("test-project", "parquet")
                assert isinstance(storage, ParquetMaterializationStorage)

    def test_storage_factory_csv(self):
        """Test factory creates CSV storage."""
        with patch("backend.app.services.materialization_service.Settings"):
            with patch("backend.app.services.materialization_service.ProjectNameMapper"):
                storage = MaterializationStorage.create("test-project", "csv")
                assert isinstance(storage, CSVMaterializationStorage)

    def test_storage_factory_default_csv(self):
        """Test factory defaults to CSV for unknown formats."""
        with patch("backend.app.services.materialization_service.Settings"):
            with patch("backend.app.services.materialization_service.ProjectNameMapper"):
                storage = MaterializationStorage.create("test-project", "unknown")
                assert isinstance(storage, CSVMaterializationStorage)
