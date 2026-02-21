# Error Handling Architecture

## Design Principles

Shape Shifter uses a **domain-driven error handling** approach that provides fault-tolerant operation with actionable user guidance.

### Core Principles

1. **Domain Knowledge Lives in Exceptions**
   - Error types encode semantic meaning (ForeignKeyError, CircularDependencyError)
   - Each exception carries structured metadata (message, tips, context)
   - HTTP layer only maps exception types → status codes (no string parsing)

2. **Separation of Concerns**
   - **Service Layer**: Raises domain exceptions with business context
   - **API Layer**: Maps exceptions to HTTP responses
   - **Frontend**: Displays structured error data

3. **User-Centric Error Messages**
   - Clear explanation of what went wrong
   - Actionable troubleshooting steps (tips)
   - Relevant context (entity names, values)
   - Recovery guidance (is it fixable?)

4. **Structured Error Responses**
   - Consistent JSON format: `{error_type, message, tips, recoverable, context}`
   - No string parsing or pattern matching
   - Type-safe error handling throughout stack

## Exception Hierarchy

```
DomainException (base)
├── DataIntegrityError          # Corrupted/invalid data
│   ├── ForeignKeyError         # Invalid FK definitions
│   └── SchemaValidationError   # Entity schema issues
├── DependencyError             # Entity relationship issues
│   ├── CircularDependencyError # Cyclic dependencies
│   └── MissingDependencyError  # Missing entity refs
├── ValidationError             # Business rule violations
│   ├── ConstraintViolationError # Failed constraints
│   └── ConfigurationError      # Invalid project config
└── ResourceError               # Resource access issues
    ├── ResourceNotFoundError   # Not found (404)
    └── ResourceConflictError   # Already exists (409)
```

### Exception Attributes

Every `DomainException` carries:
- **message**: Human-readable error description
- **tips**: List of actionable troubleshooting steps
- **recoverable**: Boolean indicating if user can fix without code changes
- **context**: Dict with debugging details (entity names, values, etc.)

### Example Exception Usage

```python
# Service layer raises domain exception
from backend.app.exceptions import ForeignKeyError

def validate_foreign_key(entity: str, fk_def: dict) -> None:
    """Validate FK definition structure."""
    if not isinstance(fk_def.get("local_keys"), list):
        raise ForeignKeyError(
            message=f"Foreign key in '{entity}' has invalid local_keys: expected list, got {type(fk_def['local_keys']).__name__}",
            entity=entity,
            foreign_key=fk_def,
            tips=[
                "Change local_keys from dict to list: local_keys: ['column1', 'column2']",
                "Ensure all key names are strings, not nested structures",
                "Check YAML syntax - keys should be a sequence (- item)",
            ]
        )
```

## Data Flow

### 1. Service Layer → Exception

```python
# backend/app/services/dependency_service.py

from backend.app.exceptions import ForeignKeyError, CircularDependencyError

def analyze_dependencies(self, project_name: str) -> DependencyGraph:
    """Analyze entity dependencies with domain error handling."""
    try:
        project = ShapeShiftProject.load(project_name)
    except Exception as e:
        raise DataIntegrityError(
            message=f"Failed to load project '{project_name}': {e}",
            context={"project": project_name},
        ) from e
    
    # Validate foreign keys
    for entity_name, entity_config in project.entities.items():
        for fk in entity_config.get("foreign_keys", []):
            if not isinstance(fk.get("local_keys"), list):
                raise ForeignKeyError(
                    message=f"Invalid FK in '{entity_name}'",
                    entity=entity_name,
                    foreign_key=fk,
                )
    
    # Detect circular dependencies
    cycle = detect_cycle(graph)
    if cycle:
        raise CircularDependencyError(
            message="Circular dependency detected",
            cycle=cycle,
        )
```

### 2. API Layer → HTTP Response

