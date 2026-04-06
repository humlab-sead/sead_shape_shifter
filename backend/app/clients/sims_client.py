"""HTTP client for the SIMS (SEAD Identity Management System) API.

Wraps the six /identity endpoints exposed by sead_authority_service:

  POST   /identity/resolve                                         Resolve + bind a batch
  GET    /identity/binding-sets/{uuid}                             Get binding set status
  POST   /identity/binding-sets/{uuid}/confirm                     Confirm a proposed binding set
  POST   /identity/binding-sets/{uuid}/change-request              Associate a Sqitch CR name
  POST   /identity/detect-change                                   Content-hash change detection
  GET    /identity/scopes                                          List known source scopes
"""

from __future__ import annotations

from uuid import UUID

import httpx
from loguru import logger

from backend.app.models.sims import (
    BindingSetResponse,
    ChangeDetectionRequest,
    ChangeDetectionResult,
    ResolveRequest,
    ResolveResponse,
    SourceScope,
)


class SimsClient:
    """Async HTTP client for the SIMS identity service."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialise SIMS client.

        Args:
            base_url: Base URL of sead_authority_service, e.g. 'http://localhost:8000'.
                      The client appends '/identity/...' paths automatically.
            timeout:  Request timeout in seconds.
        """
        self.base_url: str = base_url.rstrip("/")
        self.timeout: float = timeout
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        """Return the shared httpx client, creating it on first use."""
        if self._client is None:
            logger.debug(f"[SIMS] Creating httpx.AsyncClient timeout={self.timeout}s base={self.base_url}")
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self.base_url}/identity/{path.lstrip('/')}"

    async def _post(self, path: str, body: dict) -> dict:
        client = await self._get_client()
        url = self._url(path)
        logger.debug(f"[SIMS] POST {url}")
        response = await client.post(url, json=body)
        response.raise_for_status()
        return response.json()

    async def _get(self, path: str) -> dict | list:
        client = await self._get_client()
        url = self._url(path)
        logger.debug(f"[SIMS] GET {url}")
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Public API — mirrors sead_authority_service /identity endpoints
    # ------------------------------------------------------------------

    async def resolve(self, request: ResolveRequest) -> ResolveResponse:
        """Resolve and bind a batch of source identities (POST /identity/resolve).

        Idempotent: repeating the same request for the same scope produces the same
        Source Identity records and, if already bound, the same Tracked Identity UUIDs.

        Args:
            request: Batch resolve request containing scope, submission name, and per-entity signals.

        Returns:
            ResolveResponse with submission UUID, scope UUID, binding set, and per-entity outcomes.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses from the authority service.
        """
        data = await self._post("resolve", request.model_dump(mode="json"))
        return ResolveResponse.model_validate(data)

    async def get_binding_set(self, binding_set_uuid: UUID) -> BindingSetResponse:
        """Fetch the current state of a Binding Set (GET /identity/binding-sets/{uuid}).

        Args:
            binding_set_uuid: UUID returned by a previous :meth:`resolve` call.

        Returns:
            BindingSetResponse with lifecycle state and binding count.

        Raises:
            httpx.HTTPStatusError: 404 if the UUID is unknown.
        """
        data = await self._get(f"binding-sets/{binding_set_uuid}")
        return BindingSetResponse.model_validate(data)

    async def confirm_binding_set(self, binding_set_uuid: UUID) -> BindingSetResponse:
        """Manually confirm a proposed Binding Set (POST /identity/binding-sets/{uuid}/confirm).

        Applies to shared-metadata entities where ``auto_confirm`` is false.  Idempotent
        for sets already in *confirmed* state.

        Args:
            binding_set_uuid: UUID of the Binding Set to confirm.

        Returns:
            Updated BindingSetResponse.

        Raises:
            httpx.HTTPStatusError: 404 if the UUID is unknown.
        """
        data = await self._post(f"binding-sets/{binding_set_uuid}/confirm", {})
        return BindingSetResponse.model_validate(data)

    async def associate_change_request(self, binding_set_uuid: UUID, change_request_name: str) -> BindingSetResponse:
        """Link a Sqitch Change Request name to a confirmed Binding Set
        (POST /identity/binding-sets/{uuid}/change-request).

        Args:
            binding_set_uuid:     UUID of the *confirmed* Binding Set.
            change_request_name:  Sqitch change name, e.g. ``'deploy/2026-04/site-batch-1'``.

        Returns:
            Updated BindingSetResponse.

        Raises:
            httpx.HTTPStatusError: 404 if the UUID is unknown or set is not confirmed.
        """
        data = await self._post(
            f"binding-sets/{binding_set_uuid}/change-request",
            {"change_request_name": change_request_name},
        )
        return BindingSetResponse.model_validate(data)

    async def detect_change(self, request: ChangeDetectionRequest) -> ChangeDetectionResult:
        """Compare an incoming content hash against the stored hash for a Tracked Identity
        (POST /identity/detect-change).

        Returns ``insert`` (no prior hash), ``update`` (hash changed), or ``skip`` (hash unchanged).

        Args:
            request: Contains the ``tracked_identity_uuid`` and the new ``content_hash``.

        Returns:
            ChangeDetectionResult with outcome and the previously stored hash (if any).

        Raises:
            httpx.HTTPStatusError: 404 if the Tracked Identity UUID is unknown.
        """
        data = await self._post("detect-change", request.model_dump(mode="json"))
        return ChangeDetectionResult.model_validate(data)

    async def list_scopes(self) -> list[SourceScope]:
        """Return all registered Source Scopes (GET /identity/scopes).

        Returns:
            List of SourceScope records known to the authority service.
        """
        data = await self._get("scopes")
        return [SourceScope.model_validate(item) for item in data]
