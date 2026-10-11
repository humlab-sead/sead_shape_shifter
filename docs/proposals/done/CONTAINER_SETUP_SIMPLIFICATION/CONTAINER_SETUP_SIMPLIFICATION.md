# Simplify Container Releases And Separate Operations Checks

## Status

- **Implemented and archived** (2026-10-11); PR #543 merged phases 1-3 to `dev`.
- Validation: each phase passed its task-plan validation milestones; the release-contract, project-command, and release-bundle test suites pass, with Podman/systemd-touching suites left to CI.
- Scope: container release contents, deployment scripts, verification ownership, and related documentation
- Goal: Keep the Shape Shifter container setup small while handing ecosystem runtime checks to SEAD operations
- Layout: paths name the current `deployment/` tree (`deployment/container/` for the release bundle, `deployment/container-host/` for the source-only host tools); a release archive still unpacks under a single `container/` root

## Summary

Keep the deployable `~/container` bundle focused on running Shape Shifter. Move host provisioning out of the release, hand ecosystem-wide runtime checks to SEAD operations, and simplify duplicated configuration and command dispatch.

Shape Shifter should retain automated tests for its own authorization behavior and source-level release checks. Operators should use the tools and procedures they already manage for runtime checks such as database access, credential rotation, log review, network exposure, and recovery. Do not add a `post-install.sh` layer that only dispatches to other checks.

## Problem

The container setup repeats deployment defaults, has overlapping configuration helpers and command dispatch, and includes host provisioning in each release archive.

The verification directory also mixes application tests with checks for the wider SEAD runtime. Those checks cover firewall exposure, database grants, credentials, logs, proxy identity, application-user grants, and rollback. Shipping them with Shape Shifter makes the application release responsible for operational work that spans multiple services and systems.

The release manager currently runs the verifier found inside the candidate archive. A candidate must not supply the code trusted to validate that candidate.

## Scope

- Limit the release archive to files needed from the deployment user's `~/container` directory.
- Move host provisioning tools outside the release archive.
- Hand runtime and ecosystem verification requirements to SEAD operations through the [operations verification handoff](./OPERATIONS_VERIFICATION_HANDOFF.md).
- Keep Shape Shifter authorization behavior covered by automated application tests.
- Keep release checks outside the deployable bundle and prevent the host release manager from executing candidate-supplied verification code.
- Consolidate duplicated configuration, defaults, and command dispatch; remove dead scripts and targets.
- Update active documentation, workflows, and tests to match the new ownership.

## Non-Goals

- Changing the release tag scheme, publication trigger, or install/activate/rollback selection contract.
- Changing application image build behavior, `GIT_REF`, or `IMAGE_NAME`.
- Redesigning authorization policy, NGINX, systemd, database roles, or SEAD operations procedures.
- Implementing or selecting SEAD operations scripts, procedures, repository, tools, schedule, alerting, or evidence system. The handoff document is the deliverable for this proposal.
- Removing release-manager checksum, archive-safety, version, or required-content checks.

## Current Behavior

Verified 2026-10-11 on branch `container-deploy-versioning`, after commit `a3adcbde`.

- The Makefile, `scripts/container.sh`, and `scripts/load-env.sh` each apply defaults for shared deployment values.
- `scripts/container.sh` and `scripts/service.sh` both dispatch actions, and the Makefile repeats their target lists.
- `scripts/load-env.sh` and `scripts/env-config.sh` are sourced helpers with distinct roles: one loads deployment configuration and resolves paths; the other provides image-tag and environment-file functions.
- Host provisioning scripts under `deployment/container/scripts/deploy/` are included in release archives.
- `.github/workflows/container-release.yml` invokes `verify_container_release.sh` for source and archive checks. The host release manager also invokes the verifier found in the candidate bundle.
- The verification directory contains release checks, deployed API probes, host checks, and orchestration. The test-environment orchestrator also reconciles authorization by default.

## Proposed Design

### 1. Keep the release focused on running Shape Shifter

The release archive should contain only files the deployment user needs from `~/container`. Move host provisioning, installer, and release-management tools to a source-only location outside the archive. Keep `shape-shifter-container-release` separate from the deployment user's lifecycle commands.

