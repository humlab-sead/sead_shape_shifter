"""Tests for guarded project-to-ingester composition."""

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pandas as pd
import pytest

from backend.app.authorization.models import Action, AuthorizedResource, Principal, ResourceRecord, ResourceType
from backend.app.core.config import Settings
from backend.app.ingesters.protocol import IngestionResult, ValidationResult
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.ingester import ProjectIngesterRequest, ProjectSubmissionOptions
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services import project_ingester_service as project_ingester_module
from backend.app.services.project_data_provider_service import ProjectDataProviderError
from backend.app.services.project_ingester_service import ProjectIngesterService
from ingesters.sead_change_request.contracts import TrustedProjectContext
from ingesters.sead_change_request.ingester import SeadChangeRequestIngester


def authorized_project(
    *,
    action: Action = Action.EXECUTE,
    resource_type: ResourceType = ResourceType.PROJECT,
    lifecycle_state: str = "active",
    locator: str = "pilot",
) -> AuthorizedResource:
    """Build one project authorization result."""
    principal = Principal("operator", "test", datetime.now(UTC))
    resource = ResourceRecord(uuid4(), resource_type, locator, lifecycle_state)
    return AuthorizedResource(principal, action, resource)


def request(project_name: str = "pilot") -> ProjectIngesterRequest:
    """Build one valid request for the project-ingester service."""
    return ProjectIngesterRequest(
        project_name=project_name,
        submission_context=ProjectSubmissionOptions(
            submission_name="pilot-run",
            timestamp=datetime(2026, 10, 19, 12, 0),
            datatype="mal",
            identifier="PILOT_RUN",
        ),
    )


def core_project(*, target_model: dict[str, Any] | None = None) -> SimpleNamespace:
    """Build a mapped core project with an optional target model."""
    return SimpleNamespace(cfg={"metadata": {"target_model": target_model}, "entities": {}}, entities={})


def valid_target_model() -> dict[str, Any]:
    """Build a minimal target model for reference-only sample rows."""
    return {
        "model": {"name": "SEAD Test Model", "version": "0.1.0"},
        "entities": {"sample": {"role": "fact", "public_id": "sample_id"}},
        "constraints": [],
    }


def direct_fk_target_model() -> dict[str, Any]:
    """Build the target model used by saved-project direct-FK tests."""
    return {
        "model": {"name": "Direct FK Test Model", "version": "0.1.0"},
        "entities": {
            "location_type": {"role": "lookup", "public_id": "location_type_id", "target_table": "tbl_location_types"},
            "location": {
                "role": "fact",
                "public_id": "location_id",
                "target_table": "tbl_locations",
                "foreign_keys": [{"entity": "location_type", "required": True}],
            },
        },
        "constraints": [],
    }


def saved_direct_fk_project(
    *,
    value_source: str | None = "public_id",
    columns: list[str] | None = None,
    foreign_keys: list[dict[str, Any]] | None = None,
) -> Project:
    """Build one saved project with a direct-FK declaration and inline target model."""
    location: dict[str, Any] = {
        "type": "fixed",
        "columns": columns or ["location_type_id"],
        "values": [[42] if columns is None or "location_type_id" in columns else ["Norway"]],
    }
    if value_source is not None:
        location["foreign_key_value_sources"] = {"location_type": value_source}
    if foreign_keys:
        location["foreign_keys"] = foreign_keys
    return Project(
        metadata=ProjectMetadata(
            name="pilot",
            entity_count=1,
            data_provider_code="SEAD",
            provider_schema="test-schema",
            target_model=direct_fk_target_model(),
        ),
        entities={"location": location},
    )


class FakeProjectService:
    """Record saved-project loads."""

    def __init__(self, project: Project | None = None) -> None:
        self.project = project or Project(
            metadata=ProjectMetadata(name="pilot", entity_count=0),
            entities={},
            options={},
        )
        self.loaded: list[str] = []

    def load_project(self, project_name: str) -> Project:
        self.loaded.append(project_name)
        return self.project


