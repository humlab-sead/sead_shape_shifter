"""Tests for centralized error handling."""

from typing import Any, cast

import pytest
from fastapi import HTTPException

from backend.app.exceptions import (
    CircularDependencyError,
    DataIntegrityError,
    ForeignKeyError,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationError,
)
from backend.app.utils.error_handlers import handle_endpoint_errors
from backend.app.utils.exceptions import BadRequestError, NotFoundError


class TestErrorHandlerDecorator:
    """Tests for the @handle_endpoint_errors decorator."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test decorator allows successful execution."""

        @handle_endpoint_errors
        async def successful_endpoint():
            return {"status": "success"}

        result = await successful_endpoint()
        assert result == {"status": "success"}

    @pytest.mark.asyncio
    async def test_not_found_error_returns_404(self):
        """Test NotFoundError is converted to 404 HTTPException."""

        @handle_endpoint_errors
        async def not_found_endpoint():
            raise NotFoundError("Resource not found")

        with pytest.raises(HTTPException) as exc_info:
            await not_found_endpoint()

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Resource not found"

    @pytest.mark.asyncio
    async def test_projecturation_not_found_returns_404(self):
        """Test ResourceNotFoundError for project is converted to 404."""

        @handle_endpoint_errors
        async def config_not_found_endpoint():
            raise ResourceNotFoundError(resource_type="project", resource_id="test", message="Configuration 'test' not found")

        with pytest.raises(HTTPException) as exc_info:
            await config_not_found_endpoint()

        assert exc_info.value.status_code == 404
        # Structured response - detail is a dict
        detail = cast(dict[str, Any], exc_info.value.detail)
        assert isinstance(detail, dict)
        assert "Configuration 'test' not found" in detail["message"]

    @pytest.mark.asyncio
    async def test_entity_not_found_returns_404(self):
        """Test ResourceNotFoundError for entity is converted to 404."""

        @handle_endpoint_errors
        async def entity_not_found_endpoint():
            raise ResourceNotFoundError(resource_type="entity", resource_id="sample", message="Entity 'sample' not found")

        with pytest.raises(HTTPException) as exc_info:
            await entity_not_found_endpoint()

        assert exc_info.value.status_code == 404
        # Structured response - detail is a dict
        detail = cast(dict[str, Any], exc_info.value.detail)
        assert isinstance(detail, dict)
        assert "Entity 'sample' not found" in detail["message"]

    @pytest.mark.asyncio
    async def test_bad_request_error_returns_400(self):
        """Test BadRequestError is converted to 400 HTTPException."""

        @handle_endpoint_errors
        async def bad_request_endpoint():
            raise BadRequestError("Invalid input")

        with pytest.raises(HTTPException) as exc_info:
            await bad_request_endpoint()

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid input"

    @pytest.mark.asyncio
    async def test_entity_already_exists_returns_409(self):
        """Test ResourceConflictError for entity is converted to 409."""

        @handle_endpoint_errors
        async def conflict_endpoint():
            raise ResourceConflictError(resource_type="entity", resource_id="sample", message="Entity 'sample' already exists")

        with pytest.raises(HTTPException) as exc_info:
            await conflict_endpoint()

        assert exc_info.value.status_code == 409
        # Structured response - detail is a dict
        detail = cast(dict[str, Any], exc_info.value.detail)
        assert isinstance(detail, dict)
        assert "Entity 'sample' already exists" in detail["message"]

    @pytest.mark.asyncio
    async def test_project_conflict_returns_409(self):
        """Test ResourceConflictError for project is converted to 409."""

        @handle_endpoint_errors
        async def config_conflict_endpoint():
            raise ResourceConflictError(resource_type="project", resource_id="test", message="Configuration was modified by another user")

        with pytest.raises(HTTPException) as exc_info:
            await config_conflict_endpoint()

        assert exc_info.value.status_code == 409
        # Structured response - detail is a dict
        detail = cast(dict[str, Any], exc_info.value.detail)
        assert isinstance(detail, dict)
        assert "modified by another user" in detail["message"]

    @pytest.mark.asyncio
    async def test_generic_exception_returns_500(self):
        """Test generic Exception is converted to 500 with structured response."""

        @handle_endpoint_errors
        async def error_endpoint():
            raise ValueError("Unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            await error_endpoint()

        assert exc_info.value.status_code == 500
        # New behavior: structured response for unexpected errors
        detail = cast(dict[str, Any], exc_info.value.detail)
        assert isinstance(detail, dict)
        assert detail["error_type"] == "InternalServerError"
        assert "Unexpected error" in detail["message"]

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""

        @handle_endpoint_errors
        async def test_endpoint():
            """Test endpoint docstring."""
            return "result"

        assert test_endpoint.__name__ == "test_endpoint"
        assert test_endpoint.__doc__ == "Test endpoint docstring."

    @pytest.mark.asyncio
    async def test_handles_multiple_exception_types(self):
        """Test decorator correctly handles different exception types in sequence."""

        call_count = 0

        @handle_endpoint_errors
        async def multi_error_endpoint(error_type: str):
            nonlocal call_count
            call_count += 1

            if error_type == "not_found":
                raise NotFoundError("Not found")
            if error_type == "bad_request":
                raise BadRequestError("Bad request")
            if error_type == "conflict":
                raise ResourceConflictError(resource_type="entity", resource_id="test", message="Already exists")
            return "success"

        # Test 404
        with pytest.raises(HTTPException) as exc_info:
            await multi_error_endpoint("not_found")
        assert exc_info.value.status_code == 404

        # Test 400
        with pytest.raises(HTTPException) as exc_info:
            await multi_error_endpoint("bad_request")
        assert exc_info.value.status_code == 400

        # Test 409
        with pytest.raises(HTTPException) as exc_info:
            await multi_error_endpoint("conflict")
        assert exc_info.value.status_code == 409

        # Test success
        result = await multi_error_endpoint("success")
        assert result == "success"
        assert call_count == 4


class TestDomainExceptionHandling:
    """Tests for error handler decorator with structured domain exceptions."""

    @pytest.mark.asyncio
    async def test_resource_not_found_returns_404_with_structured_response(self):
        """ResourceNotFoundError returns 404 with structured detail."""

        @handle_endpoint_errors
        async def endpoint():
            raise ResourceNotFoundError(
                message="Project not found",
                resource_type="project",
                resource_id="test_project",
            )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()

        assert exc_info.value.status_code == 404
        detail = cast(dict[str, Any], exc_info.value.detail)

        # Verify structured response
        assert isinstance(detail, dict)
        assert detail["error_type"] == "ResourceNotFoundError"
        assert detail["message"] == "Project not found"
        assert isinstance(detail["tips"], list)
        assert detail["recoverable"] is True
        assert detail["context"]["resource_type"] == "project"
        assert detail["context"]["resource_id"] == "test_project"

    @pytest.mark.asyncio
    async def test_foreign_key_error_returns_400_with_structured_response(self):
        """ForeignKeyError returns 400 with structured detail."""

        @handle_endpoint_errors
        async def endpoint():
            raise ForeignKeyError(
                message="Invalid FK in entity 'site'",
                entity="site",
                foreign_key={"local_keys": {}},
            )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()

        assert exc_info.value.status_code == 400
        detail = cast(dict[str, Any], exc_info.value.detail)

        # Verify structured response
        assert isinstance(detail, dict)
        assert detail["error_type"] == "ForeignKeyError"
        assert "site" in detail["message"]
        assert len(detail["tips"]) > 0
        assert detail["context"]["entity"] == "site"

    @pytest.mark.asyncio
    async def test_validation_error_returns_400(self):
        """ValidationError returns 400 with structured response."""

        @handle_endpoint_errors
        async def endpoint():
            raise ValidationError(
                message="Validation failed",
                tips=["Fix validation issue"],
            )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()

        assert exc_info.value.status_code == 400
        detail = cast(dict[str, Any], exc_info.value.detail)

        assert detail["error_type"] == "ValidationError"
        assert detail["message"] == "Validation failed"
        assert detail["tips"] == ["Fix validation issue"]

    @pytest.mark.asyncio
    async def test_resource_conflict_returns_409(self):
        """ResourceConflictError returns 409 with structured response."""

        @handle_endpoint_errors
        async def endpoint():
            raise ResourceConflictError(
                message="Project already exists",
                resource_type="project",
                resource_id="duplicate",
            )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()

        assert exc_info.value.status_code == 409
        detail = cast(dict[str, Any], exc_info.value.detail)

        assert detail["error_type"] == "ResourceConflictError"
        assert detail["context"]["resource_id"] == "duplicate"

    @pytest.mark.asyncio
    async def test_circular_dependency_error_returns_500(self):
        """CircularDependencyError returns 500 with structured response."""

        @handle_endpoint_errors
        async def endpoint():
            raise CircularDependencyError(
                message="Circular dependency detected",
                cycle=["A", "B", "C"],
            )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()

        assert exc_info.value.status_code == 500
        detail = cast(dict[str, Any], exc_info.value.detail)

        assert detail["error_type"] == "CircularDependencyError"
        assert "A → B → C → A" in detail["message"]
        assert detail["context"]["cycle"] == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_data_integrity_error_returns_400(self):
        """DataIntegrityError returns 400 with structured response."""

        @handle_endpoint_errors
        async def endpoint():
            raise DataIntegrityError(
                message="Corrupted data",
                tips=["Check data source", "Validate YAML"],
            )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()

        assert exc_info.value.status_code == 400
        detail = cast(dict[str, Any], exc_info.value.detail)

        assert detail["error_type"] == "DataIntegrityError"
        assert detail["message"] == "Corrupted data"
        assert len(detail["tips"]) == 2

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_structured_500(self):
        """Unexpected errors return 500 with structured response."""

        @handle_endpoint_errors
        async def endpoint():
            raise ValueError("Unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()

        assert exc_info.value.status_code == 500
        detail = cast(dict[str, Any], exc_info.value.detail)

        # Verify structured response for unexpected errors
        assert isinstance(detail, dict)
        assert detail["error_type"] == "InternalServerError"
        assert "Unexpected error" in detail["message"]
        assert isinstance(detail["tips"], list)
        assert detail["recoverable"] is False

    @pytest.mark.asyncio
    async def test_http_exception_passes_through(self):
        """HTTPException is not wrapped, passes through unchanged."""

        @handle_endpoint_errors
        async def endpoint():
            raise HTTPException(status_code=403, detail="Forbidden")

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()

        # HTTPException should pass through as-is
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Forbidden"
