from ast import Is
from typing import Any

from src.utility import dotget

from .base import ProjectSpecification
from .entity import EntitySpecification

# pylint: disable=line-too-long, unused-argument


class CircularDependencySpecification(ProjectSpecification):
    """Validates that there are no circular dependencies between entities."""

    def is_satisfied_by(self, **kwargs) -> bool:
        """Check for circular dependencies in the entity graph."""
        self.clear()

        entities_config = self.project_cfg.get("entities", {})
        if not entities_config:
            return True

        dependencies: dict[str, set[str]] = self.build_dependency_graph(entities_config)

        # Check for cycles using DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def check_if_has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    if check_if_has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle_path = " -> ".join(path[cycle_start:] + [neighbor])
                    self.add_error(f"Circular dependency detected: {cycle_path}", entity="configuration")
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for entity in dependencies:
            if entity not in visited:
                check_if_has_cycle(entity)

        return not self.has_errors()

    def build_dependency_graph(self, entities_config):
        dependencies: dict[str, set[str]] = {}
        for entity_name, entity_data in entities_config.items():
            deps = set(entity_data.get("depends_on", []) or [])
            source = entity_data.get("source", None)
            if source and isinstance(source, str):
                deps.add(source)

            dependencies[entity_name] = deps
        return dependencies


class DataSourceExistsSpecification(ProjectSpecification):
    """Validates that all referenced data sources exist in options.data_sources."""

    def is_satisfied_by(self, **kwargs) -> bool:
        """Check if all referenced data sources exist."""
        self.clear()

        entities_config = self.project_cfg.get("entities", {})
        options = self.project_cfg.get("options", {})
        data_sources = options.get("data_sources", {})

        if not entities_config:
            return True

        for entity_name, entity_data in entities_config.items():
            # Check entity data_source
            data_source = entity_data.get("data_source")
            if data_source and isinstance(data_source, str):
                if data_source not in data_sources:
                    self.add_error(
                        f"Entity '{entity_name}': references non-existent data source '{data_source}'",
                        entity=entity_name,
                        field="data_source",
                    )

            # Check append configurations
            append_configs = entity_data.get("append", []) or []
            if append_configs and not isinstance(append_configs, list):
                append_configs = [append_configs]

            for idx, append_cfg in enumerate(append_configs):
                append_data_source = append_cfg.get("data_source")
                if append_data_source and isinstance(append_data_source, str):
                    if append_data_source not in data_sources:
                        self.add_error(
                            f"Entity '{entity_name}', append item #{idx + 1}: references non-existent data source '{append_data_source}'",
                            entity=entity_name,
                            field="append",
                        )

        return not self.has_errors()


class EntitiesSpecification(ProjectSpecification):
    """Validates individual entities using various specifications."""

    def __init__(self, project_cfg: dict[str, Any]) -> None:
        super().__init__(project_cfg)
        self.entity_specifications: list[ProjectSpecification] = [EntitySpecification(project_cfg)]

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Validate the specified entity using all entity specifications."""
        for entity_spec in self.entity_specifications:
            for name in self.project_cfg.get("entities", {}).keys():
                entity_spec.is_satisfied_by(entity_name=name)
                self.merge(entity_spec)
        return not self.has_errors()


class IsProjectSpecification(ProjectSpecification):
    """Validates the project metadata section."""

    def is_satisfied_by(self, **kwargs) -> bool:
        """Validate the metadata section of the project configuration."""
        self.clear()

        metadata = self.project_cfg.get("metadata", {})
        if not metadata:
            self.add_error("Project metadata section is missing.", entity="metadata")
            return False

        if dotget(metadata, "type") != "shapeshifter-project":
            self.add_error("Project metadata must include 'type' with value 'shapeshifter-project'.", entity="metadata", field="type")

        return not self.has_errors()


class CompositeProjectSpecification(ProjectSpecification):
    """Composite specification that runs multiple project-level validation specifications.

    This is the main entry point for validating entire project configurations.
    """

    def __init__(self, project_cfg: dict[str, Any], specifications: list[ProjectSpecification] | None = None) -> None:
        super().__init__(project_cfg)
        self.specifications: list[ProjectSpecification] = specifications or self.get_default_specifications()

    def get_default_specifications(self) -> list[ProjectSpecification]:
        """Get the default set of project-level specifications.

        Override this method to customize the validation pipeline.

        Returns:
            List of specification instances to execute
        """
        return [
            EntitiesSpecification(self.project_cfg),
            CircularDependencySpecification(self.project_cfg),
            DataSourceExistsSpecification(self.project_cfg),
        ]

    def is_satisfied_by(self, **kwargs) -> bool:
        """Run all specifications and aggregate results."""
        self.clear()
        is_project_spec = IsProjectSpecification(self.project_cfg)
        is_project_valid: bool = is_project_spec.is_satisfied_by()
        self.merge(is_project_spec)

        if not is_project_valid:
            return False

        for spec in self.specifications:
            spec.is_satisfied_by()
            self.errors.extend(spec.errors)
            self.warnings.extend(spec.warnings)

        return not self.has_errors()
