"""Tests for the read-only foreign-key integrity inspection service."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.integrity_troubleshooter import encode_key_token
from backend.app.models.project import Project
from backend.app.services.integrity_troubleshooter_service import (
    COLUMN_LIMIT,
    ROW_SAMPLE_LIMIT,
    VALUE_PAGE_SIZE,
    IntegrityTroubleshooterService,
)
from src.model import ForeignKeyConfig, ShapeShiftProject
from src.normalizer import ShapeShifter
from src.table_store import TableStore
from src.validators.data_validators import ForeignKeyIntegrityValidator

# pylint: disable=redefined-outer-name

PROJECT_NAME = "integrity-probe"

BASE_CFG: dict[str, Any] = {
    "entities": {
        "orders": {
            "type": "fixed",
            "public_id": "order_id",
            "keys": ["order_code"],
            "columns": ["order_code", "customer_code", "site"],
            "values": [
                ["O1", "C1", "A"],
                ["O2", "missing", "B"],
                ["O3", "missing", "C"],
                ["O4", "other", "D"],
            ],
            "foreign_keys": [
                {"entity": "customers", "local_keys": ["customer_code"], "remote_keys": ["code"], "how": "left"},
            ],
        },
        "customers": {
            "type": "fixed",
            "public_id": "customer_id",
            "keys": ["code"],
            "columns": ["code", "name"],
            "values": [["C1", "Alpha"]],
        },
    }
}

LOCAL_COLUMNS = ["order_code", "customer_code", "site"]


class StubProjectService:
    """Project service double that returns one in-memory API project."""

    def __init__(self, api_project: Project) -> None:
        self._api_project: Project = api_project

    def load_project(self, name: str, force_reload: bool = False) -> Project:  # pylint: disable=unused-argument
        """Return the prepared API project."""
        return self._api_project


@dataclass
class FrameSource:
    """Local and remote frames returned by a patched normalization step."""

    local: pd.DataFrame
    remote: pd.DataFrame


def build_api_project(cfg: dict[str, Any], *, name: str = PROJECT_NAME) -> Project:
    """Build an API project from a core configuration dictionary."""
    return ProjectMapper.to_api_config(cfg, name=name)


def build_saved_project(cfg: dict[str, Any]) -> ShapeShiftProject:
    """Build a resolved Core project from a core configuration dictionary."""
    return ProjectMapper.to_core(build_api_project(cfg))


def service_for(api_project: Project) -> IntegrityTroubleshooterService:
    """Build an integrity service over one in-memory API project."""
    return IntegrityTroubleshooterService(project_service=StubProjectService(api_project))  # type: ignore[arg-type]


def metadata_for(saved_project: ShapeShiftProject, *, local_entity: str = "orders", index: int = 0, count: int) -> dict[str, Any]:
    """Build warning metadata that matches the saved foreign key at the given index."""
    fk: ForeignKeyConfig = saved_project.get_table(local_entity).foreign_keys[index]
    return {"fk_index": fk.fk_index, "fk_signature": fk.identity_signature, "orphan_count": count}


def patch_frames(monkeypatch, service: IntegrityTroubleshooterService, source: FrameSource) -> None:
    """Replace the private normalization step with fixed in-memory frames."""

    async def fake_frames(_saved_project: ShapeShiftProject, _fk: ForeignKeyConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
        return source.local.copy(), source.remote.copy()

    monkeypatch.setattr(service, "_normalize_frames", fake_frames)


def local_frame(customer_codes: list[Any], *, order_codes: list[str] | None = None) -> pd.DataFrame:
    """Build a local frame with the configured columns."""
    orders = order_codes if order_codes is not None else [f"O{index:03d}" for index in range(len(customer_codes))]
    return pd.DataFrame({"order_code": orders, "customer_code": customer_codes, "site": ["A"] * len(customer_codes)})


def remote_frame(codes: list[Any]) -> pd.DataFrame:
    """Build a remote frame with the configured columns."""
    return pd.DataFrame({"code": codes, "name": [f"N{index}" for index in range(len(codes))]})


async def normalize_once(api_project: Project) -> tuple[ShapeShiftProject, ShapeShifter]:
    """Run the private full normalization used by the service."""
    saved_project = ProjectMapper.to_core(api_project)
    normalizer = ShapeShifter(project=saved_project.clone(), table_store=TableStore())
    await normalizer.normalize()
    return saved_project, normalizer


@pytest.mark.asyncio
async def test_reproduces_and_matches_the_validator_on_full_normalization():
    """A current full-data count equal to the warning reproduces and matches the validator."""
    api_project = build_api_project(BASE_CFG)
    saved_project, normalizer = await normalize_once(api_project)

    fk: ForeignKeyConfig = saved_project.get_table("orders").foreign_keys[0]
    local_df = normalizer.table_store["orders"]
    remote_df = normalizer.table_store["customers"]
    issues = ForeignKeyIntegrityValidator.validate(local_df, remote_df, fk.fk_cfg, "orders")
    assert issues and issues[0].code == "FK_DATA_INTEGRITY"
    expected_count: int = issues[0].metadata["orphan_count"]
    assert expected_count == 2

    service = service_for(api_project)
    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=expected_count),
    )

    assert result.status == "reproduced"
    assert result.reason == "reproduced"
    assert result.source == "current full normalization"
    assert result.current_orphan_count == expected_count
    assert result.recorded_orphan_count == expected_count
    assert result.values is not None
    assert result.values.distinct_value_count == expected_count
    assert result.relationship is not None and result.relationship.remote_entity == "customers"
    assert result.configured_keys is not None and result.configured_keys.local_keys == ["customer_code"]


@pytest.mark.asyncio
async def test_changed_count_is_not_reproduced(monkeypatch):
    """A current count that differs from the warning is reported as changed."""
    saved_project = build_saved_project(BASE_CFG)
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(
        monkeypatch,
        service,
        FrameSource(local=local_frame(["A", "B", "C1"]), remote=remote_frame(["C1"])),
    )

    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=5),
    )

    assert result.status == "not_reproduced"
    assert result.reason == "count_changed"
    assert result.recorded_orphan_count == 5
    assert result.current_orphan_count == 2


@pytest.mark.asyncio
async def test_equal_count_with_changed_values_stays_current(monkeypatch):
    """Count equality reproduces while each result shows its own current value set."""
    saved_project = build_saved_project(BASE_CFG)
    metadata = metadata_for(saved_project, count=2)

    first_service = service_for(build_api_project(BASE_CFG))
    patch_frames(monkeypatch, first_service, FrameSource(local=local_frame(["A", "B"]), remote=remote_frame(["C1"])))
    first = await first_service.inspect(project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata)

    second_service = service_for(build_api_project(BASE_CFG))
    patch_frames(monkeypatch, second_service, FrameSource(local=local_frame(["X", "Y"]), remote=remote_frame(["C1"])))
    second = await second_service.inspect(
        project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata
    )

    assert first.status == second.status == "reproduced"
    assert first.current_orphan_count == second.current_orphan_count == 2
    assert first.values is not None and [value.key_values for value in first.values.values] == [["A"], ["B"]]
    assert second.values is not None and [value.key_values for value in second.values.values] == [["X"], ["Y"]]


@pytest.mark.asyncio
async def test_missing_orphan_count_is_not_reproduced():
    """A warning without an integer count cannot claim reproduction."""
    saved_project = build_saved_project(BASE_CFG)
    service = service_for(build_api_project(BASE_CFG))

    metadata = metadata_for(saved_project, count=2)
    metadata.pop("orphan_count")

    result = await service.inspect(project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata)

    assert result.status == "not_reproduced"
    assert result.reason == "missing_warning_count"
    assert result.current_orphan_count is None


@pytest.mark.asyncio
async def test_boolean_orphan_count_is_not_treated_as_an_integer():
    """A boolean count is rejected because it is not a real count."""
    saved_project = build_saved_project(BASE_CFG)
    service = service_for(build_api_project(BASE_CFG))
    metadata = metadata_for(saved_project, count=2)
    metadata["orphan_count"] = True

    result = await service.inspect(project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata)

    assert result.status == "not_reproduced"
    assert result.reason == "missing_warning_count"


@pytest.mark.asyncio
async def test_missing_metadata_is_ineligible():
    """A warning without saved-link identity cannot be inspected."""
    service = service_for(build_api_project(BASE_CFG))

    result = await service.inspect(project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata={})

    assert result.status == "ineligible"
    assert result.reason == "missing_metadata"
    assert result.current_orphan_count is None


@pytest.mark.asyncio
async def test_stale_signature_is_ineligible():
    """A signature that no longer matches the saved entry is refused by name."""
    saved_project = build_saved_project(BASE_CFG)
    service = service_for(build_api_project(BASE_CFG))
    metadata = metadata_for(saved_project, count=2)
    metadata["fk_signature"] = "stale-signature"

    result = await service.inspect(project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata)

    assert result.status == "ineligible"
    assert result.reason == "signature_mismatch"


@pytest.mark.asyncio
async def test_empty_remote_is_not_reproduced(monkeypatch):
    """An empty remote key reports a named non-reproduction, not an empty success."""
    saved_project = build_saved_project(BASE_CFG)
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(monkeypatch, service, FrameSource(local=local_frame(["A"]), remote=remote_frame([])))

    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=1),
    )

    assert result.status == "not_reproduced"
    assert result.reason == "remote_empty"


@pytest.mark.asyncio
async def test_missing_column_is_not_reproduced(monkeypatch):
    """A frame missing a configured key column is invalid input, not a clean result."""
    saved_project = build_saved_project(BASE_CFG)
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(
        monkeypatch,
        service,
        FrameSource(local=pd.DataFrame({"order_code": ["O1"]}), remote=remote_frame(["C1"])),
    )

    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=1),
    )

    assert result.status == "not_reproduced"
    assert result.reason == "invalid_input"


@pytest.mark.asyncio
async def test_clean_link_is_not_reproduced_with_zero_count(monkeypatch):
    """A link with no unmatched values reports zero current values and no reproduction."""
    saved_project = build_saved_project(BASE_CFG)
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(monkeypatch, service, FrameSource(local=local_frame(["C1"]), remote=remote_frame(["C1"])))

    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=2),
    )

    assert result.status == "not_reproduced"
    assert result.reason == "no_unmatched_values"
    assert result.current_orphan_count == 0
    assert result.values is not None and result.values.distinct_value_count == 0


@pytest.mark.asyncio
async def test_value_pages_are_deterministic_and_bounded(monkeypatch):
    """Every distinct value is reachable by ordered pages of the fixed page size."""
    saved_project = build_saved_project(BASE_CFG)
    codes = [f"V{index:03d}" for index in range(VALUE_PAGE_SIZE + 5)]
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(monkeypatch, service, FrameSource(local=local_frame(codes), remote=remote_frame(["C1"])))
    metadata = metadata_for(saved_project, count=len(codes))

    first = await service.inspect(
        project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata, page=1
    )
    second = await service.inspect(
        project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata, page=2
    )
    beyond = await service.inspect(
        project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata, page=3
    )

    assert first.values is not None
    assert first.values.page_size == VALUE_PAGE_SIZE
    assert first.values.distinct_value_count == len(codes)
    assert first.values.returned_value_count == VALUE_PAGE_SIZE
    assert first.values.has_next is True
    assert [value.key_values for value in first.values.values] == [[f"V{index:03d}"] for index in range(VALUE_PAGE_SIZE)]

    assert second.values is not None
    assert second.values.returned_value_count == 5
    assert second.values.has_next is False
    assert [value.key_values for value in second.values.values] == [[f"V{index:03d}"] for index in range(VALUE_PAGE_SIZE, len(codes))]

    assert beyond.values is not None
    assert beyond.values.returned_value_count == 0
    assert beyond.values.has_next is False


@pytest.mark.asyncio
async def test_values_report_local_row_counts(monkeypatch):
    """Each distinct value reports how many local rows carry it before deduplication."""
    saved_project = build_saved_project(BASE_CFG)
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(
        monkeypatch,
        service,
        FrameSource(local=local_frame(["A", "A", "B", "C1"]), remote=remote_frame(["C1"])),
    )

    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=2),
    )

    assert result.values is not None
    counts = {tuple(value.key_values): value.local_row_count for value in result.values.values}
    assert counts == {("A",): 2, ("B",): 1}


@pytest.mark.asyncio
async def test_selected_rows_are_bounded_and_ordered(monkeypatch):
    """A selected value returns at most the row sample limit with deterministic rows."""
    saved_project = build_saved_project(BASE_CFG)
    count = ROW_SAMPLE_LIMIT + 5
    local = local_frame(["A"] * count)
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(monkeypatch, service, FrameSource(local=local, remote=remote_frame(["C1"])))

    token = encode_key_token(("A",))
    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=1),
        selected_value_token=token,
    )

    assert result.selected is not None
    assert result.selected.status == "selected"
    assert result.selected.total_row_count == count
    assert result.selected.returned_row_count == ROW_SAMPLE_LIMIT
    assert len(result.selected.rows) == ROW_SAMPLE_LIMIT
    assert result.selected.rows[0]["order_code"] == "O000"


@pytest.mark.asyncio
async def test_selected_rows_respect_the_column_cap_and_report_truncation(monkeypatch):
    """Returned columns are the FK key, business keys, and target-facing columns, capped."""
    wide_cfg = copy.deepcopy(BASE_CFG)
    extra_columns = [f"detail_{index}" for index in range(COLUMN_LIMIT + 5)]
    wide_cfg["entities"]["orders"]["columns"] = ["order_code", "customer_code"] + extra_columns
    wide_cfg["entities"]["orders"]["values"] = [["O1", "A"] + [f"D{index}" for index in range(len(extra_columns))]]
    saved_project = build_saved_project(wide_cfg)

    local = pd.DataFrame({"order_code": ["O1"], "customer_code": ["A"], **{column: ["x"] for column in extra_columns}})
    service = service_for(build_api_project(wide_cfg))
    patch_frames(monkeypatch, service, FrameSource(local=local, remote=remote_frame(["C1"])))

    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=1),
        selected_value_token=encode_key_token(("A",)),
    )

    assert result.selected is not None
    assert result.selected.status == "selected"
    assert len(result.selected.columns) == COLUMN_LIMIT
    assert result.selected.columns[0] == "customer_code"
    assert result.selected.columns[1] == "order_code"
    assert result.selected.columns_truncated is True
    assert set(result.selected.rows[0]) == set(result.selected.columns)


@pytest.mark.asyncio
async def test_excess_key_columns_refuse_the_row_sample(monkeypatch):
    """A link whose keys alone exceed the column cap refuses the row sample by name."""
    key_columns = [f"k{index}" for index in range(COLUMN_LIMIT + 1)]
    remote_keys = [f"r{index}" for index in range(COLUMN_LIMIT + 1)]

    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code"] + key_columns,
                "values": [["O1"] + ["x"] * len(key_columns)],
                "foreign_keys": [{"entity": "customers", "local_keys": key_columns, "remote_keys": remote_keys, "how": "left"}],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": remote_keys,
                "columns": remote_keys + ["name"],
                "values": [["y"] * len(remote_keys) + ["N"]],
            },
        }
    }
    saved_project = build_saved_project(cfg)

    local = pd.DataFrame({"order_code": ["O1"], **{column: ["x"] for column in key_columns}})
    remote = pd.DataFrame({**{column: ["y"] for column in remote_keys}, "name": ["N"]})
    service = service_for(build_api_project(cfg))
    patch_frames(monkeypatch, service, FrameSource(local=local, remote=remote))

    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=1),
        selected_value_token=encode_key_token(tuple("x" for _ in key_columns)),
    )

    assert result.selected is not None
    assert result.selected.status == "unavailable"
    assert result.selected.reason == "too_many_key_columns"
    assert result.selected.rows == []


@pytest.mark.asyncio
async def test_selection_uses_the_token_not_a_page_position(monkeypatch):
    """A token obtained from a later page still selects the same value's rows."""
    saved_project = build_saved_project(BASE_CFG)
    codes = [f"V{index:03d}" for index in range(VALUE_PAGE_SIZE + 3)]
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(monkeypatch, service, FrameSource(local=local_frame(codes), remote=remote_frame(["C1"])))

    page_two = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=len(codes)),
        page=2,
    )

    assert page_two.values is not None and page_two.values.values
    chosen = page_two.values.values[1]
    selected = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=len(codes)),
        page=2,
        selected_value_token=chosen.token,
    )

    assert selected.selected is not None
    assert selected.selected.status == "selected"
    assert selected.selected.key_values == chosen.key_values
    assert selected.selected.rows[0]["customer_code"] == chosen.key_values[0]


