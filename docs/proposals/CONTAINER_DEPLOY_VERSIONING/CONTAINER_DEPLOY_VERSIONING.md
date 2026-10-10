# Independently Versioned Container Releases

## Status

- Proposed change
- Scope: Publishing and deploying the `container/` files for multiple environments
- Goal: Release the complete container deployment files independently of the application and let each environment select or roll back a release

## Summary

Publish a complete `container/` archive as a GitHub Release asset when a reviewed change lands on a protected `container-release` branch. Give container releases their own `container-vX.Y.Z` tags, separate from the application's releases on `main`. An administrator downloads a specific release, verifies and installs it without changing an active version, then switches one environment at a time. Keep configuration, runtime data, and application image selection independent of the container release.

GitHub Releases are the distribution source. A shared, mutable deployment checkout or custom Git/local-source fetch mechanism is not needed. The host still needs a small install-and-select operation for independent activation and rollback.

## Problem

The existing deployment paths copy files into deployment-user-owned `~/container` directories. The single-environment deploy script fetches a repository archive and also records its ref as the application image source. Local synchronization mirrors the current tree into the active directory. Neither path provides a separately versioned, non-writable container release that can be installed, checked, and selected without also changing application settings or overwriting active files.

## Scope

- Publish a versioned asset containing the complete `container/` tree from a reviewed commit.
- Install and select releases independently for each environment, with a way to inspect and roll back the selected version.
- Preserve per-environment configuration, runtime data, ports, and documented relative path behavior.
- Keep related container lifecycle commands consistent through the selected release, and review verification scripts before changing their operational entry points.

## Non-Goals

- Change the application image release process, image build source, or image revision when selecting a container release.
- Automatically update all environments when a GitHub Release is published.
- Move `~/config` or `~/container-data` into a release.
- Make an administrator-owned release a security boundary against a deployment user who controls their account or user systemd manager.
- Publish reviewed but unmerged PR commits as production releases.

## Current Behavior

`container/scripts/deploy/deploy_single_environment.sh` downloads a repository archive into the deployment user's `~/container`, runs setup, and writes the fetched `REF` into `GIT_REF` and the derived `IMAGE_NAME`. `container/scripts/deploy/sync-to-deploy` copies the local tree into a deployment-user-owned active directory with `rsync --delete`. The application release workflow runs semantic-release on `main` and uses the repository's application version and release notes.

The shell environment loader and Makefile resolve relative configuration and data paths from the checkout's physical location. Selecting a release through `~/container` must not redirect these paths into a release directory. The current worktree also contains uncommitted container lifecycle-dispatcher changes; these are not assumed to be shipped or validated.

## Proposed Design

### Publish container releases

Use a protected `container-release` branch as the reviewed publication source. Create a promotion branch from its current tip, merge `main` into that branch, set the next version explicitly in `container/VERSION`, and submit a PR targeting `container-release`. Review the resulting `container/` tree, not just the commit list. Only promotion PRs merge into `container-release`; each merge publishes one release. Require a strictly increasing `X.Y.Z` version and reject a missing, reused, or inconsistent version. A PR builds and validates the complete archive with read-only permissions, without creating a tag or Release. After merge, the workflow publishes the merged commit under `container-vX.Y.Z` with the archive, checksum, and source commit recorded in release metadata. Restrict direct pushes to the branch, protect `container-v*` tags against rewriting, and grant publication rights only to the post-merge workflow. Do not change the application's semantic-release workflow or version.

The archive contains only the deployment bundle, but all of it: Makefile, compose and build files, scripts, service definition, and required resources. Publication fails if required files or validation checks are missing. Operators select releases by exact container tag, not by a moving branch or a generic "latest" release. A checksum detects transfer corruption; its publication alongside the asset is not, by itself, independent proof of authenticity. Production trust rests on the protected repository and release workflow.

### Install and select per environment

Install one administrator-owned release-management script per host under `/usr/local/sbin/`, from a reviewed copy in an administrator-controlled checkout. The installed script is not run from, or automatically replaced by, an environment's selected bundle. It requires a deployment user and exact container tag and offers separate `install`, `activate`, `rollback`, and `status` operations. An administrator explicitly updates the host script after review; deployment users cannot modify it.

For `install`, the script downloads a named GitHub Release archive and checksum, verifies the download and expected version, and extracts and validates it under `/opt/shape-shifter/<user>/container-releases/<tag>/`, controlled by the administrator. The installed contents are read/execute for the deployment user but not writable by them. This is per-environment versioned storage, not a shared mutable checkout. Installation does not switch `~/container` or extract over an active release.

Each environment keeps its own `~/container` selection. `activate` switches only that environment to a validated installed version and retains its previous selection; `rollback` restores it without a download. `status` reports the selected tag and source commit separately from `GIT_REF` and `IMAGE_NAME`. Preserve an existing `~/container` directory during the first transition rather than replacing or deleting its contents without review. Failed download, verification, installation, or validation leaves the selection unchanged. Activation and rollback must not change the environment's application image settings, `~/config`, or `~/container-data`.

Resolve defaults and all relative `CONFIG_DIR`, `DATA_DIR`, and `CONTAINER_DATA_DIR` overrides against the deployment user's home rather than the physical release directory, in both shell and Make; keep absolute overrides absolute. Check existing overrides before activation and document any necessary migration. Test all paths through `~/container`, not only from the release's physical location.

