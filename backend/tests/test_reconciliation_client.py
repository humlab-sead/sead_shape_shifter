"""Unit tests for ReconciliationClient.

Tests cover:
- ReconciliationQuery initialization and to_dict conversion
- ReconciliationClient HTTP operations
- Batch reconciliation with OpenRefine API format
- Entity suggestion with autocomplete
- Entity preview fetching
- Service manifest retrieval
- Client lifecycle (creation and cleanup)
- Error handling for HTTP failures
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.app.clients.reconciliation_client import ReconciliationClient, ReconciliationQuery
from backend.app.models.reconciliation import ReconciliationCandidate
from utility import R

# pylint: disable=redefined-outer-name

RECONCILIATION_SERVICE_URL = "http://localhost:8000"

class TestReconciliationQuery:
    """Tests for ReconciliationQuery class."""

    def test_basic_query_initialization(self):
        """Test creating a basic reconciliation query."""
        query = ReconciliationQuery(query="Test Site", entity_type="Site", limit=5)

        assert query.query == "Test Site"
        assert query.type == "Site"
        assert query.limit == 5
        assert query.properties == []

    def test_query_with_properties(self):
        """Test query with property filters."""
        props = [{"pid": "latitude", "v": 60.0}, {"pid": "longitude", "v": 15.0}]
        query = ReconciliationQuery(query="Site Name", entity_type="Site", properties=props)

        assert query.properties == props

    def test_to_dict_basic(self):
        """Test converting basic query to dict format."""
        query = ReconciliationQuery(query="Test", entity_type="Site", limit=10)
        result = query.to_dict()

        assert result == {"query": "Test", "type": "Site", "limit": 10}

    def test_to_dict_with_properties(self):
        """Test converting query with properties to dict."""
        props = [{"pid": "location", "v": "Sweden"}]
        query = ReconciliationQuery(query="Site", entity_type="Site", limit=5, properties=props)
        result = query.to_dict()

        assert result["properties"] == props
        assert "query" in result
        assert "type" in result
        assert "limit" in result

    def test_to_dict_no_properties(self):
        """Test that empty properties list is included in dict."""
        query = ReconciliationQuery(query="Test", entity_type="Site", limit=10, properties=[])
        result = query.to_dict()

        # Empty list should not be included
        assert "properties" not in result

    def test_default_limit(self):
        """Test default limit value."""
        query = ReconciliationQuery(query="Test", entity_type="Site")
        assert query.limit == 10


class TestReconciliationClient:
    """Tests for ReconciliationClient class."""

    def test_client_initialization(self):
        """Test client initialization with base URL."""
        client = ReconciliationClient(base_url=f"{RECONCILIATION_SERVICE_URL}/reconcile")

        assert client.base_url == f"{RECONCILIATION_SERVICE_URL}/reconcile"
        assert client.timeout == 30.0
        assert client._client is None

    def test_client_initialization_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        client = ReconciliationClient(base_url=f"{RECONCILIATION_SERVICE_URL}/reconcile/")

        assert client.base_url == f"{RECONCILIATION_SERVICE_URL}/reconcile"

    def test_client_custom_timeout(self):
        """Test client with custom timeout."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL, timeout=60.0)

        assert client.timeout == 60.0

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self):
        """Test that _get_client creates HTTP client."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        http_client = await client._get_client()

        assert http_client is not None
        assert isinstance(http_client, httpx.AsyncClient)
        assert client._client is http_client

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self):
        """Test that _get_client reuses existing client."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        http_client1 = await client._get_client()
        http_client2 = await client._get_client()

        assert http_client1 is http_client2

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self):
        """Test that close properly cleans up HTTP client."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        # Create client
        await client._get_client()
        assert client._client is not None

        # Close
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        """Test that close works when no client exists."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        # Should not raise
        await client.close()
        assert client._client is None