class FakeTableIngester:
    """Capture the config and calls made by the composition service."""

    instances: list["FakeTableIngester"] = []
    validation_result = ValidationResult(is_valid=True)
    ingestion_result = IngestionResult(
        success=True,
        message="bundle generated",
        records_inserted=3,
        scope_name="provider://pilot",
        run_id="run-1",
        deploy_artifact={"deploy_sql": "SELECT 1;"},
    )

    def __init__(self, config) -> None:
        self.config = config
        self.validation_call: tuple[dict[str, pd.DataFrame], str] | None = None
        self.ingestion_call: tuple[dict[str, pd.DataFrame], str, bool] | None = None
        self.instances.append(self)

    async def validate_tables(self, tables, *, source_name: str = "") -> ValidationResult:
        self.validation_call = (tables, source_name)
        return self.validation_result

    async def ingest_tables(self, tables, *, source_name: str = "", validate_first: bool = True) -> IngestionResult:
        self.ingestion_call = (tables, source_name, validate_first)
        return self.ingestion_result

    async def validate(self, source) -> ValidationResult:
        raise AssertionError("The file validation method must not be called")

    async def ingest(self, source, validate_first: bool = True) -> IngestionResult:
        raise AssertionError("The file ingestion method must not be called")


class FakeFileIngester:
    """Expose only the shared file methods."""

    async def validate(self, source) -> ValidationResult:
        raise AssertionError("The file validation method must not be called")

    async def ingest(self, source, validate_first: bool = True) -> IngestionResult:
        raise AssertionError("The file ingestion method must not be called")


class FakeRegistry:
    """Return a selected ingester class."""

    def __init__(self, ingester_class) -> None:
        self.ingester_class = ingester_class

    def get(self, key: str):  # pylint: disable=unused-argument
        return self.ingester_class


class FakeProjectDataProviderService:
    """Return a fixed trusted project context."""

    def __init__(self, context: TrustedProjectContext | None = None) -> None:
        self.context = context or TrustedProjectContext(
            project_name="pilot",
            provider_code="SEAD",
            provider_schema="pilot",
            scope_name="provider://pilot",
            data_provider_id=51,
            business_keys={},
        )
        self.projects: list[Project] = []

    def build_trusted_context(self, project: Project) -> TrustedProjectContext:
        self.projects.append(project)
        return self.context


def settings(tmp_path: Path, **overrides: Any) -> Settings:
    """Build the dedicated target connection settings for a service test."""
    values: dict[str, Any] = {
        "APPLICATION_ROOT": tmp_path,
        "INGEST_TARGET_HOST": "target-db",
        "INGEST_TARGET_PORT": 5444,
        "INGEST_TARGET_DBNAME": "sead_test",
        "INGEST_TARGET_USER": "ingester",
        "INGEST_OUTPUT_DIR": Path("generated/change-requests"),
    }
    values.update(overrides)
    return Settings(**values)


def install_common_mocks(
    monkeypatch,
    *,
    project_service: FakeProjectService | None = None,
    registry_ingester: type = FakeTableIngester,
    specification_valid: bool = True,
    specification_errors: list[str] | None = None,
    specification_warnings: list[str] | None = None,
    table_store: dict[str, pd.DataFrame] | None = None,
) -> tuple[FakeProjectService, list[tuple[str, Any]]]:
    """Install isolated project, specification, registry, mapping, and normalization fakes."""
    project_service = project_service or FakeProjectService()
    calls: list[tuple[str, Any]] = []
    mapped = core_project(target_model=valid_target_model())

    monkeypatch.setattr(project_ingester_module.ProjectMapper, "to_core", staticmethod(lambda project: mapped))

    class FakeSpecification:
        def __init__(self, cfg) -> None:  # pylint: disable=unused-argument
            self.errors = specification_errors or []
            self.warnings = specification_warnings or []

        def is_satisfied_by(self) -> bool:
            return specification_valid

    monkeypatch.setattr(project_ingester_module, "CompositeProjectSpecification", FakeSpecification)
    monkeypatch.setattr(
        project_ingester_module,
        "get_ingester_registry",
        lambda: FakeRegistry(registry_ingester),
    )

    async def normalize(project, *, translate, drop_foreign_keys, default_entity, env_file):
        calls.append(("normalize", (project, translate, drop_foreign_keys, default_entity, env_file)))
        return SimpleNamespace(table_store=table_store or {"sample": pd.DataFrame({"sample_id": [1, 2]})})

    monkeypatch.setattr(project_ingester_module, "normalize_project", normalize)
    return project_service, calls


