"""Shared helpers for formatting human-readable validation messages."""

from typing import Any


def format_validation_message_with_context(
    *,
    message: str,
    entity: str | None = None,
    field: str | None = None,
    expression: Any | None = None,
) -> str:
    """Prefix a message with entity and field context and append expression details when available."""
    if entity and field:
        prefix = f"Entity '{entity}', field '{field}': "
    elif entity:
        prefix = f"Entity '{entity}': "
    elif field:
        prefix = f"Field '{field}': "
    else:
        prefix = ""

    formatted = f"{prefix}{message}" if prefix else message
    if expression is not None and "Expression:" not in formatted:
        formatted = f"{formatted}. Expression: {expression!r}"
    return formatted
