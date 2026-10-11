# Phase 2 Task Plan: Install and Select Releases Per Environment

## Phase Summary

- **Phase:** [Phase 2: Install and Select Releases Per Environment](./CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md)
- **Goal:** Install an exact published container release and select or roll it back for one environment without changing other environments, application image settings, configuration, or data.
- **Readiness:** **Validated.** Phase 1 published `container-v0.1.0`; the host layout, operation set, path rules, and disposable-user validation approach are fixed in the proposal and phase plan. The live Phase 1 retry check was waived and is not a Phase 2 dependency.
- **Source proposal:** [CONTAINER_DEPLOY_VERSIONING.md](./CONTAINER_DEPLOY_VERSIONING.md)
- **Phase plan:** [CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md](./CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md)
- **Source criteria:** `PH2-AC-1` through `PH2-AC-6`, mapped to `P-AC-2` through `P-AC-6` and `P-AC-9`.
- **Dependency:** Use the published exact-tag release and source-commit contract. Keep the host management script administrator-owned under `/usr/local/sbin/`; do not run it from the selected bundle or update it automatically.

### Acceptance Criteria

- [x] `PH2-AC-1` (from `P-AC-2`): Installed release contents are complete and administrator-owned; deployment users can read and execute but cannot modify them. (Verified by `V-2` and `V-3`.)
- [x] `PH2-AC-2` (from `P-AC-3`): Activating and rolling back one environment leaves a second environment's selection and both application image revisions unchanged. (Verified by `V-2` and `V-4`.)
- [x] `PH2-AC-3` (from `P-AC-4`): Failed fetch, checksum, installation, and validation cases preserve the active selection. (Verified by `V-2` and `V-3`.)
- [x] `PH2-AC-4` (from `P-AC-5`): Activation and rollback preserve configuration, credentials, runtime data, and default and supported relative path behavior through `~/container`. (Verified by `V-1`, `V-2`, and `V-4`.)
- [x] `PH2-AC-5` (from `P-AC-6`): The selected exact container tag and source commit can be inspected without changing `GIT_REF` or `IMAGE_NAME`. (Verified by `V-2`, `V-3`, and `V-4`.)
- [x] `PH2-AC-6` (from `P-AC-9`): One administrator-owned host script installs a named release without selecting it and can explicitly activate, roll back, and report status per user even when the selected bundle is broken. (Verified by `V-2`, `V-3`, and `V-4`.)

## Repository Findings

**Repository basis:** Branch `container-deploy-versioning`, commit `768b5c473bd6`, planning date 2026-10-10. The worktree has existing edits to the Phase 1 task plan and phase plan, plus an untracked `.github/skills/review-pr/` directory. These are unrelated to this task-plan target and were left unchanged. No Phase 2 task plan existed at the target path.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| [Phase plan](./CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md), Phase 2 | Phase 2 is ready for a task plan. It fixes `/usr/local/sbin/`, `/opt/shape-shifter/<user>/container-releases/<tag>/`, separate install/activate/rollback/status operations, home-relative path resolution, and two disposable non-production users. | These decisions are treated as fixed. This plan uses an atomic symlink selector for `~/container`; activation refuses to replace an existing real directory or an unrelated symlink. |
| `container/scripts/load-env.sh` | Resolves relative `CONFIG_DIR`, `DATA_DIR`, and `CONTAINER_DATA_DIR` against the physical parent of the checkout. | Resolve relative overrides from `$HOME` instead, and keep absolute overrides unchanged. |
| `container/Makefile::resolve_path` | Resolves relative paths against `CHECKOUT_PARENT`; Make and shell currently agree on that checkout-relative behavior. | Change both implementations together and test them through a symlinked `~/container`. |
| `container/scripts/container.sh::check_deployment`, `container/service/shape-shifter.service` | The dispatcher sources `load-env.sh`; the user unit uses `WorkingDirectory=%h/container` and calls `~/container/scripts/container.sh`. | Keep this path and entry point working when `~/container` selects a read-only versioned directory. |
| `container/scripts/deploy/deploy_single_environment.sh` | Downloads a repository archive into `~/container`, copies over an existing directory, and records its `--ref` as `GIT_REF` and the derived `IMAGE_NAME`. | Stop this helper from replacing the selected container bundle. Keep application image source settings separate from the container release tag. |
| `container/scripts/deploy/sync-to-deploy` | Uses `rsync --delete` to synchronize into the deployment user's container directory and then changes ownership. | Keep it for isolated development only and reject a target that resolves to the administrator-owned release selection. |
| `container/scripts/deploy/deploy_all_environments.sh` | Calls the single-environment helper for each `USER:PORT` pair. | Document that each target user must already have its own selected container release; do not add implicit group activation. |
| `container/scripts/verify/verify_container_release.sh` | Its `archive` mode checks the archive's single `container/` root, version, and required deployment files. | Reuse the archive contract during install after safe staging; separately verify the downloaded checksum and exact tag/source identity. |
| `container/README.md`, `container/DEPLOYMENT.md`, `container/.env.example`, `container/scripts/container.sh` | Explain checkout-relative overrides, direct checkout replacement, or the old installation path/error text. The README says host installation is not yet available. | Update deployment instructions and diagnostics with the released install/select flow and the home-relative path rule. |
| Existing tests and local checks | No automated shell test suite exists under `container/`. `bash -n` passed for the current path/deploy scripts. `shellcheck` reports existing diagnostics in `sync-to-deploy` (SC1007 warnings and SC2029 informational notices) and SC1091 source-file notices. `make -C container info` passed with a temporary home; relative overrides resolved under the repository checkout. A temporary-home `load-env.sh` check also resolved relative overrides under the checkout. | Add focused shell regression tests. Compare ShellCheck output against the recorded baseline rather than claiming existing diagnostics are new. Two-user, permissions, and activation tests require a disposable Linux/systemd host and are not run during planning. |

