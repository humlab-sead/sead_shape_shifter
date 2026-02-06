"""Tests for EntityGeneratorService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.exceptions import ResourceConflictError, ResourceNotFoundError
from backend.app.models.data_source import ColumnMetadata, TableSchema
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.entity_generator_service import EntityGeneratorService


class TestEntityGeneratorService:
    """Test EntityGeneratorService for generating entity configurations from database tables."""

    @pytest.fixture
    def mock_schema_service(self):
        """Create mock schema introspection service."""
        service = MagicMock()
        service.get_table_schema = AsyncMock()
        service.data_source_service = MagicMock()
        service.data_source_service.load_data_source = MagicMock()
        
        # Mock the loader with quote_name and qualify_name methods
        mock_loader = MagicMock()
        mock_loader.quote_name = MagicMock(side_effect=lambda name: name)  # Return name as-is for simplicity
        mock_loader.qualify_name = MagicMock(side_effect=lambda schema=None, table=None: f"{schema}.{table}" if schema else table)
        service.create_loader_for_data_source = MagicMock(return_value=mock_loader)
        
        return service

    @pytest.fixture
    def mock_project_service(self):
        """Create mock project service."""
        service = MagicMock()
        service.load_project = MagicMock()
        service.add_entity_by_name = MagicMock()
        return service

    @pytest.fixture
    def generator_service(self, mock_schema_service, mock_project_service):
        """Create EntityGeneratorService with mocked dependencies."""
        return EntityGeneratorService(schema_service=mock_schema_service, project_service=mock_project_service)

    @pytest.fixture
    def mock_project(self):
        """Create mock project."""
        return Project(
            metadata=ProjectMetadata(
                type="shapeshifter-project",
                name="test_project",
                version="1.0.0",
                entity_count=1,
                created_at=0,
                modified_at=0,
                is_valid=True,
            ),
            entities={
                "existing_entity": {
                    "type": "sql",
                    "data_source": "test_db",
                    "query": "SELECT * FROM existing",
                }
            },
            options={
                "data_sources": {
                    "test_db": "@include: test_db.yml",
                }
            },
        )

    @pytest.fixture
    def mock_table_schema(self):
        """Create mock table schema with primary keys."""
        return TableSchema(
            table_name="users",
            schema_name=None,
            columns=[
                ColumnMetadata(
                    name="user_id",
                    data_type="integer",
                    nullable=False,
                    is_primary_key=True,
                    default=None,
                    max_length=None,
                ),
                ColumnMetadata(
                    name="username",
                    data_type="varchar",
                    nullable=False,
                    is_primary_key=False,
                    default=None,
                    max_length=255,
                ),
                ColumnMetadata(
                    name="email",
                    data_type="varchar",
                    nullable=True,
                    is_primary_key=False,
                    default=None,
                    max_length=255,
                ),
            ],
            row_count=1000,
        )

    @pytest.mark.asyncio
    async def test_generate_from_table_basic(
        self, generator_service: EntityGeneratorService, mock_project_service, mock_schema_service, mock_project, mock_table_schema
    ):
        """Test basic entity generation from table."""
        # Setup mocks
        mock_project_service.load_project.return_value = mock_project
        mock_schema_service.get_table_schema.return_value = mock_table_schema
        mock_schema_service.data_source_service.load_data_source.return_value = MagicMock()  # Return a mock DataSourceConfig

        # Execute
        result = await generator_service.generate_from_table(project_name="test_project", data_source_key="test_db", table_name="users")

        # Verify project was loaded
        mock_project_service.load_project.assert_called_once_with("test_project")

        # Verify schema was fetched
        mock_schema_service.get_table_schema.assert_called_once_with("test_db.yml", "users", schema=None)

        # Verify entity was added
        mock_project_service.add_entity_by_name.assert_called_once()
        call_args = mock_project_service.add_entity_by_name.call_args
        assert call_args[0][0] == "test_project"  # project_name
        assert call_args[0][1] == "users"  # entity_name (defaulted to table_name)

        # Verify generated config
        assert result["type"] == "sql"
        assert result["data_source"] == "test_db"
        assert result["query"] == "SELECT user_id, username, email FROM users"  # Updated to match actual query generation
        assert result["keys"] == ["user_id"]  # Primary key detected
        assert result["public_id"] == "users_id"

    @pytest.mark.asyncio
    async def test_generate_from_table_with_custom_entity_name(
        self, generator_service, mock_project_service, mock_schema_service, mock_project, mock_table_schema
    ):
        """Test entity generation with custom entity name."""
        mock_project_service.load_project.return_value = mock_project
        mock_schema_service.get_table_schema.return_value = mock_table_schema
        mock_schema_service.data_source_service.load_data_source.return_value = MagicMock()  # Return a mock DataSourceConfig

        result = await generator_service.generate_from_table(
            project_name="test_project", data_source_key="test_db", table_name="users", entity_name="app_users"
        )

        # Verify custom entity name was used
        call_args = mock_project_service.add_entity_by_name.call_args
        assert call_args[0][1] == "app_users"

        # public_id should still be based on table name
        assert result["public_id"] == "users_id"

    @pytest.mark.asyncio
    async def test_generate_from_table_with_schema_prefix(
        self, generator_service: EntityGeneratorService, mock_project_service, mock_schema_service, mock_project, mock_table_schema
    ):
        """Test entity generation with PostgreSQL schema prefix."""
        mock_project_service.load_project.return_value = mock_project
        
        # Update mock_table_schema to include schema_name
        mock_table_schema.schema_name = "public"
        mock_schema_service.get_table_schema.return_value = mock_table_schema
        mock_schema_service.data_source_service.load_data_source.return_value = MagicMock()  # Return a mock DataSourceConfig

        result = await generator_service.generate_from_table(
            project_name="test_project", data_source_key="test_db", table_name="users", schema="public"
        )

        # Verify schema was passed to get_table_schema
        mock_schema_service.get_table_schema.assert_called_once_with("test_db.yml", "users", schema="public")

        # Query should include schema prefix (using the mocked qualify_name which returns "schema.table")
        assert result["query"] == "SELECT user_id, username, email FROM public.users"

    @pytest.mark.asyncio
    async def test_generate_from_table_no_primary_keys(self, generator_service: EntityGeneratorService, mock_project_service, mock_schema_service, mock_project):
        """Test entity generation for table without primary keys."""
        mock_project_service.load_project.return_value = mock_project
        mock_schema_service.data_source_service.load_data_source.return_value = MagicMock()  # Return a mock DataSourceConfig

        # Table schema with no primary keys
        table_schema = TableSchema(
            table_name="logs",
            schema_name=None,
            columns=[
                ColumnMetadata(
                    name="log_id",
                    data_type="integer",
                    nullable=False,
                    is_primary_key=False,  # Not a PK
                    default=None,
                    max_length=None,
                ),
                ColumnMetadata(
                    name="message",
                    data_type="text",
                    nullable=True,
                    is_primary_key=False,
                    default=None,
                    max_length=None,
                ),
            ],
            row_count=10000,
        )
        mock_schema_service.get_table_schema.return_value = table_schema

        result = await generator_service.generate_from_table(project_name="test_project", data_source_key="test_db", table_name="logs")

        # Keys should be empty list
        assert result["keys"] == []

    @pytest.mark.asyncio
    async def test_generate_from_table_composite_primary_key(
        self, generator_service: EntityGeneratorService, mock_project_service, mock_schema_service, mock_project
    ):
        """Test entity generation for table with composite primary key."""
        mock_project_service.load_project.return_value = mock_project
        mock_schema_service.data_source_service.load_data_source.return_value = MagicMock()  # Return a mock DataSourceConfig

        # Table schema with composite PK
        table_schema = TableSchema(
            table_name="user_roles",
            schema_name=None,
            columns=[
                ColumnMetadata(
                    name="user_id",
                    data_type="integer",
                    nullable=False,
                    is_primary_key=True,  # Part of composite PK
                    default=None,
                    max_length=None,
                ),
                ColumnMetadata(
                    name="role_id",
                    data_type="integer",
                    nullable=False,
                    is_primary_key=True,  # Part of composite PK
                    default=None,
                    max_length=None,
                ),
            ],
            row_count=1000,
        )
        mock_schema_service.get_table_schema.return_value = table_schema

        result = await generator_service.generate_from_table(project_name="test_project", data_source_key="test_db", table_name="user_roles")

        # Both keys should be included
        assert result["keys"] == ["user_id", "role_id"]

    @pytest.mark.asyncio
    async def test_generate_from_table_project_not_found(self, generator_service: EntityGeneratorService, mock_project_service):
        """Test error handling when project not found."""
        mock_project_service.load_project.side_effect = ResourceNotFoundError("Project 'nonexistent' not found")

        with pytest.raises(ResourceNotFoundError, match="Project 'nonexistent' not found"):
            await generator_service.generate_from_table(project_name="nonexistent", data_source_key="test_db", table_name="users")

    @pytest.mark.asyncio
    async def test_generate_from_table_duplicate_entity_name(
        self, generator_service: EntityGeneratorService, mock_project_service, mock_schema_service, mock_project, mock_table_schema
    ):
        """Test error handling when entity name already exists."""
        mock_project_service.load_project.return_value = mock_project
        mock_schema_service.get_table_schema.return_value = mock_table_schema
        mock_schema_service.data_source_service.load_data_source.return_value = MagicMock()  # Return a mock DataSourceConfig

        with pytest.raises(ResourceConflictError, match="Entity 'existing_entity' already exists"):
            await generator_service.generate_from_table(
                project_name="test_project", data_source_key="test_db", table_name="users", entity_name="existing_entity"
            )

    @pytest.mark.asyncio
    async def test_generate_from_table_resolves_inline_data_source_dict(
        self, generator_service: EntityGeneratorService, mock_project_service, mock_schema_service, mock_project, mock_table_schema
    ):
        """Inline dict data sources should be passed through to schema introspection."""
        mock_project_service.load_project.return_value = mock_project
        mock_schema_service.get_table_schema.return_value = mock_table_schema
        mock_schema_service.data_source_service.load_data_source.return_value = MagicMock()  # Return a mock DataSourceConfig

        # Inline dict config for the project data source
        mock_project.options["data_sources"]["test_db"] = {
            "name": "inline_ds",
            "driver": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "db",
            "user": "user",
        }

        await generator_service.generate_from_table(project_name="test_project", data_source_key="test_db", table_name="users")

        mock_schema_service.get_table_schema.assert_called_once()
        args, kwargs = mock_schema_service.get_table_schema.call_args
        assert isinstance(args[0], dict)
        assert args[0]["driver"] == "postgresql"
        assert args[1] == "users"
        assert kwargs.get("schema") is None

    @pytest.mark.asyncio
    async def test_generate_from_table_missing_project_data_source_key_raises(
        self, generator_service: EntityGeneratorService, mock_project_service, mock_schema_service, mock_project
    ):
        """If the project does not define the requested data source key, raise a ResourceNotFoundError."""
        mock_project_service.load_project.return_value = mock_project
        mock_project.options["data_sources"].pop("test_db")

        with pytest.raises(ResourceNotFoundError, match="Data source 'test_db' not found"):
            await generator_service.generate_from_table(project_name="test_project", data_source_key="test_db", table_name="users")

        mock_schema_service.get_table_schema.assert_not_called()
