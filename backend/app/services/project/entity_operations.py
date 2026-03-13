"""Entity operations: add, update, delete entities within projects."""

from typing import TYPE_CHECKING, Any

from loguru import logger

from backend.app.exceptions import ResourceConflictError, ResourceNotFoundError, SchemaValidationError
from backend.app.middleware.correlation import get_correlation_id
from backend.app.models.entity import Entity
from backend.app.models.project import Project

if TYPE_CHECKING:
    pass


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
    ):
        """Initialize entity operations.

        Args:
            project_lock_getter: Function to get per-project lock
            load_project_callback: Function to load project by name
            save_project_callback: Function to save project
        """
        self._get_lock = project_lock_getter
        self._load_project = load_project_callback
        self._save_project = save_project_callback

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

    @staticmethod
    def _validate_fixed_entity_shape(entity_name: str, entity_data: dict[str, Any]) -> None:
        """Reject malformed fixed entities before they reach YAML persistence."""
        if entity_data.get("type") != "fixed":
            return

        columns = entity_data.get("columns")
        if not isinstance(columns, list):
            return

        duplicate_columns = sorted({column for column in columns if columns.count(column) > 1})
        if duplicate_columns:
            raise SchemaValidationError(
                message=f"Fixed data entity '{entity_name}' has duplicate columns {duplicate_columns}",
                entity=entity_name,
                field="columns",
            )

        values = entity_data.get("values")
        if values is None or isinstance(values, str):
            return

        if not isinstance(values, list) or not all(isinstance(row, list) for row in values):
            raise SchemaValidationError(
                message=f"Fixed data entity '{entity_name}' must have values as a list of lists",
                entity=entity_name,
                field="values",
            )

        if not values:
            return

        row_lengths = {len(row) for row in values}
        if len(row_lengths) != 1:
            raise SchemaValidationError(
                message=f"Fixed data entity '{entity_name}' has inconsistent row lengths in values",
                entity=entity_name,
                field="values",
            )

        values_length = next(iter(row_lengths))
        public_id = entity_data.get("public_id")
        identity_columns = {"system_id"}
        if isinstance(public_id, str) and public_id:
            identity_columns.add(public_id)

        expected_without_identity = len(columns)
        expected_with_identity = len(set(columns) | identity_columns)

        if values_length not in (expected_without_identity, expected_with_identity):
            raise SchemaValidationError(
                message=(
                    f"Fixed data entity '{entity_name}' has mismatched number of columns and values "
                    f"(got {values_length} values per row, expected {expected_without_identity} for data-only "
                    f"or {expected_with_identity} with identity columns)"
                ),
                entity=entity_name,
                field="values",
            )

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

        entity_dict = self._serialize_entity(entity)
        self._validate_fixed_entity_shape(entity_name, entity_dict)
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

        entity_dict = self._serialize_entity(entity)
        self._validate_fixed_entity_shape(entity_name, entity_dict)
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

            self._validate_fixed_entity_shape(entity_name, entity_data)

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

            self._validate_fixed_entity_shape(entity_name, entity_data)

            # Use the model's add_entity method to ensure proper handling
            project.add_entity(entity_name, entity_data)
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
