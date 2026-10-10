# Independently Versioned Container Releases — Phase Plan

Source proposal: [CONTAINER_DEPLOY_VERSIONING.md](./CONTAINER_DEPLOY_VERSIONING.md)

## Summary

Publish reviewed `container/` changes as separate GitHub Releases, then install and select those releases per environment. Complete lifecycle integration and verification-script review after the selected-release path is established. The proposal is the decision source; this plan sequences delivery and does not authorize implementation while its blocking decisions remain open.

## Problem

Current deployment paths overwrite deployment-user-owned files and couple a fetched repository ref to application image settings. A versioned GitHub Release supplies a repeatable bundle, but publication alone does not provide safe installation, independent activation, or rollback on the host.

## Scope

This plan covers release publication, per-environment installation and selection, path and image-setting preservation, and lifecycle and verification compatibility through the selected release. It does not change application image versioning, move configuration or data, publish unmerged PR commits, or automatically activate a new release everywhere.

## Current Position

- The application release workflow runs semantic-release on `main`; a separate `container-release` publication workflow is proposed, not implemented.
- The existing single-environment deployment script fetches a repository archive into the deployment user's directory and writes the fetched ref into application image settings. Local synchronization mirrors into that active directory.
- Container lifecycle-dispatcher edits are present but uncommitted; treat them as in-progress work rather than validated behavior.
- The proposal now fixes reviewed promotion PRs, `container/VERSION`, per-environment administrator-owned storage, home-relative overrides, and disposable non-production test users. Branch/tag protections, a container publication workflow, and a host installer are not yet in place.

## Phase Plan

### Phase 1: Publish Reviewed Container Releases

**Goal**

Produce a complete, independently versioned GitHub Release from each approved container release change without changing the application release.

**Focus**

- Require promotion PRs based on `container-release` that merge `main`, review the resulting `container/` tree, and increment `container/VERSION`; configure branch and tag protections.
- Validate the complete archive on PRs without publishing it; publish the tagged asset, checksum, and source commit only from reviewed changes merged to the release branch.
- Reject duplicate or inconsistent versions and preserve the existing application release workflow.

**Depends On**

- The proposal's reviewed promotion and version rules; protection must be configured and validated as part of this phase before publication is enabled.

**Outputs**

- A documented, validated container publication workflow and a release asset suitable for per-environment installation.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) PR validation produces no tag or Release; an approved merge produces exactly one complete archive, checksum, and source-commit record under a distinct immutable container tag.
- `PH1-AC-2` (from `P-AC-1`) Publishing a container release leaves application release tags, version, and workflow behavior unchanged; missing content or a reused version fails publication.

**Validation Milestones**

- `VM-1` PR and approved-merge checks confirm the contents, source identity, tag uniqueness, and separation from the application release; negative cases produce no publishable release. Covers `PH1-AC-1` and `PH1-AC-2`.

**Task-Plan Handoff**

- Use `P-AC-1`, the reviewed `container/VERSION` increment and promotion PR rules, and the proposal's protection requirements. Plan read-only PR checks and validate protections before any real publication. Do not publish from PR updates or reuse application tags.

**Readiness**

Ready for a task plan. The release rules are fixed; setting up and verifying branch/tag protection belongs to this phase.

### Phase 2: Install and Select Releases Per Environment

**Goal**

Install an exact published release and activate or roll it back in one environment without changing another environment, its application image, or its configuration and data.

**Focus**

- Install one administrator-owned host script outside selected bundles, then fetch and verify a named release into per-environment administrator-controlled storage without activation.
- Retain the previous selection for rollback; keep a failed download, check, installation, or validation from changing the current selection.
- Preserve environment-specific configuration, data, and home-relative path resolution through `~/container`; keep bundle tag and source commit separate from application image settings.
- Replace active-directory overwrite paths with the approved production release workflow while retaining an isolated local-development path.

**Depends On**

- Phase 1's published asset and its exact-tag/source-commit contract.
- The proposal's per-environment storage, separate installation and activation, home-relative path rule, and disposable non-production test users.

**Outputs**

