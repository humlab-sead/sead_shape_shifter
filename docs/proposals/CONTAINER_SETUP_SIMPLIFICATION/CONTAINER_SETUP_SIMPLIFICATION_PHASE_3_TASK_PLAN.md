# Container Setup Simplification — Phase 3 Task Plan

## Phase Summary

**Phase:** Phase 3 — Simplify Remaining Container Commands  
**Goal:** Remove duplicated helper names, defaults, and dispatch while preserving current command behavior.  
**Readiness:** Validated  
**Dependencies:** Phase 2 establishes the runtime bundle and source-only host-tool tree. Its task plan marks all areas done, and those changes are present in the current worktree. The worktree is uncommitted; implementation must retain the current Phase 2 paths and contracts.

**Sources**

- [Container Setup Simplification proposal](./CONTAINER_SETUP_SIMPLIFICATION.md)
- [Container Setup Simplification phase plan](./CONTAINER_SETUP_SIMPLIFICATION_PHASE_PLAN.md)
- [Phase 2 task plan](./CONTAINER_SETUP_SIMPLIFICATION_PHASE_2_TASK_PLAN.md)

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-6`): The sourced helpers are `_load-env.sh` and `_env-config.sh` with separate responsibilities; defaults, service dispatch, and project commands use the proposed single implementations without changing intended behavior.
- `PH3-AC-2` (from `P-AC-7`): Removed scripts and targets have no active callers, and active documentation and workflows use valid paths.
- `PH3-AC-3` (from `P-AC-8`): Service and rollback behavior remain intact.

**Phase-plan validation milestones covered:** `VM-7`, `VM-8`, `VM-9`.

**Fixed decisions and constraints**

- `_load-env.sh` loads deployment configuration and resolves paths. `_env-config.sh` provides image-tag and environment-file functions. Do not combine them into a generic helper.
- Preserve the existing Make command and direct-script precedence: command-line or environment overrides, then `CONFIG_DIR/deployment.env`, then shared defaults.
- Keep project adoption and movement as distinct operations. Preserve each operation's validation, dry-run, confirmation, and verification behavior; a failed authorization move must still restore the folder.
- Keep service unit naming and service behavior, but route service actions through `container.sh service <action>`.
- Keep `get-install.sh` functionality: it is an operator-documented host prerequisite check, not a dead command. Move it out of the runtime bundle to the source-only host tools, as deferred in the Phase 2 task plan.

## Repository Findings

**Repository basis:** Branch `container-setup-simplifications`, commit `a0c46fed`, planning date 2026-10-11. Existing Phase 2 implementation and planning changes are uncommitted and were considered; only this task plan is being added.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `container/Makefile`, `container/.env.example`, `container/scripts/container.sh`, `container/scripts/build.sh` | Shared settings such as `IMAGE_NAME`, `HOST_PORT`, `COMPOSE_PROJECT_NAME`, `GIT_REPO`, and `GIT_REF` have fallback values in more than one place. `.env.example` already contains their deployment values in plain `KEY=value` form. | Use one fallback source for the shared deployment values. Preserve caller and deployment-file overrides and the existing home-relative path rules. |
| `container/scripts/load-env.sh` and its callers in `container/scripts/{authorization,backup,build,container,healthcheck,move-project,setup}.sh` | The loader parses `CONFIG_DIR/deployment.env`, preserves values already in the environment, and resolves configuration and data paths. `env-config.sh` defines image-tag and env-file functions without loading configuration. Host deploy and NGINX scripts also refer to the old helper names. | Rename both helpers and update every caller, source annotation, test, and operator reference without merging their responsibilities. |
| `container/scripts/service.sh`, `container/scripts/container.sh`, `container/Makefile`, `container/service/shape-shifter.service` | Make service targets dispatch to `service.sh`; the systemd unit uses `container.sh up` and `container.sh down`. The container dispatcher currently owns the container lifecycle actions. | Move service actions into a `service` subcommand and keep lifecycle and systemd unit behavior unchanged. Service actions must not require Podman. |
| `container/scripts/adopt-project.sh`, `container/scripts/move-project.sh`, `container/scripts/authorization.sh` | Adoption writes and imports an owner manifest, then verifies the resource and grant. Movement checks source and target paths and authorization state, supports dry-run and confirmation, and restores the folder if the authorization update fails. | Add one `project.sh adopt|move` entry point and shared path/authorization helpers while keeping the two sets of safeguards distinct. |
| `container-host/deploy/manage_container_release.sh`, `container-host/verify/verify_container_release.sh`, `container-host/tests/test_release_bundle_contents.sh`, `container-host/tests/test_required_files_contract.sh` | The two trusted required-file lists and bundle inventory currently name `load-env.sh`, `env-config.sh`, and `service.sh`. The project scripts are not yet in the required-file inventory. | Update both trusted lists and the bundle test in the same change to require the renamed helpers and `project.sh`, and stop requiring removed entry points. |
| `container/DEPLOYMENT.md`, `docs/AUTHORIZATION.md`, `container-host/deploy/deploy_environment.sh`, `container-host/deploy/install_nginx_reverse_proxy.sh` | Active operator and host-tool references use the old helper, service, move-project, and `get-install.sh` paths. | Update active references. Move the documented host prerequisite check to `container-host/deploy/`; do not leave a host check in the deployable bundle. |
| `container/scripts/get-install.sh` and `container/DEPLOYMENT.md` | The script checks Podman, `podman-compose`, lingering, and rootless namespaces. The deployment guide refers to it, contrary to the Phase 2 finding that it had no documentation reference. Phase 2 deferred its disposition to this phase. | Treat the current source and guide as authoritative: preserve the check and move the script to `container-host/deploy/get-install.sh`. |

### Baseline Results

- `bash container-host/tests/test_lifecycle.sh` — **Pass**.
- `bash container-host/tests/test_path_resolution.sh` — **Pass**.
- `bash container-host/tests/test_release_bundle_contents.sh` — **Pass**; current inventory reports 20 required runtime files.
- `bash container-host/tests/test_required_files_contract.sh` — **Pass**; the verifier and manager lists match.
- `bash container-host/tests/test_release_manager.sh` — **Pass** with `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.bareRepository GIT_CONFIG_VALUE_0=all`. Without that one-command test setting, Git refuses the test's temporary bare repository because the current Git configuration sets `safe.bareRepository=explicit`.
- `shellcheck --severity=error container/scripts/*.sh container-host/deploy/*.sh container-host/verify/verify_container_release.sh container-host/tests/*.sh` — **Pass**.
- Default-severity ShellCheck on the current scripts — **Fail** on existing warnings and informational diagnostics, including `SC1007`, `SC2034`, `SC2155`, `SC2001`, and `SC1091`. Do not broaden this phase to unrelated cleanup; check for new diagnostics in touched files.
- No project-command regression suite exists in the current tree; add one for the combined command.

## Scope

**In scope**

- Rename and update the two sourced helpers and all active callers.
- Resolve shared deployment-setting defaults once while preserving precedence and path behavior.
- Route Makefile service targets through `container.sh service <action>`.
- Replace the separate project scripts with `project.sh adopt|move`.
- Move the host prerequisite checker from `container/scripts/` to `container-host/deploy/`.
- Update active documentation, host-tool references, release required-file lists, bundle inventory, and shell regression tests.

**Out of scope**

- Changing project authorization policy, service unit behavior, release selection, or rollback behavior.
- Changing the `deploy_environment.sh` user-facing options or deployment image-setting contract.
- Changing the behavior of the prerequisite check or adding host operations tooling.
- Removing documented Make targets without a verified absence of active use.
- Reworking historical proposal documents or unrelated ShellCheck warnings.

## Work Breakdown

### Area 1: Unify configuration helper names and defaults

**Objective:** Give sourced helpers clear internal names and make Make targets and direct runtime scripts use the same shared fallback values.

**Affected code:** `container/.env.example`, `container/Makefile`, `container/scripts/load-env.sh` → `container/scripts/_load-env.sh` (`NEW` path), `container/scripts/env-config.sh` → `container/scripts/_env-config.sh` (`NEW` path), `container/scripts/{authorization,backup,build,container,healthcheck,setup}.sh`, `container-host/deploy/{deploy_environment,install_nginx_reverse_proxy}.sh`, `container-host/tests/test_path_resolution.sh`.

**Dependencies:** None.

**Tasks:**

* [x] `T1.1` **Change:** Rename the sourced helpers and update all active source paths.
  * **Target:** `container/scripts/load-env.sh` → `container/scripts/_load-env.sh`; `container/scripts/env-config.sh` → `container/scripts/_env-config.sh`; all listed callers and release references.
  * **Current → required:** Callers source the old filenames. They must source the underscored names while preserving loader path/config behavior and the separate env-config functions.
  * **Implementation:** Update ShellCheck source annotations, helper examples and comments, the host deploy and NGINX paths, and tests/inventories. Do not source `_env-config.sh` from callers that only need configuration loading.
  * **Constraints:** Keep `_load-env.sh` responsible for deployment configuration and path resolution. Keep `_env-config.sh` limited to image-tag and environment-file functions.
  * **Validation:** `V-1`, `V-4`, and `V-6`.
* [x] `T1.2` **Change:** Remove duplicate fallback values for shared deployment settings.
  * **Target:** `container/.env.example`, `container/Makefile`, `container/scripts/_load-env.sh`, `container/scripts/container.sh`, `container/scripts/build.sh`, `container-host/deploy/deploy_environment.sh`, `container-host/tests/test_path_resolution.sh`.
  * **Current → required:** The Makefile and direct runtime scripts repeat values already represented in `.env.example`. Make and direct commands must resolve the same values from one fallback source.
  * **Implementation:** Use the existing plain `KEY=value` deployment template as the single fallback source for shared settings. Preserve environment and command-line overrides over `deployment.env`, and `deployment.env` over fallback values. Keep `CONFIG_DIR`, `DATA_DIR`, and `CONTAINER_DATA_DIR` home-relative resolution consistent between Make and direct script calls. Do not execute or `eval` the deployment file.
  * **Constraints:** Preserve explicit values set by callers, the `ENV_FILE` override, and the current behavior when files are absent. Keep the deploy helper's public options and stored image settings unchanged.
  * **Validation:** `V-1`, `V-6`.

**Completion evidence:** All helper callers use the new filenames, and the expanded path/default regression test proves matching resolved settings across Make and direct loading for default, file, environment, and path-override cases.

### Area 2: Consolidate service and project commands

**Objective:** Use one dispatcher for service actions and one project command with explicit `adopt` and `move` actions.

**Affected code:** `container/scripts/container.sh`, `container/scripts/service.sh` (removed), `container/Makefile`, `container/scripts/adopt-project.sh` (removed), `container/scripts/move-project.sh` (removed), `container/scripts/project.sh` (`NEW`), `container/DEPLOYMENT.md`, `docs/AUTHORIZATION.md`, `container-host/tests/test_lifecycle.sh`, `container-host/tests/test_project_commands.sh` (`NEW`).

**Dependencies:** `T1.1` for helper references used by `move`.

**Tasks:**

* [x] `T2.1` **Change:** Add service-action dispatch to `container.sh` and route Make targets through it.
  * **Target:** `container/scripts/container.sh`, `container/scripts/service.sh`, `container/Makefile`, `container-host/tests/test_lifecycle.sh`, `container/DEPLOYMENT.md`.
  * **Current → required:** `service.sh` owns install, enable, disable, start, stop, restart, status, and logs. These actions must run as `container.sh service <action>` and the Make targets must use that path.
  * **Implementation:** Preserve the service name and unit-file defaults, systemd commands, help and error statuses, and `exec` behavior for log following. Remove `service.sh` after its actions and active references move. Dispatch service actions without invoking Podman or `podman-compose`.
  * **Constraints:** Preserve all current Make service target names and the unit's `container.sh up/down` lifecycle calls.
  * **Validation:** `V-2`, `V-4`, and `V-6`.
* [x] `T2.2` **Change:** Replace the adoption and movement scripts with `project.sh adopt|move`.
  * **Target:** `container/scripts/adopt-project.sh`, `container/scripts/move-project.sh`, `container/scripts/project.sh` (`NEW`), `docs/AUTHORIZATION.md`, `container-host/tests/test_project_commands.sh` (`NEW`).
  * **Current → required:** Adoption and movement are separate scripts with distinct inputs and safeguards. One script must dispatch the two named actions without weakening either behavior.
  * **Implementation:** Share project path/locator and authorization helpers where behavior is common. Keep adoption's required owner, owner-only initial role, dry-run, manifest import, and post-import checks. Keep movement's source/target preflight, locator and grant checks, dry-run, confirmation, rollback after authorization failure, post-move verification, and restart notice. Update the documented movement command to `project.sh move`.
  * **Constraints:** Do not apply move-only filesystem validation to adoption or change authorization policy. Keep `/` and `:` locator handling as currently supported.
  * **Validation:** `V-3`, `V-4`, and `V-6`.

**Completion evidence:** Make service targets and direct service calls use the consolidated dispatcher, and project-command tests prove both actions retain their distinct success, failure, dry-run, and rollback behavior.

### Area 3: Remove stale runtime paths and align release contents

**Objective:** Keep the runtime bundle free of replaced entry points and host-only checks, with all active references and trusted file inventories aligned.

**Affected code:** `container/scripts/get-install.sh` → `container-host/deploy/get-install.sh` (`NEW`); `container-host/README.md`; `container/DEPLOYMENT.md`; `container-host/deploy/manage_container_release.sh`; `container-host/verify/verify_container_release.sh`; `container-host/tests/test_release_bundle_contents.sh`; `container-host/tests/test_required_files_contract.sh`; `container-host/tests/test_release_manager.sh`.

**Dependencies:** Areas 1 and 2.

**Tasks:**

* [x] `T3.1` **Change:** Move the documented host prerequisite check out of the runtime bundle.
  * **Target:** `container/scripts/get-install.sh` → `container-host/deploy/get-install.sh` (`NEW`); `container/DEPLOYMENT.md`; `container-host/README.md`; `container-host/tests/test_release_bundle_contents.sh`.
  * **Current → required:** The host prerequisite check is under `container/scripts/` and is documented for operators. Preserve its check behavior but keep it in the source-only host-tools tree.
  * **Implementation:** Relocate the script without changing its checks, update the operator instructions to name the source-only path and context, and list it with host deployment tools. Update the bundle test to require the relocated path and assert the old runtime path is absent.
  * **Constraints:** Do not remove the check or present it as an installed `~/container` command.
  * **Validation:** `V-4`, `V-6`, and `V-7`.
* [x] `T3.2` **Change:** Synchronize the release contract, bundle inventory, and active command references.
  * **Target:** `container-host/deploy/manage_container_release.sh`, `container-host/verify/verify_container_release.sh`, `container-host/tests/test_release_bundle_contents.sh`, `container-host/tests/test_required_files_contract.sh`, `container-host/tests/test_release_manager.sh`, `container/DEPLOYMENT.md`, `docs/AUTHORIZATION.md`, and active source references in `container/` and `container-host/`.
  * **Current → required:** The trusted required-file lists and bundle tests name old helper/service files and do not require `project.sh`. Active docs and scripts mention paths that will be renamed or removed.
  * **Implementation:** Require `_load-env.sh`, `_env-config.sh`, and `project.sh`; remove requirements for `service.sh`, `adopt-project.sh`, and `move-project.sh`; ensure the verifier and manager lists remain identical. Sweep active docs, scripts, and workflow references. Keep historical proposal references unchanged.
  * **Constraints:** Do not change release selection, checksums, archive safety, installation, activation, or rollback.
  * **Validation:** `V-4`, `V-5`, and `V-7`.

**Completion evidence:** The bundle tests and trusted required-file contract agree on the runtime files, no active reference points to a retired runtime path, and the host prerequisite check is available only from `container-host/`.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` | `T1.1`, `T1.2`, `T2.1`, `T2.2` | `V-1`, `V-2`, `V-3`, `V-4`, `V-6` | Separate renamed helpers, consistent defaults, one service dispatcher, and one project entry point pass the regression checks. |
| `PH3-AC-2` | `T1.1`, `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-4`, `V-6`, `V-7` | Retired runtime paths are absent, host-only checks are outside the bundle, and active references resolve. |
| `PH3-AC-3` | `T2.1`, `T2.2`, `T3.2` | `V-2`, `V-3`, `V-5` | Service and project behavior, including release-manager rollback, remains covered and unchanged. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Defaults and path resolution: `container-host/tests/test_path_resolution.sh` | `bash container-host/tests/test_path_resolution.sh` | `PH3-AC-1` | Make and direct helper resolution agree for defaults, deployment-file values, environment overrides, `ENV_FILE`, and relative/absolute paths. | Pass; extend assertions for the renamed helper and shared settings. |
| `V-2` | Container and service dispatch: `container-host/tests/test_lifecycle.sh` | `bash container-host/tests/test_lifecycle.sh` | `PH3-AC-1`, `PH3-AC-3` | Container lifecycle and Make callers still pass; service actions reach mocked systemd commands through the single dispatcher without invoking Podman. | Pass for current container actions; service-dispatch cases are not yet covered. |
| `V-3` | Project commands: `container-host/tests/test_project_commands.sh` (`NEW`) | `bash container-host/tests/test_project_commands.sh` | `PH3-AC-1`, `PH3-AC-3` | Temporary project directories and a sibling authorization stub verify adoption, movement, invalid inputs, dry-runs, confirmation, authorization failure rollback, and unchanged grant counts. No real container or authorization store is used. | Not run: test file does not exist yet. |
| `V-4` | Release bundle and required-file contract | `bash container-host/tests/test_release_bundle_contents.sh` and `bash container-host/tests/test_required_files_contract.sh` | `PH3-AC-1`, `PH3-AC-2` | Runtime bundle inventory includes the new helper and project paths, excludes replaced service/project scripts and host prerequisite check, and matches both trusted file lists. | Pass for the current 20-file contract. |
| `V-5` | Release manager selection and rollback: `container-host/tests/test_release_manager.sh` | `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.bareRepository GIT_CONFIG_VALUE_0=all bash container-host/tests/test_release_manager.sh` | `PH3-AC-3` | Install, activate, refusal, and rollback cases pass without changing release lifecycle behavior. | Pass with the one-command Git setting recorded above. |
| `V-6` | Shell syntax and error-severity lint for changed shell scripts | `find container/scripts container-host/deploy container-host/verify container-host/tests -type f -name '*.sh' -exec bash -n {} +`; then `shellcheck --severity=error container/scripts/*.sh container-host/deploy/*.sh container-host/verify/verify_container_release.sh container-host/tests/*.sh` | `PH3-AC-1`, `PH3-AC-2` | All scripts parse and ShellCheck reports no error-severity diagnostics. Review default-severity output only for new warnings in changed files; do not expand scope to existing warnings. | Error-severity ShellCheck passes. Default-severity ShellCheck has pre-existing warnings. |
| `V-7` | Active reference sweep | Search `container/`, `container-host/`, active documentation, and `.github/workflows/` for the old helper, service, project, and prerequisite-check paths; inspect each match. | `PH3-AC-2` | No active command or operator instruction invokes a retired path. Historical proposal/task-plan references and explicit negative assertions in tests are allowed. | Not run for Phase 3 paths. |

## Validation Results

Executed 2026-10-11 on branch `container-setup-simplifications` against the Phase 3 worktree.

| ID | Result | Evidence |
| --- | --- | --- |
| `V-1` | Pass | `bash container-host/tests/test_path_resolution.sh` — the loader and the Makefile agree on `CONFIG_DIR`, `DATA_DIR`, `CONTAINER_DATA_DIR`, and the shared settings (`CONTAINER_NAME`, `IMAGE_NAME`, `HOST_PORT`, `COMPOSE_PROJECT_NAME`, `GIT_REPO`, `GIT_REF`) for defaults, `deployment.env`, the environment, `ENV_FILE`, and path overrides, with the defaults coming from the bundled template. |
| `V-2` | Pass | `bash container-host/tests/test_lifecycle.sh` — container lifecycle and Make callers are unchanged; service actions reach the mocked `systemctl` through `container.sh service <action>` without invoking Podman. |
| `V-3` | Pass | `bash container-host/tests/test_project_commands.sh` — adoption, movement, invalid inputs, dry-runs, confirmation, and authorization-failure rollback with unchanged grant counts, using a stubbed authorization CLI. |
| `V-4` | Pass | `bash container-host/tests/test_release_bundle_contents.sh`; `bash container-host/tests/test_required_files_contract.sh`; `bash container-host/verify/verify_container_release.sh archive` — 20 required files, retired paths absent, both trusted lists identical, and `container/scripts/get-install.sh` outside the bundle. |
| `V-5` | Pass | `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.bareRepository GIT_CONFIG_VALUE_0=all bash container-host/tests/test_release_manager.sh` — install, activate, refusal, and rollback cases unchanged. |
| `V-6` | Pass | `bash -n` on all changed scripts and `shellcheck --severity=error` report no failures. Default-severity ShellCheck shows only the pre-existing classes (`SC1091` on sourced helpers, `SC2015` on the retained `A && B || C` verification lines); no new diagnostic class was introduced. |
| `V-7` | Pass | Active sweep of `container/`, `container-host/`, `.github/workflows/`, and active documentation found no retired path outside explicit negative test assertions. |

Extra checks: `make -n` succeeded for the lifecycle, setup, build, maintenance, and service targets; `make -n service-status` prints `./scripts/container.sh service status`, and the loader exports the shared settings from deployment.env or the bundled template.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Shared defaults and helper paths | `container/.env.example`, `container/Makefile`, `container/scripts/_load-env.sh` (`NEW`), `container/scripts/_env-config.sh` (`NEW`), and direct callers | `T1.1`, `T1.2` | V-1 and V-6 pass; old helper paths have no active callers. |
| Service dispatcher | `container/scripts/container.sh`, `container/Makefile`; remove `container/scripts/service.sh` | `T2.1` | V-2 passes for Make and direct service actions. |
| Project command | `container/scripts/project.sh` (`NEW`); remove `container/scripts/adopt-project.sh` and `container/scripts/move-project.sh` | `T2.2` | V-3 passes for both actions and failure safeguards. |
| Host prerequisite checker | `container-host/deploy/get-install.sh` (`NEW`); remove `container/scripts/get-install.sh` | `T3.1` | V-4 proves it is outside the runtime bundle; V-7 confirms the documented path. |
| Release contract and documentation | `container-host/deploy/manage_container_release.sh`, `container-host/verify/verify_container_release.sh`, `container-host/README.md`, `container/DEPLOYMENT.md`, `docs/AUTHORIZATION.md` | `T1.1`, `T2.1`, `T2.2`, `T3.1`, `T3.2` | V-4, V-5, and V-7 pass. |
| Regression coverage | `container-host/tests/test_path_resolution.sh`, `container-host/tests/test_lifecycle.sh`, `container-host/tests/test_release_bundle_contents.sh`, `container-host/tests/test_required_files_contract.sh`, `container-host/tests/test_project_commands.sh` (`NEW`) | `T1.1`–`T3.2` | V-1 through V-7 pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Unify configuration helper names and defaults | Done | None | Helper rename and shared defaults landed; V-1 and V-6 pass. |
| Area 2: Consolidate service and project commands | Done | Area 1 | Service dispatch and `project.sh` landed; V-2 and V-3 pass. |
| Area 3: Remove stale runtime paths and align release contents | Done | Areas 1–2 | Host prerequisite check moved; both trusted file lists updated; V-4, V-5, and V-7 pass. |

## Definition Of Done

- [x] `PH3-AC-1`, `PH3-AC-2`, and `PH3-AC-3` each have implementation and validation evidence.
- [x] All tasks and deliverables are complete; removed runtime entry points have no active callers.
- [x] Helper responsibility, override precedence, project safeguards, service behavior, and release rollback behavior remain intact.
- [x] Validation checks `V-1` through `V-7` pass, with baseline-only ShellCheck warnings recorded rather than broadened into this phase.
- [x] Active documentation and workflow references use valid paths; historical proposal references remain unchanged.