@pytest.mark.asyncio
async def test_selected_value_that_became_matched_is_unavailable(monkeypatch):
    """A token whose value no longer matches is refused with no stale rows."""
    saved_project = build_saved_project(BASE_CFG)
    metadata = metadata_for(saved_project, count=1)
    source = FrameSource(local=local_frame(["A"]), remote=remote_frame(["C1"]))
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(monkeypatch, service, source)

    first = await service.inspect(project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata)
    assert first.values is not None and first.values.values
    token = first.values.values[0].token

    source.remote = remote_frame(["A"])
    second = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=1),
        selected_value_token=token,
    )

    assert second.selected is not None
    assert second.selected.status == "unavailable"
    assert second.selected.reason == "value_no_longer_unmatched"
    assert second.selected.rows == []


@pytest.mark.asyncio
async def test_malformed_token_is_unavailable(monkeypatch):
    """A malformed token yields an explicit selection result, not an error or stale rows."""
    saved_project = build_saved_project(BASE_CFG)
    service = service_for(build_api_project(BASE_CFG))
    patch_frames(monkeypatch, service, FrameSource(local=local_frame(["A"]), remote=remote_frame(["C1"])))

    result = await service.inspect(
        project_name=PROJECT_NAME,
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=metadata_for(saved_project, count=1),
        selected_value_token="not-a-valid-token",
    )

    assert result.selected is not None
    assert result.selected.status == "unavailable"
    assert result.selected.reason == "invalid_token"


