"""Helpers for writing untrusted values to server logs."""

from __future__ import annotations

import asyncio
import re

MAX_ERROR_SUMMARY_LENGTH = 300

_SECRET_PATTERNS = (
    # Password in a connection URL, such as postgresql+psycopg://user:password@host
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://[^:/\s@]*:)[^@\s]+(@)"), r"\1[REDACTED]\2"),
    # key=value and key: value, with a quoted or unquoted value
    (
        re.compile(r"""(?i)((?:password|passwd|pwd|token|secret|api[_-]?key)["']?\s*[=:]\s*)(?:"[^"]*"|'[^']*'|[^\s&;,}]+)"""),
        r"\1[REDACTED]",
    ),
)


def sanitize_log_value(value: object) -> str:
    """Return a single-line log value with common credentials redacted."""
    sanitized = str(value)
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized.replace("\r", "\\r").replace("\n", "\\n")


def summarize_error_text(text: str) -> str:
    """Return the sanitized first line of an error message, limited in length.

    Later lines are dropped because database drivers put SQL text and parameter values there.
    """
    lines = text.strip().splitlines()
    first_line = lines[0].split("[SQL:")[0].strip() if lines else ""
    return sanitize_log_value(first_line)[:MAX_ERROR_SUMMARY_LENGTH]


def describe_exception(error: BaseException) -> str:
    """Return the type and first message line of the error that started an exception chain."""
    root = error
    seen = {id(root)}
    while (previous := root.__cause__ or root.__context__) is not None:
        # asyncio.wait_for raises TimeoutError from CancelledError, which says nothing about the cause.
        if id(previous) in seen or isinstance(previous, asyncio.CancelledError):
            break
        seen.add(id(previous))
        root = previous
    return f"{type(root).__name__}: {summarize_error_text(str(root))}"