```python
# backend/app/utils/error_handlers.py

from backend.app.exceptions import (
    DomainException,
    DataIntegrityError,
    ForeignKeyError,
    ResourceNotFoundError,
)

def handle_endpoint_errors(func):
    """Map domain exceptions to HTTP status codes."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        
        # 404 Not Found
        except ResourceNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=e.to_dict()  # Structured response
            )
        
        # 400 Bad Request (data integrity, validation)
        except (DataIntegrityError, ValidationError) as e:
            raise HTTPException(
                status_code=400,
                detail=e.to_dict()
            )
        
        # 409 Conflict
        except ResourceConflictError as e:
            raise HTTPException(
                status_code=409,
                detail=e.to_dict()
            )
        
        # 500 Internal Server Error (unexpected)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error_type": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "tips": ["Check server logs for details"],
                    "recoverable": False,
                }
            )
    
    return wrapper
```

### 3. Frontend → User Display

```typescript
// frontend/src/utils/errors.ts

interface ErrorResponse {
  error_type: string
  message: string
  tips: string[]
  recoverable: boolean
  context?: Record<string, any>
}

export function formatErrorMessage(error: any): ErrorResponse {
  // Backend sends structured error in response.data.detail
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail
    
    // Structured error response
    if (typeof detail === 'object' && detail.error_type) {
      return detail as ErrorResponse
    }
    
    // Legacy string error
    if (typeof detail === 'string') {
      return {
        error_type: 'Error',
        message: detail,
        tips: [],
        recoverable: true,
      }
    }
  }
  
  // Network or unexpected error
  return {
    error_type: 'NetworkError',
    message: error.message || 'An unexpected error occurred',
    tips: ['Check network connection', 'Refresh page and try again'],
    recoverable: true,
  }
}
```

```vue
<!-- frontend/src/components/common/ErrorAlert.vue -->
<template>
  <v-alert type="error" variant="tonal">
    <div class="text-subtitle-2 mb-2">{{ error.message }}</div>
    
    <div v-if="error.tips?.length" class="mt-3">
      <div class="text-caption font-weight-bold mb-1">Troubleshooting:</div>
      <ul class="text-caption pl-4">
        <li v-for="(tip, i) in error.tips" :key="i">{{ tip }}</li>
      </ul>
    </div>
    
    <div v-if="error.context" class="mt-2 text-caption">
      <code>{{ JSON.stringify(error.context, null, 2) }}</code>
    </div>
  </v-alert>
</template>

<script setup lang="ts">
import type { ErrorResponse } from '@/utils/errors'

defineProps<{
  error: ErrorResponse
}>()
</script>
```

## Benefits

### ✅ Type Safety
- No brittle string parsing
- IDE autocomplete for exception types
- TypeScript interfaces for error responses

### ✅ Maintainability
- Domain knowledge centralized in exceptions
- Easy to add new error types
- Clear separation of layers

### ✅ User Experience
- Consistent error display
- Actionable troubleshooting steps
- Context-aware guidance

### ✅ Testability
- Mock specific exception types
- Verify error messages and tips
- Test HTTP status code mappings

### ✅ Debuggability
- Structured logging with context
- Exception chaining preserves stack traces
- Rich metadata for troubleshooting

## Anti-Patterns to Avoid

### ❌ String Parsing in HTTP Layer
```python
# DON'T DO THIS
error_message = str(e)
if "sequence item" in error_message and "dict" in error_message:
    tips = ["Check your foreign keys"]
```

**Why:** Brittle, language-dependent, violates separation of concerns

**Instead:** Raise `ForeignKeyError` in service layer with tips

### ❌ Generic Exceptions with String Messages
```python
# DON'T DO THIS
raise Exception("Invalid foreign key format")
```

**Why:** No type safety, no structured metadata, poor UX

**Instead:** Raise `ForeignKeyError` with tips and context

### ❌ HTTP Status Logic in Services
```python
# DON'T DO THIS
def service_method():
    if not found:
        raise HTTPException(status_code=404, detail="Not found")
```

**Why:** Couples service to HTTP, can't use in CLI/scripts

**Instead:** Raise `ResourceNotFoundError`, let API layer map to 404

### ❌ Frontend String Parsing
```typescript
// DON'T DO THIS
if (error.message.includes("sequence item")) {
  tips = ["Check foreign keys"]
}
```

**Why:** Brittle, duplicates logic, hard to maintain

**Instead:** Backend sends structured error with tips field

## Migration Strategy

### Phase 1: Foundation (Current)
- ✅ Create `backend/app/exceptions.py` with hierarchy
- ✅ Document architecture in this file
- ✅ Rollback pattern matching in error handlers

