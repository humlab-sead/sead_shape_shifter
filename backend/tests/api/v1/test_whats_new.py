"""Tests for the what's-new manifest endpoint."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_whats_new_manifest_returns_archive() -> None:
    """The what's-new manifest should expose the generated release note archive."""
    response = client.get("/api/v1/whats-new")
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) >= 0

    latest = data["items"][0]
    assert latest["version"] == data["latest_version"]
    assert latest["path"] == f"/docs/whats-new/v{data['latest_version']}.md"
    assert latest["title"] == f"What's New in v{data['latest_version']}"
    assert latest["date"]


def test_whats_new_manifest_is_sorted_descending() -> None:
    """Manifest items should be sorted by semantic version descending."""
    response = client.get("/api/v1/whats-new")
    assert response.status_code == 200

    versions = [item["version"] for item in response.json()["items"][:5]]
    assert versions == sorted(versions, key=lambda v: list(map(int, v.split("."))), reverse=True)


def test_whats_new_content_returns_markdown() -> None:
    """The frontend should be able to fetch markdown content through the API."""
    data = client.get("/api/v1/whats-new").json()

    response = client.get(f"/api/v1/whats-new/{data['latest_version']}/content")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text.startswith(f"# What's New in v{data['latest_version']}")
