"""Request correlation ID middleware for tracing concurrent requests.

Assigns a unique short ID to each HTTP request, stored in a ContextVar
so all downstream code (services, state manager, caches) can include it
in log messages. This is essential for diagnosing interleaved concurrent
request issues (e.g. lost-update race conditions on entity creation).
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable accessible from any downstream code in the same async context
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="no-corr")


def get_correlation_id() -> str:
    """Get the current request's correlation ID.

    Returns a short identifier for the current request, or 'no-corr'
    if called outside a request context (e.g., during startup or tests).
    """
    return correlation_id_var.get()


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Assigns a unique correlation ID to each HTTP request.

    The ID is:
    - Read from the incoming X-Correlation-ID header (if present), or
    - Generated as a short UUID4 prefix (8 chars).

    It is set as a ContextVar for downstream logging and returned
    in the response X-Correlation-ID header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id: str = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
        token = correlation_id_var.set(req_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Correlation-ID"] = req_id
            return response
        finally:
            correlation_id_var.reset(token)
