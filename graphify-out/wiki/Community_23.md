# Community 23

> 52 nodes · cohesion 0.07

## Key Concepts

- **.extract()** (23 connections) — `backend/app/services/dependency_service.py`
- **DataIntegrityError** (22 connections) — `backend/app/exceptions.py`
- **CircularDependencyError** (19 connections) — `backend/app/exceptions.py`
- **BaseSourceNodeExtractor** (16 connections) — `backend/app/services/dependency_service.py`
- **DependencyGraph** (14 connections) — `backend/app/services/dependency_service.py`
- **.analyze_dependencies()** (14 connections) — `backend/app/services/dependency_service.py`
- **SourceNode** (11 connections) — `backend/app/services/dependency_service.py`
- **DependencyNode** (10 connections) — `backend/app/services/dependency_service.py`
- **SourceNodeService** (10 connections) — `backend/app/services/dependency_service.py`
- **.__init__()** (9 connections) — `backend/app/services/dependency_service.py`
- **Any** (8 connections) — `backend/app/services/dependency_service.py`
- **NullSourceNodeExtractor** (8 connections) — `backend/app/services/dependency_service.py`
- **CsvFileSourceNodeExtractor** (8 connections) — `backend/app/services/dependency_service.py`
- **ExcelFileSourceNodeExtractor** (8 connections) — `backend/app/services/dependency_service.py`
- **MaterializedFixedSourceNodeExtractor** (8 connections) — `backend/app/services/dependency_service.py`
- **SqlSourceNodeExtractor** (8 connections) — `backend/app/services/dependency_service.py`
- **Project** (7 connections) — `backend/app/services/dependency_service.py`
- **.get()** (6 connections) — `backend/app/services/dependency_service.py`
- **.check_circular_dependencies()** (5 connections) — `backend/app/services/dependency_service.py`
- **._get_filename_from_options()** (5 connections) — `backend/app/services/dependency_service.py`
- **.get_extractor()** (4 connections) — `backend/app/services/dependency_service.py`
- **._create_file_node()** (4 connections) — `backend/app/services/dependency_service.py`
- **dict** (3 connections)
- **Check for circular dependencies in project.      Args:         name: Project nam** (2 connections) — `backend/app/api/v1/endpoints/validation.py`
- **Base class for data integrity violations.** (1 connections) — `backend/app/exceptions.py`
- *... and 27 more nodes in this community*

## Relationships

- [[Community 144]] (18 shared connections)
- [[Community 5]] (16 shared connections)
- [[Community 14]] (12 shared connections)
- [[Community 66]] (6 shared connections)
- [[Community 1]] (5 shared connections)
- [[Community 135]] (3 shared connections)
- [[Community 81]] (1 shared connections)
- [[Community 0]] (1 shared connections)

## Source Files

- `backend/app/api/v1/endpoints/validation.py`
- `backend/app/exceptions.py`
- `backend/app/services/dependency_service.py`

## Audit Trail

- EXTRACTED: 180 (69%)
- INFERRED: 80 (31%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*