"""Tests for the read-only foreign-key link baseline."""

import copy
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

from backend.app.core.config import Settings
from backend.app.exceptions import ProjectedBudgetExceeded
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.services.link_baseline_service import LinkBaselineResult, LinkBaselineService, build_replay_project
from src.loaders.duckdb_loader.duckdb_workspace import DuckDbWorkspace
from src.model import ForeignKeyConfig, ShapeShiftProject
from src.normalizer import LoaderInstanceSet, ShapeShifter
from src.specifications.constraints import ValidationIssue
from src.table_store import TableStore
from src.transforms.link import ForeignKeyLinker
from src.transforms.link_resolution import LinkIssueResolution, resolve_row_count_issue

# pylint: disable=redefined-outer-name, too-many-lines


@dataclass
class ProductionLink:
    """One completed production link captured by the test."""

    fk_index: int | None
    link_pass: str
    local_rows: pd.DataFrame
    remote_rows: pd.DataFrame
    issues: list[ValidationIssue] = field(default_factory=list)


class StubProjectService:
    """Project service double that returns one in-memory API project."""

    def __init__(self, api_project: Project) -> None:
        self._api_project: Project = api_project

    def load_project(self, name: str, force_reload: bool = False) -> Project:  # pylint: disable=unused-argument
        """Return the prepared API project."""
        return self._api_project


def build_api_project(cfg: dict[str, Any], *, name: str = "baseline-probe", filename: str | None = None) -> Project:
    """Build an API project from a core configuration dictionary."""
    return ProjectMapper.to_api_config(cfg, name=name, filename=filename)


def build_saved_project(cfg: dict[str, Any], *, name: str = "baseline-probe") -> ShapeShiftProject:
    """Build a resolved Core project from a core configuration dictionary."""
    return ProjectMapper.to_core(build_api_project(cfg, name=name))


def service_for(api_project: Project) -> LinkBaselineService:
    """Build a baseline service over one in-memory API project."""
    return LinkBaselineService(project_service=StubProjectService(api_project))  # type: ignore[arg-type]


def metadata_for(saved_project: ShapeShiftProject, *, local_entity: str, index: int, link_pass: str) -> dict[str, Any]:
    """Build warning metadata that matches the saved foreign key at the given index."""
    fk: ForeignKeyConfig = saved_project.get_table(local_entity).foreign_keys[index]
    return {
        "fk_index": fk.fk_index,
        "fk_signature": fk.identity_signature,
        "link_pass": link_pass,
        "join_type": fk.how,
        "row_count_before": 3,
        "row_count_after": 2,
    }


async def run_production(
    saved_project: ShapeShiftProject,
    *,
    local_entity: str,
    index: int,
) -> list[ProductionLink]:
    """Run the normal pipeline and record every completed link to the saved entry."""
    observations: list[ProductionLink] = []
    original = ForeignKeyLinker.link_foreign_key

    def recording_link(linker: ForeignKeyLinker, local_df: pd.DataFrame, fk: ForeignKeyConfig, remote_df: pd.DataFrame):
        linked: pd.DataFrame = original(linker, local_df, fk, remote_df)
        if fk.local_entity == local_entity and fk.fk_index == index:
            observations.append(
                ProductionLink(
                    fk_index=fk.fk_index,
                    link_pass=linker.link_pass,
                    local_rows=local_df.copy(),
                    remote_rows=remote_df.copy(),
                    issues=list(linker.validators[-1].issues),
                )
            )
        return linked

    remote_entities: set[str] = {
        fk.remote_entity for fk in saved_project.get_table(local_entity).foreign_keys if saved_project.has_table(fk.remote_entity)
    }

    with patch.object(ForeignKeyLinker, "link_foreign_key", recording_link):
        normalizer = ShapeShifter(
            project=saved_project.clone(),
            table_store=TableStore(),
            target_entities={local_entity} | remote_entities,
        )
        await normalizer.normalize()

    return observations


def shared_columns(left: pd.DataFrame, right: pd.DataFrame) -> list[str]:
    """Return the columns both frames share, in the left frame's order."""
    return [column for column in left.columns if column in right.columns]


def assert_same_rows(left: pd.DataFrame, right: pd.DataFrame) -> None:
    """Assert two link inputs carry the same values in their shared columns."""
    columns: list[str] = shared_columns(left, right)
    assert columns, "no shared columns to compare"
    pd.testing.assert_frame_equal(
        left.reindex(columns=columns).reset_index(drop=True),
        right.reindex(columns=columns).reset_index(drop=True),
    )


def issue_tuples(issues: tuple[ValidationIssue, ...] | list[ValidationIssue]) -> list[tuple[str, str, str, dict[str, Any]]]:
    """Return comparable tuples for validation issues."""
    return [(issue.issue_type, issue.severity, issue.message, issue.metadata) for issue in issues]


def row_findings(issues: tuple[ValidationIssue, ...] | list[ValidationIssue]) -> list[tuple[str, str, str, dict[str, Any]]]:
    """Return comparable findings that do not report the width of the linked frames.

    The replay adds identity columns after the linking stage, so a
    ``column_count_mismatch`` legitimately reports different column totals than
    the production run. Those findings are compared by column increase instead.
    """
    return [finding for finding in issue_tuples(issues) if finding[0] != "column_count_mismatch"]