def project_ingester_service(
    project_service: FakeProjectService,
    *,
    provider_service: FakeProjectDataProviderService | None = None,
    runtime_settings: Settings | None = None,
) -> ProjectIngesterService:
    """Construct the service with fake dependencies."""
    return ProjectIngesterService(
        project_service=project_service,  # type: ignore
        project_data_provider_service=provider_service or FakeProjectDataProviderService(),  # type: ignore
        settings=runtime_settings or settings(Path("/tmp/project-ingester-tests")),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["validate_project_tables", "ingest_project_tables"])
@pytest.mark.parametrize(
    "authorized",
    [
        None,
        authorized_project(action=Action.READ),
        authorized_project(resource_type=ResourceType.SHARED_DATA_SOURCE),
        authorized_project(lifecycle_state="inactive"),
        authorized_project(locator=" "),
    ],
)
async def test_invalid_project_resource_is_rejected_before_project_load(monkeypatch, method_name, authorized) -> None:
    """Invalid resource authorization must not load a project or invoke downstream work."""
    project_service, calls = install_common_mocks(monkeypatch)
    service = project_ingester_service(project_service)
    method = getattr(service, method_name)

    with pytest.raises(PermissionError):
        await method("sead_change_request", authorized, request())

    assert project_service.loaded == []
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["validate_project_tables", "ingest_project_tables"])
async def test_mismatched_project_name_is_rejected_before_project_load(monkeypatch, method_name) -> None:
    """The request locator must exactly match the authorized project locator."""
    project_service, calls = install_common_mocks(monkeypatch)
    service = project_ingester_service(project_service)
    method = getattr(service, method_name)

    with pytest.raises(PermissionError):
        await method("sead_change_request", authorized_project(), request("Pilot"))

    assert not project_service.loaded
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["validate_project_tables", "ingest_project_tables"])
async def test_authorized_project_executor_needs_no_application_role(monkeypatch, tmp_path, method_name) -> None:
    """A valid project executor reaches both operations without an application role."""
    project_service, calls = install_common_mocks(monkeypatch)
    service = project_ingester_service(project_service, runtime_settings=settings(tmp_path))
    method = getattr(service, method_name)

    result = await method("sead_change_request", authorized_project(), request())

    if method_name == "validate_project_tables":
        assert result.is_valid is True
    else:
        assert result.success is True
    assert project_service.loaded == ["pilot"]
    assert calls[0][0] == "normalize"


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["validate_project_tables", "ingest_project_tables"])
async def test_direct_call_rejects_unvalidated_request_object_before_loading(monkeypatch, method_name) -> None:
    """Raw mappings cannot bypass strict request-model validation."""
    project_service, calls = install_common_mocks(monkeypatch)
    service = project_ingester_service(project_service)
    method = getattr(service, method_name)

    with pytest.raises(TypeError, match="ProjectIngesterRequest"):
        await method(
            "sead_change_request",
            authorized_project(),
            {"project_name": "pilot"},  # type: ignore
        )

    assert project_service.loaded == []
    assert not calls


@pytest.mark.asyncio
async def test_project_specification_failure_stops_before_normalization(monkeypatch) -> None:
    """Failed project specification checks return errors without table work."""
    project_service, calls = install_common_mocks(
        monkeypatch,
        specification_valid=False,
        specification_errors=[],
    )
    service = project_ingester_service(project_service)

    result = await service.validate_project_tables("sead_change_request", authorized_project(), request())

    assert result.is_valid is False
    assert result.errors == ["Project configuration validation failed"]
    assert not calls


