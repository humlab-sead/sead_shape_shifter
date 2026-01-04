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

import socket
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.app.clients.reconciliation_client import ReconciliationClient, ReconciliationQuery
from backend.app.models.reconciliation import ReconciliationCandidate

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


class TestReconciliationClientConnection:
    """Tests for ReconciliationClient connection to OpenRefine service."""

    @pytest.mark.asyncio
    async def test_connection_to_port_8000(self):
        """Test that client can attempt connection to OpenRefine service on port 8000."""
        client = ReconciliationClient(base_url="http://localhost:8000")

        # Test health check endpoint
        health_result = await client.check_health()

        # Verify the client is configured for port 8000
        assert client.base_url == "http://localhost:8000"
        assert "status" in health_result
        assert "service_url" in health_result
        assert health_result["service_url"] == "http://localhost:8000"

        # Status can be either "online" or "offline" depending on whether service is running
        assert health_result["status"] in ["online", "offline"]

        # If offline, should have error message
        if health_result["status"] == "offline":
            assert "error" in health_result
        # If online, should have service name
        else:
            assert "service_name" in health_result

        await client.close()

    @pytest.mark.asyncio
    async def test_reconcile_batch_with_port_8000(self):
        """Test batch reconciliation attempting to connect to port 8000."""
        client = ReconciliationClient(base_url="http://localhost:8000/reconcile")

        queries = {"q0": ReconciliationQuery(query="Test Site", entity_type="Site", limit=3)}

        # This test verifies the client configuration, not actual connection
        # Mock the HTTP call to avoid dependency on running service
        mock_http_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json = MagicMock(
            return_value={"q0": {"result": [{"id": "site_1", "name": "Test Site", "score": 95.0, "match": True}]}}
        )
        mock_response_obj.raise_for_status = MagicMock()
        mock_http_client.post.return_value = mock_response_obj

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.reconcile_batch(queries)

            # Verify the endpoint is constructed correctly for port 8000
            mock_http_client.post.assert_called_once()
            call_args = mock_http_client.post.call_args
            assert call_args[0][0] == "http://localhost:8000/reconcile/reconcile"

            assert "q0" in result
            assert len(result["q0"]) == 1

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


# ============================================================================
# Integration Tests - Connect to Live Service
# ============================================================================
# These tests connect to the actual OpenRefine reconciliation service.
# Run with: pytest -v -s -m integration
# Skip with: pytest -v -m "not integration"
# ============================================================================


