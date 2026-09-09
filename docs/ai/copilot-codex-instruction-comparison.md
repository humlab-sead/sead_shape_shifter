# Copilot and Codex Instruction Comparison

Date: 2026-07-03

This document compares the instruction set seen by:

1. The VS Code GitHub Copilot extension
2. The VS Code Codex extension

It reflects the current repository state. It is not a policy file.

## Summary

The two agents are close on repository-wide architecture rules, but Copilot has a broader and more detailed instruction set because it reads `.github/copilot-instructions.md` and the path-scoped `.github/instructions/*.instructions.md` files.

Codex primarily sees `AGENTS.md` files in the repository tree, plus any home-directory Codex instructions outside the repo. That means Copilot has richer guidance for docs, feature-specific rules, and workflow documents.

## Comparison Table

| Instruction area | Copilot VS Code sees it | Codex VS Code sees it | Parity | Notes |
|---|---|---|---|---|
| Repo-wide baseline | Yes: [`.github/copilot-instructions.md`](/home/roger/source/sead_shape_shifter/.github/copilot-instructions.md) | Yes: [`AGENTS.md`](/home/roger/source/sead_shape_shifter/AGENTS.md) and subtree `AGENTS.md` files | Partial | Both get core architecture and workflow rules, but through different files. |
| Directory-scoped agent rules | Yes: [`src/AGENTS.md`](/home/roger/source/sead_shape_shifter/src/AGENTS.md), [`backend/AGENTS.md`](/home/roger/source/sead_shape_shifter/backend/AGENTS.md), [`frontend/AGENTS.md`](/home/roger/source/sead_shape_shifter/frontend/AGENTS.md), [`ingesters/AGENTS.md`](/home/roger/source/sead_shape_shifter/ingesters/AGENTS.md) | Yes: same files, by nearest-`AGENTS.md` lookup | Good | This is the main place where the two agents are already aligned. |
| Python and frontend code conventions | Yes: [`.github/instructions/python.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/python.instructions.md), [`.github/instructions/frontend.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/frontend.instructions.md), plus `AGENTS.md` | Yes, but only where duplicated in `AGENTS.md` | Partial | Copilot gets explicit path-based instruction files; Codex gets the same themes only where they are repeated in `AGENTS.md`. |
| YAML and project config rules | Yes: [`.github/instructions/project-config.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/project-config.instructions.md), [`.github/instructions/shapeshifter-configuration.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/shapeshifter-configuration.instructions.md) | Partly: [`AGENTS.md`](/home/roger/source/sead_shape_shifter/AGENTS.md) covers the identity system and mapper rules, but not the full YAML rule set | Partial | Copilot has a more detailed config-validation layer than Codex. |
| Docs writing rules | Yes: [`.github/instructions/development.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/development.instructions.md), [`.github/instructions/testing.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/testing.instructions.md), [`.github/instructions/operations.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/operations.instructions.md), [`.github/instructions/user-guide.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/user-guide.instructions.md), [`.github/instructions/readme.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/readme.instructions.md), [`.github/instructions/writing-style.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/writing-style.instructions.md) | No automatic repo equivalent | Weak | This is one of the biggest gaps. Codex does not automatically get these document-scoped rules. |
| Feature-specific engineering rules | Yes: [`.github/instructions/features/validation.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/features/validation.instructions.md), [`.github/instructions/features/materialization.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/features/materialization.instructions.md), [`.github/instructions/features/loaders.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/features/loaders.instructions.md), and others | No automatic equivalent | No | Copilot has much finer-grained guidance for specific code areas. |
| Planning and workflow docs | Yes: [`.github/instructions/phase-plan.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/phase-plan.instructions.md), [`.github/instructions/task-plan.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/task-plan.instructions.md), [`.github/instructions/github-workflow.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/github-workflow.instructions.md) | Only partially via [`AGENTS.md`](/home/roger/source/sead_shape_shifter/AGENTS.md) references | Partial | Codex has the high-level references, but not the full task, phase, and workflow instruction files. |
| Graphify guidance | Yes: mentioned in [`AGENTS.md`](/home/roger/source/sead_shape_shifter/AGENTS.md) and [`.github/copilot-instructions.md`](/home/roger/source/sead_shape_shifter/.github/copilot-instructions.md) | Yes: [`AGENTS.md`](/home/roger/source/sead_shape_shifter/AGENTS.md) | Good | This part is already aligned. |
| Token optimization and `rtk` | Yes: [`AGENTS.md`](/home/roger/source/sead_shape_shifter/AGENTS.md) and [`.github/copilot-instructions.md`](/home/roger/source/sead_shape_shifter/.github/copilot-instructions.md) | Yes: [`AGENTS.md`](/home/roger/source/sead_shape_shifter/AGENTS.md) plus [`~/.codex/RTK.md`](/home/roger/.codex/RTK.md) | Good | Repo-side guidance is aligned; Codex also has a home-level file outside the repo. |
| Global user or home instructions | Not from this repo | Yes: `~/.codex/AGENTS.md` or `~/.codex/AGENTS.override.md` if present | Codex-only | This is outside the repo, so it is not something you can equalize here. |

## Current Gaps

- Copilot has the richer instruction set because it reads the `.github/instructions/**` layer.
- Codex gets the core architecture rules, but not the full set of docs, workflow, and feature-specific instruction files unless those rules are copied into `AGENTS.md`.
- The biggest mismatches are in documentation guidance, planning guidance, and feature-specific validation rules.

