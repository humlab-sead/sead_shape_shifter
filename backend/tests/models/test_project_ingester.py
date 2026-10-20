"""Tests for strict project-ingester request models."""

import pytest
from pydantic import ValidationError

from backend.app.models.ingester import ProjectIngesterRequest


def project_request() -> dict:
    """Build one valid project-ingester request."""
    return {
        "project_name": "pilot",
        "translate": True,
        "drop_foreign_keys": False,
        "default_entity": "site",
        "submission_context": {
            "submission_name": "pilot-run",
            "timestamp": "2026-10-19T12:00:00",
            "datatype": "mal",
            "identifier": "PILOT_RUN",
            "description": "Pilot data",
            "issue_identifier": "SHAPE-1",
            "author": "Operator",
            "run_id": "run-1",
        },
    }


def test_project_ingester_request_accepts_named_options() -> None:
    """The helper request parses workflow and submission options without a source path."""
    request = ProjectIngesterRequest.model_validate(project_request())

    assert request.project_name == "pilot"
    assert request.submission_context.timestamp.isoformat() == "2026-10-19T12:00:00"
    assert request.submission_context.datatype == "mal"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", "input.xlsx"),
        ("config", {}),
        ("database", {}),
        ("target_model", {}),
        ("output_folder", "output"),
        ("provider_schema", "schema"),
        ("scope_name", "scope"),
        ("sims_client", {}),
        ("run_validation", False),
        ("validate_first", False),
    ],
)
def test_project_ingester_request_rejects_untrusted_top_level_fields(field: str, value: object) -> None:
    """The request rejects source paths, config overrides, and collaborator injection."""
    payload = project_request()
    payload[field] = value

    with pytest.raises(ValidationError):
        ProjectIngesterRequest.model_validate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("project_name", "forged-project"),
        ("provider_schema", "forged-schema"),
        ("scope_name", "forged-scope"),
        ("database", {}),
        ("output_folder", "forged-output"),
        ("sims_client", {}),
    ],
)
def test_project_ingester_request_rejects_untrusted_nested_fields(field: str, value: object) -> None:
    """Nested submission options cannot override project identity or backend settings."""
    payload = project_request()
    payload["submission_context"][field] = value

    with pytest.raises(ValidationError):
        ProjectIngesterRequest.model_validate(payload)


@pytest.mark.parametrize("project_name", ["", " ", "   "])
def test_project_ingester_request_rejects_blank_project_name(project_name: str) -> None:
    """A blank project locator cannot reach the direct-call guard."""
    payload = project_request()
    payload["project_name"] = project_name

    with pytest.raises(ValidationError):
        ProjectIngesterRequest.model_validate(payload)


def test_project_ingester_request_requires_submission_identity_fields() -> None:
    """The request requires the fields used to construct submission context."""
    payload = project_request()
    del payload["submission_context"]["datatype"]

    with pytest.raises(ValidationError):
        ProjectIngesterRequest.model_validate(payload)
