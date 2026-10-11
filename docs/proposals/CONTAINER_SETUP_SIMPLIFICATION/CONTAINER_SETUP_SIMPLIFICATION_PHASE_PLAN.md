# Container Setup Simplification Phase Plan

## Summary

This plan sequences the [Container Setup Simplification proposal](./CONTAINER_SETUP_SIMPLIFICATION.md). It keeps the Shape Shifter release focused on running the application, provides a tool-agnostic operations handoff without implementing operations tooling, and simplifies the remaining deployment commands.

## Problem

The container release includes host tools and checks for the wider SEAD runtime. Scripts also duplicate configuration and command dispatch. The changes must preserve trusted release validation, lifecycle behavior, and Shape Shifter authorization tests.

## Scope

This plan covers the operations requirements handoff, removal of host-wide operational checks from Shape Shifter, release and host-tool separation, and container command simplification.

It does not include implementing operations scripts or procedures, choosing where operations maintains them, or changing deployment lifecycle behavior.

## Current Position

- The proposal and [SEAD Runtime Verification Handoff](./OPERATIONS_VERIFICATION_HANDOFF.md) define the target ownership split and required operational outcomes.
- Implementing or selecting operations tools and procedures is outside this proposal; no operations owner or delivery location is a prerequisite.
- The host release manager currently runs a verifier from the candidate release bundle.
- Current scripts include separate project commands, configuration helpers, service dispatch, and single- and all-environment deployment scripts.

## Phase Plan

### Phase 1: Separate Runtime Checks And Preserve Application Coverage

**Goal**

Keep ecosystem runtime verification outside Shape Shifter while preserving its application authorization tests.

**Focus**

- Retain the operations handoff as the tool-agnostic requirements deliverable.
- Remove host-wide operational check scripts and fixtures from the Shape Shifter release and source tree.
- Keep Shape Shifter authentication and authorization behavior covered by application tests.
- Do not add a dispatch-only `post-install.sh` wrapper or operations-tool replacements.

**Depends On**

- The proposal decisions and operations handoff.

**Outputs**

- A handoff document defining required operations outcomes without prescribing tools.
- Shape Shifter source and release contents without host-wide operational check implementations.
- Application authorization coverage retained in Shape Shifter.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-3`) The handoff defines the required runtime outcomes, and this work adds no replacement operations tooling.
- `PH1-AC-2` (from `P-AC-4`) Shape Shifter automated tests continue to cover its authentication and authorization behavior.
- `PH1-AC-3` (from `P-AC-5`) No dispatch-only `post-install.sh` is added; the handoff states that routine checks should not change system state and state-changing actions must be explicit.

**Validation Milestones**

- `VM-1` Confirm each required operations outcome is present in the handoff and no operations implementation is included (`PH1-AC-1`, `PH1-AC-3`).
- `VM-2` Confirm application authorization behavior remains covered by automated tests (`PH1-AC-2`).

**Task-Plan Handoff**

- Treat the linked handoff as the required outcomes document, not as an implemented operations procedure.
- Operations selects and implements its own tools and procedures independently.
- Preserve application authorization policy and tests; do not retain deployed operational checks in Shape Shifter.

**Readiness**

Ready for a task plan.

### Phase 2: Separate Release Contents And Trusted Validation

**Goal**

Exclude host tools from release archives and validate releases without executing candidate-supplied code.

**Focus**

- Keep only deployment-user runtime contents in the archive.
- Move host provisioning and installer tools outside the archive.
- Move source and archive release-policy checks to the release workflow.
- Make the host manager validate downloaded archive integrity and required content using trusted code.
- Rename `deploy_single_environment.sh` to `deploy_environment.sh` and remove `deploy_all_environments.sh`.

**Depends On**

- Phase 1 removes ecosystem operational checks from Shape Shifter.

**Outputs**

- A release archive containing required deployment-user runtime files only.
- Release workflow and host-manager checks that do not execute an archive-supplied verifier.
- Host provisioning outside the release, with one explicit single-environment command.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`) Release archives exclude host provisioning and ecosystem runtime checks and contain the required deployment-user runtime files.
- `PH2-AC-2` (from `P-AC-2`) The workflow checks source and archive policy; the host manager validates downloaded archives with trusted code and never runs a candidate-supplied verifier.
- `PH2-AC-3` (from `P-AC-6`) Host provisioning uses `deploy_environment.sh`; `deploy_all_environments.sh` is removed.
- `PH2-AC-4` (from `P-AC-8`) Release selection, checksum, archive-safety, service, and rollback behavior remain intact.