def column_increases(issues: tuple[ValidationIssue, ...] | list[ValidationIssue]) -> list[tuple[int, list[str]]]:
    """Return the expected column increase of each column-count finding."""
    return [
        (issue.metadata["expected_increase"], issue.metadata["added_columns"])
        for issue in issues
        if issue.issue_type == "column_count_mismatch"
    ]


# ---------------------------------------------------------------------------
# Temporary-config projection
# ---------------------------------------------------------------------------

PROJECTION_FK_TARGET: str = "customers"

PROJECTION_CFG: dict[str, Any] = {
    "entities": {
        "orders": {
            "type": "entity",
            "source": "raw_orders",
            "public_id": "order_id",
            "keys": ["customer_id"],
            "columns": ["order_code", "customer_code", "region_code", "reading_a", "reading_b"],
            "extra_columns": {"order_label": "order_code"},
            "depends_on": ["customers"],
            "filters": [
                {"type": "query", "query": "order_code != ''"},
                {"type": "query", "stage": "after_link", "query": "customer_id != ''"},
                {"type": "query", "stage": "after_unnest", "query": "reading_a > 0"},
            ],
            "unnest": {
                "id_vars": ["order_code"],
                "value_vars": ["reading_a", "reading_b"],
                "var_name": "reading_type",
                "value_name": "reading_value",
            },
            "drop_duplicates": ["reading_value"],
            "drop_empty_rows": ["reading_value"],
            "foreign_keys": [
                {"entity": "customers", "local_keys": ["customer_code"], "remote_keys": ["code"]},
                {"entity": "customers", "local_keys": ["order_code"], "remote_keys": ["code"]},
                {"entity": "regions", "local_keys": ["region_code"], "remote_keys": ["code"]},
            ],
        },
        "raw_orders": {
            "type": "fixed",
            "columns": ["order_code", "customer_code", "region_code", "reading_a", "reading_b"],
            "values": [["O1", "C1", "R1", 1, 2]],
        },
        "customers": {
            "type": "fixed",
            "public_id": "customer_id",
            "keys": ["code"],
            "columns": ["code", "name"],
            "values": [["C1", "Alpha"]],
        },
        "regions": {
            "type": "fixed",
            "public_id": "region_id",
            "keys": ["code"],
            "columns": ["code", "label"],
            "values": [["R1", "North"]],
        },
    }
}


def projection_resolution(cfg: dict[str, Any], index: int, link_pass: str) -> tuple[ShapeShiftProject, LinkIssueResolution]:
    """Build a saved project and a resolved warning for one saved foreign key."""
    saved = build_saved_project(cfg)
    resolution = resolve_row_count_issue(
        saved,
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=metadata_for(saved, local_entity="orders", index=index, link_pass=link_pass),
    )
    assert resolution.is_eligible
    return saved, resolution


@pytest.mark.parametrize(
    ("link_pass", "keeps_unnest", "keeps_after_link", "keeps_after_unnest", "keeps_dedup", "keeps_drop_empty"),
    [
        pytest.param("initial", False, False, False, False, False, id="initial"),
        pytest.param("after_unnest", True, True, False, False, True, id="after-unnest"),
        pytest.param("deferred_retry", True, True, True, True, True, id="deferred-retry"),
    ],
)
def test_projection_keeps_only_the_stages_that_run_before_the_linking_pass(
    link_pass: str,
    keeps_unnest: bool,
    keeps_after_link: bool,
    keeps_after_unnest: bool,
    keeps_dedup: bool,
    keeps_drop_empty: bool,
) -> None:
    """The temporary config keeps exactly the stages that precede the recorded pass."""
    saved, resolution = projection_resolution(PROJECTION_CFG, index=1, link_pass=link_pass)

    replay = build_replay_project(saved, resolution)
    replay_cfg = replay.get_table("orders")

    assert [fk.identity_signature for fk in replay_cfg.foreign_keys] == [
        fk.identity_signature for fk in saved.get_table("orders").foreign_keys[:1]
    ]
    assert replay_cfg.keys == set()
    assert (replay_cfg.unnest is not None) is keeps_unnest
    assert bool(replay_cfg.drop_duplicates) is keeps_dedup
    assert bool(replay_cfg.drop_empty_rows) is keeps_drop_empty

    stages = [filter_cfg.get("stage") or "extract" for filter_cfg in replay_cfg.filters]
    assert "extract" in stages
    assert ("after_link" in stages) is keeps_after_link
    assert ("after_unnest" in stages) is keeps_after_unnest


