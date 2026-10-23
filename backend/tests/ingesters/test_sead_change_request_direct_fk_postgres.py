"""Disposable PostgreSQL checks for direct target-ID foreign keys."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import psycopg
import pytest
from psycopg import sql

from backend.app.ingesters.protocol import IngesterConfig
from backend.app.services.ingester_runtime import SeadChangeRequestTargetCollisionChecker
from ingesters.sead_change_request.ingester import SeadChangeRequestIngester

pytestmark = pytest.mark.integration

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _connection_parameters() -> dict[str, Any]:
    """Return loopback disposable-database settings or skip this integration test."""
    host = os.getenv("SEAD_DISPOSABLE_POSTGRES_HOST")
    port = os.getenv("SEAD_DISPOSABLE_POSTGRES_PORT")
    dbname = os.getenv("SEAD_DISPOSABLE_POSTGRES_DB")
    user = os.getenv("SEAD_DISPOSABLE_POSTGRES_USER")
    if not all((host, port, dbname, user)):
        pytest.skip("Set SEAD_DISPOSABLE_POSTGRES_* variables for the loopback disposable database test")
    if host not in LOOPBACK_HOSTS:
        pytest.fail("The disposable PostgreSQL integration test only accepts a loopback host")

    parameters: dict[str, Any] = {"host": host, "port": int(str(port)), "dbname": dbname, "user": user}
    password = os.getenv("SEAD_DISPOSABLE_POSTGRES_PASSWORD")
    if password:
        parameters["password"] = password
    return parameters


def _create_disposable_schema(parameters: dict[str, Any], schema_name: str) -> None:
    """Create only the target tables needed by direct-ID verification."""
    schema = sql.Identifier(schema_name)
    target_types = sql.Identifier(schema_name, "tbl_location_types")
    target_locations = sql.Identifier(schema_name, "tbl_locations")
    with psycopg.connect(**parameters, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            cursor.execute(sql.SQL("CREATE TABLE {} (location_type_id integer PRIMARY KEY)").format(target_types))
            cursor.execute(
                sql.SQL("CREATE TABLE {} (location_id integer PRIMARY KEY, location_type_id integer NOT NULL)").format(target_locations)
            )
            cursor.execute(
                sql.SQL("INSERT INTO {} (location_type_id) VALUES (%s)").format(target_types),
                (42,),
            )


def _target_model(schema_name: str) -> dict[str, Any]:
    """Return a target model whose public-ID tables are in the disposable schema."""
    return {
        "model": {"name": "Disposable Direct FK Model", "version": "0.1.0"},
        "constraints": [],
        "entities": {
            "location_type": {
                "role": "lookup",
                "public_id": "location_type_id",
                "target_table": f"{schema_name}.tbl_location_types",
            },
            "location": {
                "role": "fact",
                "public_id": "location_id",
                "target_table": f"{schema_name}.tbl_locations",
                "columns": {"location_type_id": {"type": "integer", "nullable": False}},
                "foreign_keys": [{"entity": "location_type", "required": True}],
            },
        },
    }


def _ingester(
    schema_name: str,
    target_id: int,
    output_folder: Path,
    checker: object,
) -> tuple[SeadChangeRequestIngester, dict[str, pd.DataFrame]]:
    """Build one ingester with a direct ID and preassigned row identity."""
    tables = {"location": pd.DataFrame({"location_id": [None], "location_type_id": [target_id]})}
    config = IngesterConfig(
        host="localhost",
        port=5432,
        dbname="disposable",
        user="disposable",
        output_folder=str(output_folder),
        extra={
            "target_model": _target_model(schema_name),
            "foreign_key_value_sources": {"location": {"location_type": "public_id"}},
            "submission_context": {
                "submission_name": "phase3-direct-fk",
                "project_name": "direct-fk-test",
                "timestamp": "2026-10-23T12:00:00",
                "datatype": "mal",
                "identifier": "PHASE3_DIRECT_FK",
                "scope_name": "provider://direct-fk-test",
            },
            "identity_assignments": {
                "location": {0: {"state": "newly_allocated_entity", "target_id": 601}},
            },
            "collision_checker": checker,
        },
    )
    return SeadChangeRequestIngester(config), tables


class _UnavailableTargetLookup:
    """Use the real type check and fail when the row lookup is requested."""

    def __init__(self, checker: SeadChangeRequestTargetCollisionChecker) -> None:
        self._checker = checker

    async def target_id_column_type(self, table_name: str, public_id_column: str) -> str | None:
        return await self._checker.target_id_column_type(table_name, public_id_column)

    async def target_id_exists(self, _table_name: str, _public_id_column: str, _target_id: int) -> bool:
        raise psycopg.OperationalError("target row lookup unavailable")

    async def row_exists(self, table_name: str, filters: dict[str, object]) -> bool:
        return await self._checker.row_exists(table_name, filters)


@pytest.mark.asyncio
async def test_direct_fk_uses_real_postgres_lookup_before_package_acceptance(tmp_path: Path) -> None:
    """Accept an existing ID and reject absent or unavailable IDs through both table methods."""
    parameters = _connection_parameters()
    schema_name = f"shifter_direct_fk_{uuid4().hex[:12]}"
    schema = sql.Identifier(schema_name)
    checker = SeadChangeRequestTargetCollisionChecker(**parameters)

    try:
        _create_disposable_schema(parameters, schema_name)
        assert await checker.target_id_column_type(f"{schema_name}.tbl_location_types", "location_type_id") == "integer"
        assert await checker.target_id_exists(f"{schema_name}.tbl_location_types", "location_type_id", 42)

        accepted, accepted_tables = _ingester(schema_name, 42, tmp_path / "accepted", checker)
        accepted_validation = await accepted.validate_tables(accepted_tables)
        accepted_result = await accepted.ingest_tables(accepted_tables)

        assert accepted_validation.is_valid is True
        assert accepted_result.success is True
        assert accepted_result.output_path is not None
        assert accepted_result.deploy_artifact is not None
        expected_fk = [{"source_entity": "location", "target_entity": "location_type", "column": "location_type_id"}]
        assert accepted_result.deploy_artifact["metadata_artifact"]["direct_target_id_foreign_keys"] == expected_fk
        assert "42" in accepted_result.deploy_artifact["deploy_sql"]
        manifest = json.loads((Path(accepted_result.output_path) / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["direct_target_id_foreign_keys"] == expected_fk

        absent, absent_tables = _ingester(schema_name, 99999, tmp_path / "absent", checker)
        absent_validation = await absent.validate_tables(absent_tables)
        absent_result = await absent.ingest_tables(absent_tables)
        assert absent_validation.is_valid is False
        assert "value 99999" in absent_validation.errors[0]
        assert absent_result.success is False
        assert "value 99999" in (absent_result.error_details or "")
        assert not (tmp_path / "absent").exists() or not list((tmp_path / "absent").iterdir())

        unavailable, unavailable_tables = _ingester(
            schema_name,
            42,
            tmp_path / "unavailable",
            _UnavailableTargetLookup(checker),
        )
        unavailable_validation = await unavailable.validate_tables(unavailable_tables)
        unavailable_result = await unavailable.ingest_tables(unavailable_tables)
        assert unavailable_validation.is_valid is False
        assert "lookup unavailable" in unavailable_validation.errors[0]
        assert unavailable_result.success is False
        assert "lookup unavailable" in (unavailable_result.error_details or "")
        assert not (tmp_path / "unavailable").exists() or not list((tmp_path / "unavailable").iterdir())
    finally:
        with psycopg.connect(**parameters, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(schema))
