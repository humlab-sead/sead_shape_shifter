"""Adapters from authenticated request state to authorization principals."""

from datetime import UTC, datetime

from fastapi import HTTPException, Request

from backend.app.authorization.models import Principal


class AuthenticationAdapter:
    """Convert trusted-proxy identity state into a stable principal."""

    def __init__(
        self,
        *,
        enabled: bool,
        environment: str,
        development_principal_id: str | None = None,
        groups_enabled: bool = False,
    ) -> None:
        self.enabled = enabled
        self.environment = environment
        self.development_principal_id = development_principal_id
        self.groups_enabled = groups_enabled

    def principal_from_request(self, request: Request) -> Principal:
        """Return the request principal or raise the standard authentication response."""
        principal_id = getattr(request.state, "authenticated_user", None)
        provider = "trusted-proxy"
        if principal_id is None and not self.enabled and self.environment in {"development", "test"}:
            principal_id = self.development_principal_id
            provider = "development"
        if not principal_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        group_ids = getattr(request.state, "authenticated_groups", ()) if self.groups_enabled else ()
        if not isinstance(group_ids, (tuple, list, set, frozenset)) or any(
            not isinstance(group, str) or not group.strip() for group in group_ids
        ):
            raise HTTPException(status_code=401, detail="Invalid authenticated groups")
        return Principal(
            principal_id=principal_id,
            authentication_provider=provider,
            authenticated_at=datetime.now(UTC),
            group_ids=frozenset(group.strip() for group in group_ids),
        )
