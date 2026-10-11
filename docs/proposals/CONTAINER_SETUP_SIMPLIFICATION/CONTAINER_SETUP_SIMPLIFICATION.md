# Simplify the Shape Shifter Container Setup

## Status

- Proposed change
- Scope: `container/` scripts, the Makefile, and the contents of the release archive
- Goal: Reduce the number of container scripts and remove duplicated sources of truth without changing lifecycle, selection, or verification behavior

## Summary

Recommend two changes: move host provisioning scripts out of the release archive, and merge the duplicated configuration and dispatch layers.

The container setup does not do complicated work, but the same deployment defaults are defined in three files, the lifecycle commands have two dispatch scripts plus a Makefile list, and host-only installer scripts ship inside every release. Splitting release contents from host provisioning makes clear what the deployment user actually runs from `~/container`, shortens the release required-file list, and stops provisioning changes from editing release contents.

This is the right time because the release pipeline and the install/activate/rollback selection contract are now in place (`container-v0.1.0`), so the split can be made without changing them.

## Problem

`container/` holds 36 shell scripts (12 in `scripts/`, 7 in `scripts/deploy/`, 13 in `scripts/verify/`, 4 in `tests/`) plus a 382-line Makefile. Most of the scripts are legitimate, but four specific things make the setup harder to follow than its work justifies:

1. **Three sources of truth for deployment defaults.** The Makefile, `scripts/container.sh`, and `scripts/load-env.sh` each apply defaults for shared values such as `IMAGE_NAME`, `HOST_PORT`, `DATA_DIR`, `CONTAINER_NAME`, and `COMPOSE_PROJECT_NAME`. The Makefile comment instructs maintainers to "keep the two lists in step".
2. **Two dispatch layers plus the Makefile.** `scripts/container.sh` and `scripts/service.sh` each define their own action list, error handling, and usage text. The Makefile repeats both lists as one-line targets.
3. **Two sourced configuration helpers.** `scripts/load-env.sh` and `scripts/env-config.sh` are both sourced configuration helpers for the same deployment.
4. **Host provisioning ships inside the release.** `manage_container_release.sh`, `deploy_single_environment.sh`, `deploy_all_environments.sh`, `install_systemd_service.sh`, `install_nginx_reverse_proxy.sh`, `bootstrap-authentication-and-authorization.sh`, `sync-to-deploy`, and `get-install.sh` run on the host, not from `~/container`, yet they are part of the release archive and the verifier's required-file list.

What goes wrong: it is hard to tell which files run from the selected release; a provisioning change edits release contents; and several files must be changed together to keep a default or an action list consistent.

## Scope

- Split `container/` into release contents and host provisioning.
- Merge the duplicated configuration helpers and the duplicated dispatch entry points.
- Remove scripts and Makefile targets with no caller.
- Keep the release archive and `verify_container_release.sh` required-file list in step with the split.
- Update the documentation that names each moved path.

## Non-Goals

- Consolidating verification scripts, including merging `run_deployment_verification.sh` and `complete_test_deployment_verification.sh`; `RELEASE_CYCLE_EVIDENCE_AND_LOCKING` owns that.
- Changing the release publication workflow, the `container-vX.Y.Z` tag scheme, or the install/activate/rollback selection contract.
- Changing application image build or source behavior, `GIT_REF`, or `IMAGE_NAME`.
- Redesigning authorization, NGINX, or systemd behavior.
- Reducing the release manager's tag, checksum, or archive validation checks.

## Current Behavior

Verified 2026-10-11 on branch `container-deploy-versioning`, after commit `a3adcbde`.

