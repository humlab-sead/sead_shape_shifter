"""
Tests for schema introspection API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.main import app
from backend.app.models.data_source import TableMetadata, ColumnMetadata, TableSchema
from backend.app.services.schema_service import SchemaIntrospectionService, SchemaServiceError


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_schema_service():
    """Create mock schema service."""
    service = MagicMock(spec=SchemaIntrospectionService)
    return service


@pytest.fixture
def sample_tables():
    """Sample table metadata for testing."""
    return [
        TableMetadata(name="table1", schema="public", comment="Test table 1", row_count=100),
        TableMetadata(name="table2", schema="public", comment="Test table 2", row_count=200),
    ]


@pytest.fixture
def sample_table_schema():
    """Sample table schema for testing."""
    return TableSchema(
        table_name="table1",
        columns=[
            ColumnMetadata(
                name="id",
                data_type="integer",
                nullable=False,
                is_primary_key=True,
                default=None,
                max_length=None,
            ),
            ColumnMetadata(
                name="name",
                data_type="character varying",
                nullable=True,
                is_primary_key=False,
                default=None,
                max_length=255,
            ),
        ],
        primary_keys=["id"],
        indexes=["table1_pkey"],
        row_count=100,
    )


class TestListTablesEndpoint:
    """Tests for GET /data-sources/{name}/tables endpoint."""

    @pytest.mark.asyncio
    async def test_list_tables_success(self, client, mock_schema_service, sample_tables):
        """Test successful table listing."""
        mock_schema_service.get_tables = AsyncMock(return_value=sample_tables)
        
        with patch('backend.app.api.dependencies.get_schema_service', return_value=mock_schema_service):
            response = client.get("/api/v1/data-sources/sead/tables")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "table1"
        assert data[1]["name"] == "table2"
        mock_schema_service.get_tables.assert_called_once_with("sead", None)

    @pytest.mark.asyncio
    async def test_list_tables_with_schema(self, client, mock_schema_service, sample_tables):
        """Test table listing with specific schema."""
        mock_schema_service.get_tables = AsyncMock(return_value=sample_tables)
        
        with patch('backend.app.api.dependencies.get_schema_service', return_value=mock_schema_service):
            response = client.get("/api/v1/data-sources/sead/tables?schema=custom_schema")
        
        assert response.status_code == 200
        mock_schema_service.get_tables.assert_called_once_with("sead", "custom_schema")

    @pytest.mark.asyncio
    async def test_list_tables_not_found(self, client, mock_schema_service):
        """Test with non-existent data source."""
        mock_schema_service.get_tables = AsyncMock(
            side_effect=SchemaServiceError("Data source 'invalid' not found")
        )
        
        with patch('backend.app.api.dependencies.get_schema_service', return_value=mock_schema_service):
            response = client.get("/api/v1/data-sources/invalid/tables")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_tables_not_supported(self, client, mock_schema_service):
        """Test with unsupported driver."""
        mock_schema_service.get_tables = AsyncMock(
            side_effect=SchemaServiceError("Schema introspection not supported for this driver")
        )
        
        with patch('backend.app.api.dependencies.get_schema_service', return_value=mock_schema_service):
            response = client.get("/api/v1/data-sources/sead/tables")
        
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_tables_database_error(self, client, mock_schema_service):
        """Test with database error."""
        mock_schema_service.get_tables = AsyncMock(
            side_effect=SchemaServiceError("Database connection failed")
        )
        
        with patch('backend.app.api.dependencies.get_schema_service', return_value=mock_schema_service):
            response = client.get("/api/v1/data-sources/sead/tables")
        
        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()


class TestGetTableSchemaEndpoint:
    """Tests for GET /data-sources/{name}/tables/{table_name}/schema endpoint."""

    @pytest.mark.asyncio
    async def test_get_table_schema_success(self, client, mock_schema_service, sample_table_schema):
        """Test successful table schema retrieval."""
        mock_schema_service.get_table_schema = AsyncMock(return_value=sample_table_schema)
        
        with patch('backend.app.api.dependencies.get_schema_service', return_value=mock_schema_service):
            response = client.get("/api/v1/data-sources/sead/tables/table1/schema")
        
        assert response.status_code == 200
        data = response.json()
        assert data["table_name"] == "table1"
        assert len(data["columns"]) == 2
        assert data["columns"][0]["name"] == "id"
        assert data["columns"][0]["is_primary_key"] is True
        mock_schema_service.get_table_schema.assert_called_once_with("sead", "table1", None)


class TestPreviewTableDataEndpoint:
    """Tests for GET /data-sources/{name}/tables/{table_name}/preview endpoint."""

    @pytest.mark.asyncio
    async def test_preview_table_success(self, client, mock_schema_service):
        """Test successful table data preview."""
        preview_data = {
            "columns": ["id", "name"],
            "rows": [
                {"id": 1, "name": "Test 1"},
                {"id": 2, "name": "Test 2"},
            ],
            "total_rows": 100,
            "limit": 50,
            "offset": 0,
        }
        mock_schema_service.preview_table_data = AsyncMock(return_value=preview_data)
        
        with patch('backend.app.api.dependencies.get_schema_service', return_value=mock_schema_service):
            response = client.get("/api/v1/data-sources/sead/tables/table1/preview")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["rows"]) == 2
        assert data["total_rows"] == 100
        mock_schema_service.preview_table_data.assert_called_once_with("sead", "table1", None, 50, 0)

    @pytest.mark.asyncio
    async def test_preview_table_with_pagination(self, client, mock_schema_service):
        """Test table preview with custom pagination."""
        preview_data = {
            "columns": ["id", "name"],
            "rows": [{"id": 21, "name": "Test 21"}],
            "total_rows": 100,
            "limit": 10,
            "offset": 20,
        }
        mock_schema_service.preview_table_data = AsyncMock(return_value=preview_data)
        
        with patch('backend.app.api.dependencies.get_schema_service', return_value=mock_schema_service):
            response = client.get("/api/v1/data-sources/sead/tables/table1/preview?limit=10&offset=20")
        
        assert response.status_code == 200
        mock_schema_service.preview_table_data.assert_called_once_with("sead", "table1", None, 10, 20)


class TestDebugSeadTables:
    """Specific tests for debugging /data-sources/sead/tables endpoint."""

    @pytest.mark.asyncio
    async def test_sead_tables_real_service(self, client):
        """Test with real service - use this for debugging.
        
        To debug:
        1. Set breakpoint in this test
        2. Set breakpoint in backend/app/api/v1/endpoints/schema.py:list_tables
        3. Set breakpoint in backend/app/services/schema_service.py:get_tables
        4. Run: PYTHONPATH=.:backend uv run pytest backend/tests/test_schema_endpoints.py::TestDebugSeadTables::test_sead_tables_real_service -v -s
        """
        # This will use the real dependency injection
        response = client.get("/api/v1/data-sources/sead/tables")
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Body: {response.text}")
        
        # Add assertions based on expected behavior
        if response.status_code == 200:
            data = response.json()
            print(f"Number of tables: {len(data)}")
            if data:
                print(f"First table: {data[0]}")
        else:
            print(f"Error: {response.json()}")

    @pytest.mark.asyncio
    async def test_sead_tables_step_by_step(self, client):
        """Step-by-step debugging test.
        
        Run with: PYTHONPATH=.:backend uv run pytest backend/tests/test_schema_endpoints.py::TestDebugSeadTables::test_sead_tables_step_by_step -v -s --pdb
        """
        # Step 1: Check health endpoint
        health_response = client.get("/api/v1/health")
        print(f"\n1. Health check: {health_response.status_code}")
        assert health_response.status_code == 200
        
        # Step 2: List configurations to verify data source exists
        config_response = client.get("/api/v1/configurations")
        print(f"2. Configurations: {config_response.status_code}")
        
        if config_response.status_code == 200:
            configs = config_response.json()
            print(f"   Available configs: {[c['name'] for c in configs]}")
        
        # Step 3: Try to list tables
        print("3. Attempting to list tables for 'sead' data source...")
        tables_response = client.get("/api/v1/data-sources/sead/tables")
        
        print(f"   Status: {tables_response.status_code}")
        print(f"   Body: {tables_response.text[:500]}")  # First 500 chars
        
        # Add breakpoint here for debugging
        import pdb; pdb.set_trace()
        
        # Analyze the response
        if tables_response.status_code == 200:
            tables = tables_response.json()
            print(f"   Success! Found {len(tables)} tables")
        elif tables_response.status_code == 404:
            print(f"   Error 404: Data source not found")
            print(f"   Detail: {tables_response.json()}")
        elif tables_response.status_code == 400:
            print(f"   Error 400: Bad request or not supported")
            print(f"   Detail: {tables_response.json()}")
        else:
            print(f"   Error {tables_response.status_code}")
            print(f"   Detail: {tables_response.json()}")


class TestInvalidateCache:
    """Tests for POST /data-sources/{name}/cache/invalidate endpoint."""

    @pytest.mark.asyncio
    async def test_invalidate_cache_success(self, client, mock_schema_service):
        """Test successful cache invalidation."""
        mock_schema_service.invalidate_cache = MagicMock()
        
        with patch('backend.app.api.dependencies.get_schema_service', return_value=mock_schema_service):
            response = client.post("/api/v1/data-sources/sead/cache/invalidate")
        
        assert response.status_code == 204
        mock_schema_service.invalidate_cache.assert_called_once_with("sead")
