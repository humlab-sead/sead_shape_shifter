---
agent: agent
description: Create a new FastAPI backend endpoint following Shape Shifter layer conventions
---

Create a new backend endpoint for `{FEATURE_DESCRIPTION}`:

### Requirements
- **Endpoint**: `{METHOD} /api/v1/{resource}/{action}`
- **Purpose**: `{DESCRIPTION}`
- **Input**: `{REQUEST_MODEL}`
- **Output**: `{RESPONSE_MODEL}`

### Implementation Steps

1. **Create Pydantic Models** (`backend/app/models/{resource}.py`)
   - Request model with Pydantic v2 validation
   - Response model with appropriate fields
   - Preserve raw `${ENV_VARS}` in models (resolution happens in mapper)
   - Use type hints and field validators

2. **Create Service** (`backend/app/services/{resource}_service.py`)
   - Implement business logic
   - Use dependency injection to avoid circular imports
   - Handle exceptions appropriately
   - Return domain/API models (not mixed)
   - Use `TYPE_CHECKING` for forward references

3. **Create/Update Mapper** (`backend/app/mappers/{resource}_mapper.py`)
   - `to_core()`: API → Core with env var and directive resolution
   - `to_api_config()`: Core → API (preserve directives)
   - Keep layer boundaries strict

4. **Create Router** (`backend/app/api/v1/endpoints/{resource}.py`)
   ```python
   from fastapi import APIRouter, HTTPException
   from backend.app.models.{resource} import {RequestModel}, {ResponseModel}
   from backend.app.services.{resource}_service import {ResourceService}

   router = APIRouter(prefix="/{resource}", tags=["{resource}"])

   @router.{method}("/{action}")
   async def {action}({params}) -> {ResponseModel}:
       try:
           pass  # implementation
       except Exception as e:
           raise HTTPException(status_code=500, detail=str(e))
   ```

5. **Register Router** — import and add to `backend/app/api/v1/api.py`

6. **Add Tests** (`backend/tests/test_{resource}.py`) — success, error, and validation cases

### Layer Boundary Rules
- API models: raw `${ENV_VARS}` and directives preserved
- Services: work with API entities, use mapper for Core conversion
- Mappers: resolve env vars + directives at API → Core boundary only
- Core: always fully resolved (no directives)

### Pattern Example
```python
api_project: Project = project_service.load_project(name)
core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)
# domain logic on core_project
updated: Project = ProjectMapper.to_api_config(core_project.cfg, name)
project_service.save_project(updated)
```

### Code Conventions
- Line length: 140 characters; format with Black + isort
- Type hints required on all functions
- Async where appropriate
- Dependency injection for circular imports

## Related Documentation
- [DESIGN.md](../../docs/DESIGN.md)
- [DEVELOPMENT.md](../../docs/DEVELOPMENT.md)
- [python.instructions.md](../instructions/python.instructions.md)
