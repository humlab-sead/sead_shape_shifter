"""Disposable PostgreSQL tests for the inline staging deploy artifact.

These tests execute the rendered artifact against a loopback-only disposable
database. They create their own schema and target tables so no shared or
representative database is written to.

Set ``SEAD_DISPOSABLE_POSTGRES_HOST``, ``_PORT``, ``_DB``, ``_USER`` and, when
needed, ``_PASSWORD``. A skipped run does not satisfy the phase validation
milestones.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Generator, LiteralString, cast
from uuid import uuid4

import pandas as pd
import psycopg
import pytest
from psycopg.rows import TupleRow

from backend.app.ingesters.protocol import IngesterConfig, IngestionResult
from ingesters.sead_change_request.ingester import SeadChangeRequestIngester

pytestmark = pytest.mark.integration

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
SECOND_SCHEMA = "shifter_secondary"


# pylint: disable=unused-argument


class _SimsClient:
    """Return one deterministic SIMS target ID per allocated row."""

    def __init__(self, target_ids: dict[str, int] | None = None, default_target_id: int = 5001) -> None:
        self.target_ids = target_ids or {}
        self.default_target_id = default_target_id
        self.requests: list[str] = []

    async def resolve_batch(self, items, submission_context) -> dict[str, Any]:  # pylint: disable=unused-argument
        outcomes = []
        for item in items:
            self.requests.append(item.entity_name)
            outcomes.append({"target_id": self.target_ids.get(item.entity_name, self.default_target_id), "tracked_identity_uuid": None})
        return {"outcomes": outcomes, "binding_set_uuid": "binding-staging", "binding_set_state": "confirmed"}

    async def get_binding_set_state(self, binding_set_uuid: str) -> str:
        return "confirmed"

    async def derive_bridge_row(self, entity_name: str, row: dict, submission_context) -> dict[str, Any]:
        return {"state": "derived_bridge_row", "note": f"Derived {entity_name}"}

    async def associate_change_request(self, binding_set_uuid: str, change_request_name: str) -> None:
        return None


class _ReconciliationClient:
    """Return a configured existing target ID for reconciled lookups."""

    def __init__(self, target_ids: dict[str, int] | None = None) -> None:
        self.target_ids = target_ids or {}

    async def reconcile_entity(self, entity_name: str, row: dict) -> int | None:
        return self.target_ids.get(entity_name)


def _connection_parameters() -> dict[str, Any]:
    """Return disposable connection parameters or skip the test."""
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


@pytest.fixture(name="disposable_schema")
def _disposable_schema() -> Generator[str, None, None]:
    """Create an isolated schema with staging target tables and drop it afterwards."""
    parameters = _connection_parameters()
    schema_name = f"shifter_staging_{uuid4().hex[:12]}"
    ddl = [
        f'CREATE SCHEMA "{schema_name}"',
        f'CREATE SCHEMA "{SECOND_SCHEMA}"',
        f'CREATE TABLE "{schema_name}".tbl_sites (site_id serial PRIMARY KEY, site_name text NOT NULL)',
        (f'CREATE TABLE "{schema_name}".tbl_datasets (dataset_id serial PRIMARY KEY, site_id bigint NOT NULL, dataset_name text NOT NULL)'),
        (
            f'CREATE TABLE "{schema_name}".tbl_analysis_entities ('
            "analysis_entity_id serial PRIMARY KEY, dataset_id bigint NOT NULL, taxon_id bigint)"
        ),
        (
            f'CREATE TABLE "{schema_name}".tbl_abundances ('
            "abundance_id serial PRIMARY KEY, analysis_entity_id bigint NOT NULL, taxon_id bigint NOT NULL)"
        ),
        (
            f'CREATE TABLE "{schema_name}".tbl_abundance_ident_levels ('
            "abundance_ident_level_id serial PRIMARY KEY, abundance_id bigint NOT NULL, identification_level_id bigint NOT NULL)"
        ),
        f'CREATE TABLE "{SECOND_SCHEMA}".tbl_abundances (abundance_id serial PRIMARY KEY)',
    ]
    cleanup = [f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE', f'DROP SCHEMA IF EXISTS "{SECOND_SCHEMA}" CASCADE']

    with psycopg.connect(**parameters, autocommit=True) as connection:
        with connection.cursor() as cursor:
            for statement in cleanup:
                cursor.execute(cast(LiteralString, statement))
            for statement in ddl:
                cursor.execute(cast(LiteralString, statement))
    try:
        yield schema_name
    finally:
        with psycopg.connect(**parameters, autocommit=True) as connection:
            with connection.cursor() as cursor:
                for statement in cleanup:
                    cursor.execute(cast(LiteralString, statement))


def _target_model() -> dict[str, Any]:
    """Return a target model matching the disposable target tables."""
    return {
        "model": {"name": "Disposable Staging Model", "version": "0.1.0"},
        "entities": {
            "site": {"role": "lookup", "public_id": "site_id", "target_table": "tbl_sites"},
            "dataset": {
                "role": "lookup",
                "identity_tracking": "tracked",
                "reconciliation": "allocate",
                "public_id": "dataset_id",
                "target_table": "tbl_datasets",
                "synchronize_sequence_after_insert": True,
                "unique_sets": [["site_id", "dataset_name"]],
                "columns": {
                    "site_id": {"required": True, "type": "integer", "nullable": False},
                    "dataset_name": {"required": True, "type": "string", "nullable": False},
                },
                "foreign_keys": [{"entity": "site", "required": True}],
            },
            "analysis_entity": {
                "role": "fact",
                "public_id": "analysis_entity_id",
                "target_table": "tbl_analysis_entities",
                "aggregate_parent": "dataset",
                "columns": {
                    "dataset_id": {"required": True, "type": "integer", "nullable": False},
                    "taxon_id": {"type": "integer", "nullable": True},
                },
                "foreign_keys": [{"entity": "dataset", "required": True}],
            },
            "abundance": {
                "role": "fact",
                "public_id": "abundance_id",
                "target_table": "tbl_abundances",
                "aggregate_parent": "analysis_entity",
                "unique_sets": [["analysis_entity_id", "taxon_id"]],
                "columns": {
                    "analysis_entity_id": {"required": True, "type": "integer", "nullable": False},
                    "taxon_id": {"required": True, "type": "integer", "nullable": False},
                },
                "foreign_keys": [{"entity": "analysis_entity", "required": True}],
            },
            "abundance_ident_level": {
                "role": "bridge",
                "public_id": "abundance_ident_level_id",
                "target_table": "tbl_abundance_ident_levels",
                "unique_sets": [["abundance_id", "identification_level_id"]],
                "columns": {
                    "abundance_id": {"required": True, "type": "integer", "nullable": False},
                    "identification_level_id": {"required": True, "type": "integer", "nullable": False},
                },
                "foreign_keys": [{"entity": "abundance", "required": True}],
            },
        },
        "constraints": [],
    }


def _submission_context() -> dict[str, Any]:
    """Return a minimal submission context payload."""
    return {
        "submission_name": "staging-submission",
        "project_name": "staging-project",
        "timestamp": datetime(2026, 10, 17, 10, 0, 0).isoformat(),
        "datatype": "mal",
        "identifier": "STAGING_CASE",
        "author": "SEAD Expert",
        "issue_identifier": "NNN",
    }


def _source_tables(
    *,
    analysis_entity_taxon_id: int = 11,
    abundance_taxa: tuple[int, ...] = (21, 22),
    dataset_public_id: int | None = None,
    dataset_name: str = "D1",
) -> dict[str, pd.DataFrame]:
    """Return a source bundle that exercises a multi-level aggregate chain."""
    dataset_public_ids = [dataset_public_id] if dataset_public_id is not None else [None]
    return {
        "site": pd.DataFrame({"system_id": [1], "site_id": [7001]}),
        "dataset": pd.DataFrame({"system_id": [10], "dataset_id": dataset_public_ids, "site_id": [1], "dataset_name": [dataset_name]}),
        "analysis_entity": pd.DataFrame(
            {"system_id": [100], "analysis_entity_id": [None], "dataset_id": [10], "taxon_id": [analysis_entity_taxon_id]}
        ),
        "abundance": pd.DataFrame(
            {
                "system_id": list(range(1000, 1000 + len(abundance_taxa))),
                "abundance_id": [None] * len(abundance_taxa),
                "analysis_entity_id": [100] * len(abundance_taxa),
                "taxon_id": list(abundance_taxa),
            }
        ),
    }


def _ingester(
    tables: dict[str, pd.DataFrame],
    *,
    schema: str | None,
    output_folder: Any,
    sims: _SimsClient | None = None,
    reconciliation: _ReconciliationClient | None = None,
    target_model: dict[str, Any] | None = None,
) -> SeadChangeRequestIngester:
    """Build an ingester configured for inline staging."""
    return SeadChangeRequestIngester(
        IngesterConfig(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            output_folder=str(output_folder),
            extra={
                "tables": tables,
                "target_model": target_model or _target_model(),
                "submission_context": _submission_context(),
                "sims_client": sims or _SimsClient(),
                "reconciliation_client": reconciliation or _ReconciliationClient({"site": 7001}),
                "deploy_strategy": "inline_staging",
                "staging_target_schema": schema,
            },
        )
    )


def __in_memory_source_tables(ingester: SeadChangeRequestIngester) -> dict[str, pd.DataFrame]:
    """Return the in-memory tables declared by the ingester configuration."""
    extras = ingester.config.extra or {}
    tables = extras["tables"]
    assert isinstance(tables, dict)
    return tables


async def _ingest(ingester: SeadChangeRequestIngester) -> IngestionResult:
    """Ingest the configured tables through the public table method."""
    return await ingester.ingest_tables(__in_memory_source_tables(ingester))


def _run_statements(parameters: dict[str, Any], statements: list[str], *, lock_timeout_ms: int | None = None) -> None:
    """Execute the staged statements in one transaction."""
    with psycopg.connect(**parameters) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                if lock_timeout_ms is not None:
                    cursor.execute(cast(LiteralString, f"SET LOCAL lock_timeout = '{lock_timeout_ms}ms'"))
                for statement in statements:
                    cursor.execute(cast(LiteralString, statement))


async def _deploy(tables: dict[str, pd.DataFrame], schema: str, output_folder: Any, **kwargs: Any) -> list[str]:
    """Render the staging artifact and return its statements."""
    result = await _ingest(_ingester(tables, schema=schema, output_folder=output_folder, **kwargs))
    assert result.success is True, result.error_details
    assert result.deploy_artifact is not None
    assert "metadata" in result.deploy_artifact
    assert "statements" in result.deploy_artifact
    assert "deploy_strategy" in result.deploy_artifact["metadata"]
    assert result.deploy_artifact["metadata"]["deploy_strategy"] == "inline_staging"
    return list(result.deploy_artifact["statements"])


def _scalar(parameters: dict[str, Any], query: str) -> Any:
    """Return the first column of the first row."""
    with psycopg.connect(**parameters) as connection:
        with connection.cursor() as cursor:
            cursor.execute(cast(LiteralString, query))
            row = cursor.fetchone()
    return None if row is None else row[0]


class TestInlineStagingDeployment:
    """Successful deployments on a disposable database (VM-2)."""

    @pytest.mark.asyncio
    async def test_multi_level_chain_allocates_ids_and_resolves_foreign_keys(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        statements = await _deploy(
            _source_tables(),
            disposable_schema,
            tmp_path,
            sims=_SimsClient({"dataset": 900}),
        )

        _run_statements(parameters, statements)

        dataset_ids = {row[0] for row in _rows(parameters, f'SELECT dataset_id FROM "{disposable_schema}".tbl_datasets')}
        analysis_rows = _rows(parameters, f'SELECT analysis_entity_id, dataset_id FROM "{disposable_schema}".tbl_analysis_entities')
        abundance_rows = _rows(
            parameters, f'SELECT abundance_id, analysis_entity_id, taxon_id FROM "{disposable_schema}".tbl_abundances ORDER BY taxon_id'
        )
        bridge_rows = _rows(parameters, f'SELECT abundance_id FROM "{disposable_schema}".tbl_abundance_ident_levels')

        assert dataset_ids == {900}
        assert len(analysis_rows) == 1
        assert analysis_rows[0][1] == 900
        assert [row[2] for row in abundance_rows] == [21, 22]
        assert {row[1] for row in abundance_rows} == {analysis_rows[0][0]}
        assert not bridge_rows

    @pytest.mark.asyncio
    async def test_reference_only_reconciled_root_supplies_a_known_id(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        with psycopg.connect(**parameters, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    cast(
                        LiteralString,
                        f"INSERT INTO \"{disposable_schema}\".tbl_sites (site_name) VALUES ('Existing site') RETURNING site_id",
                    )
                )

                row: TupleRow | None = cursor.fetchone()
                assert row is not None
                existing_site_id = row[0]

        tables = _source_tables()
        tables["site"] = pd.DataFrame({"system_id": [1], "site_id": [existing_site_id]})
        statements = await _deploy(tables, disposable_schema, tmp_path)

        _run_statements(parameters, statements)

        inserted_sites = _scalar(parameters, f'SELECT count(*) FROM "{disposable_schema}".tbl_sites')
        dataset_site = _scalar(parameters, f'SELECT site_id FROM "{disposable_schema}".tbl_datasets')
        assert inserted_sites == 1
        assert dataset_site == existing_site_id

    @pytest.mark.asyncio
    async def test_permuted_payload_order_preserves_local_relationships(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        forward = await _deploy(
            _source_tables(abundance_taxa=(31, 32), dataset_name="FWD"),
            disposable_schema,
            tmp_path,
            sims=_SimsClient({"dataset": 7101}),
        )
        _run_statements(parameters, forward)
        reverse = await _deploy(
            _source_tables(abundance_taxa=(32, 31), dataset_name="REV"),
            disposable_schema,
            tmp_path,
            sims=_SimsClient({"dataset": 7102}),
        )
        _run_statements(parameters, reverse)

        forward_rows = _rows(parameters, _taxon_dataset_query(disposable_schema, "FWD"))
        reverse_rows = _rows(parameters, _taxon_dataset_query(disposable_schema, "REV"))

        assert [row[0] for row in forward_rows] == [31, 32]
        assert [row[0] for row in reverse_rows] == [31, 32]
        assert len({row[1] for row in forward_rows}) == 1
        assert len({row[1] for row in reverse_rows}) == 1
        assert len({row[2] for row in forward_rows}) == 1
        assert len({row[2] for row in reverse_rows}) == 1

    @pytest.mark.asyncio
    async def test_stale_sequence_is_synchronized_before_allocation(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        statements = await _deploy(_source_tables(dataset_name="STALE1"), disposable_schema, tmp_path, sims=_SimsClient({"dataset": 7201}))
        _run_statements(parameters, statements)
        first_max = _scalar(parameters, f'SELECT max(abundance_id) FROM "{disposable_schema}".tbl_abundances')

        with psycopg.connect(**parameters, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    cast(
                        LiteralString,
                        f"SELECT setval(pg_get_serial_sequence('\"{disposable_schema}\".tbl_abundances', 'abundance_id'), 1, true)",
                    )
                )

        second = await _deploy(
            _source_tables(abundance_taxa=(61,), dataset_name="STALE2"),
            disposable_schema,
            tmp_path,
            sims=_SimsClient({"dataset": 7202}),
        )
        _run_statements(parameters, second)
        second_max = _scalar(parameters, f'SELECT max(abundance_id) FROM "{disposable_schema}".tbl_abundances')

        assert second_max > first_max

    @pytest.mark.asyncio
    async def test_competing_writer_waits_for_the_staging_lock(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        statements = await _deploy(_source_tables(), disposable_schema, tmp_path)

        with psycopg.connect(**parameters) as holder:
            with holder.transaction():
                with holder.cursor() as holder_cursor:
                    for statement in statements:
                        holder_cursor.execute(cast(LiteralString, statement))

                    with psycopg.connect(**parameters) as other:
                        with pytest.raises(psycopg.errors.LockNotAvailable):
                            with other.transaction():
                                with other.cursor() as other_cursor:
                                    other_cursor.execute(cast(LiteralString, "SET LOCAL lock_timeout = '500ms'"))
                                    other_cursor.execute(
                                        cast(LiteralString, f'LOCK TABLE "{disposable_schema}".tbl_abundances IN ROW EXCLUSIVE MODE')
                                    )

    @pytest.mark.asyncio
    async def test_sims_assigned_sequence_is_advanced_after_insert(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        statements = await _deploy(_source_tables(), disposable_schema, tmp_path, sims=_SimsClient({"dataset": 8001}))
        _run_statements(parameters, statements)

        last_value = _scalar(
            parameters, f"SELECT last_value FROM {_sequence_name(parameters, disposable_schema, 'tbl_datasets', 'dataset_id')}"
        )

        assert last_value >= 8001


class TestInlineStagingRejections:
    """Pre-insert failures and rollback on a disposable database (VM-3)."""

    @pytest.mark.asyncio
    async def test_ambiguous_relation_without_a_schema_is_rejected(self, disposable_schema: str, tmp_path):
        result = await _ingest(_ingester(_source_tables(), schema=None, output_folder=tmp_path))

        assert result.success is False
        assert result.message == "Validation failed"
        assert result.error_details is not None
        assert "requires a non-empty 'staging_target_schema'" in result.error_details

    @pytest.mark.asyncio
    async def test_absent_relation_is_rejected_before_any_insert(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        statements = await _deploy(_source_tables(), "shifter_missing_schema", tmp_path)

        with pytest.raises(psycopg.errors.RaiseException, match="does not exist"):
            _run_statements(parameters, statements)

        assert _scalar(parameters, f'SELECT count(*) FROM "{disposable_schema}".tbl_datasets') == 0

    @pytest.mark.asyncio
    async def test_duplicate_unique_set_in_staged_rows_is_rejected(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        statements = await _deploy(_source_tables(abundance_taxa=(41, 41)), disposable_schema, tmp_path)

        with pytest.raises(psycopg.errors.RaiseException, match="duplicate unique_set"):
            _run_statements(parameters, statements)

        assert _scalar(parameters, f'SELECT count(*) FROM "{disposable_schema}".tbl_abundances') == 0

    @pytest.mark.asyncio
    async def test_existing_target_unique_set_match_is_rejected(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        seed = await _deploy(_source_tables(dataset_name="REPEAT"), disposable_schema, tmp_path, sims=_SimsClient({"dataset": 7301}))
        _run_statements(parameters, seed)
        existing_dataset_id = _scalar(parameters, f'SELECT max(dataset_id) FROM "{disposable_schema}".tbl_datasets')

        again = await _deploy(
            _source_tables(dataset_name="REPEAT"),
            disposable_schema,
            tmp_path,
            sims=_SimsClient({"dataset": existing_dataset_id + 1}),
        )

        with pytest.raises(psycopg.errors.RaiseException, match="match an existing target row"):
            _run_statements(parameters, again)

    @pytest.mark.asyncio
    async def test_child_of_an_existing_tracked_root_is_rejected(self, disposable_schema: str, tmp_path):
        result = await _ingest(_ingester(_source_tables(dataset_public_id=910), schema=disposable_schema, output_folder=tmp_path))

        assert result.success is False
        assert result.error_details is not None
        assert "existing tracked root" in result.error_details

    @pytest.mark.asyncio
    async def test_unresolved_reconciled_root_prevents_target_inserts(self, disposable_schema: str, tmp_path):
        """A reconciled root that cannot be resolved blocks dependent rows before any insert."""
        parameters = _connection_parameters()
        model = _target_model()
        # ``lookup-only`` never allocates on a miss, so the root stays unresolved.
        model["entities"]["site"]["reconciliation"] = "lookup-only"
        tables = _source_tables()
        tables["site"] = pd.DataFrame({"system_id": [1], "site_id": [None]})

        result = await _ingest(
            _ingester(
                tables,
                schema=disposable_schema,
                output_folder=tmp_path,
                reconciliation=_ReconciliationClient({}),
                target_model=model,
            )
        )

        assert result.success is False
        assert result.error_details is not None
        assert "site_id" in result.error_details
        assert _scalar(parameters, f'SELECT count(*) FROM "{disposable_schema}".tbl_datasets') == 0

    @pytest.mark.asyncio
    async def test_late_target_constraint_failure_rolls_back(self, disposable_schema: str, tmp_path):
        parameters = _connection_parameters()
        tables = _source_tables()
        tables["dataset"] = pd.DataFrame(
            {"system_id": [10, 11], "dataset_id": [None, None], "site_id": [1, 1], "dataset_name": ["D1", "D2"]}
        )
        statements = await _deploy(tables, disposable_schema, tmp_path)

        with pytest.raises(psycopg.errors.UniqueViolation):
            _run_statements(parameters, statements)

        assert _scalar(parameters, f'SELECT count(*) FROM "{disposable_schema}".tbl_datasets') == 0
        assert _scalar(parameters, f'SELECT count(*) FROM "{disposable_schema}".tbl_analysis_entities') == 0


def _taxon_dataset_query(schema: str, dataset_name: str) -> str:
    """Return a taxon-to-analysis-entity query scoped to one dataset name."""
    return (
        f'SELECT a.taxon_id, a.analysis_entity_id, e.dataset_id FROM "{schema}".tbl_abundances AS a '
        f'JOIN "{schema}".tbl_analysis_entities AS e ON e.analysis_entity_id = a.analysis_entity_id '
        f'JOIN "{schema}".tbl_datasets AS d ON d.dataset_id = e.dataset_id '
        f"WHERE d.dataset_name = {chr(39)}{dataset_name}{chr(39)} ORDER BY a.taxon_id"
    )


def _rows(parameters: dict[str, Any], query: str) -> list[tuple]:
    """Return all rows for a query."""
    with psycopg.connect(**parameters) as connection:
        with connection.cursor() as cursor:
            cursor.execute(cast(LiteralString, query))
            return list(cursor.fetchall())


def _sequence_name(parameters: dict[str, Any], schema: str, table: str, column: str) -> str:
    """Return the quoted sequence name for one target column."""
    name = _scalar(parameters, f"SELECT pg_get_serial_sequence('\"{schema}\".{table}', '{column}')")
    assert name is not None
    return str(name)