class TestReconciliationClientIntegration:
    """Integration tests that connect to live reconciliation service on port 8000.

    These tests are marked with @pytest.mark.integration and are skipped by default.
    To run them, use: pytest -v -s -m integration

    Make sure the OpenRefine reconciliation service is running on localhost:8000
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_health_check(self):
        """Test health check against live service on port 8000.

        This test attempts to connect to the actual service and reports detailed
        connection information. Check logs/endpoint_errors.log for [RECON] traces.
        """
        client = ReconciliationClient(base_url="http://localhost:8000", timeout=10.0)

        print("\n=== Testing Health Check ===")
        print(f"Target: {client.base_url}/reconcile")
        print(f"Timeout: {client.timeout}s")

        try:
            health = await client.check_health()

            print("\nHealth Check Result:")
            print(f"  Status: {health['status']}")
            print(f"  Service URL: {health['service_url']}")

            if health["status"] == "online":
                print(f"  Service Name: {health['service_name']}")
                assert health["service_name"] is not None
                print("\n✓ Service is ONLINE")
            else:
                print(f"  Error: {health.get('error', 'Unknown')}")
                print("\n✗ Service is OFFLINE")
                print("\nTroubleshooting:")
                print("  1. Verify service is running: docker ps | grep reconcile")
                print("  2. Check service logs: docker logs <container_id>")
                print("  3. Verify port mapping: docker port <container_id>")
                print("  4. Test direct connection: curl http://localhost:8000/reconcile")

            assert "status" in health

        except Exception as e:
            print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
            raise
        finally:
            await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_service_manifest(self):
        """Test getting service manifest from live service.

        Retrieves actual service metadata including supported entity types.
        """
        client = ReconciliationClient(base_url="http://localhost:8000", timeout=10.0)

        print("\n=== Testing Service Manifest ===")

        try:
            manifest = await client.get_service_manifest()

            print("\nManifest Retrieved:")
            print(f"  Service Name: {manifest.get('name', 'N/A')}")
            print(f"  Identifier Space: {manifest.get('identifierSpace', 'N/A')}")
            print(f"  Schema Space: {manifest.get('schemaSpace', 'N/A')}")

            if "defaultTypes" in manifest:
                print(f"\n  Supported Types ({len(manifest['defaultTypes'])}):")
                for entity_type in manifest["defaultTypes"][:5]:  # Show first 5
                    print(f"    - {entity_type.get('id', 'N/A')}: {entity_type.get('name', 'N/A')}")
                if len(manifest["defaultTypes"]) > 5:
                    print(f"    ... and {len(manifest['defaultTypes']) - 5} more")

            assert "name" in manifest
            print("\n✓ Service manifest retrieved successfully")

        except httpx.ConnectError as e:
            print(f"\n✗ Connection failed: {e}")
            print("\nService appears to be offline or unreachable")
            pytest.skip("Service not running")
        except Exception as e:
            print(f"\n✗ Error: {type(e).__name__}: {e}")
            raise
        finally:
            await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_reconcile_batch_single_query(self):
        """Test batch reconciliation with a single query against live service.

        Sends an actual reconciliation query to test the full request/response cycle.
        """
        client = ReconciliationClient(base_url="http://localhost:8000", timeout=10.0)

        print("\n=== Testing Batch Reconciliation ===")

        # Simple test query
        queries = {"q0": ReconciliationQuery(query="Test Site", entity_type="site", limit=3)}

        print(f"\nQuery: '{queries['q0'].query}'")
        print(f"Type: {queries['q0'].type}")
        print(f"Limit: {queries['q0'].limit}")

        try:
            result = await client.reconcile_batch(queries)

            print("\nReconciliation Result:")
            print(f"  Queries processed: {len(result)}")

            if "q0" in result:
                candidates = result["q0"]
                print(f"  Candidates found: {len(candidates)}")

                for i, candidate in enumerate(candidates[:3], 1):  # Show first 3
                    print(f"\n  Candidate {i}:")
                    print(f"    ID: {candidate.id}")
                    print(f"    Name: {candidate.name}")
                    print(f"    Score: {candidate.score}")
                    print(f"    Match: {candidate.match}")

            assert "q0" in result
            print("\n✓ Batch reconciliation completed successfully")

        except httpx.ConnectError as e:
            print(f"\n✗ Connection failed: {e}")
            print("\nCheck logs/endpoint_errors.log for [RECON] traces")
            pytest.skip("Service not running")
        except Exception as e:
            print(f"\n✗ Error: {type(e).__name__}: {e}")
            raise
        finally:
            await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_suggest_entities(self):
        """Test entity suggestions against live service.

        Tests autocomplete functionality with a simple prefix query.
        """
        client = ReconciliationClient(base_url="http://localhost:8000", timeout=10.0)

        print("\n=== Testing Entity Suggestions ===")

        prefix = "Site"
        print(f"\nPrefix: '{prefix}'")
        print("Limit: 5")

        try:
            suggestions = await client.suggest_entities(prefix=prefix, limit=5)

            print(f"\nSuggestions Retrieved: {len(suggestions)}")

            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n  Suggestion {i}:")
                print(f"    ID: {suggestion.id}")
                print(f"    Name: {suggestion.name}")
                print(f"    Score: {suggestion.score}")

            print("\n✓ Entity suggestions retrieved successfully")

        except httpx.ConnectError as e:
            print(f"\n✗ Connection failed: {e}")
            pytest.skip("Service not running")
        except Exception as e:
            print(f"\n✗ Error: {type(e).__name__}: {e}")
            raise
        finally:
            await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_connection_diagnostics(self):
        """Comprehensive connection diagnostics test.

        Performs multiple checks to diagnose connection issues:
        - Docker container port mapping check
        - DNS resolution
        - TCP connection
        - HTTP handshake
        - Service response

        This test provides detailed output for debugging connection problems.
        """

        print("\n=== Connection Diagnostics ===")

        host = "localhost"
        port = 8000
        timeout = 5.0

        # Test 0: Docker Port Mapping Check
        print("\n0. Docker Port Mapping Check:")
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.ID}}|{{.Image}}|{{.Ports}}"], capture_output=True, text=True, timeout=5, check=True
            )

            if result.returncode == 0:
                found_mapping = False
                found_container = False

                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) >= 3:
                        container_id, image, ports = parts[0], parts[1], parts[2]

                        # Check if port 8000 is mentioned
                        if "8000" in ports or "reconcile" in image.lower() or "openrefine" in image.lower():
                            found_container = True
                            print(f"\n   Container: {container_id[:12]}")
                            print(f"   Image: {image}")
                            print(f"   Ports: {ports}")

                            # Check if properly mapped to host
                            if "0.0.0.0:8000->8000" in ports or f"{host}:8000->8000" in ports:
                                found_mapping = True
                                print("   ✓ Port 8000 is MAPPED to host")
                            elif "8000/tcp" in ports and "->" not in ports:
                                print("   ✗ Port 8000 is EXPOSED but NOT MAPPED to host!")
                                print("\n   PROBLEM FOUND: Container has port 8000 but it's not published to host")
                                print("   Solution: Add port mapping when starting container:")
                                print("     docker run -p 8000:8000 ...")
                                print("   Or in docker-compose.yml:")
                                print("     ports:")
                                print('       - "8000:8000"')

                if not found_container:
                    print("   ⚠ No containers found with port 8000 or reconciliation service")
                elif not found_mapping:
                    print("\n   ⚠ WARNING: Container found but port not mapped to host")
                    pytest.skip("Docker port 8000 not mapped to host - see diagnostics above")

        except FileNotFoundError:
            print("   ⚠ Docker CLI not available, skipping container check")
        except Exception as e:  # pylint: disable=broad-except
            print(f"   ⚠ Could not check Docker containers: {e}")

        # Test 1: DNS Resolution
        print(f"\n1. DNS Resolution for '{host}':")
        try:
            ip_address = socket.gethostbyname(host)
            print(f"   ✓ Resolved to: {ip_address}")
        except socket.gaierror as e:
            print(f"   ✗ DNS resolution failed: {e}")
            pytest.fail(f"DNS resolution failed: {e}")

        # Test 2: TCP Connection
        print(f"\n2. TCP Connection to {host}:{port}:")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        port_open = False
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                print(f"   ✓ Port {port} is OPEN on host")
                port_open = True
            else:
                print(f"   ✗ Port {port} is CLOSED on host (error code: {result})")
                print("\n   Common causes:")
                print("   - Service running in Docker but port not mapped")
                print("   - Service not started")
                print("   - Firewall blocking connection")
                print("\n   Debug commands:")
                print(f"   - Check host port: lsof -i :{port}")
                print("   - Check Docker: docker ps --format '{{.Ports}}'")
                print("   - Check container logs: docker logs <container_id>")
                pytest.skip(f"Port {port} is not reachable on host")
        except socket.timeout:
            print(f"   ✗ Connection timeout after {timeout}s")
            pytest.skip("Connection timeout")
        except Exception as e:  # pylint: disable=broad-except
            print(f"   ✗ Connection error: {e}")
            pytest.skip(f"Connection error: {e}")
        finally:
            sock.close()

        # Test 3: HTTP Health Check
        if port_open:
            print("\n3. HTTP Health Check:")
            client = ReconciliationClient(base_url=f"http://{host}:{port}", timeout=timeout)
            try:
                health = await client.check_health()

                if health["status"] == "online":
                    print("   ✓ Service is ONLINE")
                    print(f"   ✓ Service Name: {health.get('service_name', 'Unknown')}")
                else:
                    print("   ✗ Service is OFFLINE")
                    print(f"   Error: {health.get('error', 'Unknown')}")

            except Exception as e:  # pylint: disable=broad-except
                print(f"   ✗ Health check failed: {type(e).__name__}: {e}")
            finally:
                await client.close()

        print("\n=== Diagnostics Complete ===")
        print("\nFor detailed traces, check:")
        print("  logs/endpoint_errors.log | grep '[RECON]'")
