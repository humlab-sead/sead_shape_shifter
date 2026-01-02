"""HTTP client for OpenRefine reconciliation service API."""

import json
from typing import Any

import httpx
from loguru import logger

from backend.app.models.reconciliation import ReconciliationCandidate


class ReconciliationQuery:
    """Query for reconciliation service."""

    def __init__(
        self,
        query: str,
        entity_type: str,
        limit: int = 10,
        properties: list[dict[str, Any]] | None = None,
    ):
        self.query: str = query
        self.type: str = entity_type
        self.limit: int = limit
        self.properties: list[dict[str, Any]] = properties or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to OpenRefine query format."""
        result: dict[str, Any] = {"query": self.query, "type": self.type, "limit": self.limit}
        if self.properties:
            result["properties"] = self.properties
        return result


class ReconciliationClient:
    """Client for SEAD OpenRefine reconciliation service."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize reconciliation client.

        Args:
            base_url: Base URL of reconciliation service
            timeout: Request timeout in seconds
        """
        self.base_url: str = base_url.rstrip("/")
        self.timeout: float = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def reconcile_batch(self, queries: dict[str, ReconciliationQuery]) -> dict[str, list[ReconciliationCandidate]]:
        """
        Batch reconcile multiple queries.

        Args:
            queries: dict of query_id -> ReconciliationQuery

        Returns:
            dict of query_id -> list of candidates

        Raises:
            httpx.HTTPError: If reconciliation service request fails
        """
        # Format queries for OpenRefine API
        formatted_queries: dict[str, dict[str, Any]] = {qid: q.to_dict() for qid, q in queries.items()}

        # OpenRefine expects queries as a JSON string in form data
        queries_json: str = json.dumps(formatted_queries)

        logger.debug(f"Reconciling {len(queries)} queries: {list(queries.keys())}")

        client: httpx.AsyncClient = await self._get_client()
        response: httpx.Response = await client.post(f"{self.base_url}/reconcile", data={"queries": queries_json})
        response.raise_for_status()

        # Parse response
        results: dict[str, list[ReconciliationCandidate]] = {}
        response_data: dict[str, Any] = response.json()

        for qid, result in response_data.items():
            candidates = []
            for candidate_data in result.get("result", []):
                candidates.append(ReconciliationCandidate(**candidate_data))
            results[qid] = candidates

        logger.info(f"Reconciliation completed: {len(results)} queries, " f"{sum(len(c) for c in results.values())} total candidates")

        return results

    async def check_health(self) -> dict[str, Any]:
        """
        Check if reconciliation service is available.

        Returns:
            dict with status and service metadata

        Raises:
            httpx.HTTPError: If service is unreachable
        """
        try:
            client: httpx.AsyncClient = await self._get_client()
            response: httpx.Response = await client.get(f"{self.base_url}/reconcile")
            response.raise_for_status()
            
            # OpenRefine returns service metadata on GET
            data = response.json()
            return {
                "status": "online",
                "service_name": data.get("name", "Unknown"),
                "service_url": self.base_url
            }
        except Exception as e:
            logger.warning(f"Reconciliation service health check failed: {e}")
            return {
                "status": "offline",
                "service_url": self.base_url,
                "error": str(e)
            }

    async def suggest_entities(self, prefix: str, entity_type: str | None = None, limit: int = 10) -> list[ReconciliationCandidate]:
        """
        Get entity suggestions for autocomplete.

        Args:
            prefix: Text to match
            entity_type: Optional type filter ("site", "taxon", "location")
            limit: Maximum number of suggestions

        Returns:
            list of matching candidates
        """
        params: dict[str, Any] = {"prefix": prefix}
        if entity_type:
            params["type"] = entity_type

        logger.debug(f"Fetching entity suggestions for prefix: {prefix}, type: {entity_type}")

        client: httpx.AsyncClient = await self._get_client()
        response: httpx.Response = await client.get(f"{self.base_url}/suggest/entity", params=params)
        response.raise_for_status()

        candidates = []
        for item in response.json().get("result", []):
            candidates.append(ReconciliationCandidate(**item))

        return candidates[:limit]

    async def get_entity_preview(self, entity_id: str) -> dict[str, Any]:
        """
        Get HTML preview for entity.

        Args:
            entity_id: Entity URI

        Returns:
            dict with 'id' and 'html' keys
        """
        client: httpx.AsyncClient = await self._get_client()
        response: httpx.Response = await client.get(f"{self.base_url}/flyout/entity", params={"id": entity_id})
        response.raise_for_status()
        return response.json()

    async def get_service_manifest(self) -> dict[str, Any]:
        """
        Get reconciliation service metadata.

        Returns:
            Service manifest with supported types and configuration
        """
        client: httpx.AsyncClient = await self._get_client()
        response: httpx.Response = await client.get(f"{self.base_url}/reconcile")
        response.raise_for_status()
        return response.json()
