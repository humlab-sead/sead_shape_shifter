"""Fail-closed SIMS capability preflight for the SEAD change request ingester.

Compares the identity work planned for each entity against the SIMS capability
response before orchestration. Unsupported or incomplete operations are recorded
as blocking diagnostics that name the entity and the missing requirement. Child
and derived entities require no SIMS operation and are checked without blocking.
"""

from __future__ import annotations

from typing import Protocol

from ingesters.sead_change_request.contracts import CapabilityPreflightResult, PlannedRowAction, PlannedTable
from src.target_model.effective_identity import resolve_effective_identity
from src.target_model.models import EntitySpec, TargetModel


class EntityCapability(Protocol):
    """Capability entry for one entity type published by SIMS."""

    entity_type: str
    bind_existing: bool
    allocate_new: bool


class CapabilitiesSource(Protocol):
    """Versioned SIMS capability response consumed by preflight."""

    version: str
    entities: list[EntityCapability]


def preflight_capabilities(
    planned: list[PlannedTable],
    target_model: TargetModel,
    capabilities: CapabilitiesSource,
) -> CapabilityPreflightResult:
    """Return a capability check result for the planned identity work.

    Reads the target-model name and version, normalizes each planned entity's
    required SIMS operations from its effective identity mode, and records a
    blocking diagnostic when an operation is missing from the capability
    response or the entity type is not configured. Does not modify any input.
    """
    capability_by_type = {cap.entity_type: cap for cap in capabilities.entities}
    checked_entities: list[str] = []
    diagnostics: list[str] = []

    for planned_table in planned:
        entity_name = planned_table.entity_name
        entity_spec: EntitySpec | None = target_model.entities.get(entity_name)
        if entity_spec is None:
            continue

        checked_entities.append(entity_name)
        required = _required_sims_operations(entity_spec, planned_table)
        if not required:
            continue

        capability = capability_by_type.get(entity_name)
        if capability is None:
            diagnostics.append(f"Entity '{entity_name}' is not configured in SIMS capabilities")
            continue

        if "allocate_new" in required and not capability.allocate_new:
            diagnostics.append(f"Operation 'allocate_new' is not supported for entity type '{entity_name}'")
        if "bind_existing" in required and not capability.bind_existing:
            diagnostics.append(f"Operation 'bind_existing' is not supported for entity type '{entity_name}'")

    return CapabilityPreflightResult(
        model_name=target_model.model.name,
        model_version=target_model.model.version,
        checked_entities=checked_entities,
        diagnostics=diagnostics,
    )


def has_sims_identity_operations(planned: list[PlannedTable], target_model: TargetModel) -> bool:
    """Return whether planned rows require a SIMS identity operation."""
    for planned_table in planned:
        entity_spec = target_model.entities.get(planned_table.entity_name)
        if entity_spec is not None and _required_sims_operations(entity_spec, planned_table):
            return True
    return False


def _required_sims_operations(spec: EntitySpec, planned_table: PlannedTable) -> set[str]:
    """Return the SIMS operations required by the rows actually planned for an entity."""
    effective = resolve_effective_identity(spec)

    if effective.identity_tracking in {"tracked", "reconciled"} and bool(
        (planned_table.planned_actions == PlannedRowAction.ALLOCATE).any()
    ):
        return {"allocate_new"}

    return set()