@pytest.mark.asyncio
async def test_project_specification_exception_returns_project_error(monkeypatch) -> None:
    """An exception during project specification checks is returned as a project error."""
    project_service, calls = install_common_mocks(monkeypatch)

    class RaisingSpecification:
        errors = []
        warnings = []

        def __init__(self, cfg) -> None:
            pass

        def is_satisfied_by(self) -> bool:
            raise ValueError("bad project")

    monkeypatch.setattr(project_ingester_module, "CompositeProjectSpecification", RaisingSpecification)
    service = project_ingester_service(project_service)

    result = await service.ingest_project_tables("sead_change_request", authorized_project(), request())

    assert result.success is False
    assert result.message == "Project validation failed"
    assert "bad project" in (result.error_details or "")
    assert not calls


@pytest.mark.asyncio
async def test_warning_only_project_continues_and_table_validation_results_are_preserved(monkeypatch, tmp_path) -> None:
    """Project warnings do not block work, and validation result details are returned."""
    project_service, calls = install_common_mocks(
        monkeypatch,
        specification_warnings=["project warning"],
    )
    FakeTableIngester.instances.clear()
    FakeTableIngester.validation_result = ValidationResult(
        is_valid=True,
        warnings=["table warning"],
        infos=["table info"],
        pending_confirmation_report={"status": "pending"},
    )
    service = project_ingester_service(project_service, runtime_settings=settings(tmp_path))

    result = await service.validate_project_tables("sead_change_request", authorized_project(), request())

    ingester = FakeTableIngester.instances[-1]
    assert result.is_valid is True
    assert result.warnings == ["project warning", "table warning"]
    assert result.infos == ["table info"]
    assert result.pending_confirmation_report == {"status": "pending"}
    assert ingester.validation_call is not None
    assert ingester.validation_call[1] == "project:pilot"
    assert calls[0][0] == "normalize"


@pytest.mark.asyncio
async def test_file_only_ingester_returns_file_input_error_without_normalization(monkeypatch) -> None:
    """A registered file-only ingester gets a clear table-capability error."""
    project_service, calls = install_common_mocks(monkeypatch, registry_ingester=FakeFileIngester)
    service = project_ingester_service(project_service)

    validation = await service.validate_project_tables("sead", authorized_project(), request())
    ingestion = await service.ingest_project_tables("sead", authorized_project(), request())

    assert validation.is_valid is False
    assert "file input" in validation.errors[0].lower()
    assert ingestion.success is False
    assert ingestion.message == "File input required"
    assert "file input" in (ingestion.error_details or "").lower()
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setting_override",
    [
        {"INGEST_TARGET_HOST": None},
        {"INGEST_TARGET_DBNAME": None},
        {"INGEST_TARGET_USER": None},
        {"INGEST_OUTPUT_DIR": None},
    ],
)
async def test_missing_backend_settings_stop_before_provider_or_normalization(monkeypatch, tmp_path, setting_override) -> None:
    """Incomplete server-owned target settings stop before provider, runtime, or table work."""
    project_service, calls = install_common_mocks(monkeypatch)
    provider_service = FakeProjectDataProviderService()
    injections: list[str] = []
    monkeypatch.setattr(
        project_ingester_module,
        "inject_ingester_runtime_dependencies",
        lambda key, extra, settings: injections.append("runtime") or extra,
    )
    monkeypatch.setattr(
        project_ingester_module,
        "inject_ingester_database_dependencies",
        lambda key, extra, db_config: injections.append("database") or extra,
    )
    service = project_ingester_service(
        project_service,
        provider_service=provider_service,
        runtime_settings=settings(tmp_path, **setting_override),
    )

    result = await service.validate_project_tables("sead_change_request", authorized_project(), request())

    assert result.is_valid is False
    assert result.errors
    assert not provider_service.projects
    assert not injections
    assert not calls


