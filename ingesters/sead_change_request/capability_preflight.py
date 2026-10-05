"""Fail-closed SIMS capability preflight for the SEAD change request ingester.

Compares the identity work planned for each entity against the SIMS capability
response before orchestration. Unsupported or incomplete operations are recorded
as blocking diagnostics that name the entity and the missing requirement. Child
and derived entities require no SIMS operation and are checked without blocking.
"""

from __future__ import annotations

from typing import Protocol

from ingesters.sead_change_request.contracts import CapabilityPreflightResult, PlannedTable
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
        required = _required_sims_operations(entity_spec)
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


def _required_sims_operations(spec: EntitySpec) -> set[str]:
    """Return the SIMS operations an entity's effective identity mode requires.

    Tracked entities allocate a new tracked aggregate. Reconciled entities bind
    an approved existing aggregate identity; `lookup-only` and `lookup-extensible`
    strategies never allocate, while `reconcile-exact` and `reconcile-fuzzy` may
    allocate after an approved miss. Child and derived entities have no SIMS
    operation.
    """
    effective = resolve_effective_identity(spec)

    if effective.identity_tracking == "tracked":
        return {"allocate_new"}

    if effective.identity_tracking == "reconciled":
        if effective.reconciliation in ("lookup-only", "lookup-extensible"):
            return {"bind_existing"}
        return {"bind_existing", "allocate_new"}

    return set()
