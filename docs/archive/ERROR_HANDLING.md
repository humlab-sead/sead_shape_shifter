# Error Handling Architecture

This document describes Shape Shifter's error code system and centralized tip management.

## Overview

Shape Shifter uses a **domain exception hierarchy** with **error codes** and **centralized tips** for clean, maintainable error handling.

**Key Benefits:**
- **Clean code**: No verbose tip arrays cluttering business logic
- **Easy maintenance**: Update error messages in one place  
- **Consistency**: Same tips across all occurrences
- **Discoverability**: Error codes make debugging easier
- **Flexibility**: Can override tips for specific cases

## Architecture

```
Service Layer          API Layer           Frontend
    ↓                      ↓                   ↓
Raise with         @handle_endpoint      Structured
error code         errors decorator      JSON response
    ↓                      ↓                   ↓
Tips auto-loaded   HTTP status code      Display tips
from registry      mapping               to user
```

## Error Codes

Each domain exception has a unique error code defined as a class variable:

```python
class QueryExecutionError(DomainException):
    error_code = "QUERY_EXEC_FAILED"
```

### Error Code Registry

Error codes are mapped to tips in `backend/app/error_tips.py`:

```python
ERROR_TIPS = {
    "QUERY_EXEC_FAILED": [
        "Check data source connection is active",
        "Verify SQL syntax is valid for the database type",
        "Check if query timeout needs to be increased",
        "Ensure proper database permissions are granted",
    ],
    # ... more error codes
}
```

### Available Error Codes

| Error Code | Exception | HTTP Status | Description |
|------------|-----------|-------------|-------------|
| `RESOURCE_NOT_FOUND` | ResourceNotFoundError | 404 | Resource doesn't exist |
| `RESOURCE_CONFLICT` | ResourceConflictError | 409 | Duplicate resource |
| `CONFIG_INVALID` | ConfigurationError | 400 | Invalid configuration |
| `CONFIG_YAML_ERROR` | YamlError | 400 | YAML syntax error |
| `VALIDATION_FAILED` | ValidationError | 400 | Business rule violation |
| `FOREIGN_KEY_INVALID` | ForeignKeyError | 400 | Invalid FK definition |
| `CIRCULAR_DEPENDENCY` | CircularDependencyError | 400 | Cyclic FK references |
| `DATA_INTEGRITY_VIOLATION` | DataIntegrityError | 400 | Data integrity issue |
| `QUERY_EXEC_FAILED` | QueryExecutionError | 500 | Query execution failed |
| `QUERY_EXEC_TIMEOUT` | - | 500 | Query timeout |
| `QUERY_EXEC_CONNECTION` | - | 500 | Connection failure |
| `QUERY_SECURITY_VIOLATION` | QuerySecurityError | 400 | Prohibited SQL operation |
| `SCHEMA_INTROSPECT_FAILED` | SchemaIntrospectionError | 500 | Schema introspection failed |
| `SCHEMA_NOT_SUPPORTED` | - | 400 | Driver doesn't support feature |
| `DEPENDENCY_ERROR` | DependencyError | 400 | Entity dependency issue |

## Usage Patterns

### Basic Usage (Auto-loading Tips)

```python
# Tips automatically loaded from registry based on error_code
raise QueryExecutionError(
    message=f"Failed to execute query: {error}",
    data_source=data_source_name,
    query=query,
)
```

The exception will automatically:
1. Use the class-level `error_code` ("QUERY_EXEC_FAILED")
2. Load tips from `ERROR_TIPS` registry
3. Include tips in the response

### Override Error Code

```python
# Use specific error code variant
raise QueryExecutionError(
    message="Connection timeout",
    data_source=data_source_name,
    query=query,
    error_code="QUERY_EXEC_TIMEOUT",  # Override class default
)
```

### Override Tips (Rare)

```python
# Provide custom tips for specific case
raise QueryExecutionError(
    message="Unsupported SQL function",
    data_source=data_source_name,
    query=query,
    tips=[
        "Check database driver documentation for supported functions",
        "Consider rewriting query with standard SQL",
    ],
)
```

## Adding New Error Codes

### 1. Define Error Code in Exception Class

```python
# backend/app/exceptions.py
class MyNewError(DomainException):
    """Description of when this error occurs."""
    
    error_code = "MY_ERROR_CODE"  # ← Add this
    
    def __init__(self, message: str, **kwargs):
        # Custom context if needed
        super().__init__(message, **kwargs)
```

### 2. Register Tips

```python
# backend/app/error_tips.py
ERROR_TIPS = {
    # ... existing codes ...
    "MY_ERROR_CODE": [
        "First actionable tip",
        "Second actionable tip",
        "Third actionable tip",
    ],
}
```

