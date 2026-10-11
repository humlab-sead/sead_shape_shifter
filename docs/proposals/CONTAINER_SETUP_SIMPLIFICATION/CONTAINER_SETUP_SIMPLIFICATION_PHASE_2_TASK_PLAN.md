# Container Setup Simplification — Phase 2 Task Plan

## Phase Summary

**Phase:** Phase 2 — Separate Release Contents And Trusted Validation
**Goal:** Exclude host tools from release archives and validate releases without executing candidate-supplied code.
**Readiness:** Validated
**Dependencies:** Phase 1 removed the ecosystem operational checks and kept application authorization tests ([Phase 1 task plan](./CONTAINER_SETUP_SIMPLIFICATION_PHASE_1_TASK_PLAN.md)). No operations owner or tooling decision is required.

**Sources**

- [Container Setup Simplification proposal](./CONTAINER_SETUP_SIMPLIFICATION.md)
- [Container Setup Simplification phase plan](./CONTAINER_SETUP_SIMPLIFICATION_PHASE_PLAN.md)
- [SEAD Runtime Verification Handoff](./OPERATIONS_VERIFICATION_HANDOFF.md) (Phase 1 deliverable; unchanged here)

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`): Release archives contain only deployment-user runtime contents; host provisioning and ecosystem runtime checks are outside the archive.
- `PH2-AC-2` (from `P-AC-2`): The release workflow checks source and archive policy; the host manager validates downloaded archives with trusted code and never runs a candidate-supplied verifier.
- `PH2-AC-3` (from `P-AC-6`): Host provisioning uses `deploy_environment.sh`; `deploy_all_environments.sh` is removed.
- `PH2-AC-4` (from `P-AC-8`): Release selection, checksum, archive-safety, service, and rollback behavior remain intact.

**Phase-plan validation milestones covered:** `VM-3`, `VM-4`, `VM-5`, `VM-6`.

**Fixed decisions carried from the phase plan**

- A source-only host-tools location outside `container/` is chosen: **`container-host/`**. Anything under it is outside the `git archive HEAD:container` inputs, so it cannot enter a release archive.
- Release selection, tag/version policy, checksum and archive-safety checks, and the install/activate/rollback contract are preserved.
- Operations tooling is not implemented; the runtime bundle is narrowed, not replaced.

## Repository Findings

**Repository basis:** Branch `container-setup-simplifications`, commit `a0c46fed`, planning date 2026-10-11. The worktree already contains the uncommitted Phase 1 changes (deleted operational verify scripts, updated `container/scripts/verify/README.md`, `docs/OPERATIONS.md`, `container/tests/test_verify_inventory.sh`) plus untracked phase-plan and handoff documents. Those were considered and are outside this task plan.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `.github/workflows/container-release.yml` (`Build release archive from tracked content`) | The archive is `git archive --format=tar.gz --prefix=container/ HEAD:container`, so **every** tracked file under `container/` ships, including `scripts/deploy/`, `scripts/verify/`, and `tests/`. | The archive narrows only by removing files from `container/`; no new archive command is needed. |
| `container/scripts/deploy/` (8 tracked files) | Holds the host release manager, environment provisioning, host installers, the NGINX template, and the dev sync tool. All are administrator/host tools. | Relocate to `container-host/deploy/`; the whole directory is host-side. |
| `container/scripts/deploy/deploy_single_environment.sh` | Configures one deployment user; runs `setup.sh`, writes application image settings to `~/config/deployment.env`, and optionally runs `make build`/`make up`. | Rename to `deploy_environment.sh`; it stays a host tool (run as root from a checkout). |
| `container/scripts/deploy/deploy_all_environments.sh` | Iterates `USER:PORT` pairs and calls `deploy_single_environment.sh`; reads `DEPLOY_ENVIRONMENTS`. | Remove it; no active caller exists (see reference sweep below). |
| `container/scripts/deploy/manage_container_release.sh::run_bundle_archive_check`, `::bundle_verifier_path` | `install_release` extracts the candidate archive and executes `scripts/verify/verify_container_release.sh` from **inside that candidate**; `validate_installed` re-tars the installed bundle and runs the same candidate script. | Replace with a trusted required-file check held by the manager; delete both functions. |
| `container/scripts/deploy/install_nginx_reverse_proxy.sh` | Sources `. "$SCRIPT_DIR/../load-env.sh"` (the runtime helper in `container/scripts/`). | After relocation, source `"$SCRIPT_DIR/../../container/scripts/load-env.sh"`. |
| `container/scripts/deploy/bootstrap-authentication-and-authorization.sh` | Derives `CONFIG_DIR` from `$SCRIPT_DIR/../..` (`CHECKOUT_DIR`), which equals `~/config` only while it lives in `~/container`; always reads `CONFIG_DIR/authorization.env`. | Replace the checkout-derived default with an explicit `CONFIG_DIR` requirement; remove `CHECKOUT_DIR`. Documented calls already pass `CONFIG_DIR`. |
| `container/scripts/deploy/sync-to-deploy::g_container_dir` | `$g_script_dir/../..` is the `container/` bundle and is what `rsync` sends. | Repoint to `"$g_script_dir/../../container"`. |
| `container/scripts/verify/` (post-Phase 1) | Holds `verify_container_release.sh` and `README.md`; `REQUIRED_FILES` has 21 entries and includes `scripts/verify/verify_container_release.sh`. | Relocate both files; drop the verifier entry (20 entries); add a forbidden-path contract. |
| `container/tests/` (4 tracked suites) | Development tests, not runtime files, but they ship in the archive. `test_verify_inventory.sh` asserts the contents of `container/scripts/verify/`. | Relocate to `container-host/tests/`; rewrite the inventory test as a bundle-contents test. |
| `container/tests/test_lifecycle.sh::g_container_dir`, `container/tests/test_path_resolution.sh::g_container_dir` | `"$g_test_dir/.."` is the `container/` bundle, used only for `cp -a "$g_container_dir/." "$g_release/"`. | After relocation, use `"$g_test_dir/../../container"`. One line each. |
| `container/tests/test_release_manager.sh::g_manager` | `"$g_container_dir/scripts/deploy/manage_container_release.sh"`. | Repoint to the relocated manager. |
| Active references to the moved paths | `.github/workflows/container-release.yml` (4 step invocations), `container/DEPLOYMENT.md` (many), `container/README.md` (2), `container/.env.example` (1), `container/resources/authorization.env.example` (1), `container/scripts/get-install.sh` (1), `scripts/README.md` (4), `docs/OPERATIONS.md` (1). | Update every active reference in the same change. |
| `secrets/` | Local, untracked finding ledger and reports that also name `container/scripts/deploy/...`. | Out of scope; untracked. |
| `docs/proposals/SECURITY_HARDENING_FOLLOWUP/` | An active proposal whose plan also relocates `bootstrap-authentication-and-authorization.sh` and `install_nginx_reverse_proxy.sh`, to the installed `/usr/local/sbin/shape-shifter/`. | Phase 2 changes the **source** location only; record the overlap as a coordination risk. |
| `container/scripts/get-install.sh` | Inspects host prerequisites only (Podman, `podman-compose`, lingering, rootless namespace); writes nothing; has no active caller or doc reference. | Keep in place this phase; disposition belongs to Phase 3's dead-script sweep. Recorded as a risk. |
| `container/resources/` | Includes `authorization.env.example`, which `container/DEPLOYMENT.md` instructs the deployment user to install from `~/container/resources/`. | Keep `resources/` in the runtime bundle. |

### Baseline Results

- `bash container/tests/test_verify_inventory.sh` — **Pass** (5 checks).
- `bash container/tests/test_path_resolution.sh` — **Pass**.
- `bash container/tests/test_lifecycle.sh` — **Pass**.
- `bash container/tests/test_release_manager.sh` — **Pass**.
- `bash container/scripts/verify/verify_container_release.sh dir` (worktree, `container/VERSION` = `0.1.0`, tag `container-v0.1.0` exists) — **Fail** at the tag-policy check (`tag container-v0.1.0 already exists; the version must be new`). The 21-entry required-file check passes before it. This failure is the expected state for an unchanged version and is not caused by Phase 2.
- `git archive --format=tar.gz --prefix=container/ HEAD:container` then `bash container/scripts/verify/verify_container_release.sh archive <file>` — **Pass**.
- `shellcheck -S warning container/scripts/deploy/*.sh container/scripts/*.sh container/scripts/verify/*.sh` — **Fail (4 pre-existing findings)**: 1 in `container/scripts/authorization.sh`, 2 in `container/scripts/build.sh`, 1 in `container/scripts/service.sh`. The `deploy/` and `verify/` scripts are clean at warning level.

Do not fix the unrelated shellcheck findings or the version/tag state as part of this phase.

## Scope

**In scope**

- Choose the source-only location `container-host/` and move host provisioning, installer, and release-management tools into it.
- Move the release-policy checker and its README out of `container/`.
- Point the release workflow at the relocated checker and add a forbidden-contract check so archives cannot carry host or verification tooling.
- Replace the host release manager's candidate-supplied verifier with a trusted required-file check inside the manager.
- Rename `deploy_single_environment.sh` to `deploy_environment.sh` and remove `deploy_all_environments.sh`.
- Move the shell regression suites to `container-host/tests/`, rewrite the verification-inventory test as a bundle-contents test, and add a required-file contract test and a no-candidate-code test.
- Update every active reference to the moved or removed paths.

**Out of scope**

- Renaming `load-env.sh`/`env-config.sh` to `_load-env.sh`/`_env-config.sh`, consolidating deployment defaults, `container.sh service <action>`, and `project.sh adopt|move` — those are Phase 3.
- Changing the release tag scheme, publication trigger, required-content policy rules, `GIT_REF`, or `IMAGE_NAME`.
- Editing the `container/Containerfile`, `podman-compose.yml`, `service/shape-shifter.service`, or `container/resources/` contents.
- Removing `container/scripts/get-install.sh` (Phase 3 dead-script sweep).
- Implementing, selecting, or scheduling SEAD operations checks.
- Moving `container/README.md` or `container/DEPLOYMENT.md` out of the bundle.

**Affected components:** `container/` tree contents, a new source-only `container-host/` tree, the `container-release` workflow, the host release manager, four shell regression suites, and the active documentation that names those paths.

## Work Breakdown

### Area 1: Relocate Host Tooling And Release Checks To `container-host/`

**Objective:** `container/` holds only deployment-user runtime contents, and every host tool and release check lives in `container-host/`, which archive construction cannot reach.

**Affected code:** `container/scripts/deploy/**`, `container/scripts/verify/**`, `container/tests/**`, `container-host/**` (`NEW`).

**Dependencies:** None.

**Tasks**

- [x] `T1.1` **Change:** Move the host provisioning, installer, and release-management tools to `container-host/deploy/`.
  - **Target:** `NEW` `container-host/deploy/manage_container_release.sh`; `NEW` `container-host/deploy/deploy_environment.sh` (renamed from `container/scripts/deploy/deploy_single_environment.sh`); `NEW` `container-host/deploy/install_systemd_service.sh`; `NEW` `container-host/deploy/install_nginx_reverse_proxy.sh`; `NEW` `container-host/deploy/bootstrap-authentication-and-authorization.sh`; `NEW` `container-host/deploy/nginx-shape-shifter.conf.template`; `NEW` `container-host/deploy/sync-to-deploy`.
  - **Current → required:** These administrator/host tools are tracked under `container/` and therefore ship in every release archive. Move them to `container-host/deploy/`, which is outside the `git archive HEAD:container` inputs.
  - **Implementation:** Use `git mv` for each file to preserve history and file modes (all are executable except `nginx-shape-shifter.conf.template`). Do not change script contents in this task.
  - **Constraints:** Move only `container/scripts/deploy/`. Do not move `container/scripts/*.sh` (`container.sh`, `load-env.sh`, `env-config.sh`, `setup.sh`, `build.sh`, `backup.sh`, `healthcheck.sh`, `service.sh`, `authorization.sh`, `adopt-project.sh`, `move-project.sh`, `get-install.sh`), `container/service/`, `container/resources/`, `container/README.md`, or `container/DEPLOYMENT.md`.
  - **Validation:** `V-1`, `V-3`, `V-8`.
- [x] `T1.2` **Change:** Remove the all-environments command.
  - **Target:** `container/scripts/deploy/deploy_all_environments.sh` (delete).
  - **Current → required:** It iterates `USER:PORT` pairs from arguments or `DEPLOY_ENVIRONMENTS` and calls `deploy_single_environment.sh`. The consolidated design configures each environment explicitly, so delete it and do not add a replacement.
  - **Implementation:** Delete the file. Confirmed consumers of `DEPLOY_ENVIRONMENTS` are this script and its documentation in `container/DEPLOYMENT.md` and `container/.env.example` (both updated in Area 5); `container/scripts/setup.sh` and `container/scripts/load-env.sh` do not read it.
  - **Constraints:** Do not add a group/multi-environment command or an all-environments Makefile target.
  - **Validation:** `V-1`, `V-8`.
- [x] `T1.3` **Change:** Fix the path resolution the relocation breaks in three moved tools.
  - **Target:** `container-host/deploy/sync-to-deploy::g_container_dir`; `container-host/deploy/install_nginx_reverse_proxy.sh` (sourced helper path); `container-host/deploy/bootstrap-authentication-and-authorization.sh::CHECKOUT_DIR`, `::CONFIG_DIR`.
  - **Current → required:** `sync-to-deploy` must resolve the runtime bundle as `"$g_script_dir/../../container"`; `install_nginx_reverse_proxy.sh` must source `"$SCRIPT_DIR/../../container/scripts/load-env.sh"`; `bootstrap-authentication-and-authorization.sh` must stop deriving `CONFIG_DIR` from the checkout and instead require it via `CONFIG_DIR="${CONFIG_DIR:?CONFIG_DIR must name the deployment user's configuration directory}"`, dropping `CHECKOUT_DIR`.
  - **Implementation:** Minimal edits only. Keep `sync-to-deploy`'s `refuse_managed_target` logic, `install_nginx_reverse_proxy.sh`'s upstream-port resolution (`PORT`/`HOST_PORT` then `8012`) and template rendering, and the bootstrap's validate-before-write ordering and `/etc/nginx` writes unchanged. Update the bootstrap failure text to point at `container-host/README.md` and `container/DEPLOYMENT.md`.
  - **Constraints:** Preserve `install_nginx_reverse_proxy.sh`'s documented `CONFIG_DIR`/`sudo -u` behavior; it still reads `HOST_PORT` from `CONFIG_DIR/deployment.env`. Leave `bootstrap-authentication-and-authorization.sh::DEPLOY_DIR="/data/$DEPLOY_USER/container"` unchanged.
  - **Validation:** `V-1`, `V-3`, `V-8`; manual: `bash container-host/deploy/install_nginx_reverse_proxy.sh --help` succeeds, and `bash container-host/deploy/bootstrap-authentication-and-authorization.sh` without `CONFIG_DIR` fails with the new message.
- [x] `T1.4` **Change:** Move the release-policy checks out of `container/`.
  - **Target:** `NEW` `container-host/verify/verify_container_release.sh` (from `container/scripts/verify/verify_container_release.sh`); `NEW` `container-host/verify/README.md` (from `container/scripts/verify/README.md`); remove the now-empty `container/scripts/verify/` directory.
  - **Current → required:** Both files sit inside `container/` and ship in the archive. Move them to the source-only tree used by the release workflow.
  - **Implementation:** `git mv` both files; confirm `container/scripts/verify/` is empty and removed. Content changes belong to Area 2.
  - **Constraints:** Do not change release-policy semantics in this task.
  - **Validation:** `V-1`, `V-3`, `V-6`.
- [x] `T1.5` **Change:** Document the source-only tree.
  - **Target:** `NEW` `container-host/README.md`.
  - **Current → required:** No document explains why host tooling and release checks are outside `container/`.
  - **Implementation:** State that `container-host/` holds host-side tools, release-policy checks, and their regression tests; that it is outside the `git archive HEAD:container` inputs and never ships in a release archive; that its scripts run from a repository checkout; and that it is not an operations toolkit. Link `container/DEPLOYMENT.md` and `container-host/verify/README.md`.
  - **Constraints:** Do not restate the operations requirements from the Phase 1 handoff; link it instead.
  - **Validation:** `V-8`.

**Completion evidence:** `container/` has no `scripts/deploy/`, `scripts/verify/`, or `tests/` entries; all moved tools and checks run from `container-host/`; no tracked file under `container-host/` can be reached by `git archive HEAD:container`.

### Area 2: Move Release-Policy Checks To The Workflow

**Objective:** The workflow validates source and archive policy from the source-only tree, and archives cannot contain host or verification tooling.

**Affected code:** `container-host/verify/verify_container_release.sh`; `.github/workflows/container-release.yml`.

**Dependencies:** Area 1 (`T1.4`).

**Tasks**

- [x] `T2.1` **Change:** Narrow the required-file contract and reject host/verification tooling in both verification modes.
  - **Target:** `container-host/verify/verify_container_release.sh::REQUIRED_FILES`; `NEW` `FORBIDDEN_PREFIXES`; `check_dir`; `check_archive`.
  - **Current → required:** `REQUIRED_FILES` has 21 entries including `scripts/verify/verify_container_release.sh`; nothing rejects host tooling. Drop the verifier entry (20 entries) and add `FORBIDDEN_PREFIXES=(scripts/deploy scripts/verify tests)` rejected in both `dir` and `archive` modes.
  - **Implementation:** Write both lists with one entry per line and the closing `)` on its own line, so the contract test in Area 4 can compare them reliably. Add a `check_forbidden` helper that fails when any forbidden prefix exists under the `container/` root (`-e`/directory presence in `dir` mode; a matching `container/<prefix>/` archive entry in `archive` mode). Run the required-file and forbidden checks **before** the tag and ancestry checks so they always execute. Keep the existing single-`container/`-root, `.git`-absence, and `X.Y.Z` checks.
  - **Constraints:** Keep the `dir`/`archive` CLI, `--container-dir`, `--git-dir`, `--require-main-merged`, `--resume-at-head`, exit codes, and the read-only guarantee. Do not add a second dispatch layer.
  - **Validation:** `V-3`, `V-4`, `V-6`, `V-7`.
- [x] `T2.2` **Change:** Correct the default container directory and usage text.
  - **Target:** `container-host/verify/verify_container_release.sh::main` (`dir` default) and the file header.
  - **Current → required:** `container_dir` defaults to `dirname(dirname(script_dir))`, which was `container/` from `container/scripts/verify/` but is the repository root from `container-host/verify/`. Default to `<repo>/container`.
  - **Implementation:** `container_dir="$(dirname "$(dirname "$(script_dir)")")/container"`. Update the header path examples and the `sed -n '3,26p'` usage range so `--help` output stays accurate.
  - **Constraints:** Keep the `--container-dir` and `--git-dir` overrides working.
  - **Validation:** `V-6`, `V-7`.
- [x] `T2.3` **Change:** Point the workflow at the relocated checker.
  - **Target:** `.github/workflows/container-release.yml` — the `Verify release inputs` and `Verify release archive` steps in the `validate` and `publish` jobs (4 invocations).
  - **Current → required:** Each step runs `bash container/scripts/verify/verify_container_release.sh ...`. Replace with `bash container-host/verify/verify_container_release.sh ...`.
  - **Implementation:** Change only the four `run:` commands. Keep `git archive --format=tar.gz --prefix=container/ HEAD:container` unchanged; narrowing the archive comes from removing files from `container/`.
  - **Constraints:** Keep the job conditions, permissions, tag-resume logic, checksum asset, and asset-completeness checks unchanged.
  - **Validation:** `V-6`, `V-8`.

**Completion evidence:** The workflow validates `container/` and the built archive using the source-only checker, and a `container/` tree containing `scripts/deploy/`, `scripts/verify/`, or `tests/` fails the check.

### Area 3: Validate Releases Without Candidate-Supplied Code

**Objective:** The host release manager validates a downloaded archive with its own trusted code and never executes a file from the candidate bundle.

**Affected code:** `container-host/deploy/manage_container_release.sh`.

**Dependencies:** Area 2 (`T2.1` defines the required-file contract).

**Tasks**

- [x] `T3.1` **Change:** Replace the bundle verifier with a trusted required-content check.
  - **Target:** `container-host/deploy/manage_container_release.sh::bundle_verifier_path` (delete); `::run_bundle_archive_check` (delete); `NEW` `g_required_files`; `::install_release`; `::validate_installed`.
  - **Current → required:** `install_release` runs the candidate's `scripts/verify/verify_container_release.sh` after extraction, and `validate_installed` re-tars the installed bundle and runs the same candidate script. Both must instead check a trusted list held by the manager.
  - **Implementation:** Add `readonly g_required_files=(...)` with the same 20 entries and identical formatting as `T2.1` (one per line, closing `)` on its own line). In `install_release`, after the existing checksum, `check_archive_safety`, VERSION/tag match, extraction, and single-`container/`-root checks, loop over `g_required_files` and `die` when `$extract_dir/container/<entry>` is missing. In `validate_installed`, drop the `mktemp`/`tar`/verifier block and instead loop over `g_required_files` checking `$bundle/<entry>`, keeping the existing `TAG`, `COMMIT`, and `VERSION`-matches-tag assertions. Replace the failure message that named `scripts/verify/verify_container_release.sh`.
  - **Constraints:** Preserve checksum verification, `check_archive_safety`, the VERSION/tag match, the single-root check, staging cleanup (`install_cleanup_on_exit`), `apply_install_permissions`, and the install/activate/rollback selector contract. The manager must not read, execute, or source any candidate-supplied file.
  - **Validation:** `V-2`, `V-4`, `V-6`.
- [x] `T3.2` **Change:** State the trusted-validation rule in the manager's own documentation.
  - **Target:** `container-host/deploy/manage_container_release.sh` header comment and `usage()`.
  - **Current → required:** The header does not say the manager validates with its own code. Document that `install` verifies the checksum, rejects unsafe paths, checks the expected archive root and version, and checks a required-file list using the manager's own code, and never executes anything from the candidate archive.
  - **Constraints:** Do not change CLI usage text for commands or arguments.
  - **Validation:** `V-8`.

**Completion evidence:** A valid archive installs and an archive missing a required file is refused, with no candidate-supplied file executed in either case.

### Area 4: Relocate And Extend The Shell Regression Tests

**Objective:** The shell suites live in the source-only tree, pass, and cover the bundle boundary, the shared required-file contract, and the no-candidate-code rule.

**Affected code:** `container/tests/**`; `container-host/tests/**` (`NEW`).

**Dependencies:** Areas 1–3.

**Tasks**

- [x] `T4.1` **Change:** Move the shell regression suites to `container-host/tests/`.
  - **Target:** `NEW` `container-host/tests/test_lifecycle.sh`; `NEW` `container-host/tests/test_path_resolution.sh`; `NEW` `container-host/tests/test_release_manager.sh`; remove the now-empty `container/tests/` directory.
  - **Current → required:** The suites are development artifacts tracked inside `container/` and therefore shipped in the archive.
  - **Implementation:** `git mv` each file, preserving executable mode. In `test_lifecycle.sh` and `test_path_resolution.sh`, change `g_container_dir="$(CDPATH='' cd -- "$g_test_dir/.." && pwd)"` to resolve the runtime bundle: `"$g_test_dir/../../container"`. In `test_release_manager.sh`, set `g_repo_root="$(CDPATH='' cd -- "$g_test_dir/../.." && pwd)"`, `g_container_dir="$g_repo_root/container"`, and `g_manager="$g_repo_root/container-host/deploy/manage_container_release.sh"`. Update each `Usage:` line.
  - **Constraints:** Keep every existing assertion; change only paths, the `Usage:` lines, and the `test_verify_inventory.sh` replacement from `T4.2`.
  - **Validation:** `V-1`, `V-2`, `V-5`.
- [x] `T4.2` **Change:** Rewrite the verification-inventory test as a release-bundle contents test.
  - **Target:** `container/tests/test_verify_inventory.sh` → `NEW` `container-host/tests/test_release_bundle_contents.sh`.
  - **Current → required:** The old test asserts that `container/scripts/verify/` holds only `README.md` and `verify_container_release.sh`. Those files moved, so assert the new boundary instead.
  - **Implementation:** Assert (a) `container/scripts/deploy`, `container/scripts/verify`, and `container/tests` do not exist; (b) `container/` holds the runtime files `VERSION`, `README.md`, `DEPLOYMENT.md`, `Makefile`, `podman-compose.yml`, `Containerfile`, `.env.example`, `.containerignore`, `scripts/container.sh`, `scripts/load-env.sh`, `scripts/env-config.sh`, `scripts/setup.sh`, `scripts/build.sh`, `scripts/backup.sh`, `scripts/healthcheck.sh`, `scripts/service.sh`, `service/shape-shifter.service`, `resources/backend.env.example`, `resources/.pgpass.example`, `resources/authorization.env.example`; (c) `container-host/deploy/` holds `manage_container_release.sh`, `deploy_environment.sh`, `install_systemd_service.sh`, `install_nginx_reverse_proxy.sh`, `bootstrap-authentication-and-authorization.sh`, `nginx-shape-shifter.conf.template`, `sync-to-deploy`, and no `deploy_all_environments.sh` or `deploy_single_environment.sh`; (d) `container-host/verify/` holds `verify_container_release.sh` and `README.md`, and the README names the checker; (e) the runtime helper referenced by `container-host/deploy/install_nginx_reverse_proxy.sh` (`<repo>/container/scripts/load-env.sh`) exists; (f) `container/` contains no `verify_container_release.sh`, `deploy_all_environments.sh`, or `deploy_single_environment.sh` anywhere.
  - **Constraints:** Read-only; no network; no root. Distinct positive and negative assertions, and a non-zero exit with a count when any check fails.
  - **Validation:** `V-3`.
- [x] `T4.3` **Change:** Add the required-file contract test.
  - **Target:** `NEW` `container-host/tests/test_required_files_contract.sh`.
  - **Current → required:** The workflow verifier and the host manager each hold a required-file list; nothing keeps them aligned.
  - **Implementation:** Extract the entries between `REQUIRED_FILES=(` and the following `)` from `container-host/verify/verify_container_release.sh`, and between `g_required_files=(` and the following `)` from `container-host/deploy/manage_container_release.sh`; assert both are non-empty and identical with `diff`; assert neither lists `scripts/verify/verify_container_release.sh`, `scripts/deploy`, or `tests`.
  - **Constraints:** Read-only; print both lists on mismatch; fail with a non-zero exit.
  - **Validation:** `V-4`.
- [x] `T4.4` **Change:** Cover the no-candidate-code rule and trusted required-file check in the manager suite.
  - **Target:** `container-host/tests/test_release_manager.sh`.
  - **Current → required:** The suite proves checksum, traversal, version, and refusal behavior but never proves the manager ignores candidate-supplied code.
  - **Implementation:** Extend the existing `make_release` fixture so one release bundle additionally contains a `scripts/verify/verify_container_release.sh` that would `touch` a sentinel path if executed, and one containing a `scripts/deploy/` trap. Install them and assert (a) install succeeds when the 20 required files are present, (b) neither sentinel exists, proving no candidate file was executed, and (c) a bundle missing a `g_required_files` entry (for example `Makefile`) is refused with nothing installed and staging cleaned up. Reuse `expect_ok`, `expect_fail`, `assert_no_path`, and `assert_no_staging`.
  - **Constraints:** Keep the suite root-free, network-free, and runnable from a temporary directory; keep all existing assertions.
  - **Validation:** `V-2`.

**Completion evidence:** All four suites run from `container-host/tests/` and pass, including the bundle-contents, contract, and no-candidate-code cases.

### Area 5: Update Active Documentation And Cross-References

**Objective:** Every active reference resolves to the authoritative new path, and no active text names a removed command.

**Affected code:** `container/DEPLOYMENT.md`; `container/README.md`; `container/.env.example`; `container/resources/authorization.env.example`; `container/scripts/get-install.sh`; `scripts/README.md`; `docs/OPERATIONS.md`.

**Dependencies:** Areas 1–4.

**Tasks**

- [x] `T5.1` **Change:** Update `container/DEPLOYMENT.md`.
  - **Target:** `container/DEPLOYMENT.md` — the install/verify paragraph, the single-environment section, the multiple-environments section, the NGINX section, the authorization-inputs section, the systemd section, and the `sync-to-deploy` paragraph.
  - **Current → required:** It names `container/scripts/deploy/manage_container_release.sh`, the bundle's `scripts/verify/verify_container_release.sh` check, `scripts/deploy/deploy_single_environment.sh`, `scripts/deploy/deploy_all_environments.sh` plus `DEPLOY_ENVIRONMENTS`, `scripts/deploy/install_nginx_reverse_proxy.sh`, `scripts/deploy/nginx-shape-shifter.conf.template`, `scripts/deploy/bootstrap-authentication-and-authorization.sh`, `scripts/deploy/install_systemd_service.sh`, and `container/scripts/deploy/sync-to-deploy`. Replace each with its `container-host/deploy/` path, its new name, or its removal.
  - **Implementation:** Rewrite the install sentence to describe the manager's trusted checks (checksum, safe paths, expected root and version, required files) with no candidate verifier. Replace the multiple-environments section with guidance to run `container-host/deploy/deploy_environment.sh` once per environment and to give each environment its own user and port. State that host tools run from a repository checkout and are not read from the selected release. Keep the deployment-user sections and the authorization-input instructions intact, except for the bootstrap path.
  - **Constraints:** Keep the quick-navigation links and anchors valid; do not describe operations checks as shipped.
  - **Validation:** `V-8`.
- [x] `T5.2` **Change:** Update `container/README.md`.
  - **Target:** `container/README.md` — the NGINX template reference and the host-manager install command in the Container Releases section.
  - **Current → required:** `scripts/deploy/nginx-shape-shifter.conf.template` and `container/scripts/deploy/manage_container_release.sh` must point at `container-host/deploy/`.
  - **Implementation:** Update both paths and add one sentence stating that the release archive carries only deployment-user runtime contents, while host tooling, release-policy checks, and their tests live in `container-host/` and are never shipped.
  - **Constraints:** Keep the existing release-stream explanation and the `gh release` inspection commands.
  - **Validation:** `V-8`.
- [x] `T5.3` **Change:** Remove the retired multi-environment template block from `container/.env.example`.
  - **Target:** `container/.env.example` — the "Multi-environment deploys" block documenting `DEPLOY_ENVIRONMENTS`.
  - **Current → required:** The block documents a variable consumed only by the removed `deploy_all_environments.sh`; `container/scripts/setup.sh` does not read it.
  - **Implementation:** Delete the block and its commented example; leave the rest of the file unchanged.
  - **Constraints:** Do not reformat or reorder unrelated variables.
  - **Validation:** `V-8`.
- [x] `T5.4` **Change:** Update the remaining active references.
  - **Target:** `container/resources/authorization.env.example` (bootstrap path comment); `container/scripts/get-install.sh` (deploy-helper path comment); `scripts/README.md` (Deployment Scripts section heading, `deploy_single_environment.sh` subsection, `install_nginx_reverse_proxy.sh` and `install_systemd_service.sh` examples); `docs/OPERATIONS.md` (NGINX template path).
  - **Current → required:** Each names `container/scripts/deploy/...` or `deploy_single_environment.sh`. Point each at the corresponding `container-host/deploy/` path and name.
  - **Implementation:** Text-only edits; keep the surrounding instructions and examples otherwise unchanged.
  - **Constraints:** Do not edit `docs/proposals/**` or the untracked `secrets/**` references.
  - **Validation:** `V-8`.

**Completion evidence:** A repository-wide sweep of active sources, workflows, and documentation for the old paths and names returns no stale reference.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (from `P-AC-1`) | `T1.1`, `T1.2`, `T1.4`, `T2.1`, `T4.2`, `T5.3` | `V-3`, `V-6`, `V-7`, `V-8` | `container/` contains no `scripts/deploy/`, `scripts/verify/`, or `tests/`; the verifier requires the 20 runtime files and rejects those prefixes; the built archive passes archive-mode verification. |
| `PH2-AC-2` (from `P-AC-2`) | `T2.1`, `T2.3`, `T3.1`, `T4.3`, `T4.4` | `V-2`, `V-4`, `V-6` | The workflow runs the source-only checker; the manager validates with its own required-file list; the contract test proves both lists are identical; the manager never executes a candidate file. |
| `PH2-AC-3` (from `P-AC-6`) | `T1.1`, `T1.2`, `T1.3`, `T4.2`, `T5.1`, `T5.2`, `T5.3`, `T5.4` | `V-1`, `V-3`, `V-8` | Host provisioning uses `container-host/deploy/deploy_environment.sh`; `deploy_all_environments.sh` is deleted with no active caller; all active references resolve. |
| `PH2-AC-4` (from `P-AC-8`) | `T3.1`, `T4.1`, `T4.4` | `V-2`, `V-5` | The manager suite still passes selection, checksum, traversal, version, and rollback cases; the lifecycle and path-resolution suites pass unchanged. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Shell syntax of every changed or moved script | `bash -n` on `container-host/deploy/*.sh`, `container-host/deploy/sync-to-deploy`, `container-host/verify/verify_container_release.sh`, `container-host/tests/*.sh`, `container/scripts/get-install.sh` | `PH2-AC-3` | Exit status 0 for each file | Not run: files are not relocated yet. Current `container/scripts/deploy/*.sh` parse cleanly (used by the passing suites). |
| `V-2` | Host release manager behavior and trusted validation | `bash container-host/tests/test_release_manager.sh` | `PH2-AC-2`, `PH2-AC-4` | Pass, including valid install, missing-required-file refusal, and the case proving no candidate-supplied file is executed | **Pass** at the current path (`container/tests/test_release_manager.sh`) |
| `V-3` | Release bundle contents and source-only tree inventory | `bash container-host/tests/test_release_bundle_contents.sh` | `PH2-AC-1`, `PH2-AC-3` | Pass: `container/` has no host/verification/tests paths, holds the 20 runtime files, and `container-host/{deploy,verify}/` hold the expected inventory | Not run: test is new (`container/tests/test_verify_inventory.sh` passes today with the pre-move assertions) |
| `V-4` | Required-file contract alignment | `bash container-host/tests/test_required_files_contract.sh` | `PH2-AC-2` | Pass: the verifier and manager lists are identical, non-empty, and exclude the verifier entry | Not run: test is new |
| `V-5` | Lifecycle and path-resolution regression | `bash container-host/tests/test_lifecycle.sh`; `bash container-host/tests/test_path_resolution.sh` | `PH2-AC-4` | Pass with all existing assertions unchanged | **Pass** at the current path |
| `V-6` | Archive built the way the workflow builds it | `git add -A`; `version="$(tr -d '[:space:]' < container/VERSION)"`; `git archive --format=tar.gz --prefix=container/ "$(git write-tree):container" -o "/tmp/container-v${version}.tar.gz"`; `bash container-host/verify/verify_container_release.sh archive "/tmp/container-v${version}.tar.gz"` | `PH2-AC-1`, `PH2-AC-2` | Pass: the archive unpacks to one `container/` root, holds all 20 required files, and contains no `scripts/deploy/`, `scripts/verify/`, or `tests/` | **Pass** with the current contract (21 files) built from `HEAD:container` |
| `V-7` | Source-tree policy check | `bash container-host/verify/verify_container_release.sh dir --container-dir container` | `PH2-AC-1` | The 20-file required check and the forbidden-prefix check pass; the run still fails only on the pre-existing `container-v0.1.0 already exists` tag-policy line for the unchanged version | **Fail** at the current path on the same tag-policy line, after `all 21 required deployment files are present` |
| `V-8` | Active-reference sweep | `grep -rnE 'scripts/deploy/|scripts/verify/|deploy_single_environment|deploy_all_environments|container/tests/' container/ container-host/ scripts/README.md docs/OPERATIONS.md .github/workflows/` (exclude `docs/proposals/**`, `secrets/**`, `graphify-out/**`); additionally `shellcheck -S warning container-host/deploy/*.sh container-host/verify/*.sh` | `PH2-AC-1`, `PH2-AC-3` | No stale active reference remains; shellcheck reports no finding in the moved host tools or verifier | **Fail (expected)**: active sources, workflows, and docs point at the old paths today. shellcheck baseline: 4 pre-existing findings, none in `deploy/` or `verify/` |

Run `V-1`, `V-2`, `V-3`, `V-4`, and `V-5` after every area that touches them; run `V-6`, `V-7`, and `V-8` before declaring the phase complete.

### Validation Results

Executed on branch `container-setup-simplifications` at commit `a0c46fed`, with the Phase 1 worktree changes preserved and the Phase 2 changes applied on top.

| ID | Result | Evidence |
| --- | --- | --- |
| `V-1` | Pass | `bash -n` exits 0 for every relocated script, the four suites, and `container/scripts/get-install.sh` |
| `V-2` | Pass | `container-host/tests/test_release_manager.sh` passes every case, including the two candidate-code bundles: `Installed container-v0.21.0` with no sentinel created, and no sentinel for the `scripts/deploy/` trap |
| `V-3` | Pass | `container-host/tests/test_release_bundle_contents.sh` passes all 22 checks |
| `V-4` | Pass | `container-host/tests/test_required_files_contract.sh` confirms both lists hold 20 identical entries and exclude the verifier entry |
| `V-5` | Pass | `container-host/tests/test_lifecycle.sh` and `container-host/tests/test_path_resolution.sh` pass with all existing assertions unchanged |
| `V-6` | Pass | Archive built from `$(git write-tree):container` verifies in `archive` mode: one `container/` root, 20 required files, no forbidden prefix |
| `V-7` | Fail (expected) | `dir --container-dir container` passes the 20-file and forbidden-prefix checks, then fails only on the pre-existing `tag container-v0.1.0 already exists` line |
| `V-8` | Pass, with noted guards | No stale active reference remains outside the test suites. The only sweep hits are deliberate absence guards in `container-host/tests/` (for example `container/tests`, `deploy_all_environments.sh`, `deploy_single_environment.sh`). `shellcheck -S warning container-host/deploy/*.sh container-host/verify/*.sh` reports no finding; the four pre-existing findings in `container/scripts/{authorization,build,service}.sh` are unchanged |

Additional negative checks: a tree containing `container/tests/` fails both `dir` and `archive` verification with the forbidden-prefix message; `bash container-host/deploy/bootstrap-authentication-and-authorization.sh` without `CONFIG_DIR` fails with the new message; `bash container-host/deploy/install_nginx_reverse_proxy.sh --help` exits 0.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Relocated host tools | `container-host/deploy/manage_container_release.sh`, `deploy_environment.sh`, `install_systemd_service.sh`, `install_nginx_reverse_proxy.sh`, `bootstrap-authentication-and-authorization.sh`, `nginx-shape-shifter.conf.template`, `sync-to-deploy` | `T1.1`, `T1.3` | Files exist under `container-host/deploy/` with working relative paths (`V-1`, `V-3`) |
| Removed all-environments command | `container/scripts/deploy/deploy_all_environments.sh` (deleted) | `T1.2` | The file is absent and has no active caller (`V-8`) |
| Relocated release-policy checks | `container-host/verify/verify_container_release.sh`, `container-host/verify/README.md` | `T1.4`, `T2.1`, `T2.2` | Files exist at the new path; the 20-file and forbidden checks run (`V-3`, `V-6`, `V-7`) |
| Source-only tree overview | `container-host/README.md` (`NEW`) | `T1.5` | Documented purpose, no shipping in archives (`V-8`) |
| Trusted host-manager validation | `container-host/deploy/manage_container_release.sh::g_required_files`, `::install_release`, `::validate_installed` | `T3.1`, `T3.2` | No candidate-supplied file is executed; missing required file refused (`V-2`) |
| Workflow repointed | `.github/workflows/container-release.yml` | `T2.3` | All four steps invoke `container-host/verify/verify_container_release.sh` (`V-8`) |
| Relocated shell suites | `container-host/tests/test_lifecycle.sh`, `test_path_resolution.sh`, `test_release_manager.sh` | `T4.1`, `T4.4` | Suites pass from the new path (`V-2`, `V-5`) |
| Bundle-contents test | `container-host/tests/test_release_bundle_contents.sh` (`NEW`, replaces `container/tests/test_verify_inventory.sh`) | `T4.2` | Passes (`V-3`) |
| Required-file contract test | `container-host/tests/test_required_files_contract.sh` (`NEW`) | `T4.3` | Passes (`V-4`) |
| Updated documentation and references | `container/DEPLOYMENT.md`, `container/README.md`, `container/.env.example`, `container/resources/authorization.env.example`, `container/scripts/get-install.sh`, `scripts/README.md`, `docs/OPERATIONS.md` | `T5.1`–`T5.4` | Reference sweep is clean (`V-8`) |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Relocate host tooling and release checks to `container-host/` | Done | None | Includes the `deploy_environment.sh` rename, the `deploy_all_environments.sh` removal, and the three relocation path fixes |
| Area 2: Move release-policy checks to the workflow | Done | Area 1 | Adds the forbidden-prefix contract and fixes the default container dir |
| Area 3: Validate releases without candidate-supplied code | Done | Area 2 | Adds `g_required_files`; deletes `bundle_verifier_path` and `run_bundle_archive_check` |
| Area 4: Relocate and extend the shell regression tests | Done | Areas 1–3 | Four suites move; two tests are new |
| Area 5: Update active documentation and cross-references | Done | Areas 1–4 | Nine documentation/config files |

## Definition Of Done

- [x] `T1.1`–`T1.5`, `T2.1`–`T2.3`, `T3.1`–`T3.2`, `T4.1`–`T4.4`, and `T5.1`–`T5.4` are complete.
- [x] `PH2-AC-1`, `PH2-AC-2`, `PH2-AC-3`, and `PH2-AC-4` each have implementation and validation evidence.
- [x] `container/` contains no `scripts/deploy/`, `scripts/verify/`, or `tests/` content, and the built archive passes archive-mode verification (`V-3`, `V-6`).
- [x] The host manager executes no file from a candidate archive and refuses a bundle missing a required file (`V-2`).
- [x] The verifier and manager required-file lists are proven identical (`V-4`).
- [x] `deploy_environment.sh` exists as the single-environment command and `deploy_all_environments.sh` has no active caller (`V-8`).
- [x] Release selection, checksum, archive-safety, lifecycle, and rollback behavior are regression-tested and unchanged (`V-2`, `V-5`).
- [x] All four shell suites pass from `container-host/tests/`, and `bash -n` passes on every changed script (`V-1`, `V-2`, `V-3`, `V-4`, `V-5`).
- [x] Every active reference resolves; only the pre-existing tag-policy failure and the four pre-existing shellcheck findings remain (`V-7`, `V-8`).
- [x] Deviations, the cross-proposal relocation overlap, and the `get-install.sh` disposition are recorded.
- [x] No unresolved question affects implementation, correctness, or validation.

## Implementation Notes

- The plan's literal bootstrap requirement `${CONFIG_DIR:?CONFIG_DIR must name the deployment user's configuration directory}` does not parse: bash treats the apostrophe inside `${...:?}` as an opening single quote and fails. The message now reads "CONFIG_DIR must name the configuration directory for the deployment user" and still points at `container-host/README.md` and `container/DEPLOYMENT.md`.
- `T2.1` added two header lines to the verifier, so the `T2.2` usage range moved from `3,26` to `3,33`; the range now prints the complete usage block through the `Exit status` line.
- `T4.4` reuses the existing incomplete-archive case for the missing-required-file refusal: `assert_no_staging` was added to the `container-v0.14.0` case rather than duplicating it. The two candidate-code bundles (`container-v0.21.0` verifier trap, `container-v0.22.0` deploy trap) are new.
- `V-6` staged only `container/` and `container-host/` before `git write-tree`, instead of `git add -A`, so unrelated worktree changes (for example `graphify-out/`, `uv.lock`) were not added to the index.
- `container/tests/test_verify_inventory.sh` carried local Phase 1 modifications, so it was removed with `git rm -f` when replaced by `container-host/tests/test_release_bundle_contents.sh`.
- The `container/scripts/deploy/`, `container/scripts/verify/`, and `container/tests/` directories are now empty of tracked files and were removed from the working tree.

## Risks And Open Questions

- **Cross-proposal overlap.** `docs/proposals/SECURITY_HARDENING_FOLLOWUP/` plans to relocate `bootstrap-authentication-and-authorization.sh` and `install_nginx_reverse_proxy.sh` to the installed `/usr/local/sbin/shape-shifter/`. Phase 2 changes the source location only. Reconcile the two before either is implemented if both proceed; the installed-location decision stays with that proposal.
- **Relocation changes helper resolution.** `install_nginx_reverse_proxy.sh` and `bootstrap-authentication-and-authorization.sh` lose their sibling `load-env.sh` and checkout-derived `CONFIG_DIR`. `T1.3` fixes both, and `V-1`/`V-8` plus the manual checks cover them, but neither has an automated end-to-end test (both need root and a host). Treat the manual checks as required, not optional.
- **Duplicated required-file contract.** The list now lives in two trusted places (workflow verifier and host manager). `V-4` enforces equality, and any future runtime file must be added to both lists and to the bundle-contents test in the same change.
- **`container/scripts/get-install.sh` stays in the bundle.** It only inspects host prerequisites and has no active caller, so it is not "host provisioning," but a reviewer may see it as host tooling that `PH2-AC-1` excludes. Recommended resolution: Phase 3's dead-script sweep dispositions or removes it; if removed earlier, move it with the host tools.
- **No automation runs the shell suites.** No workflow invokes `container-host/tests/*.sh`, so the phase relies on manual runs. Adding a CI job is outside this proposal's scope; note it as follow-up work rather than expanding Phase 2.
- **`container/DEPLOYMENT.md` stays in the runtime bundle** while documenting host tools that live outside it. Accepted because the deployment user needs it from `~/container`, `container/README.md` links it, and the administrator reads it from the repository. If reviewers prefer a host-only operator guide, that split belongs to a later phase.
- **Open question:** should the release workflow also assert the required-file contract against the installed manager copy? Recommendation: no. The manager is installed from a reviewed copy and validated by its own tests; adding a cross-check would require a new artifact and is not part of `PH2-AC-2`.

## Implementation Handoff Note

Implement these areas in order. Stop and report evidence if the verified repository state conflicts with this plan — for example, if a moved path already has a different caller, if `container/scripts/deploy/` contains a file not listed here, or if `container/VERSION` or the `container-v*` tags changed. Do not invent a replacement design or broaden scope into Phase 3.
