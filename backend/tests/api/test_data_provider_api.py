"""Tests for the read-only data provider API endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import settings as application_settings
from backend.app.main import app

# pylint: disable=redefined-outer-name, unused-argument

PROVIDER_PATH = "/api/v1/data-providers"

PROVIDER_RECORD = (
    "code: synthetic\n"
    "name: Synthetic Provider\n"
    "schemas:\n"
    "  - provider_schema: radiocarbon/strucke-pilot\n"
    "    scope_name: provider://synthetic/radiocarbon/strucke-pilot\n"
    "  - provider_schema: archeobotany/arbodat-pilot\n"
    "    scope_name: provider://synthetic/archeobotany/arbodat-pilot\n"
)


@pytest.fixture
def provider_dir(tmp_path: Path, monkeypatch) -> Path:
    """Point the configured provider directory at an isolated temporary directory."""
    directory = tmp_path / "data-providers"
    directory.mkdir()
    monkeypatch.setattr(application_settings, "GLOBAL_DATA_PROVIDER_DIR", directory)
    return directory


def _write_provider(directory: Path, filename: str, content: str) -> Path:
    """Write one provider file into the temporary registry."""
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_lists_providers_for_authenticated_principal(authorized_client: AsyncClient, provider_dir: Path) -> None:
    """An authenticated request returns providers with nested schema scopes in sorted order."""
    _write_provider(provider_dir, "synthetic.yml", PROVIDER_RECORD)
    _write_provider(
        provider_dir,
        "another.yml",
        "code: another\nname: Another\nschemas:\n  - provider_schema: alpha\n    scope_name: provider://another/alpha\n",
    )

    response = await authorized_client.get(PROVIDER_PATH)

    assert response.status_code == 200
    assert response.json() == [
        {"code": "another", "name": "Another", "schemas": [{"provider_schema": "alpha", "scope_name": "provider://another/alpha"}]},
        {
            "code": "synthetic",
            "name": "Synthetic Provider",
            "schemas": [
                {"provider_schema": "archeobotany/arbodat-pilot", "scope_name": "provider://synthetic/archeobotany/arbodat-pilot"},
                {"provider_schema": "radiocarbon/strucke-pilot", "scope_name": "provider://synthetic/radiocarbon/strucke-pilot"},
            ],
        },
    ]


@pytest.mark.asyncio
async def test_empty_registry_returns_empty_list(authorized_client: AsyncClient, provider_dir: Path) -> None:
    """An empty provider directory returns an empty list, not an error."""
    response = await authorized_client.get(PROVIDER_PATH)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_invalid_registry_returns_server_error_without_paths(authorized_client: AsyncClient, provider_dir: Path) -> None:
    """Invalid registry content fails the whole response without leaking paths or file content."""
    _write_provider(provider_dir, "synthetic.yml", PROVIDER_RECORD)
    _write_provider(provider_dir, "broken.yml", "code: [unclosed\n")

    response = await authorized_client.get(PROVIDER_PATH)

    assert response.status_code == 500
    assert response.json() == {"detail": "Data provider registry is unavailable"}
    assert str(provider_dir) not in response.text
    assert "synthetic" not in response.text


@pytest.mark.asyncio
async def test_missing_directory_returns_server_error(authorized_client: AsyncClient, provider_dir: Path) -> None:
    """A missing configured directory returns a server error, not an empty list."""
    provider_dir.rmdir()

    response = await authorized_client.get(PROVIDER_PATH)

    assert response.status_code == 500
    assert response.json() == {"detail": "Data provider registry is unavailable"}


@pytest.mark.asyncio
async def test_anonymous_request_is_rejected(provider_dir: Path) -> None:
    """A request without an authenticated principal is rejected."""
    _write_provider(provider_dir, "synthetic.yml", PROVIDER_RECORD)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(PROVIDER_PATH)

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


@pytest.mark.asyncio
async def test_mutation_methods_are_not_available(authorized_client: AsyncClient, provider_dir: Path) -> None:
    """The registry exposes no create, update, or delete route."""
    _write_provider(provider_dir, "synthetic.yml", PROVIDER_RECORD)

    for method in ("post", "put", "patch", "delete"):
        response = await authorized_client.request(method.upper(), PROVIDER_PATH)
        assert response.status_code == 405, method
