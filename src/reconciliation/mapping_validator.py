"""Sidecar validation functions for ``<project>-mapping.yml`` alignment.

These validators check that an ``EntityMapping`` from the mapping sidecar is
consistent with the corresponding ``TableConfig`` from the project
configuration.  They raise ``SidecarValidationError`` on hard failures and
log warnings for soft misalignments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.exceptions import ShapeShifterCoreError
from src.reconciliation.mapping_model import EntityMapping

if TYPE_CHECKING:
    from src.model import TableConfig

# ---------------------------------------------------------------------------
# Columns that must never be used as a mapping local key.
# ---------------------------------------------------------------------------
_FORBIDDEN_LOCAL_KEY_COLUMNS: frozenset[str] = frozenset({"system_id"})


class SidecarValidationError(ShapeShifterCoreError):
    """Raised when a sidecar ``EntityMapping`` fails validation against its entity config."""


# ---------------------------------------------------------------------------
# Public validators
# ---------------------------------------------------------------------------


def validate_entity_mapping(entity_mapping: EntityMapping, entity_config: TableConfig) -> None:
    """Validate that *entity_mapping.public_id* matches *entity_config.public_id*.

    Raises:
        SidecarValidationError: If the public IDs differ.
    """
    mapping_public_id = entity_mapping.public_id
    config_public_id = entity_config.public_id

    if mapping_public_id != config_public_id:
        raise SidecarValidationError(
            f"Mapping for entity '{entity_config.entity_name}' specifies public_id "
            f"'{mapping_public_id}', but entity public_id is '{config_public_id}'. "
            f"Keys must match."
        )


def validate_local_key(entity_mapping: EntityMapping, entity_config: TableConfig) -> None:
    """Validate that *entity_mapping.local_key* is a valid business key.

    Checks performed (hard errors):
        - ``local_key`` must not be ``system_id``.
        - ``local_key`` must not be the entity's ``public_id`` column.

    Checks performed (warnings):
        - Warns if any component of *local_key* is not present in
          ``entity_config.keys``.

    Raises:
        SidecarValidationError: If *local_key* is a forbidden column.
    """
    # Normalise to list for uniform handling.
    local_keys: list[str] = _normalise_local_key(entity_mapping.local_key)
    config_public_id: str = entity_config.public_id
    config_keys: set[str] = entity_config.keys
    derived_columns: set[str] = set(entity_config.extra_column_names)

    for key in local_keys:
        if key in _FORBIDDEN_LOCAL_KEY_COLUMNS:
            raise SidecarValidationError(
                f"Mapping local_key '{key}' must not be '{key}'. " f"Use a business key from entity.keys: {sorted(config_keys)}"
            )

        if key == config_public_id:
            raise SidecarValidationError(
                f"Mapping local_key '{key}' must not be the entity's public_id "
                f"('{config_public_id}'). "
                f"Use a business key from entity.keys: {sorted(config_keys)}"
            )

        if key in derived_columns:
            raise SidecarValidationError(
                f"Mapping local_key '{key}' must not be a derived or auto-generated column. "
                f"Use a business key from entity.keys: {sorted(config_keys)}"
            )

        if key not in config_keys:
            logger.warning(
                f"Mapping local_key '{key}' for entity '{entity_config.entity_name}' "
                f"is not in entity.keys: {sorted(config_keys)}. "
                f"Proceeding, but consider updating the sidecar or entity configuration."
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalise_local_key(local_key: str | list[str]) -> list[str]:
    """Return *local_key* as a list of column-name strings."""
    if isinstance(local_key, str):
        return [local_key]
    return local_key
