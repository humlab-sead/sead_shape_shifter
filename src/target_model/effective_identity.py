"""Shared effective identity resolution for target-model entities.

Computes the effective ``identity_tracking``, ``reconciliation``, and
``aggregate_parent`` values for one entity by applying the documented defaults
from the entity's role and aggregate parent. Target-model validation,
documentation generation, and ingester planning all use the same resolver so
they cannot drift.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.target_model.models import EntitySpec


@dataclass(frozen=True, slots=True)
class EffectiveIdentity:
    """Resolved identity intent for one target-model entity."""

    identity_tracking: str | None
    reconciliation: str | None
    aggregate_parent: str | None


def resolve_effective_identity(spec: EntitySpec) -> EffectiveIdentity:
    """Return the effective identity intent for one target-model entity.

    Reads the declared ``identity_tracking``, ``reconciliation``, and
    ``aggregate_parent`` fields and applies the documented defaults when a
    field is omitted:

    - an ``aggregate_parent`` implies ``identity_tracking: child``;
    - otherwise ``fact`` implies ``tracked``, ``lookup``/``classifier`` imply
      ``reconciled``, and ``bridge`` implies ``derived``;
    - ``tracked`` implies ``reconciliation: allocate``, ``lookup`` implies
      ``reconcile-exact``, ``classifier`` implies ``lookup-only``, ``derived``
      implies ``derive``, and ``child`` has no reconciliation strategy.

    Does not mutate the input spec.
    """
    identity_tracking: str | None = spec.identity_tracking
    reconciliation: str | None = spec.reconciliation
    aggregate_parent: str | None = spec.aggregate_parent

    if identity_tracking is None:
        if aggregate_parent:
            identity_tracking = "child"
        elif spec.role == "fact":
            identity_tracking = "tracked"
        elif spec.role in ("lookup", "classifier"):
            identity_tracking = "reconciled"
        elif spec.role == "bridge":
            identity_tracking = "derived"

    if reconciliation is None:
        if identity_tracking == "child":
            reconciliation = None
        elif identity_tracking == "tracked":
            reconciliation = "allocate"
        elif spec.role == "lookup":
            reconciliation = "reconcile-exact"
        elif spec.role == "classifier":
            reconciliation = "lookup-only"
        elif identity_tracking == "derived":
            reconciliation = "derive"

    return EffectiveIdentity(
        identity_tracking=identity_tracking,
        reconciliation=reconciliation,
        aggregate_parent=aggregate_parent,
    )
