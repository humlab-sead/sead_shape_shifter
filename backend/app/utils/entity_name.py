"""Validation rules for entity names created through the application."""

import re

from backend.app.exceptions import ConfigurationError

ENTITY_NAME_PATTERN = r"^[a-z][a-z0-9_]*$"
_ENTITY_NAME_RE = re.compile(ENTITY_NAME_PATTERN)


def validate_new_entity_name(entity_name: str) -> None:
    """Reject new entity names that do not use the supported identifier format."""
    if len(entity_name) < 2 or not _ENTITY_NAME_RE.fullmatch(entity_name):
        raise ConfigurationError(
            message=(
                "New entity names must be at least two characters and use lowercase letters, "
                "digits, and underscores, starting with a letter."
            ),
            context={"entity_name": entity_name},
        )
