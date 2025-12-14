"""Service for analyzing entity dependencies in configurations."""

from typing import Any

from loguru import logger

from app.models.config import Configuration


class DependencyServiceError(Exception):
    """Base exception for dependency service errors."""


class CircularDependencyError(DependencyServiceError):
    """Raised when circular dependencies are detected."""


class DependencyNode(dict):
    """Dependency graph node representation."""

    def __init__(self, name: str, depends_on: list[str], depth: int = 0):
        """Initialize dependency node."""
        super().__init__(name=name, depends_on=depends_on, depth=depth)


class DependencyGraph(dict):
    """Dependency graph representation."""

    def __init__(
        self,
        nodes: list[DependencyNode],
        edges: list[tuple[str, str]],
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

    def analyze_dependencies(self, config: Configuration) -> DependencyGraph:
        """
        Analyze dependencies in configuration.

        Args:
            config: Configuration to analyze

        Returns:
            Dependency graph with nodes, edges, and cycle information
        """
        entities = config.entities

        # Build dependency map
        dependency_map: dict[str, list[str]] = {}
        for entity_name, entity_data in entities.items():
            depends_on = []

            # Check source field
            if isinstance(entity_data, dict):
                source = entity_data.get("source")
                if source and source in entities:
                    depends_on.append(source)

                # Check depends_on field
                explicit_deps = entity_data.get("depends_on", [])
                if isinstance(explicit_deps, list):
                    depends_on.extend([dep for dep in explicit_deps if dep in entities])

                # Check foreign_keys
                foreign_keys = entity_data.get("foreign_keys", [])
                if isinstance(foreign_keys, list):
                    for fk in foreign_keys:
                        if isinstance(fk, dict):
                            remote_entity = fk.get("entity")
                            if remote_entity and remote_entity in entities:
                                depends_on.append(remote_entity)

            dependency_map[entity_name] = list(set(depends_on))  # Remove duplicates

        # Detect cycles
        cycles = self._find_cycles(dependency_map)
        has_cycles = len(cycles) > 0

        # Calculate topological order if no cycles
        topological_order = None if has_cycles else self._topological_sort(dependency_map)

        # Calculate depths for visualization
        depths = self._calculate_depths(dependency_map, topological_order)

        # Build nodes and edges
        nodes = [DependencyNode(name=name, depends_on=deps, depth=depths.get(name, 0)) for name, deps in dependency_map.items()]

        edges = [(entity, dep) for entity, deps in dependency_map.items() for dep in deps]

        logger.debug(f"Analyzed dependencies: {len(nodes)} nodes, {len(edges)} edges, " f"cycles: {has_cycles}")

        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            has_cycles=has_cycles,
            cycles=cycles,
            topological_order=topological_order,
        )

    def check_circular_dependencies(self, config: Configuration) -> dict[str, Any]:
        """
        Check for circular dependencies in configuration.

        Args:
            config: Configuration to check

        Returns:
            Dictionary with has_cycles flag and list of cycles
        """
        graph = self.analyze_dependencies(config)

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
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependency_map.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
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
        in_degree = {node: 0 for node in dependency_map}

        # Calculate in-degrees
        for deps in dependency_map.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        # Start with nodes that have no dependencies
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
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
_dependency_service: DependencyService | None = None


def get_dependency_service() -> DependencyService:
    """Get singleton DependencyService instance."""
    global _dependency_service
    if _dependency_service is None:
        _dependency_service = DependencyService()
    return _dependency_service