## Practical Follow-Up

If you want the two agents to be closer to equal, the most direct change is to copy or summarize the most important `.github/instructions/*.instructions.md` content into the repository `AGENTS.md` files that Codex reads.

The highest-value additions are:

1. Python conventions from [`.github/instructions/python.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/python.instructions.md)
2. Frontend conventions from [`.github/instructions/frontend.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/frontend.instructions.md)
3. YAML and config rules from [`.github/instructions/shapeshifter-configuration.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/shapeshifter-configuration.instructions.md)
4. Testing and writing-style rules from [`.github/instructions/testing.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/testing.instructions.md) and [`.github/instructions/writing-style.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/writing-style.instructions.md)
5. Feature-specific rules for validation, loaders, materialization, and other core flows

## Remediation Plan

Goal: give Codex a repo-local instruction set that is close to the Copilot instruction set without duplicating every `.github/instructions/*.instructions.md` file verbatim.

### Step 1: Add repo-level Codex coverage for `.github` **COMPLETED**

Create:

- [`.github/AGENTS.md`](/home/roger/source/sead_shape_shifter/.github/AGENTS.md)

Purpose:

- Make Codex aware of the same always-on repo guidance that Copilot gets from `.github/copilot-instructions.md`.
- Summarize the instruction families under `.github/instructions/` so Codex can find the right local rules when working in repo metadata, prompts, workflows, and docs support files.

Recommended content to include:

- The same always-on architecture rules already present in the root `AGENTS.md`
- A short index of the instruction files under `.github/instructions/`
- A note that `.github/instructions/*.instructions.md` remain the detailed source for Copilot users

### Step 2: Add docs-scoped Codex coverage **COMPLETED**

Create:

- [`docs/AGENTS.md`](/home/roger/source/sead_shape_shifter/docs/AGENTS.md)

Purpose:

- Give Codex direct instructions for `docs/` work, which is where Copilot currently has the most extra coverage.
- Cover the writing style, scope boundaries, and document-specific rules that are now split across several Copilot instruction files.

Recommended content to include:

- Writing rules for `docs/DEVELOPMENT.md`, `docs/TESTING.md`, `docs/OPERATIONS.md`, `docs/USER_GUIDE.md`, and `docs/DESIGN.md`
- A short note that `docs/archive/` is reference-only
- A link back to the root `AGENTS.md` for core architecture and naming rules

### Step 3: Add a small AI-docs subfolder file

Create:

- [`docs/ai/AGENTS.md`](/home/roger/source/sead_shape_shifter/docs/ai/AGENTS.md)

Purpose:

- Keep AI-facing comparison notes, prompt notes, and instruction summaries under one Codex-visible rule file.
- Prevent future AI instruction docs from drifting away from the repo conventions used elsewhere.

Recommended content to include:

- Treat files in `docs/ai/` as reference notes, not policy
- Prefer concrete comparisons and action lists over broad summaries

### Step 4: Add test-scoped coverage where needed

Create:

- [`tests/AGENTS.md`](/home/roger/source/sead_shape_shifter/tests/AGENTS.md)
- [`backend/tests/AGENTS.md`](/home/roger/source/sead_shape_shifter/backend/tests/AGENTS.md)
- [`frontend/tests/AGENTS.md`](/home/roger/source/sead_shape_shifter/frontend/tests/AGENTS.md)

Purpose:

- Match Copilot’s testing guidance more closely when Codex is editing tests directly.
- Keep test-level expectations close to the test files instead of relying only on the root `AGENTS.md`.

Recommended content to include:

- The applicable testing rules from [`.github/instructions/testing.instructions.md`](/home/roger/source/sead_shape_shifter/.github/instructions/testing.instructions.md)
- The relevant test patterns from the root and subtree `AGENTS.md` files
- A short reminder about async tests, mock boundaries, and supported test commands

### Step 5: Add focused instruction files only where they are still needed

If you want Codex to get even closer to Copilot for specific areas, keep the existing subtree `AGENTS.md` files and add only narrow, local files where Copilot currently has a path-scoped instruction file and Codex still lacks a nearby `AGENTS.md`.

Examples:

- `docs/AGENTS.md` for all docs guidance instead of many separate docs files
- `.github/AGENTS.md` for repository metadata, prompts, workflow notes, and AI instruction summaries
- `tests/AGENTS.md` files for test-specific local guidance when a package or area has its own testing pattern

### Recommended minimum set

If you want the smallest set that gives the biggest gain, add these first:

1. [`.github/AGENTS.md`](/home/roger/source/sead_shape_shifter/.github/AGENTS.md)
2. [`docs/AGENTS.md`](/home/roger/source/sead_shape_shifter/docs/AGENTS.md)
3. [`docs/ai/AGENTS.md`](/home/roger/source/sead_shape_shifter/docs/ai/AGENTS.md)
4. [`tests/AGENTS.md`](/home/roger/source/sead_shape_shifter/tests/AGENTS.md)
5. [`backend/tests/AGENTS.md`](/home/roger/source/sead_shape_shifter/backend/tests/AGENTS.md)
6. [`frontend/tests/AGENTS.md`](/home/roger/source/sead_shape_shifter/frontend/tests/AGENTS.md)

That set does not fully duplicate Copilot’s `.github/instructions/**` model, but it does give Codex most of the missing local coverage in the places where the gap is largest: docs, repo metadata, and tests.
