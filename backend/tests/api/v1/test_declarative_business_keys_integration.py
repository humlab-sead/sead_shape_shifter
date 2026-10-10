"""Cross-layer regressions for declarative business keys.

These tests exercise the persisted backend behavior: validation and reads must
not rewrite an existing fixed project or its values sidecar, and a materialized
entity's named values must survive an open, edit, and save round-trip.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.app.core.config import settings
from backend.app.services import project_service, validation_service, yaml_service

# pylint: disable=redefined-outer-name, unused-argument

FULL_ORDER = ["system_id", "method_id", "created_at", "label"]
LEGACY_ORDER = ["system_id", "method_id", "label", "created_at"]


@pytest.fixture
def reset_services():
    """Reset backend service singletons between tests."""
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    yield

    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


def _error_messages(payload: dict) -> list[str]:
    return [str(entry.get("message", entry)) for entry in payload.get("errors", [])]


async def _create_project(client, name: str, entities: dict) -> Path:
    """Create a project through the protected API and return its YAML path."""
    response = await client.post("/api/v1/projects", json={"name": name, "entities": entities})
    assert response.status_code == 201, response.text
    return settings.PROJECTS_DIR / name / "shapeshifter.yml"


async def test_missing_key_validation_and_reads_leave_project_and_values_unchanged(
    tmp_path: Path, monkeypatch, reset_services, authorized_client
) -> None:
    """An existing fixed entity with an unproduced key must not be repaired by validation or reads."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    entity_data = {
        "type": "fixed",
        "public_id": "sample_id",
        "keys": ["missing_key"],
        "columns": ["name", "country"],
        "values": "@load:materialized/sample.parquet",
    }
    yaml_path = await _create_project(authorized_client, "broken_keys", {"sample": entity_data})

    sidecar_path = tmp_path / "broken_keys" / "materialized" / "sample.parquet"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"system_id": [1], "sample_id": [10], "name": ["Uppsala"], "country": ["Sweden"]}).to_parquet(sidecar_path, index=False)

    yaml_before = yaml_path.read_bytes()
    sidecar_before = sidecar_path.read_bytes()

    project_response = await authorized_client.post("/api/v1/projects/broken_keys/validate")
    assert project_response.status_code == 200
    project_payload = project_response.json()
    assert project_payload["is_valid"] is False
    assert any("missing_key" in message and "do not create output columns" in message for message in _error_messages(project_payload))

    entity_response = await authorized_client.post("/api/v1/projects/broken_keys/entities/sample/validate")
    assert entity_response.status_code == 200
    entity_payload = entity_response.json()
    assert entity_payload["is_valid"] is False
    assert any("missing_key" in message for message in _error_messages(entity_payload))

    get_entity = await authorized_client.get("/api/v1/projects/broken_keys/entities/sample")
    assert get_entity.status_code == 200
    fixed_schema = get_entity.json()["fixed_schema"]
    assert fixed_schema["full_columns"] == ["system_id", "sample_id", "name", "country"]
    assert fixed_schema["key_columns"] == ["missing_key"]

    get_values = await authorized_client.get("/api/v1/projects/broken_keys/entities/sample/values")
    assert get_values.status_code == 200
    assert get_values.json()["columns"] == ["system_id", "sample_id", "name", "country"]

    # No call above may create a placeholder column or repair either file.
    assert yaml_path.read_bytes() == yaml_before
    assert sidecar_path.read_bytes() == sidecar_before


