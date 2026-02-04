# Error Handling Implementation Plan

## Overview

This plan guides the systematic implementation of the domain exception hierarchy across Shape Shifter, replacing brittle string-parsing error handling with type-safe, user-centric domain exceptions.

## Prerequisites

- ✅ **Design Complete**: Exception hierarchy defined in `backend/app/exceptions.py`
- ✅ **Architecture Documented**: Pattern described in `docs/ERROR_HANDLING_ARCHITECTURE.md`
- ✅ **Rollback Complete**: Pattern matching removed from error handlers

## Implementation Phases

### Phase 1: Backend Foundation (1-2 hours)

#### 1.1 Update Error Handler Decorator

**File**: `backend/app/utils/error_handlers.py`

**Changes**:
- Import domain exceptions from `backend.app.exceptions`
- Map exception types to HTTP status codes:
  - `ResourceNotFoundError` → 404
  - `DataIntegrityError`, `ValidationError` → 400
  - `ResourceConflictError` → 409
  - `DependencyError` → 500 (or 400 for validation issues)
- Return `e.to_dict()` for structured responses
- Remove all string pattern matching

**Example**:
```python
from backend.app.exceptions import (
    DomainException,
    DataIntegrityError,
    ForeignKeyError,
    ResourceNotFoundError,
    ResourceConflictError,
    ValidationError,
)

def handle_endpoint_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        
        # Let HTTPException pass through
        except HTTPException:
            raise
        
        # 404 Not Found
        except ResourceNotFoundError as e:
            logger.debug(f"Resource not found: {e}")
            raise HTTPException(status_code=404, detail=e.to_dict())
        
        # 400 Bad Request
        except (DataIntegrityError, ValidationError) as e:
            logger.warning(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail=e.to_dict())
        
        # 409 Conflict
        except ResourceConflictError as e:
            logger.warning(f"Resource conflict: {e}")
            raise HTTPException(status_code=409, detail=e.to_dict())
        
        # 500 Internal Server Error (unexpected)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error_type": "InternalServerError",
                    "message": str(e),
                    "tips": ["Check server logs for details"],
                    "recoverable": False,
                    "context": {},
                }
            )
    
    return wrapper
```

**Testing**:
- Verify 404/400/409 status codes
- Confirm structured response format
- Test with mock domain exceptions

---

### Phase 2: Dependency Service Migration (2-3 hours)

#### 2.1 Update DependencyService

**File**: `backend/app/services/dependency_service.py`

**Changes**:

1. **Import domain exceptions**:
```python
from backend.app.exceptions import (
    DataIntegrityError,
    ForeignKeyError,
    CircularDependencyError,
    MissingDependencyError,
)
```

2. **Replace generic exceptions with domain exceptions**:

**Before**:
```python
try:
    project = ShapeShiftProject.load(project_name)
except Exception as e:
    raise DependencyServiceError(f"Failed to load project: {e}")
```

**After**:
```python
try:
    project = ShapeShiftProject.load(project_name)
except Exception as e:
    raise DataIntegrityError(
        message=f"Failed to load project '{project_name}': {e}",
        tips=[
            "Check YAML syntax and structure",
            "Validate project with validation endpoint",
            "Review recent changes to project file",
        ],
        context={"project": project_name},
    ) from e
```

3. **Add FK validation with specific errors**:

```python
for entity_name, entity_config in project.entities.items():
    foreign_keys = entity_config.get("foreign_keys", [])
    
    for fk in foreign_keys:
        # Validate structure
        if not isinstance(fk, dict):
            raise ForeignKeyError(
                message=f"Foreign key in '{entity_name}' must be a dict, not {type(fk).__name__}",
                entity=entity_name,
                foreign_key=fk,
            )
        
        # Validate local_keys
        local_keys = fk.get("local_keys")
        if not isinstance(local_keys, list):
            raise ForeignKeyError(
                message=f"Foreign key 'local_keys' in '{entity_name}' must be a list of strings, not {type(local_keys).__name__}",
                entity=entity_name,
                foreign_key=fk,
                tips=[
                    "Change format from 'local_keys: {key: value}' to 'local_keys: [key]'",
                    "Ensure YAML uses sequence syntax with '- item'",
                    "Check for copy-paste errors from other configs",
                ]
            )
        
        # Validate each key is a string
        for i, key in enumerate(local_keys):
            if not isinstance(key, str):
                raise ForeignKeyError(
                    message=f"Key at index {i} in 'local_keys' of '{entity_name}' must be a string, not {type(key).__name__}",
                    entity=entity_name,
                    foreign_key=fk,
                    tips=[
                        f"Change key from {key} to a string value",
                        "Remove nested structures or dicts from key list",
                    ]
                )
        
        # Validate remote_keys (same pattern)
        # ...
        
        # Validate referenced entity exists
        ref_entity = fk.get("entity")
        if ref_entity and ref_entity not in project.entities:
            raise MissingDependencyError(
                message=f"Entity '{entity_name}' references non-existent entity '{ref_entity}'",
                entity=entity_name,
                missing_entity=ref_entity,
            )
```

4. **Detect circular dependencies**:

```python
# After building graph
from backend.app.utils.graph import detect_cycles

cycles = detect_cycles(dependency_graph)
if cycles:
    # Take first cycle for simplicity
    cycle = cycles[0]
    raise CircularDependencyError(
        message=f"Circular dependency detected involving {len(cycle)} entities",
        cycle=cycle,
    )
```

**Testing**:
- Unit tests for each FK validation case
- Test with real corrupted project data
- Verify structured error responses
- Confirm tips are actionable

#### 2.2 Remove DependencyServiceError

**File**: `backend/app/services/dependency_service.py`

- Remove `DependencyServiceError` class definition
- Update all imports that reference it
- Verify no other services use it

---

### Phase 3: Frontend Integration (2-3 hours)

#### 3.1 Update Error Utilities

**File**: `frontend/src/utils/errors.ts`

**Changes**:

```typescript
export interface ErrorResponse {
  error_type: string
  message: string
  tips: string[]
  recoverable: boolean
  context?: Record<string, any>
}

/**
 * Extract structured error from API response.
 * Backend sends errors in response.data.detail with format:
 * { error_type, message, tips, recoverable, context }
 */
export function parseApiError(error: any): ErrorResponse {
  // Check for structured error response
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail
    
    // New structured format
    if (typeof detail === 'object' && detail.error_type) {
      return {
        error_type: detail.error_type,
        message: detail.message,
        tips: detail.tips || [],
        recoverable: detail.recoverable ?? true,
        context: detail.context || {},
      }
    }
    
    // Legacy string format (backward compatibility)
    if (typeof detail === 'string') {
      return {
        error_type: 'Error',
        message: detail,
        tips: [],
        recoverable: true,
        context: {},
      }
    }
  }
  
  // Network or other error
  return {
    error_type: error.name || 'NetworkError',
    message: error.message || 'An unexpected error occurred',
    tips: [
      'Check network connection',
      'Refresh page and try again',
      'Check browser console for details',
    ],
    recoverable: true,
    context: {},
  }
}

/**
 * Format error for display (legacy compatibility).
 */
export function formatErrorMessage(error: any): string {
  const parsed = parseApiError(error)
  return parsed.message
}
```

#### 3.2 Update ErrorAlert Component

**File**: `frontend/src/components/common/ErrorAlert.vue`

**Changes**:

```vue
<template>
  <v-alert
    :type="alertType"
    variant="tonal"
    closable
    :title="errorTitle"
  >
    <!-- Main error message -->
    <div class="text-body-2 mb-2">
      {{ error.message }}
    </div>
    
    <!-- Troubleshooting tips -->
    <div v-if="error.tips && error.tips.length > 0" class="mt-3">
      <div class="text-caption font-weight-bold mb-1">
        💡 Troubleshooting:
      </div>
      <ul class="text-caption pl-4 mb-0">
        <li v-for="(tip, index) in error.tips" :key="index" class="mb-1">
          {{ tip }}
        </li>
      </ul>
    </div>
    
    <!-- Technical context (collapsible) -->
    <v-expansion-panels v-if="showContext && error.context && Object.keys(error.context).length > 0" class="mt-3">
      <v-expansion-panel>
        <v-expansion-panel-title class="text-caption">
          🔍 Technical Details
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <pre class="text-caption">{{ JSON.stringify(error.context, null, 2) }}</pre>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
    
    <!-- Recovery indicator -->
    <div v-if="!error.recoverable" class="mt-2 text-caption text-warning">
      ⚠️ This error may require developer assistance to resolve.
    </div>
  </v-alert>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ErrorResponse } from '@/utils/errors'

const props = withDefaults(
  defineProps<{
    error: ErrorResponse
    showContext?: boolean
  }>(),
  {
    showContext: false,
  }
)

const errorTitle = computed(() => {
  return props.error.error_type || 'Error'
})

const alertType = computed(() => {
  return props.error.recoverable ? 'error' : 'warning'
})
</script>
```