- The Makefile applies defaults for `CONFIG_DIR`, `DATA_DIR`, `CONTAINER_NAME`, `IMAGE_NAME`, `HOST_PORT`, `COMPOSE_PROJECT_NAME`, `GIT_REPO`, and `GIT_REF`, and passes them to `container.sh` through `CONTAINER_ENV`. `scripts/container.sh` re-applies defaults for `CONTAINER_DATA_DIR`, `HOST_PORT`, `IMAGE_NAME`, `CONTAINER_NAME`, and `COMPOSE_PROJECT_NAME`. `scripts/load-env.sh` re-applies defaults for `CONFIG_DIR` and `DATA_DIR`.
- `scripts/container.sh` and `scripts/service.sh` each end with a case statement over their actions and a usage function. The Makefile defines one target per action for both.
- `scripts/load-env.sh` reads `CONFIG_DIR/deployment.env` into the environment and resolves paths. `scripts/env-config.sh` derives image tags from a git ref and writes keys back into `deployment.env`.
- `scripts/verify/verify_container_release.sh::REQUIRED_FILES` lists 21 files, including `scripts/service.sh` and `scripts/verify/verify_container_release.sh`.
- Everything under `scripts/deploy/` is host provisioning: `manage_container_release.sh` installs and selects releases, `deploy_single_environment.sh` configures a user and writes `deployment.env`, the `install_*` and `bootstrap-*` scripts run as root, and `sync-to-deploy` is a development-only mirror.
- `scripts/adopt-project.sh` and `scripts/move-project.sh` call `scripts/authorization.sh`; they are deployment-user tools that run against the running container.
- Commit `a3adcbde` removed the Makefile `setup-env` and `setup-directories` targets and `scripts/deploy/rebuild-image.sh`; none had a caller.

## Proposed Design

### 1. Split release contents from host provisioning

Move the host-only scripts to a directory the release archive excludes, for example `container/host/`: the release manager, the deploy scripts, the nginx and systemd installers, the authorization bootstrap, and the development sync script.

Keep in place everything that runs from `~/container`: the Makefile, `podman-compose.yml`, `Containerfile`, `resources/`, `service/`, and the `scripts/` files for build, setup, lifecycle, backup, healthcheck, authorization, project management, and verification.

Update the archive job and `verify_container_release.sh::REQUIRED_FILES` in the same change so the required list names only release contents.

Decide in Phase 1 whether the host directory is `container/host/` or a top-level `host/`. `container/host/` keeps the topic together with less documentation churn.

### 2. Give host provisioning one entry point

Replace `deploy_single_environment.sh`, `deploy_all_environments.sh`, and `install_systemd_service.sh` with one `shape-shifter-provision` script that takes `environment <user>`, `service <user>`, or `all`, using the dispatcher pattern already used by `container.sh`.

Keep `shape-shifter-container-release` as the separate script for install, activate, rollback, and status. Keep the old provisioning script names as thin wrappers until their documented callers move.

### 3. Merge the configuration helpers

Combine `load-env.sh` and `env-config.sh` into one sourced `scripts/lib.sh`. Keep reading `deployment.env`, resolving paths, deriving image tags, and writing keys in one place.

### 4. Keep one source of truth for defaults

Resolve `CONFIG_DIR`, `DATA_DIR`, `CONTAINER_DATA_DIR`, `IMAGE_NAME`, `HOST_PORT`, `CONTAINER_NAME`, and `COMPOSE_PROJECT_NAME` in one place and pass them to the scripts. Remove the per-script re-defaulting and the Makefile-to-script duplication so `make <target>` and a direct script call use identical values.

### 5. Collapse the dispatch scripts

Move the service actions into `container.sh` as `container.sh service <action>`, so one file owns the unit name and the systemd command for each action and the Makefile only passes the action through.

### 6. Leave the release manager and verification alone

Keep `manage_container_release.sh` as-is apart from being host-only; its checksum, tag, and archive checks are what make a selected release trustworthy. Leave every verification script in place.

## Alternatives Considered

- **Delete dead files only.** This is what commit `a3adcbde` did. It removes clutter but leaves the duplicated defaults, the two dispatch layers, and host provisioning inside the release.
- **Move host provisioning to a top-level `host/` directory.** This gives a sharper split but breaks more documented paths and separates the release manager from the release it installs. Phase 1 decides whether the split should be this strong.
- **One script with every subcommand.** Fewer files, but a large script that mixes host provisioning with container lifecycle and is harder to review and test.
- **Keep both dispatch layers and document the overlap.** This keeps the duplication the proposal exists to remove.

## Risks And Tradeoffs

