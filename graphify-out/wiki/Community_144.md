# Community 144

> 20 nodes · cohesion 0.14

## Key Concepts

- **dependency_service.py** (30 connections) — `backend/app/services/dependency_service.py`
- **__init__.py** (9 connections) — `backend/app/utils/__init__.py`
- **sql.py** (7 connections) — `backend/app/utils/sql.py`
- **extract_tables()** (7 connections) — `backend/app/utils/sql.py`
- **convert_ruamel_types()** (6 connections) — `backend/app/utils/yaml_utils.py`
- **find_cycles()** (5 connections) — `backend/app/utils/graph.py`
- **topological_sort()** (5 connections) — `backend/app/utils/graph.py`
- **calculate_depths()** (5 connections) — `backend/app/utils/graph.py`
- **graph.py** (4 connections) — `backend/app/utils/graph.py`
- **yaml_utils.py** (3 connections) — `backend/app/utils/yaml_utils.py`
- **Service for analyzing entity dependencies in projects.** (1 connections) — `backend/app/services/dependency_service.py`
- **Service for analyzing entity dependencies.** (1 connections) — `backend/app/services/dependency_service.py`
- **Utility modules for the backend application.  This package contains reusable uti** (1 connections) — `backend/app/utils/__init__.py`
- **Find all cycles in dependency graph using DFS.      Args:         dependency_map** (1 connections) — `backend/app/utils/graph.py`
- **Perform topological sort on dependency graph.      Args:         dependency_map:** (1 connections) — `backend/app/utils/graph.py`
- **Calculate depth of each node in dependency graph.      Args:         dependency_** (1 connections) — `backend/app/utils/graph.py`
- **Extract table names from an SQL query using sqlparse.      Returns a sorted, ded** (1 connections) — `backend/app/utils/sql.py`
- **Any** (1 connections) — `backend/app/utils/yaml_utils.py`
- **Utilities for YAML processing and type conversion.  DEPRECATION NOTE: convert_ru** (1 connections) — `backend/app/utils/yaml_utils.py`
- **DEPRECATED: No longer needed. Kept for backward compatibility.      Recursively** (1 connections) — `backend/app/utils/yaml_utils.py`

## Relationships

- [[Community 23]] (18 shared connections)
- [[Community 131]] (6 shared connections)
- [[Community 5]] (5 shared connections)
- [[Community 1]] (2 shared connections)
- [[Community 0]] (1 shared connections)
- [[Community 135]] (1 shared connections)
- [[Community 24]] (1 shared connections)
- [[Community 14]] (1 shared connections)
- [[Community 46]] (1 shared connections)
- [[Community 26]] (1 shared connections)

## Source Files

- `backend/app/services/dependency_service.py`
- `backend/app/utils/__init__.py`
- `backend/app/utils/graph.py`
- `backend/app/utils/sql.py`
- `backend/app/utils/yaml_utils.py`

## Audit Trail

- EXTRACTED: 84 (92%)
- INFERRED: 7 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*