async def test_materialized_values_open_edit_save_roundtrip_preserves_named_rows(
    tmp_path: Path, monkeypatch, reset_services, authorized_client
) -> None:
    """GET, edit one named field, PUT with the ETag, then GET preserves named values and order."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    entity_data = {
        "type": "fixed",
        "public_id": "method_id",
        "keys": ["label"],
        "columns": ["created_at", "label"],
        "values": "@load:materialized/method.parquet",
        "materialized": {
            "enabled": True,
            "source_state": {"type": "csv", "public_id": "method_id", "keys": ["label"]},
            "materialized_at": "2026-06-15T00:00:00Z",
        },
    }
    await _create_project(authorized_client, "materialized", {"method": entity_data})

    sidecar_path = tmp_path / "materialized" / "materialized" / "method.parquet"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"system_id": [1], "method_id": [53], "created_at": ["2026-05-19"], "label": ["Sampling"]}).to_parquet(
        sidecar_path, index=False
    )

    entity_response = await authorized_client.get("/api/v1/projects/materialized/entities/method")
    assert entity_response.status_code == 200
    assert entity_response.json()["fixed_schema"]["full_columns"] == FULL_ORDER

    get_first = await authorized_client.get("/api/v1/projects/materialized/entities/method/values")
    assert get_first.status_code == 200
    first_payload = get_first.json()
    assert first_payload["columns"] == FULL_ORDER
    assert first_payload["values"] == [[1, 53, "2026-05-19", "Sampling"]]

    put_response = await authorized_client.put(
        "/api/v1/projects/materialized/entities/method/values",
        json={"columns": FULL_ORDER, "values": [[1, 53, "2026-05-20", "Sampling"]]},
        headers={"If-Match": first_payload["etag"]},
    )
    assert put_response.status_code == 200, put_response.text

    get_second = await authorized_client.get("/api/v1/projects/materialized/entities/method/values")
    assert get_second.status_code == 200
    second_payload = get_second.json()
    assert second_payload["columns"] == FULL_ORDER
    assert second_payload["values"] == [[1, 53, "2026-05-20", "Sampling"]]

    saved = pd.read_parquet(sidecar_path)
    assert saved.columns.tolist() == FULL_ORDER
    assert saved.values.tolist() == [[1, 53, "2026-05-20", "Sampling"]]
    # The produced key `label` added no position beyond its declared data column.
    assert saved.columns.tolist().count("label") == 1


async def test_materialized_values_accepts_exact_legacy_order_and_keeps_authoritative_file_order(
    tmp_path: Path, monkeypatch, reset_services, authorized_client
) -> None:
    """The exact recognized legacy order is remapped by name before writing."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    entity_data = {
        "type": "fixed",
        "public_id": "method_id",
        "keys": ["label"],
        "columns": ["created_at", "label"],
        "values": "@load:materialized/method.parquet",
    }
    await _create_project(authorized_client, "legacy_order", {"method": entity_data})

    sidecar_path = tmp_path / "legacy_order" / "materialized" / "method.parquet"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"system_id": [1], "method_id": [53], "created_at": ["2026-05-19"], "label": ["Sampling"]}).to_parquet(
        sidecar_path, index=False
    )

    put_response = await authorized_client.put(
        "/api/v1/projects/legacy_order/entities/method/values",
        json={"columns": LEGACY_ORDER, "values": [[1, 53, "Sampling", "2026-05-20"]]},
    )
    assert put_response.status_code == 200, put_response.text
    assert put_response.json()["columns"] == FULL_ORDER
    assert put_response.json()["values"] == [[1, 53, "2026-05-20", "Sampling"]]

    saved = pd.read_parquet(sidecar_path)
    assert saved.columns.tolist() == FULL_ORDER
    assert saved.values.tolist() == [[1, 53, "2026-05-20", "Sampling"]]


async def test_materialized_values_reject_unknown_duplicate_width_and_stale_requests_without_writing(
    tmp_path: Path, monkeypatch, reset_services, authorized_client
) -> None:
    """Unsafe layouts, a mismatched row width, and a stale ETag fail without changing the stored sidecar."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    entity_data = {
        "type": "fixed",
        "public_id": "method_id",
        "keys": ["label"],
        "columns": ["created_at", "label"],
        "values": "@load:materialized/method.parquet",
    }
    await _create_project(authorized_client, "unsafe_writes", {"method": entity_data})

    sidecar_path = tmp_path / "unsafe_writes" / "materialized" / "method.parquet"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"system_id": [1], "method_id": [53], "created_at": ["2026-05-19"], "label": ["Sampling"]}).to_parquet(
        sidecar_path, index=False
    )
    sidecar_before = sidecar_path.read_bytes()

    unknown = await authorized_client.put(
        "/api/v1/projects/unsafe_writes/entities/method/values",
        json={"columns": ["system_id", "method_id", "created_at"], "values": [[1, 53, "2026-05-20"]]},
    )
    assert unknown.status_code == 422

    duplicate = await authorized_client.put(
        "/api/v1/projects/unsafe_writes/entities/method/values",
        json={"columns": ["system_id", "system_id", "created_at", "label"], "values": [[1, 53, "2026-05-20", "Sampling"]]},
    )
    assert duplicate.status_code == 422

    # A correct column order with a short row must not create a placeholder cell or write the file.
    width_mismatch = await authorized_client.put(
        "/api/v1/projects/unsafe_writes/entities/method/values",
        json={"columns": FULL_ORDER, "values": [[1, 53, "2026-05-20"]]},
    )
    assert width_mismatch.status_code == 422

    stale = await authorized_client.put(
        "/api/v1/projects/unsafe_writes/entities/method/values",
        json={"columns": FULL_ORDER, "values": [[1, 53, "2026-05-21", "Sampling"]]},
        headers={"If-Match": "not-the-current-etag"},
    )
    assert stale.status_code == 409

    assert sidecar_path.read_bytes() == sidecar_before
