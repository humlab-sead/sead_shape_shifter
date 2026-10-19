"""Tests for project authorization on the retired Change Request file routes."""

from unittest.mock import patch

import pytest

# pylint: disable=redefined-outer-name

VALIDATE_PATH = "/api/v1/ingesters/sead_change_request/validate"
INGEST_PATH = "/api/v1/ingesters/sead_change_request/ingest"


@pytest.mark.parametrize("operation", ["validate", "ingest"])
@pytest.mark.parametrize("project_name", [None, "inaccessible_project"])
@pytest.mark.asyncio
async def test_change_request_routes_require_top_level_project_authorization(authorized_client, operation: str, project_name: str | None):
    """Reject missing or inaccessible top-level projects before the retired-input handler."""
    request_body = {
        "source": "/tmp/unused.xlsx",
        "project_name": project_name,
        "submission_context": {"project_name": "scope_alpha"},
    }
    if operation == "ingest":
        request_body.update({"submission_name": "scope_delivery_1", "data_types": "mal"})
    if project_name is None:
        request_body.pop("project_name")

    path = VALIDATE_PATH if operation == "validate" else INGEST_PATH
    with patch("backend.app.api.v1.endpoints.ingesters.get_ingester_service") as get_ingester_service:
        response = await authorized_client.post(path, json=request_body)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    assert "scope_alpha" not in response.text
    get_ingester_service.assert_not_called()
