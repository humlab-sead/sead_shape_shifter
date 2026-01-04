"""Utilities for migrating reconciliation configuration from v1 to v2 format."""

from typing import Any

from loguru import logger


def migrate_mapping_v1_to_v2(old_mapping: dict[str, Any]) -> dict[str, Any]:
    """
    Migrate a single mapping entry from v1 to v2 format.

    Changes:
    - source_values (list) → source_value (single value)

    Args:
        old_mapping: v1 format mapping entry

    Returns:
        v2 format mapping entry
    """
    new_mapping = {**old_mapping}

    # Convert source_values (list) to source_value (single)
    if "source_values" in new_mapping:
        source_values = new_mapping.pop("source_values")
        # Take first value if list, otherwise use as-is
        new_mapping["source_value"] = source_values[0] if isinstance(source_values, list) and source_values else source_values

    return new_mapping


def migrate_spec_v1_to_v2(old_spec: dict[str, Any]) -> dict[str, Any]:
    """
    Migrate a single entity reconciliation spec from v1 to v2 format.

    Changes:
    - Remove 'keys' field (target_field is now the dict key)
    - Remove 'columns' field (unused)
    - Migrate all mapping entries

    Args:
        old_spec: v1 format spec
        target_field: The target field name (from keys[0])

    Returns:
        v2 format spec
    """
    new_spec = {**old_spec}

    # Remove obsolete fields
    new_spec.pop("keys", None)
    new_spec.pop("columns", None)

    # Migrate mappings
    if "mapping" in new_spec and isinstance(new_spec["mapping"], list):
        new_spec["mapping"] = [migrate_mapping_v1_to_v2(m) for m in new_spec["mapping"]]

    return new_spec


def migrate_config_v1_to_v2(old_config: dict[str, Any]) -> dict[str, Any]:
    """
    Migrate entire reconciliation configuration from v1 to v2 format.

    v1 format:
        entities:
          site:
            keys: [site_name]
            property_mappings: {...}
            ...

    v2 format:
        version: "2.0"
        entities:
          site:
            site_name:
              property_mappings: {...}
              ...

    Args:
        old_config: v1 format configuration

    Returns:
        v2 format configuration
    """
    logger.info("Migrating reconciliation config from v1 to v2 format")

    new_config = {
        "version": "2.0",
        "service_url": old_config.get("service_url", ""),
        "entities": {},
    }

    old_entities = old_config.get("entities", {})

    for entity_name, old_spec in old_entities.items():
        # Extract target field from keys[0]
        keys = old_spec.get("keys", [])
        if not keys:
            logger.warning(f"Entity '{entity_name}' has no keys, skipping migration")
            continue

        target_field = keys[0]

        if len(keys) > 1:
            logger.warning(
                f"Entity '{entity_name}' has multiple keys {keys}, using first '{target_field}'. "
                "Composite keys are not supported in v2 format."
            )

        # Migrate the spec
        migrated_spec = migrate_spec_v1_to_v2(old_spec)

        # Create nested structure: entity -> target_field -> spec
        new_config["entities"][entity_name] = {target_field: migrated_spec}

        logger.debug(f"Migrated entity '{entity_name}' with target field '{target_field}'")

    logger.info(f"Successfully migrated {len(old_entities)} entities to v2 format")
    return new_config


def detect_format_version(config: dict[str, Any]) -> str:
    """
    Detect the format version of a reconciliation configuration.

    Args:
        config: Reconciliation configuration dictionary

    Returns:
        Version string ("1.0" or "2.0")
    """
    # Explicit version field (v2)
    if "version" in config:
        return config["version"]

    # Check structure to infer version
    entities = config.get("entities", {})
    if not entities:
        return "1.0"  # Default to v1 for empty configs

    # Sample first entity to check structure
    first_entity = next(iter(entities.values()))

    # v1: entity value is a spec dict with 'keys' field
    if isinstance(first_entity, dict) and "keys" in first_entity:
        return "1.0"

    # v2: entity value is a dict of {target_field: spec}
    if isinstance(first_entity, dict) and "keys" not in first_entity:
        # Check if it's a nested dict (v2 format)
        if all(isinstance(v, dict) for v in first_entity.values()):
            return "2.0"

    return "1.0"  # Default to v1
