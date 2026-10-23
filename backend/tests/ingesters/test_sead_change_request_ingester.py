"""Tests for the SEAD change request ingester scaffold behavior."""

import gzip
import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import httpx
import pandas as pd
import pytest

from backend.app.ingesters import IngesterConfig
from backend.app.ingesters.protocol import IngestionResult, ValidationResult
from backend.app.models.sims import CapabilitiesResponse, EntityCapabilityResponse
from backend.app.services.ingester_runtime import SeadChangeRequestSimsAdapter
from ingesters.sead_change_request import ChangeRowState, DeployArtifact, SourceTableBundle
from ingesters.sead_change_request.contracts import (
    CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE,
    FIXED_PROVIDER_TARGET_TABLE,
    SimsResolveItem,
    SubmissionContext,
    TrustedProjectContext,
    resolve_bundle_name,
)
from ingesters.sead_change_request.ingester import SeadChangeRequestIngester

# pylint: disable=unused-argument

TEST_SCOPE_NAME = "provider://mal/test-pilot"
"""Provider-schema scope used by ingester tests instead of a project-name fallback."""


class FakeReconciliationClient:
    """Simple fake reconciliation client for ingester tests."""

    def __init__(self, target_id: int | None) -> None:
        self.target_id = target_id

    async def reconcile_entity(self, entity_name: str, row: dict) -> int | None:
        return self.target_id


class FakeSimsClient:
    """Simple fake SIMS client for ingester tests."""

    def __init__(
        self,
        *,
        binding_set_uuid: str = "binding-123",
        binding_set_state: str = "confirmed",
        confirmed_binding_set_state: str | None = None,
        target_id: int | None = 501,
        target_ids: dict[str, int] | None = None,
    ) -> None:
        self.binding_set_uuid = binding_set_uuid
        self.binding_set_state = binding_set_state
        self.confirmed_binding_set_state = confirmed_binding_set_state or binding_set_state
        self.target_id = target_id
        self.target_ids = target_ids or {}
        self.approved_aggregate_ids: list[int] = []
        self.associated_change_requests: list[tuple[str, str]] = []
        self.scope_names: list[str | None] = []
        self.run_ids: list[str | None] = []

    async def resolve_batch(self, items: list[SimsResolveItem], submission_context) -> dict:
        self.scope_names.append(submission_context.scope_name)
        self.run_ids.append(submission_context.run_id)
        outcomes = []
        for item in items:
            if item.approved_aggregate_id is not None:
                self.approved_aggregate_ids.append(item.approved_aggregate_id)
                outcomes.append({"target_id": item.approved_aggregate_id, "tracked_identity_uuid": None})
            else:
                outcomes.append({"target_id": self.target_ids.get(item.entity_name, self.target_id), "tracked_identity_uuid": None})
        return {
            "outcomes": outcomes,
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
        }

    async def allocate_entity(self, entity_name: str, row: dict, submission_context) -> dict:
        return {
            "target_id": self.target_ids.get(entity_name, self.target_id),
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
            "note": f"Allocated {entity_name}",
        }

    async def bind_existing_entity(self, entity_name: str, row: dict, approved_aggregate_id: int, submission_context) -> dict:
        self.approved_aggregate_ids.append(approved_aggregate_id)
        return {
            "target_id": approved_aggregate_id,
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
            "note": f"Bound {entity_name} to approved aggregate ID {approved_aggregate_id}",
        }

    async def derive_bridge_row(self, entity_name: str, row: dict, submission_context) -> dict:
        return {
            "state": ChangeRowState.DERIVED_BRIDGE_ROW.value,
            "target_id": None,
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
            "note": f"Derived {entity_name}",
        }

    async def get_binding_set_state(self, binding_set_uuid: str) -> str:
        return self.binding_set_state

    async def confirm_binding_set(self, binding_set_uuid: str) -> str:
        self.binding_set_state = self.confirmed_binding_set_state
        return self.binding_set_state

    async def associate_change_request(self, binding_set_uuid: str, change_request_name: str) -> None:
        self.associated_change_requests.append((binding_set_uuid, change_request_name))


class CountingSimsClient(FakeSimsClient):
    """Fake SIMS client that counts resolve batches so tests can prove zero calls."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.batch_calls = 0

    async def resolve_batch(self, items, submission_context):
        self.batch_calls += 1
        return await super().resolve_batch(items, submission_context)


class FakeBackendSimsClient:
    """Minimal fake backend SIMS client for adapter-backed ingester tests."""

    def __init__(
        self,
        binding_set_uuid: str = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        lifecycle_state: str = "confirmed",
        *,
        target_id: int | None = None,
        resolve_error: httpx.HTTPStatusError | None = None,
    ) -> None:
        self.binding_set_uuid = binding_set_uuid
        self.lifecycle_state = lifecycle_state
        self.target_id = target_id
        self.resolve_error = resolve_error
        self.associated_change_requests: list[tuple[str, str]] = []

    async def resolve(self, request: object):
        if self.resolve_error is not None:
            raise self.resolve_error
        outcomes = []
        for resolution_request in request.requests:
            requested_aggregate_id = resolution_request.approved_aggregate_id
            target_id = requested_aggregate_id if requested_aggregate_id is not None else self.target_id
            outcomes.append(
                type(
                    "Outcome",
                    (),
                    {"tracked_identity_uuid": None, "target_id": target_id},
                )()
            )
        return cast(
            Any,
            type(
                "ResolveResponse",
                (),
                {
                    "binding_set": type(
                        "BindingSetResponse",
                        (),
                        {
                            "binding_set_uuid": self.binding_set_uuid,
                            "lifecycle_state": type("LifecycleState", (), {"value": self.lifecycle_state})(),
                        },
                    )(),
                    "outcomes": outcomes,
                },
            )(),
        )

    async def get_capabilities(self) -> CapabilitiesResponse:
        """Return a permissive capability set for the entities used by adapter tests."""
        entity_types = (
            "sample",
            "sample_group",
            "taxon",
            "sample_taxon",
            "submission",
            "submission_state",
            "data_provider",
            "citation",
            "dataset",
            "site",
            "method",
        )
        return CapabilitiesResponse(
            version="1.0",
            entities=[
                EntityCapabilityResponse(
                    entity_type=entity_type,
                    entity_subtype="shared_metadata",
                    bind_existing=True,
                    allocate_new=True,
                    auto_confirm=True,
                    accept_uuid=False,
                )
                for entity_type in entity_types
            ],
        )

    async def get_binding_set(self, binding_set_uuid):
        return cast(
            Any,
            type("BindingSetResponse", (), {"lifecycle_state": type("LifecycleState", (), {"value": self.lifecycle_state})()})(),
        )

    async def confirm_binding_set(self, binding_set_uuid):
        self.lifecycle_state = "confirmed"
        return cast(
            Any,
            type("BindingSetResponse", (), {"lifecycle_state": type("LifecycleState", (), {"value": self.lifecycle_state})()})(),
        )

    async def associate_change_request(self, binding_set_uuid, change_request_name: str):
        self.associated_change_requests.append((str(binding_set_uuid), change_request_name))
        return cast(
            Any,
            type("BindingSetResponse", (), {"lifecycle_state": type("LifecycleState", (), {"value": self.lifecycle_state})()})(),
        )


class FakeCollisionChecker:
    """Simple fake target collision checker for ingester tests."""

    def __init__(
        self,
        *,
        target_ids: set[tuple[str, str, int]] | None = None,
        rows: set[tuple[str, tuple[tuple[str, object], ...]]] | None = None,
        column_types: dict[tuple[str, str], str | None] | None = None,
        type_error: Exception | None = None,
        exists_error: Exception | None = None,
    ) -> None:
        self.target_ids = target_ids or set()
        self.rows = rows or set()
        self.column_types = column_types or {}
        self.type_error = type_error
        self.exists_error = exists_error
        self.checked_ids: list[tuple[str, str, int]] = []
        self.checked_types: list[tuple[str, str]] = []

    async def target_id_exists(self, table_name: str, public_id_column: str, target_id: int) -> bool:
        self.checked_ids.append((table_name, public_id_column, target_id))
        if self.exists_error is not None:
            raise self.exists_error
        return (table_name, public_id_column, target_id) in self.target_ids

    async def target_id_column_type(self, table_name: str, public_id_column: str) -> str | None:
        self.checked_types.append((table_name, public_id_column))
        if self.type_error is not None:
            raise self.type_error
        return self.column_types.get((table_name, public_id_column), "integer")

    async def row_exists(self, table_name: str, filters: dict[str, object]) -> bool:
        return (table_name, tuple(sorted(filters.items()))) in self.rows


class StubBundleFileDeployStrategy:
    """Test strategy that emits an extra sidecar file in the artifact bundle."""

    def build_artifact(self, change_package, target_model, submission_context):
        return DeployArtifact(
            deploy_sql="SELECT 1;",
            statements=["SELECT 1;"],
            metadata={"deploy_strategy": "stub_bundle_file"},
            revert_sql="ROLLBACK;",
            verify_sql="ROLLBACK;",
            metadata_artifact={"artifact_type": "stub", "deploy_strategy": "stub_bundle_file"},
            bundle_files={"deploy/test-submission/sample.csv": "sample_id\n501\n"},
        )


def minimal_target_model(**extra_entities: dict) -> dict:
    """Build a minimal target model payload for ingester tests."""
    return {
        "model": {"name": "SEAD Test Model", "version": "0.1.0"},
        "entities": extra_entities,
        "constraints": [],
    }


_NO_COLLISION_CHECKER = object()


def direct_fk_target_model(*, foreign_key: dict | None = None, nullable: bool | None = False) -> dict:
    """Build a target model with a location FK whose source may contain a target ID."""
    location: dict[str, Any] = {
        "role": "fact",
        "public_id": "location_id",
        "target_table": "tbl_locations",
        "foreign_keys": [foreign_key or {"entity": "location_type", "required": True}],
    }
    if nullable is not None:
        location["columns"] = {"location_type_id": {"nullable": nullable}}
    return minimal_target_model(
        location_type={"role": "lookup", "public_id": "location_type_id", "target_table": "tbl_location_types"},
        location=location,
    )


def make_direct_fk_ingester(
    tables: dict[str, pd.DataFrame],
    *,
    collision_checker: object = _NO_COLLISION_CHECKER,
    foreign_key: dict | None = None,
    nullable: bool | None = False,
    extra: dict[str, Any] | None = None,
    output_folder: str | None = None,
) -> SeadChangeRequestIngester:
    """Build an ingester with an explicit standalone direct-FK declaration."""
    config_extra: dict[str, Any] = {
        "tables": tables,
        "target_model": direct_fk_target_model(foreign_key=foreign_key, nullable=nullable),
        "foreign_key_value_sources": {"location": {"location_type": "public_id"}},
        "submission_context": minimal_submission_context(),
    }
    if collision_checker is not _NO_COLLISION_CHECKER:
        config_extra["collision_checker"] = collision_checker
    config_extra.update(extra or {})
    config_values: dict[str, Any] = {
        "host": "localhost",
        "port": 5432,
        "dbname": "test_db",
        "user": "test_user",
        "extra": config_extra,
    }
    if output_folder is not None:
        config_values["output_folder"] = output_folder
    return SeadChangeRequestIngester(IngesterConfig(**config_values))


def submission_target_model() -> dict:
    """Build the submission-aware target contract used by ingester tests."""
    return minimal_target_model(
        submission_state={"role": "classifier", "public_id": "submission_state_id", "target_table": "tbl_submission_states"},
        data_provider={"role": "lookup", "public_id": "data_provider_id", "target_table": "tbl_data_providers"},
        citation={"role": "lookup", "public_id": "biblio_id", "target_table": "tbl_biblio"},
        submission={
            "role": "fact",
            "identity_tracking": "tracked",
            "reconciliation": "allocate",
            "public_id": "submission_id",
            "target_table": "tbl_submissions",
            "synchronize_sequence_after_insert": True,
            "foreign_keys": [{"entity": "submission_state"}, {"entity": "data_provider"}, {"entity": "citation"}],
        },
        dataset={
            "role": "lookup",
            "identity_tracking": "tracked",
            "reconciliation": "allocate",
            "public_id": "dataset_id",
            "target_table": "tbl_datasets",
            "synchronize_sequence_after_insert": True,
            "columns": {
                "data_type_id": {"required": True, "type": "integer", "nullable": False},
            },
            "foreign_keys": [{"entity": "submission"}],
        },
    )


def conditional_location_target_model() -> dict:
    """Build a target contract with a conditional location -> location_type foreign key."""
    return minimal_target_model(
        location_type={"role": "lookup", "public_id": "location_type_id"},
        location={
            "role": "fact",
            "public_id": "location_id",
            "columns": {"location_type_id": {"type": "integer", "nullable": False}},
            "foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "location"}}],
        },
    )


def minimal_submission_context(**overrides: object) -> dict:
    """Build a minimal submission context payload for ingester tests."""
    payload: dict[str, object] = {
        "submission_name": "test-submission",
        "project_name": "test-project",
        "timestamp": "2026-05-23T22:00:00",
        "datatype": "mal",
        "identifier": "TEST_SUBMISSION",
        "description": "test bundle",
        "issue_identifier": "NNN",
        "author": "SEAD Expert",
        "data_provider_code": "SEAD",
        "scope_name": TEST_SCOPE_NAME,
    }
    payload.update(overrides)
    return payload


def minimal_trusted_project_context(
    *,
    project_name: str = "test-project",
    provider_code: str = "SEAD",
    data_provider_id: int = 51,
    business_keys: dict[str, tuple[str, ...]] | None = None,
) -> TrustedProjectContext:
    """Build the backend-owned project facts used by Change Request ingester tests."""
    return TrustedProjectContext(
        project_name=project_name,
        provider_code=provider_code,
        provider_schema="test-pilot",
        scope_name=TEST_SCOPE_NAME,
        data_provider_id=data_provider_id,
        business_keys=business_keys if business_keys is not None else {},
    )


def verified_provider_row(provider_code: str = "SEAD", data_provider_id: int = 51) -> FakeCollisionChecker:
    """Build a collision checker that confirms one SEAD provider row."""
    return FakeCollisionChecker(
        rows={
            (
                FIXED_PROVIDER_TARGET_TABLE,
                (("data_provider_code", provider_code), ("data_provider_id", data_provider_id)),
            )
        }
    )


def expected_bundle_name(**overrides: object) -> str:
    """Build the expected CR bundle name for tests."""
    payload = minimal_submission_context(**overrides)
    submission_context = SubmissionContext(
        submission_name=str(payload["submission_name"]),
        project_name=str(payload["project_name"]),
        timestamp=datetime.fromisoformat(str(payload["timestamp"])),
        change_request_name=payload.get("change_request_name") if isinstance(payload.get("change_request_name"), str) else None,
        datatype=str(payload["datatype"]),
        identifier=str(payload["identifier"]),
        description=payload.get("description") if isinstance(payload.get("description"), str) else None,
        issue_identifier=payload.get("issue_identifier") if isinstance(payload.get("issue_identifier"), str) else None,
        author=payload.get("author") if isinstance(payload.get("author"), str) else None,
    )
    return resolve_bundle_name(submission_context)


def configured_tables(ingester: SeadChangeRequestIngester) -> dict[str, pd.DataFrame]:
    """Return the in-memory tables declared by the test ingester configuration."""
    tables = (ingester.config.extra or {}).get("tables")
    assert isinstance(tables, dict), "test ingester config must declare config.extra['tables']"
    return tables


async def validate_bundle(ingester: SeadChangeRequestIngester) -> ValidationResult:
    """Validate the ingester's configured tables through the public table method."""
    return await ingester.validate_tables(configured_tables(ingester))


