"""Insert-order planning for selected target-model entities.

The change-request ingester renders target inserts in package order. This module
derives the order required by declared aggregate-parent and foreign-key
dependencies for the entities selected for insertion, and reports dependency
cycles before any target row is written.

The module is pure: it reads the target model and caller selections only.

Rules:

- An aggregate-parent link creates an edge when both entities are inserted.
- A required foreign key creates an edge when both entities are inserted.
- A conditional foreign key (``required_when``) is required for the owning
  entity whenever that entity is inserted, so it also creates an edge.
- An optional foreign key creates an edge only when the caller reports that the
  relationship is present in the submitted rows.
- A reference-only row creates no edge: its target row already exists, and its
  target ID is resolved before insertion.

Edges whose owning entity or target entity is not inserted are omitted. The
caller is responsible for resolving those IDs before the insert runs.
"""

from __future__ import annotations

import heapq
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from src.target_model.models import TargetModel

AGGREGATE_PARENT_EDGE = "aggregate_parent"
REQUIRED_FOREIGN_KEY_EDGE = "required_foreign_key"
PRESENT_OPTIONAL_FOREIGN_KEY_EDGE = "present_optional_foreign_key"


@dataclass(frozen=True, slots=True)
class InsertDependencyEdge:
    """One insert-order requirement between two selected entities."""

    entity: str
    """Entity that must be inserted after ``requires``."""

    requires: str
    """Entity that must be inserted first."""

    reason: str
    """Which declaration produced the edge."""


@dataclass(frozen=True, slots=True)
class InsertPlan:
    """Insert order and dependency cycle report for a selected entity set.

    ``order`` lists every selected entity when the graph is acyclic. When a cycle
    exists, it lists the entities that can still be inserted first, in
    dependency order. ``cycles`` holds one canonically sorted member tuple per
    dependency cycle, including self-referencing required foreign keys.
    """

    order: tuple[str, ...]
    edges: tuple[InsertDependencyEdge, ...]
    cycles: tuple[tuple[str, ...], ...]

    @property
    def is_acyclic(self) -> bool:
        """Return ``True`` when no dependency cycle exists."""
        return not self.cycles


def build_insert_plan(
    target_model: TargetModel,
    insert_entities: Iterable[str],
    *,
    present_optional_foreign_keys: Iterable[tuple[str, str]] = (),
) -> InsertPlan:
    """Return the insert dependency plan for the selected entities.

    Args:
        target_model: Target model that declares aggregate parents and foreign
            keys.
        insert_entities: Entity names whose rows this submission inserts.
        present_optional_foreign_keys: ``(entity, target)`` pairs for optional
            foreign keys that the submitted rows actually use.

    Raises:
        ValueError: If an entity name or optional foreign-key pair is not
            declared in the target model.

    Entities are inserted in dependency order with alphabetical ordering among
    entities that are ready at the same time, so the same selection always
    produces the same order.
    """
    insert_set = set(insert_entities)
    unknown_entities = insert_set.difference(target_model.entities)
    if unknown_entities:
        raise ValueError(f"Unknown insert entities: {', '.join(sorted(unknown_entities))}")

    present_optional = _validate_present_optional_foreign_keys(target_model, present_optional_foreign_keys)
    edges = _collect_edges(target_model, insert_set, present_optional)
    dependency_pairs = {(edge.entity, edge.requires) for edge in edges.values()}

    order, remaining = _dependency_order(insert_set, dependency_pairs)
    cycles = _dependency_cycles(remaining, dependency_pairs)

    sorted_edges = tuple(edges[key] for key in sorted(edges))
    return InsertPlan(order=tuple(order), edges=sorted_edges, cycles=cycles)


