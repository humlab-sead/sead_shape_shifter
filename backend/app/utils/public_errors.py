"""Helpers for public-facing error messages."""

from __future__ import annotations

from backend.app.middleware.correlation import get_correlation_id


def public_error_detail(action: str) -> str:
    """Return a stable public error message with the current correlation ID."""

    correlation_id = get_correlation_id()
    return f"{action}. Correlation ID: {correlation_id}"