- The archive job and the required-file list must change together. A mismatch either breaks publication or lets an incomplete bundle appear valid. Run the verifier in both `dir` and `archive` modes after the move.
- Moving paths changes `container/README.md`, `container/DEPLOYMENT.md`, `docs/OPERATIONS.md`, `docs/AUTHORIZATION.md`, and `scripts/README.md`. Update them in the same change. References under `docs/proposals/done/` are historical and stay as they are.
- `container/tests/test_verify_inventory.sh` asserts the verification inventory and the required-file contract. Keep it aligned with the new required-file list.
- Merging provisioning commands changes the administrative command line. Keep old names as wrappers until their documented callers move.
- Simplification must not weaken the release manager's validation. Its size is deliberate.

## Testing And Validation

- Run `bash -n` on every changed script.
- Run the four `container/tests/*.sh` suites.
- Run `verify_container_release.sh dir` and `verify_container_release.sh archive` on a built archive.
- Run `make -n <target>` for every lifecycle, setup, build, maintenance, and service target.
- Confirm the built release archive contains no host provisioning files and that the required-file list matches the archive.
- Grep the repository for moved and removed paths and confirm only `docs/proposals/done/` references remain.
- Provision one disposable non-production user end to end with the merged script and confirm install, activate, status, rollback, systemd start, and health check still work.

## Acceptance Criteria

- `P-AC-1`: The release archive contains only files that run from `~/container`; host provisioning is excluded, and `verify_container_release.sh` requires exactly the release contents.
- `P-AC-2`: Host provisioning has at most two scripts (`shape-shifter-container-release` and one provisioning script); the deployment user's commands run through `make`.
- `P-AC-3`: Each deployment default is defined in one place; `make <target>` and a direct script call resolve identical values for the same inputs.
- `P-AC-4`: No removed script or target has a caller or a documented reference outside `docs/proposals/done/`.
- `P-AC-5`: Lifecycle, systemd, release selection, and rollback behavior are unchanged; all `container/tests` suites pass and the verifier passes in both modes.
- `P-AC-6`: Documentation names the release contents and the host provisioning scripts, and every moved path is updated.
- `P-AC-7`: No verification script is removed or redefined; consolidating the two verification orchestrators remains with `RELEASE_CYCLE_EVIDENCE_AND_LOCKING`.
- `P-AC-8`: The release manager's tag, checksum, and archive checks are unchanged.

## Planning Handoff

- **Confirmed decision:** split release contents from host provisioning, and remove the duplicated defaults and dispatch layers. The script count and archive size should drop; the exact final count is not fixed.
- **Rejected:** deleting dead files only (done in `a3adcbde`, insufficient); one mega-script; keeping the duplicated layers.
- **Behavior to preserve:** the release archive contract; the install/activate/rollback selection contract with immutable per-tag storage and the `~/container` symlink; separation of the container tag from `GIT_REF` and `IMAGE_NAME`; read-only verification scripts; explicit opt-ins for state-changing checks; the release manager's validation.
- **Expected validation results:** the archive contains no host provisioning; the required-file list matches the archive; the tests and the verifier pass; documentation is consistent; a disposable user provisions, activates, rolls back, and starts under systemd.
- **Open questions, with the phase that must resolve each:**
  - Where the host provisioning directory lives (`container/host/` or top-level `host/`) — Phase 1.
  - Whether the service action merges into `container.sh` or stays in `service.sh` — Phase 1.
  - How long old provisioning command names remain as wrappers — Phase 1.
- **Depends on:** the completed Phase 1 of [CONTAINER_DEPLOY_VERSIONING](../CONTAINER_DEPLOY_VERSIONING/CONTAINER_DEPLOY_VERSIONING.md). That proposal's guidance is to plan implementation anew after the release policy was agreed; this proposal is the input to that new plan.

## Recommended Delivery Order

1. Split release contents from host provisioning, updating the archive job and the required-file list together.
2. Merge `load-env.sh` and `env-config.sh` into one helper and remove the duplicated defaults.
3. Collapse the dispatch scripts and update the Makefile targets.
4. Merge the provisioning commands and keep the old names as wrappers.
5. Update every documented path and re-run the tests and the verifier.

## Final Recommendation

Do the split and the merges. The dead-code removal is already committed (`a3adcbde`). Next, split release contents from host provisioning with the archive and the required-file list updated in the same change, then merge the configuration helpers and the dispatch entry points, and finally re-check every documented path. Keep the release manager and the verification scripts as they are.
