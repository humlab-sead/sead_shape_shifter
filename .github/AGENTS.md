# `.github/` — Agent Guide

This directory holds Copilot and Codex instruction files, prompt templates, and workflow definitions for the Shape Shifter repository.

> Repo-wide architecture rules are in the root [`AGENTS.md`](../AGENTS.md). Read that file first. This file adds the instruction index below, which is the main thing Codex does not get automatically when working in this directory.

## Instruction file index

The files under `instructions/` are the detailed source of truth for Copilot. Codex should read the relevant file before working in the matching area.

### Code conventions

| File                                    | When to read it                                                 |
|-----------------------------------------|-----------------------------------------------------------------|
| `instructions/python.instructions.md`   | Editing Python in `src/`, `backend/`, `ingesters/`, or `tests/` |
| `instructions/frontend.instructions.md` | Editing Vue, Pinia, or TypeScript in `frontend/src/`            |

### Configuration and YAML

| File                                                      | When to read it                                                |
|-----------------------------------------------------------|----------------------------------------------------------------|
| `instructions/shapeshifter-configuration.instructions.md` | Editing or validating `shapeshifter.yml` and other project YAML files |

### Feature-specific engineering rules

These files live under `instructions/features/` and cover specific subsystems.

| File                                                    | When to read it                                                         |
|---------------------------------------------------------|-------------------------------------------------------------------------|
| `instructions/features/entities.instructions.md`        | Working on entity models or entity-related services                     |
| `instructions/features/execution.instructions.md`       | Working on normalizer, workflow, or process state                       |
| `instructions/features/graph.instructions.md`           | Working on graph components or Cytoscape integration in the frontend    |
| `instructions/features/ingesters.instructions.md`       | Adding or editing ingester implementations                              |
| `instructions/features/loaders.instructions.md`         | Adding or editing data loaders                                          |
| `instructions/features/materialization.instructions.md` | Working on materialization services or endpoints                        |
| `instructions/features/reconciliation.instructions.md`  | Working on reconciliation services or the reconciliation client         |
| `instructions/features/specifications.instructions.md`  | Working on project specifications or constraint validators              |
| `instructions/features/target-model.instructions.md`    | Working on target model validation or the target model schema           |
| `instructions/features/transforms.instructions.md`      | Working on transform dispatch or transform implementations              |
| `instructions/features/validation.instructions.md`      | Working on validators in `src/validators/` or `backend/app/validators/` |

### Documentation

| File                                         | When to read it                                              |
|----------------------------------------------|--------------------------------------------------------------|
| `instructions/writing-style.instructions.md` | Writing any docs, comments, docstrings, or PR text           |
| `instructions/development.instructions.md`   | Editing `docs/DEVELOPMENT.md` or developer-facing setup docs |
| `instructions/testing.instructions.md`       | Editing `docs/TESTING.md` or writing test guidance           |
| `instructions/operations.instructions.md`    | Editing `docs/OPERATIONS.md` or deployment and runbook docs  |
| `instructions/user-guide.instructions.md`    | Editing `docs/USER_GUIDE.md` or end-user task docs           |
| `instructions/readme.instructions.md`        | Editing `README.md`                                          |
| `instructions/design.instructions.md`        | Editing `docs/DESIGN.md` or architecture documentation       |
| `instructions/glossary.instructions.md`      | Editing `docs/GLOSSARY.md`                                   |

### Planning and workflow

| File                                                       | When to read it                                                   |
|------------------------------------------------------------|-------------------------------------------------------------------|
| `instructions/github-workflow.instructions.md`             | Creating a GitHub issue, preparing a commit, or writing a handoff |
| `instructions/phase-plan.instructions.md`                  | Creating or updating a phased implementation plan                 |
| `instructions/task-plan.instructions.md`                   | Creating or updating a task plan for one development phase        |
| `instructions/proposal-document-structure.instructions.md` | Creating or editing proposal documents in `docs/proposals/`       |
| `instructions/proposal-writing-guide.instructions.md`      | Writing or updating design proposals                              |
| `instructions/diagrams.instructions.md`                    | Creating or editing Mermaid diagrams anywhere in the repository   |
| `instructions/semantic-rules.instructions.md`              | Creating or maintaining semantic validation rules                 |

## Notes for Codex

- These `.instructions.md` files are the detailed source for Copilot users and are injected automatically by path-based `applyTo` rules. Codex must read the relevant file explicitly before starting work in the matching area.
- `docs/archive/` is reference-only; ignore it unless the user specifically asks about historical content.
- `docs/features/` is a backlog, not authoritative implementation guidance.
- The root `AGENTS.md` remains the primary always-on reference. This file adds directory-level context and the instruction index only.
