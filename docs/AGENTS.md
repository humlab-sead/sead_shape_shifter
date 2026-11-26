# `docs/` — Agent Guide

This directory is the source of truth for project documentation. The files here describe how the system works, how to develop and operate it, and how users complete tasks. "Documentation and Code" in the root `AGENTS.md` says what to do when a document and the code disagree.

> Shared rules are in the root [`AGENTS.md`](../AGENTS.md).

## Scope map

Each main document has a defined scope. Do not add content to the wrong file.

| Document | What it covers |
|---|---|
| `README.md` (repo root) | Project overview, entry-point links, quick start, badges. Not the full developer guide. |
| `DESIGN.md` | System structure, component responsibilities, runtime flows, technical constraints, and major design decisions. |
| `DEVELOPMENT.md` | Local setup, contributor workflow, common commands, coding conventions, and day-to-day development practices. |
| `TESTING.md` | Test strategy, test levels, quality expectations, validation workflow, and repository-specific testing guidance. |
| `OPERATIONS.md` | Runtime environments, deployment, release flow, verification, rollback, recovery, and operational dependencies. |
| `USER_GUIDE.md` | End-user workflows, task-oriented guidance, and common user scenarios. Write for researchers and data managers, not developers. |
| `GLOSSARY.md` | Key Shape Shifter terms for import, transformation, and implementation. |
| `DIAGRAMS.md` | Active runtime diagrams. Historical diagrams go in `docs/archive/`. |
| `CONFIGURATION_GUIDE.md` | Project YAML structure, entity configuration, and field-level reference for `shapeshifter.yml`. |
| `TARGET_MODEL_GUIDE.md` | Target model structure, usage, and how to configure and extend it. |
| `TARGET_MODEL_SCHEMA_REFERENCE.md` | Generated schema reference for the target model YAML format. |

## Writing rules

Read [`writing-style.instructions.md`](../.github/instructions/writing-style.instructions.md) before editing any document. Before editing one of these documents, also read its rules in `.github/instructions/`. They cover audience, content limits, size and the sources to check.

| Document | Rules |
|---|---|
| `DESIGN.md` | `design.instructions.md` |
| `DEVELOPMENT.md` | `development.instructions.md` |
| `TESTING.md` | `testing.instructions.md` |
| `OPERATIONS.md` | `operations.instructions.md` |
| `USER_GUIDE.md` | `user-guide.instructions.md` |
| `GLOSSARY.md` | `glossary.instructions.md` |
| `README.md` (repo root) | `readme.instructions.md` |

## Subdirectory notes

| Directory | Purpose |
|---|---|
| `docs/archive/`   | Historical reference only. |
| `docs/proposals/` | Design proposals and phase plans. Read `.github/instructions/proposal-document-structure.instructions.md` and `.github/instructions/proposal-writing-guide.instructions.md` before editing. |
| `docs/ai/`        | AI-facing comparison notes, prompt notes, and instruction summaries. Treat as reference notes, not policy. |
| `docs/rules/`     | Semantic validation rule definitions. |
| `docs/images/`    | Diagrams and screenshots referenced by other docs. |
| `docs/templates/` | Document templates for new contributors. |
| `docs/testing/`   | Supplementary testing notes and test data documentation. |
| `docs/whats-new/` | Release-note contributor workflow; read `.github/instructions/whats-new-release-notes.instructions.md` when editing versioned notes. |
