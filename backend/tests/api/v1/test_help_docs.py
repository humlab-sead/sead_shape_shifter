"""Tests for help document endpoints."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_help_doc_returns_user_guide_markdown() -> None:
    """The Help view endpoint should return markdown instead of SPA HTML."""
    response = client.get("/api/v1/help-docs/USER_GUIDE")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text.startswith("# Shape Shifter Project Editor - User Guide")


def test_help_doc_rejects_invalid_name() -> None:
    """Help doc names should be sanitized to prevent path traversal."""
    response = client.get("/api/v1/help-docs/USER.GUIDE")
    assert response.status_code == 400