## Scope

**In scope**

- Resolve relative `CONFIG_DIR`, `DATA_DIR`, and `CONTAINER_DATA_DIR` overrides against the deployment user's home in Make and shell scripts.
- Add one root-run host release manager with exact-tag `install`, `activate`, `rollback`, and `status` operations.
- Download and verify GitHub Release assets, validate and stage their complete archive, and install immutable-per-tag contents under the approved administrator-owned directory.
- Select a release through `~/container` without changing `~/config`, `~/container-data`, `GIT_REF`, or `IMAGE_NAME`.
- Prevent the existing production deployment helper and development sync helper from overwriting administrator-owned selected releases.
- Update container deployment documentation and add targeted shell tests.

**Out of scope**

- Changing application image source/version behavior, `GIT_REF`, or `IMAGE_NAME` as a side effect of release-manager operations.
- Automatically activating a published release, synchronizing selections between environments, or installing a release during publication.
- Replacing or deleting an existing `~/container` directory without administrator review.
- Finishing the lifecycle dispatcher or retiring verification scripts; those belong to Phase 3.
- Running on production accounts or restarting production services for validation.

## Work Breakdown

### Area 1: Resolve deployment paths from the user's home

**Objective:** Make direct scripts and Make resolve defaults and relative overrides consistently, independent of the physical release directory.

**Affected code:** `container/scripts/load-env.sh`; `container/Makefile::resolve_path`; `container/scripts/container.sh::check_deployment`; `container/.env.example`; `container/README.md`; `container/DEPLOYMENT.md`; `container/tests/test_path_resolution.sh` (`NEW`).

**Dependencies:** None.

**Tasks:**

* [x] `T2.1` **Change:** Resolve relative deployment paths from `$HOME`. *(Implemented 2026-10-10: `load-env.sh`, `Makefile::resolve_path`, `container.sh` diagnostics, `.env.example`, `README.md` and `DEPLOYMENT.md` updated; `V-1` passed.)*
  * **Target:** `container/scripts/load-env.sh`, `container/Makefile::resolve_path`, their path comments/diagnostics, and `container/tests/test_path_resolution.sh` (`NEW`).
  * **Current → required:** Relative paths resolve beside the physical checkout; resolve relative `CONFIG_DIR`, `DATA_DIR`, and `CONTAINER_DATA_DIR` against the deployment user's home. Preserve absolute overrides and existing environment/configuration precedence.
  * **Implementation:** Keep shell and Make path rules identical, including selection of `deployment.env` when `CONFIG_DIR` is supplied as a relative environment or command-line override. Exercise both the normal directory and a `~/container` symlink to a versioned release path. Do not source or rewrite application image settings as part of path resolution.
  * **Constraints:** Preserve `ENV_FILE` support, absolute paths, `CONFIG_DIR/deployment.env` behavior, and the current default directories `~/config` and `~/container-data`.
  * **Validation:** `V-1`; assert default paths, relative and absolute overrides, environment/config precedence, and equal results from `load-env.sh` and `make -C ... info`.

