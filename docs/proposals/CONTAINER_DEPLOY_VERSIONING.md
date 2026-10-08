# Admin-Owned Versioned Container Deployment Bundles

## Status

- Proposed change
- Scope: Deployment bundle installation and refresh for multiple Shape Shifter environments on one server
- Goal: Let an administrator manage read-only, versioned deployment files while each environment selects and rolls back its bundle independently, and simplify repeated container lifecycle commands

## Summary

Replace deployment-user-owned copies of `container/` with administrator-managed, versioned copies of the complete deployment bundle. Each environment should select one version through its `~/container` path, while its `~/config` and `~/container-data` remain separate and owned by that environment's user. Refreshing a bundle should install a new version without editing the active version, then switch one environment at a time with a clear rollback path.

The refresh workflow should support both a pinned GitHub revision and a reviewed local development tree. It should update the complete `container/` bundle, not only `scripts/`, because the scripts depend on the Makefile, Containerfile, compose file, service definition, and resources. As part of the same change, consolidate closely related container lifecycle commands behind one dispatcher, following the existing `service.sh <action>` pattern.

## Problem

The server may host several environments, each with a separate copy of deployment files. Those copies are currently writable by their deployment users, so the intended read-only status is not enforced.

There are two existing update paths, but neither provides controlled, read-only release management:

- `deploy_single_environment.sh` downloads the GitHub archive as the deployment user, overlays `container/` into `~/container`, runs setup, and normally builds and starts the image.
- `sync-to-deploy` mirrors the local `container/` tree, deletes target files removed from the source, and changes ownership to the deployment user. It is useful for development synchronization, but it is not a GitHub refresh workflow or an immutable release installer.

Using one mutable global directory would also couple all environments to the same update and make rollback or staged rollout difficult.

## Scope

- Version and install complete deployment bundles under an administrator-controlled location.
- Let each deployment select a bundle version independently.
- Define permissions and refresh, activation, and rollback behavior.
- Preserve per-environment configuration, runtime data, and existing path behavior.
- Support reviewed local changes as well as pinned GitHub revisions.
- Consolidate repeated container lifecycle entry points without merging unrelated setup, build, backup, or service-management responsibilities.
- Review verification scripts for ongoing operational use, active proposal dependencies, and completed one-off purposes before retaining, consolidating, relocating, or retiring them.

## Non-Goals

- Change how application images are built or which application revision an environment runs.
- Move `~/config` or `~/container-data` into the shared bundle location.
- Treat file ownership as a security boundary against a deployment user who controls their own account or user systemd manager.
- Update every environment automatically whenever a new bundle is installed.

## Current Behavior

`deploy_single_environment.sh` fetches the `container/` archive into the deployment user's home and invokes `setup.sh`; its default path then builds and starts the image. `deploy_all_environments.sh` repeats that process per user. `sync-to-deploy` instead copies the current local tree and applies deployment-user ownership.

The environment loader and Makefile support relative `CONFIG_DIR` and `DATA_DIR` overrides resolved relative to the checkout parent. The Makefile derives its checkout location with `realpath`. A shared release reached through `~/container` must not silently change where those overrides resolve.

Container lifecycle operations currently have separate `up.sh`, `down.sh`, and `logs.sh` entry points. They repeat environment loading and compose setup. Make exposes lifecycle targets, and the systemd unit invokes `up.sh` and `down.sh` directly. `service.sh <action>` is an existing dispatcher pattern, but it manages systemd rather than the container itself.

The `scripts/verify/` directory contains reusable read-only checks, explicitly opted-in state-changing checks, and two orchestration scripts. The deployment verification handoff is marked closed, while the proposed Release Cycle Evidence And Locking process still refers to `run_deployment_verification.sh`. A script's connection to completed work therefore does not by itself establish that the script is obsolete.

## Proposed Design

An administrator installs each selected Git revision or reviewed local bundle as a separate release under a root-controlled shared directory. A release contains the complete deployment bundle and is not modified after installation. Deployment users receive read and execute access to release files but no write access.

Each environment's `~/container` selects one installed release. The administrator activates a release for one environment at a time, after review and validation. The previous selection remains available so rollback does not require another download. Installing or activating a release must not overwrite or remove that environment's `~/config` or `~/container-data`.

The refresh operation should:

1. Require an explicit Git tag or commit, or an explicitly selected local source tree; do not silently follow a moving branch for production updates.
2. Stage and validate the complete bundle before making it selectable.
3. Record the source revision for each installed release.
4. Change an environment's selected release only after validation succeeds, and leave its previous selection intact on failure.
5. Keep bundle revision separate from the application image revision in `deployment.env`, so operators can update deployment tooling without unintentionally selecting a different application image source.

The implementation must preserve current config and data path resolution for both default paths and documented relative overrides. It must verify behavior through the `~/container` selection path rather than assuming the symlink's physical path has no effect. If preserving relative override behavior is impractical, resolve relative overrides against a stable per-environment home path and document any migration needed before activation.

The existing dev-side synchronization workflow may remain for local testing, but it should install or stage a new administrator-owned release rather than making the active release deployment-user-writable.

### Container lifecycle commands

Add one container command dispatcher, following `service.sh <action>`, with explicit subcommands for at least `up`, `down`, and `logs`. Assess `restart`, `status`, and `healthcheck` for inclusion during design; include them only if the dispatcher can preserve their existing behavior and reduce duplicated setup. Keep image build, first-time setup, backup, authorization, and systemd service management as separate responsibilities.

The Make targets should retain their current names and delegate to the dispatcher. Update the systemd unit to invoke its `up` and `down` subcommands. The dispatcher should load deployment configuration once, establish the compose context consistently, provide usage and a nonzero exit for missing or unknown commands, and preserve log-following interrupt behavior. Replace the current standalone entry points only after all repository callers and documented commands are updated; temporary forwarding wrappers may preserve compatibility for existing deployment copies during rollout.

### Verification script lifecycle

Review verification scripts as part of simplifying and versioning the bundle. For each script, determine whether it supports a recurring operational check, an active proposal or release process, a completed one-off verification, or a check that has been replaced by another entry point. Use current callers, documentation, proposal status, and evidence-retention needs to make that determination.

Keep or consolidate checks that support ongoing deployment or release verification. A script tied only to completed work may be retired or moved out of the operational verification set after its remaining callers and documentation are updated and its evidence-retention needs are satisfied. A proposal being marked complete is a reason to reassess its scripts, not sufficient grounds by itself to remove them. Preserve the distinction between read-only checks and commands that mutate a deployment, and require explicit opt-in for state-changing verification.

## Alternatives Considered

**Keep a writable copy for each environment.** This is the smallest change and preserves existing path assumptions, but it leaves deployment files mutable by each deployment user and repeats the same bundle across users.

**Use one shared mutable bundle for every environment.** This removes duplicate copies but changes every environment at once, couples environments to one version, and makes staged rollout and rollback harder.

**Refresh only `scripts/` from GitHub.** Rejected because the scripts and deployment files are versioned and used together. Updating only scripts can combine incompatible versions of the Makefile, Containerfile, compose configuration, service unit, or resources.

**Keep every lifecycle operation as a separate script.** This avoids a dispatcher but retains repeated environment and compose setup across closely related commands.

**Merge all scripts into one command.** Rejected because setup, builds, backups, authorization, service management, and container lifecycle have different responsibilities and options. A single command for those unrelated jobs would become harder to navigate than the current flat directory.

**Keep every verification script indefinitely because it was used by a proposal.** Rejected because completed work can leave one-off tools behind. Retention should follow ongoing operational use, active process requirements, and evidence needs rather than historical association alone.

## Risks And Tradeoffs

- Shared releases reduce duplication but add a host-level installation and activation workflow that requires administrator privileges.
- Relative config and data overrides currently depend on checkout location. A symlink or shared release path may change their resolution unless explicitly preserved and tested.
- Root ownership prevents ordinary edits to release contents, but does not prevent a deployment user from changing files or services under that user's control, including potentially replacing a home-directory symlink. This is change control, not isolation from a compromised deployment account.
- Production updates should use immutable revisions. If signature or checksum verification is required, the accepted source-verification policy must be decided before implementation.
- A dispatcher reduces duplicated lifecycle setup but can become a large command suite. Keep its command set limited to related container operations and preserve the existing Make and systemd interfaces.
- Existing deployment copies may continue to invoke standalone script paths until refreshed. Keep compatibility wrappers during rollout or coordinate their replacement with bundle activation.
- Removing a proposal-specific verification script too early could leave a gap in an active release process or discard a check whose evidence is still needed. Require a documented disposition and caller/reference review before retirement.

## Testing And Validation

