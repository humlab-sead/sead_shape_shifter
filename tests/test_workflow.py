"""Tests for the shared Core normalization step and the file-writing workflow.

Covers ``normalize_project()`` (no-write, option parity) and ``workflow()``
(preserved file output, shape logging, and ``None`` return) from ``src/workflow.py``.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.workflow import normalize_project, workflow

# pylint: disable=redefined-outer-name


@pytest.fixture
def workflow_project_config() -> dict[str, Any]:
    """Inline project with an FK link, a droppable FK local key, and a translation row.

    - ``parent_ref`` is an extra column used only for linking, so ``drop_foreign_keys`` removes it.
    - ``child_name`` is translated to ``renamed_child_name`` when ``translate`` is enabled.
    """
    return {
        "metadata": {"name": "workflow_test", "version": "1.0.0"},
        "entities": {
            "parent": {
                "type": "fixed",
                "public_id": "parent_id",
                "keys": [],
                "columns": ["system_id", "parent_id", "label"],
                "values": [[1, 10, "Parent A"], [2, 20, "Parent B"]],
            },
            "child": {
                "type": "fixed",
                "public_id": "child_id",
                "keys": [],
                "depends_on": ["parent"],
                "columns": ["system_id", "child_id", "child_name"],
                "values": [[1, None, "first"], [2, None, "second"]],
                "extra_columns": {"parent_ref": 1},
                "foreign_keys": [{"entity": "parent", "local_keys": ["parent_ref"], "remote_keys": ["system_id"]}],
            },
        },
        "options": {
            "translation": [{"arbodat_field": "child_name", "english_column_name": "renamed_child_name"}],
        },
    }


@pytest.fixture
def workflow_project(workflow_project_config: dict[str, Any]) -> ShapeShiftProject:
    """Inline ShapeShiftProject for workflow tests."""
    return ShapeShiftProject(cfg=workflow_project_config)


def capture_tables(shapeshifter: ShapeShifter) -> dict[str, pd.DataFrame]:
    """Deep-copy the current tables of a ShapeShifter for later comparison."""
    return {name: table.copy(deep=True) for name, table in shapeshifter.table_store.items()}


OPTION_COMBINATIONS = [(translate, drop) for translate in (False, True) for drop in (False, True)]


class TestNormalizeProject:
    """No-write behavior and option handling of normalize_project()."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("translate", "drop_foreign_keys"), OPTION_COMBINATIONS)
    async def test_matches_workflow_tables_before_dispatch(
        self, workflow_project: ShapeShiftProject, translate: bool, drop_foreign_keys: bool
    ) -> None:
        """normalize_project returns the same tables workflow passes to store for every option combination."""
        result = await normalize_project(workflow_project, translate=translate, drop_foreign_keys=drop_foreign_keys)
        no_write_tables = capture_tables(result)

        captured: dict[str, dict[str, pd.DataFrame]] = {}

        def capture_store(self: ShapeShifter, target: str, mode: str) -> ShapeShifter:  # pylint: disable=unused-argument
            captured["tables"] = capture_tables(self)
            return self

        with patch.object(ShapeShifter, "store", capture_store), patch.object(ShapeShifter, "log_shapes", Mock()):
            await workflow(
                workflow_project,
                target="unused-target",
                translate=translate,
                target_type="csv",
                drop_foreign_keys=drop_foreign_keys,
            )

        assert set(no_write_tables) == set(captured["tables"])
        for entity, table in no_write_tables.items():
            pd.testing.assert_frame_equal(table, captured["tables"][entity])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("translate", "drop_foreign_keys"), OPTION_COMBINATIONS)
    async def test_options_have_observable_effects(
        self, workflow_project: ShapeShiftProject, translate: bool, drop_foreign_keys: bool
    ) -> None:
        """Each option produces its expected change to the returned tables."""
        result = await normalize_project(workflow_project, translate=translate, drop_foreign_keys=drop_foreign_keys)
        child = result.table_store["child"]

        assert ("parent_ref" in child.columns) == (not drop_foreign_keys)
        assert ("renamed_child_name" in child.columns) == translate
        assert ("child_name" in child.columns) == (not translate)
        # The linked FK column survives both options and holds the parent's system_id values.
        assert "parent_id" in child.columns
        assert child["parent_id"].tolist() == [1, 1]

    @pytest.mark.asyncio
    async def test_translate_without_rows_keeps_columns(self, workflow_project_config: dict[str, Any]) -> None:
        """Translation enabled with no translation rows leaves column names unchanged."""
        workflow_project_config["options"] = {}
        project = ShapeShiftProject(cfg=workflow_project_config)

        result = await normalize_project(project, translate=True, drop_foreign_keys=False)

        assert "child_name" in result.table_store["child"].columns
        assert "renamed_child_name" not in result.table_store["child"].columns

    @pytest.mark.asyncio
    async def test_option_order_and_no_write_calls(self, workflow_project: ShapeShiftProject) -> None:
        """normalize() completes before FK dropping, FK dropping precedes translation, and nothing writes output."""
        calls: list[str] = []
        with patch("src.workflow.ShapeShifter") as shapeshifter_cls:
            instance = shapeshifter_cls.return_value
            instance.normalize = AsyncMock(side_effect=lambda: calls.append("normalize"))
            instance.drop_foreign_key_columns = Mock(side_effect=lambda: calls.append("drop_foreign_key_columns"))
            instance.translate = Mock(side_effect=lambda translations_map: calls.append("translate"))
            instance.store = Mock()
            instance.log_shapes = Mock()

            result = await normalize_project(workflow_project, translate=True, drop_foreign_keys=True, default_entity="child")

        assert calls == ["normalize", "drop_foreign_key_columns", "translate"]
        shapeshifter_cls.assert_called_once_with(project=workflow_project, default_entity="child")
        instance.translate.assert_called_once_with(translations_map={"child_name": "renamed_child_name"})
        assert result is instance
        instance.store.assert_not_called()
        instance.log_shapes.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_project_string_raises(self, tmp_path: Path) -> None:
        """A missing project file path fails in resolve_config before any normalization."""
        missing = str(tmp_path / "does-not-exist.yml")
        with pytest.raises(FileNotFoundError):
            await normalize_project(missing, translate=False, drop_foreign_keys=False)

    @pytest.mark.asyncio
    async def test_string_project_without_env_file_raises(self, tmp_path: Path) -> None:
        """An existing project file path without an environment file fails in resolve_config."""
        project_file = tmp_path / "project.yml"
        project_file.write_text("entities: {}\n", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Environment file not specified"):
            await normalize_project(str(project_file), translate=False, drop_foreign_keys=False)


class TestWorkflowContract:
    """workflow() keeps its file output, shape log, and None return after delegation."""

    @pytest.mark.asyncio
    async def test_workflow_writes_csv_output_and_shape_log(self, workflow_project: ShapeShiftProject, tmp_path: Path) -> None:
        """workflow returns None, writes one CSV per entity, and writes table_shapes.tsv beside the target."""
        target = tmp_path / "out"

        returned = await workflow(
            workflow_project,
            target=str(target),
            translate=False,
            target_type="csv",
            drop_foreign_keys=True,
        )

        assert returned is None
        assert (target / "parent.csv").exists()
        assert (target / "child.csv").exists()

        shapes = pd.read_csv(target / "table_shapes.tsv", sep="\t")
        assert set(shapes["entity"]) == {"parent", "child"}
        expected_rows = {"parent": 2, "child": 2}
        assert dict(zip(shapes["entity"], shapes["num_rows"])) == expected_rows

    @pytest.mark.asyncio
    async def test_workflow_calls_store_then_log_shapes(self, workflow_project: ShapeShiftProject, tmp_path: Path) -> None:
        """workflow stores before logging shapes and returns None."""
        calls: list[str] = []
        with (
            patch.object(ShapeShifter, "store", Mock(side_effect=lambda target, mode: calls.append("store"))),
            patch.object(ShapeShifter, "log_shapes", Mock(side_effect=lambda target: calls.append("log_shapes"))),
        ):
            returned = await workflow(
                workflow_project,
                target=str(tmp_path / "out"),
                translate=True,
                target_type="csv",
                drop_foreign_keys=False,
            )

        assert returned is None
        assert calls == ["store", "log_shapes"]
        # No output was written because store and log_shapes were replaced.
        assert not (tmp_path / "out").exists()

    @pytest.mark.asyncio
    async def test_workflow_rejects_invalid_project_before_output(self, tmp_path: Path) -> None:
        """An invalid project input fails before any output directory is created."""
        target = tmp_path / "out"
        with pytest.raises(FileNotFoundError):
            await workflow(
                str(tmp_path / "missing-project.yml"),
                target=str(target),
                translate=False,
                target_type="csv",
                drop_foreign_keys=False,
            )
        assert not target.exists()
