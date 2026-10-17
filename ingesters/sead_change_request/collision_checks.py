"""Target-side collision checks for the SEAD change request ingester."""

from dataclasses import dataclass, field
from typing import Protocol

import pandas as pd

from ingesters.sead_change_request.contracts import ChangeRowState, IdentityResolutionResult, ResolvedIdentityTable, TargetProjectionResult
from ingesters.sead_change_request.staging_eligibility import PendingDeploymentMap
from src.target_model.effective_identity import resolve_effective_identity
from src.target_model.models import EntitySpec, TargetModel

GENERATION_TIME_ROW_STATES: set[ChangeRowState] = {
    ChangeRowState.NEWLY_ALLOCATED_ENTITY,
    ChangeRowState.DERIVED_BRIDGE_ROW,
}
STAGED_ROW_STATES: set[ChangeRowState] = {
    ChangeRowState.NEWLY_ALLOCATED_ENTITY,
    ChangeRowState.DERIVED_BRIDGE_ROW,
    ChangeRowState.PENDING_DEPLOYMENT_ID,
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


async def check_projected_collisions(
    projection_result: TargetProjectionResult,
    identity_result: IdentityResolutionResult,
    target_model: TargetModel,
    collision_checker: TargetCollisionChecker,
    pending: PendingDeploymentMap | None = None,
) -> CollisionCheckResult:
    """Run target-side collision checks for rows that would be inserted.

    Known target IDs and complete derived-bridge sets are always checked. With
    ``pending``, values that only exist after deployment are deferred to the
    deployment checks instead of being reported as misses.
    """
    diagnostics: list[str] = []
    row_states = STAGED_ROW_STATES if pending is not None else GENERATION_TIME_ROW_STATES

    for entity_name, projected_table in projection_result.tables.items():
        resolved_table: ResolvedIdentityTable | None = identity_result.tables.get(entity_name)
        entity_spec: EntitySpec | None = target_model.entities.get(entity_name)
        if resolved_table is None or entity_spec is None:
            continue

        insert_mask: pd.Series = resolved_table.row_states.isin(row_states)
        if pending is not None:
            insert_mask = insert_mask & ~_pending_row_mask(pending, entity_name, insert_mask.index)
        if not bool(insert_mask.any()):
            continue

        insert_frame: pd.DataFrame = projected_table.frame.loc[insert_mask]
        table_name: str = entity_spec.target_table or entity_name

        effective = resolve_effective_identity(entity_spec)
        if effective.identity_tracking == "derived":
            diagnostics.extend(
                await _check_bridge_collisions(entity_name, table_name, entity_spec, insert_frame, collision_checker, pending)
            )
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
        return [f"Entity '{entity_name}' cannot run collision checks because '{public_id_column}' is missing from the projected frame"]

    for row_index, row in insert_frame.iterrows():
        target_id = row[public_id_column]
        if pd.isna(target_id):
            diagnostics.append(
                f"Entity '{entity_name}' row '{row_index}' cannot run collision checks because '{public_id_column}' is unresolved"
            )
            continue

        if await collision_checker.target_id_exists(table_name, public_id_column, int(target_id)):
            diagnostics.append(
                f"Entity '{entity_name}' row '{row_index}' collides "
                f"with existing target ID {int(target_id)} in '{table_name}.{public_id_column}'"
            )

    return diagnostics


async def _check_bridge_collisions(
    entity_name: str,
    table_name: str,
    entity_spec: EntitySpec,
    insert_frame: pd.DataFrame,
    collision_checker: TargetCollisionChecker,
    pending: PendingDeploymentMap | None = None,
) -> list[str]:
    diagnostics: list[str] = []

    if not entity_spec.unique_sets:
        return [f"Bridge entity '{entity_name}' cannot run collision checks because unique_sets metadata is missing"]

    for row_index, row in insert_frame.iterrows():
        evaluable_sets = []
        deferred_sets = 0
        for unique_set in entity_spec.unique_sets:
            if any(column not in insert_frame.columns for column in unique_set):
                continue
            if any(pd.isna(row[column]) for column in unique_set):
                if pending is not None and any(pending.is_pending_foreign_key(entity_name, column, row_index) for column in unique_set):
                    deferred_sets += 1
                continue
            evaluable_sets.append(unique_set)

        if not evaluable_sets:
            if deferred_sets:
                continue
            diagnostics.append(
                f"Bridge entity '{entity_name}' row '{row_index}' cannot run collision checks "
                "because no complete unique_set is projected"
            )
            continue

        for unique_set in evaluable_sets:
            filters = {column: row[column] for column in unique_set}
            if await collision_checker.row_exists(table_name, filters):
                diagnostics.append(
                    f"Bridge entity '{entity_name}' row '{row_index}' collides with an existing "
                    f"target row in '{table_name}' on unique_set {unique_set}"
                )
                break

    return diagnostics


def _pending_row_mask(pending: PendingDeploymentMap, entity_name: str, index: pd.Index) -> pd.Series:
    """Return a mask of rows whose target ID is pending deployment."""
    mask = pending.pending_row_mask.get(entity_name)
    if mask is None:
        return pd.Series(False, index=index)
    return mask.reindex(index).fillna(False).astype(bool)
