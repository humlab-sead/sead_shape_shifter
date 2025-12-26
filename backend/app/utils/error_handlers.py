"""Centralized error handling utilities for API endpoints."""

import inspect
from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from loguru import logger

from backend.app.services.config_service import (
    ConfigConflictError,
    ConfigurationNotFoundError,
    ConfigurationServiceError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InvalidConfigurationError,
)
from backend.app.services.dependency_service import DependencyServiceError
from backend.app.services.query_service import QueryExecutionError, QuerySecurityError
from backend.app.services.schema_service import SchemaServiceError
from backend.app.services.yaml_service import YamlServiceError
from backend.app.utils.exceptions import BadRequestError, BaseAPIException, NotFoundError

T = TypeVar("T")


def handle_endpoint_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle common endpoint errors and convert them to HTTPException.

    Maps service-level exceptions to appropriate HTTP status codes:
    - 404: NotFoundError, ConfigurationNotFoundError, EntityNotFoundError
    - 400: BadRequestError, InvalidConfigurationError, QuerySecurityError
    - 409: ConflictError, EntityAlreadyExistsError, ConfigConflictError
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
        except (NotFoundError, ConfigurationNotFoundError, EntityNotFoundError) as e:
            logger.debug(f"Resource not found in {func.__name__}: {e}")
            raise HTTPException(status_code=404, detail=str(e)) from e

        # Handle 400 Bad Request errors
        except (BadRequestError, InvalidConfigurationError, QuerySecurityError) as e:
            logger.warning(f"Bad request in {func.__name__}: {e}")
            raise HTTPException(status_code=400, detail=str(e)) from e

        # Handle 409 Conflict errors
        except (EntityAlreadyExistsError, ConfigConflictError) as e:
            logger.warning(f"Conflict in {func.__name__}: {e}")
            raise HTTPException(status_code=409, detail=str(e)) from e

        # Handle custom API exceptions with status codes
        except BaseAPIException as e:
            logger.error(f"API error in {func.__name__}: {e}")
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e

        # Handle service-level errors (generic 500)
        except (
            ConfigurationServiceError,
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