- A documented install, inspect, activate, and rollback workflow with validated independent environment selections.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-2`) Installed release contents are complete and administrator-owned; deployment users can read and execute but cannot modify them.
- `PH2-AC-2` (from `P-AC-3`) Activating and rolling back one environment leaves a second environment's selection and both application image revisions unchanged.
- `PH2-AC-3` (from `P-AC-4`) Failed fetch, checksum, installation, and validation cases preserve the active selection.
- `PH2-AC-4` (from `P-AC-5`) Activation and rollback preserve configuration, credentials, runtime data, and default and supported relative path behavior through `~/container`.
- `PH2-AC-5` (from `P-AC-6`) The selected exact container tag and source commit can be inspected without changing `GIT_REF` or `IMAGE_NAME`.
- `PH2-AC-6` (from `P-AC-9`) One administrator-owned host script installs a named release without selecting it and can explicitly activate, roll back, and report status per user even when the selected bundle is broken.

**Validation Milestones**

- `VM-2` Isolated installation and negative-path checks confirm permissions, source identity, an independently installed host script, and unchanged selection on failure. Covers `PH2-AC-1`, `PH2-AC-3`, `PH2-AC-5`, and `PH2-AC-6`.
- `VM-3` Two disposable non-production environments confirm independent activation and offline rollback, unchanged image settings and config/data contents, and consistent default and relative path resolution through `~/container`. Covers `PH2-AC-2`, `PH2-AC-4`, `PH2-AC-5`, and `PH2-AC-6`.

**Task-Plan Handoff**

- Use `P-AC-2` through `P-AC-6` and `P-AC-9`. The proposal fixes a host script under `/usr/local/sbin/`, per-user storage under `/opt/shape-shifter/<user>/container-releases/<tag>/`, all relative overrides against the user's home, and unchanged absolute overrides. Plan the first transition to preserve an existing `~/container`; validate using disposable non-production users. Do not treat administrator ownership as account isolation.

**Readiness**

Requires Phase 1's published asset. The host layout, relative-path rule, and non-production test approach are fixed for task planning.

### Phase 3: Integrate Lifecycle and Preserve Verification

**Goal**

Run lifecycle commands consistently from the selected release and retain required operational verification before retiring old entry points.

**Focus**

- Integrate the in-progress dispatcher with Make and systemd while preserving the current command behavior, including clear failures and interruptible logs.
- Review verification scripts against callers, active processes, and required evidence; retain, consolidate, move, or retire each with safeguards intact.
- Coordinate old entry points and deployment documentation with the selected-release rollout; cut over only after parity checks.

**Depends On**

- Phase 2's validated selected-release path and path-resolution behavior.
- Review of remaining callers of old lifecycle and verification entry points before their removal.

**Outputs**

- Lifecycle and verification commands documented for selected releases, with compatibility or migration steps for older deployment copies and a disposition for each verification script.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-7`) Make and systemd lifecycle behavior works through the selected release; missing or unknown commands fail clearly and log following remains interruptible.
- `PH3-AC-2` (from `P-AC-8`) Every verification script has a justified disposition; active release checks and evidence remain available and state-changing checks retain explicit safeguards.

**Validation Milestones**

- `VM-4` Compare lifecycle commands, Make targets, systemd behavior, and prior entry-point callers with the existing behavior through the selected release. Covers `PH3-AC-1`.
- `VM-5` Review each verification-script disposition and exercise retained checks and safeguards before removing old commands or references. Covers `PH3-AC-2`.

**Task-Plan Handoff**

- Use `P-AC-7` and `P-AC-8`; inspect the uncommitted dispatcher changes and current callers before selecting migration steps. Depend on Phase 2's confirmed selection path, not on the physical release location.

**Readiness**

Requires the Phase 2 selection contract and caller review before a task plan can fix compatibility and validation.

## Cross-Phase Rules

- Treat the container tag and source commit as separate from application image revision; never change application image selection as a side effect of publication or activation.
- Validate a full release before selecting it; keep prior releases available for rollback and preserve per-environment configuration and runtime data.
- Do not publish PR updates, overwrite installed releases, or remove legacy entry points while active callers or required verification evidence remain.
- Validate through `~/container` and keep operational documentation aligned with behavior that is actually shipped.

## Validation Strategy

- `VM-1` confirms `PH1-AC-1` and `PH1-AC-2` through PR and publication checks, including duplicate-version and missing-content failures.
- `VM-2` and `VM-3` confirm `PH2-AC-1` through `PH2-AC-6` in disposable non-production environments, including failed installs, independent rollback, and path and image-setting preservation.
- `VM-4` and `VM-5` confirm `PH3-AC-1` and `PH3-AC-2` through behavior comparison and verification-script review before cutover.
- Exact commands, fixtures, users, and assertions belong in the corresponding phase task plan; no production deployment is a validation baseline.
