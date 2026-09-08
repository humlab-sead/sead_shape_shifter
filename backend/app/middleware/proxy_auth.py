"""Authentication middleware for identities asserted by a trusted reverse proxy."""

from collections.abc import Iterable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class ProxyAuthenticationMiddleware(BaseHTTPMiddleware):
    """Require a non-empty identity header supplied by the trusted reverse proxy."""

    def __init__(
        self,
        app,
        *,
        enabled: bool,
        header_name: str,
        groups_enabled: bool = False,
        groups_header_name: str = "X-Authenticated-Groups",
        public_paths: Iterable[str] = (),
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.header_name = header_name
        self.groups_enabled = groups_enabled
        self.groups_header_name = groups_header_name
        self.public_paths = frozenset(public_paths)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Reject protected requests without a valid proxy-authenticated identity."""
        if not self.enabled or request.url.path in self.public_paths:
            return await call_next(request)

        identity = request.headers.get(self.header_name)
        if identity is None:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        identity = identity.strip()
        if not identity or any(ord(character) < 32 for character in identity) or len(identity) > 255:
            return JSONResponse(status_code=401, content={"detail": "Invalid authenticated identity"})

        request.state.authenticated_user = identity
        if self.groups_enabled:
            groups_header = request.headers.get(self.groups_header_name, "")
            groups = tuple(group.strip() for group in groups_header.split(",") if group.strip())
            if any(any(ord(character) < 32 for character in group) or len(group) > 255 for group in groups):
                return JSONResponse(status_code=401, content={"detail": "Invalid authenticated groups"})
            request.state.authenticated_groups = groups
        return await call_next(request)