async def ingest_bundle(ingester: SeadChangeRequestIngester, validate_first: bool = True) -> IngestionResult:
    """Ingest the ingester's configured tables through the public table method."""
    return await ingester.ingest_tables(configured_tables(ingester), validate_first=validate_first)


def emitted_bundle_dir(root: Path, bundle_name: str) -> Path:
    """Locate the bundle directory emitted under the exclusive run folder."""
    run_folders = [path for path in Path(root).iterdir() if path.is_dir() and (path / bundle_name).is_dir()]
    assert len(run_folders) == 1, f"expected one run folder containing bundle {bundle_name}, found {len(run_folders)}"
    return run_folders[0] / bundle_name


class TestSeadChangeRequestIngesterValidation:
    """Tests for DataFrame-first validation handoff."""

    @pytest.mark.asyncio
    async def test_validate_accepts_tables_from_config_extra(self):
        """Validation should accept the MVP Delivery in-memory table bundle from config.extra."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1, 2]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is True
        assert result.errors == []
        assert any("1 table" in info for info in result.infos)
        assert any("2 row" in info for info in result.infos)
        assert any("Validated submission context for 'test-submission' in project 'test-project'" in info for info in result.infos)
        assert any("Planned 'sample': 2 reference_existing" in info for info in result.infos)

    @pytest.mark.asyncio
    async def test_validate_accepts_source_bundle_argument(self):
        """Validation should accept an already-built source bundle directly."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )
        bundle = SourceTableBundle(
            tables={"sample": pd.DataFrame({"sample_id": [1]})},
            source_name="normalized submission",
            warnings=["sample warning"],
        )

        result = await ingester._validate_bundle(bundle)

        assert result.is_valid is True
        assert result.warnings == ["sample warning"]
        assert any("normalized submission" in info for info in result.infos)

    @pytest.mark.asyncio
    async def test_validate_tables_reports_the_source_name_as_diagnostics(self):
        """The public table method should keep the source name separate from the file contract."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate_tables(
            {"sample": pd.DataFrame({"sample_id": [1]})},
            source_name="normalized submission",
        )

        assert result.is_valid is True
        assert any("Source bundle name: normalized submission" in info for info in result.infos)

    @pytest.mark.asyncio
    async def test_validate_tables_reports_invalid_table_values_as_a_structured_failure(self):
        """A non-DataFrame value should become a validation failure, not an exception."""
        ingester = SeadChangeRequestIngester(IngesterConfig(host="localhost", port=5432, dbname="test_db", user="test_user"))

        result = await ingester.validate_tables({"sample": [{"sample_id": 1}]})  # type: ignore[dict-item]

        assert result.is_valid is False
        assert result.errors == ["Source table 'sample' must be a pandas DataFrame"]
        assert result.warnings == []

    @pytest.mark.asyncio
    async def test_ingest_tables_reports_invalid_table_values_with_and_without_validation(self):
        """The public table method should follow validate_first for adapter failures."""
        ingester = SeadChangeRequestIngester(IngesterConfig(host="localhost", port=5432, dbname="test_db", user="test_user"))

        validated_result = await ingester.ingest_tables({"sample": [{"sample_id": 1}]})  # type: ignore[dict-item]
        bypassed_result = await ingester.ingest_tables({"sample": [{"sample_id": 1}]}, validate_first=False)  # type: ignore[dict-item]

        assert validated_result.success is False
        assert validated_result.message == "Validation failed"
        assert validated_result.error_details == "Source table 'sample' must be a pandas DataFrame"
        assert bypassed_result.success is False
        assert bypassed_result.message == "Invalid source bundle"
        assert bypassed_result.error_details == "Source table 'sample' must be a pandas DataFrame"

    @pytest.mark.asyncio
    async def test_validate_requires_authorized_project_context_for_submission_target(self):
        """Submission-aware targets should require the authorized saved project facts."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"dataset": pd.DataFrame({"dataset_id": [None]})},
                    "target_model": submission_target_model(),
                    "submission_context": minimal_submission_context(data_provider_code=None),
                    "reconciliation_client": FakeReconciliationClient(target_id=51),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["Change Request ingestion requires an authorized saved project with a fixed data provider row"]

    @pytest.mark.asyncio
    async def test_validate_rejects_provider_row_missing_from_sead(self):
        """Submission-aware targets should not accept a provider row that SEAD does not have."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"dataset": pd.DataFrame({"dataset_id": [None]})},
                    "target_model": submission_target_model(),
                    "submission_context": minimal_submission_context(data_provider_code="UNKNOWN"),
                    "trusted_project_context": minimal_trusted_project_context(provider_code="UNKNOWN", data_provider_id=999),
                    "collision_checker": verified_provider_row(),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["No SEAD data provider row matches data_provider_id 999 and data_provider_code 'UNKNOWN'"]

    @pytest.mark.asyncio
    async def test_validate_rejects_retired_workbook_path_without_reading_it(self, tmp_path):
        """Validation should reject a workbook path before any workbook is read."""
        workbook_path = tmp_path / "submission.xlsx"
        workbook_path.write_bytes(b"not a workbook")

        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                submission_name="test-submission",
                output_folder=str(tmp_path),
                extra={
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate(workbook_path)

        assert result.is_valid is False
        assert result.errors == [CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE]

    @pytest.mark.asyncio
    async def test_validate_rejects_string_source_before_resolution(self):
        """Validation should reject a string source even when config.extra holds tables."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate("submission.csv")

        assert result.is_valid is False
        assert result.errors == [CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE]

    @pytest.mark.asyncio
    async def test_validate_rejects_string_source_before_inspecting_tables(self):
        """A string source must not select malformed tables from config.extra."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": [{"sample_id": 1}]},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingester.validate("submission.xlsx")

        assert result.is_valid is False
        assert result.errors == [CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE]

    @pytest.mark.asyncio
    async def test_validate_fails_when_target_model_missing(self):
        """Validation should require target-model metadata before planning rows."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={"tables": {"sample": pd.DataFrame({"sample_id": [1]})}},
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["Target model is required; provide config.extra['target_model'] as a dict or TargetModel"]

    @pytest.mark.asyncio
    async def test_validate_fails_when_submission_context_missing(self):
        """Validation should require explicit submission context metadata."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["Submission context is required; provide config.extra['submission_context']"]

    @pytest.mark.asyncio
    async def test_validate_fails_when_submission_context_timestamp_invalid(self):
        """Validation should reject invalid submission timestamps at the boundary."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(timestamp="not-a-timestamp"),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["Submission context timestamp must be a valid ISO-8601 datetime string"]

    @pytest.mark.asyncio
    async def test_validate_fails_when_submission_context_description_multiline(self):
        """Validation should reject multiline SQL-header descriptions at the boundary."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(description="line one\nline two"),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["Submission context description must be a single line"]

    @pytest.mark.asyncio
    async def test_validate_fails_when_submission_context_description_too_long(self):
        """Validation should reject overlong SQL-header descriptions at the boundary."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(description="x" * 80),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["Submission context description must be shorter than 80 characters"]

    @pytest.mark.asyncio
    async def test_validate_fails_when_identity_assignments_malformed(self):
        """Validation should reject malformed identity-assignment payloads at the boundary."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {"sample": {0: {"state": "not-a-state"}}},
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["Identity assignment for 'sample' row '0' has invalid state 'not-a-state'"]

    @pytest.mark.asyncio
    async def test_validate_fails_for_unknown_target_model_table(self):
        """Validation should fail when the bundle includes a table not declared in the target model."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(site={"role": "fact", "public_id": "site_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["Source table 'sample' is not present in the target model"]

    @pytest.mark.asyncio
    async def test_validate_surfaces_bridge_planning_diagnostics_as_warnings(self):
        """Validation should surface early bridge-planning blockers as warnings for now."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample_taxon": pd.DataFrame({"sample_id": [1], "taxon_id": [2]})},
                    "target_model": minimal_target_model(sample_taxon={"role": "bridge"}),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "sample_taxon": {
                            0: {
                                "state": ChangeRowState.DERIVED_BRIDGE_ROW,
                                "target_id": 5001,
                            }
                        }
                    },
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is True
        assert result.warnings == [
            "Bridge entity 'sample_taxon' has no unique_sets metadata; MVP Delivery uniqueness checks will be blocked"
        ]
        assert any("1 evaluate_bridge" in info for info in result.infos)

    @pytest.mark.asyncio
    async def test_validate_reports_blocked_rows_after_identity_resolution(self):
        """Validation should fail when planned work lacks required identity assignments."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert any("Blocked rows after identity resolution: 1" in info for info in result.infos)
        assert any("Outcome classification:" in info for info in result.infos)
        assert any("pending_review" in info for info in result.infos)
        assert result.errors == [
            "Entity 'sample' has 1 row(s) without a resolved target ID for 'sample_id'",
            "Entity 'sample' row '0' is missing an identity assignment for planned action 'allocate'",
        ]

    @pytest.mark.asyncio
    async def test_validate_accepts_identity_assignments(self):
        """Validation should summarize zero blocked rows when identity assignments are provided."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                                "note": "Allocated by test harness",
                            }
                        }
                    },
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is True
        assert any("Blocked rows after identity resolution: 0" in info for info in result.infos)
        assert any("Outcome classification:" in info for info in result.infos)
        assert any("allowed_update" in info for info in result.infos)
        assert result.warnings == ["Entity 'sample' row '0': Allocated by test harness"]

    @pytest.mark.asyncio
    async def test_validate_accepts_matched_only_rows_for_conditional_foreign_key(self):
        """A submission whose location rows all match existing records must not trigger the condition."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"location": pd.DataFrame({"location_id": [501], "location_type_id": [None], "location_name": ["existing"]})},
                    "target_model": conditional_location_target_model(),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is True
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_validate_rejects_inserted_row_without_conditional_foreign_key_value(self):
        """An inserted location row must fail validation when its conditional FK has no value."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"location": pd.DataFrame({"location_id": [None], "location_type_id": [None]})},
                    "target_model": conditional_location_target_model(),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "location": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 601,
                            }
                        }
                    },
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == ["Entity 'location' has 1 missing conditional FK value(s) for 'location_type_id'"]

    @pytest.mark.asyncio
    async def test_validate_accepts_an_existing_direct_target_id_without_a_parent_table(self):
        checker = FakeCollisionChecker(target_ids={("tbl_location_types", "location_type_id", 42)})
        frame = pd.DataFrame({"location_id": [None], "location_type_id": ["00042"]})
        ingester = make_direct_fk_ingester(
            {"location": frame},
            collision_checker=checker,
            extra={"identity_assignments": {"location": {0: {"state": ChangeRowState.NEWLY_ALLOCATED_ENTITY, "target_id": 601}}}},
        )

        result = await ingester.validate_tables({"location": frame})
        preparation = await ingester._prepare_change_request(SourceTableBundle(tables={"location": frame}))

        assert result.is_valid is True
        assert result.errors == []
        assert checker.checked_types == [("tbl_location_types", "location_type_id")] * 2
        assert checker.checked_ids == [("tbl_location_types", "location_type_id", 42)] * 2
        assert preparation.change_package is not None
        assert preparation.change_package.tables["location"].frame.at[0, "location_type_id"] == 42
        assert isinstance(preparation.change_package.tables["location"].frame.at[0, "location_type_id"], int)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", ["not-an-id", 4.25, True])
    async def test_validate_rejects_malformed_direct_target_ids(self, value):
        checker = FakeCollisionChecker()
        ingester = make_direct_fk_ingester(
            {"location": pd.DataFrame({"location_id": [None], "location_type_id": [value]})},
            collision_checker=checker,
            extra={"identity_assignments": {"location": {0: {"state": ChangeRowState.NEWLY_ALLOCATED_ENTITY, "target_id": 601}}}},
        )

        result = await ingester.validate_tables({"location": pd.DataFrame({"location_id": [None], "location_type_id": [value]})})

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Entity 'location'" in result.errors[0]
        assert "column 'location_type_id'" in result.errors[0]
        assert repr(value) in result.errors[0]
        assert not checker.checked_types
        assert not checker.checked_ids

    @pytest.mark.asyncio
    async def test_validate_rejects_missing_or_unverifiable_direct_target_ids(self):
        tables = {"location": pd.DataFrame({"location_id": [None], "location_type_id": [42]})}
        identity = {"identity_assignments": {"location": {0: {"state": ChangeRowState.NEWLY_ALLOCATED_ENTITY, "target_id": 601}}}}

        absent_ingester = make_direct_fk_ingester(tables, collision_checker=FakeCollisionChecker(), extra=identity)
        absent_result = await absent_ingester.validate_tables(tables)
        assert absent_result.is_valid is False
        assert "value 42" in absent_result.errors[0]
        assert "absent" in absent_result.errors[0]

        unavailable_ingester = make_direct_fk_ingester(tables, extra=identity)
        unavailable_result = await unavailable_ingester.validate_tables(tables)
        assert unavailable_result.is_valid is False
        assert "value 42" in unavailable_result.errors[0]
        assert "unavailable" in unavailable_result.errors[0]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("checker", "expected"),
        [
            (FakeCollisionChecker(column_types={("tbl_location_types", "location_type_id"): "text"}), "non-integer type 'text'"),
            (FakeCollisionChecker(type_error=RuntimeError("catalog failure")), "catalog failure"),
            (FakeCollisionChecker(exists_error=RuntimeError("lookup failure")), "lookup failure"),
        ],
    )
    async def test_validate_fails_closed_for_non_integer_columns_and_database_errors(self, checker, expected):
        tables = {"location": pd.DataFrame({"location_id": [None], "location_type_id": [42]})}
        ingester = make_direct_fk_ingester(
            tables,
            collision_checker=checker,
            extra={"identity_assignments": {"location": {0: {"state": ChangeRowState.NEWLY_ALLOCATED_ENTITY, "target_id": 601}}}},
        )

        result = await ingester.validate_tables(tables)

        assert result.is_valid is False
        assert "Entity 'location'" in result.errors[0]
        assert "column 'location_type_id'" in result.errors[0]
        assert "value 42" in result.errors[0]
        assert expected in result.errors[0]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("foreign_key", "nullable"),
        [
            ({"entity": "location_type", "required": True}, True),
            ({"entity": "location_type", "required_when": {"has_new_rows": "location"}}, True),
            ({"entity": "location_type"}, False),
        ],
    )
    async def test_validate_requires_missing_direct_values_on_selected_inserts(self, foreign_key, nullable):
        tables = {"location": pd.DataFrame({"location_id": [None], "location_type_id": [None]})}
        checker = FakeCollisionChecker()
        ingester = make_direct_fk_ingester(
            tables,
            collision_checker=checker,
            foreign_key=foreign_key,
            nullable=nullable,
            extra={"identity_assignments": {"location": {0: {"state": ChangeRowState.NEWLY_ALLOCATED_ENTITY, "target_id": 601}}}},
        )

        result = await ingester.validate_tables(tables)

        assert result.is_valid is False
        assert "Entity 'location'" in result.errors[0]
        assert "column 'location_type_id'" in result.errors[0]
        assert not checker.checked_types
        assert not checker.checked_ids

    @pytest.mark.asyncio
    async def test_validate_skips_lookup_for_zero_insert_and_excluded_rows(self):
        zero_insert_checker = FakeCollisionChecker()
        zero_insert_tables = {"location": pd.DataFrame({"location_id": [701], "location_type_id": ["bad"]})}
        zero_insert_ingester = make_direct_fk_ingester(zero_insert_tables, collision_checker=zero_insert_checker)

        zero_insert_result = await zero_insert_ingester.validate_tables(zero_insert_tables)

        assert zero_insert_result.is_valid is True
        assert not zero_insert_checker.checked_types
        assert not zero_insert_checker.checked_ids

        checker = FakeCollisionChecker(target_ids={("tbl_location_types", "location_type_id", 42)})
        tables = {
            "location": pd.DataFrame(
                {"location_id": [701, None], "location_type_id": ["bad", 42]},
                index=[0, 1],
            )
        }
        ingester = make_direct_fk_ingester(
            tables,
            collision_checker=checker,
            extra={"identity_assignments": {"location": {1: {"state": ChangeRowState.NEWLY_ALLOCATED_ENTITY, "target_id": 601}}}},
        )

        result = await ingester.validate_tables(tables)

        assert result.is_valid is True
        assert checker.checked_ids == [("tbl_location_types", "location_type_id", 42)]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", [None, "not-an-id"])
    async def test_validate_checks_only_assigned_direct_fk_update_columns(self, value):
        tables = {
            "location": pd.DataFrame(
                {
                    "location_id": [701],
                    "location_type_id": [value],
                    "location_name": ["new name"],
                    "location_name__existing": ["old name"],
                }
            )
        }
        checker = FakeCollisionChecker()
        ingester = make_direct_fk_ingester(
            tables,
            collision_checker=checker,
            extra={"mutable_fields_by_entity": {"location": ["location_name"]}},
        )

        result = await ingester.validate_tables(tables)

        assert result.is_valid is True
        assert not checker.checked_types
        assert not checker.checked_ids

    @pytest.mark.asyncio
    async def test_validate_checks_a_direct_fk_when_an_update_assigns_it(self):
        tables = {
            "location": pd.DataFrame(
                {
                    "location_id": [701],
                    "location_type_id": [42],
                    "location_type_id__existing": [41],
                }
            )
        }
        checker = FakeCollisionChecker(target_ids={("tbl_location_types", "location_type_id", 42)})
        ingester = make_direct_fk_ingester(
            tables,
            collision_checker=checker,
            foreign_key={"entity": "location_type"},
            nullable=False,
            extra={"mutable_fields_by_entity": {"location": ["location_type_id"]}},
        )

        result = await ingester.validate_tables(tables)

        assert result.is_valid is True
        assert checker.checked_types == [("tbl_location_types", "location_type_id")]
        assert checker.checked_ids == [("tbl_location_types", "location_type_id", 42)]

    @pytest.mark.asyncio
    async def test_validate_rejects_null_non_nullable_direct_fk_on_assigned_update(self):
        tables = {
            "location": pd.DataFrame(
                {
                    "location_id": [701],
                    "location_type_id": [None],
                    "location_type_id__existing": [42],
                }
            )
        }
        ingester = make_direct_fk_ingester(
            tables,
            collision_checker=FakeCollisionChecker(),
            foreign_key={"entity": "location_type"},
            nullable=False,
            extra={"mutable_fields_by_entity": {"location": ["location_type_id"]}},
        )

        result = await ingester.validate_tables(tables)

        assert result.is_valid is False
        assert "Entity 'location'" in result.errors[0]
        assert "column 'location_type_id'" in result.errors[0]
        assert "missing direct FK value" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_accepts_client_orchestrated_assignments(self):
        """Validation should accept assignments produced by the thin client orchestration layer."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "sims_client": FakeSimsClient(
                        binding_set_state="confirmed",
                        target_id=501,
                        target_ids={"submission": 1, "dataset": 91924},
                    ),
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is True
        assert result.pending_confirmation_report is None
        assert any("Binding Set UUID: binding-123" in info for info in result.infos)
        assert result.warnings == ["Entity 'sample' row '0': Allocated sample"]

    @pytest.mark.asyncio
    async def test_validate_returns_pending_confirmation_report_for_proposed_binding_set(self):
        """Validation should surface a pending confirmation report when SIMS returns a proposed Binding Set."""
        sims_client = FakeSimsClient(binding_set_state="proposed", target_id=501)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "sims_client": sims_client,
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.pending_confirmation_report is not None
        assert result.pending_confirmation_report["binding_set_uuid"] == "binding-123"
        assert result.pending_confirmation_report["binding_set_state"] == "proposed"
        assert sims_client.run_ids[0] is not None
        assert sims_client.run_ids[0] in result.pending_confirmation_report["rerun_instruction"]

    @pytest.mark.asyncio
    async def test_validate_reports_outcome_counts_for_existing_rows_with_mutable_field_scope(self):
        """Validation infos should include no-op and allowed-update counts based on configured mutable fields."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "sample_id": [101, 102],
                                "sample_name": ["A", "B updated"],
                                "sample_name__existing": ["A", "B"],
                                "sample_note": ["new note", "new note"],
                                "sample_note__existing": ["old note", "old note"],
                            }
                        )
                    },
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "mutable_fields_by_entity": {"sample": ["sample_name"]},
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is True
        assert any(
            "Outcome classification: 0 new_data, 1 no_op, 1 allowed_update, 0 pending_review, 0 blocked" in info for info in result.infos
        )

    @pytest.mark.asyncio
    async def test_validate_routes_existing_rows_to_issue3a_planning_actions(self):
        """Validation should route existing-row updates into candidate and blocked Issue 3A planning actions."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "sample_id": [101, 102],
                                "sample_name": ["A changed", "B changed"],
                                "sample_name__existing": ["A", "B"],
                            }
                        ),
                        "sample_location": pd.DataFrame(
                            {
                                "sample_location_id": [201],
                                "site_note": ["new"],
                            }
                        ),
                    },
                    "target_model": minimal_target_model(
                        sample={"role": "fact", "public_id": "sample_id"},
                        sample_location={"role": "fact", "public_id": "sample_location_id"},
                    ),
                    "submission_context": minimal_submission_context(),
                    "mutable_fields_by_entity": {
                        "sample": ["sample_name"],
                        "sample_location": ["site_note"],
                    },
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert any("Planned 'sample': 2 update_existing_candidate" in info for info in result.infos)
        assert any("Planned 'sample_location': 1 block_existing_update" in info for info in result.infos)
        assert any(
            "Identity work queues:" in info and "2 update_candidate" in info and "1 blocked_existing_update" in info
            for info in result.infos
        )
        assert any("blocked existing-row update planning" in warning for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_validate_blocks_existing_row_updates_outside_first_slice_scope(self):
        """Validation should keep existing-row updates blocked for entities outside the first-slice allowlist."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "sample_id": [101],
                                "sample_name": ["A changed"],
                                "sample_name__existing": ["A"],
                            }
                        )
                    },
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "mutable_fields_by_entity": {"sample": ["sample_name"]},
                    "existing_row_update_entities": ["other_entity"],
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert any("outside the first existing-row update slice" in warning for warning in result.warnings)
        assert any("1 blocked_existing_update" in info for info in result.infos)


class TestSeadChangeRequestIngesterIngest:
    """Tests for scaffold ingest behavior."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("deploy_strategy", ["inline_insert", "copy_csv", "inline_staging"])
    async def test_ingest_preserves_direct_ids_and_writes_manifest_metadata(self, tmp_path, deploy_strategy):
        tables = {"location": pd.DataFrame({"location_id": [None], "location_type_id": ["42"]})}
        checker = FakeCollisionChecker(target_ids={("tbl_location_types", "location_type_id", 42)})
        extra: dict[str, Any] = {
            "deploy_strategy": deploy_strategy,
            "identity_assignments": {"location": {0: {"state": ChangeRowState.NEWLY_ALLOCATED_ENTITY, "target_id": 601}}},
        }
        if deploy_strategy == "inline_staging":
            extra["staging_target_schema"] = "public"
        ingester = make_direct_fk_ingester(
            tables,
            collision_checker=checker,
            extra=extra,
            output_folder=str(tmp_path / deploy_strategy),
        )

        result = await ingester.ingest_tables(tables)

        assert result.success is True
        assert result.deploy_artifact is not None
        expected_metadata = [{"source_entity": "location", "target_entity": "location_type", "column": "location_type_id"}]
        assert result.deploy_artifact["metadata_artifact"]["direct_target_id_foreign_keys"] == expected_metadata
        if deploy_strategy == "copy_csv":
            assert any("42" in content for content in result.deploy_artifact["bundle_files"].values())
        else:
            assert "42" in result.deploy_artifact["deploy_sql"]

        bundle_root = emitted_bundle_dir(tmp_path / deploy_strategy, expected_bundle_name())
        manifest = json.loads((bundle_root / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["direct_target_id_foreign_keys"] == expected_metadata
        if deploy_strategy == "inline_staging":
            assert result.deploy_artifact["metadata_artifact"]["known_id_mapping_count"] == 0
            assert '"_local_location_type_id"' not in result.deploy_artifact["deploy_sql"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("validate_first", "expected_message"),
        [(True, "Validation failed"), (False, "Direct foreign-key validation failed")],
    )
    async def test_ingest_fails_without_a_direct_id_checker_and_removes_reserved_run(self, tmp_path, validate_first, expected_message):
        tables = {"location": pd.DataFrame({"location_id": [None], "location_type_id": [42]})}
        ingester = make_direct_fk_ingester(
            tables,
            extra={"identity_assignments": {"location": {0: {"state": ChangeRowState.NEWLY_ALLOCATED_ENTITY, "target_id": 601}}}},
            output_folder=str(tmp_path),
        )

        result = await ingester.ingest_tables(tables, validate_first=validate_first)

        assert result.success is False
        assert result.message == expected_message
        assert "Entity 'location'" in result.error_details
        assert "column 'location_type_id'" in result.error_details
        assert "value 42" in result.error_details
        assert not list(tmp_path.iterdir())

    @pytest.mark.asyncio
    async def test_ingest_emits_empty_artifact_bundle_for_valid_reference_only_bundle(self, tmp_path):
        """Ingest should emit an artifact bundle even when no rows enter the MVP Delivery insert package."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1, 2]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingest_bundle(ingester)

        assert result.success is True
        assert "Deploy artifact emitted to" in result.message
        assert result.tables_processed == 0
        assert result.records_inserted == 0
        assert result.error_details is None
        bundle_name = expected_bundle_name()
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "deploy" / f"{bundle_name}.sql").exists()

    @pytest.mark.asyncio
    async def test_ingest_emits_submission_and_links_new_dataset(self, tmp_path):
        """Ingest should resolve the provider, emit one submission, and link new datasets to it."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "dataset": pd.DataFrame(
                            {
                                "system_id": [10],
                                "dataset_id": [None],
                                "dataset_name": ["Pilot dataset"],
                                "data_type_id": [8],
                            }
                        )
                    },
                    "target_model": submission_target_model(),
                    "submission_context": minimal_submission_context(),
                    "trusted_project_context": minimal_trusted_project_context(),
                    "collision_checker": verified_provider_row(),
                    "reconciliation_client": FakeReconciliationClient(target_id=51),
                    "sims_client": FakeSimsClient(
                        binding_set_state="confirmed",
                        target_id=501,
                        target_ids={"submission": 1, "dataset": 91924},
                    ),
                },
            )
        )

        result = await ingest_bundle(ingester)

        assert result.success is True
        assert result.deploy_artifact is not None
        deploy_sql = result.deploy_artifact["deploy_sql"]
        assert 'INSERT INTO "tbl_submissions"' in deploy_sql
        assert 'INSERT INTO "tbl_datasets"' in deploy_sql
        assert '"submission_id"' in deploy_sql
        assert '"data_type_id"' in deploy_sql
        assert "tbl_submission_tasks" not in deploy_sql

    @pytest.mark.asyncio
    async def test_ingest_copy_csv_emits_submission_and_dataset_payloads(self, tmp_path):
        """Copy-CSV should emit payloads for the new submission and linked dataset only."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "dataset": pd.DataFrame(
                            {
                                "system_id": [10],
                                "dataset_id": [None],
                                "dataset_name": ["Pilot dataset"],
                                "data_type_id": [8],
                            }
                        )
                    },
                    "target_model": submission_target_model(),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "copy_csv",
                    "trusted_project_context": minimal_trusted_project_context(),
                    "collision_checker": verified_provider_row(),
                    "reconciliation_client": FakeReconciliationClient(target_id=51),
                    "sims_client": FakeSimsClient(
                        binding_set_state="confirmed",
                        target_id=501,
                        target_ids={"submission": 1, "dataset": 91924},
                    ),
                },
            )
        )

        result = await ingest_bundle(ingester)

        assert result.success is True
        assert result.deploy_artifact is not None
        bundle_files = result.deploy_artifact["bundle_files"]
        assert any(path.endswith("/tbl_submissions.gz") for path in bundle_files)
        assert any(path.endswith("/tbl_datasets.gz") for path in bundle_files)
        assert not any(path.endswith("/tbl_data_providers.gz") for path in bundle_files)
        assert not any(path.endswith("/tbl_submission_states.gz") for path in bundle_files)

    @pytest.mark.asyncio
    async def test_ingest_rejects_retired_file_input(self):
        """Ingest should reject the retired file input before resolving any source."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
            )
        )

        result = await ingester.ingest("submission.xlsx")

        assert result.success is False
        assert result.message == "File input retired"
        assert result.error_details == CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE

    @pytest.mark.asyncio
    async def test_ingest_returns_invalid_submission_context_error(self):
        """Ingest should stop at the submission-context boundary when the context is malformed."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(timestamp="invalid"),
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Invalid submission context"
        assert result.error_details == "Submission context timestamp must be a valid ISO-8601 datetime string"

    @pytest.mark.asyncio
    async def test_ingest_returns_invalid_submission_context_error_for_multiline_description(self, tmp_path):
        """Ingest should reject malformed descriptions before emitting any bundle files."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(description="line one\nline two"),
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Invalid submission context"
        assert result.error_details == "Submission context description must be a single line"
        assert not (tmp_path / expected_bundle_name()).exists()

    @pytest.mark.asyncio
    async def test_ingest_blocks_when_identity_resolution_incomplete(self):
        """Ingest should stop before generation when identity work remains unresolved."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Identity resolution incomplete"
        assert result.error_details == "Entity 'sample' row '0' is missing an identity assignment for planned action 'allocate'"

    @pytest.mark.asyncio
    async def test_ingest_blocks_sample_without_required_fields_or_references(self, tmp_path):
        """Ingest must not emit artifacts when required sample fields or references are missing."""
        target_model = minimal_target_model(
            sample_group={"role": "fact", "public_id": "sample_group_id"},
            sample_type={"role": "lookup", "public_id": "sample_type_id"},
            sample={
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
        )
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "physical_sample_id": [None],
                                "sample_group_id": [None],
                                "sample_type_id": [None],
                                "sample_name": [None],
                            }
                        )
                    },
                    "target_model": target_model,
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "PK/FK projection incomplete"
        assert result.error_details == (
            "Entity 'sample' has 1 null value(s) in required target column 'sample_name'\n"
            "Entity 'sample' has 1 missing required FK value(s) for 'sample_group_id'\n"
            "Entity 'sample' has 1 missing required FK value(s) for 'sample_type_id'"
        )
        assert result.deploy_artifact is None
        assert not list(tmp_path.iterdir())

    @pytest.mark.asyncio
    async def test_ingest_blocks_inserted_row_without_conditional_foreign_key_value(self, tmp_path):
        """Ingest must not emit artifacts when an inserted row misses its conditional FK value."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"location": pd.DataFrame({"location_id": [None], "location_type_id": [None]})},
                    "target_model": conditional_location_target_model(),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "location": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 601,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "PK/FK projection incomplete"
        assert result.error_details == "Entity 'location' has 1 missing conditional FK value(s) for 'location_type_id'"
        assert result.deploy_artifact is None
        assert not list(tmp_path.iterdir())

    @pytest.mark.asyncio
    async def test_ingest_accepts_resolved_identity_assignments(self, tmp_path):
        """Ingest should emit the MVP Delivery artifact bundle when assignments are present."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is True
        assert "Deploy artifact emitted to" in result.message
        assert result.tables_processed == 1
        assert result.records_inserted == 1
        assert result.error_details is None
        assert result.deploy_artifact is not None
        assert "Rollback is not implemented" in result.deploy_artifact["revert_sql"]
        assert "Verification is not implemented" in result.deploy_artifact["verify_sql"]
        bundle_name = expected_bundle_name()
        assert result.deploy_artifact["deploy_sql"].startswith(f"-- deploy mal: {bundle_name}\n/")
        assert result.deploy_artifact["metadata"]["deploy_strategy"] == "inline_insert"
        assert result.deploy_artifact["metadata_artifact"]["non_revertible"] is True
        assert result.deploy_artifact["metadata_artifact"]["deploy_strategy"] == "inline_insert"
        assert result.deploy_artifact["metadata_artifact"]["verify_placeholder"] is True
        assert result.deploy_artifact["metadata_artifact"]["contract_version"] == 1
        assert result.deploy_artifact["metadata_artifact"]["description"] == "test bundle"
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "deploy" / f"{bundle_name}.sql").exists()
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "revert" / f"{bundle_name}.sql").exists()
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "verify" / f"{bundle_name}.sql").exists()
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "manifest.json").exists()

    @pytest.mark.asyncio
    async def test_ingest_accepts_named_deploy_strategy(self, tmp_path):
        """Ingest should accept the default named deploy strategy from config.extra."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "inline_insert",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is True
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["metadata"]["deploy_strategy"] == "inline_insert"
        assert 'INSERT INTO "tbl_sample" ("sample_id") VALUES (501);' in result.deploy_artifact["deploy_sql"]

    @pytest.mark.asyncio
    async def test_ingest_emits_update_statement_for_accepted_existing_row(self, tmp_path):
        """Ingest should render accepted existing-row updates as UPDATE statements in the deploy artifact."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "sample_id": [101],
                                "sample_name": ["updated name"],
                                "sample_name__existing": ["old name"],
                            }
                        )
                    },
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"}),
                    "submission_context": minimal_submission_context(),
                    "mutable_fields_by_entity": {"sample": ["sample_name"]},
                    "existing_row_update_entities": ["sample"],
                },
            )
        )

        result = await ingest_bundle(ingester)

        assert result.success is True
        assert result.tables_processed == 1
        assert result.records_inserted == 1
        assert result.deploy_artifact is not None
        assert 'UPDATE "tbl_sample" SET "sample_name" = \'updated name\' WHERE "sample_id" = 101;' in result.deploy_artifact["deploy_sql"]
        assert "INSERT INTO" not in result.deploy_artifact["deploy_sql"]
        bundle_name = expected_bundle_name()
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "deploy" / f"{bundle_name}.sql").exists()

    @pytest.mark.asyncio
    async def test_ingest_emits_strategy_sidecar_files(self, tmp_path):
        """Ingest should write additional files emitted by a deploy strategy into the artifact bundle."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": StubBundleFileDeployStrategy(),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is True
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["bundle_files"] == {"deploy/test-submission/sample.csv": "sample_id\n501\n"}
        bundle_name = expected_bundle_name()
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "deploy" / "test-submission" / "sample.csv").read_text(
            encoding="utf-8"
        ) == "sample_id\n501\n"

    @pytest.mark.asyncio
    async def test_ingest_rejects_unknown_named_deploy_strategy(self):
        """Ingest should fail cleanly when config.extra requests an unsupported deploy strategy."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "unknown_strategy",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Invalid deploy strategy"
        assert result.error_details == (
            "Unsupported deploy strategy 'unknown_strategy'; expected 'inline_insert', 'copy_csv', or 'inline_staging'"
        )

    @pytest.mark.asyncio
    async def test_ingest_accepts_copy_csv_deploy_strategy(self, tmp_path):
        """Ingest should emit a CSV-backed artifact bundle for the copy_csv strategy."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "copy_csv",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is True
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["metadata"]["deploy_strategy"] == "copy_csv"
        assert result.deploy_artifact["metadata_artifact"]["bundle_file_count"] == 1
        assert result.deploy_artifact["metadata_artifact"]["payload_format"] == "csv"
        assert result.deploy_artifact["metadata_artifact"]["payload_empty_string_rule"] == "quoted_empty_field"
        bundle_name = expected_bundle_name()
        assert (
            f'\\copy "sample" ("sample_id") FROM program \'zcat -qac {bundle_name}/sample.gz\' '
            "WITH (FORMAT csv, DELIMITER E'\\t', ENCODING 'utf-8');" in result.deploy_artifact["deploy_sql"]
        )
        assert result.deploy_artifact["bundle_files"] == {f"deploy/{bundle_name}/sample.gz": "501\n"}
        assert (
            gzip.decompress((emitted_bundle_dir(tmp_path, bundle_name) / "deploy" / bundle_name / "sample.gz").read_bytes()).decode("utf-8")
            == "501\n"
        )
        assert '"description": "test bundle"' in (emitted_bundle_dir(tmp_path, bundle_name) / "manifest.json").read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_ingest_copy_csv_writes_date_only_timestamps_without_time_component(self, tmp_path):
        """Ingest should emit date-only pandas timestamps as YYYY-MM-DD in bundle payloads."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None], "sample_date": [pd.Timestamp("2026-05-23")]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "copy_csv",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is True
        bundle_name = expected_bundle_name()
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["bundle_files"] == {f"deploy/{bundle_name}/sample.gz": "501\t2026-05-23\n"}
        assert gzip.decompress((emitted_bundle_dir(tmp_path, bundle_name) / "deploy" / bundle_name / "sample.gz").read_bytes()).decode(
            "utf-8"
        ) == ("501\t2026-05-23\n")

    @pytest.mark.asyncio
    async def test_ingest_rejects_timezone_aware_target_column_before_writing_bundle(self, tmp_path):
        """Ingest should fail clearly and emit nothing for a timezone-aware target column."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None], "collected_at": [pd.Timestamp("2026-05-23 10:15:00+02:00")]})},
                    "target_model": minimal_target_model(
                        sample={
                            "role": "fact",
                            "public_id": "sample_id",
                            "columns": {
                                "sample_id": {"type": "integer"},
                                "collected_at": {"type": "timestamp with time zone"},
                            },
                        }
                    ),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Invalid deploy artifact input"
        assert result.error_details is not None
        assert "timezone-aware" in result.error_details
        assert not list(tmp_path.iterdir())

    @pytest.mark.asyncio
    async def test_ingest_rejects_unsafe_copy_csv_target_table_name(self, tmp_path):
        """Ingest should return a structured failure when copy_csv table names are unsafe for bundle paths."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(
                        sample={"role": "fact", "public_id": "sample_id", "target_table": "../tbl_sample"}
                    ),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "copy_csv",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Invalid deploy artifact input"
        assert result.error_details == (
            "Unsafe table name '../tbl_sample' for copy_csv deploy artifact; expected only letters, digits, and underscores"
        )

    @pytest.mark.asyncio
    async def test_ingest_retains_separate_bundles_for_distinct_run_ids(self, tmp_path):
        """Ingest should write each effective run ID to its own run folder instead of replacing a prior bundle."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "copy_csv",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        first_result = await ingest_bundle(ingester, validate_first=False)
        second_result = await ingest_bundle(ingester, validate_first=False)

        assert first_result.success is True
        assert second_result.success is True
        assert first_result.run_id != second_result.run_id
        bundle_name = expected_bundle_name()
        run_folders = [path for path in tmp_path.iterdir() if path.is_dir() and (path / bundle_name).is_dir()]
        assert len(run_folders) == 2
        assert all((folder / bundle_name / "manifest.json").exists() for folder in run_folders)

    @pytest.mark.asyncio
    async def test_ingest_run_folder_collision_fails_before_sims_calls(self, tmp_path):
        """A repeated run ID under the same clock should fail before any SIMS or file work."""
        sims_client = FakeSimsClient(target_id=501)
        run_id = "fixed-run-id"
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(run_id=run_id),
                    "deploy_strategy": "copy_csv",
                    "sims_client": sims_client,
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        with patch(
            "ingesters.sead_change_request.artifact_writer.utc_now",
            return_value=datetime(2026, 5, 23, 22, 0, 0),
        ):
            first = await ingest_bundle(ingester, validate_first=False)
            sims_calls = len(sims_client.run_ids)
            second = await ingest_bundle(ingester, validate_first=False)

        assert first.success is True
        assert second.success is False
        assert second.message == "Output folder collision"
        assert second.run_id == run_id
        assert second.output_path is None
        assert len(sims_client.run_ids) == sims_calls
        assert first.output_path is not None
        assert Path(first.output_path).exists()

    @pytest.mark.asyncio
    async def test_ingest_cleans_up_reserved_folder_after_write_failure(self, tmp_path):
        """A write failure should remove the reserved run folder without leaving partial output."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        with patch(
            "ingesters.sead_change_request.ingester.write_artifact_bundle",
            side_effect=RuntimeError("disk full"),
        ):
            with pytest.raises(RuntimeError, match="disk full"):
                await ingest_bundle(ingester, validate_first=False)

        assert not list(tmp_path.iterdir())

    @pytest.mark.asyncio
    async def test_ingest_copy_csv_manifest_matches_emitted_files_for_multitable_bundle(self, tmp_path):
        """Ingest should emit manifest checksums and row counts that match the on-disk bundle files."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "sample_id": [None],
                                "sample_note": ['tab\tquote"slash\\line\nend'],
                            }
                        ),
                        "site": pd.DataFrame(
                            {
                                "site_id": [None],
                                "site_name": ["North Ridge"],
                            }
                        ),
                    },
                    "target_model": minimal_target_model(
                        sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"},
                        site={"role": "fact", "public_id": "site_id", "target_table": "tbl_site"},
                    ),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "copy_csv",
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        },
                        "site": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 601,
                            }
                        },
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is True
        bundle_name = expected_bundle_name()
        bundle_root = emitted_bundle_dir(tmp_path, bundle_name)
        manifest = json.loads((bundle_root / "manifest.json").read_text(encoding="utf-8"))

        assert manifest["table_order"] == ["tbl_sample", "tbl_site"]
        assert manifest["row_counts"] == {"tbl_sample": 1, "tbl_site": 1}

        for relative_path in manifest["files"]:
            file_path = bundle_root / relative_path
            assert file_path.exists()
            assert manifest["checksums"][relative_path] == sha256(file_path.read_bytes()).hexdigest()

        assert gzip.decompress((bundle_root / "deploy" / bundle_name / "tbl_sample.gz").read_bytes()).decode("utf-8") == (
            '501\t"tab\tquote""slash\\line\nend"\n'
        )
        assert gzip.decompress((bundle_root / "deploy" / bundle_name / "tbl_site.gz").read_bytes()).decode("utf-8") == "601\tNorth Ridge\n"

    @pytest.mark.asyncio
    async def test_ingest_stops_when_target_id_collision_detected(self):
        """Ingest should stop before package generation when a target ID collision is detected."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"}),
                    "submission_context": minimal_submission_context(),
                    "collision_checker": FakeCollisionChecker(target_ids={("tbl_sample", "sample_id", 501)}),
                    "identity_assignments": {
                        "sample": {
                            0: {
                                "state": ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                                "target_id": 501,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Target collision checks failed"
        assert result.error_details == "Entity 'sample' row '0' collides with existing target ID 501 in 'tbl_sample.sample_id'"

    @pytest.mark.asyncio
    async def test_ingest_stops_when_bridge_uniqueness_metadata_missing_at_collision_check(self):
        """Ingest should fail before package generation when insertable bridge rows lack usable uniqueness metadata."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample_taxon": pd.DataFrame({"sample_id": [101], "taxon_id": [9001]})},
                    "target_model": minimal_target_model(sample_taxon={"role": "bridge"}),
                    "submission_context": minimal_submission_context(),
                    "collision_checker": FakeCollisionChecker(),
                    "identity_assignments": {
                        "sample_taxon": {
                            0: {
                                "state": ChangeRowState.DERIVED_BRIDGE_ROW,
                                "target_id": 5001,
                            }
                        }
                    },
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Target collision checks failed"
        assert result.error_details == "Bridge entity 'sample_taxon' cannot run collision checks because unique_sets metadata is missing"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("deploy_strategy", ["inline_insert", "copy_csv"])
    @pytest.mark.asyncio
    async def test_ingest_returns_pending_confirmation_report_for_proposed_binding_set(self, deploy_strategy):
        """Ingest should return the structured pending confirmation report when SIMS blocks finalization."""
        sims_client = FakeSimsClient(binding_set_state="proposed", confirmed_binding_set_state="proposed", target_id=501)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": deploy_strategy,
                    "sims_client": sims_client,
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Binding Set confirmation incomplete"
        assert result.pending_confirmation_report is not None
        assert result.pending_confirmation_report["binding_set_uuid"] == "binding-123"
        assert result.deploy_artifact is None
        assert sims_client.run_ids[0] is not None
        assert sims_client.run_ids[0] in result.pending_confirmation_report["rerun_instruction"]

    @pytest.mark.parametrize("deploy_strategy", ["inline_insert", "copy_csv"])
    @pytest.mark.asyncio
    async def test_ingest_blocks_before_writing_when_sims_has_no_aggregate_id(self, tmp_path, deploy_strategy):
        """Ingest should block artifact output when SIMS does not return an aggregate ID."""
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=None)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": deploy_strategy,
                    "sims_client": sims_client,
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "SIMS aggregate ID allocation capability incomplete"
        assert result.error_details is not None
        assert "complete target projection" in result.error_details
        assert "SIMS aggregate ID" in result.error_details
        assert result.deploy_artifact is None
        assert not list(tmp_path.iterdir())

    @pytest.mark.asyncio
    async def test_ingest_runs_mixed_pilot_bundle(self, tmp_path):
        """Ingest should handle a mixed pilot bundle with existing, allocated, reconciled, and bridge rows."""
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=501)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "system_id": [1, 2],
                                "sample_id": [101, None],
                                "sample_name": ["Existing Sample", "New Sample"],
                            }
                        ),
                        "taxon": pd.DataFrame(
                            {
                                "system_id": [10, 11],
                                "taxon_id": [9001, None],
                                "taxon_name": ["Existing Taxon", "Reconciled Taxon"],
                            }
                        ),
                        "sample_taxon": pd.DataFrame(
                            {
                                "sample_id": [2],
                                "taxon_id": [11],
                                "abundance": [3],
                            }
                        ),
                    },
                    "target_model": minimal_target_model(
                        sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"},
                        taxon={"role": "classifier", "public_id": "taxon_id", "target_table": "tbl_taxon"},
                        sample_taxon={
                            "role": "bridge",
                            "target_table": "tbl_sample_taxon",
                            "unique_sets": [["sample_id", "taxon_id"]],
                            "foreign_keys": [{"entity": "sample"}, {"entity": "taxon"}],
                        },
                    ),
                    "submission_context": minimal_submission_context(change_request_name="deploy/mixed-pilot"),
                    "sims_client": sims_client,
                    "reconciliation_client": FakeReconciliationClient(target_id=9200),
                    "collision_checker": FakeCollisionChecker(),
                },
            )
        )

        result = await ingest_bundle(ingester)

        assert result.success is True
        assert result.message.startswith("Deploy artifact emitted to '")
        assert result.tables_processed == 2
        assert result.records_inserted == 2
        assert result.error_details is None
        assert sims_client.associated_change_requests == [("binding-123", "deploy/mixed-pilot")]
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["metadata"]["binding_set_uuid"] == "binding-123"
        assert result.deploy_artifact["metadata"]["change_request_name"] == "deploy/mixed-pilot"
        assert result.deploy_artifact["metadata"]["change_request_associated"] is True
        assert result.deploy_artifact["metadata"]["deploy_strategy"] == "inline_insert"
        assert result.deploy_artifact["metadata"]["verify_placeholder"] is True
        assert result.deploy_artifact["metadata_artifact"]["deploy_statement_count"] == 2
        assert result.deploy_artifact["metadata_artifact"]["deploy_strategy"] == "inline_insert"
        assert result.deploy_artifact["metadata_artifact"]["verify_placeholder"] is True
        assert 'INSERT INTO "tbl_sample" ("sample_id", "sample_name") VALUES (501, ' in result.deploy_artifact["deploy_sql"]
        assert (
            'INSERT INTO "tbl_sample_taxon" ("sample_id", "taxon_id", "abundance") VALUES (501, 9200, 3);'
            in result.deploy_artifact["deploy_sql"]
        )
        assert "tbl_taxon" not in result.deploy_artifact["deploy_sql"]
        assert "Existing Sample" not in result.deploy_artifact["deploy_sql"]
        bundle_name = expected_bundle_name(change_request_name="deploy/mixed-pilot")
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "deploy" / f"{bundle_name}.sql").exists()
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "verify" / f"{bundle_name}.sql").exists()
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "manifest.json").exists()

    @pytest.mark.asyncio
    async def test_ingest_runs_mixed_pilot_bundle_with_backend_bridge_adapter(self, tmp_path):
        """Ingest should handle bridge rows through the real backend adapter seam."""
        adapter = SeadChangeRequestSimsAdapter(cast(Any, FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)))
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "sample": pd.DataFrame(
                            {
                                "system_id": [1, 2],
                                "sample_id": [101, None],
                                "sample_name": ["Existing Sample", "New Sample"],
                            }
                        ),
                        "taxon": pd.DataFrame(
                            {
                                "system_id": [10, 11],
                                "taxon_id": [9001, None],
                                "taxon_name": ["Existing Taxon", "Reconciled Taxon"],
                            }
                        ),
                        "sample_taxon": pd.DataFrame(
                            {
                                "sample_id": [2],
                                "taxon_id": [11],
                                "abundance": [3],
                            }
                        ),
                    },
                    "target_model": minimal_target_model(
                        sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"},
                        taxon={"role": "classifier", "public_id": "taxon_id", "target_table": "tbl_taxon"},
                        sample_taxon={
                            "role": "bridge",
                            "target_table": "tbl_sample_taxon",
                            "unique_sets": [["sample_id", "taxon_id"]],
                            "foreign_keys": [{"entity": "sample"}, {"entity": "taxon"}],
                        },
                    ),
                    "submission_context": minimal_submission_context(change_request_name="deploy/backend-bridge"),
                    "trusted_project_context": minimal_trusted_project_context(),
                    "sims_client": adapter,
                    "reconciliation_client": FakeReconciliationClient(target_id=9200),
                    "collision_checker": FakeCollisionChecker(),
                },
            )
        )

        result = await ingest_bundle(ingester)

        assert result.success is True
        assert result.records_inserted == 2
        assert result.deploy_artifact is not None
        assert (
            'INSERT INTO "tbl_sample_taxon" ("sample_id", "taxon_id", "abundance") VALUES (501, 9200, 3);'
            in result.deploy_artifact["deploy_sql"]
        )
        bundle_name = expected_bundle_name(change_request_name="deploy/backend-bridge")
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "deploy" / f"{bundle_name}.sql").exists()

    @pytest.mark.asyncio
    async def test_ingest_blocks_artifact_when_approved_match_conflicts_with_sims(self, tmp_path):
        request = httpx.Request("POST", "http://sims.test/identity/resolve")
        response = httpx.Response(409, request=request, text="approved aggregate ID is already bound elsewhere")
        conflict = httpx.HTTPStatusError("409 Conflict", request=request, response=response)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, FakeBackendSimsClient(resolve_error=conflict)))
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"taxon": pd.DataFrame({"taxon_id": [None], "taxon_name": ["Approved taxon"]})},
                    "target_model": minimal_target_model(taxon={"role": "classifier", "public_id": "taxon_id", "target_table": "tbl_taxa"}),
                    "submission_context": minimal_submission_context(),
                    "trusted_project_context": minimal_trusted_project_context(),
                    "sims_client": adapter,
                    "reconciliation_client": FakeReconciliationClient(target_id=77),
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is False
        assert result.message == "Identity resolution incomplete"
        assert "HTTP 409" in (result.error_details or "")
        assert "already bound elsewhere" in (result.error_details or "")
        assert result.deploy_artifact is None
        assert not list(tmp_path.iterdir())

    @pytest.mark.asyncio
    async def test_ingest_associates_change_request_after_confirmation(self, tmp_path):
        """Ingest should associate the requested CR name when the Binding Set is already confirmed."""
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=501)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(change_request_name="deploy/test-change"),
                    "sims_client": sims_client,
                },
            )
        )

        result = await ingest_bundle(ingester, validate_first=False)

        assert result.success is True
        assert "Deploy artifact emitted to" in result.message
        assert sims_client.associated_change_requests == [("binding-123", "deploy/test-change")]
        assert result.deploy_artifact is not None
        assert result.deploy_artifact["metadata"]["change_request_associated"] is True
        bundle_name = expected_bundle_name(change_request_name="deploy/test-change")
        assert (emitted_bundle_dir(tmp_path, bundle_name) / "deploy" / f"{bundle_name}.sql").exists()

    @pytest.mark.asyncio
    async def test_ingest_returns_validation_failure_for_unknown_target_model_table(self):
        """Ingest should stop when the source bundle and target model do not align."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [1]})},
                    "target_model": minimal_target_model(site={"role": "fact", "public_id": "site_id"}),
                    "submission_context": minimal_submission_context(),
                },
            )
        )

        result = await ingest_bundle(ingester)

        assert result.success is False
        assert result.message == "Validation failed"
        assert result.error_details == "Source table 'sample' is not present in the target model"


def staging_target_model() -> dict:
    """Build an aggregate chain used to exercise the inline staging strategy."""
    return minimal_target_model(
        site={"role": "lookup", "public_id": "site_id", "target_table": "tbl_sites"},
        dataset={
            "role": "lookup",
            "identity_tracking": "tracked",
            "reconciliation": "allocate",
            "public_id": "dataset_id",
            "target_table": "tbl_datasets",
            "synchronize_sequence_after_insert": True,
            "columns": {"site_id": {"required": True, "type": "integer"}},
            "foreign_keys": [{"entity": "site", "required": True}],
        },
        analysis_entity={
            "role": "fact",
            "public_id": "analysis_entity_id",
            "target_table": "tbl_analysis_entities",
            "aggregate_parent": "dataset",
            "columns": {"dataset_id": {"required": True, "type": "integer"}},
            "foreign_keys": [{"entity": "dataset", "required": True}],
        },
    )


class TestSeadChangeRequestIngesterStaging:
    """Tests for the opt-in inline staging strategy."""

    @pytest.mark.asyncio
    async def test_ingest_emits_staging_artifact_with_deployment_time_child_ids(self, tmp_path):
        """Staging keeps child ID allocation in the generated deployment SQL."""
        sims_client = FakeSimsClient(target_id=501)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "site": pd.DataFrame({"system_id": [1], "site_id": [7001]}),
                        "dataset": pd.DataFrame({"system_id": [10], "dataset_id": [None], "site_id": [1], "dataset_name": ["D1"]}),
                        "analysis_entity": pd.DataFrame({"system_id": [100], "analysis_entity_id": [None], "dataset_id": [10]}),
                    },
                    "target_model": staging_target_model(),
                    "submission_context": minimal_submission_context(),
                    "sims_client": sims_client,
                    "reconciliation_client": FakeReconciliationClient(target_id=7001),
                    "deploy_strategy": "inline_staging",
                    "staging_target_schema": "public",
                },
            )
        )
        result = await ingest_bundle(ingester)
        result = await ingest_bundle(ingester)
        assert result.success is True, result.error_details
        assert result.success is True, result.error_details
        assert result.deploy_artifact is not None
        deploy_sql = result.deploy_artifact["deploy_sql"]
        assert result.deploy_artifact["metadata"]["deploy_strategy"] == "inline_staging"
        assert '"public"."tbl_analysis_entities"' in deploy_sql
        assert "SELECT 'analysis_entity', \"_local_system_id\"," in deploy_sql


class TestDatabaseSequenceIdentity:
    """Database-sequence IDs must be resolved before Change Request preparation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("deploy_strategy", ["inline_insert", "copy_csv", "inline_staging"])
    async def test_validation_and_ingestion_block_unresolved_ids_without_allocator_calls(self, tmp_path, deploy_strategy):
        class UnexpectedAllocator:
            """Fail if preparation attempts to consume a target sequence."""

            async def reserve_target_id(self, table_name: str, public_id_column: str) -> int:
                raise AssertionError(f"Unexpected target sequence allocation for {table_name}.{public_id_column}")

        sims_client = CountingSimsClient()
        extra: dict[str, Any] = {
            "tables": {"sample": pd.DataFrame({"sample_id": [None], "sample_name": ["A"]})},
            "target_model": minimal_target_model(
                sample={
                    "role": "fact",
                    "public_id": "sample_id",
                    "public_id_generation": "database_sequence",
                    "target_table": "tbl_samples",
                    "identity_tracking": "derived",
                    "reconciliation": "derive",
                }
            ),
            "submission_context": minimal_submission_context(),
            "sims_client": sims_client,
            "target_id_allocator": UnexpectedAllocator(),
            "deploy_strategy": deploy_strategy,
        }
        if deploy_strategy == "inline_staging":
            extra["staging_target_schema"] = "public"

        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra=extra,
            )
        )

        validation = await validate_bundle(ingester)
        ingestion = await ingest_bundle(ingester, validate_first=False)

        assert validation.is_valid is False
        assert any("pre-resolve it before Change Request validation or bundle generation" in error for error in validation.errors)
        assert ingestion.success is False
        assert "pre-resolve it before Change Request validation or bundle generation" in (ingestion.error_details or "")
        assert sims_client.batch_calls == 0