class TestReconciliationClientBatchReconcile:
    """Tests for ReconciliationClient.reconcile_batch method."""

    @pytest.mark.asyncio
    async def test_reconcile_batch_basic(self):
        """Test basic batch reconciliation."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        queries = {
            "q0": ReconciliationQuery(query="SITE001", entity_type="Site", limit=3),
            "q1": ReconciliationQuery(query="SITE002", entity_type="Site", limit=3),
        }

        mock_response = {
            "q0": {
                "result": [
                    {"id": "site_1", "name": "Site 001", "score": 95.5, "match": True},
                    {"id": "site_2", "name": "Site 001 Backup", "score": 85.0, "match": False},
                ]
            },
            "q1": {"result": [{"id": "site_3", "name": "Site 002", "score": 98.0, "match": True}]},
        }

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.post.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.reconcile_batch(queries)

            assert len(result) == 2
            assert "q0" in result
            assert "q1" in result

            # Check q0 results
            assert len(result["q0"]) == 2
            assert isinstance(result["q0"][0], ReconciliationCandidate)
            assert result["q0"][0].id == "site_1"
            assert result["q0"][0].name == "Site 001"
            assert result["q0"][0].score == 95.5
            assert result["q0"][0].match is True

            # Check q1 results
            assert len(result["q1"]) == 1
            assert result["q1"][0].id == "site_3"

        await client.close()

    @pytest.mark.asyncio
    async def test_reconcile_batch_empty_results(self):
        """Test batch reconciliation with no matches."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        queries = {"q0": ReconciliationQuery(query="UNKNOWN", entity_type="Site")}

        mock_response = {"q0": {"result": []}}

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.post.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.reconcile_batch(queries)

            assert len(result) == 1
            assert result["q0"] == []

        await client.close()

    @pytest.mark.asyncio
    async def test_reconcile_batch_http_error(self):
        """Test batch reconciliation handles HTTP errors."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        queries = {"q0": ReconciliationQuery(query="Test", entity_type="Site")}

        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("500 Server Error", request=MagicMock(), response=MagicMock())
        )
        mock_http_client.post.return_value = mock_response

        with patch.object(client, "_get_client", return_value=mock_http_client):
            with pytest.raises(httpx.HTTPStatusError):
                await client.reconcile_batch(queries)

        await client.close()

    @pytest.mark.asyncio
    async def test_reconcile_batch_calls_correct_endpoint(self):
        """Test that reconcile_batch calls the correct API endpoint."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        queries = {"q0": ReconciliationQuery(query="Test", entity_type="Site")}
        mock_response = {"q0": {"result": []}}

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.post.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            await client.reconcile_batch(queries)

            # Verify correct endpoint was called
            mock_http_client.post.assert_called_once()
            call_args = mock_http_client.post.call_args
            assert call_args[0][0] == f"{RECONCILIATION_SERVICE_URL}/reconcile"

        await client.close()

    @pytest.mark.asyncio
    async def test_reconcile_batch_with_properties(self):
        """Test batch reconciliation with property filters."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        queries = {"q0": ReconciliationQuery(query="Site Name", entity_type="Site", properties=[{"pid": "latitude", "v": 60.0}])}

        mock_response = {"q0": {"result": [{"id": "site_1", "name": "Site Name", "score": 100.0, "match": True}]}}

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.post.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.reconcile_batch(queries)

            assert len(result["q0"]) == 1
            assert result["q0"][0].score == 100.0

        await client.close()


class TestReconciliationClientSuggestEntities:
    """Tests for ReconciliationClient.suggest_entities method."""

    @pytest.mark.asyncio
    async def test_suggest_entities_basic(self):
        """Test basic entity suggestion."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_response = {
            "result": [
                {"id": "site_1", "name": "Site Alpha", "score": 90.0, "match": False},
                {"id": "site_2", "name": "Site Beta", "score": 85.0, "match": False},
            ]
        }

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.suggest_entities(prefix="Site", limit=10)

            assert len(result) == 2
            assert isinstance(result[0], ReconciliationCandidate)
            assert result[0].id == "site_1"
            assert result[0].name == "Site Alpha"

        await client.close()

    @pytest.mark.asyncio
    async def test_suggest_entities_with_type_filter(self):
        """Test entity suggestion with type filter."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_response = {"result": [{"id": "site_1", "name": "Test Site", "score": 95.0, "match": False}]}

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.suggest_entities(prefix="Test", entity_type="Site", limit=5)

            assert len(result) == 1
            # Verify type parameter was passed
            mock_http_client.get.assert_called_once()
            call_args = mock_http_client.get.call_args
            assert call_args[1]["params"]["type"] == "Site"

        await client.close()

    @pytest.mark.asyncio
    async def test_suggest_entities_limit_enforcement(self):
        """Test that suggestion limit is enforced."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        # Return more results than limit
        mock_response = {"result": [{"id": f"site_{i}", "name": f"Site {i}", "score": 90.0 - i, "match": False} for i in range(20)]}

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = AsyncMock(json=lambda: mock_response, raise_for_status=lambda: None)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.suggest_entities(prefix="Site", limit=5)

            # Should be limited to 5
            assert len(result) == 5

        await client.close()

    @pytest.mark.asyncio
    async def test_suggest_entities_empty_results(self):
        """Test entity suggestion with no matches."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_response = {"result": []}

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.suggest_entities(prefix="NONEXISTENT")

            assert result == []

        await client.close()

    @pytest.mark.asyncio
    async def test_suggest_entities_http_error(self):
        """Test entity suggestion handles HTTP errors."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("404 Not Found", request=MagicMock(), response=MagicMock())
        )
        mock_http_client.get.return_value = mock_response

        with patch.object(client, "_get_client", return_value=mock_http_client):
            with pytest.raises(httpx.HTTPStatusError):
                await client.suggest_entities(prefix="Test")

        await client.close()


