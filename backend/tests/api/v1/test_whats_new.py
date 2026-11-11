"""Tests for the what's-new manifest endpoint."""

import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import whats_new as whats_new_endpoint
from backend.app.main import app


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as client:
        yield client


def test_whats_new_manifest_returns_archive(client) -> None:
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


def test_whats_new_manifest_is_sorted_descending(client) -> None:
    """Manifest items should be sorted by semantic version descending."""
    response = client.get("/api/v1/whats-new")
    assert response.status_code == 200

    versions = [item["version"] for item in response.json()["items"][:5]]
    assert versions == sorted(versions, key=lambda v: list(map(int, v.split("."))), reverse=True)


def test_whats_new_content_returns_markdown(client) -> None:
    """The frontend should be able to fetch markdown content through the API."""
    data = client.get("/api/v1/whats-new").json()

    response = client.get(f"/api/v1/whats-new/{data['latest_version']}/content")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text.startswith(f"# What's New in v{data['latest_version']}")


def test_manifest_and_endpoint_include_pending_snapshot(monkeypatch, tmp_path, client) -> None:
    """The pending snapshot is available separately from versioned release notes."""
    (tmp_path / "v2.5.0.md").write_text("# What's New in v2.5.0\n\nDate: 2026-10-27\n", encoding="utf-8")
    pending_content = "# Pending Release\n\nA change is not in a released version yet.\n"
    (tmp_path / "PENDING.md").write_text(pending_content, encoding="utf-8")
    monkeypatch.setattr(whats_new_endpoint, "WHATS_NEW_DIR", tmp_path)

    manifest_response = client.get("/api/v1/whats-new")
    pending_response = client.get("/api/v1/whats-new/pending")

    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["pending_available"] is True
    assert [item["version"] for item in manifest["items"]] == ["2.5.0"]
    assert pending_response.status_code == 200
    assert pending_response.headers["content-type"].startswith("text/markdown")
    assert pending_response.text == pending_content


def test_pending_snapshot_is_unavailable_when_file_is_missing(monkeypatch, tmp_path, client) -> None:
    monkeypatch.setattr(whats_new_endpoint, "WHATS_NEW_DIR", tmp_path)

    manifest_response = client.get("/api/v1/whats-new")
    pending_response = client.get("/api/v1/whats-new/pending")

    assert manifest_response.json()["pending_available"] is False
    assert pending_response.status_code == 404
