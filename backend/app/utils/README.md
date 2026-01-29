# Backend Utilities

This directory contains reusable utility modules for the Shape Shifter backend.

## Modules

### `graph.py` - Graph Algorithms

Pure functions for dependency graph analysis. Originally refactored from `dependency_service.py` to improve testability and reduce conditional logic.

**Functions:**

- **`find_cycles(dependency_map: dict[str, list[str]]) -> list[list[str]]`**
  - Detects all cycles in a dependency graph using depth-first search (DFS)
  - Returns list of cycles, where each cycle is a list of entity names forming the cycle
  - Time complexity: O(V + E) where V = vertices (entities), E = edges (dependencies)
  - Used by: `DependencyService.analyze_dependencies()`
  - Tests: `backend/tests/utils/test_graph.py::TestFindCycles`

- **`topological_sort(dependency_map: dict[str, list[str]]) -> list[str]`**
  - Performs topological sort using Kahn's algorithm
  - Returns entities in dependency order (dependencies before dependents)
  - Should only be called when no cycles exist
  - Time complexity: O(V + E)
  - Used by: `DependencyService.analyze_dependencies()`, `TaskService` (dependency-order strategy)
  - Tests: `backend/tests/utils/test_graph.py::TestTopologicalSort`

- **`calculate_depths(dependency_map: dict[str, list[str]], topological_order: list[str] | None) -> dict[str, int]`**
  - Calculates depth (distance from root) for each node in dependency graph
  - Uses topological order for accurate calculation when available
  - Falls back to heuristic (depth 1 for nodes with dependencies) when cycles exist
  - Used by: `DependencyService.analyze_dependencies()` for graph visualization
  - Tests: `backend/tests/utils/test_graph.py::TestCalculateDepths`

**Design Philosophy:**
- Pure functions with no side effects
- No enum-based conditional logic
- Framework-agnostic (can be used outside FastAPI context)
- Easily testable with simple input/output

---

### `sql.py` - SQL Parsing Utilities

SQL parsing and analysis utilities using the `sqlparse` library.

**Functions:**

- **`extract_tables(sql: str) -> list[str]`**
  - Extracts table names from SQL query strings
  - Handles FROM clauses, various JOIN types, subqueries, CTEs
  - Returns sorted list of unique table names
  - Supports schema-qualified names (returns table name only)
  - Handles table aliases correctly
  - Used by: `SqlSourceNodeExtractor` in `dependency_service.py`
  - Tests: `backend/tests/utils/test_sql.py::TestExtractTables`

**Supported SQL Features:**
- Simple SELECT with FROM
- INNER JOIN, LEFT JOIN, RIGHT JOIN, FULL JOIN, CROSS JOIN
- Comma-separated tables in FROM clause
- Subqueries
- Common Table Expressions (CTEs)
- Schema-qualified table names (`schema.table`)
- Table aliases (`users AS u`, `users u`)

**Limitations:**
- May not extract tables from UPDATE/DELETE statements without FROM clause
- Complex nested subqueries might have edge cases
- Relies on sqlparse's parsing accuracy

**Design Philosophy:**
- Single-purpose function with clear responsibility
- Library-based parsing (sqlparse) instead of regex
- Returns sorted list for consistent output
- Handles SQL case-insensitivity

---

## Usage Examples

### Graph Algorithms

```python
from backend.app.utils.graph import find_cycles, topological_sort, calculate_depths

# Define dependency map
dependency_map = {
    "base_entity": [],
    "derived1": ["base_entity"],
    "derived2": ["base_entity"],
    "final": ["derived1", "derived2"],
}

# Check for cycles
cycles = find_cycles(dependency_map)
if cycles:
    print(f"Circular dependencies found: {cycles}")
else:
    print("No cycles detected")

# Get processing order
order = topological_sort(dependency_map)
print(f"Processing order: {order}")
# Output: ['base_entity', 'derived1', 'derived2', 'final']

# Calculate depths for visualization
depths = calculate_depths(dependency_map, order)
print(f"Depths: {depths}")
# Output: {'base_entity': 0, 'derived1': 1, 'derived2': 1, 'final': 2}
```

### SQL Table Extraction

```python
from backend.app.utils.sql import extract_tables

sql = """
SELECT u.name, COUNT(o.id) as order_count
FROM users u
INNER JOIN orders o ON u.id = o.user_id
LEFT JOIN addresses a ON u.id = a.user_id
WHERE u.active = true
GROUP BY u.name
"""

tables = extract_tables(sql)
print(f"Tables used: {tables}")
# Output: ['addresses', 'orders', 'users']
```

---

## Testing

Both modules have comprehensive test coverage:

```bash
# Run all utility tests
uv run pytest backend/tests/utils/ -v

# Run specific module tests
uv run pytest backend/tests/utils/test_graph.py -v
uv run pytest backend/tests/utils/test_sql.py -v
```

**Test Coverage:**
- **graph.py**: 15+ test cases covering cycles, topological sort, depth calculation
- **sql.py**: 18+ test cases covering various SQL patterns and edge cases

---

## Design Principles

These utilities follow Shape Shifter's backend patterns:

1. **Separation of Concerns**: Pure utility functions separated from service logic
2. **Testability**: No dependencies on application state or config
3. **Reusability**: Can be imported and used in multiple services
4. **Type Safety**: Full type hints for all function signatures
5. **No Side Effects**: Pure functions that don't modify input or global state
6. **Framework Agnostic**: Can work outside FastAPI/Pydantic context

---

## Migration Notes

These utilities were refactored from `dependency_service.py` (January 2026) to:
- Improve testability (pure functions vs. instance methods)
- Reduce complexity in DependencyService
- Enable reuse in other services
- Eliminate enum-based conditional logic

**Original locations:**
- `DependencyService._find_cycles()` → `graph.find_cycles()`
- `DependencyService._topological_sort()` → `graph.topological_sort()`
- `DependencyService._calculate_depths()` → `graph.calculate_depths()`
- SQL table extraction logic → `sql.extract_tables()`

**API compatibility:** The public `DependencyService` API remains unchanged; these are internal implementation details.
