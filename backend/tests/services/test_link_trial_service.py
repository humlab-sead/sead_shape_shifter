"""Tests for read-only foreign-key link trials."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

from backend.app.core.config import Settings
from backend.app.exceptions import ProjectedBudgetExceeded
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.services.link_baseline_service import LinkBaselineResult
from backend.app.services.link_trial_service import LinkTrialService
from src.model import ForeignKeyConfig, ShapeShiftProject
from src.transforms.link import ForeignKeyLinker


def _python_value(value: Any) -> Any:
    if bool(pd.isna(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def _rows_for_project(frame: pd.DataFrame) -> list[list[Any]]:
    columns: list[str] = [column for column in frame.columns if column != "system_id"]
    return [[_python_value(value) for value in row] for row in frame.loc[:, columns].itertuples(index=False, name=None)]


def make_baseline(
    local_rows: pd.DataFrame,
    remote_rows: pd.DataFrame,
    *,
    local_keys: list[str] | None = None,
    remote_keys: list[str] | None = None,
    how: str | None = "inner",
    omit_how: bool = False,
    constraints: dict[str, Any] | None = None,
    link_pass: str = "initial",
) -> LinkBaselineResult:
    """Build a reproduced baseline context for in-memory trial inputs."""
    saved_local_keys: list[str] = local_keys or [next(column for column in local_rows.columns if column != "system_id")]
    saved_remote_keys: list[str] = remote_keys or [next(column for column in remote_rows.columns if column != "system_id")]
    local_columns: list[str] = [column for column in local_rows.columns if column != "system_id"]
    remote_columns: list[str] = [column for column in remote_rows.columns if column != "system_id"]

    fk_data: dict[str, Any] = {
        "entity": "customers",
        "local_keys": saved_local_keys,
        "remote_keys": saved_remote_keys,
    }
    if not omit_how:
        fk_data["how"] = how
    if constraints is not None:
        fk_data["constraints"] = constraints

    config: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": [local_columns[0]],
                "columns": local_columns,
                "values": _rows_for_project(local_rows),
                "foreign_keys": [fk_data],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": [remote_columns[0]],
                "columns": remote_columns,
                "values": _rows_for_project(remote_rows),
            },
        }
    }
    api_project = ProjectMapper.to_api_config(config, name="link-trial-test")
    saved_project: ShapeShiftProject = ProjectMapper.to_core(api_project)
    fk: ForeignKeyConfig = saved_project.get_table("orders").foreign_keys[0]

    return LinkBaselineResult(
        status="reproduced",
        reason="reproduced",
        message="The test baseline is reproduced.",
        entity_name="orders",
        remote_entity="customers",
        fk_index=0,
        link_pass=link_pass,
        local_rows=local_rows.copy(deep=True),
        remote_rows=remote_rows.copy(deep=True),
        _saved_project=saved_project,
        _foreign_key=fk,
    )


def service_with_limit(limit: int, tmp_path) -> LinkTrialService:
    settings = Settings(
        _env_file=None,
        APPLICATION_ROOT=tmp_path,
        LINK_TRIAL_MAX_OUTPUT_ROWS=limit,
    )  # pyright: ignore[reportCallIssue]
    return LinkTrialService(settings=settings)


def assert_no_trial_data(result) -> None:
    assert result.input_a_rows is None
    assert result.output_rows is None
    assert result.unmatched_a_rows is None
    assert result.multiply_matched_a_rows is None
    assert result.a_rows is None
    assert result.issues == ()


@pytest.mark.parametrize(
    ("how", "expected_output"),
    [
        ("inner", 2),
        ("left", 3),
    ],
)
def test_trial_reports_cancelling_loss_and_expansion(how: str, expected_output: int, tmp_path) -> None:
    local_rows = pd.DataFrame({"customer_code": ["missing", "duplicate"]})
    remote_rows = pd.DataFrame({"system_id": [1, 2], "code": ["duplicate", "duplicate"]})
    baseline = make_baseline(
        local_rows,
        remote_rows,
        local_keys=["customer_code"],
        remote_keys=["code"],
        how=how,
    )

    result = service_with_limit(3, tmp_path).run_trial(
        baseline,
        local_keys=["customer_code"],
        remote_keys=["code"],
    )

    assert result.status == "complete"
    assert result.input_a_rows == 2
    assert result.output_rows == expected_output
    assert result.unmatched_a_rows == 1
    assert result.multiply_matched_a_rows == 1
    assert result.a_rows is not None
    assert [row.output_row_contribution for row in result.a_rows] == ([0, 2] if how == "inner" else [1, 2])
    assert result.a_rows[0].remote_match_count == 0
    assert result.a_rows[1].remote_match_count == 2


@pytest.mark.parametrize(("how", "omit_how"), [(None, False), (None, True)])
def test_trial_treats_missing_join_type_as_inner(how: str | None, omit_how: bool, tmp_path) -> None:
    local_rows = pd.DataFrame({"customer_code": ["matched", "missing"]})
    remote_rows = pd.DataFrame({"system_id": [1], "code": ["matched"]})
    baseline = make_baseline(
        local_rows,
        remote_rows,
        local_keys=["customer_code"],
        remote_keys=["code"],
        how=how,
        omit_how=omit_how,
        constraints={"allow_row_decrease": True},
    )

    result = service_with_limit(10, tmp_path).run_trial(
        baseline,
        local_keys=["customer_code"],
        remote_keys=["code"],
    )

    assert result.status == "complete"
    assert result.output_rows == 1
    assert result.unmatched_a_rows == 1
    assert result.a_rows is not None
    assert [row.output_row_contribution for row in result.a_rows] == [1, 0]


@pytest.mark.parametrize(
    ("null_keys_equal", "expected_output"),
    [
        (False, 1),
        (True, 2),
    ],
)
def test_trial_uses_production_null_policy_for_partial_compound_keys(
    null_keys_equal: bool,
    expected_output: int,
    tmp_path,
) -> None:
    local_rows = pd.DataFrame({"a_type": ["x", "x"], "a_code": [None, "C1"]})
    remote_rows = pd.DataFrame({"system_id": [1, 2], "b_type": ["x", "x"], "b_code": [None, "C1"]})
    baseline = make_baseline(
        local_rows,
        remote_rows,
        local_keys=["a_type", "a_code"],
        remote_keys=["b_type", "b_code"],
        constraints={"allow_null_keys": True, "null_keys_equal": null_keys_equal},
    )

    result = service_with_limit(10, tmp_path).run_trial(
        baseline,
        local_keys=["a_type", "a_code"],
        remote_keys=["b_type", "b_code"],
    )

    assert result.status == "complete"
    assert result.output_rows == expected_output
    assert result.unmatched_a_rows == (1 if null_keys_equal is False else 0)


def test_trial_changes_only_the_ordered_key_pairs_and_preserves_input_state(tmp_path) -> None:
    local_rows = pd.DataFrame({"saved_code": ["old"], "trial_code": ["new"]})
    remote_rows = pd.DataFrame({"system_id": [5], "saved_value": ["old"], "trial_value": ["new"]})
    baseline = make_baseline(
        local_rows,
        remote_rows,
        local_keys=["saved_code"],
        remote_keys=["saved_value"],
        constraints={"allow_row_decrease": True},
    )
    saved_fk = baseline._foreign_key
    assert saved_fk is not None
    saved_fk_data = copy.deepcopy(saved_fk.fk_cfg)
    local_before = baseline.local_rows.copy(deep=True)
    remote_before = baseline.remote_rows.copy(deep=True)
    captured_configs: list[dict[str, Any]] = []
    original_link = ForeignKeyLinker.link_foreign_key

    def capture_trial_fk(linker, local_df, fk, remote_df):
        captured_configs.append(copy.deepcopy(fk.fk_cfg))
        return original_link(linker, local_df, fk, remote_df)

    with patch.object(ForeignKeyLinker, "link_foreign_key", capture_trial_fk):
        result = service_with_limit(10, tmp_path).run_trial(
            baseline,
            local_keys=["trial_code"],
            remote_keys=["trial_value"],
        )

    assert result.status == "complete"
    assert len(captured_configs) == 1
    assert captured_configs[0]["local_keys"] == ["trial_code"]
    assert captured_configs[0]["remote_keys"] == ["trial_value"]
    for key, value in saved_fk_data.items():
        if key not in ("local_keys", "remote_keys"):
            assert captured_configs[0][key] == value
    assert saved_fk.fk_cfg == saved_fk_data
    pd.testing.assert_frame_equal(baseline.local_rows, local_before)
    pd.testing.assert_frame_equal(baseline.remote_rows, remote_before)


@pytest.mark.parametrize(
    ("limit", "remote_count", "expected_status"),
    [
        (3, 2, "complete"),
        (2, 2, "complete"),
        (2, 3, "incomplete"),
    ],
)
@pytest.mark.parametrize("how", ["inner", "left"])
def test_trial_enforces_output_row_limit_before_materializing_merges(
    limit: int,
    remote_count: int,
    expected_status: str,
    how: str,
    tmp_path,
) -> None:
    local_rows = pd.DataFrame({"a": ["K"]})
    remote_rows = pd.DataFrame({"system_id": list(range(remote_count)), "b": ["K"] * remote_count})
    baseline = make_baseline(local_rows, remote_rows, local_keys=["a"], remote_keys=["b"], how=how)
    service = service_with_limit(limit, tmp_path)

    if expected_status == "incomplete":
        with (
            patch.object(ForeignKeyLinker, "link_foreign_key", side_effect=AssertionError("production merge ran")),
            patch(
                "backend.app.services.link_trial_service.merge_with_nonmatching_null_keys",
                side_effect=AssertionError("diagnostic merge ran"),
            ),
        ):
            result = service.run_trial(baseline, local_keys=["a"], remote_keys=["b"])
        assert result.status == "incomplete"
        assert result.reason == "row_limit_exceeded"
        assert_no_trial_data(result)
    else:
        result = service.run_trial(baseline, local_keys=["a"], remote_keys=["b"])
        assert result.status == "complete"
        assert result.output_rows == remote_count


def test_trial_preflight_uses_a_key_weighted_cardinality_not_global_average(tmp_path) -> None:
    local_rows = pd.DataFrame({"a": ["hot", "hot"]})
    remote_rows = pd.DataFrame({"system_id": [1, 2, 3, 4], "b": ["cold", "hot", "hot", "hot"]})
    baseline = make_baseline(local_rows, remote_rows, local_keys=["a"], remote_keys=["b"])

    result = service_with_limit(5, tmp_path).run_trial(baseline, local_keys=["a"], remote_keys=["b"])

    assert result.status == "incomplete"
    assert result.reason == "row_limit_exceeded"
    assert_no_trial_data(result)


@pytest.mark.parametrize(
    ("local_keys", "remote_keys"),
    [
        ([], ["b"]),
        (["missing"], ["b"]),
        (["a", "a"], ["b", "b"]),
        (["a", "other"], ["b"]),
        ([1], ["b"]),
    ],
)
def test_invalid_key_selections_fail_before_linking(local_keys, remote_keys, tmp_path) -> None:
    baseline = make_baseline(pd.DataFrame({"a": ["K"]}), pd.DataFrame({"system_id": [1], "b": ["K"]}))

    with patch.object(ForeignKeyLinker, "link_foreign_key", side_effect=AssertionError("production merge ran")):
        result = service_with_limit(10, tmp_path).run_trial(baseline, local_keys=local_keys, remote_keys=remote_keys)

    assert result.status == "failed"
    assert result.reason == "invalid_keys"
    assert_no_trial_data(result)


def test_non_reproduced_baseline_cannot_run_a_trial(tmp_path) -> None:
    baseline = LinkBaselineResult(
        status="not_reproduced",
        reason="warning_changed",
        message="The warning changed.",
        entity_name="orders",
    )

    result = service_with_limit(10, tmp_path).run_trial(baseline, local_keys=["a"], remote_keys=["b"])

    assert result.status == "failed"
    assert result.reason == "baseline_not_reproduced"
    assert_no_trial_data(result)


@pytest.mark.parametrize(
    ("local_rows", "remote_rows", "how", "constraints"),
    [
        (pd.DataFrame({"a": [None]}), pd.DataFrame({"system_id": [1], "b": ["K"]}), "inner", {"allow_null_keys": False}),
        (
            pd.DataFrame({"a": ["missing"]}),
            pd.DataFrame({"system_id": [1], "b": ["K"]}),
            "left",
            {"allow_unmatched_left": False},
        ),
    ],
)
def test_constraint_violations_fail_without_complete_data(local_rows, remote_rows, how: str, constraints: dict[str, Any], tmp_path) -> None:
    baseline = make_baseline(
        local_rows,
        remote_rows,
        local_keys=["a"],
        remote_keys=["b"],
        how=how,
        constraints=constraints,
    )

    result = service_with_limit(10, tmp_path).run_trial(baseline, local_keys=["a"], remote_keys=["b"])

    assert result.status == "failed"
    assert result.reason == "constraint_violation"
    assert_no_trial_data(result)


def test_incompatible_key_dtypes_return_a_named_failure(tmp_path) -> None:
    local_rows = pd.DataFrame({"a": [1]})
    remote_rows = pd.DataFrame({"system_id": [1], "b": ["not-a-number"]})
    baseline = make_baseline(local_rows, remote_rows, local_keys=["a"], remote_keys=["b"])

    result = service_with_limit(10, tmp_path).run_trial(baseline, local_keys=["a"], remote_keys=["b"])

    assert result.status == "failed"
    assert result.reason == "link_failed"
    assert_no_trial_data(result)


def test_trial_uses_the_baseline_linking_pass_for_findings(tmp_path) -> None:
    local_rows = pd.DataFrame({"a": ["missing"]})
    remote_rows = pd.DataFrame({"system_id": [1], "b": ["K"]})
    baseline = make_baseline(
        local_rows,
        remote_rows,
        local_keys=["a"],
        remote_keys=["b"],
        constraints={"allow_row_decrease": True},
        link_pass="deferred_retry",
    )

    result = service_with_limit(10, tmp_path).run_trial(baseline, local_keys=["a"], remote_keys=["b"])

    assert result.status == "complete"
    assert result.issues
    assert all(issue.metadata.get("link_pass") == "deferred_retry" for issue in result.issues)


def test_baseline_context_fields_are_required_for_trials(tmp_path) -> None:
    baseline = make_baseline(
        pd.DataFrame({"a": ["K"]}),
        pd.DataFrame({"system_id": [1], "b": ["K"]}),
    )
    incomplete = LinkBaselineResult(
        status="reproduced",
        reason="reproduced",
        message="Missing internal context.",
        entity_name="orders",
        local_rows=baseline.local_rows,
        remote_rows=baseline.remote_rows,
    )

    result = service_with_limit(10, tmp_path).run_trial(incomplete, local_keys=["a"], remote_keys=["b"])

    assert result.status == "failed"
    assert result.reason == "baseline_not_reproduced"
    assert_no_trial_data(result)


def minimal_baseline(
    local_rows: pd.DataFrame,
    remote_rows: pd.DataFrame,
    *,
    local_keys: list[str],
    remote_keys: list[str],
    how: str = "inner",
) -> LinkBaselineResult:
    """Build a baseline whose project holds metadata only, so frames can be large."""
    local_columns: list[str] = [column for column in local_rows.columns if column != "system_id"]
    remote_columns: list[str] = [column for column in remote_rows.columns if column != "system_id"]
    config: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "columns": local_columns,
                "values": [local_columns],
                "foreign_keys": [{"entity": "customers", "local_keys": local_keys, "remote_keys": remote_keys, "how": how}],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "columns": remote_columns,
                "values": [remote_columns],
            },
        }
    }
    saved_project = ShapeShiftProject(cfg=config)
    fk: ForeignKeyConfig = saved_project.get_table("orders").foreign_keys[0]
    return LinkBaselineResult(
        status="reproduced",
        reason="reproduced",
        message="The test baseline is reproduced.",
        entity_name="orders",
        remote_entity="customers",
        fk_index=0,
        link_pass="initial",
        local_rows=local_rows.copy(deep=True),
        remote_rows=remote_rows.copy(deep=True),
        _saved_project=saved_project,
        _foreign_key=fk,
    )


def service_with_memory_limit(limit_mb: int, tmp_path) -> LinkTrialService:
    """Build a trial service with the configured memory limit in MiB."""
    settings = Settings(
        _env_file=None,
        APPLICATION_ROOT=tmp_path,
        LINK_EXPERIMENT_MAX_MEMORY_MB=limit_mb,
    )  # pyright: ignore[reportCallIssue]
    return LinkTrialService(settings=settings)


def test_over_budget_retained_inputs_raise_before_any_merge(tmp_path) -> None:
    """Retained inputs above the limit are rejected without running the join."""
    rows = 20_000
    local_rows = pd.DataFrame({"customer_code": ["x" * 40] * rows})
    remote_rows = pd.DataFrame({"system_id": [1], "code": ["x" * 40]})
    baseline = minimal_baseline(local_rows, remote_rows, local_keys=["customer_code"], remote_keys=["code"])

    with patch.object(ForeignKeyLinker, "link_foreign_key") as link:
        with pytest.raises(ProjectedBudgetExceeded) as raised:
            service_with_memory_limit(1, tmp_path).run_trial(baseline, local_keys=["customer_code"], remote_keys=["code"])

    assert raised.value.code == "PROJECTED_BUDGET_EXCEEDED"
    assert raised.value.context["stage"] == "link trial"
    link.assert_not_called()


def test_over_budget_projected_merge_raises_before_the_join(tmp_path) -> None:
    """A duplicate-key expansion above the limit is rejected before materializing it."""
    local_rows = pd.DataFrame({"customer_code": ["same"] * 500})
    remote_rows = pd.DataFrame({"system_id": range(500), "code": ["same"] * 500})
    baseline = minimal_baseline(local_rows, remote_rows, local_keys=["customer_code"], remote_keys=["code"])

    with patch.object(ForeignKeyLinker, "link_foreign_key") as link:
        with pytest.raises(ProjectedBudgetExceeded):
            service_with_memory_limit(1, tmp_path).run_trial(baseline, local_keys=["customer_code"], remote_keys=["code"])

    link.assert_not_called()


def test_trial_completes_when_the_projection_fits_the_limit(tmp_path) -> None:
    """The same inputs complete under a limit that covers the projected peak."""
    local_rows = pd.DataFrame({"customer_code": ["same"] * 50})
    remote_rows = pd.DataFrame({"system_id": range(50), "code": ["same"] * 50})
    baseline = minimal_baseline(local_rows, remote_rows, local_keys=["customer_code"], remote_keys=["code"])

    result = service_with_memory_limit(100, tmp_path).run_trial(baseline, local_keys=["customer_code"], remote_keys=["code"])

    assert result.status == "complete"
    assert result.output_rows == 2500
