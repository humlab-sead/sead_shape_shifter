# `docs/` — Agent Guide

This directory is the source of truth for project documentation. The files here define how the system works, how to develop and operate it, and how users complete tasks. Do not treat `docs/archive/` or `docs/features/` as authoritative.

> Repo-wide architecture rules are in the root [`AGENTS.md`](../AGENTS.md). Read that file alongside this one when working in `docs/`.

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

These rules apply to all documents in `docs/`.

- Write for the intended audience of each document. `DESIGN.md` targets developers. `USER_GUIDE.md` targets researchers and data managers. `OPERATIONS.md` targets operators.
- State the purpose before details. Use numbered steps for procedures.
- Name the actual thing, action, rule, input, output, or result. Avoid vague or overloaded wording.
- Preserve document structure and register when editing. Do not normalize existing style across the whole document unless that is the task.
- State defaults, required fields, constraints, tradeoffs, and error cases explicitly.
- Keep code blocks, paths, YAML, and identifiers exact. Do not paraphrase technical values.
- Every section should answer a real question from the document's target audience. If a section does not support action or understanding, shorten or remove it.
- Distinguish current design from planned (next release cycle) or aspirational (long-term, no defined timeline). Mark sections not yet implemented with `TBD`.
- Mark intentionally undefined processes `TBD` rather than inventing process.

## Document-specific rules

### `DESIGN.md`

- Cover system structure, component interactions, data ownership, cross-cutting concerns, constraints, and tradeoffs.
- Do not include endpoint details; link to generated API docs.
- Target 1000–2200 words; stay under 3000.
- Read `.github/instructions/design.instructions.md` before editing.

### `DEVELOPMENT.md`

- Cover local setup, bootstrap steps, common commands, coding conventions, and validation workflow before commit.
- Do not include runtime deployment, production configuration, or operational procedures.
- Target 800–1800 words; stay under 2500.
- Verify claims against `Makefile`, `pyproject.toml`, `.python-version`, and `.github/workflows/` before writing them.
- Read `.github/instructions/development.instructions.md` before editing.

### `TESTING.md`

- Cover test strategy, test levels and their responsibilities, execution commands, test environment expectations, and fixture and mock policy.
- Do not include local bootstrap steps, deployment procedures, or line-by-line explanations of individual test files.
- Read `.github/instructions/testing.instructions.md` before editing.

### `OPERATIONS.md`

- Cover environments, runtime configuration, deployment flow, CI/CD, verification, rollback, health checks, and incident basics.
- Do not include local development setup or contributor workflow.
- Read `.github/instructions/operations.instructions.md` before editing.

### `USER_GUIDE.md`

- Write for researchers, data managers, and SEAD contributors who are not developers.
- Organize progressively: quick-start workflow first, common workflows next, advanced topics last.
- Do not include architecture explanations, YAML schema reference, API reference, or implementation detail.
- Read `.github/instructions/user-guide.instructions.md` before editing.

### `GLOSSARY.md`

- Use the fixed three-section structure: Data Import and Target Domain / Shape Shifter Transformation Concepts / Implementation and Architecture Concepts.
- Do not frame Shape Shifter as SEAD-specific. Use "target model", "target schema", or "downstream system". SEAD appears only as an example.
- Read `.github/instructions/glossary.instructions.md` before editing.

### `README.md` (repo root)

- Keep it short: project description, badges, high-level features, quick start, prerequisites, links to the main docs.
- Do not add detailed setup, test commands, deployment procedures, or environment variable catalogs.
- Read `.github/instructions/readme.instructions.md` before editing.

## Subdirectory notes

| Directory | Purpose |
|---|---|
| `docs/archive/`   | Historical reference only. Do not treat as the source of truth for current practice. |
| `docs/features/`  | Feature backlog. Not authoritative implementation guidance unless the user is asking about planned features. |
| `docs/proposals/` | Design proposals and phase plans. Read `.github/instructions/proposal-document-structure.instructions.md` and `.github/instructions/proposal-writing-guide.instructions.md` before editing. |
| `docs/ai/`        | AI-facing comparison notes, prompt notes, and instruction summaries. Treat as reference notes, not policy. |
| `docs/rules/`     | Semantic validation rule definitions. |
| `docs/images/`    | Diagrams and screenshots referenced by other docs. |
| `docs/templates/` | Document templates for new contributors. |
| `docs/testing/`   | Supplementary testing notes and test data documentation. |
| `docs/whats-new/` | Release notes and change summaries. |