### 2. Hand runtime verification to SEAD operations

SEAD operations owns checks for firewall and network exposure, deployed container configuration, database accounts and grants, authorization-store protection, credential rotation, log scanning, proxy identity, deployed application-user grants, and rollback/recovery.

Use the [operations verification handoff](./OPERATIONS_VERIFICATION_HANDOFF.md) to state required outcomes. This proposal does not implement or select operations tooling. Do not add a new Shape Shifter `post-install.sh` or another wrapper that only sequences existing checks.

Remove host-wide operational check scripts and their fixtures from the Shape Shifter release and source tree; do not replace them with new operations scripts here. SEAD operations can use the handoff requirements with its existing tools and procedures. Keep Shape Shifter's application authorization policy and automated tests in its source repository.

### 3. Keep release validation trusted and outside the bundle

Move release-policy checks out of `deployment/container/scripts/verify/` and the deployable archive. The release workflow should validate the source tree, tag/version policy, required release content, and built archive.

The host release manager must independently validate downloaded content using trusted code it already owns: checksum, safe archive paths, expected archive root and version, and required files. It must not execute a verifier extracted from the candidate archive. Do not add another standalone verifier solely to dispatch checks between the workflow and the manager.

### 4. Simplify configuration and commands

- Rename `load-env.sh` and `env-config.sh` to `_load-env.sh` and `_env-config.sh` to mark them as internal sourced helpers. Keep their responsibilities separate: `_load-env.sh` loads deployment configuration and resolves paths; `_env-config.sh` provides image-tag and environment-file functions.
- Do not replace the two helpers with a generic `_common.sh`. Combining environment-loading side effects with build and deployment utility functions would make callers source unrelated behavior and would obscure each helper's purpose.
- Resolve shared deployment defaults in one place so Makefile targets and direct script calls use the same values.
- Move service actions into `container.sh service <action>` and have Makefile targets dispatch through it.
- Replace `adopt-project.sh` and `move-project.sh` with one `project.sh` command exposing `adopt` and `move`. Share project-path and authorization helpers while preserving each command's distinct validation and safeguards.
- Rename `deploy_single_environment.sh` to `deploy_environment.sh` and remove `deploy_all_environments.sh`. Configure each environment explicitly rather than using an all-environments command.
- Remove dead scripts and Makefile targets only after confirming they have no active callers.

## Alternatives Considered

- **Keep runtime checks in the Shape Shifter release:** rejected because database, network, credential, logging, and recovery responsibilities span the SEAD runtime.
- **Add `post-install.sh` as a universal entry point:** rejected because a wrapper that only calls other checks adds another layer below Makefile or the operator's runbook.
- **Run a verifier supplied by the candidate archive:** rejected because the candidate would provide code used to validate itself.
- **Delete all authorization checks:** rejected because Shape Shifter authorization still requires automated application tests, and operations may need deployed integration probes.
- **Keep duplicate operational scripts in both repositories:** rejected because copies can diverge and make ownership unclear.
- **Put every command in one large dispatcher:** rejected because it mixes deployment-user lifecycle operations, host provisioning, and wider runtime checks.

## Risks And Tradeoffs

- The handoff defines required outcomes but is not an implemented operations procedure. SEAD operations must apply its own tools and procedures; that implementation is outside this proposal.
- Removing runtime probes from Shape Shifter must not remove automated tests for authentication and authorization behavior.
- Release workflow and host manager checks cover different execution points. The workflow validates the source and release artifact; the manager validates downloaded archive integrity and installability using trusted code.
- The release required-content contract must remain aligned with archive construction and host-manager validation.
- Moving scripts changes active documentation and callers. Update them together; historical proposal references can remain unchanged.

## Testing And Validation

