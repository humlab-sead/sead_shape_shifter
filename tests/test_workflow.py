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

        assert result.output_expectation_evaluation is None
        assert ("parent_ref" in child.columns) == (not drop_foreign_keys)
        assert ("renamed_child_name" in child.columns) == translate
        assert ("child_name" in child.columns) == (not translate)
        # The linked FK column survives both options and holds the parent's system_id values.
        assert "parent_id" in child.columns
        assert child["parent_id"].tolist() == [1, 1]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("translate", "drop_foreign_keys"), OPTION_COMBINATIONS)
    async def test_evaluates_expectations_before_optional_output_transformations(
        self, workflow_project: ShapeShiftProject, translate: bool, drop_foreign_keys: bool
    ) -> None:
        """Metrics use normalized columns before foreign-key removal and translation."""
        workflow_project.cfg["options"]["output_expectations"] = [
            {
                "name": "children-by-name",
                "entity": "child",
                "metric": "grouped_row_count",
                "column": "child_name",
                "groups": {"first": {"equals": 1}, "second": {"equals": 1}},
            }
        ]

        result = await normalize_project(
            workflow_project,
            translate=translate,
            drop_foreign_keys=drop_foreign_keys,
            check_output_expectations=True,
        )

        evaluation = result.output_expectation_evaluation
        assert evaluation is not None
        assert evaluation.passed is True
        assert [(item.group_value, item.measured_value) for item in evaluation.results] == [("first", 1), ("second", 1)]
        child = result.table_store["child"]
        assert ("renamed_child_name" in child.columns) is translate
        assert ("child_name" in child.columns) is (not translate)
        assert ("parent_ref" in child.columns) is (not drop_foreign_keys)

    @pytest.mark.asyncio
    async def test_incomplete_expected_entity_has_no_measurement(self, workflow_project: ShapeShiftProject) -> None:
        """Evaluation records incomplete entities instead of measuring a partial table."""
        workflow_project.cfg["options"]["output_expectations"] = [
            {"name": "child-count", "entity": "child", "metric": "row_count", "equals": 2}
        ]

        with patch("src.workflow.ShapeShifter") as shapeshifter_cls:
            instance = shapeshifter_cls.return_value
            instance.table_store = {"parent": pd.DataFrame({"label": ["Parent A"]})}
            instance.incomplete_entities = {"child": "source query failed"}
            instance.normalize = AsyncMock()

            result = await normalize_project(
                workflow_project,
                translate=False,
                drop_foreign_keys=False,
                check_output_expectations=True,
            )

        instance.normalize.assert_awaited_once_with(continue_on_error=True)
        assert result.output_expectation_evaluation is not None
        assert result.output_expectation_evaluation.passed is False
        failed_result = result.output_expectation_evaluation.results[0]
        assert failed_result.measured_value is None
        assert failed_result.status == "fail"
        assert "source query failed" in (failed_result.failure_reason or "")

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
    """workflow() keeps its file output and returns results only when expectations are configured."""

    @pytest.mark.asyncio
    async def test_invalid_output_expectations_stop_before_normalization(self, workflow_project_config: dict[str, Any]) -> None:
        """Invalid declarations fail before the full workflow starts normalization."""
        workflow_project_config["options"]["output_expectations"] = [
            {"name": "missing-site", "entity": "missing", "metric": "row_count", "equals": 0}
        ]
        project = ShapeShiftProject(cfg=workflow_project_config)
        normalize = AsyncMock()

        with patch("src.workflow.normalize_project", normalize):
            with pytest.raises(ValueError, match="Invalid output expectation declarations"):
                await workflow(
                    project,
                    target="unused-target",
                    translate=False,
                    target_type="csv",
                    drop_foreign_keys=False,
                )

        normalize.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_valid_output_expectation_declaration_allows_workflow(self, workflow_project: ShapeShiftProject) -> None:
        """A valid declaration leaves the existing normalize-and-store flow available."""
        workflow_project.cfg["options"]["output_expectations"] = [
            {"name": "child-count", "entity": "child", "metric": "row_count", "min": 1, "max": 2}
        ]
        normalized = Mock()
        evaluation = Mock()
        evaluation.passed = True
        normalized.output_expectation_evaluation = evaluation
        normalized.incomplete_entities = {}
        normalize = AsyncMock(return_value=normalized)

        with patch("src.workflow.normalize_project", normalize):
            returned = await workflow(
                workflow_project,
                target="unused-target",
                translate=False,
                target_type="csv",
                drop_foreign_keys=False,
            )

        normalize.assert_awaited_once()
        call_args = normalize.await_args
        assert call_args is not None
        assert call_args.kwargs["check_output_expectations"] is True
        normalized.store.assert_called_once_with(target="unused-target", mode="csv")
        assert returned is evaluation

    @pytest.mark.asyncio
    async def test_failed_expectations_prevent_store_and_shape_log(self, workflow_project: ShapeShiftProject, tmp_path: Path) -> None:
        """Every failing result is returned and neither writer runs."""
        workflow_project.cfg["options"]["output_expectations"] = [
            {"name": "parent-count", "entity": "parent", "metric": "row_count", "equals": 99},
            {"name": "child-count", "entity": "child", "metric": "row_count", "equals": 99},
            {
                "name": "children-by-name",
                "entity": "child",
                "metric": "grouped_row_count",
                "column": "child_name",
                "groups": {"first": {"equals": 1}, "second": {"equals": 1}},
            },
        ]
        target = tmp_path / "out"

        with (
            patch.object(ShapeShifter, "store", Mock()) as store,
            patch.object(ShapeShifter, "log_shapes", Mock()) as log_shapes,
        ):
            returned = await workflow(
                workflow_project,
                target=str(target),
                translate=False,
                target_type="csv",
                drop_foreign_keys=False,
            )

        assert returned is not None
        assert returned.passed is False
        assert [result.name for result in returned.results] == [
            "parent-count",
            "child-count",
            "children-by-name",
            "children-by-name",
        ]
        assert [result.status for result in returned.results] == ["fail", "fail", "pass", "pass"]
        store.assert_not_called()
        log_shapes.assert_not_called()
        assert not target.exists()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("translate", "drop_foreign_keys"), OPTION_COMBINATIONS)
    async def test_failed_expectations_prevent_write_with_output_transformations(
        self, workflow_project: ShapeShiftProject, translate: bool, drop_foreign_keys: bool, tmp_path: Path
    ) -> None:
        """Optional output transformations cannot allow output after a failed check."""
        workflow_project.cfg["options"]["output_expectations"] = [
            {"name": "child-count", "entity": "child", "metric": "row_count", "equals": 99}
        ]
        target = tmp_path / "out"

        with (
            patch.object(ShapeShifter, "store", Mock()) as store,
            patch.object(ShapeShifter, "log_shapes", Mock()) as log_shapes,
        ):
            returned = await workflow(
                workflow_project,
                target=str(target),
                translate=translate,
                target_type="csv",
                drop_foreign_keys=drop_foreign_keys,
            )

        assert returned is not None
        assert returned.passed is False
        store.assert_not_called()
        log_shapes.assert_not_called()
        assert not target.exists()

    @pytest.mark.asyncio
    async def test_incomplete_expected_entity_prevents_write(self, workflow_project: ShapeShiftProject) -> None:
        """An expected entity that did not finish normalization blocks both writers."""
        workflow_project.cfg["options"]["output_expectations"] = [
            {"name": "child-count", "entity": "child", "metric": "row_count", "equals": 2}
        ]

        with patch("src.workflow.ShapeShifter") as shapeshifter_cls:
            instance = shapeshifter_cls.return_value
            instance.table_store = {"parent": pd.DataFrame({"label": ["Parent A"]})}
            instance.incomplete_entities = {"child": "source query failed"}
            instance.normalize = AsyncMock()
            instance.store = Mock()
            instance.log_shapes = Mock()

            returned = await workflow(
                workflow_project,
                target="unused-target",
                translate=False,
                target_type="csv",
                drop_foreign_keys=False,
            )

        assert returned is not None
        assert returned.passed is False
        assert returned.results[0].measured_value is None
        assert "source query failed" in (returned.results[0].failure_reason or "")
        instance.store.assert_not_called()
        instance.log_shapes.assert_not_called()

    @pytest.mark.asyncio
    async def test_unconfigured_incomplete_entity_fails_before_dispatch(self, workflow_project: ShapeShiftProject) -> None:
        """A partial run fails even when every configured check passes."""
        workflow_project.cfg["options"]["output_expectations"] = [
            {"name": "parent-count", "entity": "parent", "metric": "row_count", "equals": 2}
        ]

        with patch("src.workflow.ShapeShifter") as shapeshifter_cls:
            instance = shapeshifter_cls.return_value
            instance.table_store = {"parent": pd.DataFrame({"label": ["a", "b"]})}
            instance.incomplete_entities = {"child": "source query failed"}
            instance.normalize = AsyncMock()
            instance.store = Mock()
            instance.log_shapes = Mock()

            with pytest.raises(ValueError, match="incomplete"):
                await workflow(
                    workflow_project,
                    target="unused-target",
                    translate=False,
                    target_type="csv",
                    drop_foreign_keys=False,
                )

        instance.store.assert_not_called()
        instance.log_shapes.assert_not_called()

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
