"""Target-side collision checks for the SEAD change request ingester."""

from dataclasses import dataclass, field
from typing import Protocol

import pandas as pd

from ingesters.sead_change_request.contracts import ChangeRowState, IdentityResolutionResult, MaterializationResult, ResolvedIdentityTable
from src.target_model.models import EntitySpec, TargetModel

INSERTABLE_ROW_STATES: set[ChangeRowState] = {
    ChangeRowState.NEWLY_ALLOCATED_ENTITY,
    ChangeRowState.DERIVED_BRIDGE_ROW,
}


class TargetCollisionChecker(Protocol):
    """Read-only checker used to detect target-side collisions before SQL generation."""

    async def target_id_exists(self, table_name: str, public_id_column: str, target_id: int) -> bool: ...

    async def row_exists(self, table_name: str, filters: dict[str, object]) -> bool: ...


@dataclass(slots=True)
class CollisionCheckResult:
    """Collision diagnostics collected before change-package generation."""

    diagnostics: list[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.diagnostics)


async def check_materialized_collisions(
    materialization_result: MaterializationResult,
    identity_result: IdentityResolutionResult,
    target_model: TargetModel,
    collision_checker: TargetCollisionChecker,
) -> CollisionCheckResult:
    """Run target-side collision checks for rows that would be inserted."""
    diagnostics: list[str] = []

    for entity_name, materialized_table in materialization_result.tables.items():
        resolved_table: ResolvedIdentityTable | None = identity_result.tables.get(entity_name)
        entity_spec: EntitySpec | None = target_model.entities.get(entity_name)
        if resolved_table is None or entity_spec is None:
            continue

        insert_mask: pd.Series = resolved_table.row_states.isin(INSERTABLE_ROW_STATES)
        if not bool(insert_mask.any()):
            continue

        insert_frame: pd.DataFrame = materialized_table.frame.loc[insert_mask]
        table_name: str = entity_spec.target_table or entity_name

        if entity_spec.role == "bridge":
            diagnostics.extend(await _check_bridge_collisions(entity_name, table_name, entity_spec, insert_frame, collision_checker))
            continue

        diagnostics.extend(await _check_target_id_collisions(entity_name, table_name, entity_spec, insert_frame, collision_checker))

    return CollisionCheckResult(diagnostics=diagnostics)


async def _check_target_id_collisions(
    entity_name: str, table_name: str, entity_spec: EntitySpec, insert_frame: pd.DataFrame, collision_checker: TargetCollisionChecker
) -> list[str]:
    diagnostics: list[str] = []
    public_id_column: str | None = entity_spec.public_id

    if not public_id_column:
        return [f"Entity '{entity_name}' cannot run collision checks because public_id metadata is missing"]
    if public_id_column not in insert_frame.columns:
        return [f"Entity '{entity_name}' cannot run collision checks because '{public_id_column}' is missing from the materialized frame"]

    for row_index, row in insert_frame.iterrows():
        target_id = row[public_id_column]
        if pd.isna(target_id):
            diagnostics.append(
                f"Entity '{entity_name}' row '{row_index}' cannot run collision checks because '{public_id_column}' is unresolved"
            )
            continue

        if await collision_checker.target_id_exists(table_name, public_id_column, int(target_id)):
            diagnostics.append(
                f"Entity '{entity_name}' row '{row_index}' collides with existing target ID {int(target_id)} in '{table_name}.{public_id_column}'"
            )

    return diagnostics


async def _check_bridge_collisions(
    entity_name: str,
    table_name: str,
    entity_spec: EntitySpec,
    insert_frame: pd.DataFrame,
    collision_checker: TargetCollisionChecker,
) -> list[str]:
    diagnostics: list[str] = []

    if not entity_spec.unique_sets:
        return [f"Bridge entity '{entity_name}' cannot run collision checks because unique_sets metadata is missing"]

    for row_index, row in insert_frame.iterrows():
        evaluable_sets = []
        for unique_set in entity_spec.unique_sets:
            if any(column not in insert_frame.columns for column in unique_set):
                continue
            if any(pd.isna(row[column]) for column in unique_set):
                continue
            evaluable_sets.append(unique_set)

        if not evaluable_sets:
            diagnostics.append(
                f"Bridge entity '{entity_name}' row '{row_index}' cannot run collision checks because no complete unique_set is materialized"
            )
            continue

        for unique_set in evaluable_sets:
            filters = {column: row[column] for column in unique_set}
            if await collision_checker.row_exists(table_name, filters):
                diagnostics.append(
                    f"Bridge entity '{entity_name}' row '{row_index}' collides with an existing target row in '{table_name}' on unique_set {unique_set}"
                )
                break

    return diagnostics
