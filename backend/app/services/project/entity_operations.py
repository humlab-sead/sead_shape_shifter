"""Entity operations: add, update, delete entities within projects."""

import hashlib
import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from backend.app.exceptions import EntityConflictError, ResourceConflictError, ResourceNotFoundError
from backend.app.middleware.correlation import get_correlation_id
from backend.app.models.entity import Entity
from backend.app.models.project import Project
from backend.app.services.project.entity_persistence_strategies import EntityPersistenceStrategyRegistry

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
    canonical = json.dumps(entity_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
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
        self._persistence_strategy_registry = persistence_strategy_registry or EntityPersistenceStrategyRegistry()

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

    def _prepare_entity_for_persistence(self, entity_name: str, entity_data: dict[str, Any]) -> dict[str, Any]:
        """Apply the configured persistence strategy for the entity type."""
        strategy = self._persistence_strategy_registry.get_strategy(entity_data)
        return strategy.prepare_for_persistence(entity_name, entity_data)

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
        if entity_name in project.entities:
            raise ResourceConflictError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' already exists")

        entity_dict = self._prepare_entity_for_persistence(entity_name, self._serialize_entity(entity))
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

        entity_dict = self._prepare_entity_for_persistence(entity_name, self._serialize_entity(entity))
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

            entity_data = self._prepare_entity_for_persistence(entity_name, entity_data)

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

    def update_entity_by_name(self, project_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Update entity in project by project name.

        Serialized per-project to prevent lost-update race conditions.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Updated entity data as dict

        Raises:
            ProjectNotFoundError: If project not found
            ResourceNotFoundError: If entity not found
        """
        corr: str = get_correlation_id()
        lock = self._get_lock(project_name)
        logger.info(
            "[{}] update_entity_by_name: ACQUIRING lock project='{}' entity='{}'",
            corr,
            project_name,
            entity_name,
        )

        with lock:
            project: Project = self._load_project(project_name)

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

            # Ensure public_id is preserved (three-tier identity model)
            # If not in incoming data, keep existing value (even if None)
            if "public_id" not in entity_data and "public_id" in project.entities[entity_name]:
                entity_data["public_id"] = project.entities[entity_name]["public_id"]

            entity_data = self._prepare_entity_for_persistence(entity_name, entity_data)

            # Use the model's add_entity method to ensure proper handling
            project.add_entity(entity_name, entity_data)

            if self._save_entity_boundary:
                self._save_entity_boundary(project_name, entity_name, entity_data)
            else:
                self._save_project(project)

    def update_entity_by_name_if_match(
        self,
        project_name: str,
        entity_name: str,
        entity_data: dict[str, Any],
        expected_etag: str,
    ) -> None:
        """
        Update entity with ETag-based optimistic locking (compare-and-swap).

        Performs the stale-check against a freshly disk-loaded project inside
        the per-project lock.  If the current entity ETag does not match
        *expected_etag* the update is rejected with :exc:`EntityConflictError`
        (HTTP 409) carrying the current ETag and entity so the client can
        present a reload-before-saving prompt.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Updated entity data as dict
            expected_etag: ETag from the client's last entity read

        Raises:
            ResourceNotFoundError: If project or entity not found
            EntityConflictError: If the entity has changed since the client read it
        """
        corr: str = get_correlation_id()
        lock = self._get_lock(project_name)
        logger.info(
            "[{}] update_entity_by_name_if_match: ACQUIRING lock project='{}' entity='{}'",
            corr,
            project_name,
            entity_name,
        )

        with lock:
            # Force-load from disk to bypass ApplicationState cache so the stale-check
            # always reflects the latest persisted content.
            project: Project = self._load_project(project_name, force_reload=True)

            if entity_name not in project.entities:
                raise ResourceNotFoundError(
                    resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found"
                )

            current_entity = project.entities[entity_name]
            current_etag = compute_entity_etag(current_entity)

            if current_etag != expected_etag:
                logger.info(
                    "[{}] update_entity_by_name_if_match: ETag mismatch project='{}' entity='{}' expected='{}' current='{}'",
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

            # Preserve public_id (three-tier identity model)
            if "public_id" not in entity_data and "public_id" in project.entities[entity_name]:
                entity_data["public_id"] = project.entities[entity_name]["public_id"]

            entity_data = self._prepare_entity_for_persistence(entity_name, entity_data)
            project.add_entity(entity_name, entity_data)

            logger.info(
                "[{}] update_entity_by_name_if_match: ETag matched, saving project='{}' entity='{}'",
                corr,
                project_name,
                entity_name,
            )

            if self._save_entity_boundary:
                self._save_entity_boundary(project_name, entity_name, entity_data)
            else:
                self._save_project(project)

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