#### 3.3 Update Stores

**Files**: 
- `frontend/src/stores/validation.ts`
- `frontend/src/stores/project.ts`
- `frontend/src/stores/entity.ts`

**Pattern**:

```typescript
import { parseApiError, type ErrorResponse } from '@/utils/errors'

export const useValidationStore = defineStore('validation', () => {
  const error = ref<ErrorResponse | null>(null)
  
  async function loadDependencies(projectName: string) {
    error.value = null
    loading.value = true
    
    try {
      const response = await api.get(`/projects/${projectName}/dependencies`)
      dependencies.value = response.data
    } catch (e) {
      error.value = parseApiError(e)
      console.error('Failed to load dependencies:', error.value)
    } finally {
      loading.value = false
    }
  }
  
  return {
    error,
    loadDependencies,
    // ...
  }
})
```

**Testing**:
- Verify tips display correctly
- Test context expansion
- Check recoverable vs non-recoverable styling
- Validate backward compatibility with string errors

---

### Phase 4: Service Expansion (3-4 hours)

Apply the pattern to other services:

#### 4.1 ProjectService

**Exceptions to use**:
- `ResourceNotFoundError` - Project doesn't exist
- `ResourceConflictError` - Project name collision
- `ConfigurationError` - Invalid project structure
- `DataIntegrityError` - Corrupted YAML

**Key methods**:
- `load_project()` → ResourceNotFoundError
- `create_project()` → ResourceConflictError
- `copy_project()` → ResourceConflictError
- `save_project()` → DataIntegrityError

#### 4.2 ValidationService

**Exceptions to use**:
- `ConstraintViolationError` - Failed constraint checks
- `SchemaValidationError` - Invalid entity schemas
- `ConfigurationError` - Project structure issues

**Key methods**:
- `validate_entity()` → SchemaValidationError
- `validate_constraints()` → ConstraintViolationError
- `validate_project()` → ConfigurationError

#### 4.3 QueryService

**Exceptions to use**:
- `DataIntegrityError` - SQL parsing/execution errors
- `ResourceNotFoundError` - Data source doesn't exist
- Keep existing `QuerySecurityError` (already specific)

#### 4.4 SchemaService

**Exceptions to use**:
- `ResourceNotFoundError` - Data source not found
- `DataIntegrityError` - Can't introspect schema

---

### Phase 5: Testing & Validation (2-3 hours)

#### 5.1 Unit Tests

Create `backend/tests/test_exceptions.py`:

```python
"""Tests for domain exception hierarchy."""

import pytest

from backend.app.exceptions import (
    ForeignKeyError,
    CircularDependencyError,
    ResourceNotFoundError,
)


def test_foreign_key_error_structure():
    """ForeignKeyError creates structured error dict."""
    error = ForeignKeyError(
        message="Invalid FK",
        entity="site",
        foreign_key={"local_keys": {}},
    )
    
    error_dict = error.to_dict()
    
    assert error_dict["error_type"] == "ForeignKeyError"
    assert error_dict["message"] == "Invalid FK"
    assert isinstance(error_dict["tips"], list)
    assert error_dict["recoverable"] is True
    assert error_dict["context"]["entity"] == "site"


def test_circular_dependency_error_cycle_formatting():
    """CircularDependencyError formats cycle in message."""
    cycle = ["A", "B", "C"]
    error = CircularDependencyError(
        message="Cycle detected",
        cycle=cycle,
    )
    
    assert "A → B → C → A" in error.message
    assert error.to_dict()["context"]["cycle"] == cycle


def test_resource_not_found_error_defaults():
    """ResourceNotFoundError has sensible defaults."""
    error = ResourceNotFoundError(
        message="Project not found",
        resource_type="project",
        resource_id="test",
    )
    
    error_dict = error.to_dict()
    assert error_dict["recoverable"] is True
    assert len(error_dict["tips"]) > 0
```