**Completion evidence:** The new path regression test passes through a symlinked `~/container`; Make and direct shell callers resolve all three paths to the same home-relative locations.

### Area 2: Install and verify exact releases without activation

**Objective:** Install one complete, verified release into administrator-controlled per-user storage without changing the selected version.

**Affected code:** `container/scripts/deploy/manage_container_release.sh` (`NEW`); `container/tests/test_release_manager.sh` (`NEW`); `container/scripts/verify/verify_container_release.sh` (existing archive contract).

**Dependencies:** `T2.1` for correct operation after selecting a version; install itself does not activate a release.

**Tasks:**

* [x] `T2.2` **Change:** Add safe exact-tag release installation. *(Implemented 2026-10-10: `manage_container_release.sh` (`NEW`) `install`; `V-2` and `V-3` passed. Source-commit resolution now prefers `git ls-remote` because `api.github.com` is rate-limited for this network.)*
  * **Target:** `container/scripts/deploy/manage_container_release.sh` (`NEW`) and `container/tests/test_release_manager.sh` (`NEW`).
  * **Current → required:** No host release manager exists. Add a root-only command interface `install|activate|rollback|status USER [container-vX.Y.Z]`; `install` requires a valid dedicated user and an exact `container-vX.Y.Z` tag.
  * **Implementation:** Fetch the named GitHub Release archive and checksum by exact tag; resolve the annotated tag's peeled commit and record it separately from application settings. Verify the checksum before extraction; reject missing assets, mismatched version/tag, malformed release identity, incomplete archives, absolute or parent-traversal archive paths, and extraction failures. Extract into a temporary sibling under `/opt/shape-shifter/<user>/container-releases/`, validate the extracted bundle with its `scripts/verify/verify_container_release.sh archive` check, then move it into `<tag>/container`. Set root ownership and remove write permission from deployment-user access while preserving file execute bits. Do not overwrite an existing tag directory; accept it only if its stored tag/commit and required contents validate, otherwise fail clearly.
  * **Constraints:** `install` must not change `~/container`, `~/config`, `~/container-data`, `GIT_REF`, or `IMAGE_NAME`. Never accept a branch name, `latest`, arbitrary repository URL, or user-controlled storage path. Check required host commands before starting and clean only the command's own temporary directory on failure.
  * **Validation:** `V-2` and `V-3`; test valid `container-v0.1.0`, missing/invalid tags, checksum mismatch, version mismatch, incomplete archive, unsafe archive entries, install interruption, and an existing conflicting tag directory. Assert the active selector and application settings remain byte-for-byte unchanged.

**Completion evidence:** A valid exact release is present under its version directory, root-owned and not writable by its deployment user; all tested failures leave the selection untouched.

### Area 3: Activate, inspect, and roll back one environment

**Objective:** Change only one deployment user's selected release and retain a local rollback target.

**Affected code:** `container/scripts/deploy/manage_container_release.sh` (`NEW`); `container/tests/test_release_manager.sh` (`NEW`); `container/service/shape-shifter.service`; `container/scripts/load-env.sh`.

**Dependencies:** `T2.1` and `T2.2`.

**Tasks:**

