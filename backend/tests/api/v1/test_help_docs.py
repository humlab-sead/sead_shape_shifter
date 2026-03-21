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


def test_help_doc_returns_nested_markdown_file() -> None:
    """The Help view endpoint should allow safe nested docs paths."""
    response = client.get("/api/v1/help-docs/other/USER_GUIDE_APPENDIX")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text.startswith("# Shape Shifter Project Editor - Appendix")


def test_help_doc_rejects_invalid_name() -> None:
    """Help doc paths should be sanitized to prevent path traversal."""
    response = client.get("/api/v1/help-docs/%2E%2E/USER_GUIDE")
    assert response.status_code == 400