#### 5.2 Integration Tests

Update `backend/tests/api/test_dependencies.py`:

```python
def test_dependency_endpoint_foreign_key_error():
    """Dependencies endpoint returns structured FK error."""
    # Create project with invalid FK
    project_data = {
        "entities": {
            "site": {
                "foreign_keys": [
                    {
                        "entity": "location",
                        "local_keys": {"name": "location_name"}  # Invalid: dict instead of list
                    }
                ]
            }
        }
    }
    
    response = client.get("/api/v1/projects/invalid/dependencies")
    
    assert response.status_code == 400
    detail = response.json()["detail"]
    
    assert detail["error_type"] == "ForeignKeyError"
    assert "list" in detail["message"].lower()
    assert len(detail["tips"]) > 0
    assert detail["context"]["entity"] == "site"
    assert detail["recoverable"] is True
```

#### 5.3 Manual Testing

**Test cases**:

1. **FK with dict instead of list**:
   - Load project with `local_keys: {name: value}`
   - Verify 400 response with structured error
   - Check tips mention list format
   - Verify frontend displays tips

2. **Circular dependency**:
   - Create A→B→C→A cycle
   - Verify error shows cycle path
   - Check tips suggest breaking cycle

3. **Missing entity reference**:
   - FK references non-existent entity
   - Verify error identifies both entities
   - Check tips suggest creating entity

4. **Network error** (simulate):
   - Disconnect network
   - Verify fallback error format
   - Check generic tips display

---

### Phase 6: Documentation & Rollout (1-2 hours)

#### 6.1 Update Developer Documentation

**File**: `docs/DEVELOPMENT_GUIDE.md`

Add section:

```markdown
## Error Handling

Shape Shifter uses domain exceptions for fault-tolerant operation:

### Raising Exceptions

Always use domain exceptions from `backend.app.exceptions`:

```python
from backend.app.exceptions import ForeignKeyError

def validate_fk(entity, fk):
    if not isinstance(fk.get("local_keys"), list):
        raise ForeignKeyError(
            message=f"Invalid FK in '{entity}'",
            entity=entity,
            foreign_key=fk,
            tips=[
                "Change to list format: local_keys: [key1, key2]",
                "Check YAML syntax",
            ]
        )
```

### Exception Guidelines

- **Be specific**: Use most specific exception type
- **Provide context**: Include entity names, values
- **Write actionable tips**: Tell users HOW to fix
- **Test error paths**: Verify structured responses

See [ERROR_HANDLING_ARCHITECTURE.md](ERROR_HANDLING_ARCHITECTURE.md) for details.
```

#### 6.2 Create Migration Guide

**File**: `docs/ERROR_HANDLING_MIGRATION.md`

Document:
- What changed and why
- Breaking changes (response format)
- Backward compatibility notes
- Timeline for legacy format deprecation

#### 6.3 Update CHANGELOG

Add entry:

```markdown
## [Unreleased]

### Changed

- **Error Handling**: Migrated to domain exception hierarchy for structured, actionable error messages
  - All API errors now return structured format: `{error_type, message, tips, recoverable, context}`
  - Frontend displays troubleshooting tips for common errors
  - Removed brittle string-parsing error enhancement
  - See [ERROR_HANDLING_ARCHITECTURE.md](docs/ERROR_HANDLING_ARCHITECTURE.md) for details

### Improved

- Foreign key validation provides specific guidance for format errors
- Circular dependency detection includes complete cycle path
- Error messages include actionable troubleshooting steps
```

---

## Implementation Checklist