class TestSeadChangeRequestIngesterStagingValidation:
    """Tests for inline-staging configuration and eligibility."""

    @pytest.mark.asyncio
    async def test_staging_requires_an_explicit_schema(self):
        """Validation fails when staging is selected without a schema."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                extra={
                    "tables": {"site": pd.DataFrame({"system_id": [1], "site_id": [7001]})},
                    "target_model": staging_target_model(),
                    "submission_context": minimal_submission_context(),
                    "deploy_strategy": "inline_staging",
                },
            )
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert result.errors == [
            "Deploy strategy 'inline_staging' requires a non-empty 'staging_target_schema'; "
            "target table names exist in more than one schema"
        ]

    @pytest.mark.asyncio
    async def test_staging_blocks_a_child_of_an_existing_tracked_root(self, tmp_path):
        """A child of an existing tracked root is rejected before rendering."""
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {
                        "site": pd.DataFrame({"system_id": [1], "site_id": [7001]}),
                        "dataset": pd.DataFrame({"system_id": [10], "dataset_id": [900], "site_id": [1], "dataset_name": ["D1"]}),
                        "analysis_entity": pd.DataFrame({"system_id": [100], "analysis_entity_id": [None], "dataset_id": [10]}),
                    },
                    "target_model": staging_target_model(),
                    "submission_context": minimal_submission_context(),
                    "sims_client": FakeSimsClient(target_id=501),
                    "reconciliation_client": FakeReconciliationClient(target_id=7001),
                    "deploy_strategy": "inline_staging",
                    "staging_target_schema": "public",
                },
            )
        )

        result = await ingest_bundle(ingester)

        assert result.success is False
        assert result.message == "Validation failed"
        assert "existing tracked root" in result.error_details


class TestDeclaredBusinessKeys:
    """Tracked business keys must pass validation before any SIMS request."""

    @staticmethod
    def _ingester(
        tmp_path,
        *,
        keys: tuple[str, ...],
        frame: pd.DataFrame,
        sims_client: CountingSimsClient,
        deploy_strategy: str | None = None,
    ):
        extra = {
            "tables": {"sample": frame},
            "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_samples"}),
            "submission_context": minimal_submission_context(),
            "trusted_project_context": minimal_trusted_project_context(business_keys={"sample": keys}),
            "sims_client": sims_client,
        }
        if deploy_strategy is not None:
            extra["deploy_strategy"] = deploy_strategy
            if deploy_strategy == "inline_staging":
                extra["staging_target_schema"] = "public"
        return SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra=extra,
            )
        )

    @pytest.mark.asyncio
    async def test_rejects_a_tracked_entity_without_declared_keys(self, tmp_path):
        sims_client = CountingSimsClient(target_id=501)
        ingester = self._ingester(
            tmp_path,
            keys=(),
            frame=pd.DataFrame({"sample_id": [None], "sample_code": ["S1"]}),
            sims_client=sims_client,
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert any("declares no business keys" in error for error in result.errors)
        assert sims_client.batch_calls == 0

    @pytest.mark.asyncio
    async def test_rejects_missing_key_values(self, tmp_path):
        sims_client = CountingSimsClient(target_id=501)
        ingester = self._ingester(
            tmp_path,
            keys=("sample_code",),
            frame=pd.DataFrame({"sample_id": [None], "sample_code": [None]}),
            sims_client=sims_client,
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert any("value is missing" in error for error in result.errors)
        assert sims_client.batch_calls == 0

    @pytest.mark.asyncio
    async def test_rejects_duplicate_key_values_in_one_delivery(self, tmp_path):
        sims_client = CountingSimsClient(target_id=501)
        ingester = self._ingester(
            tmp_path,
            keys=("sample_code",),
            frame=pd.DataFrame({"sample_id": [None, None], "sample_code": ["S1", "S1"]}),
            sims_client=sims_client,
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert any("share one business key value" in error for error in result.errors)
        assert sims_client.batch_calls == 0

    @pytest.mark.asyncio
    async def test_rejects_a_key_column_missing_from_the_delivery(self, tmp_path):
        sims_client = CountingSimsClient(target_id=501)
        ingester = self._ingester(
            tmp_path,
            keys=("sample_code",),
            frame=pd.DataFrame({"sample_id": [None], "other": ["S1"]}),
            sims_client=sims_client,
        )

        result = await validate_bundle(ingester)

        assert result.is_valid is False
        assert any("missing declared business key column" in error for error in result.errors)
        assert sims_client.batch_calls == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("deploy_strategy", ["inline_insert", "copy_csv", "inline_staging"])
    async def test_accepts_unique_keys_and_reports_the_effective_scope_and_run(self, tmp_path, deploy_strategy):
        sims_client = CountingSimsClient(target_id=501)
        ingester = self._ingester(
            tmp_path,
            keys=("sample_code",),
            frame=pd.DataFrame({"sample_id": [None], "sample_code": ["S1"]}),
            sims_client=sims_client,
            deploy_strategy=deploy_strategy,
        )

        result = await ingest_bundle(ingester)

        assert result.success is True
        assert sims_client.batch_calls == 1
        assert result.scope_name == TEST_SCOPE_NAME
        assert result.run_id
        assert result.deploy_artifact is not None
        assert set(sims_client.scope_names) == {result.scope_name}
        assert set(sims_client.run_ids) == {result.run_id}
        manifest_metadata = result.deploy_artifact["metadata_artifact"]
        assert manifest_metadata["scope_name"] == result.scope_name
        assert manifest_metadata["run_id"] == result.run_id
        assert result.deploy_artifact["metadata"]["scope_name"] == result.scope_name
        assert result.deploy_artifact["metadata"]["run_id"] == result.run_id
        manifest_path = next(tmp_path.rglob("manifest.json"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["scope_name"] == result.scope_name
        assert manifest["run_id"] == result.run_id

    @pytest.mark.asyncio
    async def test_normalized_string_keys_reach_identity_decisions_and_artifacts(self, tmp_path):
        """A zero-padded key should stay a string in the identity decision and the emitted artifact."""
        sims_client = CountingSimsClient(target_id=501)
        ingester = self._ingester(
            tmp_path,
            keys=("sample_code",),
            frame=pd.DataFrame({"sample_id": [None], "sample_code": ["001"]}),
            sims_client=sims_client,
        )

        result = await ingest_bundle(ingester)

        assert result.success is True
        assert sims_client.batch_calls == 1
        assert result.deploy_artifact is not None
        assert "'001'" in result.deploy_artifact["deploy_sql"]


class TestRetiredFileInput:
    """The public file methods must reject workbooks and paths without side effects."""

    @staticmethod
    def _ingester(tmp_path: Path) -> tuple[SeadChangeRequestIngester, CountingSimsClient]:
        sims_client = CountingSimsClient(target_id=501)
        ingester = SeadChangeRequestIngester(
            IngesterConfig(
                host="localhost",
                port=5432,
                dbname="test_db",
                user="test_user",
                output_folder=str(tmp_path),
                extra={
                    "tables": {"sample": pd.DataFrame({"sample_id": [None]})},
                    "target_model": minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
                    "submission_context": minimal_submission_context(),
                    "sims_client": sims_client,
                },
            )
        )
        return ingester, sims_client

    @pytest.mark.asyncio
    @pytest.mark.parametrize("source", ["submission.xlsx", Path("submission.xlsx")])
    async def test_validate_rejects_file_sources_without_preparation(self, tmp_path: Path, source: str | Path):
        ingester, sims_client = self._ingester(tmp_path)

        with patch.object(SeadChangeRequestIngester, "_prepare_change_request", side_effect=AssertionError("must not prepare")):
            result = await ingester.validate(source)

        assert result.is_valid is False
        assert result.errors == [CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE]
        assert sims_client.batch_calls == 0
        assert not list(tmp_path.iterdir())

    @pytest.mark.asyncio
    @pytest.mark.parametrize("validate_first", [True, False])
    async def test_ingest_rejects_file_sources_without_preparation(self, tmp_path: Path, validate_first: bool):
        ingester, sims_client = self._ingester(tmp_path)

        with patch.object(SeadChangeRequestIngester, "_prepare_change_request", side_effect=AssertionError("must not prepare")):
            result = await ingester.ingest("submission.xlsx", validate_first=validate_first)

        assert result.success is False
        assert result.message == "File input retired"
        assert result.error_details == CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE
        assert result.records_inserted == 0
        assert sims_client.batch_calls == 0
        assert not list(tmp_path.iterdir())
