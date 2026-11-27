"""Project settings can only make the backend read files in the project's allowed folders.

Each refused case uses a stand-in file. The checks cover the different places in project
settings that can name a file, because a check tied to one settings layout misses the rest.
"""

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

from backend.app.core.config import Settings
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.reconciliation.resolvers import SqlQueryReconciliationSourceResolver
from backend.app.services.shapeshift_service import ShapeShiftService
from backend.app.services.validation_service import ValidationService
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter

# pylint: disable=redefined-outer-name, unused-argument

MARKER = "standinmarker7f3a"
REFUSED = "outside the allowed folders"


def _write_csv(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{value}\n", encoding="utf-8")
    return path


def _write_xlsx(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Sheet1"
    sheet.append(["a"])
    sheet.append([value])
    workbook.save(path)
    return path


def _write_sqlite(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("create table t (a text)")
    connection.execute("insert into t values (?)", (value,))
    connection.commit()
    connection.close()
    return path


@pytest.fixture
def layout(tmp_path: Path):
    """An application folder like the deployed one, plus a folder outside it."""
    app = tmp_path / "app"
    mock = MagicMock(spec=Settings)
    mock.APPLICATION_ROOT = mock.application_root = app
    mock.PROJECTS_DIR = mock.projects_root = app / "projects"
    mock.GLOBAL_DATA_DIR = mock.global_data_dir = app / "shared" / "shared-data"
    mock.GLOBAL_DATA_SOURCE_DIR = mock.global_data_source_dir = app / "shared" / "data-sources"
    mock.GLOBAL_TARGET_MODEL_DIR = mock.global_target_model_dir = app / "shared" / "target-models"
    mock.resolver_allowed_env_vars = frozenset()
    mock.env_prefix = "SHAPE_SHIFTER_"
    mock.env_file = str(tmp_path / "missing.env")
    for folder in (mock.PROJECTS_DIR / "mine", mock.GLOBAL_DATA_DIR, mock.GLOBAL_DATA_SOURCE_DIR, mock.GLOBAL_TARGET_MODEL_DIR):
        folder.mkdir(parents=True)
    (mock.PROJECTS_DIR / "mine" / "shapeshifter.yml").write_text("metadata: {name: mine}\n", encoding="utf-8")

    class Layout:
        settings = mock
        project_file = mock.PROJECTS_DIR / "mine" / "shapeshifter.yml"
        forbidden = {
            "outside the application": _write_csv(tmp_path / "outside" / "stand-in-secret", MARKER),
            "another project": _write_csv(mock.PROJECTS_DIR / "theirs" / "data.csv", MARKER),
            "application credentials": _write_csv(app / ".pgpass", MARKER),
        }
        local_csv = _write_csv(mock.PROJECTS_DIR / "mine" / "local.csv", "from-project")
        shared_csv = _write_csv(mock.GLOBAL_DATA_DIR / "shared.csv", "from-shared")

    with (
        patch("backend.app.mappers.project_mapper.settings", mock),
        patch("backend.app.services.validation_service.get_settings", return_value=mock),
    ):
        yield Layout()


def _api_project(layout, entity: dict[str, Any], options: dict[str, Any] | None = None) -> Project:
    return Project(
        metadata=ProjectMetadata(name="mine", type="shapeshifter-project", entity_count=1, file_path=str(layout.project_file)),
        entities={"e": {"public_id": "e_id", "keys": [], **entity}},
        options=options or {},
    )


async def _load(layout, entity: dict[str, Any], options: dict[str, Any] | None = None) -> str:
    shifter = ShapeShifter(ProjectMapper.to_core(_api_project(layout, entity, options)), target_entities={"e"})
    await shifter.normalize()
    return shifter.table_store["e"].to_csv()


async def _assert_refused(awaitable) -> None:
    with pytest.raises(Exception, match=REFUSED) as error:
        await awaitable
    assert MARKER not in str(error.value)


def _csv_append(path: str) -> dict[str, Any]:
    return {
        "type": "fixed",
        "columns": ["a"],
        "values": [["x"]],
        "append": [{"type": "csv", "columns": ["a"], "options": {"filename": path, "names": ["a"]}}],
    }


@pytest.mark.parametrize("target", ["outside the application", "another project", "application credentials"])
async def test_append_item_cannot_read_a_forbidden_file(layout, target: str) -> None:
    await _assert_refused(_load(layout, _csv_append(str(layout.forbidden[target]))))


async def test_append_item_cannot_use_a_url(layout) -> None:
    await _assert_refused(_load(layout, _csv_append(layout.forbidden["outside the application"].as_uri())))


async def test_append_item_cannot_leave_through_a_symlink(layout) -> None:
    link = layout.settings.GLOBAL_DATA_DIR / "link.csv"
    link.symlink_to(layout.forbidden["outside the application"])
    await _assert_refused(_load(layout, _csv_append(str(link))))


async def test_append_item_cannot_use_a_home_folder_shortcut(layout) -> None:
    await _assert_refused(_load(layout, _csv_append("~/some-file")))


@pytest.mark.parametrize("driver", ["csv", "xlsx", "openpyxl"])
async def test_project_data_source_cannot_read_a_forbidden_file(layout, tmp_path: Path, driver: str) -> None:
    secret = layout.forbidden["outside the application"] if driver == "csv" else _write_xlsx(tmp_path / "outside" / "s.xlsx", MARKER)
    loader_options = {"filename": str(secret)} if driver == "csv" else {"filename": str(secret), "sheet_name": "Sheet1"}
    options = {"data_sources": {"leak": {"driver": driver, "options": loader_options}}}
    entity = {"type": "sql", "columns": ["a"], "data_source": "leak", "query": "unused"}
    await _assert_refused(_load(layout, entity, options))


async def test_referenced_options_cannot_read_a_forbidden_file(layout) -> None:
    options = {"hidden": {"filename": str(layout.forbidden["outside the application"]), "names": ["a"]}}
    await _assert_refused(_load(layout, {"type": "csv", "columns": ["a"], "options": "@value: options.hidden"}, options))


@pytest.mark.parametrize("key", ["filename", "database", "dbname"])
async def test_sqlite_data_source_cannot_open_a_forbidden_database(layout, key: str) -> None:
    database = _write_sqlite(layout.settings.APPLICATION_ROOT / "state" / "authorization.sqlite3", MARKER)
    options = {"data_sources": {"leak": {"driver": "sqlite", key: str(database)}}}
    entity = {"type": "sql", "columns": ["a"], "data_source": "leak", "query": "select a from t"}
    await _assert_refused(_load(layout, entity, options))


async def test_reconciliation_query_cannot_read_a_forbidden_file(layout) -> None:
    options = {"data_sources": {"leak": {"driver": "csv", "options": {"filename": str(layout.forbidden["outside the application"])}}}}
    core = ProjectMapper.to_core(_api_project(layout, {"type": "fixed", "columns": ["a"], "values": [["x"]]}, options))
    mapping = MagicMock()
    mapping.metadata.source = resolution_source = MagicMock(data_source="leak", type="sql", query="unused")
    resolver = SqlQueryReconciliationSourceResolver("mine", core, MagicMock())
    # The resolver currently fails while building its table settings, so that step is replaced here.
    # The file check must still apply once it is repaired.
    with (
        patch("backend.app.services.reconciliation.resolvers.core.ResolutionSource", type(resolution_source)),
        patch("backend.app.services.reconciliation.resolvers.TableConfig", return_value=MagicMock(options={}, source=None)),
    ):
        await _assert_refused(resolver.resolve("e", mapping))


async def test_unsaved_preview_settings_cannot_read_a_forbidden_file(layout) -> None:
    saved = ProjectMapper.to_core(_api_project(layout, {"type": "fixed", "columns": ["a"], "values": [["x"]]}))
    service = ShapeShiftService(project_service=MagicMock())

    async def get_project(_name: str) -> ShapeShiftProject:
        return saved

    service.project_cache.get_project = get_project  # type: ignore[method-assign]
    service.get_project_version = lambda _name: 1  # type: ignore[method-assign]
    override = {"public_id": "e_id", "keys": [], **_csv_append(str(layout.forbidden["outside the application"]))}
    await _assert_refused(service.preview_entity("mine", "e", override_config=override))


def test_clone_and_resolve_keep_the_allowed_folders(layout) -> None:
    core = ProjectMapper.to_core(_api_project(layout, {"type": "fixed", "columns": ["a"], "values": [["x"]]}))
    assert core.file_roots
    assert core.clone().file_roots == core.file_roots
    assert core.resolve().file_roots == core.file_roots


def test_a_project_file_directly_in_the_projects_folder_does_not_allow_all_projects(layout) -> None:
    project = _api_project(layout, {"type": "fixed", "columns": ["a"], "values": [["x"]]})
    assert project.metadata is not None
    project.metadata.file_path = str(layout.settings.PROJECTS_DIR / "mine.yml")
    roots = ProjectMapper.to_core(project).file_roots
    assert roots is not None
    assert layout.settings.PROJECTS_DIR.resolve() not in roots


def test_validation_does_not_open_a_forbidden_load_target(layout) -> None:
    forbidden = layout.forbidden["outside the application"]
    config = {
        "metadata": {"name": "mine"},
        "entities": {"e": {"type": "fixed", "columns": ["a"], "values": f"@load:{forbidden}"}},
        "options": {},
    }
    with patch("src.configuration.resolve.load_data_file") as load_data_file:
        result = ValidationService().validate_project(config, source_path=str(layout.project_file))
    load_data_file.assert_not_called()
    assert not result.is_valid
    assert any("outside the approved data roots" in error.message for error in result.errors)
    assert MARKER not in result.model_dump_json()


def test_validation_still_loads_from_the_project_folder(layout) -> None:
    config = {
        "metadata": {"name": "mine"},
        "entities": {"e": {"type": "fixed", "columns": ["a"], "values": f"@load:{layout.local_csv}"}},
        "options": {},
    }
    result = ValidationService().validate_project(config, source_path=str(layout.project_file))
    assert not any("approved data roots" in error.message for error in result.errors)


@pytest.mark.parametrize("source", ["local_csv", "shared_csv"])
async def test_append_item_can_read_allowed_files(layout, source: str) -> None:
    path: Path = getattr(layout, source)
    assert path.read_text(encoding="utf-8").strip() in await _load(layout, _csv_append(str(path)))


async def test_append_item_can_read_a_local_relative_file(layout) -> None:
    entity = _csv_append("local.csv")
    entity["append"][0]["options"]["location"] = "local"
    assert "from-project" in await _load(layout, entity)


async def test_top_level_local_csv_still_loads(layout) -> None:
    entity = {"type": "csv", "columns": ["a"], "options": {"filename": "local.csv", "location": "local", "names": ["a"]}}
    assert "from-project" in await _load(layout, entity)


@pytest.mark.parametrize("driver", ["xlsx", "openpyxl"])
async def test_shared_excel_data_source_still_loads(layout, driver: str) -> None:
    workbook = _write_xlsx(layout.settings.GLOBAL_DATA_DIR / "book.xlsx", "from-excel")
    options = {"data_sources": {"book": {"driver": driver, "options": {"filename": str(workbook), "sheet_name": "Sheet1"}}}}
    entity = {"type": "sql", "columns": ["a"], "data_source": "book", "query": "unused"}
    assert "from-excel" in await _load(layout, entity, options)


async def test_sqlite_database_in_the_project_folder_still_loads(layout) -> None:
    database = _write_sqlite(layout.settings.PROJECTS_DIR / "mine" / "own.sqlite3", "from-sqlite")
    options = {"data_sources": {"own": {"driver": "sqlite", "filename": str(database)}}}
    entity = {"type": "sql", "columns": ["a"], "data_source": "own", "query": "select a from t"}
    assert "from-sqlite" in await _load(layout, entity, options)


async def test_core_projects_without_allowed_folders_are_not_limited(layout) -> None:
    """The command-line tool builds projects without allowed folders and keeps its behaviour."""
    core = ShapeShiftProject(
        cfg={"entities": {"e": {"public_id": "e_id", "keys": [], **_csv_append(str(layout.forbidden["outside the application"]))}}}
    )
    shifter = ShapeShifter(core, target_entities={"e"})
    await shifter.normalize()
    assert MARKER in shifter.table_store["e"].to_csv()


def test_validation_only_expands_approved_environment_variables(layout, monkeypatch) -> None:
    monkeypatch.setenv("UNAPPROVED_STANDIN", MARKER)
    config = {
        "metadata": {"name": "mine"},
        "entities": {"e": {"type": "fixed", "columns": ["a"], "values": [["${UNAPPROVED_STANDIN}"]]}},
        "options": {},
    }
    with patch("backend.app.services.validation_service.CompositeProjectSpecification") as specification:
        specification.return_value.get_report.return_value = ""
        specification.return_value.errors = []
        specification.return_value.warnings = []
        ValidationService().validate_project(config, source_path=str(layout.project_file))
    assert MARKER not in str(specification.call_args.args[0])
