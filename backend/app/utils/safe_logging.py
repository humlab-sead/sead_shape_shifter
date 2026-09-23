"""Helpers for writing untrusted values to server logs."""

from __future__ import annotations

import re

_SECRET_PATTERNS = (
    (re.compile(r"(?i)(password|passwd|pwd|token|secret|api[_-]?key)=([^\s&;,]+)"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)(postgres(?:ql)?://[^:/\s]+:)[^@\s]+(@)"), r"\1[REDACTED]\2"),
)


def sanitize_log_value(value: object) -> str:
    """Return a single-line log value with common credentials redacted."""
    sanitized = str(value)
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized.replace("\r", "\\r").replace("\n", "\\n")