def test_projection_keeps_unnest_independent_deduplication_for_every_pass() -> None:
    """Deduplication on a plain column is not tied to unnest and stays in place."""
    cfg = copy.deepcopy(PROJECTION_CFG)
    cfg["entities"]["orders"]["drop_duplicates"] = ["order_code"]
    saved = build_saved_project(cfg)

    for link_pass in ("initial", "after_unnest", "deferred_retry"):
        resolution = resolve_row_count_issue(
            saved,
            issue_type="row_count_mismatch",
            local_entity="orders",
            metadata=metadata_for(saved, local_entity="orders", index=1, link_pass=link_pass),
        )
        replay_cfg = build_replay_project(saved, resolution).get_table("orders")

        assert replay_cfg.drop_duplicates == ["order_code"]


def test_projection_preserves_source_columns_extra_columns_and_dependencies() -> None:
    """Everything the link input depends on survives the projection unchanged."""
    saved, resolution = projection_resolution(PROJECTION_CFG, index=1, link_pass="initial")
    saved_cfg = saved.get_table("orders")

    replay_cfg = build_replay_project(saved, resolution).get_table("orders")

    assert replay_cfg.source == saved_cfg.source
    assert replay_cfg.columns == saved_cfg.columns
    assert replay_cfg.extra_columns == saved_cfg.extra_columns
    assert replay_cfg.entity_cfg.get("depends_on") == ["customers"]


def test_projection_keeps_only_the_foreign_keys_before_the_selected_entry() -> None:
    """Earlier entries keep their order, including two links to the same entity."""
    saved, resolution = projection_resolution(PROJECTION_CFG, index=2, link_pass="initial")

    replay_cfg = build_replay_project(saved, resolution).get_table("orders")

    assert [(fk.remote_entity, fk.local_keys) for fk in replay_cfg.foreign_keys] == [
        ("customers", ["customer_code"]),
        ("customers", ["order_code"]),
    ]
    assert all(fk.fk_index != 2 for fk in replay_cfg.foreign_keys)
    assert resolution.fk is not None and resolution.fk.remote_entity == "regions"


def test_projection_leaves_the_saved_and_api_projects_unchanged() -> None:
    """The saved Core project, the API project, and the project filename are untouched."""
    api_project = build_api_project(PROJECTION_CFG, filename="projects/demo/shapeshifter.yml")
    saved = ProjectMapper.to_core(api_project)
    resolution = resolve_row_count_issue(
        saved,
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=metadata_for(saved, local_entity="orders", index=1, link_pass="initial"),
    )
    api_snapshot: dict[str, Any] = api_project.model_dump()
    saved_snapshot: dict[str, Any] = copy.deepcopy(saved.cfg)

    replay = build_replay_project(saved, resolution)

    assert api_project.model_dump() == api_snapshot
    assert saved.cfg == saved_snapshot
    assert replay.cfg != saved.cfg
    assert replay.filename == saved.filename


def test_projection_uses_the_mapper_resolved_values_and_project_filename() -> None:
    """Directives resolve through the mapper before the projection is built."""
    cfg = copy.deepcopy(PROJECTION_CFG)
    cfg["entities"]["orders"]["columns"] = ["order_code", "customer_code", "region_code", "@value: entities.customers.keys"]
    cfg["entities"]["orders"]["unnest"]["value_vars"] = ["region_code"]
    api_project = build_api_project(cfg, filename="projects/demo/shapeshifter.yml")

    saved = ProjectMapper.to_core(api_project)
    resolution = resolve_row_count_issue(
        saved,
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=metadata_for(saved, local_entity="orders", index=1, link_pass="after_unnest"),
    )
    replay = build_replay_project(saved, resolution)

    assert api_project.entities["orders"]["columns"][-1] == "@value: entities.customers.keys"
    assert "code" in replay.get_table("orders").columns
    assert replay.filename == "projects/demo/shapeshifter.yml"


# ---------------------------------------------------------------------------
# Production parity
# ---------------------------------------------------------------------------

INNER_JOIN_CFG: dict[str, Any] = {
    "entities": {
        "orders": {
            "type": "fixed",
            "public_id": "order_id",
            "keys": ["order_code"],
            "columns": ["order_code", "customer_code"],
            "values": [["O1", "C1"], ["O2", "C2"], ["O3", "missing"]],
            "foreign_keys": [
                {
                    "entity": "customers",
                    "local_keys": ["customer_code"],
                    "remote_keys": ["code"],
                    "how": "inner",
                    "constraints": {"allow_row_decrease": True},
                }
            ],
        },
        "customers": {
            "type": "fixed",
            "public_id": "customer_id",
            "keys": ["code"],
            "columns": ["code", "name"],
            "values": [["C1", "Alpha"], ["C2", "Beta"], ["C3", "Gamma"]],
        },
    }
}


