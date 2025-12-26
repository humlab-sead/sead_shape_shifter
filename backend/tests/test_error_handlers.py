"""Tests for centralized error handling."""

import pytest
from fastapi import HTTPException

from backend.app.services.config_service import (
    ConfigConflictError,
    ConfigurationNotFoundError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
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
    async def test_configuration_not_found_returns_404(self):
        """Test ConfigurationNotFoundError is converted to 404."""

        @handle_endpoint_errors
        async def config_not_found_endpoint():
            raise ConfigurationNotFoundError("Configuration 'test' not found")

        with pytest.raises(HTTPException) as exc_info:
            await config_not_found_endpoint()

        assert exc_info.value.status_code == 404
        assert "Configuration 'test' not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_entity_not_found_returns_404(self):
        """Test EntityNotFoundError is converted to 404."""

        @handle_endpoint_errors
        async def entity_not_found_endpoint():
            raise EntityNotFoundError("Entity 'sample' not found")

        with pytest.raises(HTTPException) as exc_info:
            await entity_not_found_endpoint()

        assert exc_info.value.status_code == 404
        assert "Entity 'sample' not found" in exc_info.value.detail

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
        """Test EntityAlreadyExistsError is converted to 409."""

        @handle_endpoint_errors
        async def conflict_endpoint():
            raise EntityAlreadyExistsError("Entity 'sample' already exists")

        with pytest.raises(HTTPException) as exc_info:
            await conflict_endpoint()

        assert exc_info.value.status_code == 409
        assert "Entity 'sample' already exists" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_config_conflict_returns_409(self):
        """Test ConfigConflictError is converted to 409."""

        @handle_endpoint_errors
        async def config_conflict_endpoint():
            raise ConfigConflictError("Configuration was modified by another user")

        with pytest.raises(HTTPException) as exc_info:
            await config_conflict_endpoint()

        assert exc_info.value.status_code == 409
        assert "modified by another user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_generic_exception_returns_500(self):
        """Test generic Exception is converted to 500."""

        @handle_endpoint_errors
        async def error_endpoint():
            raise ValueError("Unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            await error_endpoint()

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Unexpected error"

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
                raise EntityAlreadyExistsError("Already exists")
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