### 3. Use in Services

```python
# backend/app/services/my_service.py
from backend.app.exceptions import MyNewError

def my_method(self):
    if something_wrong:
        raise MyNewError(
            message="Clear description of what went wrong",
            # Tips auto-loaded from registry
        )
```

## Error Response Structure

Exceptions are converted to JSON by `@handle_endpoint_errors`:

```json
{
  "error_type": "QueryExecutionError",
  "error_code": "QUERY_EXEC_FAILED",
  "message": "Failed to execute query: connection timeout",
  "tips": [
    "Check data source connection is active",
    "Verify SQL syntax is valid for the database type",
    "Check if query timeout needs to be increased",
    "Ensure proper database permissions are granted"
  ],
  "recoverable": true,
  "context": {
    "data_source": "my_database",
    "query": "SELECT * FROM ..."
  }
}
```

**Note:** The `error_code` field in the response contains the resolved error code (either the class default or a provided override). The exception instance stores this in the `code` attribute to avoid conflicts with the `ClassVar` class-level `error_code`.

## Testing

### Testing Auto-loaded Tips

```python
def test_query_execution_error_has_tips(self):
    """Tips should auto-load from registry."""
    with pytest.raises(QueryExecutionError) as exc_info:
        service.execute_query("bad_source", "SELECT 1")
    
    error = exc_info.value
    assert error.code == "QUERY_EXEC_FAILED"  # Instance attribute
    assert len(error.tips) > 0
    assert "connection" in error.tips[0].lower()
```

### Testing Custom Error Codes

```python
def test_timeout_uses_specific_code(self):
    """Timeout should use specific error code."""
    with pytest.raises(QueryExecutionError) as exc_info:
        # ... trigger timeout ...
        pass
    
    error = exc_info.value
    assert error.code == "QUERY_EXEC_TIMEOUT"  # Instance attribute
    assert any("timeout" in tip.lower() for tip in error.tips)
```

## Migration Guide

### Before (Inline Tips)

```python
raise QueryExecutionError(
    message=f"Query execution failed: {error}",
    data_source=data_source_name,
    query=query,
    tips=[                                    # ← Clutters code
        "Check data source connection",
        "Verify SQL syntax",
        "Check timeout settings",
        "Ensure proper permissions",
    ],
)
```

### After (Auto-loaded Tips)

```python
raise QueryExecutionError(
    message=f"Query execution failed: {error}",
    data_source=data_source_name,
    query=query,
    # Tips auto-loaded from registry ✨
)
```

**Cleanup Steps:**
1. Ensure error code is defined in exception class
2. Ensure tips are registered in `error_tips.py`
3. Remove `tips=[...]` parameter from raise statements
4. Verify tests still pass

## Best Practices

### Error Messages
- **Be specific**: "Query timeout (30s exceeded)" > "Query failed"
- **Include context**: Data source name, entity name, etc.
- **Avoid jargon**: Write for end users, not developers

### Tips
- **Be actionable**: "Check X" > "X might be wrong"
- **Order by likelihood**: Most common fixes first
- **Be specific**: "Set timeout > 30s in settings" > "Increase timeout"
- **Avoid duplicates**: Similar tips should share error codes

### Error Codes
- **Use categories**: `QUERY_EXEC_*`, `SCHEMA_*`, `RESOURCE_*`
- **Be specific when needed**: `QUERY_EXEC_TIMEOUT` > `QUERY_EXEC_FAILED`
- **Reuse generic codes**: `RESOURCE_NOT_FOUND` works for projects, entities, files
- **Document in registry**: Add comments for complex error scenarios

## Frontend Integration

Frontend receives structured error responses and can:

```typescript
// Display error message
const message = error.detail.message;

// Show actionable tips
error.detail.tips.forEach(tip => {
  addTipToUI(tip);
});

// Check if user can recover
if (error.detail.recoverable) {
  showRetryButton();
} else {
  showContactSupportButton();
}

// Use error code for specific handling
if (error.detail.error_code === 'QUERY_EXEC_TIMEOUT') {
  suggestIncreaseTimeout();
}

// Access from Python exception (if needed in backend)
// Note: Instance attribute is 'code', class attribute is 'error_code'
try:
    raise QueryExecutionError("Failed")
except QueryExecutionError as e:
    print(e.code)  # "QUERY_EXEC_FAILED" (instance attribute)
    print(e.__class__.error_code)  # "QUERY_EXEC_FAILED" (class attribute)
```

## Related Documentation

- [exceptions.py](backend/app/exceptions.py) - Domain exception hierarchy
- [error_tips.py](backend/app/error_tips.py) - Centralized tip registry
- [error_handlers.py](backend/app/utils/error_handlers.py) - HTTP error mapping