async def assert_parity(cfg: dict[str, Any], *, local_entity: str, index: int) -> tuple[LinkBaselineResult, ProductionLink]:
    """Compare one baseline with an independent production run of the same link."""
    api_project = build_api_project(cfg)
    saved = ProjectMapper.to_core(api_project)

    observations = await run_production(saved, local_entity=local_entity, index=index)
    assert len(observations) == 1, f"expected exactly one completed link, got {len(observations)}"
    production = observations[0]
    assert production.issues, "the production link raised no warning"

    warning = next(issue for issue in production.issues if issue.issue_type == "row_count_mismatch")
    result = await service_for(api_project).build_baseline(
        project_name="baseline-probe",
        issue_type="row_count_mismatch",
        local_entity=local_entity,
        metadata=warning.metadata,
    )

    assert result.status == "reproduced", result.message
    assert result.link_pass == production.link_pass
    assert result.row_count_before == production.local_rows.shape[0]
    assert result.row_count_after == warning.metadata["row_count_after"]
    assert row_findings(result.issues) == row_findings(production.issues)
    assert column_increases(result.issues) == column_increases(production.issues)
    assert result._saved_project is not None
    assert result._foreign_key is not None
    assert result._foreign_key.identity_signature == saved.get_table(local_entity).foreign_keys[index].identity_signature
    assert result.local_rows is not None and result.remote_rows is not None
    assert_same_rows(production.local_rows, result.local_rows)
    assert_same_rows(production.remote_rows, result.remote_rows)
    assert len(result.local_rows) == production.local_rows.shape[0]
    return result, production


@pytest.mark.asyncio
async def test_inner_join_baseline_matches_the_production_link() -> None:
    """An inner link reports the production counts, findings, and full rows."""
    result, production = await assert_parity(INNER_JOIN_CFG, local_entity="orders", index=0)

    assert (result.row_count_before, result.row_count_after) == (3, 2)
    assert production.link_pass == "initial"
    assert [issue[0] for issue in issue_tuples(result.issues)] == ["row_count_mismatch"]


@pytest.mark.asyncio
async def test_baseline_keeps_selected_local_key_that_only_exists_in_source() -> None:
    """The replay extracts selected FK keys that are not declared as entity columns."""
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "entity",
                "source": "raw_orders",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code"],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["code"],
                        "constraints": {"allow_row_decrease": True},
                    }
                ],
            },
            "raw_orders": {
                "type": "fixed",
                "public_id": "raw_order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code"],
                "values": [["O1", "C1"], ["O2", "C2"], ["O3", "missing"]],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["code"],
                "columns": ["code", "name"],
                "values": [["C1", "Alpha"], ["C2", "Beta"], ["C3", "Gamma"]],
            },
        }
    }

    result, _ = await assert_parity(cfg, local_entity="orders", index=0)

    assert (result.row_count_before, result.row_count_after) == (3, 2)


@pytest.mark.asyncio
async def test_baseline_keeps_selected_local_key_produced_by_an_earlier_fk() -> None:
    """The replay retains a local key produced by an earlier FK's extra_columns."""
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "entity",
                "source": "raw_orders",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code"],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["code"],
                        "extra_columns": {"customer_name": "name"},
                    },
                    {
                        "entity": "customer_names",
                        "local_keys": ["customer_name"],
                        "remote_keys": ["name"],
                        "constraints": {"allow_row_decrease": True},
                    },
                ],
            },
            "raw_orders": {
                "type": "fixed",
                "public_id": "raw_order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code"],
                "values": [["O1", "C1"], ["O2", "C2"], ["O3", "C3"]],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["code"],
                "columns": ["code", "name"],
                "values": [["C1", "Alpha"], ["C2", "Beta"], ["C3", "Gamma"]],
            },
            "customer_names": {
                "type": "fixed",
                "public_id": "customer_name_id",
                "keys": ["name"],
                "columns": ["name"],
                "values": [["Alpha"], ["Beta"]],
            },
        }
    }

    result, _ = await assert_parity(cfg, local_entity="orders", index=1)

    assert (result.row_count_before, result.row_count_after) == (3, 2)


@pytest.mark.asyncio
async def test_left_join_baseline_matches_the_production_link() -> None:
    """A left link keeps unmatched rows and matches the production finding."""
    cfg = copy.deepcopy(INNER_JOIN_CFG)
    fk = cfg["entities"]["orders"]["foreign_keys"][0]
    fk["how"] = "left"
    fk["constraints"] = {"allow_row_decrease": True, "allow_unmatched_left": True}
    cfg["entities"]["orders"]["values"] = [["O1", "C1"], ["O2", "missing"]]
    cfg["entities"]["customers"]["values"] = [["C1", "Alpha"], ["C1", "Alpine"]]

    result, production = await assert_parity(cfg, local_entity="orders", index=0)

    assert production.link_pass == "initial"
    assert (result.row_count_before, result.row_count_after) == (2, 3)


@pytest.mark.asyncio
async def test_unnest_link_baseline_matches_the_production_link() -> None:
    """A link deferred by unnest reproduces at the after-unnest pass."""
    cfg: dict[str, Any] = {
        "entities": {
            "measurements": {
                "type": "fixed",
                "public_id": "measurement_id",
                "keys": ["sample_code"],
                "columns": ["sample_code", "reading_a", "reading_b"],
                "values": [["S1", 10, 20], ["S2", 30, 40]],
                "unnest": {
                    "id_vars": ["sample_code"],
                    "value_vars": ["reading_a", "reading_b"],
                    "var_name": "reading_type",
                    "value_name": "reading_value",
                },
                "foreign_keys": [
                    {
                        "entity": "readings",
                        "local_keys": ["reading_value"],
                        "remote_keys": ["value"],
                        "how": "inner",
                        "constraints": {"allow_row_decrease": True},
                    }
                ],
            },
            "readings": {
                "type": "fixed",
                "public_id": "reading_id",
                "keys": ["value"],
                "columns": ["value", "label"],
                "values": [[10, "ten"], [20, "twenty"]],
            },
        }
    }

    result, production = await assert_parity(cfg, local_entity="measurements", index=0)

    assert production.link_pass == "after_unnest"
    assert result.link_pass == "after_unnest"
    assert (result.row_count_before, result.row_count_after) == (4, 2)