@pytest.mark.asyncio
async def test_trusted_config_uses_backend_values_and_only_named_submission_fields(monkeypatch, tmp_path) -> None:
    """The injected config excludes request overrides and uses the authorized project."""
    project_service, calls = install_common_mocks(monkeypatch)
    provider_service = FakeProjectDataProviderService()
    injection_order: list[str] = []

    def inject_runtime(key, extra, configured_settings):  # pylint: disable=unused-argument
        injection_order.append("runtime")
        assert set(extra) == {"target_model", "trusted_project_context", "submission_context", "deploy_strategy"}
        return dict(extra)

    def inject_database(key, extra, db_config):  # pylint: disable=unused-argument
        injection_order.append("database")
        assert db_config == {
            "host": "target-db",
            "port": 5444,
            "dbname": "sead_test",
            "user": "ingester",
        }
        return dict(extra)

    monkeypatch.setattr(project_ingester_module, "inject_ingester_runtime_dependencies", inject_runtime)
    monkeypatch.setattr(project_ingester_module, "inject_ingester_database_dependencies", inject_database)
    FakeTableIngester.instances.clear()
    service = project_ingester_service(
        project_service,
        provider_service=provider_service,
        runtime_settings=settings(tmp_path),
    )

    project_request = request().model_copy(update={"deploy_strategy": "direct"})
    result = await service.validate_project_tables("sead_change_request", authorized_project(), project_request)

    config = FakeTableIngester.instances[-1].config
    assert result.is_valid is True
    assert config.host == "target-db"
    assert config.port == 5444
    assert config.dbname == "sead_test"
    assert config.user == "ingester"
    assert config.output_folder == str(tmp_path / "generated/change-requests")
    assert config.submission_name == "pilot-run"
    assert config.data_types == "mal"
    assert set(config.extra) == {"target_model", "trusted_project_context", "submission_context", "deploy_strategy"}
    assert config.extra["submission_context"]["project_name"] == "pilot"
    assert "scope_name" not in config.extra["submission_context"]
    assert config.extra["deploy_strategy"] == "direct"
    assert config.extra["trusted_project_context"].project_name == "pilot"
    assert injection_order == ["runtime", "database"]
    assert provider_service.projects == [project_service.project]
    assert project_service.loaded == ["pilot"]
    assert calls[0][1][1:4] == (False, False, None)


@pytest.mark.asyncio
async def test_missing_target_model_stops_before_provider_or_normalization(monkeypatch, tmp_path) -> None:
    """A project without a resolved target model cannot start ingester work."""
    project_service, calls = install_common_mocks(monkeypatch)
    provider_service = FakeProjectDataProviderService()
    mapped = core_project(target_model=None)
    monkeypatch.setattr(project_ingester_module.ProjectMapper, "to_core", staticmethod(lambda project: mapped))
    monkeypatch.setattr(
        project_ingester_module,
        "inject_ingester_runtime_dependencies",
        lambda *args: pytest.fail("Runtime injection must not happen for a missing target model"),
    )
    service = project_ingester_service(
        project_service,
        provider_service=provider_service,
        runtime_settings=settings(tmp_path),
    )

    result = await service.validate_project_tables("sead_change_request", authorized_project(), request())

    assert result.is_valid is False
    assert "metadata.target_model" in result.errors[0]
    assert not provider_service.projects
    assert not calls


@pytest.mark.asyncio
async def test_invalid_target_model_stops_before_provider_or_normalization(monkeypatch, tmp_path) -> None:
    """An invalid resolved target model cannot reach provider or runtime services."""
    project_service, calls = install_common_mocks(monkeypatch)
    provider_service = FakeProjectDataProviderService()
    mapped = core_project(target_model={"model": {"name": "missing-version"}})
    monkeypatch.setattr(project_ingester_module.ProjectMapper, "to_core", staticmethod(lambda project: mapped))
    monkeypatch.setattr(
        project_ingester_module,
        "inject_ingester_runtime_dependencies",
        lambda *args: pytest.fail("Runtime injection must not happen for an invalid target model"),
    )
    service = project_ingester_service(
        project_service,
        provider_service=provider_service,
        runtime_settings=settings(tmp_path),
    )

    result = await service.validate_project_tables("sead_change_request", authorized_project(), request())

    assert result.is_valid is False
    assert result.errors
    assert not provider_service.projects
    assert not calls


