import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from src.loaders.base_loader import LoaderType
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter


def test_local_file_loader_resolves_paths_relative_to_project_file() -> None:
    """File-backed entities with location=local should resolve relative to the project file directory."""
    project = ShapeShiftProject.from_file(
        "./data/projects/arbodat/shapeshifter.yml",
        env_prefix="SHAPE_SHIFTER",
        env_file=".env",
    )
    shapeshifter = ShapeShifter(project=project)
    table_cfg = project.get_table("relative_ages")

    expected_path = str(Path("./data/projects/arbodat/relative_ages_arbodat_pilot_subset.xlsx").resolve())

    mock_loader = Mock()
    mock_loader.loader_type.return_value = LoaderType.FILE
    mock_loader.load = AsyncMock(return_value=None)

    with patch.object(shapeshifter, "resolve_loader", return_value=mock_loader):
        asyncio.run(shapeshifter.resolve_source(table_cfg))

    assert table_cfg.options["filename"] == expected_path
    mock_loader.load.assert_awaited_once()