- Install a bundle from a pinned GitHub revision and from a reviewed local source; verify each records its source revision.
- Verify deployment users can read and execute release files but cannot modify release contents.
- Activate a new version for one test environment and verify other environments remain on their selected versions.
- Verify a failed installation or validation does not change the active selection, and verify rollback restores the previous selection.
- Verify `make setup`, `make build`, `make up`, and the systemd unit work through the selected bundle path.
- Verify lifecycle dispatcher commands match current `up.sh`, `down.sh`, and `logs.sh` behavior, including log-follow interruption; verify Make targets and systemd start/stop use the dispatcher correctly.
- Verify missing and unknown dispatcher commands show usage and fail without running a container operation.
- Review verification scripts against current callers, documentation, completed handoffs, and active proposals; verify each has a retain, consolidate, move, or retire disposition before changing the set.
- For every retained or replacement release-verification entry point, verify the required checks and evidence remain available; verify retired scripts have no active callers or required evidence outputs and no stale documented commands remain.
- Verify state-changing verification checks remain clearly identified and require their existing explicit opt-in or confirmation.
- Verify default and relative `CONFIG_DIR`, `DATA_DIR`, and `CONTAINER_DATA_DIR` values resolve to the intended per-environment paths.
- Verify deployment configuration, credentials, and runtime data remain unchanged during refresh and activation.

## Acceptance Criteria

- `P-AC-1`: Complete deployment bundles are installed as separate, administrator-owned versions; deployment users cannot modify installed release contents.
- `P-AC-2`: Each environment selects its bundle version independently, and a bundle activation or rollback for one environment does not change another environment's selection.
- `P-AC-3`: A failed fetch, installation, or validation leaves the environment's currently selected bundle unchanged.
- `P-AC-4`: The documented refresh workflow accepts a pinned GitHub revision and a reviewed local source without updating only `scripts/`.
- `P-AC-5`: Bundle refresh does not overwrite or relocate per-environment configuration or runtime data.
- `P-AC-6`: Default and supported relative path overrides resolve correctly when commands run through the environment's selected bundle.
- `P-AC-7`: Bundle revision and application image revision can be selected and inspected independently.
- `P-AC-8`: Container lifecycle operations have one documented dispatcher entry point with explicit commands for `up`, `down`, and `logs`; any additional commands are included only with behavior parity.
- `P-AC-9`: Existing Make lifecycle targets and systemd start/stop behavior delegate to the dispatcher and retain their documented behavior.
- `P-AC-10`: Missing or unknown dispatcher commands fail clearly, and `logs` remains interruptible by the operator.
- `P-AC-11`: Each verification script has a documented disposition based on its current callers, operational role, active proposal dependencies, and evidence needs; completed proposal status alone does not trigger removal.
- `P-AC-12`: Consolidating or retiring verification scripts leaves active release checks and required evidence available, removes stale references, and preserves explicit safeguards for state-changing checks.

## Planning Handoff

- Preserve environment-specific configuration, runtime data, ports, and independent rollout choices.
- Treat installed bundle versions as immutable; install first, validate, then activate.
- Keep the prior selected version available for rollback.
- Preserve documented path resolution, especially relative overrides, or define and validate a migration before changing it.
- Preserve the current Make target interface and systemd start/stop behavior while consolidating lifecycle commands. Keep setup, build, backup, authorization, and systemd service management outside the container dispatcher.
- Review verification scripts against the closed deployment verification handoff and active Release Cycle Evidence And Locking proposal. Record each disposition and preserve every still-required check, evidence output, read-only guarantee, and mutation safeguard.
- Resolve the host installation root and source-verification policy before implementation. The proposal does not prescribe an exact command name or require a particular checksum/signature mechanism.

## Open Questions

- What administrator-controlled root should hold installed releases?
- Should production bundle sources require signed tags or verified checksums, or is an explicit immutable commit sufficient?
- Should local-source installation be limited to test environments?
- Should `restart`, `status`, and `healthcheck` join the initial container dispatcher, or remain separate commands?
- Which verification scripts are recurring release or operational checks, and which were created only for completed verification work?

## Final Recommendation

Use administrator-owned, immutable, versioned copies of the complete deployment bundle, with independent per-environment selection and rollback. Add a focused dispatcher for related container lifecycle operations while retaining Make and systemd interfaces. Review verification scripts by current purpose and evidence needs before consolidating or retiring them. Do not use a single mutable global checkout, refresh only the scripts directory, or combine unrelated maintenance commands into one dispatcher.