* [x] `T2.3` **Change:** Implement atomic per-user selection, status, and rollback. *(Implemented 2026-10-10: `manage_container_release.sh` (`NEW`) `activate`/`rollback`/`status`; `V-2` and `V-4` passed.)*
  * **Target:** `container/scripts/deploy/manage_container_release.sh` (`NEW`) and `container/tests/test_release_manager.sh` (`NEW`).
  * **Current → required:** The service uses `~/container`, but that path is a mutable checkout. Make it a symlink to an administrator-controlled per-user selector under `/opt/shape-shifter/<user>/`; the selector points to the installed `<tag>/container`.
  * **Implementation:** `activate` selects only an already-installed, validated tag and atomically replaces the per-user selector; preserve the previous selected tag for `rollback`. `rollback` works offline and swaps to the retained installed tag. `status` reports selected tag and source commit separately from `GIT_REF` and `IMAGE_NAME`, reading only those keys rather than evaluating `deployment.env`. Serialize operations per user. For first transition, refuse to replace a real `~/container` directory or unrelated symlink; leave it intact and report that an administrator must review and move it before activation. Never switch another user's selector.
  * **Constraints:** Preserve `~/config`, `~/container-data`, the systemd `WorkingDirectory=%h/container`, and existing application image settings. Do not install or activate on behalf of every environment as a side effect of a multi-environment command.
  * **Validation:** `V-2`, `V-3`, and `V-4`; verify atomic selection, repeated activation, offline rollback, unknown/uninstalled tags, a broken selected bundle, real-directory and unrelated-symlink refusal, and status output.

**Completion evidence:** Each disposable test user has an independent selected tag and rollback target; users cannot write installed content; failures do not change active selection, configuration, data, or application image settings.

### Area 4: Route deployment and documentation through selected releases

**Objective:** Keep production helpers from fetching or overwriting the active container bundle while retaining an isolated local-development sync path.

**Affected code:** `container/scripts/deploy/deploy_single_environment.sh`; `container/scripts/deploy/deploy_all_environments.sh`; `container/scripts/deploy/sync-to-deploy`; `container/README.md`; `container/DEPLOYMENT.md`; `container/.env.example`; `container/tests/test_path_resolution.sh` (`NEW`); `container/tests/test_release_manager.sh` (`NEW`).

**Dependencies:** `T2.2` and `T2.3`.

**Tasks:**

* [x] `T2.4` **Change:** Remove mutable checkout replacement from production deployment flows. *(Implemented 2026-10-10: `deploy_single_environment.sh`, `deploy_all_environments.sh`, `sync-to-deploy`, `README.md`, `DEPLOYMENT.md` updated; `V-1`, `V-3`, `V-4`, and `V-5` passed.)*
  * **Target:** The deployment helpers and container deployment documentation listed above.
  * **Current → required:** `deploy_single_environment.sh` fetches and copies a repository archive into `~/container` and ties that ref to `GIT_REF`/`IMAGE_NAME`; `sync-to-deploy` uses `rsync --delete`. Production deployment must operate on an explicitly selected release, not replace it from a moving branch or application-image ref.
  * **Implementation:** Make `deploy_single_environment.sh` require a valid selected `~/container` release and stop downloading or copying container files. Keep its repository/ref options, if retained, scoped to application image configuration only. Keep `deploy_all_environments.sh` per-user and require each target's selection to be prepared explicitly; it must not activate a shared version. Make `sync-to-deploy` refuse a target that resolves to an administrator-owned release, and document its use only for isolated development with an explicit non-production destination such as `container-dev`. Document the manual first-transition review, exact-tag install/activate/status/rollback commands, source-commit reporting, permissions, failure behavior, and home-relative path rules.
  * **Constraints:** Do not delete or automatically relocate an existing `~/container`; do not write a container tag into `GIT_REF` or alter `IMAGE_NAME` during install/activate/rollback. Keep configuration and data outside the release tree.
  * **Validation:** `V-1`, `V-3`, and `V-4`; verify helpers refuse to overwrite selected releases, application ref/image behavior remains explicit and separate, and documentation commands match the manager interface.

**Completion evidence:** Production helpers preserve the active release; local sync is explicitly isolated; operator docs describe the tested path and per-environment workflows.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (`P-AC-2`) | `T2.2`, `T2.3` | `V-2`, `V-3` | Exact release is complete under `/opt/shape-shifter/<user>/container-releases/<tag>/`; files are root-owned, readable/executable, and not deployment-user-writable. |
| `PH2-AC-2` (`P-AC-3`) | `T2.3`, `T2.4` | `V-4` | Two users retain independent tags through activation and offline rollback; both `GIT_REF` and `IMAGE_NAME` values remain unchanged. |
| `PH2-AC-3` (`P-AC-4`) | `T2.2`, `T2.3` | `V-2`, `V-3` | Fetch, checksum, extraction, validation, and selection failures leave the prior `~/container` target unchanged. |
| `PH2-AC-4` (`P-AC-5`) | `T2.1`, `T2.3`, `T2.4` | `V-1`, `V-4` | Config/data checksums remain unchanged; default and relative path overrides resolve from home through the selected symlink; absolute paths remain unchanged. |
| `PH2-AC-5` (`P-AC-6`) | `T2.2`, `T2.3` | `V-2`, `V-3`, `V-4` | Status reports exact container tag and source commit separately and leaves `GIT_REF` and `IMAGE_NAME` untouched. |
| `PH2-AC-6` (`P-AC-9`) | `T2.2`, `T2.3` | `V-2`, `V-3`, `V-4` | One root-owned host script, installed under `/usr/local/sbin/`, installs without activation and can activate, roll back, and report each user's selection while the selected bundle itself is unavailable. |

