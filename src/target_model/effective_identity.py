"""Shared effective identity resolution for target-model entities.

Computes the effective ``identity_tracking``, ``reconciliation``, and
``aggregate_parent`` values for one entity by applying the documented defaults
from the entity's role and aggregate parent. Target-model validation,
documentation generation, and ingester planning all use the same resolver so
they cannot drift.

Also resolves an entity's full aggregate-parent chain to the tracked or
reconciled root that owns its identity. Aggregate children receive their target
IDs from the root, so callers that plan deployment-time ID allocation need the
root entity and a chain that ends at a supported root.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.target_model.models import EntitySpec, TargetModel

AGGREGATE_ROOT_IDENTITIES: frozenset[str] = frozenset({"tracked", "reconciled"})
"""Effective identity values that can own an aggregate child's target ID."""


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


@dataclass(frozen=True, slots=True)
class AggregateChainIssue:
    """Problem found while resolving one entity's aggregate ownership chain.

    ``entity`` names the entity whose chain was resolved, which may differ from
    the entity named in ``message`` when the problem sits further up the chain.
    ``cycle`` carries the canonical cycle members for ``AGGREGATE_PARENT_CYCLE``
    so callers can report one cycle only once.
    """

    code: str
    message: str
    entity: str
    cycle: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class AggregateChain:
    """Resolved aggregate ownership for one target-model entity.

    ``parent_chain`` starts with the immediate aggregate parent and ends with
    the root entity. ``root_identity_tracking`` holds the root's effective
    identity, which must be ``tracked`` or ``reconciled`` before the child can
    receive a deployment-time target ID.
    """

    entity: str
    parent_chain: tuple[str, ...]
    root_entity: str | None
    root_identity_tracking: str | None
    root_reconciliation: str | None
    issues: tuple[AggregateChainIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return ``True`` when the chain ends at a supported root without issues."""
        return not self.issues

    @property
    def entity_chain(self) -> tuple[str, ...]:
        """Return the entity followed by its ordered parent chain."""
        return (self.entity, *self.parent_chain)


def resolve_aggregate_chain(target_model: TargetModel, entity_name: str) -> AggregateChain:
    """Return the aggregate-parent chain and root identity for one entity.

    Walks the declared ``aggregate_parent`` links until an entity without a
    parent is reached. That terminal entity is the root. An entity without an
    ``aggregate_parent`` is its own root, which lets callers ask about roots and
    children with the same function.

    Reports unknown entities and parents, self-references, multi-entity cycles,
    terminal roots that are neither tracked nor reconciled, and missing
    ``public_id`` metadata on the child or the root. Cycle members are rotated
    so every entity in the cycle reports the same ``cycle`` tuple.

    Does not mutate the target model.
    """
    entity_spec = target_model.entities.get(entity_name)
    if entity_spec is None:
        return AggregateChain(
            entity=entity_name,
            parent_chain=(),
            root_entity=None,
            root_identity_tracking=None,
            root_reconciliation=None,
            issues=(
                AggregateChainIssue(
                    code="UNKNOWN_AGGREGATE_CHILD",
                    message=f"Entity '{entity_name}' is not part of the target model",
                    entity=entity_name,
                ),
            ),
        )

    if entity_spec.aggregate_parent is None:
        if entity_spec.identity_tracking == "child":
            return AggregateChain(
                entity=entity_name,
                parent_chain=(),
                root_entity=None,
                root_identity_tracking=None,
                root_reconciliation=None,
                issues=(
                    AggregateChainIssue(
                        code="CHILD_IDENTITY_MISSING_AGGREGATE_PARENT",
                        message=f"Entity '{entity_name}' declares identity_tracking 'child' but has no aggregate_parent",
                        entity=entity_name,
                    ),
                ),
            )
        effective = resolve_effective_identity(entity_spec)
        return AggregateChain(
            entity=entity_name,
            parent_chain=(),
            root_entity=entity_name,
            root_identity_tracking=effective.identity_tracking,
            root_reconciliation=effective.reconciliation,
        )

    parent_chain: list[str] = []
    visited: list[str] = [entity_name]
    current_name = entity_name
    current_spec = entity_spec

    while current_spec.aggregate_parent is not None:
        parent_name = current_spec.aggregate_parent

        if parent_name == current_name:
            issue = AggregateChainIssue(
                code="SELF_REFERENTIAL_AGGREGATE_PARENT",
                message=f"Entity '{current_name}' cannot use itself as aggregate_parent",
                entity=entity_name,
            )
            return AggregateChain(entity_name, tuple(parent_chain), None, None, None, (issue,))

        parent_spec = target_model.entities.get(parent_name)
        if parent_spec is None:
            issue = AggregateChainIssue(
                code="UNKNOWN_AGGREGATE_PARENT",
                message=f"Entity '{current_name}' references unknown aggregate_parent '{parent_name}'",
                entity=entity_name,
            )
            return AggregateChain(entity_name, tuple(parent_chain), None, None, None, (issue,))

        if parent_name in visited:
            cycle = _canonical_cycle(visited[visited.index(parent_name) :])
            issue = AggregateChainIssue(
                code="AGGREGATE_PARENT_CYCLE",
                message=f"Aggregate parents form a cycle: {' -> '.join((*cycle, cycle[0]))}",
                entity=entity_name,
                cycle=cycle,
            )
            return AggregateChain(entity_name, tuple(parent_chain), None, None, None, (issue,))

        parent_chain.append(parent_name)
        visited.append(parent_name)
        current_name = parent_name
        current_spec = parent_spec

    root_spec = current_spec
    root_effective = resolve_effective_identity(root_spec)
    issues: list[AggregateChainIssue] = []

    if root_effective.identity_tracking not in AGGREGATE_ROOT_IDENTITIES:
        issues.append(
            AggregateChainIssue(
                code="INVALID_AGGREGATE_ROOT_IDENTITY",
                message=(
                    f"Entity '{entity_name}' resolves to root '{current_name}' with identity_tracking "
                    f"'{root_effective.identity_tracking}'; aggregate roots must be tracked or reconciled"
                ),
                entity=entity_name,
            )
        )

    if not entity_spec.public_id:
        issues.append(
            AggregateChainIssue(
                code="AGGREGATE_CHILD_MISSING_PUBLIC_ID",
                message=f"Aggregate child '{entity_name}' must declare public_id",
                entity=entity_name,
            )
        )

    if not root_spec.public_id:
        issues.append(
            AggregateChainIssue(
                code="AGGREGATE_ROOT_MISSING_PUBLIC_ID",
                message=f"Aggregate root '{current_name}' of entity '{entity_name}' must declare public_id",
                entity=entity_name,
            )
        )

    return AggregateChain(
        entity=entity_name,
        parent_chain=tuple(parent_chain),
        root_entity=current_name,
        root_identity_tracking=root_effective.identity_tracking,
        root_reconciliation=root_effective.reconciliation,
        issues=tuple(issues),
    )


def _canonical_cycle(cycle: list[str]) -> tuple[str, ...]:
    """Rotate a cycle so it starts at its smallest member name."""
    start = min(range(len(cycle)), key=lambda index: cycle[index])
    return tuple(cycle[start:] + cycle[:start])
