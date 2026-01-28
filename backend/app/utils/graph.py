def find_cycles(dependency_map: dict[str, list[str]]) -> list[list[str]]:
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


def topological_sort(dependency_map: dict[str, list[str]]) -> list[str]:
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


def calculate_depths(dependency_map: dict[str, list[str]], topological_order: list[str] | None) -> dict[str, int]:
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
