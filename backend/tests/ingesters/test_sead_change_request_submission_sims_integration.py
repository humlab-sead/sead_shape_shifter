"""Disposable PostgreSQL checks for SIMS-allocated submission IDs in change request artifacts."""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import psycopg
import pytest
from psycopg import sql

from backend.app.ingesters import IngesterConfig
from backend.app.services.ingester_runtime import SeadChangeRequestTargetCollisionChecker
from ingesters.sead_change_request.contracts import SubmissionContext, resolve_bundle_name
from ingesters.sead_change_request.ingester import SeadChangeRequestIngester


class DisposableProviderResolver:
    """Resolve the test data provider to a row seeded only during artifact execution."""

    async def reconcile_entity(self, entity_name: str, row: dict[str, Any]) -> int | None:  # pylint: disable=unused-argument
        return 1


class DisposableManagedIdentityAllocator:
    """Return previously SIMS-allocated IDs for the artifact check."""

    target_ids = {
        "submission": 81042,
        "sample": 63876,
        "dataset": 91925,
        "analysis_entity": 223430,
    }

    async def allocate_entity(
        self,
        entity_name: str,
        row: dict[str, Any],  # pylint: disable=unused-argument
        submission_context: SubmissionContext,  # pylint: disable=unused-argument
    ) -> dict[str, Any]:
        return {
            "target_id": self.target_ids[entity_name],
            "binding_set_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "binding_set_state": "confirmed",
            "note": f"Using the existing disposable SIMS {entity_name} reservation",
        }


class RecordingDisposableTargetDatabase(SeadChangeRequestTargetCollisionChecker):
    """Record sequence IDs reserved while using the real disposable database adapter."""

    def __init__(self, **connection_kwargs: Any) -> None:
        super().__init__(**connection_kwargs)
        self.reserved_ids: list[int] = []

    async def reserve_target_id(self, table_name: str, public_id_column: str) -> int | None:
        target_id = await super().reserve_target_id(table_name, public_id_column)
        if target_id is not None:
            self.reserved_ids.append(target_id)
        return target_id


def _submission_target_model() -> dict[str, Any]:
    """Build the target model needed to insert a submission and its linked dataset."""
    return {
        "model": {"name": "Disposable SEAD Model", "version": "1.0.0"},
        "constraints": [],
        "entities": {
            "submission_state": {
                "role": "classifier",
                "public_id": "submission_state_id",
                "target_table": "tbl_submission_states",
            },
            "data_provider": {
                "role": "lookup",
                "public_id": "data_provider_id",
                "target_table": "tbl_data_providers",
            },
            "citation": {"role": "lookup", "public_id": "biblio_id", "target_table": "tbl_biblio"},
            "site": {"role": "lookup", "public_id": "site_id", "target_table": "tbl_sites"},
            "method": {"role": "lookup", "public_id": "method_id", "target_table": "tbl_methods"},
            "sample_group": {
                "role": "lookup",
                "public_id": "sample_group_id",
                "target_table": "tbl_sample_groups",
                "foreign_keys": [
                    {"entity": "site", "required": True},
                    {"entity": "method", "required": True},
                ],
            },
            "sample_type": {"role": "classifier", "public_id": "sample_type_id", "target_table": "tbl_sample_types"},
            "submission": {
                "role": "fact",
                "identity_tracking": "tracked",
                "reconciliation": "allocate",
                "public_id": "submission_id",
                "target_table": "tbl_submissions",
                "foreign_keys": [
                    {"entity": "submission_state", "required": True},
                    {"entity": "data_provider", "required": True},
                    {"entity": "citation"},
                ],
            },
            "dataset": {
                "role": "lookup",
                "identity_tracking": "tracked",
                "reconciliation": "allocate",
                "public_id": "dataset_id",
                "target_table": "tbl_datasets",
                "columns": {
                    "dataset_name": {"required": True, "type": "string", "nullable": False},
                    "data_type_id": {"required": True, "type": "integer", "nullable": False},
                    "method_id": {"required": True, "type": "integer", "nullable": False},
                    "submission_id": {"required": True, "type": "integer", "nullable": False},
                },
                "foreign_keys": [{"entity": "submission", "required": True}],
            },
            "sample": {
                "role": "fact",
                "public_id": "physical_sample_id",
                "target_table": "tbl_physical_samples",
                "columns": {
                    "sample_group_id": {"required": True, "type": "integer", "nullable": False},
                    "sample_type_id": {"required": True, "type": "integer", "nullable": False},
                    "sample_name": {"required": True, "type": "string", "nullable": False},
                },
                "foreign_keys": [
                    {"entity": "sample_group", "required": True},
                    {"entity": "sample_type", "required": True},
                ],
            },
            "analysis_entity": {
                "role": "bridge",
                "identity_tracking": "tracked",
                "reconciliation": "allocate",
                "public_id": "analysis_entity_id",
                "target_table": "tbl_analysis_entities",
                "columns": {
                    "physical_sample_id": {"required": True, "type": "integer", "nullable": False},
                    "dataset_id": {"required": True, "type": "integer", "nullable": False},
                },
                "foreign_keys": [
                    {"entity": "sample", "required": True},
                    {"entity": "dataset", "required": True},
                ],
            },
        },
    }


