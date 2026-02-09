"""Tests for health check endpoint."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint returns 200 OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "projects_dir" in data
    assert "backups_dir" in data


def test_root_endpoint():
    """Test root endpoint returns API information or frontend."""
    response = client.get("/")
    assert response.status_code == 200

    # If frontend is built, we get HTML; if not, we get JSON
    content_type = response.headers.get("content-type", "")
    
    if "application/json" in content_type:
        # API-only mode (frontend not built)
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert data["docs"] == "/api/v1/docs"
    else:
        # Frontend is built and serving SPA
        # Just verify we get a successful response
        assert "text/html" in content_type or "application/octet-stream" in content_type
