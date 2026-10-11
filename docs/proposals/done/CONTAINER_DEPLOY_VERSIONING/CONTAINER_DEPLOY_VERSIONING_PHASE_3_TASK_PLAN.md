# Phase 3 Task Plan: Integrate Lifecycle and Preserve Verification

## Phase Summary

- **Phase:** [Phase 3: Integrate Lifecycle and Preserve Verification](./CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md)
- **Goal:** Run every lifecycle command from the selected container release through Make and systemd without changing current command behavior, and give every verification script a documented disposition before any old entry point is removed.
- **Readiness:** **Validated.** The phase plan's stated precondition — the Phase 2 selection contract plus a caller review — is satisfied. Phase 2 is implemented and validated (see the [Phase 2 task plan](./CONTAINER_DEPLOY_VERSIONING_PHASE_2_TASK_PLAN.md)), and the caller review is recorded in Repository Findings.
- **Source proposal:** [CONTAINER_DEPLOY_VERSIONING.md](./CONTAINER_DEPLOY_VERSIONING.md)
- **Phase plan:** [CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md](./CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md)
- **Source criteria:** `PH3-AC-1` (from `P-AC-7`) and `PH3-AC-2` (from `P-AC-8`).
- **Dependency:** Phase 2's validated selected-release path. The lifecycle dispatcher and its Make and systemd callers already run through `~/container`; this phase proves and preserves that, and settles the disposition of each verification script.
- **Waiver:** The live systemd user-service check (`V-3`) is waived by user decision (2026-10-11) and is not run. Unit validity and path resolution are covered statically by `V-2`, and dispatcher actions by `V-1`; see [Validation And Testing](#validation-and-testing) and [Risks And Open Questions](#risks-and-open-questions).

### Acceptance Criteria

- [x] `PH3-AC-1` (from `P-AC-7`): Make and systemd lifecycle behavior works through the selected release; missing or unknown commands fail clearly and log following remains interruptible. (Verified by `V-1`, `V-2`, `V-6`, and `V-7`; `V-3` is waived by user decision.)
- [x] `PH3-AC-2` (from `P-AC-8`): Every verification script has a justified disposition; active release checks and evidence remain available and state-changing checks retain explicit safeguards. (Verified by `V-4`, `V-5`, `V-6`, and `V-7`.)

## Repository Findings

**Repository basis:** Branch `container-deploy-versioning`, commit `6cfaf910`, planning date 2026-10-11. The worktree contains the uncommitted Phase 2 changes to `container/` described in the [Phase 2 task plan](./CONTAINER_DEPLOY_VERSIONING_PHASE_2_TASK_PLAN.md), including the untracked `container/tests/` directory. Those changes were read as the current state and left unchanged.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `container/scripts/container.sh`, `container/Makefile`, `container/service/shape-shifter.service` | The dispatcher (`up`, `down`, `restart`, `logs`, `status`, `help`) is committed in `7e17837a`. Make lifecycle targets invoke `scripts/container.sh`, and the unit runs `%h/container/scripts/container.sh up\|down`. `logs` uses `exec`, and an empty or unknown action prints usage and exits 64. | Preserve this contract and add regression coverage. The phase plan's "in-progress dispatcher edits" premise is stale: the only uncommitted `container.sh` change is a Phase 2 diagnostic-wording edit. |
| `container/scripts/verify/verify_container_release.sh::REQUIRED_FILES` | Lists `container.sh`, `load-env.sh`, `env-config.sh`, `setup.sh`, `build.sh`, `backup.sh`, `healthcheck.sh`, the unit, and three resources. It omits `scripts/service.sh` and `scripts/verify/verify_container_release.sh`. | `make service-*` needs `service.sh`, and the Phase 2 installer needs the release verifier inside the bundle. A release missing either currently passes validation. |
| `git archive HEAD:container \| tar -t \| grep -c scripts/verify/` | The published archive already contains `scripts/verify/` (19 entries). | Adding those files to `REQUIRED_FILES` changes no current archive; it only makes an omission fail. |
| `container/scripts/verify/README.md` | Documents 12 of the 14 verification files. `verify_container_release.sh` and `verify_readonly_role.sql` are absent, and no row names callers or a disposition. | Add a disposition table with purpose, callers, safeguard, and decision. |
| `.github/workflows/container-release.yml`; `container/scripts/deploy/manage_container_release.sh::run_bundle_archive_check` | The publication workflow and the Phase 2 installer both invoke `verify_container_release.sh`. | It is an active release check: retain, never remove. |
| `docs/proposals/RELEASE_CYCLE_EVIDENCE_AND_LOCKING/README.md` | Active proposal. Constraints to preserve include "Keep `container/scripts/verify/` scripts read-only except for the deliberate rollback exercise". It plans a run-record envelope that supplements the existing checks. | Retain every verification script; defer consolidating the two orchestrators to that proposal. |
| `container/scripts/verify/rollback_exercise.sh` (confirmation gate before line 224); `run_deployment_verification.sh` (`--authenticated`, `--rollback`); `complete_test_deployment_verification.sh` (`--authenticated`, `--grant-access`, `--rollback`, `--yes`) | Every state-changing or interactive check is explicitly opt-in and does not run by default. | Preserve these safeguards unchanged; the inventory test asserts they remain. |
| `docs/OPERATIONS.md::Release, Verification, And Rollback` | Describes rollback by switching `GIT_REF` and `IMAGE_NAME` and rebuilding. It does not mention the container release manager. `::Deployment Entry Points` still says the checkout "holds neither" configuration nor data. | Update to the install/activate/rollback contract and the selected-release wording. |
| `container/scripts/get-install.sh` | Still downloads the repository archive and extracts `*/container/*` into the current directory, which is `~/container` — now a root-owned selection symlink. It also writes `GIT_REPO`, `GIT_REF`, and `IMAGE_NAME`. | The extraction conflicts with the selection contract. No active caller exists: references appear only under `docs/proposals/done/`. |
| `systemd-analyze verify container/service/shape-shifter.service` | Exits 0 and warns `Command /data/roger/container/scripts/container.sh is not executable: No such file or directory`, because no selected release exists at the verifying user's home. | The unit syntax is valid and `%h` resolves to the home root. Use a rendered copy with a temporary home root for a warning-free check. |
| `HOME=<tmp> make -C <symlinked ~/container> -n up` | Emits `DATA_DIR="<tmp>/container-data" ... ./scripts/container.sh up`. | Make operates through the symlinked selection and resolves paths from `$HOME`, as Phase 2 specified. |
| `grep` across tracked Markdown, shell, YAML, and Python | No active reference to `up.sh`, `down.sh`, `logs.sh`, or `status.sh` remains outside `docs/proposals/done/`. | The consolidated names need no further caller coordination; record the migration instead. |
| `.venv/bin/graphify query "container/scripts/container.sh lifecycle actions"` | `graph.json` holds 601 `container/scripts` references, but the query returned frontend package and generic script nodes rather than the container shell scripts. | Graphify did not surface this phase's targets; findings come from source, configuration, and the commands above. |

## Scope

**In scope**

- Preserve and regression-test the dispatcher, Make, and systemd lifecycle contract operating through `~/container`.
- Complete the release required-file list for the lifecycle and release-check dependencies.
- Align the systemd installer diagnostic with the selected-release flow.
- Document a disposition for every verification script, including callers and safeguards, and enforce the inventory with a test.
- Update `docs/OPERATIONS.md` and `container/DEPLOYMENT.md` for selected-release lifecycle, verification, rollback, and migration from older deployment copies.
- Give the pre-release install path in `get-install.sh` a disposition that no longer writes the deployment tree into `~/container`.

**Out of scope**

- Consolidating the two deployment-verification orchestrators or building a run-record envelope; `RELEASE_CYCLE_EVIDENCE_AND_LOCKING` owns that.
- Changing `container.sh` action semantics, adding actions, or adding a `make verify` target.
- Changing the release manager, the installation layout, or the selection contract established in Phase 2.
- Adding, removing, or redefining any verification check.
- Changing authorization policy, route classification, or deployment layout.

**Affected areas:** the container lifecycle dispatcher and its callers, the systemd installer, the release-verification required-file contract, the verification-script documentation, `get-install.sh`, `docs/OPERATIONS.md`, `container/DEPLOYMENT.md`, and a new shell test directory under `container/tests/`.

## Work Breakdown

### Area 1: Lifecycle parity through the selected release

**Objective:** Make and systemd lifecycle commands demonstrably operate on the selected release with the current behavior preserved, and make a release that lacks a lifecycle or release-check dependency fail validation.

**Affected code:** `container/tests/test_lifecycle.sh` (`NEW`); `container/scripts/verify/verify_container_release.sh::REQUIRED_FILES`; `container/scripts/deploy/install_systemd_service.sh`; `container/scripts/container.sh`; `container/Makefile`.

**Dependencies:** None.

**Tasks:**

* [x] `T3.1` **Change:** Add a dispatcher and Make lifecycle parity test. *(Implemented 2026-10-11: `container/tests/test_lifecycle.sh` (`NEW`); `V-1` passed with 40 assertions.)*
  * **Target:** `container/tests/test_lifecycle.sh` (`NEW`).
  * **Current → required:** The dispatcher contract is implemented and committed but has no automated coverage. Add a test that exercises it through a symlinked `~/container`.
  * **Implementation:** Build a temporary home with a physical release directory (`scripts/container.sh`, `Makefile`, `podman-compose.yml`, `Containerfile`, `service/shape-shifter.service`, `.env.example`, `VERSION`), point `~/container` at it, and seed `CONFIG_DIR/backend.env` plus the seven data subdirectories. Put `podman` and `podman-compose` stubs on `PATH` that record their argv to a file and exit 0 so `check_deployment` passes. Assert for each action: `up` runs `podman-compose -f podman-compose.yml -p <project> up -d --no-build`; `down` runs `down`; `restart` runs `down` then `up`; `status` queries `podman ps` and `podman inspect`; `logs` runs `logs -f`. Assert that an empty action and an unknown action both print usage and exit 64. Assert `logs` replaces the dispatcher process, so a SIGINT sent to the process group reaches the stub. Repeat the read-only and failing cases through `make -C "$HOME/container"`. Record checksums of the release tree before and after and assert they are unchanged.
  * **Constraints:** Use stubs only; never invoke real Podman, build an image, or touch a real deployment. Do not change `container.sh` behavior; if the test exposes a defect, fix only what the documented contract requires. Keep the test independent of Phase 2's `container/tests/` files.
  * **Validation:** `V-1`; `V-7`.

* [x] `T3.2` **Change:** Complete the release required-file list for lifecycle and release-check dependencies. *(Implemented 2026-10-11: `scripts/service.sh` and `scripts/verify/verify_container_release.sh` added to `REQUIRED_FILES` (now 21); `V-4` passed.)*
  * **Target:** `container/scripts/verify/verify_container_release.sh::REQUIRED_FILES`.
  * **Current → required:** The list omits `scripts/service.sh`, which every `make service-*` target needs, and `scripts/verify/verify_container_release.sh`, which Phase 2 installation and activation invoke inside the bundle. A tree or archive missing either currently passes validation.
  * **Implementation:** Add `scripts/service.sh` and `scripts/verify/verify_container_release.sh` to `REQUIRED_FILES`. Keep the existing entries and order, so the tree check and the archive check both assert them.
  * **Constraints:** Do not change the version, tag, or ancestry checks. The published archive already contains both paths, so no current release regresses. The check lives inside the archive, so the change takes effect for the next container release.
  * **Validation:** `V-4`.

* [x] `T3.3` **Change:** Align the systemd installer diagnostic with the selected release. *(Implemented 2026-10-11: `install_systemd_service.sh` requires a selected release and names the release manager; `V-2` and `V-6` passed.)*
  * **Target:** `container/scripts/deploy/install_systemd_service.sh`.
  * **Current → required:** The script warns `no container/ directory found for $USER; run the deploy helper first` and then runs `make service-install`, which fails obscurely when `~/container` is not a selected release.
  * **Implementation:** Require a complete selected release the way `deploy_single_environment.sh` does after Phase 2: refuse when `~/container` is not a symlink, or when it does not resolve to a directory containing `Makefile` and `VERSION`, and name the release manager commands (`shape-shifter-container-release install|activate`) in the failure message. Keep the existing root check, lingering, and `make service-install` behavior.
  * **Constraints:** Do not install or activate a release, and do not change the enable/start behavior.
  * **Validation:** `V-2`; `V-6`.

**Completion evidence:** The lifecycle parity test passes against stubs; the release verifier fails with a clear message when `scripts/service.sh` or `scripts/verify/verify_container_release.sh` is absent; `install_systemd_service.sh` states the selected-release requirement instead of failing inside `make`.

### Area 2: Verification-script dispositions and safeguard preservation

**Objective:** Every verification script has a documented, justified disposition with its callers and safeguards, and the inventory and safeguards are enforced by a test.

**Affected code:** `container/scripts/verify/README.md`; `container/tests/test_verify_inventory.sh` (`NEW`).

**Dependencies:** None.

**Tasks:**

* [x] `T3.4` **Change:** Document the disposition of every verification script. *(Implemented 2026-10-11: disposition table added to `container/scripts/verify/README.md`; `V-5` and `V-6` passed.)*
  * **Target:** `container/scripts/verify/README.md`.
  * **Current → required:** The README describes 12 of the 14 files, names no callers, and states no disposition, so `PH3-AC-2` cannot be assessed from one place.
  * **Implementation:** Replace the summary table with a disposition table carrying `Script`, `Purpose`, `Callers`, `Safeguard`, and `Disposition` columns. Cover all 14 tracked files plus `deployment-verification.options.yml.example` and `disposable-project/shapeshifter.yml`. Record `retain` for every file with its reason, including: `verify_container_release.sh` as the active release check invoked by `.github/workflows/container-release.yml` and by the Phase 2 installer; `verify_readonly_role.sql` as the SQL input of `verify_postgres_grants.sh`; `rollback_exercise.sh` with its confirmation gate; and `complete_test_deployment_verification.sh` with a note that consolidation with `run_deployment_verification.sh` is deferred to `RELEASE_CYCLE_EVIDENCE_AND_LOCKING`. Keep the existing run examples.
  * **Constraints:** Document only; do not add, remove, or change any check. Record the callers from `.github/workflows/`, `container/scripts/deploy/`, `docs/OPERATIONS.md`, and `run_deployment_verification.sh`, not from memory.
  * **Validation:** `V-5`; `V-6`.

* [x] `T3.5` **Change:** Add a verification inventory and safeguard test. *(Implemented 2026-10-11: `container/tests/test_verify_inventory.sh` (`NEW`); `V-5` passed with 29 assertions.)*
  * **Target:** `container/tests/test_verify_inventory.sh` (`NEW`).
  * **Current → required:** Nothing prevents a new verification script from being added undocumented, or a safeguard from being removed silently.
  * **Implementation:** For each tracked `container/scripts/verify/*.sh` and `*.sql` file name, assert the basename appears in `README.md` on a row that also contains one of `retain`, `consolidate`, `move`, or `retire`. Assert `rollback_exercise.sh` still reads a confirmation prompt and honours `--yes`, and that `run_deployment_verification.sh` and `complete_test_deployment_verification.sh` still declare `--authenticated` and `--rollback` as opt-in flags rather than defaults. Fail with the missing file name or safeguard so the report is actionable.
  * **Constraints:** Read files with `git ls-files` under `container/scripts/verify/`; do not execute any verification script. Keep the test read-only.
  * **Validation:** `V-5`; `V-7`.

**Completion evidence:** The inventory test passes on the documented set and fails when a script is added without a disposition row or when a safeguard is removed.

### Area 3: Old entry points, migration, and operator documentation

**Objective:** Operators can run lifecycle, verification, and rollback for a selected release from the runbook, and no pre-release entry point still writes the deployment tree into `~/container`.

**Affected code:** `docs/OPERATIONS.md`; `container/DEPLOYMENT.md`; `container/scripts/get-install.sh`; `container/README.md`.

**Dependencies:** Areas 1 and 2 for the tested commands the documentation names.

**Tasks:**

* [x] `T3.6` **Change:** Update `docs/OPERATIONS.md` for selected-release lifecycle, verification, and rollback. *(Implemented 2026-10-11: entry-point and rollback sections updated; `V-6` passed.)*
  * **Target:** `docs/OPERATIONS.md::Deployment Entry Points`, `docs/OPERATIONS.md::Release, Verification, And Rollback`.
  * **Current → required:** Rollback is described as setting `GIT_REF` and `IMAGE_NAME` to the last known-good release and rebuilding, which is superseded. `Deployment Entry Points` still describes the checkout as holding neither configuration nor data.
  * **Implementation:** Keep the first-start sequence and the verification subsections. State that lifecycle commands run from the selected release through `~/container`. Replace the rollback paragraph with the container release manager commands (`shape-shifter-container-release install`, `activate`, `status`, `rollback`) and note that the application image is rebuilt separately and is not changed by selecting a release. Correct the deployment-entry-point wording.
  * **Constraints:** Keep the runbook shape and the existing firewall and container-configuration check descriptions. Do not duplicate `container/DEPLOYMENT.md`; link to it.
  * **Validation:** `V-6`.

* [x] `T3.7` **Change:** Document the migration from pre-release deployment copies. *(Implemented 2026-10-11: migration subsection added to `container/DEPLOYMENT.md`; `V-6` passed.)*
  * **Target:** `container/DEPLOYMENT.md`.
  * **Current → required:** The document describes the selected-release flow but does not say what to do with an older copy that has `up.sh`, `down.sh`, `logs.sh`, and `status.sh`, a mutable `~/container`, or a unit that names a retired script.
  * **Implementation:** Add a short migration subsection: for an older copy, move the existing `~/container` directory aside, install and activate an exact release, reinstall the unit with `make service-install`, and use `make up`, `down`, `restart`, `logs`, and `status` through the selection. State that the four scripts no longer exist in a release and that `install_systemd_service.sh` now requires a selected release. Name the host prerequisite check from `T3.8`.
  * **Constraints:** Do not instruct deleting an existing `~/container` without review; keep the Phase 2 first-transition rule. Keep configuration and data outside the release.
  * **Validation:** `V-6`.

* [x] `T3.8` **Change:** Retire the pre-release install path in `get-install.sh`. *(Implemented 2026-10-11: `get-install.sh` is now a host prerequisite check; `V-6` and `V-7` passed.)*
  * **Target:** `container/scripts/get-install.sh`.
  * **Current → required:** The script downloads the repository archive for a branch and extracts `*/container/*` into the current directory, which is `~/container`; after Phase 2 that path is a root-owned selection symlink, so the extraction either fails or fights the selection contract. It also records application image settings from the extracted `.env.example`.
  * **Implementation:** Keep the host prerequisite checks (Podman, `podman-compose`, lingering, rootless user namespaces) and remove the archive download, the extraction, and the `container/`-dependent `deployment.env` recording. Update the header and usage so the script is a host prerequisite check, and keep its existing exit status on a failed prerequisite.
  * **Constraints:** No active caller exists (references appear only under `docs/proposals/done/`). `deploy_single_environment.sh` remains the supported path for application image settings, so removing that block here does not drop a capability. Do not add a download of the container tree.
  * **Validation:** `V-6`; `V-7`.

**Completion evidence:** `docs/OPERATIONS.md` and `container/DEPLOYMENT.md` describe the tested selected-release commands and the migration path, and no container script writes the deployment tree into `~/container`.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (`P-AC-7`) | `T3.1`, `T3.2`, `T3.3`, `T3.6`, `T3.7` | `V-1`, `V-2`, `V-3`, `V-6`, `V-7` | Make and the dispatcher run each lifecycle action through a symlinked `~/container`; the unit parses and its commands resolve relative to the home root; empty and unknown commands print usage and exit 64; `logs` replaces the dispatcher so the follow is interruptible; the release supplies `scripts/service.sh`. The live systemd start/stop check (`V-3`) is waived by user decision, so unit behavior is supported by static checks (`V-2`) and dispatcher coverage (`V-1`) only. |
| `PH3-AC-2` (`P-AC-8`) | `T3.2`, `T3.4`, `T3.5`, `T3.6`, `T3.8` | `V-4`, `V-5`, `V-6`, `V-7` | Every verification file appears in the disposition table with a caller and a disposition; `verify_container_release.sh` stays an active release check; `rollback_exercise.sh` and the orchestrator keep their opt-in safeguards; a release missing a required dependency fails validation. |

## Validation And Testing

`V-1` through `V-7` implement `VM-4` and `VM-5`. Planning baselines: `bash -n container/scripts/container.sh` passed; `HOME=<tmp> make -C <symlinked ~/container> -n up` passed and resolved `DATA_DIR` under `$HOME`; `systemd-analyze verify container/service/shape-shifter.service` exited 0 with a missing-command warning because no selected release exists at the verifying user's home; `REQUIRED_FILES` omits `scripts/service.sh` and `scripts/verify/verify_container_release.sh`; the archive already contains `scripts/verify/`; the verification README omits two files. The live systemd check (`V-3`) was **waived by user decision on 2026-10-11** and is recorded as not run, not as a pass.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Dispatcher and Make lifecycle parity through the selection | `bash container/tests/test_lifecycle.sh` (`NEW`). Temporary home, physical release directory, `~/container` symlink, seeded `backend.env` and data directories, and `podman`/`podman-compose` stubs that record argv. Cases: `up`, `down`, `restart`, `logs`, `status`, empty action, unknown action, SIGINT during `logs`, release tree unchanged, and the same cases through `make -C "$HOME/container"`. | `PH3-AC-1` | Each action maps to the documented compose invocation; empty and unknown actions print usage and exit 64; the SIGINT reaches the compose stub, proving the dispatcher was replaced; nothing is written into the release tree. | **Passed 2026-10-11:** 40 assertions, exit 0. |
| `V-2` | systemd unit integrity through the selection path | Copy `container/service/shape-shifter.service`, substitute `%h` with a temporary root containing an executable `container/scripts/container.sh` stub, and run `systemd-analyze verify <rendered unit>`. Assert no "not executable" or "not found" warning, and assert the unit contains `WorkingDirectory=%h/container`, `ExecStart=%h/container/scripts/container.sh up`, `ExecStop=%h/container/scripts/container.sh down`, and no `IMAGE_NAME`, `HOST_PORT`, `CONFIG_DIR`, or `DATA_DIR`. | `PH3-AC-1` | The unit parses and every path resolves under the home root without a warning. | **Passed 2026-10-11:** `systemd-analyze verify` exited 0 with no path or executability warning; the rendered unit resolved `WorkingDirectory`, `ExecStart`, and `ExecStop` under the rendered root and set no deployment value. |
| `V-3` | systemd live user-service lifecycle | On a host with a running systemd user manager and a selected release for the target user: `make service-install`, `make service-start`, `make service-status`, `make service-stop`, and `make service-logs`. Confirm `systemctl --user show -p ExecStart` resolves to the selected release's `scripts/container.sh`, that start and stop succeed, and that Ctrl-C ends log following. | `PH3-AC-1` | The unit starts and stops the container through the selected release, and log following is interruptible. | **Waived by user decision (2026-10-11); not run and not claimed as a pass.** The Phase 2 disposable container has no systemd, and this developer account is not a deployment user with a selected release. `V-2` covers unit validity and path resolution statically, and `V-1` covers every dispatcher action the unit invokes. |
| `V-4` | Release required-file coverage | Run `bash container/scripts/verify/verify_container_release.sh dir --container-dir <temp copy outside a git repository>` on a complete tree. Remove `scripts/service.sh` and expect failure naming it; restore; remove `scripts/verify/verify_container_release.sh` and expect failure naming it. Then build `git archive --format=tar.gz --prefix=container/ HEAD:container` and run `archive` mode. | `PH3-AC-2` | The complete tree and archive pass; each missing dependency fails the check with a message naming the file. | **Passed 2026-10-11:** the complete tree passed with 21 required files; removing either dependency failed with `required deployment file missing: container/<path>`; the archive check passed for version 0.1.0. |
| `V-5` | Verification inventory and safeguards | `bash container/tests/test_verify_inventory.sh` (`NEW`). | `PH3-AC-2` | Every tracked verification file appears in the README disposition table with a disposition; the rollback confirmation gate and the orchestrators' opt-in flags remain. | **Passed 2026-10-11:** 29 assertions, exit 0. A negative probe with an undocumented script name failed as intended. |
| `V-6` | Documentation and script consistency | Inspect the changed documents and the retired install path: `docs/OPERATIONS.md` names `shape-shifter-container-release install\|activate\|status\|rollback` and no longer instructs changing `GIT_REF` or `IMAGE_NAME` for a container rollback; `container/DEPLOYMENT.md` documents the older-copy migration and the host prerequisite check; `container/scripts/get-install.sh` contains no archive extraction (`tar -xz`) and no `deployment.env` write. | `PH3-AC-1`, `PH3-AC-2` | Documentation matches the implemented commands, and no container script writes the deployment tree into `~/container`. | **Passed 2026-10-11:** all four manager commands named in `docs/OPERATIONS.md`; the superseded rollback guidance is gone; the lifecycle-through-selection statement, the migration subsection, and the host prerequisite check are present; `get-install.sh` has no `tar -xz` and no `deployment.env` write. |
| `V-7` | Phase 2 contract regression and lint | `bash container/tests/test_path_resolution.sh`; `bash container/tests/test_release_manager.sh`; `bash container/tests/test_lifecycle.sh`; `bash container/tests/test_verify_inventory.sh`; `bash -n` and `shellcheck -S warning` on every changed shell file; `systemd-analyze verify container/service/shape-shifter.service`. | Existing behavior | Both Phase 2 suites still pass; no ShellCheck diagnostics beyond the recorded baseline. | **Passed 2026-10-11:** path resolution 27 and release manager 79 assertions passed; `bash -n` clean; ShellCheck reports only the two pre-existing `sync-to-deploy` SC1007 warnings and no others. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Lifecycle parity test | `container/tests/test_lifecycle.sh` (`NEW`) | `T3.1` | `V-1` passes, including the clear-failure and interruptible-log cases through a symlinked `~/container`. |
| Release required-file coverage | `container/scripts/verify/verify_container_release.sh::REQUIRED_FILES` | `T3.2` | `V-4` passes; a tree missing `scripts/service.sh` or `scripts/verify/verify_container_release.sh` fails validation. |
| Systemd installer diagnostic | `container/scripts/deploy/install_systemd_service.sh` | `T3.3` | The failure names the selected-release requirement instead of failing inside `make`. |
| Verification dispositions | `container/scripts/verify/README.md` | `T3.4` | Every verification file has a row with purpose, callers, safeguard, and disposition. |
| Verification inventory test | `container/tests/test_verify_inventory.sh` (`NEW`) | `T3.5` | `V-5` passes; an undocumented script or a removed safeguard fails the test. |
| Operator runbook update | `docs/OPERATIONS.md` | `T3.6` | `V-6` passes; the rollback and entry-point guidance matches the implemented commands. |
| Migration and lifecycle guidance | `container/DEPLOYMENT.md` | `T3.7` | `V-6` passes; an older copy has documented steps to move to a selected release. |
| Retired pre-release install path | `container/scripts/get-install.sh` | `T3.8` | `V-6` passes; the script performs prerequisite checks only and writes nothing into `~/container`. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Lifecycle parity through the selected release | Done | None | `V-1` (40 assertions) and `V-2` pass; `REQUIRED_FILES` now lists 21 files and `V-4` fails on either missing dependency. |
| Area 2: Verification-script dispositions and safeguard preservation | Done | None | `V-5` (29 assertions) passes; every tracked file has a disposition row and the safeguards are asserted unchanged. |
| Area 3: Old entry points, migration, and operator documentation | Done | Areas 1 and 2 | `V-6` passes; `get-install.sh` is a host prerequisite check and no container script writes the deployment tree into `~/container`. |

## Execution Record

Implementation date 2026-10-11, branch `container-deploy-versioning`, from commit `6cfaf910` plus the changes below. The uncommitted Phase 2 `container/` changes were read as the current state and preserved.

**Implemented deliverables:**

- `container/tests/test_lifecycle.sh` (`NEW`): dispatcher and Make parity test through a symlinked `~/container` with `podman` and `podman-compose` stubs (`T3.1`).
- `container/scripts/verify/verify_container_release.sh::REQUIRED_FILES`: added `scripts/service.sh` and `scripts/verify/verify_container_release.sh` (19 → 21 entries) (`T3.2`).
- `container/scripts/deploy/install_systemd_service.sh`: requires a selected release, refuses a real directory or unrelated symlink, and names the release manager in the failure (`T3.3`).
- `container/scripts/verify/README.md`: disposition table with `Script`, `Verifies`, `Callers`, `Safeguard`, and `Disposition` for all 14 tracked files plus `deployment-verification.options.yml.example` and `disposable-project/shapeshifter.yml` (`T3.4`).
- `container/tests/test_verify_inventory.sh` (`NEW`): asserts a disposition row per tracked file and that the rollback confirmation gate and the orchestrators' opt-in flags remain (`T3.5`).
- `docs/OPERATIONS.md`: entry-point wording corrected; the four release manager commands named; the superseded `GIT_REF`/`IMAGE_NAME` rollback guidance replaced (`T3.6`).
- `container/DEPLOYMENT.md`: migration subsection for a pre-release copy, including the four retired lifecycle scripts, the move-aside step, and the host prerequisite check (`T3.7`).
- `container/scripts/get-install.sh`: reduced to a host prerequisite check; the archive download, extraction, and `deployment.env` writes removed (`T3.8`).

**Issues found during implementation:**

- `F3-1` The lifecycle test's PATH-based stubs were ignored: this shell exports `BASH_ENV=/data/roger/.bash_env`, which re-exports `PATH` in every nested bash and dropped the stub directory, so `command -v podman` resolved to `/usr/bin/podman`. `dsn` now runs children with `env -u BASH_ENV -u ENV`, which is a no-op where those variables are unset. Test-only; no product change.
- `F3-2` A background child of a non-interactive shell has SIGINT set to ignore, so a trap in the stub could not fire. The `logs` case enables job control (`set -m`) for the backgrounded command so SIGINT remains deliverable, and it backgrounds the raw command rather than the `dsn` function so the exec can be measured by PID. Test-only.

**Validation results (2026-10-11):**

| ID | Result | Evidence |
| --- | --- | --- |
| `V-1` | Passed | `bash container/tests/test_lifecycle.sh`: 40 assertions, exit 0. Includes `up`, `down`, `restart`, `status`, `logs` (exec proven by unchanged PID and by SIGINT reaching the follower), empty and unknown actions exiting 64 with usage, the missing-data-directory diagnostic, the same cases through `make`, and an unchanged release-tree checksum. |
| `V-2` | Passed | Rendered unit with `%h` replaced by a temporary root: `systemd-analyze verify` exited 0 with no path or executability warning; `WorkingDirectory`, `ExecStart`, and `ExecStop` resolved under the rendered root; no deployment value is set in the unit. |
| `V-3` | Waived | By user decision (2026-10-11). Not run and not claimed as a pass; covered statically by `V-1` and `V-2`. |
| `V-4` | Passed | Complete tree passed with 21 required files; removing `scripts/service.sh` and removing `scripts/verify/verify_container_release.sh` each failed with `required deployment file missing: container/<path>`; the `git archive`-built archive passed. |
| `V-5` | Passed | `bash container/tests/test_verify_inventory.sh`: 29 assertions, exit 0. A negative probe with an undocumented script name was reported as undocumented. |
| `V-6` | Passed | `docs/OPERATIONS.md` names all four `shape-shifter-container-release` commands and no longer instructs changing `GIT_REF` or `IMAGE_NAME` for a container rollback; `container/DEPLOYMENT.md` carries the migration subsection and the host prerequisite check; `container/scripts/get-install.sh` has no `tar -xz` and no `deployment.env` write; `install_systemd_service.sh` names the release manager. |
| `V-7` | Passed | `test_path_resolution.sh` 27 assertions and `test_release_manager.sh` 79 assertions passed; `bash -n` clean on all changed shell files; ShellCheck reports only the two pre-existing `sync-to-deploy` SC1007 warnings. |

**Acceptance criteria with supporting evidence:**

- `PH3-AC-1` (`P-AC-7`): Make and the dispatcher perform every lifecycle action through a symlinked `~/container`; empty and unknown actions print usage and exit 64; `logs` replaces the dispatcher so a SIGINT reaches the follower; the release supplies `scripts/service.sh`; the unit parses and resolves its paths under the home root (`V-1`, `V-2`, `V-4`, `V-6`, `V-7`). The live systemd start/stop check is waived, so unit behavior rests on static checks and dispatcher coverage rather than a started unit.
- `PH3-AC-2` (`P-AC-8`): every tracked verification file has a disposition row naming its callers and safeguard; `verify_container_release.sh` remains an active release check invoked by the publication workflow and the installer; `rollback_exercise.sh` keeps its confirmation gate and `--yes`; both orchestrators keep `--authenticated` and `--rollback` opt-in; a release missing a required dependency fails validation (`V-4`, `V-5`, `V-6`, `V-7`).

**Deviations recorded:**

- The phase plan's Checkpoint 1 text (`Phase 3 Readiness` still reads "Requires the Phase 2 selection contract and caller review") was not edited. That condition is now satisfied and this task plan was implemented against it; the phase plan is outside this task plan's named deliverables.
- The lifecycle parity test needed two test-only workarounds (`F3-1`, `F3-2`) because of this shell environment. No `container.sh`, Makefile, or unit behavior was changed; `V-1` passes as written.

**Definition Of Done:** satisfied. `V-1`, `V-2`, `V-4`, `V-5`, `V-6`, and `V-7` pass; `V-3` is recorded as waived by user decision and is not claimed as a pass.

## Definition Of Done

- [x] Every `PH3-AC-*` criterion has implementation and validation evidence mapped to its `T*` and `V*` IDs.
- [x] All three work areas and their deliverables are complete.
- [x] `V-1`, `V-2`, `V-4`, `V-5`, `V-6` and `V-7` pass, and no ShellCheck diagnostic beyond the recorded baseline is introduced.
- [x] `V-3` is recorded as **waived by user decision on 2026-10-11** and is not claimed as a pass; `V-2` and `V-1` cover unit validity, path resolution, and every dispatcher action statically.
- [x] Every verification script retains its behavior and its opt-in safeguard; no check is added, removed, or redefined.
- [x] `verify_container_release.sh` remains an active release check, and a release that lacks a lifecycle or release-check dependency fails validation.
- [x] `docs/OPERATIONS.md`, `container/DEPLOYMENT.md`, and `container/scripts/verify/README.md` match the implemented commands and the migration path.
- [x] Deviations and follow-up work are documented, and no unresolved question affects implementation, correctness, or validation.

## Risks And Open Questions

- **Live systemd validation is waived by user decision (2026-10-11).** `V-3` needs a running systemd user manager and a selected release for a deployment user; the Phase 2 disposable container has none, and this developer account is not a deployment user. `V-2` verifies the unit parses and every path resolves under the home root, and `V-1` verifies each dispatcher action the unit invokes, but neither starts the unit. Unit-driven start, stop, and interruptible log following therefore remain unverified; the first deployment to a systemd host should run `V-3` then and record the result.
- **The lifecycle test depends on this shell environment being neutralized.** `container/tests/test_lifecycle.sh` unsets `BASH_ENV` and `ENV` for its child processes and enables job control for the `logs` case, because a startup file that re-exports `PATH` would bypass the stubs and a background child would otherwise ignore SIGINT (`F3-1`, `F3-2`). Both are no-ops on a host without those variables. If a future edit removes them, the test can silently exercise the real Podman instead of the stubs.
- **The `REQUIRED_FILES` change alters publication validation.** A container tree or archive that lacks `scripts/service.sh` or `scripts/verify/verify_container_release.sh` will fail from the next release onward. That is the intent, but it is a behavior change to a protected workflow and should be stated in the release notes for the next container version.
- **Phase 2's changes are uncommitted.** If they are reverted, `~/container` is no longer a manager-owned symlink and the lifecycle parity this phase verifies cannot hold. `T3.1` should be run against the worktree state, and the commit should include both phases' container changes together.
- **`get-install.sh` has no active caller.** Removing its download is safe for repositories and documentation, but an operator with a private host script that invokes it would need to switch to the release manager. The supported flow already requires that. The host prerequisite checks it still performs are now its only purpose.
- **Two deployment-verification orchestrators overlap.** `run_deployment_verification.sh` and `complete_test_deployment_verification.sh` cover related checks. This plan retains both and records the overlap; consolidating them belongs to `RELEASE_CYCLE_EVIDENCE_AND_LOCKING`, which also adds the run-record envelope. Resolve it there rather than in this phase.
- **Verification dispositions assume the active proposals keep their current needs.** `RELEASE_CYCLE_EVIDENCE_AND_LOCKING` and `SECURITY_HARDENING_FOLLOWUP` both reference these scripts. If either changes its check set, the disposition table and the inventory test must be updated in that work, not here.
- **graphify did not surface this phase's targets.** The graph query returned unrelated nodes despite 601 `container/scripts` entries in `graph.json`. Findings were taken from source and direct commands; no graph-derived claim is used in this plan.