@pytest.mark.asyncio
async def test_deferred_link_baseline_matches_the_production_link() -> None:
    """A deferred link reproduces at the deferred retry pass."""
    cfg = copy.deepcopy(INNER_JOIN_CFG)
    cfg["entities"]["orders"]["foreign_keys"][0]["defer_dependency"] = True
    # The deferred link removes the hard dependency on customers, so declare the
    # reverse dependency to keep the local entity first in the processing order.
    cfg["entities"]["customers"]["depends_on"] = ["orders"]

    result, production = await assert_parity(cfg, local_entity="orders", index=0)

    assert production.link_pass == "deferred_retry"
    assert result.link_pass == "deferred_retry"
    assert (result.row_count_before, result.row_count_after) == (3, 2)


@pytest.mark.asyncio
async def test_earlier_foreign_key_to_another_entity_matches_the_production_link() -> None:
    """The replay applies the earlier link to a different parent before the selected one."""
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code", "region_code"],
                "values": [["O1", "C1", "R1"], ["O2", "missing", "R2"], ["O3", "C3", "R3"]],
                "foreign_keys": [
                    {
                        "entity": "regions",
                        "local_keys": ["region_code"],
                        "remote_keys": ["code"],
                        "constraints": {"allow_row_decrease": True},
                    },
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["code"],
                        "constraints": {"allow_row_decrease": True},
                    },
                ],
            },
            "regions": {
                "type": "fixed",
                "public_id": "region_id",
                "keys": ["code"],
                "columns": ["code", "label"],
                "values": [["R1", "North"], ["R2", "South"]],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["code"],
                "columns": ["code", "name"],
                "values": [["C1", "Alpha"], ["C3", "Gamma"]],
            },
        }
    }

    result, production = await assert_parity(cfg, local_entity="orders", index=1)

    assert (result.row_count_before, result.row_count_after) == (2, 1)
    assert len(production.local_rows) == 2


@pytest.mark.asyncio
async def test_second_link_to_the_same_entity_matches_the_production_link() -> None:
    """A second link to the same parent runs after the first drops its remote ID."""
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code", "region_code"],
                "values": [["O1", "C1", "R1"], ["O2", "missing", "R2"]],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["region_code"],
                        "remote_keys": ["region_code"],
                        "extra_columns": {"customer_region_name": "name"},
                        "drop_remote_id": True,
                        "constraints": {"allow_row_decrease": True},
                    },
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["code"],
                        "constraints": {"allow_row_decrease": True},
                    },
                ],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["code"],
                "columns": ["code", "region_code", "name"],
                "values": [["C1", "R1", "Alpha"], ["C2", "R2", "Beta"]],
            },
        }
    }

    result, production = await assert_parity(cfg, local_entity="orders", index=1)

    assert (result.row_count_before, result.row_count_after) == (2, 1)
    assert "customer_id" not in production.local_rows.columns
    assert "customer_region_name" in production.local_rows.columns


@pytest.mark.asyncio
async def test_partially_null_compound_key_matches_the_production_link() -> None:
    """A partially null compound key follows the saved null policy in both runs."""
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code", "region_code"],
                "values": [["O1", "C1", "R1"], ["O2", "C2", None], ["O3", "C3", "R1"]],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code", "region_code"],
                        "remote_keys": ["code", "region_code"],
                        "constraints": {"allow_null_keys": True, "allow_row_decrease": True},
                    }
                ],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["code", "region_code"],
                "columns": ["code", "region_code", "name"],
                "values": [["C1", "R1", "Alpha"], ["C2", None, "Beta"], ["C3", "R2", "Gamma"]],
            },
        }
    }

    result, production = await assert_parity(cfg, local_entity="orders", index=0)

    assert (result.row_count_before, result.row_count_after) == (3, 1)
    assert result.local_rows is not None and result.local_rows["region_code"].isna().any()
    assert "region_code" in production.local_rows.columns


@pytest.mark.asyncio
async def test_duplicate_remote_matches_expand_rows_like_the_production_link() -> None:
    """Several remote rows per key expand the local row count in both runs."""
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code"],
                "values": [["O1", "C1"], ["O2", "C2"]],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["code"],
                        "constraints": {"allow_row_decrease": True},
                    }
                ],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["code"],
                "columns": ["code", "region_code", "name"],
                "values": [["C1", "R1", "Alpha"], ["C1", "R2", "Alpine"], ["C2", "R1", "Beta"]],
            },
        }
    }

    result, _ = await assert_parity(cfg, local_entity="orders", index=0)

    assert (result.row_count_before, result.row_count_after) == (2, 3)


