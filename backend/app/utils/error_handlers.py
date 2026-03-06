"""Centralized error handling utilities for API endpoints."""

import inspect
from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from loguru import logger

from backend.app.exceptions import (
    DataIntegrityError,
    DependencyError,
    DomainException,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationError,
)
from backend.app.services.project import ProjectServiceError
from backend.app.services.yaml_service import YamlServiceError
from backend.app.utils.exceptions import BaseAPIException

T = TypeVar("T")

# Note: Error logging is configured centrally in backend.app.core.logging_config
# All errors are automatically logged to logs/app.log and logs/error.log


def handle_endpoint_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle common endpoint errors and convert them to HTTPException.

    Maps domain exceptions to appropriate HTTP status codes with structured responses:
    - 404: ResourceNotFoundError (and legacy exceptions)
    - 400: DataIntegrityError, ValidationError (and legacy exceptions)
    - 409: ResourceConflictError (and legacy exceptions)
    - 500: DependencyError, unexpected exceptions

    Domain exceptions return structured responses with:
    - error_type: Exception class name
    - message: Human-readable error description
    - tips: List of actionable troubleshooting steps
    - recoverable: Whether user can fix without developer help
    - context: Additional debugging information

    Args:
        func: Async endpoint function to wrap

    Returns:
        Wrapped function with error handling
    """
    # Validate function is async before creating wrapper
    if not inspect.iscoroutinefunction(func):
        raise TypeError(f"{func.__name__} must be an async function to use @handle_endpoint_errors")

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)

        # Let HTTPException pass through unchanged
        except HTTPException:
            raise

        # === Domain Exception Handling (Structured Responses) ===

        # Handle 404 Not Found errors
        except ResourceNotFoundError as e:
            logger.debug(f"Resource not found in {func.__name__}: {e}")
            raise HTTPException(status_code=404, detail=e.to_dict()) from e

        # Handle 400 Bad Request errors (data integrity and validation)
        except (DataIntegrityError, ValidationError) as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            raise HTTPException(status_code=400, detail=e.to_dict()) from e

        # Handle 409 Conflict errors
        except ResourceConflictError as e:
            logger.warning(f"Resource conflict in {func.__name__}: {e}")
            raise HTTPException(status_code=409, detail=e.to_dict()) from e

        # Handle 500 Dependency errors
        except DependencyError as e:
            logger.error(f"Dependency error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail=e.to_dict()) from e

        # Handle any other domain exceptions (500 with structured response)
        except DomainException as e:
            logger.exception(f"Domain error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail=e.to_dict()) from e

        # === Legacy Exception Handling (String Responses) ===
        # Note: Most domain exceptions now inherit from DomainException (handled above)
        # These handlers remain for backward compatibility and non-domain exceptions

        # Handle custom API exceptions with status codes (legacy)
        except BaseAPIException as e:
            logger.exception(f"API error in {func.__name__}: {e}")
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e

        # Handle service-level errors (legacy - generic 500)
        except (ProjectServiceError, YamlServiceError) as e:
            logger.exception(f"Service error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

        # Handle unexpected errors (structured response)
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error_type": "InternalServerError",
                    "message": str(e) or "An unexpected error occurred",
                    "tips": [
                        "Check server logs for details",
                        "Verify your request parameters are valid",
                    ],
                    "recoverable": False,
                    "context": {},
                },
            ) from e

    return wrapper  # type: ignore
