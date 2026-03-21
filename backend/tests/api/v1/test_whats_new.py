"""Tests for the what's-new manifest endpoint."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_whats_new_manifest_returns_archive() -> None:
    """The what's-new manifest should expose the generated release note archive."""
    response = client.get("/api/v1/whats-new")
    assert response.status_code == 200

    data = response.json()
    assert data["latest_version"] == "1.24.0"
    assert len(data["items"]) >= 24

    latest = data["items"][0]
    assert latest["version"] == "1.24.0"
    assert latest["path"] == "/docs/whats-new/v1.24.0.md"
    assert latest["title"] == "What's New in v1.24.0"
    assert latest["date"] == "2026-03-17"


def test_whats_new_manifest_is_sorted_descending() -> None:
    """Manifest items should be sorted by semantic version descending."""
    response = client.get("/api/v1/whats-new")
    assert response.status_code == 200

    versions = [item["version"] for item in response.json()["items"][:5]]
    assert versions == ["1.24.0", "1.23.0", "1.22.0", "1.21.0", "1.20.0"]
