"""Entity operations: add, update, delete entities within projects."""

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

from loguru import logger

from backend.app.exceptions import ConfigurationError, EntityConflictError, ResourceConflictError, ResourceNotFoundError
from backend.app.middleware.correlation import get_correlation_id
from backend.app.models.entity import Entity
from backend.app.models.project import Project
from backend.app.services.project.entity_persistence_strategies import EntityPersistenceStrategyRegistry
from backend.app.utils.entity_name import validate_new_entity_name
from backend.app.utils.sql import extract_tables
from src.model import TableConfig

_ENTITY_VALUE_REFERENCE_RE = re.compile(r"@value:\s*entities\.([A-Za-z0-9_-]+)(?=\.|\s|$)")


def _iter_config_strings(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _iter_config_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_config_strings(item)
    elif isinstance(value, str):
        yield value


if TYPE_CHECKING:
    pass


def compute_entity_etag(entity_dict: dict[str, Any]) -> str:
    """Compute a stable, content-based ETag for an entity dict.

    The ETag is the first 16 hex characters of the SHA-256 digest of the
    canonical JSON representation of *entity_dict*.  Logically identical
    dicts (same keys, same values, any insertion order) always produce the
    same ETag, making it safe to compare across requests.

    Args:
        entity_dict: Entity data as stored in the project file.

    Returns:
        16-character lowercase hex string.
    """
    canonical: str = json.dumps(entity_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


class EntityOperations:
    """Handles entity CRUD operations within projects.

    This component manages individual entities within projects, both via
    Project object manipulation and via project name (load/save pattern).
    """

    def __init__(
        self,
        project_lock_getter,  # Callable[[str], threading.Lock]
        load_project_callback,  # Callable[[str], Project]
        save_project_callback,  # Callable[[Project], Project]
        persistence_strategy_registry: EntityPersistenceStrategyRegistry | None = None,
        save_entity_boundary_callback=None,  # Callable[[str, str, dict | None], None] | None
        save_entity_rename_callback=None,  # Callable[[str, str, str, Project], list[str]] | None
    ):
        """Initialize entity operations.

        Args:
            project_lock_getter: Function to get per-project lock
            load_project_callback: Function to load project by name
            save_project_callback: Function to save project (full project, fallback)
            persistence_strategy_registry: Registry for type-specific persistence strategies
            save_entity_boundary_callback: Optional callback for boundary-based entity save.
                Signature: (project_name: str, entity_name: str, entity_dict: dict | None) -> None.
                When provided, entity mutations use boundary save instead of full project save.
                Pass None to fall back to whole-project save.
        """
        self._get_lock = project_lock_getter
        self._load_project = load_project_callback
        self._save_project = save_project_callback
        self._save_entity_boundary = save_entity_boundary_callback
        self._save_entity_rename = save_entity_rename_callback
        self._persistence_strategy_registry = persistence_strategy_registry or EntityPersistenceStrategyRegistry()

    @staticmethod
    def _find_entity_dependents(project: Project, entity_name: str) -> list[str]:
        """Return sorted entity names that directly reference an entity."""
        dependents: set[str] = set()
        for dependent_name, entity_data in (project.entities or {}).items():
            if dependent_name == entity_name or not isinstance(entity_data, dict) or not entity_data:
                continue

            table_config = TableConfig(
                entities_cfg=project.entities,
                entity_name=dependent_name,
                project_options=project.options,
            )
            if entity_name in table_config.referenced_entities:
                dependents.add(dependent_name)
                continue

            for value in _iter_config_strings(entity_data):
                if any(match.group(1) == entity_name for match in _ENTITY_VALUE_REFERENCE_RE.finditer(value)):
                    dependents.add(dependent_name)
                    break

            if entity_data.get("data_source") == "@internal" and isinstance(entity_data.get("query"), str):
                if entity_name.casefold() in {table.casefold() for table in extract_tables(entity_data["query"])}:
                    dependents.add(dependent_name)

        return sorted(dependents)

    @staticmethod
    def _serialize_entity(entity: Entity) -> dict[str, Any]:
        """
        Serialize entity to dict, preserving public_id field even when None.

        This ensures the three-tier identity model (system_id, keys, public_id)
        is always complete in YAML files, while avoiding bloat from other None fields.

        Args:
            entity: Entity to serialize

        Returns:
            Entity dict with public_id preserved
        """
        # Exclude None fields to avoid YAML bloat, but preserve public_id separately
        entity_dict: dict[str, Any] = entity.model_dump(
            exclude_none=True, exclude={"surrogate_id"}, mode="json"
        )  # Exclude deprecated field

        # Ensure public_id is always present (even if None) for three-tier identity model
        if "public_id" not in entity_dict:
            entity_dict["public_id"] = entity.public_id

        return entity_dict

    def _prepare_entity_for_persistence(
        self,
        project_options: dict[str, Any] | None,
        entity_name: str,
        entity_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply the configured persistence strategy for the entity type."""
        strategy = self._persistence_strategy_registry.get_strategy(entity_data)
        return strategy.prepare_for_persistence(entity_name, entity_data, project_options)

    # Object-based entity operations (work on Project instances)

    def add_entity(self, project: Project, entity_name: str, entity: Entity) -> Project:
        """
        Add entity to project.

        Args:
            project: Project to modify
            entity_name: Entity name
            entity: Entity data

        Returns:
            Updated project

        Raises:
            ResourceConflictError: If entity already exists
        """
        validate_new_entity_name(entity_name)
        if entity_name in project.entities:
            raise ResourceConflictError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' already exists")

        entity_dict = self._prepare_entity_for_persistence(getattr(project, "options", {}), entity_name, self._serialize_entity(entity))
        project.entities[entity_name] = entity_dict
        logger.debug(f"Added entity '{entity_name}'")
        return project

    def update_entity(self, project: Project, entity_name: str, entity: Entity) -> Project:
        """
        Update entity in project.

        Args:
            project: Project to modify
            entity_name: Entity name
            entity: Updated entity data

        Returns:
            Updated project

        Raises:
            ResourceNotFoundError: If entity not found
        """
        if entity_name not in project.entities:
            raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

        entity_dict = self._prepare_entity_for_persistence(getattr(project, "options", {}), entity_name, self._serialize_entity(entity))
        project.entities[entity_name] = entity_dict
        logger.debug(f"Updated entity '{entity_name}'")
        return project

    def delete_entity(self, project: Project, entity_name: str) -> Project:
        """
        Delete entity from project.

        Args:
            project: Project to modify
            entity_name: Entity name

        Returns:
            Updated project

        Raises:
            ResourceNotFoundError: If entity not found
        """
        if entity_name not in project.entities:
            raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

        del project.entities[entity_name]

        logger.debug(f"Deleted entity '{entity_name}'")
        return project

    def get_entity(self, project: Project, entity_name: str) -> dict[str, Any]:
        """
        Get entity from project.

        Args:
            project: Project
            entity_name: Entity name

        Returns:
            Entity data

        Raises:
            ResourceNotFoundError: If entity not found
        """
        if entity_name not in project.entities:
            raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

        return project.entities[entity_name]

    # Name-based entity operations (load/modify/save pattern with locking)

    def add_entity_by_name(self, project_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Add entity to project by project name.

        Serialized per-project to prevent lost-update race conditions.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Entity data as dict

        Raises:
            ProjectNotFoundError: If project not found
            ResourceConflictError: If entity already exists
        """
        validate_new_entity_name(entity_name)
        corr: str = get_correlation_id()
        lock = self._get_lock(project_name)
        logger.info(
            "[{}] add_entity_by_name: ACQUIRING lock project='{}' entity='{}'",
            corr,
            project_name,
            entity_name,
        )

        with lock:
            project: Project = self._load_project(project_name)

            before_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] add_entity_by_name: project='{}' BEFORE add: count={} names={} adding='{}'",
                corr,
                project_name,
                len(before_names),
                before_names,
                entity_name,
            )

            if entity_name in project.entities:
                raise ResourceConflictError(
                    resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' already exists"
                )

            entity_data = self._prepare_entity_for_persistence(getattr(project, "options", {}), entity_name, entity_data)

            # Use the model's add_entity method to ensure proper handling
            project.add_entity(entity_name, entity_data)

            after_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] add_entity_by_name: project='{}' AFTER add: count={} names={}",
                corr,
                project_name,
                len(after_names),
                after_names,
            )

            if self._save_entity_boundary:
                self._save_entity_boundary(project_name, entity_name, entity_data)
            else:
                self._save_project(project)

    def update_entity_by_name(
        self,
        project_name: str,
        entity_name: str,
        entity_data: dict[str, Any],
        *,
        expected_etag: str | None = None,
        new_name: str | None = None,
    ) -> list[str]:
        """
        Update entity in project by project name.

        Serialized per-project to prevent lost-update race conditions.  When
        *expected_etag* is supplied the update is conditional (compare-and-swap):
        the project is force-loaded from disk so the stale-check always reflects
        the latest persisted state.  If the recomputed ETag does not match
        *expected_etag* the request is rejected with :exc:`EntityConflictError`
        (HTTP 409) carrying the current ETag and entity.  Omitting *expected_etag*
        performs an unconditional update (backward compatible).

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Updated entity data as dict
            expected_etag: When provided, the ETag the client received on last read.
                If the current persisted ETag differs, raises EntityConflictError.
            new_name: Optional replacement name. Renames are rejected while other entities refer to the entity.

        Raises:
            ProjectNotFoundError: If project not found
            ResourceNotFoundError: If entity not found
            EntityConflictError: If *expected_etag* is given and does not match the
                current entity ETag
            ResourceConflictError: If the target name exists or the entity has dependents
        """
        corr: str = get_correlation_id()
        lock = self._get_lock(project_name)
        logger.info("[{}] update_entity_by_name: ACQUIRING lock project='{}' entity='{}'", corr, project_name, entity_name)

        with lock:
            # Force-load from disk when performing a conditional (ETag) update so the
            # stale-check always reflects the latest persisted content.
            project: Project = self._load_project(project_name, force_reload=expected_etag is not None)

            entity_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] update_entity_by_name: project='{}' current entities={} names={} updating='{}'",
                corr,
                project_name,
                len(entity_names),
                entity_names,
                entity_name,
            )

            if entity_name not in project.entities:
                raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

            if expected_etag is not None:
                current_entity = project.entities[entity_name]
                current_etag: str = compute_entity_etag(current_entity)
                if current_etag != expected_etag:
                    logger.info(
                        "[{}] update_entity_by_name: ETag mismatch project='{}' entity='{}' expected='{}' current='{}'",
                        corr,
                        project_name,
                        entity_name,
                        expected_etag,
                        current_etag,
                    )
                    raise EntityConflictError(
                        message=f"Entity '{entity_name}' was modified by another user. Reload before saving.",
                        entity_name=entity_name,
                        current_etag=current_etag,
                        current_entity=current_entity,
                    )

            rename_entity: bool = new_name is not None and new_name != entity_name
            if rename_entity:
                assert new_name is not None
                validate_new_entity_name(new_name)
                if new_name in project.entities:
                    raise ResourceConflictError(
                        message=f"Entity '{new_name}' already exists",
                        resource_type="entity",
                        resource_id=new_name,
                        context={"conflict_type": "entity_name_collision", "new_name": new_name},
                    )

                dependent_names: list[str] = self._find_entity_dependents(project, entity_name)
                if dependent_names:
                    raise ResourceConflictError.create_entity_has_dependents(
                        entity_name=entity_name,
                        new_name=new_name,
                        dependent_names=dependent_names,
                    )

                if self._save_entity_rename is None:
                    raise ConfigurationError(message="Safe entity rename persistence is not configured.")

            # Ensure public_id is preserved (three-tier identity model)
            # If not in incoming data, keep existing value (even if None)
            if "public_id" not in entity_data and "public_id" in project.entities[entity_name]:
                entity_data["public_id"] = project.entities[entity_name]["public_id"]

            persistence_name: None | str = new_name if rename_entity else entity_name
            assert persistence_name is not None
            entity_data = self._prepare_entity_for_persistence(getattr(project, "options", {}), persistence_name, entity_data)

            if rename_entity:
                project.entities.pop(entity_name)
                assert new_name is not None
                project.add_entity(new_name, entity_data)
                if project.metadata and project.metadata.default_entity == entity_name:
                    project.metadata.default_entity = new_name
                assert self._save_entity_rename is not None
                return self._save_entity_rename(project_name, entity_name, new_name, project)

            # Use the model's add_entity method to ensure proper handling
            project.add_entity(entity_name, entity_data)

            if self._save_entity_boundary:
                self._save_entity_boundary(project_name, entity_name, entity_data)
            else:
                self._save_project(project)
            return []

    def delete_entity_by_name(self, project_name: str, entity_name: str) -> None:
        """
        Delete entity from project by project name.

        Serialized per-project to prevent lost-update race conditions.

        Args:
            project_name: Project name
            entity_name: Entity name

        Raises:
            ProjectNotFoundError: If project not found
            ResourceNotFoundError: If entity not found
        """
        corr: str = get_correlation_id()
        lock = self._get_lock(project_name)
        logger.info(
            "[{}] delete_entity_by_name: ACQUIRING lock project='{}' entity='{}'",
            corr,
            project_name,
            entity_name,
        )

        with lock:
            project: Project = self._load_project(project_name)

            before_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] delete_entity_by_name: project='{}' BEFORE delete: count={} names={} removing='{}'",
                corr,
                project_name,
                len(before_names),
                before_names,
                entity_name,
            )

            if entity_name not in project.entities:
                raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

            del project.entities[entity_name]

            after_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] delete_entity_by_name: project='{}' AFTER delete: count={} names={}",
                corr,
                project_name,
                len(after_names),
                after_names,
            )

            if self._save_entity_boundary:
                self._save_entity_boundary(project_name, entity_name, None)
            else:
                self._save_project(project)

    def get_entity_by_name(self, project_name: str, entity_name: str) -> dict[str, Any]:
        """
        Get entity from project by project name.

        Args:
            project_name: Project name
            entity_name: Entity name

        Returns:
            Entity data as dict

        Raises:
            ProjectNotFoundError: If project not found
            ResourceNotFoundError: If entity not found
        """
        project: Project = self._load_project(project_name)

        if entity_name not in project.entities:
            raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

        return project.entities[entity_name]

    def get_entity_etag_by_name(self, project_name: str, entity_name: str) -> str:
        """
        Return the current ETag for an entity.

        Args:
            project_name: Project name
            entity_name: Entity name

        Returns:
            16-character hex ETag string

        Raises:
            ResourceNotFoundError: If project or entity not found
        """
        entity_dict = self.get_entity_by_name(project_name, entity_name)
        return compute_entity_etag(entity_dict)