Local development synchronization may continue for isolated testing, but it is not the production release source and must not overwrite an administrator-owned active release.

### Container lifecycle and verification

Finish the in-progress dispatcher for `up`, `down`, and `logs` while preserving Make target names, systemd start/stop, clear errors for unknown commands, and interruptible log following. Keep build, setup, backup, authorization, and systemd management separate. Preserve compatibility with old entry points until their callers have moved to a selected release.

Before consolidating or removing verification scripts, identify their callers, operational use, active proposal dependencies, and required output. Preserve recurring release checks and the existing explicit opt-in for state-changing checks; completed proposal status alone is not grounds for removal.

## Alternatives Considered

- **Fetch an arbitrary Git revision or local source for production.** This broadens the installer and source-verification policy. A named GitHub Release gives operators a reviewed, repeatable production input; local trees remain for isolated development testing.
- **Publish on each PR update.** PR commits can change before review. PRs validate an archive; merging to the protected release branch publishes it.
- **Use application release tags.** They couple deployment-file changes to application versioning. A `container-v` prefix keeps the two independently selectable.
- **Use one shared mutable host checkout.** A change to it would affect every environment at once and weaken rollback.
- **Refresh only `scripts/`.** Deployment files must stay compatible as a complete set.

## Risks And Tradeoffs

- Promotion PRs must show the resulting `container/` content after merging `main`; branch/tag protection must be configured before publication is enabled.
- GitHub availability and access are required to fetch a release not already installed; retain the previous release for offline rollback.
- Installing outside a user's writable tree requires administrator access. A `~/container` selection under that user's control is change management, not protection from a compromised deployment account.
- Relative paths, systemd callers, and existing deployment copies may need a coordinated transition. Preserve their behavior until the selected-release path is validated.
- Verification scripts must not be removed solely to simplify the release archive if operations or active proposals still require them.

## Testing And Validation

- On a PR, verify archive completeness and checks without creating a tag or Release. After a merge, verify exactly one distinct container tag and GitHub Release identify the commit and contain the archive and checksum; application version and release behavior remain unchanged.
- In isolated test environments, install a named release, inspect its recorded tag and commit, verify deployment-user read/execute but denied write access, and confirm invalid or corrupt assets leave the current selection intact.
- Verify one administrator-controlled host script can manage two disposable non-production deployment users, cannot be edited by either user, and remains usable for rollback if the selected bundle is broken.
- Activate and roll back one environment while another stays on its selected version. Check `~/config`, `~/container-data`, image settings, and default and relative paths through `~/container`; run setup, Make, and systemd checks where applicable.
- Check dispatcher behavior, prior entry-point compatibility, and the disposition of each verification script, including evidence outputs and opt-in safeguards for state-changing checks.

## Acceptance Criteria

- `P-AC-1`: A PR to `container-release` validates but cannot publish; a reviewed merge publishes one complete, verifiable GitHub Release asset at an immutable `container-vX.Y.Z` tag, separate from the application release.
- `P-AC-2`: A deployment user can read and execute an installed container release but cannot modify its contents.
- `P-AC-3`: Each environment can inspect, select, and roll back its container release independently of other environments and its application image revision.
- `P-AC-4`: A failed fetch, checksum check, installation, or validation does not change the selected release.
- `P-AC-5`: Installation and activation preserve per-environment configuration, credentials, runtime data, and documented default and relative path behavior.
- `P-AC-6`: Operators can select an exact GitHub container release and inspect its tag and source commit without changing `GIT_REF` or `IMAGE_NAME`.
- `P-AC-7`: Lifecycle commands retain their Make and systemd behavior through the selected release; missing or unknown commands fail clearly and logs remain interruptible.
- `P-AC-8`: Every verification script has a documented retain, consolidate, move, or retire decision; required release checks and evidence remain available and state-changing checks retain explicit safeguards.
- `P-AC-9`: One administrator-owned script per host installs an exact release without activating it and explicitly activates, rolls back, and reports status for each deployment user; it remains usable when a selected bundle is broken.

## Planning Handoff

- First create and protect `container-release` and `container-v*`, require reviewed promotion PRs that merge `main` and increment `container/VERSION`, then validate PRs and publish complete assets on merge. The policy is decided; GitHub protections still need to be configured and checked. Do not conflate this workflow with application semantic-release on `main`.
- Then install the reviewed host-management script once per host under `/usr/local/sbin/`; stage named releases under `/opt/shape-shifter/<user>/container-releases/<tag>/`. Validate installation separately from activation in two disposable non-production deployment users, including first-transition preservation and offline rollback. Preserve image settings, config/data, home-relative paths, and absolute overrides.
- Coordinate the in-progress lifecycle dispatcher and verification-script review with selected-release rollout; do not treat worktree changes as deployed behavior.
- Validate publication with PR checks and the first intentionally reviewed release, not disposable production tags. Configure GitHub protections before enabling publication; use disposable non-production users for host checks.

## Final Recommendation

Use GitHub Releases to distribute separately tagged, complete `container/` versions. Keep only the small host-side operation needed to verify, install, and select one release per environment; retire the existing phase and task plans and plan implementation anew after the release policy is agreed.