### Phase 2: Implement Domain (Dependencies)
- Update `DependencyService` to raise domain exceptions
- Remove string-based error enhancement
- Test with corrupted FK data

### Phase 3: Update Error Handlers
- Refactor `error_handlers.py` to map exception types
- Remove pattern matching logic
- Add structured response formatting

### Phase 4: Frontend Integration
- Update `errors.ts` to expect structured responses
- Enhance `ErrorAlert.vue` with tips display
- Update stores to use new error format

### Phase 5: Expand Coverage
- Apply pattern to other services (validation, query, project)
- Create service-specific exception subclasses
- Add integration tests

### Phase 6: Validation & Refinement
- User testing with real error scenarios
- Iterate on tips quality
- Add more context fields as needed

## Example: Complete Flow

### Scenario: User has corrupted FK definition

**1. Service Layer**
```python
# backend/app/services/dependency_service.py
def analyze_dependencies(self, project_name: str):
    for entity, config in project.entities.items():
        for fk in config.get("foreign_keys", []):
            if isinstance(fk.get("local_keys"), dict):
                raise ForeignKeyError(
                    message=f"Foreign key 'local_keys' in entity '{entity}' must be a list, not dict",
                    entity=entity,
                    foreign_key=fk,
                    tips=[
                        "Change format from 'local_keys: {key: value}' to 'local_keys: [key]'",
                        "Ensure YAML uses sequence syntax: '- item'",
                    ]
                )
```

**2. API Layer**
```python
# backend/app/api/v1/endpoints/dependencies.py
@router.get("/{project_name}/dependencies")
@handle_endpoint_errors  # Maps ForeignKeyError → 400
async def get_dependencies(project_name: str):
    return dependency_service.analyze_dependencies(project_name)
```

**3. HTTP Response**
```json
{
  "status": 400,
  "detail": {
    "error_type": "ForeignKeyError",
    "message": "Foreign key 'local_keys' in entity 'site' must be a list, not dict",
    "tips": [
      "Change format from 'local_keys: {key: value}' to 'local_keys: [key]'",
      "Ensure YAML uses sequence syntax: '- item'"
    ],
    "recoverable": true,
    "context": {
      "entity": "site",
      "foreign_key": {
        "entity": "location",
        "local_keys": {"name": "location_name"}
      }
    }
  }
}
```

**4. Frontend Display**
```
❌ Error

Foreign key 'local_keys' in entity 'site' must be a list, not dict

Troubleshooting:
• Change format from 'local_keys: {key: value}' to 'local_keys: [key]'
• Ensure YAML uses sequence syntax: '- item'

Context:
{
  "entity": "site",
  "foreign_key": {...}
}
```

## Testing Strategy

### Unit Tests: Services
```python
def test_foreign_key_validation():
    """Service raises ForeignKeyError with tips."""
    with pytest.raises(ForeignKeyError) as exc_info:
        service.validate_foreign_key("site", {"local_keys": {}})
    
    assert exc_info.value.entity == "site"
    assert "list" in exc_info.value.message
    assert len(exc_info.value.tips) > 0
```

### Integration Tests: API
```python
def test_dependency_endpoint_error_format():
    """API returns structured error response."""
    response = client.get("/api/v1/projects/bad/dependencies")
    
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_type"] == "ForeignKeyError"
    assert isinstance(detail["tips"], list)
    assert detail["recoverable"] is True
```

### E2E Tests: Frontend
```typescript
test('displays foreign key error with tips', async () => {
  // Mock API error response
  mockApi.get('/dependencies').replyOnce(400, {
    detail: {
      error_type: 'ForeignKeyError',
      message: 'Invalid FK',
      tips: ['Fix your keys'],
      recoverable: true,
    }
  })
  
  await wrapper.vm.loadDependencies()
  
  expect(wrapper.find('.error-message').text()).toBe('Invalid FK')
  expect(wrapper.find('.tips-list').exists()).toBe(true)
})
```

## Summary

This architecture provides:
- **Clarity**: Exceptions encode semantic meaning
- **Actionability**: Tips guide users to resolution
- **Maintainability**: Type-safe, layered design
- **Extensibility**: Easy to add new exception types
- **User Experience**: Consistent, helpful error messages

The key insight: **Errors are part of the domain model**, not just technical failures. Treat them with the same care as business logic.