### Backend Foundation
- [ ] Update `error_handlers.py` with domain exception mapping
- [ ] Remove all pattern matching logic
- [ ] Add structured response formatting
- [ ] Test HTTP status code mapping

### Dependency Service
- [ ] Import domain exceptions
- [ ] Add FK structure validation with `ForeignKeyError`
- [ ] Add FK value validation (list of strings)
- [ ] Add missing entity validation with `MissingDependencyError`
- [ ] Add circular dependency detection with `CircularDependencyError`
- [ ] Remove `DependencyServiceError` class
- [ ] Update all method signatures
- [ ] Add unit tests for each exception case

### Frontend Integration
- [ ] Create `ErrorResponse` interface in `errors.ts`
- [ ] Implement `parseApiError()` utility
- [ ] Update `ErrorAlert.vue` with tips display
- [ ] Add context expansion panel
- [ ] Update validation store with `ErrorResponse`
- [ ] Update project store
- [ ] Update entity store
- [ ] Test backward compatibility

### Service Expansion
- [ ] ProjectService exception migration
- [ ] ValidationService exception migration
- [ ] QueryService exception migration
- [ ] SchemaService exception migration

### Testing
- [ ] Unit tests for exception classes
- [ ] Unit tests for service error cases
- [ ] Integration tests for API endpoints
- [ ] E2E tests for frontend error display
- [ ] Manual testing with real error scenarios

### Documentation
- [ ] Update `DEVELOPMENT_GUIDE.md`
- [ ] Create `ERROR_HANDLING_MIGRATION.md`
- [ ] Update `CHANGELOG.md`
- [ ] Add inline code documentation

---

## Success Metrics

### Quantitative
- ✅ All tests passing
- ✅ Zero pattern matching in error handlers
- ✅ 100% of domain errors have tips
- ✅ No `raise Exception()` in service layer

### Qualitative
- ✅ Users can understand and fix errors without developer help
- ✅ Error messages are clear and actionable
- ✅ Troubleshooting tips match common user questions
- ✅ Context provides relevant debugging info

---

## Rollout Strategy

### Week 1: Foundation & Dependencies
- Complete Phase 1-2 (backend foundation + dependency service)
- Deploy to development environment
- Test with known error scenarios
- Gather feedback from team

### Week 2: Frontend & Expansion
- Complete Phase 3-4 (frontend integration + service expansion)
- Deploy to staging environment
- User acceptance testing
- Iterate on tips quality

### Week 3: Polish & Production
- Complete Phase 5-6 (testing + documentation)
- Final review and refinement
- Deploy to production
- Monitor error logs for issues

---

## Risk Mitigation

### Backward Compatibility
- Frontend handles both structured and string errors
- `parseApiError()` gracefully degrades
- Legacy error format deprecated over 2 releases

### Testing Coverage
- Each exception type has unit test
- Each service method has error path test
- Integration tests verify end-to-end flow
- Manual testing with production-like data

### Incremental Rollout
- Start with one domain (dependencies)
- Validate approach before expanding
- Easy to rollback individual changes
- No breaking changes to external APIs

---

## Future Enhancements

### Phase 7: Analytics
- Track most common error types
- Measure error resolution rate
- Identify areas needing better tips

### Phase 8: Self-Service
- Link tips to documentation
- Add "Fix automatically" buttons for common issues
- Integrate with auto-fix service

### Phase 9: Localization
- Translate error messages
- Localize tips content
- Support multiple languages

---

## Questions & Decisions

### Open Questions
1. Should we include stack traces in context for non-recoverable errors?
2. Do we need error severity levels (warning, error, critical)?
3. Should tips link to documentation URLs?

### Decisions Made
- ✅ Use `to_dict()` method for structured responses
- ✅ HTTP layer does NOT inspect exception strings
- ✅ Frontend stores use `ErrorResponse` type
- ✅ Context is optional and excludes sensitive data
- ✅ Tips are short, actionable bullet points

---

## Contact & Support

For questions about this implementation:
- Review `docs/ERROR_HANDLING_ARCHITECTURE.md` for design rationale
- Check `backend/app/exceptions.py` for exception types
- See `backend/tests/test_exceptions.py` for usage examples
- Consult team lead for architectural guidance
