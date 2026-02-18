"""Mapper between core ShapeShiftProject and API Project models.

This mapper uses Pydantic's schema introspection (model_dump/model_fields) as the
single source of truth, eliminating hardcoded field lists. The Entity Pydantic model
defines all valid fields - adding new fields to Entity automatically updates the mapper.

Architecture:
- YAML files are the source of truth for project structure
- Core (ShapeShiftProject) is a thin dict wrapper over YAML structure
- API (Project/Entity) uses Pydantic models for validation
- This mapper bridges the two layers, preserving sparse YAML structure

Directive Resolution Strategy:
- **API → Core (to_core)**: Resolves @include: and @value: directives (processing needs concrete values)
- **YAML → API (to_api_config)**: Preserves directives (editing layer keeps references)
- **API → YAML (to_core_dict)**: Preserves directives (saves original structure)
- **Core → API**: Not needed (processing is one-way, no roundtrip)

Principle: Directives live in YAML/API layer, resolved values in Core layer.
The API layer is the editing/persistence boundary. Core is the execution/processing boundary.

No hardcoded field lists - all field handling is derived from Pydantic schemas.
"""

from typing import Any, Literal

from loguru import logger

from backend.app.core.config import settings
from backend.app.mappers.project_name_mapper import ProjectNameMapper
from backend.app.middleware.correlation import get_correlation_id
from backend.app.models import (
    Entity,
    Project,
    ProjectMetadata,
)
from backend.app.utils import convert_ruamel_types
from src.configuration.config import Config
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
            type=metadata_dict.get("type", "shapeshifter-project"),
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

        # Map task_list (preserve as-is)
        task_list = cfg_dict.get("task_list")

        return Project(
            metadata=metadata,
            entities=entities,
            options=options,
            task_list=task_list,
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
                "type": api_config.metadata.type or "shapeshifter-project",
                "description": api_config.metadata.description,
                "version": api_config.metadata.version,
                "default_entity": api_config.metadata.default_entity,
            },
            "entities": {},
            "options": api_config.options or {},
        }

        # Add task_list if present
        if api_config.task_list is not None:
            cfg_dict["task_list"] = api_config.task_list

        # Map entities (preserve sparse structure)
        for entity_name, api_entity in api_config.entities.items():
            cfg_dict["entities"][entity_name] = ProjectMapper._api_entity_to_dict(api_entity)

        # Defensive: verify entity count survived serialization
        input_count = len(api_config.entities)
        output_count = len(cfg_dict["entities"])
        if output_count != input_count:
            corr = get_correlation_id()
            input_names = sorted(api_config.entities.keys())
            output_names = sorted(cfg_dict["entities"].keys())
            logger.error(
                "[{}] ProjectMapper.to_core_dict ENTITY COUNT MISMATCH: input={}" + " input_names={} output={} output_names={}",
                corr,
                input_count,
                input_names,
                output_count,
                output_names,
            )

        unresolved: list[str] = Config.find_unresolved_directives(cfg_dict)
        if unresolved:
            extra: str = "" if len(unresolved) <= 5 else f" (and {len(unresolved) - 5} more)"
            logger.debug(f"@value references in config (will be resolved on load): {', '.join(unresolved[:5])}{extra}")

        return cfg_dict

    @staticmethod
    def to_core(api_config: Project) -> ShapeShiftProject:
        """Convert API Project to core ShapeShiftProject.

        Conditionally resolves @include: and @value: directives only if needed.
        Resolves file paths based on location field at the API → Core boundary.
        """
        cfg_dict: dict[str, Any] = ProjectMapper.to_core_dict(api_config=api_config)

        # Resolve file paths in entity options based on location field
        # This gives Core fully resolved absolute paths without storing them in YAML
        entities = cfg_dict.get("entities", {})
        for entity_dict in entities.values():
            options = entity_dict.get("options")
            if not options or not isinstance(options, dict):
                continue
            
            filename: str = options.get("filename") or ""

            if not filename:
                continue

            location: str = options.get("location", "global") or "global"
            if location not in ["global", "local"]:
                logger.warning(f"Unknown location '{location}' for file '{filename}', defaulting to global")
                location = "global"

            # Resolve to absolute path based on location
            resolved_path: str = ProjectMapper.resolve_file_path(api_config.filename, filename, location)
            
            # Update to absolute path for Core (Core doesn't need to know about location)
            options["filename"] = resolved_path
            options["location"] = location
            
            logger.debug(f"Resolved {location} file: {filename} -> {resolved_path}")

        project = ShapeShiftProject(cfg=cfg_dict, filename=api_config.filename or "")

        # Only resolve if there are unresolved directives
        if not project.is_resolved():
            # Pass env_prefix and env_file from settings for proper env var resolution
            project = project.resolve(
                filename=api_config.filename,
                env_prefix=settings.env_prefix,
                env_filename=settings.env_file,
            )

        return project

    @staticmethod
    def resolve_file_path(project_name: str|None, filename: str, location: Literal["global", "local"]) -> str:
        
        if location == "global":
            return str(settings.GLOBAL_DATA_DIR / filename)
        
        if location == "local":
            # Convert project name with ":" instead of "/" to path and resolve relative to projects dir
            project_path: str = ProjectNameMapper.to_path(project_name or "")
            return str(settings.PROJECTS_DIR / project_path / filename)
        
        logger.warning(f"Unknown location '{location}' for file '{filename}', using global")
        return str(settings.GLOBAL_DATA_DIR / filename)

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

        Uses Pydantic model_dump(mode="json") to automatically serialize ALL fields,
        including nested Pydantic models, recursively. This eliminates brittleness -
        adding new nested models to Entity won't require manual handling here.

        The Entity model schema is the single source of truth.
        """
        # If already a dict, deep convert ruamel types and remove 'name' (API-only field)
        if isinstance(api_entity, dict):
            # Deep convert to avoid ruamel.yaml types in nested structures
            entity_dict: dict[str, Any] = convert_ruamel_types(api_entity)
            entity_dict.pop("name", None)
            return entity_dict

        # Use mode="json" to recursively serialize ALL nested Pydantic models to dicts
        # This is NOT brittle - new nested models are automatically handled!
        #
        # mode="json": Recursively converts everything to JSON-compatible types
        # (dict, list, str, int, float, bool, None). Perfect for YAML serialization.
        #
        # exclude_none: Don't include fields that are None
        # exclude_unset: Don't include fields that weren't explicitly set
        # exclude={'name'}: name is API metadata, not part of core entity structure
        entity_dict = api_entity.model_dump(exclude_none=True, exclude_unset=True, exclude={"name"}, mode="json")

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