def _validate_present_optional_foreign_keys(
    target_model: TargetModel,
    present_optional_foreign_keys: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    """Return validated optional foreign-key pairs without duplicates."""
    pairs: list[tuple[str, str]] = []
    for entity_name, required_name in present_optional_foreign_keys:
        if entity_name not in target_model.entities:
            raise ValueError(f"Unknown entity '{entity_name}' in present optional foreign keys")
        if required_name not in target_model.entities:
            raise ValueError(f"Unknown target entity '{required_name}' in present optional foreign keys")
        optional_targets = {
            foreign_key.entity
            for foreign_key in target_model.entities[entity_name].foreign_keys
            if not foreign_key.required and foreign_key.via is None
        }
        if required_name not in optional_targets:
            raise ValueError(f"Entity '{entity_name}' has no optional foreign key to '{required_name}'")
        pair = (entity_name, required_name)
        if pair not in pairs:
            pairs.append(pair)
    return tuple(pairs)


def _collect_edges(
    target_model: TargetModel,
    insert_set: set[str],
    present_optional: tuple[tuple[str, str], ...],
) -> dict[tuple[str, str, str], InsertDependencyEdge]:
    """Return deduplicated dependency edges for the selected entities."""
    edges: dict[tuple[str, str, str], InsertDependencyEdge] = {}

    def add(entity: str, requires: str, reason: str) -> None:
        key = (entity, requires, reason)
        edges[key] = InsertDependencyEdge(entity=entity, requires=requires, reason=reason)

    for entity_name in sorted(insert_set):
        entity_spec = target_model.entities[entity_name]

        if entity_spec.aggregate_parent and entity_spec.aggregate_parent in insert_set:
            add(entity_name, entity_spec.aggregate_parent, AGGREGATE_PARENT_EDGE)

        for foreign_key in entity_spec.foreign_keys:
            if foreign_key.via is not None or foreign_key.entity not in insert_set:
                continue
            conditional = foreign_key.required or (
                foreign_key.required_when is not None and foreign_key.required_when.has_new_rows == entity_name
            )
            if conditional:
                add(entity_name, foreign_key.entity, REQUIRED_FOREIGN_KEY_EDGE)

    for entity_name, required_name in present_optional:
        if entity_name in insert_set and required_name in insert_set:
            add(entity_name, required_name, PRESENT_OPTIONAL_FOREIGN_KEY_EDGE)

    return edges


def _dependency_order(
    insert_set: set[str],
    dependency_pairs: set[tuple[str, str]],
) -> tuple[list[str], set[str]]:
    """Return a deterministic dependency order and the entities it could not place."""
    dependents: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {entity_name: 0 for entity_name in insert_set}
    for entity_name, required_name in dependency_pairs:
        if entity_name == required_name:
            # A self-reference cannot be ordered by entity; the cycle report
            # names it instead of blocking every other entity.
            continue
        dependents[required_name].add(entity_name)
        indegree[entity_name] += 1

    ready: list[str] = [entity_name for entity_name, count in indegree.items() if count == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        entity_name = heapq.heappop(ready)
        order.append(entity_name)
        for dependent in sorted(dependents[entity_name]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)

    placed = set(order)
    return order, insert_set.difference(placed)


def _dependency_cycles(
    remaining: set[str],
    dependency_pairs: set[tuple[str, str]],
) -> tuple[tuple[str, ...], ...]:
    """Return one sorted member tuple per cycle among the selected entities.

    A self-referencing required foreign key is a cycle even though the entity can
    still be inserted: its rows must be ordered among themselves.
    """
    self_references = {(entity,) for entity, required in dependency_pairs if entity == required}

    remaining_pairs = {(entity, required) for entity, required in dependency_pairs if entity in remaining and required in remaining}
    components = _strongly_connected_components(remaining, remaining_pairs) if remaining else []
    cycles = {tuple(sorted(component)) for component in components if len(component) > 1}

    if not cycles and not self_references:
        return ()
    return tuple(sorted(cycles.union(self_references)))


def _strongly_connected_components(
    entities: set[str],
    dependency_pairs: set[tuple[str, str]],
) -> list[set[str]]:
    """Return strongly connected components using Tarjan's algorithm."""
    adjacency: dict[str, list[str]] = {entity_name: [] for entity_name in entities}
    for entity_name, required_name in sorted(dependency_pairs):
        adjacency[entity_name].append(required_name)

    index_by_entity: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    components: list[set[str]] = []
    next_index = 0

    def visit(entity_name: str) -> None:
        nonlocal next_index
        index_by_entity[entity_name] = next_index
        lowlink[entity_name] = next_index
        next_index += 1
        stack.append(entity_name)
        on_stack.add(entity_name)

        for required_name in adjacency[entity_name]:
            if required_name not in index_by_entity:
                visit(required_name)
                lowlink[entity_name] = min(lowlink[entity_name], lowlink[required_name])
            elif required_name in on_stack:
                lowlink[entity_name] = min(lowlink[entity_name], index_by_entity[required_name])

        if lowlink[entity_name] == index_by_entity[entity_name]:
            component: set[str] = set()
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.add(member)
                if member == entity_name:
                    break
            components.append(component)

    for entity_name in sorted(entities):
        if entity_name not in index_by_entity:
            visit(entity_name)

    return components