# ---------------------------------------------------------------------------
# Stale, unavailable, and invalid warnings
# ---------------------------------------------------------------------------


async def baseline_for_metadata(cfg: dict[str, Any], metadata: dict[str, Any], *, local_entity: str = "orders") -> LinkBaselineResult:
    """Build a baseline from explicit warning metadata."""
    return await service_for(build_api_project(cfg)).build_baseline(
        project_name="baseline-probe",
        issue_type="row_count_mismatch",
        local_entity=local_entity,
        metadata=metadata,
    )


@pytest.mark.asyncio
async def test_changed_source_rows_report_a_changed_warning() -> None:
    """Changed data that keeps the link but changes the counts is not presented as current."""
    saved = build_saved_project(INNER_JOIN_CFG)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="initial")
    metadata["row_count_before"] = 3
    metadata["row_count_after"] = 2

    stale_cfg = copy.deepcopy(INNER_JOIN_CFG)
    stale_cfg["entities"]["orders"]["values"] = [["O1", "C1"], ["O2", "C2"], ["O3", "missing"], ["O4", "missing"]]

    result = await baseline_for_metadata(stale_cfg, metadata)

    assert result.status == "not_reproduced"
    assert result.reason == "warning_changed"
    assert (result.row_count_before, result.row_count_after) == (4, 2)
    assert result.local_rows is None
    assert result.remote_rows is None
    assert result._saved_project is not None
    assert result._foreign_key is not None


@pytest.mark.asyncio
async def test_warning_that_no_longer_occurs_is_not_reproduced() -> None:
    """Data that no longer loses rows reports no warning instead of the stored one."""
    saved = build_saved_project(INNER_JOIN_CFG)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="initial")

    clean_cfg = copy.deepcopy(INNER_JOIN_CFG)
    clean_cfg["entities"]["orders"]["values"] = [["O1", "C1"], ["O2", "C2"]]

    result = await baseline_for_metadata(clean_cfg, metadata)

    assert result.status == "not_reproduced"
    assert result.reason == "warning_not_raised"
    assert result.local_rows is None
    assert result.remote_rows is None
    assert result._saved_project is not None
    assert result._foreign_key is not None


@pytest.mark.asyncio
async def test_missing_remote_entity_is_not_reproduced() -> None:
    """A warning whose remote entity is gone cannot be reproduced."""
    saved = build_saved_project(INNER_JOIN_CFG)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="initial")

    missing_cfg = copy.deepcopy(INNER_JOIN_CFG)
    del missing_cfg["entities"]["customers"]

    result = await baseline_for_metadata(missing_cfg, metadata)

    assert result.status == "not_reproduced"
    assert result.reason == "remote_entity_not_found"
    assert result.remote_entity == "customers"
    assert result._saved_project is not None
    assert result._foreign_key is not None
    assert result.local_rows is None
    assert result.remote_rows is None


@pytest.mark.asyncio
async def test_unresolvable_source_reports_a_replay_failure() -> None:
    """A replay that cannot load its own input reports the failure and no trial inputs."""
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "entity",
                "source": "raw_orders",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code"],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["code"],
                        "constraints": {"allow_row_decrease": True},
                    }
                ],
            },
            "raw_orders": {"type": "entity", "keys": ["order_code"], "columns": ["order_code", "customer_code"]},
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["code"],
                "columns": ["code", "name"],
                "values": [["C1", "Alpha"]],
            },
        }
    }
    saved = build_saved_project(cfg)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="initial")

    result = await baseline_for_metadata(cfg, metadata)

    assert result.status == "not_reproduced"
    assert result.reason == "replay_failed"
    assert result.local_rows is None
    assert result._saved_project is not None
    assert result._foreign_key is not None


@pytest.mark.asyncio
async def test_missing_link_pass_is_rejected() -> None:
    """A warning without a linking pass is rejected instead of guessing one."""
    saved = build_saved_project(INNER_JOIN_CFG)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="initial")
    del metadata["link_pass"]

    result = await baseline_for_metadata(INNER_JOIN_CFG, metadata)

    assert result.status == "not_reproduced"
    assert result.reason == "missing_link_pass"
    assert result._saved_project is not None
    assert result._foreign_key is not None


@pytest.mark.asyncio
async def test_unknown_link_pass_is_rejected() -> None:
    """A linking pass outside the pipeline passes is rejected."""
    saved = build_saved_project(INNER_JOIN_CFG)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="after_link")

    result = await baseline_for_metadata(INNER_JOIN_CFG, metadata)

    assert result.status == "not_reproduced"
    assert result.reason == "unknown_link_pass"
    assert result._saved_project is not None
    assert result._foreign_key is not None