## Validation And Testing

`V-1` through `V-5` implement `VM-2` and `VM-3`. During planning, `bash -n` passed for the existing loader, dispatcher, deployment helpers, and sync script. ShellCheck baseline diagnostics are recorded above. `make -C container info` passed with a temporary home and confirmed current default paths use home; relative overrides currently resolve beside the repository checkout. The two-user, permissions, and systemd checks require an isolated Linux host and were not run during planning. Execution results for the implemented changes are recorded in the [Execution Record](#execution-record).

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Home-relative path contract in `load-env.sh`, Make, and `container.sh` | `bash container/tests/test_path_resolution.sh` (`NEW`); the test creates a temporary home, `deployment.env`, and `~/container` symlink, then checks direct-shell and `make -C "$HOME/container" info` outputs for defaults, relative overrides, absolute overrides, and precedence. Also run `bash -n container/scripts/load-env.sh container/scripts/container.sh container/scripts/deploy/deploy_single_environment.sh`. | `PH2-AC-4` | All three path variables resolve identically from `$HOME` through the symlink; absolute overrides stay absolute; configuration and CLI/environment precedence is preserved. | Not run: test file is new. Existing shell syntax check passed. |
| `V-2` | Release manager archive and failure handling | `bash container/tests/test_release_manager.sh` (`NEW`) using temporary directories and local fixtures; cover exact-tag syntax, matching `VERSION`, checksum success/failure, source commit parsing, required files, archive traversal/absolute paths, interrupted staging, and existing tag conflicts. | `PH2-AC-1`, `PH2-AC-3`, `PH2-AC-5`, `PH2-AC-6` | Valid bundles stage completely; invalid or incomplete candidates fail before selection changes; same-tag installs never overwrite existing files. | Not run: test file and manager functions are new. |
| `V-3` | One-user host install and access controls | On a disposable Linux/systemd host with two non-production users, install exact published `container-v0.1.0` for the first user using `sudo /usr/local/sbin/shape-shifter-container-release install USER container-v0.1.0`; inspect tag/source commit, installed path, owner/mode, and `~/container` before and after. Check write access as that user and attempt an invalid/nonexistent tag. | `PH2-AC-1`, `PH2-AC-3`, `PH2-AC-5`, `PH2-AC-6` | Installation records the peeled tag commit, files are administrator-owned and not writable by the deployment user, installation does not activate, and invalid fetches preserve current selection. | **Passed 2026-10-10:** disposable Podman container host, 93 assertions, exit 0. See the [Execution Record](#execution-record). |
| `V-4` | Two-user activation, rollback, and state preservation | On the same disposable host, snapshot each user's selector, `~/config/deployment.env`, `~/config`, and `~/container-data`; install the release for both users, activate different installed versions where available (use `container-v0.1.0` for at least one), then activate and roll back one user with network access disabled. Test unknown/uninstalled tags, broken selected content, and first-transition directory refusal. | `PH2-AC-2`, `PH2-AC-3`, `PH2-AC-4`, `PH2-AC-5`, `PH2-AC-6` | Only the requested user's selector changes; rollback succeeds offline; both users' image settings, configuration, data, and unselected release remain unchanged; failures leave the active selector intact. | **Passed 2026-10-10:** same disposable host with three non-production users, offline stage run with `--network=none`, 37 assertions, exit 0. The second version was locally built because only `container-v0.1.0` is published. See the [Execution Record](#execution-record). |
| `V-5` | Deployment helper and documentation regression | Run `bash -n` and `shellcheck` on changed shell files; run `bash container/tests/test_path_resolution.sh` and `bash container/tests/test_release_manager.sh`; inspect updated README/DEPLOYMENT examples against the implemented CLI. On the disposable host, run `sync-to-deploy --dry-run --remote-dir container-dev` and confirm it refuses a manager-owned `~/container` target. | `PH2-AC-2`, `PH2-AC-4`, `PH2-AC-5`, `PH2-AC-6` | Production helpers do not copy into or activate `~/container`; local sync targets only the isolated development path; new code adds no ShellCheck diagnostics beyond recorded baseline; docs match tested operations. | **Passed 2026-10-10:** only the two pre-existing `sync-to-deploy` SC1007 warnings remain; the guard refused the manager-owned target and allowed `container-dev` both locally and on the disposable host. See the [Execution Record](#execution-record). |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Home-relative path resolution | `container/scripts/load-env.sh`; `container/Makefile`; `container/scripts/container.sh`; `container/.env.example` | `T2.1` | Direct shell and Make tests pass through a temporary `~/container` symlink. |
| Path regression test | `container/tests/test_path_resolution.sh` (`NEW`) | `T2.1`, `T2.4` | Covers defaults, relative/absolute overrides, precedence, and symlink path resolution. |
| Host release manager | `container/scripts/deploy/manage_container_release.sh` (`NEW`), manually installed as `/usr/local/sbin/shape-shifter-container-release` | `T2.2`, `T2.3` | Installs and validates an exact release, controls selection, and reports tag/source commit without altering application settings. |
| Release manager regression test | `container/tests/test_release_manager.sh` (`NEW`) | `T2.2`, `T2.3` | Covers release validation, safe staging, selection failures, and no-overwrite behavior. |
| Deployment helper and local-sync safeguards | `container/scripts/deploy/deploy_single_environment.sh`; `container/scripts/deploy/deploy_all_environments.sh`; `container/scripts/deploy/sync-to-deploy` | `T2.4` | Production helpers require the selected release and do not overwrite it; local sync rejects administrator-owned release targets. |
| Operator documentation | `container/README.md`; `container/DEPLOYMENT.md`; `container/.env.example` | `T2.1`, `T2.4` | Documents install, activate, status, rollback, first transition, permissions, exact tags, and home-relative paths. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Resolve deployment paths from the user's home | Done | None | `V-1` passed (27 assertions). Loader and Makefile agree for defaults, relative and absolute overrides, precedence, and `ENV_FILE`. |
| Area 2: Install and verify exact releases without activation | Done | Area 1 | `V-2` (79 assertions) and `V-3` (on a disposable container host) passed. |
| Area 3: Activate, inspect, and roll back one environment | Done | Areas 1 and 2 | `V-2` covers atomic selection, offline rollback, refusals, and status with a broken bundle; `V-4` confirmed it across two real users on a disposable host, including an offline rollback. |
| Area 4: Route deployment and documentation through selected releases | Done | Areas 2 and 3 | `V-1`, `V-3`, `V-4`, and `V-5` passed. The local `sync-to-deploy` guard and the disposable-host checks were exercised. |

## Execution Record

Implementation date 2026-10-10, branch `container-deploy-versioning`. The first pass started from commit `768b5c47`; the host validation ran after the branch tip advanced to `6cfaf910` (`feat(review-pr): ...`), which is unrelated to this phase. Pre-existing worktree changes to the Phase 1 task plan and the phase plan were left unchanged. This phase's changes are uncommitted.

**Implemented deliverables:**

- `container/scripts/load-env.sh`, `container/Makefile`, `container/scripts/container.sh`, `container/.env.example`: relative `CONFIG_DIR`, `DATA_DIR`, and `CONTAINER_DATA_DIR` overrides and the `deployment.env` lookup now resolve from `$HOME`; absolute overrides are unchanged (`T2.1`).
- `container/tests/test_path_resolution.sh` (`NEW`): temporary home, versioned release directory, and `~/container` symlink; asserts loader/Make agreement and expected values (`T2.1`).
- `container/scripts/deploy/manage_container_release.sh` (`NEW`): root-only `install|activate|rollback|status USER [container-vX.Y.Z]` host manager (`T2.2`, `T2.3`).
- `container/tests/test_release_manager.sh` (`NEW`): 79 checks against the manager using temporary directories, `file://` assets, and a local bare git remote (`T2.2`, `T2.3`).
- `container/scripts/deploy/deploy_single_environment.sh`, `container/scripts/deploy/deploy_all_environments.sh`, `container/scripts/deploy/sync-to-deploy`: production helpers require a selected release, `--repo`/`--ref` stay scoped to application image settings, and `sync-to-deploy` refuses a manager-owned target and points isolated development at `container-dev` (`T2.4`).
- `container/README.md`, `container/DEPLOYMENT.md`, `container/.env.example`: released install/select workflow, first transition, permissions, failure behavior, source-commit reporting, the optional `git` requirement, and the home-relative path rule (`T2.1`, `T2.2`, `T2.4`).

**Fixes made during host validation:**

- `F2-1` `api.github.com` refused unauthenticated requests from the validation network with `API rate limit exceeded` (HTTP 403), so the original resolver could not record a source commit and `install` failed. `resolve_source_commit` now tries `git ls-remote` on the annotated tag's peeled ref first and falls back to the API tag lookup and the release notes. `git` is optional; the fallbacks are unchanged. Covered by a local test with no API fixture at all and by the host run, where `git` resolved the real tag.

**Validation results (2026-10-10):**

| ID | Result | Evidence |
| --- | --- | --- |
| `V-1` | Passed | `bash container/tests/test_path_resolution.sh`: 27 assertions passed, exit 0. `bash -n` passed for the changed shell files. |
| `V-2` | Passed | `bash container/tests/test_release_manager.sh`: 79 assertions passed, exit 0. |
| `V-3` | Passed | Disposable Podman container host (rootless Podman 5.7.0, `python:3.13-slim` base with `curl` and `git`), `--network=host`: 93 assertions passed, exit 0. Installed the real published `container-v0.1.0`; `release-info` recorded `COMMIT=71f52f8268daed3f04c501e50cf59341fbb1273d`, the Phase 1 merge commit. Installed tree is `root:root` with no group/other write bits; the deployment user could read and execute but could not modify, create, or delete installed content. Install created no selector and no `~/container`, and left `deployment.env` byte-identical. |
| `V-4` | Passed | Same disposable host with two real deployment users, then a second container started with `--network=none`: 37 assertions passed, exit 0. `rollback` succeeded with no network and restored the previous version; each user kept its own selection; configuration, credentials, runtime data, ownership, modes, and `GIT_REF`/`IMAGE_NAME` were unchanged; a missing selected bundle was reported without hiding the selection and could not be activated; a real `~/container` directory and an unrelated symlink were both refused and left intact. |
| `V-5` | Passed | `bash -n` and `shellcheck -S warning` report only the two pre-existing `sync-to-deploy` SC1007 warnings and no new diagnostics. Both new test scripts pass. The local `sync-to-deploy` guard was exercised with exported `sudo`/`getent` functions: a symlinked manager `~/container` was refused with exit 1, and `--remote-dir container-dev` was allowed with exit 0 in dry-run. On the disposable host, `sync-to-deploy --dry-run` against the manager-owned `~/container` was refused and against `container-dev` was allowed. |

**Acceptance criteria with supporting evidence:**

- `PH2-AC-1` (`P-AC-2`): the installed `container-v0.1.0` tree under `/opt/shape-shifter/ss-phase2-a/container-releases/container-v0.1.0/` is complete and `root:root`; the deployment user could read and execute it but every write, create, and delete attempt failed (`V-2`, `V-3`).
- `PH2-AC-2` (`P-AC-3`): activating and rolling back one user left the other user's selection, and both users' `GIT_REF` and `IMAGE_NAME` values, unchanged (`V-2`, `V-4`).
- `PH2-AC-3` (`P-AC-4`): checksum mismatch, version/tag mismatch, incomplete archive, absolute and parent-traversal archive paths, unreadable archive, missing asset, and a tag with no published asset all left the selection untouched and cleaned up staging (`V-2`, `V-3`).
- `PH2-AC-4` (`P-AC-5`): configuration, credentials, runtime data, and their ownership and modes were unchanged by install, activate, and rollback; relative and default paths resolved from home through the `~/container` symlink and absolute overrides were unchanged (`V-1`, `V-2`, `V-4`).
- `PH2-AC-5` (`P-AC-6`): `status` reported the exact container tag and source commit separately from `GIT_REF` and `IMAGE_NAME`, reading those keys without evaluating `deployment.env`, both online and with networking disabled (`V-2`, `V-3`, `V-4`).
- `PH2-AC-6` (`P-AC-9`): one root-owned script installed under `/usr/local/sbin/` installed a named release without selecting it and activated, rolled back, and reported each user's selection, including when the selected bundle was missing and while the host had no network access (`V-2`, `V-3`, `V-4`).

**Definition Of Done:** satisfied for `V-1` through `V-5`. Two limits are recorded rather than claimed as passed:

- The validation host was a container, not a systemd host, so `WorkingDirectory=%h/container`, the user service, and service start/stop through the selected release were not exercised. Those belong to Phase 3 (`PH3-AC-1`). The unit file, its `~/container` entry point, and the resolved paths were inspected but not started.
- Only `container-v0.1.0` is published. The second version used for the two-version rollback was built locally from the reviewed `container/` tree with the repository's own `git archive` packaging command and `VERSION` bumped to `0.2.0`, served from local storage, and installed with only the asset and git sources redirected. The release root stayed at the production path and the users were real system users. It is not a published GitHub release, and no release was published for this validation.

**Residual observations (not changed; outside this task plan's named deliverables):**

- `container/scripts/deploy/bootstrap-authentication-and-authorization.sh` still derives its default `CONFIG_DIR` from the script's physical location. It resolves to `~/config` when invoked through `~/container` (the documented path), but not when invoked by a physical release path. Recorded for follow-up.
- `container/resources/backend.env.example`, `container/resources/.pgpass.example`, `container/scripts/setup.sh`, and the verification scripts still use "checkout" for the deployment tree. This is wording only and does not affect behaviour; the task plan named only `.env.example` for documentation scope.
- The host validation harness lives outside the repository at `/tmp/ss-phase2/` (`Containerfile`, `lib.sh`, `setup_common.sh`, `validate_online.sh`, `validate_offline.sh`). It is not part of this task plan's deliverables and is not committed; re-running the checks requires recreating it.

## Definition Of Done

- [x] Every `PH2-AC-*` criterion has implementation and validation evidence mapped to its `T*` and `V*` IDs.
- [x] All four work areas and their deliverables are complete.
- [x] `V-1` and `V-2` automated tests pass; ShellCheck introduces no new diagnostics beyond the documented baseline.
- [x] `V-3` and `V-4` pass on two disposable non-production users on a disposable container host; no production account or service was changed for validation. The container host has no systemd, so unit-driven start/stop was not exercised and is recorded as a limit.
- [x] The `~/container` transition preserves an existing real directory until an administrator reviews and moves it (`V-2`, `V-4`).
- [x] Activation/rollback preserve config, credentials, runtime data, and application image settings; rollback works without network access (`V-2`, `V-4`).
- [x] Deployment, local-development, and operator documentation match the implemented command behaviour, including the optional `git` requirement.
- [x] Deviations, baseline warnings, and remaining follow-up are recorded; no unresolved decision affects implementation or validation.

## Risks And Open Questions

- The relative-path contract changed from checkout-relative to home-relative. Explicit relative overrides in an existing `deployment.env` now resolve under the deployment user's home; `T2.1` documents this and `V-1` verifies default and absolute-path behaviour.
- The initial `~/container` directory may contain unreviewed deployment files. The manager refuses to replace a real directory or an unrelated symlink and requires administrator review; verified by `V-2` and `V-4`.
- `api.github.com` is rate-limited per network address and refused unauthenticated requests during host validation. Source-commit resolution now prefers `git ls-remote`; a host without `git` still depends on the API and can fail until the limit resets. Recorded as `F2-1`.
- Only `container-v0.1.0` is published, so the two-version rollback check used a locally built bundle. Re-validating with two genuinely published releases remains open.
- Administrator-owned storage protects bundle files from ordinary deployment-user writes, but it is not a security boundary against a user who controls their account or user systemd manager.
- The validation host was a container without systemd, so unit-driven start and stop through the selected release was not exercised. `PH3-AC-1` covers that in Phase 3.
- The Phase 1 live retry check was waived. The reviewed workflow's retry-recovery defect remains a separate follow-up; Phase 2 uses the successful `container-v0.1.0` asset and does not claim retry recovery is fixed.
