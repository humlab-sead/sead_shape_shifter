"""Mapper between core ShapeShiftConfig and API Configuration models."""

from typing import Any

from loguru import logger

from backend.app.models import (
    ConfigMetadata,
    Configuration,
    Entity,
    ForeignKeyConfig,
)


class ConfigMapper:
    """Bidirectional mapper between core and API configuration models."""

    @staticmethod
    def to_api_config(cfg_dict: dict[str, Any], name: str) -> Configuration:
        """
        Convert core config dict to API Configuration.

        Args:
            cfg_dict: Core configuration dictionary (ShapeShiftConfig.cfg format)
            name: Configuration name

        Returns:
            API configuration model with sparse structure
        """
        logger.debug(f"Converting core config dict to API config: {name}")

        # Extract metadata from YAML metadata section or use defaults
        metadata_dict = cfg_dict.get("metadata", {})
        metadata = ConfigMetadata(
            name=metadata_dict.get("name", name),
            description=metadata_dict.get("description", ""),
            version=metadata_dict.get("version", "1.0.0"),
            file_path=None,
            entity_count=len(cfg_dict.get("entities", {})),
            created_at=0,
            modified_at=0,
            is_valid=True,
        )

        # Map entities (preserve sparse structure)
        entities = {}
        for entity_name, entity_dict in cfg_dict.get("entities", {}).items():
            entities[entity_name] = ConfigMapper._dict_to_api_entity(entity_name, entity_dict)

        # Map options (preserve as-is)
        options = cfg_dict.get("options", {})

        return Configuration(
            metadata=metadata,
            entities=entities,
            options=options,
        )

    @staticmethod
    def to_core_dict(api_config: Configuration) -> dict[str, Any]:
        """
        Convert API Configuration to core config dict.

        Args:
            api_config: API configuration model

        Returns:
            Core configuration dictionary (for ShapeShiftConfig)
        """
        assert api_config.metadata is not None
        logger.debug(f"Converting API config to core dict: {api_config.metadata.name}")

        # Build core config dict with all three required sections
        cfg_dict: dict[str, Any] = {
            "metadata": {
                "name": api_config.metadata.name,
                "description": api_config.metadata.description,
                "version": api_config.metadata.version,
            },
            "entities": {},
            "options": api_config.options or {},
        }

        # Map entities (preserve sparse structure)
        for entity_name, api_entity in api_config.entities.items():
            cfg_dict["entities"][entity_name] = ConfigMapper._api_entity_to_dict(api_entity)

        return cfg_dict

    @staticmethod
    def _dict_to_api_entity(entity_name: str, entity_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Convert core entity dict to API entity dict.

        Only includes fields that are explicitly set (non-None/non-empty).
        This preserves sparse YAML structure.

        """
        # Build entity dict with only defined fields
        api_dict: dict[str, Any] = {
            "name": entity_name,
        }

        # Add type only if explicitly set
        if "type" in entity_dict:
            api_dict["type"] = entity_dict["type"]

        # Known fields to handle explicitly
        known_fields = {
            "name", "type", "source", "data_source", "query", "surrogate_id",
            "keys", "columns", "extra_columns", "values", "depends_on",
            "drop_duplicates", "drop_empty_rows", "check_column_names", "options",
            "foreign_keys", "filters", "unnest", "append"
        }

        # Conditionally add known fields with primitive types
        # Note: source and options can be None/empty and should be preserved
        for field in [
            "source",
            "data_source",
            "query",
            "surrogate_id",
            "keys",
            "columns",
            "extra_columns",
            "values",
            "depends_on",
            "drop_duplicates",
            "drop_empty_rows",
            "check_column_names",
            "options",
        ]:
            if field in entity_dict:
                api_dict[field] = entity_dict[field]

        if entity_dict.get("foreign_keys"):
            fk_data = entity_dict["foreign_keys"]
            
            # Keep foreign_keys as plain dicts (not ForeignKeyConfig objects)
            # since Configuration.entities stores plain dicts
            if isinstance(fk_data, dict):
                # Dict format: {"fk_name": {"entity": "...", "key": "..."}}
                # Convert to list format
                api_dict["foreign_keys"] = [
                    {
                        "entity": fk["entity"],
                        "local_keys": fk.get("local_keys", fk.get("key", [])),
                        "remote_keys": fk.get("remote_keys", fk.get("key", [])),
                    }
                    for fk_name, fk in fk_data.items()
                ]
            else:
                # List format: [{"entity": "...", "local_keys": [...], "remote_keys": [...]}]
                # Keep as-is (already in correct format)
                api_dict["foreign_keys"] = fk_data

        # Handle top-level fields: filters, unnest, append
        for field in ["filters", "unnest", "append"]:
            if entity_dict.get(field):
                api_dict[field] = entity_dict[field]

        # Preserve any other fields not explicitly handled (custom fields like arbodat_codes, surrogate_name, etc.)
        for field, value in entity_dict.items():
            if field not in known_fields and field not in api_dict:
                api_dict[field] = value

        # Return dict directly since Configuration.entities expects dict[str, dict[str, Any]]
        return api_dict

    @staticmethod
    def _api_entity_to_dict(api_entity: Entity | dict[str, Any]) -> dict[str, Any]:
        """
        Convert API Entity to core entity dict.

        Only includes fields that are explicitly set (non-None/non-empty).
        This preserves sparse YAML structure.
        """
        # If already a dict, return as-is (for direct dict inputs)
        # but remove 'name' field as it's not part of core entity structure
        if isinstance(api_entity, dict):
            entity_dict = api_entity.copy()
            entity_dict.pop('name', None)  # Remove name if present
            return entity_dict

        # Build entity dict with only defined fields
        entity_dict: dict[str, Any] = {}

        # Only include type if it was explicitly set
        if api_entity.type:
            entity_dict["type"] = api_entity.type

        # Conditionally add fields only if they have values
        if api_entity.source is not None:
            entity_dict["source"] = api_entity.source

        if api_entity.data_source:
            entity_dict["data_source"] = api_entity.data_source

        if api_entity.query:
            entity_dict["query"] = api_entity.query

        if api_entity.surrogate_id:
            entity_dict["surrogate_id"] = api_entity.surrogate_id

        if api_entity.keys:
            entity_dict["keys"] = api_entity.keys

        if api_entity.columns:
            entity_dict["columns"] = api_entity.columns

        if api_entity.values:
            entity_dict["values"] = api_entity.values

        if api_entity.foreign_keys:
            # Convert list of ForeignKeyConfig to list format (preserving original structure)
            entity_dict["foreign_keys"] = [
                {
                    "entity": fk.entity,
                    "local_keys": fk.local_keys,
                    "remote_keys": fk.remote_keys,
                    **({"how": fk.how} if fk.how else {}),
                    **({"extra_columns": fk.extra_columns} if fk.extra_columns else {}),
                    **({"drop_remote_id": fk.drop_remote_id} if fk.drop_remote_id else {}),
                }
                for fk in api_entity.foreign_keys
            ]

        # Handle filters, unnest, append as direct fields (not under 'advanced')
        if api_entity.filters:
            entity_dict["filters"] = [filter_cfg.model_dump(exclude_none=True) for filter_cfg in api_entity.filters]

        if api_entity.unnest:
            entity_dict["unnest"] = api_entity.unnest.model_dump(exclude_none=True)

        if api_entity.append:
            entity_dict["append"] = [append_cfg.model_dump(exclude_none=True) for append_cfg in api_entity.append]

        if api_entity.depends_on:
            entity_dict["depends_on"] = api_entity.depends_on

        if api_entity.drop_duplicates is not None:
            entity_dict["drop_duplicates"] = api_entity.drop_duplicates

        if api_entity.drop_empty_rows is not None:
            entity_dict["drop_empty_rows"] = api_entity.drop_empty_rows

        # check_column_names defaults to True, only include if explicitly set to False
        if api_entity.check_column_names is False:
            entity_dict["check_column_names"] = False

        return entity_dict
