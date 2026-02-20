# Add Backend Endpoint Prompt

Create a new FastAPI endpoint following Shape Shifter conventions.

## Prompt Template

```
Create a new backend endpoint for {FEATURE_DESCRIPTION}:

### Requirements
- **Endpoint**: {METHOD} /api/v1/{resource}/{action}
- **Purpose**: {DESCRIPTION}
- **Input**: {REQUEST_MODEL}
- **Output**: {RESPONSE_MODEL}

### Implementation Steps

1. **Create Pydantic Models** (`backend/app/models/{resource}.py`)
   - Request model with Pydantic v2 validation
   - Response model with appropriate fields
   - Preserve raw `${ENV_VARS}` in models (resolution in mapper)
   - Use type hints and field validators

2. **Create Service** (`backend/app/services/{resource}_service.py`)
   - Implement business logic
   - Use dependency injection for circular import avoidance
   - Handle exceptions appropriately
   - Return domain/API models (not mixed)
   - Use TYPE_CHECKING for forward references

3. **Create/Update Mapper** (`backend/app/mappers/{resource}_mapper.py`)
   - Implement `to_core()` - API → Core with env var resolution
   - Implement `to_api_config()` - Core → API
   - Handle directive resolution (@include:, @value:)
   - Keep layer boundaries clear

4. **Create Router** (`backend/app/api/v1/endpoints/{resource}.py`)
   ```python
   from fastapi import APIRouter, HTTPException, status
   from backend.app.models.{resource} import {RequestModel}, {ResponseModel}
   from backend.app.services.{resource}_service import {ResourceService}
   
   router = APIRouter(prefix="/{resource}", tags=["{resource}"])
   
   @router.{method}("/{action}")
   async def {action}({params}) -> {ResponseModel}:
       """
       {DESCRIPTION}
       
       Args:
           {param_descriptions}
       
       Returns:
           {ResponseModel}: {return_description}
       
       Raises:
           HTTPException: {error_conditions}
       """
       try:
           # Implementation
           pass
       except Exception as e:
           raise HTTPException(status_code=500, detail=str(e))
   ```

5. **Register Router** (`backend/app/api/v1/api.py`)
   - Import router
   - Add to `api_router.include_router()`

6. **Add Tests** (`backend/tests/test_{resource}.py`)
   - Use FastAPI TestClient
   - Test success cases
   - Test error cases
   - Mock dependencies appropriately

### Layer Boundary Rules ⭐
- API models: Raw `${ENV_VARS}`, directives preserved
- Services: Work with API entities, use mapper for Core conversion
- Mappers: Resolve env vars + directives at API → Core boundary
- Core: Always fully resolved (no directives)

### Pattern Example
```python
# Service layer
api_project: Project = project_service.load_project(name)
core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)
# ... domain logic on core_project ...
updated: Project = ProjectMapper.to_api_config(core_project.cfg, name)
project_service.save_project(updated)
```

### Code Conventions
- Line length: 140 characters
- Format with Black + isort
- Type hints required
- Use dependency injection for circular imports
- Async functions where appropriate
```

## Example Usage

```
Create a new backend endpoint for exporting entity data:

Requirements:
- Endpoint: POST /api/v1/entities/export
- Purpose: Export normalized entity data to CSV/Excel
- Input: ProjectName, EntityNames, ExportFormat
- Output: FileDownloadResponse with path

[... follow full implementation steps ...]
```

## Related Documentation
- [AGENTS.md](../../AGENTS.md#common-implementation-tasks)
- [BACKEND_API.md](../../docs/BACKEND_API.md)
- [Layer Boundary Architecture](../../AGENTS.md#layer-boundary-architecture-awesome-rule-)
