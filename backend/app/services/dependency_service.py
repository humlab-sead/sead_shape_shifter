"""Service for analyzing entity dependencies in projects."""

from typing import Any

from loguru import logger

from backend.app.models.project import Project
from src.model import ShapeShiftProject


class DependencyServiceError(Exception):
    """Base exception for dependency service errors."""


class CircularDependencyError(DependencyServiceError):
    """Raised when circular dependencies are detected."""


class DependencyNode(dict):
    """Dependency graph node representation."""

    def __init__(self, name: str, depends_on: list[str], depth: int = 0, entity_type: str | None = None):
        """Initialize dependency node."""
        super().__init__(name=name, depends_on=depends_on, depth=depth, type=entity_type)


class DependencyGraph(dict):
    """Dependency graph representation."""

    def __init__(
        self,
        nodes: list[DependencyNode],
        edges: list[dict[str, Any]],
        has_cycles: bool,
        cycles: list[list[str]],
        topological_order: list[str] | None,
    ):
        """Initialize dependency graph."""
        super().__init__(
            nodes=nodes,
            edges=edges,
            has_cycles=has_cycles,
            cycles=cycles,
            topological_order=topological_order,
        )


class DependencyService:
    """Service for analyzing entity dependencies."""

    def analyze_dependencies(self, api_project: Project) -> DependencyGraph:
        """
        Analyze dependencies in project.

        Args:
            api_project: Project to analyze

        Returns:
            Dependency graph with nodes, edges, and cycle information
        """
        project = ShapeShiftProject(
            cfg={"entities": api_project.entities, "options": api_project.options}, filename=api_project.filename or ""
        )

        dependency_map: dict[str, list[str]] = {
            entity_name: list(project.get_table(entity_name).depends_on or []) for entity_name in api_project.entities
        }

        # Detect cycles
        cycles: list[list[str]] = self._find_cycles(dependency_map)
        has_cycles: bool = len(cycles) > 0

        # Calculate topological order if no cycles
        topological_order: None | list[str] = None if has_cycles else self._topological_sort(dependency_map)

        # Calculate depths for visualization
        depths: dict[str, int] = self._calculate_depths(dependency_map, topological_order)

        allowed_entity_types = {"data", "sql", "fixed"}
        nodes: list[DependencyNode] = []
        for name, deps in dependency_map.items():
            entity_type = api_project.entities.get(name, {}).get("type")
            normalized_type = entity_type if entity_type in allowed_entity_types else None
            nodes.append(DependencyNode(name=name, depends_on=deps, depth=depths.get(name, 0), entity_type=normalized_type))

        # Build edges with foreign key information
        edges: list[dict[str, Any]] = []
        for entity_name in api_project.entities:
            entity_config = api_project.entities[entity_name]
            foreign_keys = entity_config.get("foreign_keys") or []

            for fk in foreign_keys:
                target_entity = fk.get("entity")
                if target_entity:
                    local_keys = fk.get("local_keys", [])
                    remote_keys = fk.get("remote_keys", [])

                    # Format keys for display
                    if isinstance(local_keys, list) and isinstance(remote_keys, list):
                        keys_label = " → ".join(
                            [", ".join(local_keys) if local_keys else "", ", ".join(remote_keys) if remote_keys else ""]
                        )
                    else:
                        keys_label = f"{local_keys} → {remote_keys}"

                    edges.append(
                        {
                            "source": entity_name,
                            "target": target_entity,
                            "local_keys": local_keys,
                            "remote_keys": remote_keys,
                            "label": keys_label,
                        }
                    )

        logger.debug(f"Analyzed dependencies: {len(nodes)} nodes, {len(edges)} edges, " f"cycles: {has_cycles}")

        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            has_cycles=has_cycles,
            cycles=cycles,
            topological_order=topological_order,
        )

    def check_circular_dependencies(self, project: Project) -> dict[str, Any]:
        """
        Check for circular dependencies in project.

        Args:
            config: Project to check

        Returns:
            Dictionary with has_cycles flag and list of cycles
        """
        graph = self.analyze_dependencies(project)

        return {
            "has_cycles": graph["has_cycles"],
            "cycles": graph["cycles"],
            "cycle_count": len(graph["cycles"]),
        }

    def _find_cycles(self, dependency_map: dict[str, list[str]]) -> list[list[str]]:
        """
        Find all cycles in dependency graph using DFS.

        Args:
            dependency_map: Entity name -> list of dependencies

        Returns:
            List of cycles, where each cycle is a list of entity names
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> None:
            """Depth-first search to find cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependency_map.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start: int = path.index(neighbor)
                    cycle: list[str] = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for node in dependency_map:
            if node not in visited:
                dfs(node)

        return cycles

    def _topological_sort(self, dependency_map: dict[str, list[str]]) -> list[str]:
        """
        Perform topological sort on dependency graph.

        Args:
            dependency_map: Entity name -> list of dependencies

        Returns:
            Topologically sorted list of entity names
        """
        in_degree: dict[str, int] = {node: 0 for node in dependency_map}

        # Calculate in-degrees
        for deps in dependency_map.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        # Start with nodes that have no dependencies
        queue: list[str] = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node: str = queue.pop(0)
            result.append(node)

            # Reduce in-degree for neighbors
            for neighbor in dependency_map.get(node, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        return result

    def _calculate_depths(self, dependency_map: dict[str, list[str]], topological_order: list[str] | None) -> dict[str, int]:
        """
        Calculate depth of each node in dependency graph.

        Args:
            dependency_map: Entity name -> list of dependencies
            topological_order: Topologically sorted entity names (if no cycles)

        Returns:
            Dictionary mapping entity name to depth level
        """
        depths = {node: 0 for node in dependency_map}

        if topological_order:
            # Process in topological order
            for node in topological_order:
                for dep in dependency_map.get(node, []):
                    if dep in depths:
                        depths[dep] = max(depths[dep], depths[node] + 1)
        else:
            # If there are cycles, use simple heuristic
            for node, deps in dependency_map.items():
                if deps:
                    depths[node] = 1

        return depths


# Singleton instance
_dependency_service: DependencyService | None = None  # pylint: disable=invalid-name


def get_dependency_service() -> DependencyService:
    """Get singleton DependencyService instance."""
    global _dependency_service  # pylint: disable=global-statement
    if _dependency_service is None:
        _dependency_service = DependencyService()
    return _dependency_service