**Validation Milestones**

- `VM-3` Confirm archive contents match the runtime-file contract and exclude host and ecosystem operational tools (`PH2-AC-1`).
- `VM-4` Confirm valid and invalid archives are handled by trusted workflow and host-manager checks without executing candidate code (`PH2-AC-2`).
- `VM-5` Confirm the single-environment command has the new name and the all-environments command has no active caller (`PH2-AC-3`).
- `VM-6` Confirm release selection, integrity checks, service behavior, and rollback remain unchanged (`PH2-AC-4`).

**Task-Plan Handoff**

- Preserve release tag/version policy and the install, activate, and rollback contract.
- Keep archive path safety, checksum, expected root/version, and required-file validation.
- Choose a source-only host-tools location that cannot enter release archives.
- Do not wait for operations tooling implementation before removing Shape Shifter's operational checks.

**Readiness**

Ready for a task plan.

### Phase 3: Simplify Remaining Container Commands

**Goal**

Remove duplicated helper names, defaults, and dispatch while preserving current command behavior.

**Focus**

- Rename sourced helpers to `_load-env.sh` and `_env-config.sh`, keeping their distinct responsibilities.
- Resolve shared deployment defaults in one place.
- Route service actions through `container.sh service <action>`.
- Replace `adopt-project.sh` and `move-project.sh` with `project.sh adopt|move`.
- Remove dead scripts and targets and update active references.

**Depends On**

- Phase 2 establishes the release contents and source-only host-tools location.

**Outputs**

- Clearly named internal configuration helpers with updated callers.
- One project command entry point for `adopt` and `move`.
- One service-action dispatch path and one source of shared defaults.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-6`) The sourced helpers are `_load-env.sh` and `_env-config.sh` with separate responsibilities; defaults, service dispatch, and project commands use the proposed single implementations without changing intended behavior.
- `PH3-AC-2` (from `P-AC-7`) Removed scripts and targets have no active callers, and active documentation and workflows use valid paths.
- `PH3-AC-3` (from `P-AC-8`) Service and rollback behavior remain intact.

**Validation Milestones**

- `VM-7` Confirm helper callers, direct commands, and Makefile targets resolve the same intended configuration and actions (`PH3-AC-1`).
- `VM-8` Confirm removed or renamed paths have no active callers and active references resolve (`PH3-AC-2`).
- `VM-9` Confirm service and rollback behavior remain unchanged (`PH3-AC-3`).

**Task-Plan Handoff**

- Preserve each project's current validation and safety behavior, including dry-run, confirmation, and rollback for `move`.
- Keep `_load-env.sh` responsible for loading deployment configuration and resolving paths; keep `_env-config.sh` responsible for image-tag and environment-file functions.
- Do not combine the helpers into a generic `_common.sh`.
- Add no future project commands until their behavior is defined.

**Readiness**

Ready for a task plan.

## Cross-Phase Rules

- Do not add operations scripts or procedures to Shape Shifter; the handoff states required outcomes only.
- Keep Shape Shifter authorization behavior covered by application tests.
- Never use code from a candidate archive to validate that same archive.
- Avoid wrapper-only entry points and keep active documentation aligned with the implementation.

## Validation Strategy

- Validate each phase's acceptance criteria before completing dependent changes.
- Use application tests for authorization behavior and release/workflow checks for archive validation.
- Confirm the release bundle excludes host and ecosystem operational tools.
- Exact commands, files, fixtures, and assertions belong in each phase task plan.
