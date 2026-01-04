"""Centralized error handling utilities for API endpoints."""

import inspect
import sys
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from loguru import logger

from backend.app.services.dependency_service import DependencyServiceError
from backend.app.services.project_service import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InvalidProjectError,
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectServiceError,
)
from backend.app.services.query_service import QueryExecutionError, QuerySecurityError
from backend.app.services.schema_service import SchemaServiceError
from backend.app.services.yaml_service import YamlServiceError
from backend.app.utils.exceptions import BadRequestError, BaseAPIException, NotFoundError

T = TypeVar("T")

# Configure file logging for endpoint errors
_ERROR_LOG_FILE = Path("logs/endpoint_errors.log")
_ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Add file handler for error logging (if not already added)
_error_logger_id = None
try:
    _error_logger_id = logger.add(
        _ERROR_LOG_FILE,
        level="WARNING",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )
except Exception as e:  # pylint: disable=broad-except
    # If logger.add fails (e.g., already added), log to stderr but continue
    print(f"Warning: Could not add error log file handler: {e}", file=sys.stderr)


def handle_endpoint_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle common endpoint errors and convert them to HTTPException.

    Maps service-level exceptions to appropriate HTTP status codes:
    - 404: NotFoundError, ProjectNotFoundError, EntityNotFoundError
    - 400: BadRequestError, InvalidProjectError, QuerySecurityError
    - 409: ConflictError, EntityAlreadyExistsError, ProjectConflictError
    - 500: All other exceptions

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

        # Handle 404 Not Found errors
        except (NotFoundError, ProjectNotFoundError, EntityNotFoundError) as e:
            logger.debug(f"Resource not found in {func.__name__}: {e}")
            raise HTTPException(status_code=404, detail=str(e)) from e

        # Handle 400 Bad Request errors
        except (BadRequestError, InvalidProjectError, QuerySecurityError) as e:
            logger.warning(f"Bad request in {func.__name__}: {e}")
            raise HTTPException(status_code=400, detail=str(e)) from e

        # Handle 409 Conflict errors
        except (EntityAlreadyExistsError, ProjectConflictError) as e:
            logger.warning(f"Conflict in {func.__name__}: {e}")
            raise HTTPException(status_code=409, detail=str(e)) from e

        # Handle custom API exceptions with status codes
        except BaseAPIException as e:
            logger.error(f"API error in {func.__name__}: {e}")
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e

        # Handle service-level errors (generic 500)
        except (
            ProjectServiceError,
            YamlServiceError,
            QueryExecutionError,
            SchemaServiceError,
            DependencyServiceError,
        ) as e:
            logger.error(f"Service error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

        # Handle unexpected errors
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    return wrapper  # type: ignore
