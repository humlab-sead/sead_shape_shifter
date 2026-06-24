import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from src.loaders.base_loader import LoaderType
from src.model import ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter


def test_global_include_with_relative_env_path_resolves_against_application_root(tmp_path, monkeypatch) -> None:
    """Env-derived include paths should resolve relative to APPLICATION_ROOT."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SHAPE_SHIFTER_APPLICATION_ROOT", raising=False)
    monkeypatch.delenv("SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                'SHAPE_SHIFTER_APPLICATION_ROOT="data"',
                'SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR="shared/data-sources"',
            ]
        ),
        encoding="utf-8",
    )

    shared_dir = tmp_path / "data" / "shared" / "data-sources"
    shared_dir.mkdir(parents=True)
    (shared_dir / "sead-options.yml").write_text("driver: postgresql\n", encoding="utf-8")

    project_dir = tmp_path / "projects" / "project-a"
    project_dir.mkdir(parents=True)
    project_file = project_dir / "shapeshifter.yml"
    project_file.write_text(
        "\n".join(
            [
                "entities: {}",
                "options:",
                "  data_sources:",
                "    sead: '@include: ${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml'",
            ]
        ),
        encoding="utf-8",
    )

    project = ShapeShiftProject.from_file(str(project_file), env_prefix="SHAPE_SHIFTER", env_file=str(env_file))

    assert project.data_sources["sead"]["driver"] == "postgresql"


def test_application_root_env_var_name_is_configurable(tmp_path, monkeypatch) -> None:
    """The runtime root env var name should come from resolution context."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SHAPE_SHIFTER_APPLICATION_ROOT", raising=False)
    monkeypatch.delenv("SHAPE_SHIFTER_DATA_ROOT", raising=False)
    monkeypatch.delenv("SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                'SHAPE_SHIFTER_DATA_ROOT="runtime-data"',
                'SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR="shared/data-sources"',
            ]
        ),
        encoding="utf-8",
    )

    shared_dir = tmp_path / "runtime-data" / "shared" / "data-sources"
    shared_dir.mkdir(parents=True)
    (shared_dir / "sead-options.yml").write_text("driver: postgresql\n", encoding="utf-8")

    project_file = tmp_path / "shapeshifter.yml"
    project_file.write_text(
        "\n".join(
            [
                "entities: {}",
                "options:",
                "  data_sources:",
                "    sead: '@include: ${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml'",
            ]
        ),
        encoding="utf-8",
    )

    project = ShapeShiftProject.from_file(
        str(project_file),
        env_prefix="SHAPE_SHIFTER",
        env_file=str(env_file),
        application_root_env_var="DATA_ROOT",
    )

    assert project.data_sources["sead"]["driver"] == "postgresql"


def test_local_file_loader_resolves_paths_relative_to_project_file() -> None:
    """File-backed entities with location=local should resolve relative to the project file directory."""
    project: ShapeShiftProject = ShapeShiftProject.from_file(
        "./tests/test_data/projects/arbodat/shapeshifter.yml",
        env_prefix="SHAPE_SHIFTER",
        env_file=".env",
    )
    shapeshifter = ShapeShifter(project=project)
    table_cfg: TableConfig = project.get_table("relative_ages")

    expected_path = str(Path("./tests/test_data/projects/arbodat/relative_ages_arbodat_pilot_subset.xlsx").resolve())

    mock_loader = Mock()
    mock_loader.loader_type.return_value = LoaderType.FILE
    mock_loader.load = AsyncMock(return_value=None)

    with patch.object(shapeshifter.loaders, "resolve_loader", return_value=mock_loader):
        asyncio.run(shapeshifter.resolve_source(table_cfg))

    assert table_cfg.options["filename"] == expected_path
    mock_loader.load.assert_awaited_once()