@pytest.mark.asyncio
async def test_provider_binding_failure_stops_before_runtime_injection(monkeypatch, tmp_path) -> None:
    """A missing registered provider binding cannot reach runtime clients or table work."""
    project_service, calls = install_common_mocks(monkeypatch)
    provider_service = FakeProjectDataProviderService()
    injections: list[str] = []

    def fail_build_context(project: Project) -> TrustedProjectContext:
        raise ProjectDataProviderError("Provider-schema pair is not registered")

    provider_service.build_trusted_context = fail_build_context
    monkeypatch.setattr(
        project_ingester_module,
        "inject_ingester_runtime_dependencies",
        lambda *args: injections.append("runtime") or args[1],
    )
    monkeypatch.setattr(
        project_ingester_module,
        "inject_ingester_database_dependencies",
        lambda *args: injections.append("database") or args[1],
    )
    service = project_ingester_service(
        project_service,
        provider_service=provider_service,
        runtime_settings=settings(tmp_path),
    )

    result = await service.validate_project_tables("sead_change_request", authorized_project(), request())

    assert result.is_valid is False
    assert "not registered" in result.errors[0]
    assert not injections
    assert not calls


@pytest.mark.asyncio
async def test_successful_ingest_writes_only_bundle_under_managed_root(monkeypatch, tmp_path) -> None:
    """The helper passes normalized tables to the real ingester without workbook I/O."""

    project_service, calls = install_common_mocks(monkeypatch, registry_ingester=SeadChangeRequestIngester)
    provider_service = FakeProjectDataProviderService()
    monkeypatch.setattr(
        project_ingester_module,
        "inject_ingester_runtime_dependencies",
        lambda key, extra, configured_settings: dict(extra),
    )
    monkeypatch.setattr(
        project_ingester_module,
        "inject_ingester_database_dependencies",
        lambda key, extra, db_config: dict(extra),
    )
    service = project_ingester_service(
        project_service,
        provider_service=provider_service,
        runtime_settings=settings(tmp_path),
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: pytest.fail("The helper must not read a workbook"))

    validation = await service.validate_project_tables("sead_change_request", authorized_project(), request())
    output_root = tmp_path / "generated/change-requests"
    assert validation.is_valid is True
    assert not output_root.exists()

    result = await service.ingest_project_tables("sead_change_request", authorized_project(), request())

    assert result.success is True
    assert result.records_processed == 0
    assert result.scope_name == "provider://pilot"
    assert result.run_id is not None
    assert result.deploy_artifact is not None
    assert result.output_path is not None
    assert calls[0][0] == "normalize"
    run_folders = [path for path in output_root.iterdir() if path.is_dir()]
    assert len(run_folders) == 1
    bundle_dirs = [path for path in run_folders[0].iterdir() if path.is_dir()]
    assert len(bundle_dirs) == 1
    assert Path(result.output_path).resolve() == bundle_dirs[0].resolve()
    bundle_files = {path.relative_to(bundle_dirs[0]).as_posix() for path in bundle_dirs[0].rglob("*") if path.is_file()}
    assert any(path.startswith("deploy/") for path in bundle_files)
    assert any(path.startswith("revert/") for path in bundle_files)
    assert any(path.startswith("verify/") for path in bundle_files)
    assert "manifest.json" in bundle_files
    assert not any(path.lower().endswith((".xlsx", ".xls")) for path in bundle_files)


class _DirectFkCollisionChecker:
    """Return deterministic target lookup results for saved-project service tests."""

    def __init__(self, existing_id: int) -> None:
        self.existing_id = existing_id

    async def target_id_column_type(self, _table_name: str, _column_name: str) -> str:
        return "integer"

    async def target_id_exists(self, _table_name: str, _column_name: str, target_id: int) -> bool:
        return target_id == self.existing_id

    async def row_exists(self, _table_name: str, _filters: dict[str, object]) -> bool:
        return True


