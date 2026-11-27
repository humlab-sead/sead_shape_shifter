"""Models that describe what the current user may do."""

from pydantic import BaseModel, Field


class UserPermissions(BaseModel):
    """Deployment-wide actions the current user may perform, used by the UI to show or hide features."""

    can_read_logs: bool = Field(..., description="Whether the user may view and download the application logs")
