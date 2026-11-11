"""HTTP client for OpenRefine reconciliation service API."""

import json
import time
from copy import deepcopy
from typing import Any

import httpx
from loguru import logger
from pydantic import ValidationError

from backend.app.models.reconciliation import (
    CandidateVerificationRequestItem,
    CandidateVerificationResponse,
    CandidateVerificationResult,
    ReconciliationCandidate,
)

_CANDIDATE_VERIFICATION_BATCH_SIZE = 100
_SERVICE_MANIFEST_CACHE_TTL_SECONDS = 30
_SERVICE_MANIFEST_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


class CandidateVerificationUnavailableError(Exception):
    """Raised when the Authority Service or its SEAD database is unavailable."""


class CandidateVerificationProtocolError(Exception):
    """Raised when the Authority Service returns an invalid verification response."""


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
            logger.debug(f"Creating new httpx.AsyncClient with timeout={self.timeout}s")
            self._client = httpx.AsyncClient(timeout=self.timeout)
            logger.debug(f"Client created successfully for base_url={self.base_url}")
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def verify_candidates(self, items: list[CandidateVerificationRequestItem]) -> list[CandidateVerificationResult]:
        """Check candidate URIs in ordered batches of at most 100."""
        if not items:
            return []

        client = await self._get_client()
        verified: list[CandidateVerificationResult] = []
        for offset in range(0, len(items), _CANDIDATE_VERIFICATION_BATCH_SIZE):
            batch = items[offset : offset + _CANDIDATE_VERIFICATION_BATCH_SIZE]
            try:
                response = await client.post(
                    f"{self.base_url}/reconcile/verify-candidates",
                    json={"items": [item.model_dump() for item in batch]},
                )
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise CandidateVerificationUnavailableError("The Authority Service is unavailable") from exc
            except httpx.HTTPError as exc:
                raise CandidateVerificationProtocolError("The Authority Service request failed") from exc

            if response.status_code == 503:
                raise CandidateVerificationUnavailableError("The Authority Service cannot access the SEAD database")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise CandidateVerificationProtocolError(f"The Authority Service returned HTTP {response.status_code}") from exc

            try:
                response_data = response.json()
            except ValueError as exc:
                raise CandidateVerificationProtocolError("The Authority Service returned invalid JSON") from exc

            try:
                parsed_response = CandidateVerificationResponse.model_validate(response_data)
            except ValidationError as exc:
                raise CandidateVerificationProtocolError("The Authority Service returned an invalid candidate-check response") from exc

            if len(parsed_response.results) != len(batch):
                raise CandidateVerificationProtocolError("The Authority Service returned a different number of candidate results")

            for requested, result in zip(batch, parsed_response.results, strict=True):
                if result.type != requested.type or result.id != requested.id:
                    raise CandidateVerificationProtocolError("The Authority Service returned candidate results in a different order")
                if result.outcome == "unsupported_type":
                    raise CandidateVerificationProtocolError(f"The Authority Service does not support candidate type {result.type!r}")

            verified.extend(parsed_response.results)

        return verified

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

        logger.info(f"[RECON] Starting batch reconciliation: {len(queries)} queries")
        logger.debug(f"[RECON] Query IDs: {list(queries.keys())}")
        logger.debug(f"[RECON] Target URL: {self.base_url}/reconcile")
        logger.debug(f"[RECON] Timeout: {self.timeout}s")
        logger.debug(f"[RECON] Request payload: {queries_json}")

        try:
            client: httpx.AsyncClient = await self._get_client()
            logger.debug("[RECON] Client obtained, making POST request...")

            endpoint_url = f"{self.base_url}/reconcile"
            logger.debug(f"[RECON] POST {endpoint_url}")

            response: httpx.Response = await client.post(endpoint_url, data={"queries": queries_json})

            logger.debug(f"[RECON] Response body: {response.text}")

            logger.debug(f"[RECON] Response received: status={response.status_code}")
            logger.debug(f"[RECON] Response headers: {dict(response.headers)}")

            response.raise_for_status()
            logger.debug("[RECON] Response status OK")
        except httpx.ConnectError as e:
            logger.error(f"[RECON] Connection failed to {self.base_url}: {type(e).__name__}: {e}")
            logger.error(f"[RECON] Connection error details: {e.__class__.__module__}.{e.__class__.__name__}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.error(f"[RECON] Underlying cause: {type(e.__cause__).__name__}: {e.__cause__}")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"[RECON] Request timeout after {self.timeout}s: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"[RECON] HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            raise
        except Exception as e:
            logger.error(f"[RECON] Unexpected error during batch reconciliation: {type(e).__name__}: {e}")
            logger.exception("[RECON] Full traceback:")
            raise

        # Parse response
        logger.debug("[RECON] Parsing response data...")
        results: dict[str, list[ReconciliationCandidate]] = {}

        try:
            response_data: dict[str, Any] = response.json()
            logger.debug(f"[RECON] Response parsed successfully, {len(response_data)} query results")
        except Exception as e:
            logger.error(f"[RECON] Failed to parse JSON response: {e}")
            logger.error(f"[RECON] Response text: {response.text[:500]}")
            raise

        for qid, result in response_data.items():
            candidates = []
            for candidate_data in result.get("result", []):
                candidates.append(ReconciliationCandidate(**candidate_data))
            results[qid] = candidates

        logger.info(
            f"[RECON] Batch reconciliation completed: {len(results)} queries, " f"{sum(len(c) for c in results.values())} total candidates"
        )

        return results

    async def check_health(self) -> dict[str, Any]:
        """
        Check if reconciliation service is available.

        Returns:
            dict with status and service metadata

        Raises:
            httpx.HTTPError: If service is unreachable
        """
        logger.debug(f"[RECON] Health check: {self.base_url}/reconcile")
        try:
            client: httpx.AsyncClient = await self._get_client()
            logger.debug("[RECON] Sending GET request to health endpoint...")

            response: httpx.Response = await client.get(f"{self.base_url}/reconcile")
            logger.debug(f"[RECON] Health check response: status={response.status_code}")

            response.raise_for_status()

            # OpenRefine returns service metadata on GET
            data = response.json()
            logger.info(f"[RECON] Service is ONLINE: {data.get('name', 'Unknown')}")
            return {"status": "online", "service_name": data.get("name", "Unknown"), "service_url": self.base_url}
        except httpx.ConnectError as e:
            logger.error(f"[RECON] Health check - Connection failed: {type(e).__name__}: {e}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.error(f"[RECON] Health check - Underlying cause: {type(e.__cause__).__name__}: {e.__cause__}")
            return {"status": "offline", "service_url": self.base_url, "error": f"Connection failed: {e}"}
        except httpx.TimeoutException as e:
            logger.error(f"[RECON] Health check - Timeout after {self.timeout}s: {e}")
            return {"status": "offline", "service_url": self.base_url, "error": f"Timeout: {e}"}
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"[RECON] Health check - Unexpected error: {type(e).__name__}: {e}")
            logger.exception("[RECON] Health check - Full traceback:")
            return {"status": "offline", "service_url": self.base_url, "error": str(e)}

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

        logger.debug(f"[RECON] Fetching entity suggestions for prefix: {prefix}, type: {entity_type}")
        logger.debug(f"[RECON] Suggest endpoint: {self.base_url}/suggest/entity")
        logger.debug(f"[RECON] Suggest params: {params}")

        try:
            client: httpx.AsyncClient = await self._get_client()
            response: httpx.Response = await client.get(f"{self.base_url}/suggest/entity", params=params)
            logger.debug(f"[RECON] Suggest response: status={response.status_code}")
            logger.debug(f"[RECON] Suggest response body: {response.text}")
            response.raise_for_status()

            candidates = []
            for item in response.json().get("result", []):
                candidates.append(ReconciliationCandidate(**item))

            logger.debug(f"[RECON] Suggestions retrieved: {len(candidates)} candidates")
            return candidates[:limit]
        except Exception as e:
            logger.error(f"[RECON] Entity suggestion failed: {type(e).__name__}: {e}")
            raise

    async def get_entity_preview(self, entity_id: str) -> dict[str, Any]:
        """
        Get HTML preview for entity.

        Args:
            entity_id: Entity URI

        Returns:
            dict with 'id' and 'html' keys
        """
        logger.debug(f"[RECON] Fetching entity preview for id: {entity_id}")
        client: httpx.AsyncClient = await self._get_client()
        response: httpx.Response = await client.get(f"{self.base_url}/flyout/entity", params={"id": entity_id})
        logger.debug(f"[RECON] Preview response: status={response.status_code}")
        logger.debug(f"[RECON] Preview response body: {response.text}")
        response.raise_for_status()
        return response.json()

    async def get_service_manifest(self) -> dict[str, Any]:
        """
        Get reconciliation service metadata.

        Returns:
            Service manifest with supported types and configuration
        """
        now = time.monotonic()
        cached_manifest = _SERVICE_MANIFEST_CACHE.get(self.base_url)
        if cached_manifest and now < cached_manifest[0]:
            logger.debug(f"[RECON] Returning cached service manifest for {self.base_url}")
            return deepcopy(cached_manifest[1])

        logger.debug("[RECON] Fetching service manifest")
        client: httpx.AsyncClient = await self._get_client()
        response: httpx.Response = await client.get(f"{self.base_url}/reconcile")
        logger.debug(f"[RECON] Manifest response: status={response.status_code}")
        logger.debug(f"[RECON] Manifest response body: {response.text}")
        response.raise_for_status()
        manifest = response.json()
        if isinstance(manifest, dict):
            _SERVICE_MANIFEST_CACHE[self.base_url] = (
                time.monotonic() + _SERVICE_MANIFEST_CACHE_TTL_SECONDS,
                deepcopy(manifest),
            )
        return manifest