@pytest.mark.asyncio
async def test_null_and_mixed_type_tokens_round_trip(monkeypatch):
    """Null and mixed scalar key values keep their type through the token."""
    cfg = copy.deepcopy(BASE_CFG)
    cfg["entities"]["orders"]["foreign_keys"][0]["constraints"] = {"null_keys_equal": True}
    saved_project = build_saved_project(cfg)
    service = service_for(build_api_project(cfg))
    patch_frames(
        monkeypatch,
        service,
        FrameSource(local=local_frame([None, 7, "C1"]), remote=remote_frame(["C1"])),
    )
    metadata = metadata_for(saved_project, count=2)

    page = await service.inspect(project_name=PROJECT_NAME, issue_type="FK_DATA_INTEGRITY", local_entity="orders", metadata=metadata)

    assert page.values is not None
    tokens = {tuple(value.key_values): value.token for value in page.values.values}
    assert set(tokens) == {(None,), (7,)}

    for key, token in tokens.items():
        selected = await service.inspect(
            project_name=PROJECT_NAME,
            issue_type="FK_DATA_INTEGRITY",
            local_entity="orders",
            metadata=metadata,
            selected_value_token=token,
        )
        assert selected.selected is not None
        assert selected.selected.status == "selected"
        assert tuple(selected.selected.key_values or []) == key


@pytest.mark.asyncio
async def test_inspection_writes_nothing_to_shared_caches_or_the_project():
    """The inspection uses a private normalization run and leaves the project unchanged."""
    api_project = build_api_project(BASE_CFG)
    saved_project = build_saved_project(BASE_CFG)
    api_snapshot = api_project.model_dump()

    service = service_for(api_project)
    with patch("backend.app.services.shapeshift_service.ShapeShiftService.normalize_project") as normalize_project:
        normalize_project.side_effect = AssertionError("shared cache normalization must not run")
        result = await service.inspect(
            project_name=PROJECT_NAME,
            issue_type="FK_DATA_INTEGRITY",
            local_entity="orders",
            metadata=metadata_for(saved_project, count=2),
        )

    assert result.status == "reproduced"
    assert api_project.model_dump() == api_snapshot
    normalize_project.assert_not_called()
    # The saved project used for parsing is rebuilt from the API project, so the
    # stub project is the only shared object and must be untouched.
    assert build_saved_project(BASE_CFG).cfg == saved_project.cfg