@pytest.mark.asyncio
async def test_unsupported_join_is_ineligible() -> None:
    """A right join offers no troubleshooting baseline."""
    cfg = copy.deepcopy(INNER_JOIN_CFG)
    cfg["entities"]["orders"]["foreign_keys"][0]["how"] = "right"
    cfg["entities"]["orders"]["foreign_keys"][0]["constraints"] = {"allow_row_increase": True, "allow_unmatched_right": True}
    saved = build_saved_project(cfg)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="initial")
    metadata["join_type"] = "right"

    result = await baseline_for_metadata(cfg, metadata)

    assert result.status == "ineligible"
    assert result.reason == "unsupported_join"
    assert result._saved_project is not None
    assert result._foreign_key is not None


@pytest.mark.asyncio
async def test_changed_foreign_key_signature_is_ineligible() -> None:
    """A warning whose signature no longer matches the saved entry is ineligible."""
    saved = build_saved_project(INNER_JOIN_CFG)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="initial")
    metadata["fk_signature"] = "stale-signature"

    result = await baseline_for_metadata(INNER_JOIN_CFG, metadata)

    assert result.status == "ineligible"
    assert result.reason == "signature_mismatch"
    assert result.local_rows is None


@pytest.mark.asyncio
async def test_constraint_violation_is_not_reported_as_reproduced() -> None:
    """A link that violates a saved constraint reports failure, not a valid comparison."""
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code"],
                "values": [["O1", "C1"], ["O2", None]],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["code"],
                        "constraints": {"allow_row_decrease": True},
                    }
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
    saved = build_saved_project(cfg)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="initial")

    result = await baseline_for_metadata(cfg, metadata)

    assert result.status == "not_reproduced"
    assert result.reason == "constraint_violation"
    assert result.local_rows is None
    assert result.remote_rows is None


# ---------------------------------------------------------------------------
# Read-only behavior and replay lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_baseline_does_not_change_the_project_or_production_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """A baseline run leaves the saved project, its file, and production caches untouched."""
    api_project = build_api_project(INNER_JOIN_CFG, filename="projects/demo/shapeshifter.yml")
    saved = ProjectMapper.to_core(api_project)
    observations = await run_production(saved, local_entity="orders", index=0)
    warning = next(issue for issue in observations[0].issues if issue.issue_type == "row_count_mismatch")

    api_snapshot: dict[str, Any] = api_project.model_dump()
    saved_snapshot: dict[str, Any] = copy.deepcopy(saved.cfg)
    production_local: pd.DataFrame = observations[0].local_rows.copy()
    production_remote: pd.DataFrame = observations[0].remote_rows.copy()

    cache_calls: list[str] = []
    for target in (
        "backend.app.utils.caches.ShapeShiftCache.set_dataframe",
        "backend.app.utils.caches.ShapeShiftCache.set_table_store",
        "backend.app.utils.caches.ShapeShiftCache.fetch_cached_entity_data",
        "backend.app.utils.caches.ShapeShiftProjectCache.get_project",
    ):
        monkeypatch.setattr(target, lambda *args, _name=target, **kwargs: cache_calls.append(_name))

    result = await service_for(api_project).build_baseline(
        project_name="baseline-probe",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=warning.metadata,
    )

    assert result.status == "reproduced"
    assert not cache_calls
    assert api_project.model_dump() == api_snapshot
    assert saved.cfg == saved_snapshot
    assert observations[0].local_rows.equals(production_local)
    assert observations[0].remote_rows.equals(production_remote)


@pytest.mark.asyncio
async def test_replay_uses_its_own_store_and_closes_its_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    """The replay builds private tables and closes its workspace and loaders on success."""
    api_project = build_api_project(INNER_JOIN_CFG, filename="projects/demo/shapeshifter.yml")
    saved = ProjectMapper.to_core(api_project)
    observations = await run_production(saved, local_entity="orders", index=0)
    warning = next(issue for issue in observations[0].issues if issue.issue_type == "row_count_mismatch")

    captured: dict[str, ShapeShifter] = {}
    closed: dict[str, int] = {"workspace": 0, "loaders": 0}
    original_normalize = ShapeShifter.normalize

    async def recording_normalize(self: ShapeShifter) -> ShapeShifter:
        captured["normalizer"] = self
        return await original_normalize(self)

    original_close = DuckDbWorkspace.close
    original_close_all = LoaderInstanceSet.close_all

    def counting_close(self: DuckDbWorkspace) -> None:
        closed["workspace"] += 1
        original_close(self)

    def counting_close_all(self: LoaderInstanceSet) -> None:
        closed["loaders"] += 1
        original_close_all(self)

    monkeypatch.setattr(ShapeShifter, "normalize", recording_normalize)
    monkeypatch.setattr(DuckDbWorkspace, "close", counting_close)
    monkeypatch.setattr(LoaderInstanceSet, "close_all", counting_close_all)

    result = await service_for(api_project).build_baseline(
        project_name="baseline-probe",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=warning.metadata,
    )

    normalizer = captured["normalizer"]
    assert result.status == "reproduced"
    assert isinstance(normalizer.table_store, TableStore)
    assert normalizer.duckdb_workspace.connection is None
    # ``__del__`` may close the workspace again once the normalizer is collected.
    assert closed["workspace"] >= 1
    assert closed["loaders"] == 1
    assert result.local_rows is not None
    assert result.local_rows is not normalizer.table_store["orders"]