- Run `bash -n` on changed shell scripts and all four `deployment/container/tests/*.sh` suites.
- Update every caller and test to source `_load-env.sh` or `_env-config.sh`; confirm both helpers preserve their existing behavior.
- Validate source and archive policy in the release workflow, and test the host manager's trusted checks against valid and invalid archives without executing archive-supplied code.
- Confirm release archives exclude host provisioning and operations checks and contain the required runtime files.
- Confirm application authorization behavior remains covered by automated tests.
- Confirm the handoff document defines the operational outcomes; implementation of operations checks is outside this proposal's validation scope.
- Run `make -n` for each lifecycle, setup, build, maintenance, and service target.
- Verify `project.sh adopt` and `project.sh move` preserve current dry-run, validation, confirmation, and rollback behavior.
- Search active documentation, workflows, and scripts for moved paths; confirm each active reference resolves to its authoritative location.
- Exercise provisioning, release activation, status, rollback, systemd start, and health checks on a disposable non-production user.

## Acceptance Criteria

- `P-AC-1`: Release archives contain only deployment-user runtime contents; host provisioning and ecosystem runtime checks are outside the archive.
- `P-AC-2`: The release workflow checks source and archive policy. The host manager checks downloaded archives using trusted code and does not execute candidate-supplied code.
- `P-AC-3`: The operations handoff defines the required tool-agnostic runtime outcomes. This proposal removes host-wide operational check scripts from Shape Shifter and does not implement replacement operations tooling.
- `P-AC-4`: Shape Shifter automated tests continue to cover its authentication and authorization behavior; operational deployment probes, if retained, are owned outside the application release.
- `P-AC-5`: No new `post-install.sh` wrapper is added solely to dispatch checks. Routine checks do not change system state; state-changing procedures are explicit and documented.
- `P-AC-6`: Shared defaults, configuration loading, and service dispatch are consolidated without changing intended lifecycle behavior; sourced helpers are named `_load-env.sh` and `_env-config.sh` and retain separate responsibilities; project commands use `project.sh adopt|move`; host provisioning uses `deploy_environment.sh` and has no all-environments command.
- `P-AC-7`: Removed scripts and targets have no active callers, and active documentation and workflows use valid paths.
- `P-AC-8`: Release selection, checksum and archive-safety checks, service behavior, and rollback behavior are preserved; focused container tests and release checks pass.

## Planning Handoff

- **Confirmed decisions:** keep the container bundle focused on the deployment user's runtime needs; provide the operations handoff as the deliverable for runtime verification; do not implement operations tooling or add a dispatch-only post-install entry point; keep application authorization tests in Shape Shifter; do not trust a candidate-supplied release verifier.
- **Behavior to preserve:** release version/tag policy; archive safety and integrity checks; install/activate/rollback selection; Shape Shifter authorization behavior; explicit safeguards for operations that change state.
- **Expected validation:** source and archive checks pass; the host manager rejects invalid or unsafe archives without running their code; the runtime bundle excludes host and operations tools; app authorization tests remain; the handoff document defines the operational outcomes.
- **Other phase decisions:** choose the source-only host-tools directory and wrapper-retirement point; classify any mixed container-configuration checks as application tests or operations checks. SEAD operations selects and implements its own checks outside this proposal.
- **Depends on:** the completed [CONTAINER_DEPLOY_VERSIONING](../CONTAINER_DEPLOY_VERSIONING/CONTAINER_DEPLOY_VERSIONING.md).
- **Related handoff:** [SEAD Runtime Verification Handoff](./OPERATIONS_VERIFICATION_HANDOFF.md).

## Recommended Delivery Order

1. Confirm the operations handoff defines the required outcomes without prescribing tools.
2. Move host provisioning out of the release bundle, remove host-wide operational check scripts, rename the single-environment command, and remove the all-environments command.
3. Update release workflow and host-manager validation so neither relies on a candidate-supplied verifier.
4. Preserve application authorization tests; leave operations check implementation to SEAD operations.
5. Consolidate container defaults, configuration helpers, and service dispatch; update active documentation and run validation.

## Final Recommendation

Keep Shape Shifter's container setup focused on running and testing Shape Shifter. Provide the linked handoff as the runtime verification requirements for SEAD operations, without implementing operations tooling here. Move host-wide checks and provisioning out of Shape Shifter, keep release validation trusted, and simplify the remaining scripts without adding a dispatch-only post-install layer.