class TestReconciliationClientEntityPreview:
    """Tests for ReconciliationClient.get_entity_preview method."""

    @pytest.mark.asyncio
    async def test_get_entity_preview_basic(self):
        """Test getting entity preview."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_response = {"id": "site_123", "html": "<div>Site preview content</div>"}

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.get_entity_preview(entity_id="site_123")

            assert result["id"] == "site_123"
            assert "html" in result
            assert "Site preview content" in result["html"]

        await client.close()

    @pytest.mark.asyncio
    async def test_get_entity_preview_calls_correct_endpoint(self):
        """Test that get_entity_preview calls correct endpoint."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_response = {"id": "site_1", "html": "<div>Preview</div>"}

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            await client.get_entity_preview(entity_id="site_1")

            # Verify correct endpoint
            mock_http_client.get.assert_called_once()
            call_args = mock_http_client.get.call_args
            assert call_args[0][0] == f"{RECONCILIATION_SERVICE_URL}/flyout/entity"
            assert call_args[1]["params"]["id"] == "site_1"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_entity_preview_http_error(self):
        """Test entity preview handles HTTP errors."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("500 Server Error", request=MagicMock(), response=MagicMock())
        )
        mock_http_client.get.return_value = mock_response

        with patch.object(client, "_get_client", return_value=mock_http_client):
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_entity_preview(entity_id="invalid_id")

        await client.close()


class TestReconciliationClientServiceManifest:
    """Tests for ReconciliationClient.get_service_manifest method."""

    @pytest.mark.asyncio
    async def test_get_service_manifest_basic(self):
        """Test getting service manifest."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_response = {
            "name": "SEAD Reconciliation Service",
            "identifierSpace": "http://sead.se/entity/",
            "schemaSpace": "http://sead.se/schema/",
            "defaultTypes": [
                {"id": "Site", "name": "Site"},
                {"id": "Taxon", "name": "Taxon"},
            ],
        }

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.get_service_manifest()

            assert result["name"] == "SEAD Reconciliation Service"
            assert "defaultTypes" in result
            assert len(result["defaultTypes"]) == 2

        await client.close()

    @pytest.mark.asyncio
    async def test_get_service_manifest_calls_correct_endpoint(self):
        """Test that get_service_manifest calls correct endpoint."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_response = {"name": "Test Service"}

        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(return_value=mock_response)
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            await client.get_service_manifest()

            # Verify correct endpoint
            mock_http_client.get.assert_called_once()
            call_args = mock_http_client.get.call_args
            assert call_args[0][0] == f"{RECONCILIATION_SERVICE_URL}/reconcile"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_service_manifest_http_error(self):
        """Test service manifest handles HTTP errors."""
        client = ReconciliationClient(base_url=RECONCILIATION_SERVICE_URL)

        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("503 Service Unavailable", request=MagicMock(), response=MagicMock())
        )
        mock_http_client.get.return_value = mock_response

        with patch.object(client, "_get_client", return_value=mock_http_client):
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_service_manifest()

        await client.close()