@pytest.mark.asyncio
@pytest.mark.parametrize(("target_id", "expected_valid"), [(42, True), (999, False)])
async def test_saved_direct_fk_map_reaches_validation_and_ingestion_through_real_mapper_and_ingester(
    monkeypatch, tmp_path, target_id, expected_valid
) -> None:
    """Use the saved map in both table methods, accepting only IDs found by target lookup."""
    project = saved_direct_fk_project()
    project_service = FakeProjectService(project)
    provider_service = FakeProjectDataProviderService()
    source_tables = {"location": pd.DataFrame({"location_id": [None], "location_type_id": [target_id]})}
    checker = _DirectFkCollisionChecker(existing_id=42)
    seen_maps: list[dict[str, dict[str, str]]] = []

    class ValidSpecification:
        def __init__(self, _cfg) -> None:
            self.errors: list[str] = []
            self.warnings: list[str] = []

        def is_satisfied_by(self) -> bool:
            return True

    monkeypatch.setattr(project_ingester_module, "CompositeProjectSpecification", ValidSpecification)

    async def normalize(mapped_project, *, translate, drop_foreign_keys, default_entity, env_file):  # pylint: disable=unused-argument
        assert mapped_project.get_table("location").foreign_keys == []
        return SimpleNamespace(table_store=source_tables)

    monkeypatch.setattr(project_ingester_module, "normalize_project", normalize)

    def inject_runtime(key, extra, configured_settings):  # pylint: disable=unused-argument
        seen_maps.append(extra["foreign_key_value_sources"])
        return {
            **extra,
            "identity_assignments": {"location": {0: {"state": "newly_allocated_entity", "target_id": 601}}},
        }

    monkeypatch.setattr(project_ingester_module, "inject_ingester_runtime_dependencies", inject_runtime)

    def inject_database(key, extra, db_config):  # pylint: disable=unused-argument
        return {**extra, "collision_checker": checker}

    monkeypatch.setattr(project_ingester_module, "inject_ingester_database_dependencies", inject_database)
    runtime_settings = settings(tmp_path, INGEST_OUTPUT_DIR=tmp_path / "generated/change-requests")
    service = ProjectIngesterService(
        project_service=project_service,  # type: ignore[arg-type]
        project_data_provider_service=provider_service,  # type: ignore[arg-type]
        settings=runtime_settings,
    )

    validation = await service.validate_project_tables("sead_change_request", authorized_project(), request())
    ingestion = await service.ingest_project_tables("sead_change_request", authorized_project(), request())

    expected_map = {"location": {"location_type": "public_id"}}
    assert validation.is_valid is expected_valid
    assert ingestion.success is expected_valid
    assert seen_maps == [expected_map, expected_map]
    if expected_valid:
        assert ingestion.output_path is not None
        assert ingestion.deploy_artifact is not None
        manifest = json.loads((Path(ingestion.output_path) / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["direct_target_id_foreign_keys"] == [
            {"source_entity": "location", "target_entity": "location_type", "column": "location_type_id"}
        ]
        assert str(target_id) in ingestion.deploy_artifact["deploy_sql"]
    else:
        assert "value 999" in validation.errors[0]
        assert "value 999" in (ingestion.error_details or "")
        output_root = tmp_path / "generated/change-requests"
        assert not output_root.exists() or not list(output_root.glob("**/*"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("value_source", "expected_map"),
    [("system_id", {"location": {"location_type": "system_id"}}), (None, None)],
)
@pytest.mark.parametrize("method_name", ["validate_project_tables", "ingest_project_tables"])
async def test_saved_default_and_explicit_system_id_keep_the_core_link_and_config_shape(
    monkeypatch, tmp_path, value_source, expected_map, method_name
) -> None:
    """Keep the local Core link and omit the config map when the saved project has no declaration."""
    project_service = FakeProjectService(saved_direct_fk_project(value_source=value_source, foreign_keys=[{"entity": "location_type"}]))

    class ValidSpecification:
        def __init__(self, _cfg) -> None:
            self.errors: list[str] = []
            self.warnings: list[str] = []

        def is_satisfied_by(self) -> bool:
            return True

    monkeypatch.setattr(project_ingester_module, "CompositeProjectSpecification", ValidSpecification)

    async def normalize(*_args, **_kwargs):
        return SimpleNamespace(table_store={"location": pd.DataFrame({"location_type_id": [1]})})

    monkeypatch.setattr(project_ingester_module, "normalize_project", normalize)
    monkeypatch.setattr(
        project_ingester_module,
        "get_ingester_registry",
        lambda: FakeRegistry(FakeTableIngester),
    )
    monkeypatch.setattr(project_ingester_module, "inject_ingester_runtime_dependencies", lambda _key, extra, _settings: extra)
    monkeypatch.setattr(project_ingester_module, "inject_ingester_database_dependencies", lambda _key, extra, _config: extra)
    FakeTableIngester.instances.clear()
    FakeTableIngester.validation_result = ValidationResult(is_valid=True)
    FakeTableIngester.ingestion_result = IngestionResult(
        success=True,
        message="bundle generated",
        records_inserted=1,
        scope_name="provider://pilot",
        run_id="run-1",
        deploy_artifact={"deploy_sql": "SELECT 1;"},
    )
    service = project_ingester_service(project_service, runtime_settings=settings(tmp_path))

    result = await getattr(service, method_name)("sead_change_request", authorized_project(), request())

    assert result.is_valid is True if method_name == "validate_project_tables" else result.success is True
    config = FakeTableIngester.instances[-1].config
    if expected_map is None:
        assert "foreign_key_value_sources" not in config.extra
    else:
        assert config.extra["foreign_key_value_sources"] == expected_map
    mapped_project = ProjectMapper.to_core(project_service.project)
    assert mapped_project.get_table("location").foreign_keys


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("columns", "foreign_keys", "expected_code"),
    [
        (["location_type_id"], [{"entity": "location_type"}], "DIRECT_FK_CORE_LINK_CONFLICT"),
        (["location_name"], None, "DIRECT_FK_OUTPUT_COLUMN_MISSING"),
    ],
)
@pytest.mark.parametrize("method_name", ["validate_project_tables", "ingest_project_tables"])
async def test_saved_direct_fk_declaration_errors_stop_before_normalization(
    monkeypatch, tmp_path, columns, foreign_keys, expected_code, method_name
) -> None:
    """Reject direct-mode conflicts and missing output columns before row processing."""
    project_service = FakeProjectService(saved_direct_fk_project(columns=columns, foreign_keys=foreign_keys))

    class ValidSpecification:
        def __init__(self, _cfg) -> None:
            self.errors: list[str] = []
            self.warnings: list[str] = []

        def is_satisfied_by(self) -> bool:
            return True

    monkeypatch.setattr(project_ingester_module, "CompositeProjectSpecification", ValidSpecification)
    monkeypatch.setattr(
        project_ingester_module,
        "normalize_project",
        lambda *args, **kwargs: pytest.fail("Invalid direct declarations must stop before normalization"),
    )
    provider_service = FakeProjectDataProviderService()
    service = ProjectIngesterService(
        project_service=project_service,  # type: ignore[arg-type]
        project_data_provider_service=provider_service,  # type: ignore[arg-type]
        settings=settings(tmp_path),
    )

    result = await getattr(service, method_name)("sead_change_request", authorized_project(), request())
    error_details = result.errors[0] if method_name == "validate_project_tables" else result.error_details

    assert result.is_valid is False if method_name == "validate_project_tables" else result.success is False
    assert error_details is not None
    assert expected_code in error_details
    assert "entity 'location'" in error_details
    if expected_code == "DIRECT_FK_CORE_LINK_CONFLICT":
        assert "field 'foreign_key_value_sources.location_type'" in error_details
    else:
        assert "column 'location_type_id'" in error_details
    assert not provider_service.projects
    output_root = tmp_path / "generated/change-requests"
    assert not output_root.exists() or not list(output_root.glob("**/*"))


@pytest.mark.asyncio
async def test_ingestion_forces_validation_and_does_not_write_after_validation_failure(monkeypatch, tmp_path) -> None:
    """Ingestion calls the table method with validation enabled and maps its failure."""
    project_service, _ = install_common_mocks(monkeypatch)
    FakeTableIngester.instances.clear()
    FakeTableIngester.ingestion_result = IngestionResult(
        success=False,
        message="Validation failed",
        error_details="missing required sample_id",
    )
    service = project_ingester_service(project_service, runtime_settings=settings(tmp_path))

    result = await service.ingest_project_tables("sead_change_request", authorized_project(), request())

    ingester = FakeTableIngester.instances[-1]
    assert result.success is False
    assert result.records_processed == 0
    assert result.error_details == "missing required sample_id"
    assert ingester.ingestion_call is not None
    assert ingester.ingestion_call[2] is True
    assert not list((tmp_path / "generated/change-requests").glob("**/*"))
