"""Integration regressions for declarative business keys.

The tests run the core pipeline over a real local source file. They confirm that
output columns come from producers, that a missing business key fails at the
right validation stage, and that neither validation nor extraction rewrites the
source file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.specifications.entity import EntityFieldsBaseSpecification

# pylint: disable=redefined-outer-name

SOURCE_HEADER = "sample_code,site_code,measure"
SOURCE_ROWS = "S1,A,10\nS2,B,20\n"
PRODUCER_QUERY = "SELECT sample_code, site_code, measure FROM raw ORDER BY sample_code"


def _write_source(path: Path) -> None:
    """Write the shared local source file used by both cases."""
    path.write_text(f"{SOURCE_HEADER}\n{SOURCE_ROWS}", encoding="utf-8")


def _source_backed_project(csv_path: Path, target_keys: list[str]) -> dict[str, Any]:
    """Build a project whose SQL entity exposes loader-discovered columns.

    ``raw`` loads a real CSV file with producer-declared columns. ``sample``
    queries that table through the internal DuckDB workspace with no stored
    columns, so its columns are discovered by the loader at run time.
    """
    return {
        "entities": {
            "raw": {
                "type": "csv",
                "options": {"filename": str(csv_path)},
                "columns": ["sample_code", "site_code", "measure"],
                "keys": ["sample_code"],
            },
            "sample": {
                "type": "sql",
                "data_source": "@internal",
                "depends_on": ["raw"],
                "columns": [],
                "keys": target_keys,
                "query": PRODUCER_QUERY,
            },
        }
    }


@pytest.mark.asyncio
async def test_loader_discovered_missing_key_fails_at_runtime_without_writing_source(tmp_path: Path) -> None:
    """A key absent from loader-discovered columns fails after loading and leaves the source file unchanged."""
    csv_path = tmp_path / "source.csv"
    _write_source(csv_path)
    before = csv_path.read_bytes()

    project = ShapeShiftProject(cfg=_source_backed_project(csv_path, ["missing_key"]), filename=str(tmp_path / "project.yml"))
    normalizer = ShapeShifter(project=project)

    try:
        with pytest.raises(ValueError) as excinfo:
            await normalizer.normalize()
    finally:
        normalizer.duckdb_workspace.close()
        normalizer.loaders.close_all()

    message = str(excinfo.value)
    assert "sample" in message
    assert "missing_key" in message
    assert "do not create output columns" in message
    # A failed run must not repair configuration by touching the source file.
    assert csv_path.read_bytes() == before


@pytest.mark.asyncio
async def test_loader_discovered_produced_key_keeps_producer_column_order(tmp_path: Path) -> None:
    """A produced key appears once, in producer order, among loader-discovered columns."""
    csv_path = tmp_path / "source.csv"
    _write_source(csv_path)
    before = csv_path.read_bytes()

    project = ShapeShiftProject(cfg=_source_backed_project(csv_path, ["site_code"]), filename=str(tmp_path / "project.yml"))
    normalizer = ShapeShifter(project=project)

    try:
        await normalizer.normalize()
        columns: list[str] = list(normalizer.table_store["sample"].columns)
    finally:
        normalizer.duckdb_workspace.close()
        normalizer.loaders.close_all()

    # Identity leads, then the producer columns in query order; the key adds no extra position.
    assert columns == ["system_id", "sample_code", "site_code", "measure"]
    assert columns.count("site_code") == 1
    assert csv_path.read_bytes() == before


def test_configured_missing_key_fails_structural_validation_before_loading(tmp_path: Path) -> None:
    """A configured key with no producer fails structural validation without reading the source file."""
    missing_source = tmp_path / "not_loaded.csv"
    spec = EntityFieldsBaseSpecification(
        {
            "entities": {
                "sample": {
                    "type": "csv",
                    "options": {"filename": str(missing_source)},
                    "columns": ["site_code"],
                    "keys": ["missing_key"],
                }
            }
        }
    )

    assert spec.is_satisfied_by(entity_name="sample") is False
    error_text = "\n".join(str(error) for error in spec.errors)
    assert "sample" in error_text
    assert "missing_key" in error_text
    assert "do not create output columns" in error_text
    # Structural validation must not load the source, so the file stays absent.
    assert not missing_source.exists()
