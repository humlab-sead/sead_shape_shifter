````markdown
# Error Handling Architecture

## Overview

Shape Shifter uses a domain-driven error handling model based on structured exceptions.

The architecture separates responsibilities between:
- the service layer
- the API layer
- the frontend

Errors are treated as part of the domain model rather than generic runtime failures.

---

# Core Principles

## Domain Exceptions

Errors are represented as typed exceptions with semantic meaning.

Examples:
- `ForeignKeyError`
- `CircularDependencyError`
- `SchemaValidationError`
- `ResourceNotFoundError`

This avoids brittle string parsing and keeps error handling predictable.

---

## Separation of Concerns

### Service Layer
Responsible for:
- validating business rules
- detecting invalid states
- raising domain exceptions

### API Layer
Responsible for:
- converting domain exceptions into HTTP responses
- assigning status codes

### Frontend
Responsible for:
- displaying structured error information
- presenting troubleshooting guidance

---

## Structured Error Responses

All domain exceptions produce a consistent response format.

```json
{
  "error_type": "ForeignKeyError",
  "message": "Invalid foreign key definition",
  "tips": [
    "Use list syntax for local_keys"
  ],
  "recoverable": true,
  "context": {
    "entity": "site"
  }
}
````

### Fields

| Field         | Description                                |
| ------------- | ------------------------------------------ |
| `error_type`  | Exception class name                       |
| `message`     | Human-readable description                 |
| `tips`        | Suggested corrective actions               |
| `recoverable` | Whether the issue can be fixed by the user |
| `context`     | Optional debugging metadata                |

---

# Exception Hierarchy

```text
DomainException
├── DataIntegrityError
│   ├── ForeignKeyError
│   └── SchemaValidationError
├── DependencyError
│   ├── CircularDependencyError
│   └── MissingDependencyError
├── ValidationError
│   ├── ConstraintViolationError
│   └── ConfigurationError
└── ResourceError
    ├── ResourceNotFoundError
    └── ResourceConflictError
```

---

# Error Flow

## 1. Service Layer

The service layer detects invalid conditions and raises domain exceptions.

Example:

* invalid foreign key definitions
* circular dependencies
* missing resources
* invalid configuration

---

## 2. API Layer

The API layer maps exceptions to HTTP status codes.

Typical mappings:

| Exception Type          | HTTP Status |
| ----------------------- | ----------- |
| `ResourceNotFoundError` | 404         |
| `ValidationError`       | 400         |
| `DataIntegrityError`    | 400         |
| `ResourceConflictError` | 409         |
| unexpected exceptions   | 500         |

Unexpected errors are logged and converted into generic internal server errors.

---

## 3. Frontend

The frontend consumes structured error responses directly.

The UI can:

* display readable messages
* show troubleshooting tips
* present debugging context when needed

No frontend string parsing is required.

---

# Design Guidelines

## Prefer Typed Exceptions

Use domain-specific exceptions instead of generic exceptions.

Preferred:

```python
raise ForeignKeyError(message="Invalid foreign key")
```

Avoid:

```python
raise Exception("Invalid foreign key")
```

---

## Keep HTTP Logic Out of Services

Service code should not raise HTTP exceptions directly.

Preferred:

```python
raise ResourceNotFoundError(...)
```

Avoid:

```python
raise HTTPException(status_code=404)
```

This keeps the service layer reusable outside HTTP APIs.

---

## Avoid String Parsing

Do not infer behavior from exception messages.

Avoid:

```python
if "foreign key" in str(error):
```

Use typed exceptions instead.

---

# Testing Strategy

## Service Tests

Verify:

* correct exception types
* correct metadata
* validation behavior

---

## API Tests

Verify:

* HTTP status mappings
* response structure
* serialized error payloads

---

## Frontend Tests

Verify:

* error rendering
* troubleshooting display
* handling of structured responses

---

# Summary

The architecture is based on structured domain exceptions shared across the backend and frontend.

Key characteristics:

* typed exceptions
* structured error payloads
* consistent API responses
* clear layer separation
* maintainable error handling
* predictable frontend behavior

The result is a simpler and more maintainable error handling model with better user-facing diagnostics.