async def _sequence_state(connection_kwargs: dict[str, Any], table_name: str, column_name: str) -> tuple[int, bool]:
    """Read one target sequence's last value and called state."""
    async with await psycopg.AsyncConnection.connect(**connection_kwargs) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", (table_name, column_name))
            sequence_name = (await cursor.fetchone())[0]
            assert sequence_name is not None
            sequence_identifier = sql.Identifier(*(part.strip('"') for part in sequence_name.split(".")))
            await cursor.execute(sql.SQL("SELECT last_value, is_called FROM {}").format(sequence_identifier))
            last_value, is_called = await cursor.fetchone()
    return int(last_value), bool(is_called)


async def _fetch_count(connection_kwargs: dict[str, Any], query: str, params: tuple[object, ...]) -> int:
    """Return one count from the disposable target database."""
    async with await psycopg.AsyncConnection.connect(**connection_kwargs) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(query, params)
            row = await cursor.fetchone()
    return int(row[0])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_both_artifacts_use_sims_submission_id_and_rollback(tmp_path: Path) -> None:
    """Generate and execute both artifact forms with a SIMS-allocated submission ID."""
    host = os.getenv("SEAD_DISPOSABLE_POSTGRES_HOST")
    port = os.getenv("SEAD_DISPOSABLE_POSTGRES_PORT")
    dbname = os.getenv("SEAD_DISPOSABLE_POSTGRES_DB")
    user = os.getenv("SEAD_DISPOSABLE_POSTGRES_USER")
    if not all((host, port, dbname, user)):
        pytest.skip("Set SEAD_DISPOSABLE_POSTGRES_* variables for the loopback disposable database test")
    if host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("The disposable PostgreSQL integration test only accepts a loopback host")
    psql_path = shutil.which("psql")
    if psql_path is None:
        pytest.skip("psql is required to execute the generated copy_csv artifact")

    connection_kwargs: dict[str, Any] = {
        "host": host,
        "port": int(port),
        "dbname": dbname,
        "user": user,
    }
    password = os.getenv("SEAD_DISPOSABLE_POSTGRES_PASSWORD")
    if password:
        connection_kwargs["password"] = password

    provider_count = await _fetch_count(
        connection_kwargs,
        "SELECT count(*) FROM public.tbl_data_providers WHERE data_provider_id = %s",
        (1,),
    )
    assert provider_count == 0, "Disposable baseline must not already contain provider ID 1"
    initial_submission_sequence = await _sequence_state(connection_kwargs, "public.tbl_submissions", "submission_id")
    managed_sequence_states = {
        ("public.tbl_physical_samples", "physical_sample_id"): await _sequence_state(
            connection_kwargs, "public.tbl_physical_samples", "physical_sample_id"
        ),
        ("public.tbl_datasets", "dataset_id"): await _sequence_state(connection_kwargs, "public.tbl_datasets", "dataset_id"),
        ("public.tbl_analysis_entities", "analysis_entity_id"): await _sequence_state(
            connection_kwargs, "public.tbl_analysis_entities", "analysis_entity_id"
        ),
    }
    target_database = RecordingDisposableTargetDatabase(**connection_kwargs)
    psql_environment = os.environ.copy()
    if password:
        psql_environment["PGPASSWORD"] = password
    artifact_names: list[str] = []
    for strategy in ("inline_insert", "copy_csv"):
        run_id = uuid4().hex
        submission_name = f"ss-{strategy[:1]}-{run_id[:8]}"
        dataset_name = f"ss-ds-{run_id[:8]}"
        sample_name = f"ss-s-{run_id[:8]}"
        context = SubmissionContext(
            submission_name=submission_name,
            project_name="local-disposable-verification",
            timestamp=datetime.now(),
            datatype="mal",
            identifier=run_id,
            description="Rollback-only submission sequence verification",
            issue_identifier="LOCAL",
            author="Shape Shifter verification",
            data_provider_code="SEAD",
        )
        output_folder = tmp_path / strategy
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host=host,
                port=int(port),
                dbname=dbname,
                user=user,
                output_folder=str(output_folder),
                extra={
                    "tables": {
                        "site": pd.DataFrame({"system_id": [1], "site_id": [1]}),
                        "method": pd.DataFrame({"system_id": [81], "method_id": [81]}),
                        "sample_group": pd.DataFrame(
                            {
                                "system_id": [40],
                                "sample_group_id": [1],
                                "site_id": [1],
                                "method_id": [81],
                            }
                        ),
                        "sample_type": pd.DataFrame({"system_id": [50], "sample_type_id": [1]}),
                        "sample": pd.DataFrame(
                            {
                                "system_id": [20],
                                "physical_sample_id": [None],
                                "sample_group_id": [40],
                                "sample_type_id": [50],
                                "sample_name": [sample_name],
                            }
                        ),
                        "dataset": pd.DataFrame(
                            {
                                "system_id": [30],
                                "dataset_id": [None],
                                "dataset_name": [dataset_name],
                                "data_type_id": [5],
                                "method_id": [81],
                            }
                        ),
                        "analysis_entity": pd.DataFrame(
                            {
                                "system_id": [60],
                                "analysis_entity_id": [None],
                                "physical_sample_id": [20],
                                "dataset_id": [30],
                            }
                        ),
                    },
                    "target_model": _submission_target_model(),
                    "submission_context": {
                        "submission_name": context.submission_name,
                        "project_name": context.project_name,
                        "timestamp": context.timestamp.isoformat(),
                        "datatype": context.datatype,
                        "identifier": context.identifier,
                        "description": context.description,
                        "issue_identifier": context.issue_identifier,
                        "author": context.author,
                        "data_provider_code": context.data_provider_code,
                    },
                    "deploy_strategy": strategy,
                    "reconciliation_client": DisposableProviderResolver(),
                    "sims_client": DisposableManagedIdentityAllocator(),
                    "target_id_allocator": target_database,
                    "collision_checker": target_database,
                },
            )
        )

        result = await ingester.ingest("disposable-sequence-verification.xlsx")
        assert result.success is True, result.error_details
        assert result.deploy_artifact is not None
        artifact = result.deploy_artifact
        submission_id = DisposableManagedIdentityAllocator.target_ids["submission"]
        artifact_names.append(submission_name)

        artifact_directory = output_folder / resolve_bundle_name(context)
        rollback_script = tmp_path / f"{strategy}-{run_id}-rollback.sql"
        statements = "\n".join(artifact["statements"])
        rollback_script.write_text(
            "\n".join(
                [
                    "BEGIN;",
                    "INSERT INTO public.tbl_data_providers (data_provider_id, data_provider_code, data_provider_name)",
                    "VALUES (1, 'SEAD', 'Disposable verification provider');",
                    "SET CONSTRAINTS ALL DEFERRED;",
                    statements,
                    "DO $verify$",
                    "BEGIN",
                    f"    IF NOT EXISTS (SELECT 1 FROM public.tbl_submissions WHERE submission_id = {submission_id} "
                    f"AND submission_name = '{submission_name}' AND data_provider_id = 1) THEN",
                    "        RAISE EXCEPTION 'Submission row or provider link was not inserted';",
                    "    END IF;",
                    f"    IF NOT EXISTS (SELECT 1 FROM public.tbl_datasets WHERE dataset_id = 91925 "
                    f"AND dataset_name = '{dataset_name}' AND submission_id = {submission_id}) THEN",
                    "        RAISE EXCEPTION 'Dataset row does not point to the reserved submission ID';",
                    "    END IF;",
                    f"    IF NOT EXISTS (SELECT 1 FROM public.tbl_physical_samples WHERE physical_sample_id = 63876 "
                    f"AND sample_name = '{sample_name}' AND sample_group_id = 1 AND sample_type_id = 1) THEN",
                    "        RAISE EXCEPTION 'Sample row or required reference was not inserted';",
                    "    END IF;",
                    "    IF NOT EXISTS (SELECT 1 FROM public.tbl_analysis_entities WHERE analysis_entity_id = 223430 "
                    "AND physical_sample_id = 63876 AND dataset_id = 91925) THEN",
                    "        RAISE EXCEPTION 'Analysis entity does not point to the sample and dataset';",
                    "    END IF;",
                    "END",
                    "$verify$;",
                    "ROLLBACK;",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                psql_path,
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                "-h",
                host,
                "-p",
                port,
                "-U",
                user,
                "-d",
                dbname,
                "-f",
                str(rollback_script),
            ],
            cwd=artifact_directory / "deploy",
            env=psql_environment,
            capture_output=True,
            check=False,
            text=True,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr

        assert (
            await _fetch_count(
                connection_kwargs,
                "SELECT count(*) FROM public.tbl_submissions WHERE submission_id = %s",
                (submission_id,),
            )
            == 0
        )
        assert (
            await _fetch_count(
                connection_kwargs,
                "SELECT count(*) FROM public.tbl_datasets WHERE dataset_id = %s",
                (91925,),
            )
            == 0
        )
        assert (
            await _fetch_count(
                connection_kwargs,
                "SELECT count(*) FROM public.tbl_physical_samples WHERE physical_sample_id = %s",
                (63876,),
            )
            == 0
        )
        assert (
            await _fetch_count(
                connection_kwargs,
                "SELECT count(*) FROM public.tbl_analysis_entities WHERE analysis_entity_id = %s",
                (223430,),
            )
            == 0
        )
        assert (
            await _fetch_count(
                connection_kwargs,
                "SELECT count(*) FROM public.tbl_data_providers WHERE data_provider_id = %s",
                (1,),
            )
            == 0
        )

    assert len(artifact_names) == 2
    assert not target_database.reserved_ids
    assert await _sequence_state(connection_kwargs, "public.tbl_submissions", "submission_id") == initial_submission_sequence
    for sequence, expected_state in managed_sequence_states.items():
        assert await _sequence_state(connection_kwargs, *sequence) == expected_state
