"""API endpoints for @value directive validation."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.directive_validator import DirectiveValidator
from backend.app.services.project_service import ProjectService

router = APIRouter()


class ValidateDirectiveRequest(BaseModel):
    """Request to validate a @value directive."""

    directive: str
    local_entity: str | None = None
    remote_entity: str | None = None
    is_local_keys: bool | None = None


class ValidateDirectiveResponse(BaseModel):
    """Response from directive validation."""

    is_valid: bool
    path: str
    error: str | None = None
    suggestions: list[str] = []


@router.post("/projects/{project_name}/validate-directive", response_model=ValidateDirectiveResponse)
async def validate_directive(project_name: str, request: ValidateDirectiveRequest):
    """
    Validate a @value directive against project structure.

    Args:
        project_name: Project name
        request: Validation request with directive and optional FK context

    Returns:
        Validation result with error/suggestions if invalid
    """
    try:
        project_service = ProjectService()
        project = project_service.load_project(project_name)

        validator = DirectiveValidator(project)

        # Use FK-specific validation if context provided
        if request.local_entity and request.remote_entity and request.is_local_keys is not None:
            result = validator.validate_foreign_key_directive(
                request.local_entity,
                request.remote_entity,
                request.directive,
                request.is_local_keys,
            )
        else:
            result = validator.validate_directive(request.directive)

        return ValidateDirectiveResponse(
            is_valid=result.is_valid,
            path=result.path,
            error=result.error,
            suggestions=result.suggestions,
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")  # pylint: disable=raise-missing-from
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/projects/{project_name}/valid-directives", response_model=list[str])
async def get_valid_directives(project_name: str, max_depth: int = 3):
    """
    Get all valid @value directive paths in the project.

    Args:
        project_name: Project name
        max_depth: Maximum path depth to traverse

    Returns:
        List of valid @value directive paths
    """
    try:
        project_service = ProjectService()
        project = project_service.load_project(project_name)

        validator = DirectiveValidator(project)
        return validator.get_all_valid_paths(max_depth)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")  # pylint: disable=raise-missing-from
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