@pytest.mark.asyncio
async def test_failed_replay_still_closes_its_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    """A replay that fails while loading still closes its workspace and loaders."""
    cfg: dict[str, Any] = {
        "entities": {
            "orders": {
                "type": "entity",
                "source": "raw_orders",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code"],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["code"],
                        "constraints": {"allow_row_decrease": True},
                    }
                ],
            },
            "raw_orders": {"type": "entity", "keys": ["order_code"], "columns": ["order_code", "customer_code"]},
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["code"],
                "columns": ["code", "name"],
                "values": [["C1", "Alpha"]],
            },
        }
    }
    api_project = build_api_project(cfg)
    saved = ProjectMapper.to_core(api_project)
    metadata = metadata_for(saved, local_entity="orders", index=0, link_pass="initial")

    closed: dict[str, int] = {"workspace": 0, "loaders": 0}
    original_close = DuckDbWorkspace.close
    original_close_all = LoaderInstanceSet.close_all

    def counting_close(self: DuckDbWorkspace) -> None:
        closed["workspace"] += 1
        original_close(self)

    def counting_close_all(self: LoaderInstanceSet) -> None:
        closed["loaders"] += 1
        original_close_all(self)

    monkeypatch.setattr(DuckDbWorkspace, "close", counting_close)
    monkeypatch.setattr(LoaderInstanceSet, "close_all", counting_close_all)

    result = await service_for(api_project).build_baseline(
        project_name="baseline-probe",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=metadata,
    )

    assert result.status == "not_reproduced"
    assert result.reason == "replay_failed"
    # ``__del__`` may close the workspace again once the normalizer is collected.
    assert closed["workspace"] >= 1
    assert closed["loaders"] == 1


# ---------------------------------------------------------------------------
# Experiment memory budget
# ---------------------------------------------------------------------------

LARGE_INPUT_ROWS: int = 10_000


def large_input_cfg() -> dict[str, Any]:
    """Build a project whose replay inputs are larger than one MiB."""
    codes: list[str] = [f"{index:05d}" + "x" * 55 for index in range(LARGE_INPUT_ROWS)]
    return {
        "entities": {
            "orders": {
                "type": "fixed",
                "public_id": "order_id",
                "keys": ["order_code"],
                "columns": ["order_code", "customer_code"],
                "values": [[f"O{index}", code] for index, code in enumerate(codes)],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["code"],
                        "how": "inner",
                        "constraints": {"allow_row_decrease": True},
                    }
                ],
            },
            "customers": {
                "type": "fixed",
                "public_id": "customer_id",
                "keys": ["code"],
                "columns": ["code"],
                "values": [[codes[0]]],
            },
        }
    }


def large_input_metadata(saved_project: ShapeShiftProject) -> dict[str, Any]:
    """Build metadata matching the warning raised by the large-input project."""
    fk: ForeignKeyConfig = saved_project.get_table("orders").foreign_keys[0]
    return {
        "fk_index": fk.fk_index,
        "fk_signature": fk.identity_signature,
        "link_pass": "initial",
        "join_type": "inner",
        "row_count_before": LARGE_INPUT_ROWS,
        "row_count_after": 1,
    }


@pytest.mark.asyncio
async def test_reproduction_rejects_over_budget_inputs_before_the_merge(tmp_path) -> None:
    """Retained inputs above the configured limit cannot open a baseline."""
    api_project = build_api_project(large_input_cfg())
    saved = ProjectMapper.to_core(api_project)
    settings = Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        APPLICATION_ROOT=tmp_path,
        LINK_EXPERIMENT_MAX_MEMORY_MB=1,
    )  # pyright: ignore[reportCallIssue]
    service = LinkBaselineService(project_service=StubProjectService(api_project), settings=settings)  # type: ignore[arg-type]

    with patch.object(ForeignKeyLinker, "link_foreign_key") as link:
        with pytest.raises(ProjectedBudgetExceeded) as raised:
            await service.build_baseline(
                project_name="baseline-probe",
                issue_type="row_count_mismatch",
                local_entity="orders",
                metadata=large_input_metadata(saved),
            )

    assert raised.value.code == "PROJECTED_BUDGET_EXCEEDED"
    assert raised.value.context["stage"] == "link reproduction"
    link.assert_not_called()


@pytest.mark.asyncio
async def test_reproduction_completes_within_the_default_memory_limit(tmp_path) -> None:
    """The same inputs reproduce under the default 100 MiB limit."""
    api_project = build_api_project(large_input_cfg())
    saved = ProjectMapper.to_core(api_project)
    service = LinkBaselineService(
        project_service=StubProjectService(api_project),  # type: ignore[arg-type]
        settings=Settings(_env_file=None, APPLICATION_ROOT=tmp_path),  # pyright: ignore[reportCallIssue]
    )

    result = await service.build_baseline(
        project_name="baseline-probe",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=large_input_metadata(saved),
    )

    assert result.status == "reproduced", result.message
    assert result.local_rows is not None
    assert len(result.local_rows) == LARGE_INPUT_ROWS
