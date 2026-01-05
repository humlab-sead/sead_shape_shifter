"""Mapper between core ShapeShiftProject and API Project models.

This mapper uses Pydantic's schema introspection (model_dump/model_fields) as the
single source of truth, eliminating hardcoded field lists. The Entity Pydantic model
defines all valid fields - adding new fields to Entity automatically updates the mapper.

Architecture:
- YAML files are the source of truth for project structure
- Core (ShapeShiftProject) is a thin dict wrapper over YAML structure
- API (Project/Entity) uses Pydantic models for validation
- This mapper bridges the two layers, preserving sparse YAML structure

No hardcoded field lists - all field handling is derived from Pydantic schemas.
"""

from typing import Any

from loguru import logger

from backend.app.models import (
    Entity,
    Project,
    ProjectMetadata,
)
from src.model import ShapeShiftProject


class ProjectMapper:
    """Bidirectional mapper between core and API project models."""

    @staticmethod
    def to_api_config(cfg_dict: dict[str, Any], name: str, filename: str | None = None) -> Project:
        """
        Convert core config dict to API Project.

        Note: The filename (name parameter) is the authoritative source for project name.
        Any metadata.name in the YAML file is ignored to prevent duplicate files.

        Args:
            cfg_dict: Core configuration dictionary (ShapeShiftProject.cfg format)
            name: Project name derived from filename (authoritative source)

        Returns:
            API configuration model with sparse structure
        """
        logger.debug(f"Converting core config dict to API config: {name}")

        # Extract metadata from YAML metadata section or use defaults
        metadata_dict: dict[str, Any] = cfg_dict.get("metadata", {})
        metadata: ProjectMetadata = ProjectMetadata(
            name=name,  # Filename is the authoritative source
            description=metadata_dict.get("description", ""),
            version=metadata_dict.get("version", "1.0.0"),
            default_entity=metadata_dict.get("default_entity"),
            file_path=filename,
            entity_count=len(cfg_dict.get("entities", {})),
            created_at=0,
            modified_at=0,
            is_valid=True,
        )

        # Map entities (preserve sparse structure)
        entities: dict[str, dict[str, Any]] = {}
        for entity_name, entity_dict in cfg_dict.get("entities", {}).items():
            entities[entity_name] = ProjectMapper._dict_to_api_entity(entity_name, entity_dict)

        # Map options (preserve as-is)
        options = cfg_dict.get("options", {})

        return Project(
            metadata=metadata,
            entities=entities,
            options=options,
        )

    @staticmethod
    def to_core_dict(api_config: Project) -> dict[str, Any]:
        """
        Convert API Project to core config dict.

        Args:
            api_config: API configuration model

        Returns:
            Core configuration dictionary (for ShapeShiftProject)
        """
        assert api_config.metadata is not None
        logger.debug(f"Converting API config to core dict: {api_config.metadata.name}")

        cfg_dict: dict[str, Any] = {
            "metadata": {
                "name": api_config.metadata.name,
                "description": api_config.metadata.description,
                "version": api_config.metadata.version,
                "default_entity": api_config.metadata.default_entity,
            },
            "entities": {},
            "options": api_config.options or {},
        }

        # Map entities (preserve sparse structure)
        for entity_name, api_entity in api_config.entities.items():
            cfg_dict["entities"][entity_name] = ProjectMapper._api_entity_to_dict(api_entity)

        return cfg_dict

    @staticmethod
    def to_core(api_config: Project) -> ShapeShiftProject:
        cfg_dict: dict[str, Any] = ProjectMapper.to_core_dict(api_config=api_config)
        shapeshift = ShapeShiftProject(cfg=cfg_dict, filename=api_config.filename or "")
        return shapeshift

    @staticmethod
    def to_core_config(api_config: Project) -> ShapeShiftProject:
        return ProjectMapper.to_core(api_config)

    @staticmethod
    def _dict_to_api_entity(entity_name: str, entity_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Convert core entity dict to API entity dict.

        Uses Entity model schema to identify known fields, preserving custom fields.
        No hardcoded field lists - relies on Pydantic model as source of truth.
        """
        # Get Entity model fields from Pydantic schema
        # entity_fields: dict_keys[str, FieldInfo] = Entity.model_fields.keys()

        # Start with entity name (API-only field, not in core)
        api_dict: dict[str, Any] = {"name": entity_name}

        # Copy all fields present in input, handling special cases
        for field, value in entity_dict.items():
            # Handle foreign_keys dict-to-list conversion
            if field == "foreign_keys" and isinstance(value, dict):
                # Dict format: {"fk_name": {"entity": "...", "key": "..."}}
                # Convert to list format expected by API
                api_dict["foreign_keys"] = [
                    {
                        "entity": fk["entity"],
                        "local_keys": fk.get("local_keys", fk.get("key", [])),
                        "remote_keys": fk.get("remote_keys", fk.get("key", [])),
                        **{k: v for k, v in fk.items() if k not in ["entity", "local_keys", "remote_keys", "key"]},
                    }
                    for fk_name, fk in value.items()
                ]
            else:
                # Preserve all other fields as-is (both Entity fields and custom fields)
                api_dict[field] = value

        # Return dict directly since Project.entities expects dict[str, dict[str, Any]]
        return api_dict

    @staticmethod
    def _api_entity_to_dict(api_entity: Entity | dict[str, Any]) -> dict[str, Any]:
        """
        Convert API Entity to core entity dict.

        Uses Pydantic model_dump() to eliminate hardcoded field lists.
        The Entity model schema is the single source of truth.
        """
        # If already a dict, return as-is but remove 'name' (API-only field)
        if isinstance(api_entity, dict):
            entity_dict: dict[str, Any] = api_entity.copy()
            entity_dict.pop("name", None)
            return entity_dict

        # Use Pydantic's model_dump to automatically serialize all fields
        # exclude_none: Don't include fields that are None
        # exclude_unset: Don't include fields that weren't explicitly set
        # exclude={'name'}: name is API metadata, not part of core entity structure
        entity_dict = api_entity.model_dump(exclude_none=True, exclude_unset=True, exclude={"name"}, mode="python")

        # Special handling for nested Pydantic models - serialize them explicitly
        # This ensures proper dict format instead of model instances

        if api_entity.foreign_keys:
            entity_dict["foreign_keys"] = [fk.model_dump(exclude_none=True, exclude_unset=True) for fk in api_entity.foreign_keys]

        if api_entity.filters:
            entity_dict["filters"] = [filter_cfg.model_dump(exclude_none=True, exclude_unset=True) for filter_cfg in api_entity.filters]

        if api_entity.unnest:
            entity_dict["unnest"] = api_entity.unnest.model_dump(exclude_none=True, exclude_unset=True)

        if api_entity.append:
            entity_dict["append"] = [append_cfg.model_dump(exclude_none=True, exclude_unset=True) for append_cfg in api_entity.append]

        # Handle check_column_names default: only include if explicitly False
        # (Pydantic includes default=True values, we want sparse YAML)
        if entity_dict.get("check_column_names") is True:
            entity_dict.pop("check_column_names", None)

        # Handle drop_duplicates and drop_empty_rows defaults
        # Only include if not False (the default)
        if entity_dict.get("drop_duplicates") is False:
            entity_dict.pop("drop_duplicates", None)
        if entity_dict.get("drop_empty_rows") is False:
            entity_dict.pop("drop_empty_rows", None)

        return entity_dict
