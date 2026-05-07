---
description: "Use for DESIGN.md and other architecture-focused documentation in sead_shape_shifter, including system structure, component boundaries, runtime flows, technical constraints, and major design decisions."
applyTo: "docs/DESIGN.md"
---
# Design Docs

## Purpose

Keep `docs/DESIGN.md` focused on how the system is structured, how its major components interact, and which design decisions shape the codebase. Write for developers who need to understand architecture — not operators, not new contributors learning workflow.

When editing an existing document, preserve its structure unless reorganization is explicitly requested.

## What belongs

- Runtime flows and component interactions
- Module and subsystem responsibilities and boundaries
- External dependencies and integration points
- Data ownership and persistence design
- Cross-cutting concerns: validation, error handling, logging, configuration, security, performance
- Major technical constraints, design decisions, and known tradeoffs

## Scope boundaries

- `docs/DESIGN.md` — architecture, component responsibilities, key flows, cross-cutting concerns, constraints, decisions
- `docs/DIAGRAMS.md` — visual diagrams of the active runtime; historical diagrams in `docs/archive/`
- `docs/DEVELOPMENT.md` — contributor workflow, local setup, common commands
- `docs/TESTING.md` — test strategy, test levels, quality expectations
- `docs/OPERATIONS.md` — deployment, release flow, rollback, observability
- `README.md` — short overview and entry-point links only
- Generated API docs — endpoint request/response details; do not duplicate here
- `docs/archive/` — historical reference only; not authoritative for current design

## Writing rules

- Every section must answer a real design question about structure, boundaries, flows, constraints, or tradeoffs. Remove sections that don't.
- Prefer bullets and focused explanations over narrative prose.
- Do not restate implementation detail obvious from the code unless it clarifies a boundary or constraint.
- Distinguish current design from planned or aspirational. Mark unfinalized areas `TBD`.
- Do not document endpoint details here; link to generated API docs.

## Size expectations

Target 1000–2200 words. Stay under 3000. Move detailed subsystem material into companion design notes or ADRs rather than expanding this file.

## Sources to trust

- `src/` — core domain model and pipeline
- `backend/app/` — API layer, services, and mappers
- `frontend/src/` — component and store structure
- `pyproject.toml` — declared dependencies and package boundaries
- `docker/` — runtime service topology and build configuration
- `AGENTS.md` — canonical architecture rules
- `docs/DIAGRAMS.md` — authoritative visual design
- `docs/DEVELOPMENT.md`, `docs/OPERATIONS.md` — cross-references for scope boundaries

Verify design claims against the current codebase, configuration, and AGENTS.md before documenting them.

## Common failure modes

- Documenting aspirational architecture as if it is implemented behavior
- Duplicating operations or development documentation (deployment, commands, workflow)
- Describing endpoints individually instead of describing API boundaries
- Over-documenting framework internals rather than system-specific design decisions
- Treating archived documentation as current design truth
- Expanding the document into a full developer manual

