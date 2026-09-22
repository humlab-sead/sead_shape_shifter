# Task Plan: Target Environment Configuration Layout

## Phase Summary

- **Document type:** Deployment configuration migration task plan
- **Status:** Closed; implementation and live deployment verification complete with documented validation limitations
- **Source proposal:** [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md)
- **Related phase:** Phase 2 resource and manifest preparation; prerequisite to Phase 3 migration readiness
- **Goal:** Require the deployment user's `~/config`, `~/container`, and `~/container-data` sibling directories, move deployment-specific configuration and authorization inputs into `~/config`, and keep `~/container` replaceable and effectively read-only.
- **Planning decision:** This is a separate deployment-layout change, not a redefinition of authorization Phase 3. The master cutover plan should reference this plan as a prerequisite before Phase 3 execution.
- **Dependencies:** The existing authorization manifest and principal roster are reviewed in [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md). The target deployment is not released to end users, so no backward-compatible path fallback is required.

### Acceptance Criteria

- `CFG-AC-1` A normal deployment user home contains three required sibling directories: `container` for replaceable deployment code and build context, `config` for environment-specific configuration and authorization policy, and `container-data` for mutable runtime data and state. Explicit path overrides remain available for tests and controlled alternate layouts.
- `CFG-AC-2` No runtime path or deployment helper requires an environment-specific file under `container`; `container` can be replaced from a release archive without overwriting configuration or runtime data.
- `CFG-AC-3` `podman-compose.yml`, `Makefile`, lifecycle scripts, systemd integration, and deployment helpers resolve configuration and data paths from target-environment settings rather than a test user, host, or checkout path.
- `CFG-AC-4` The authorization bootstrap reads its credentials, group configuration, and manifest filename from `config`, and imports the configured manifest without using repository-local secrets.
- `CFG-AC-5` A fresh environment setup creates configuration templates and runtime directories in the correct locations, preserves existing target files, and applies restrictive permissions to credential files.
- `CFG-AC-6` Image builds work with a replaceable `container` checkout containing the required UCanAccess dependency under `container/lib`; runtime configuration and mutable deployment data remain outside the checkout.
- `CFG-AC-7` Existing runtime behavior is preserved: the container receives `backend.env`, the authorization database remains in `container-data/state`, PostgreSQL credentials remain file-mounted, backups remain under `container-data/backups`, and systemd starts the configured environment.
- `CFG-AC-8` Documentation and deployment verification commands describe the new layout and no longer instruct operators to edit `container/.env` or `container-data/backend.env`.

## Repository Findings

**Repository basis:** branch `authorization-system-cutover`; planning date 2026-09-21; existing uncommitted deployment-script and security-report changes were observed and are outside this plan's implementation scope.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `container/Makefile` configuration block, `container/.env.example` | The Makefile reads `container/.env`, defaults `DATA_DIR` to `../container-data`, exports `CONTAINER_DATA_DIR`, and creates `container-data/backend.env` during setup | Replace the local `.env` input with the required sibling `CONFIG_DIR` and `DATA_DIR` layout, defaulting to `~/config` and `~/container-data` for the deployment user, while retaining explicit overrides for tests |
| `container/podman-compose.yml` service `shape-shifter` | Compose reads `backend.env` and mounts projects, shared data, logs, output, backups, tmp, state, and `.pgpass` from `CONTAINER_DATA_DIR` | Keep mutable mounts under `DATA_DIR`; read `backend.env` and `.pgpass` from `CONFIG_DIR`; require Make or lifecycle scripts to export absolute paths before invoking Compose |
| `container/scripts/load-env.sh` | The shared loader sources `container/.env` and resolves relative `DATA_DIR` relative to the checkout | Load `CONFIG_DIR/deployment.env`, default to `~/config` and `~/container-data` under the deployment user's home, resolve explicit relative overrides from the checkout parent, and preserve command-line/environment precedence |
| `container/scripts/setup.sh` and Make targets `setup`, `setup-env`, `validate`, `update-env` | Setup mutates the checkout by creating `.env`; it creates `backend.env` and `.pgpass` in `container-data` | Setup must create `config` and `container-data` contents without writing mutable files into `container`; validation and editor targets must inspect `config` |
| `container/scripts/build.sh`, `container/Containerfile`, `container/Makefile` target `install-ucanaccess` | Standalone builds use `container` as context and `Containerfile` copies `lib/`; UCanAccess JARs are currently expected in `container/lib` | Keep UCanAccess under `container/lib/ucanaccess` for now. Treat it as an interim build dependency, not deployment configuration or runtime state, and defer its relocation to a separate change |
| `container/scripts/authorization.sh`, `backup.sh`, `up.sh`, `down.sh`, `logs.sh`, `verify/*` | Scripts derive data paths from `load-env.sh`; authorization restore uses `DATA_DIR/backend.env` for temporary containers; backup copies runtime configuration from `container-data` | Update all consumers to use the shared resolved `CONFIG_DIR` and keep state/backups in `DATA_DIR`; test restore and verification paths explicitly |
| `container/scripts/deploy/bootstrap-authentication-and-authorization.sh` | The bootstrap currently sources `secrets/.env`, installs `secrets/groups.d/shape-shifter.conf`, and resolves the manifest through that environment | Source `CONFIG_DIR/authorization.env`, install `CONFIG_DIR/groups.d/shape-shifter.conf`, and resolve a manifest filename relative to `CONFIG_DIR`; do not retain a repository-local fallback |
| `container/scripts/deploy/deploy_single_environment.sh`, `deploy_all_environments.sh`, `install_nginx_reverse_proxy.sh`, `install_systemd_service.sh` | Deployment helpers document and write `~/container/.env` and `~/container-data/backend.env`; systemd works from `~/container` and nginx reads `HOST_PORT` from the checkout config | Provision `~/config`, record deployment defaults there, preserve `~/container-data`, and have helpers consume the same resolved config path without hard-coded user or test values |
| `container/service/shape-shifter.service` | The unit sets `WorkingDirectory=%h/container` and starts `container/scripts/up.sh`, relying on the checkout loader | Keep the working directory for code execution but make `up.sh` resolve the sibling config directory through the shared loader |
| `secrets/.env`, `resources/authorization/test-initial-manifest.yaml`, `secrets/groups.d/shape-shifter.conf` | These are the current test deployment authorization inputs; the first is ignored and contains credentials, while the manifest and group file are policy inputs | The target deployment copy belongs under `~/config`; repository policy must not gain plaintext credentials, and the reviewed manifest must be provisioned separately from the release checkout |
| `container/resources/backend.env.example`, `container/resources/.pgpass.example`, `container/.env.example` | These are generic templates in the repository, not target credentials | Keep or relocate only generic templates in the read-only checkout; setup copies them into `CONFIG_DIR` and never treats them as live environment files |

## Target Layout

Each deployment user has this layout:

```text
~/container/                 # replaceable release checkout/build context
├── Containerfile
├── Makefile
├── podman-compose.yml
├── scripts/
├── service/
├── resources/               # generic templates only
└── lib/                     # interim UCanAccess build dependency

~/config/                    # target-environment configuration and policy
├── deployment.env           # image, ref, port, compose name, CONFIG_DIR/DATA_DIR overrides
├── backend.env              # runtime environment injected into the container
├── authorization.env        # bootstrap credentials, rosters, actor, manifest filename
├── authorization-manifest.yaml
├── groups.d/
│   └── shape-shifter.conf
├── .pgpass/
│   └── .pgpass

~/container-data/            # mutable runtime data
├── projects/
├── shared/
├── logs/
├── output/
├── backups/
├── tmp/
└── state/
    └── authorization.sqlite3
```

The normal deployment layout requires these three sibling directories under the deployment user's home: `~/container`, `~/config`, and `~/container-data`. `CONFIG_DIR` and `DATA_DIR` default to `~/config` and `~/container-data`; explicit absolute or relative overrides remain available for tests and controlled alternate layouts. There is no fallback to `container/.env`, `secrets/.env`, or `container-data/backend.env`.

`authorization.env` should store `AUTHORIZATION_MANIFEST=authorization-manifest.yaml`, not a repository-relative path. The bootstrap resolves a relative manifest filename within `CONFIG_DIR` and accepts an absolute path only when an operator deliberately configures one.

## Scope

**In scope**

- Define and implement the `container` / `config` / `container-data` separation.
- Update Makefile configuration loading, setup, validation, editor, diagnostics, lifecycle target environment, and compose export behavior.
- Update `podman-compose.yml` runtime env-file and PostgreSQL credential paths.
- Update shared shell environment loading and every script consumer identified above.
- Move authorization bootstrap inputs from repository-local `secrets` to target `config`.
- Preserve the current UCanAccess JAR storage under `container/lib/ucanaccess` for now and validate GitHub, local, and standalone image builds.
- Update deployment helpers, systemd integration, backup/restore behavior, deployment verification, and deployment documentation.
- Provide a no-fallback migration procedure for the unreleased development deployment.

**Out of scope**

- Authorization policy changes, role changes, principal changes, or manifest grant changes.
- Changes to project YAML, project data, shared data files, or the authorization schema.
- Backward compatibility with the old `container/.env`, `secrets/.env`, or `container-data/backend.env` paths.
- Replacing Podman, podman-compose, nginx, or systemd.
- Adding secrets to the repository or image.

**Affected components**

- Deployment configuration: `container/Makefile`, `container/podman-compose.yml`, templates, and `container/service/`.
- Shell operations: `container/scripts/`, especially environment loading, setup, build, lifecycle, backup, authorization, verification, and deploy helpers.
- Target files created outside the repository: `~/config/*` and `~/container-data/*`.
- Documentation: `container/README.md`, `container/DEPLOYMENT.md`, relevant `docs/OPERATIONS.md`, and cutover inventory/status records.
- Validation: shell checks, Makefile dry runs, rendered Compose configuration, image builds, container lifecycle, authorization import/reconcile, backup/restore, and deployment verification.

## Work Breakdown

### Area 1: Define the external configuration contract

**Objective:** Establish one path contract and file ownership model used by Make, Compose, scripts, systemd, and deployment helpers.

**Affected code:** `container/Makefile`, `container/.env.example`, `container/scripts/load-env.sh`, `container/podman-compose.yml`, `container/service/shape-shifter.service`.

**Dependencies:** None.

* [x] `T1.1` **Change:** Replace checkout-local deployment defaults with an external `CONFIG_DIR/deployment.env` contract.
  * **Target:** `container/Makefile` configuration block and `container/.env.example`.
  * **Current → required:** Make includes `container/.env` and writes it during setup. Make must load `CONFIG_DIR/deployment.env`, default `CONFIG_DIR` to `~/config` and `DATA_DIR` to `~/container-data` for the canonical deployment layout, and never create or require `container/.env`.
  * **Implementation:** Capture command-line and environment values before including the deployment env; default `CONFIG_DIR` and `DATA_DIR` to `~/config` and `~/container-data`; resolve them to absolute paths; export `CONFIG_DIR`, `CONTAINER_DATA_DIR`, and all Compose variables. Keep precedence explicit: command line, process environment, deployment env, built-in defaults. Keep generic examples separate from live files.
  * **Constraints:** Do not include a fallback to the old path. Require the canonical sibling layout for normal deployment helpers, but preserve explicit path overrides for tests and controlled alternate layouts. Do not embed a target user, hostname, port, or environment name.
  * **Validation:** `V-1`, `V-2`.
* [x] `T1.2` **Change:** Make the shared shell loader resolve the same external paths.
  * **Target:** `container/scripts/load-env.sh` and callers that source it.
  * **Current → required:** The loader sources `container/.env` and resolves relative data paths from the checkout. It must source `CONFIG_DIR/deployment.env`, default to the deployment user's `~/config` and `~/container-data`, export resolved `CONFIG_DIR` and `DATA_DIR`, and preserve explicitly supplied environment values.
  * **Implementation:** Define the config directory before loading the deployment env; default to the deployment user's home layout; resolve explicit relative overrides against the checkout's parent layout; reject missing required files only at commands that need them; keep loader behavior safe to source.
  * **Constraints:** A direct script invocation and a Make invocation must resolve identical paths. Raw `podman-compose` is not the supported operator entry point; Make and lifecycle scripts must load and export the host-side Compose variables.
  * **Validation:** `V-1`, `V-3`.
* [x] `T1.3` **Change:** Pass external config paths through Compose and systemd.
  * **Target:** `container/podman-compose.yml`, `container/service/shape-shifter.service`.
  * **Current → required:** Compose reads `backend.env` and `.pgpass` from `container-data`; systemd relies on implicit checkout-local configuration. Compose must read runtime configuration and PostgreSQL credentials from `CONFIG_DIR` while mutable mounts remain under `DATA_DIR`.
  * **Implementation:** Use absolute `CONFIG_DIR` and `CONTAINER_DATA_DIR` values exported by Make; mount `${CONFIG_DIR}/.pgpass/.pgpass` read-only and use `${CONFIG_DIR}/backend.env` as the service env file. Keep state at `${CONTAINER_DATA_DIR}/state` and backups at `${CONTAINER_DATA_DIR}/backups`. Update systemd comments and any environment assumptions.
  * **Constraints:** Do not mount all of `config` into the application container. Only the runtime env file and required credential file are exposed.
  * **Validation:** `V-2`, `V-4`, `V-8`.

**Completion evidence:** The canonical deployment-user home layout produces identical resolved Compose paths from `make config`, a direct lifecycle-script invocation, and systemd's lifecycle script; temporary test directories work through explicit `CONFIG_DIR` and `DATA_DIR` overrides.

### Area 2: Move setup and runtime operations to the new directories

**Objective:** Setup and operational commands create, read, back up, and validate target files outside the checkout.

**Affected code:** `container/scripts/setup.sh`, `container/scripts/up.sh`, `down.sh`, `logs.sh`, `status.sh`, `healthcheck.sh`, `backup.sh`, `authorization.sh`, `verify/rollback_exercise.sh`, `verify/run_deployment_verification.sh`, `verify/verify_credential_rotation.sh`, and Make targets that call them.

**Dependencies:** Area 1.

* [x] `T2.1` **Change:** Make `setup` provision `CONFIG_DIR` and `DATA_DIR` without mutating `container`.
  * **Target:** `container/scripts/setup.sh`, `container/Makefile` targets `setup`, `setup-directories`, `setup-env`, `validate`, `update-env`.
  * **Current → required:** Setup creates `container/.env`, `container-data/backend.env`, and `container-data/.pgpass`. It must create `config/deployment.env`, `config/backend.env`, and `config/.pgpass/.pgpass` from generic templates while preserving existing files.
  * **Implementation:** Create directories with explicit modes; copy generic deployment and runtime templates; require the authorization-specific files before bootstrap rather than generating credentials; add clear next-step output for `config/backend.env`, `config/.pgpass/.pgpass`, and `config/authorization.env`.
  * **Constraints:** Never copy credentials or the reviewed authorization manifest from the repository into a live target automatically. Do not overwrite existing config.
  * **Validation:** `V-5`, `V-6`.
* [x] `T2.2` **Change:** Update runtime and maintenance scripts to use config and data ownership correctly.
  * **Target:** lifecycle scripts, `backup.sh`, `authorization.sh`, and verification scripts listed above.
  * **Current → required:** Several scripts derive `backend.env`, `.pgpass`, and backups from `DATA_DIR`; authorization restore and verification invoke temporary containers with old paths. They must use `CONFIG_DIR` for configuration and `DATA_DIR` for mutable state.
  * **Implementation:** Keep authorization SQLite, project data, logs, output, tmp, and backup archives in `DATA_DIR`; use `CONFIG_DIR/backend.env` and `CONFIG_DIR/.pgpass/.pgpass` for runtime injection and restore checks; decide and document which config files are copied into a backup with mode preservation.
  * **Constraints:** Do not expose `authorization.env` or `.pgpass` through application container mounts; preserve restrictive permissions and backup operator controls.
  * **Validation:** `V-7`, `V-8`, `V-9`.
* [x] `T2.3` **Change:** Make diagnostics and editor targets report and edit the external configuration.
  * **Target:** `container/Makefile` diagnostics, `make config`, `make validate`, `make update-env`, and script help text.
  * **Current → required:** Help and status output refer to `container/.env` and `container-data/backend.env`. They must name `CONFIG_DIR/deployment.env` and `CONFIG_DIR/backend.env` and show resolved absolute paths where useful.
  * **Constraints:** Documentation and command output must not imply that files under `container` are writable deployment state.
  * **Validation:** `V-1`, `V-5`, `V-10`.

**Completion evidence:** A fresh temporary layout is initialized, existing config is preserved on a second setup run, lifecycle commands consume the external files, and backups contain the intended runtime/configuration records without moving mutable state into `container`.

### Area 3: Relocate authorization bootstrap inputs

**Objective:** Make authorization bootstrap fully target-environment-specific and independent of repository-local secrets.

**Affected code:** `container/scripts/deploy/bootstrap-authentication-and-authorization.sh`, `container/scripts/authorization.sh`, `config` provisioning documentation, and the reviewed deployment inventory.

**Dependencies:** Areas 1 and 2.

* [x] `T3.1` **Change:** Read authorization credentials and policy from `CONFIG_DIR`.
  * **Target:** `container/scripts/deploy/bootstrap-authentication-and-authorization.sh`.
  * **Current → required:** The script sources `secrets/.env`, installs `secrets/groups.d/shape-shifter.conf`, and imports the manifest path from that source. It must source `CONFIG_DIR/authorization.env`, install `CONFIG_DIR/groups.d/shape-shifter.conf`, and require `AUTHORIZATION_MANIFEST` with `-z` validation.
  * **Implementation:** Resolve `CONFIG_DIR` from the deployment environment; source only `CONFIG_DIR/authorization.env`; resolve a relative `AUTHORIZATION_MANIFEST` filename beneath `CONFIG_DIR`; validate readable files before mutating htpasswd or application roles; retain principal-only deployment role assignments and the configured audit actor.
  * **Constraints:** No fallback to `secrets/.env`, repository `resources/`, or a test-specific path. Do not add collaborator grants or alter the reviewed manifest policy.
  * **Validation:** `V-11`, `V-12`, `V-13`.
* [x] `T3.2` **Change:** Define the target configuration provisioning and permissions for authorization files.
  * **Target:** deployment runbook and the target `~/config` migration procedure; repository templates only where generic examples are safe.
  * **Current → required:** Authorization credentials are currently kept in ignored repository `secrets/.env`; the target must receive them through an operator-controlled `config/authorization.env`, manifest, and group file.
  * **Implementation:** Document manual or secured provisioning of `authorization.env`, `authorization-manifest.yaml`, and `groups.d/shape-shifter.conf`; make the deployment user the owner of all of `~/config`; specify restrictive file modes; record that the manifest is policy data while `authorization.env` contains credentials; require `SHAPE_SHIFTER_AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE=true` in `backend.env` before importing the reviewed manifest.
  * **Constraints:** Do not commit target credentials. Do not silently generate administrator passwords or change the reviewed administrator roster.
  * **Validation:** `V-12`, `V-14`.
* [x] `T3.3` **Change:** Update the inventory and status records to the new target paths.
  * **Target:** `secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md`, `secrets/STATUS_20260921.md`.
  * **Current → required:** Records point to repository-local manifest/config paths and describe a development-only layout. They must identify the target `~/config` files and separate source-controlled generic templates from target-provisioned policy.
  * **Constraints:** Preserve the reviewed resource counts, owners, administrators, and deferred collaborator decisions.
  * **Validation:** `V-14`.

**Completion evidence:** Running the bootstrap with a temporary `CONFIG_DIR` uses only that directory for credentials, groups, and manifest; an absent manifest fails before account or role mutation; the reviewed YAML dry-run/import/reconcile commands use the new path.

### Area 4: Preserve and validate checkout build dependencies

**Objective:** Keep runtime configuration and mutable state outside `container` while preserving the current checkout-owned UCanAccess build dependency and all supported image build modes.

**Affected code:** `container/scripts/build.sh`, `container/Containerfile`, `container/Makefile` targets `build`, `build-local`, `build-no-cache`, and UCanAccess installation scripts.

**Dependencies:** Area 1; configuration directory contract must be stable.

* [x] `T4.1` **Change:** Preserve downloaded UCanAccess JARs under `container/lib/ucanaccess` as an interim build dependency.
  * **Target:** `container/scripts/install-ucanaccess.sh`, `container/scripts/build.sh`, `container/Containerfile`, Makefile validation/help.
  * **Current → required:** The build context expects UCanAccess JARs under `container/lib/ucanaccess`. Keep installation and validation on that path until a separate build-dependency relocation is approved.
  * **Implementation:** Preserve the existing dependency directory, Containerfile copy behavior, and final `/app/lib` contents. Ensure GitHub and local source modes use the same checkout dependency input.
  * **Constraints:** UCanAccess is an explicit interim exception to the goal of keeping target-specific files outside `container`; it is not runtime configuration or mutable application state. Do not copy secrets into the build context or change application source resolution or image runtime paths.
  * **Validation:** `V-15`, `V-16`.
* [x] `T4.2` **Change:** Test clean checkout replacement and repeated builds.
  * **Target:** build scripts and deployment procedure.
  * **Current → required:** A rebuild may currently depend on files left in `container/lib` or `.env`. A replacement checkout plus persistent `config` and `container-data` must build and start when the required UCanAccess dependency is present under `container/lib`.
  * **Constraints:** Preserve image identity, Git ref, UID/GID, cache-busting, and release-tag behavior. Do not move runtime configuration or mutable state into the checkout.
  * **Validation:** `V-16`, `V-17`.

**Completion evidence:** A replacement of `~/container` builds the configured image using the required checkout-owned UCanAccess dependency and preserved `~/config` and `~/container-data` contents.

### Area 5: Update deployment helpers and operational documentation

**Objective:** Make deployment provisioning and operator instructions target-environment-agnostic.

**Affected code:** `container/scripts/deploy/deploy_single_environment.sh`, `deploy_all_environments.sh`, `install_nginx_reverse_proxy.sh`, `install_systemd_service.sh`, `container/README.md`, `container/DEPLOYMENT.md`, `docs/OPERATIONS.md`, and cutover plan references.

**Dependencies:** Areas 1–4.

* [x] `T5.1` **Change:** Provision and preserve sibling `config` during deployment archive replacement.
  * **Target:** `container/scripts/deploy/deploy_single_environment.sh` and `deploy_all_environments.sh`.
  * **Current → required:** The single-environment helper writes deployment defaults to `~/container/.env` and tells operators to edit `~/container-data/backend.env`. It must create or preserve `~/config`, record defaults in `~/config/deployment.env`, and preserve both `~/config` and `~/container-data` when replacing `~/container`.
  * **Constraints:** Do not use a test user, hostname, or port as a code-level default beyond the generic application default. Do not overwrite target credentials, policy, data, or state.
  * **Validation:** `V-18`.
* [x] `T5.2` **Change:** Resolve nginx and systemd configuration from the target config contract.
  * **Target:** `install_nginx_reverse_proxy.sh`, `install_systemd_service.sh`, `container/service/shape-shifter.service`.
  * **Current → required:** Nginx and systemd instructions refer to checkout-local `.env` values and paths. They must use the configured `CONFIG_DIR`/`deployment.env` and continue to execute code from `container`.
  * **Constraints:** Keep nginx credentials and authorization group installation on the host; do not mount or copy all config into the application image.
  * **Validation:** `V-18`, `V-19`.
* [x] `T5.3` **Change:** Rewrite deployment documentation and cutover references.
  * **Target:** `container/README.md`, `container/DEPLOYMENT.md`, `docs/OPERATIONS.md`, `docs/proposals/CENTRALIZED_AUTHORIZATION_CUTOVER/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md`, and relevant inventory/status records.
  * **Current → required:** Documentation describes `container/.env`, `container-data/backend.env`, and a two-directory layout. It must describe the three-directory layout, provisioning order, permissions, replacement workflow, and authorization manifest location.
  * **Constraints:** Mark the old development layout as retired rather than documenting compatibility behavior.
  * **Validation:** `V-20`.

**Completion evidence:** A new operator can provision one target environment from the deployment helper, replace `container`, restart the service, and locate all configuration and data files from the documented commands without guessing paths.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `CFG-AC-1` | `T1.1`, `T2.1`, `T5.1` | `V-5`, `V-18` | Temporary target uses separate `container`, `config`, and `container-data` directories |
| `CFG-AC-2` | `T1.1`, `T2.3`, `T4.2`, `T5.1` | `V-10`, `V-16`, `V-18` | No setup or deployment command writes live configuration into `container` |
| `CFG-AC-3` | `T1.1`, `T1.2`, `T1.3`, `T5.2` | `V-1`, `V-2`, `V-3`, `V-19` | Make, Compose, scripts, systemd, and deploy helpers use resolved target paths |
| `CFG-AC-4` | `T3.1`, `T3.2` | `V-11`, `V-12`, `V-13`, `V-14` | Bootstrap imports only the configured target manifest and credentials |
| `CFG-AC-5` | `T2.1`, `T3.2` | `V-5`, `V-6`, `V-12` | Setup is idempotent and permissions are correct |
| `CFG-AC-6` | `T4.1`, `T4.2` | `V-15`, `V-16`, `V-17` | Replaceable checkout and checkout-owned UCanAccess dependency build successfully |
| `CFG-AC-7` | `T1.3`, `T2.2`, `T4.2` | `V-4`, `V-7`, `V-8`, `V-9`, `V-17` | Runtime mounts, authorization state, PostgreSQL credentials, and backups remain correct |
| `CFG-AC-8` | `T2.3`, `T3.3`, `T5.3` | `V-10`, `V-14`, `V-20` | Documentation and operator output describe only the new layout |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Makefile configuration precedence | Run `make -C "$HOME/container" -n config` with the canonical sibling layout, then repeat with `CONFIG_DIR=/tmp/shape-config DATA_DIR=/tmp/shape-data` and a temporary `deployment.env` | `CFG-AC-1`, `CFG-AC-3` | Canonical defaults and explicit test overrides resolve correctly; no `container/.env` is read | Passed 2026-09-21: canonical, absolute, and relative overrides resolve as documented, and a stale `container/.env` is ignored |
| `V-2` | Render Compose configuration | Run `make -C "$HOME/container" config` with canonical files, then repeat with `CONFIG_DIR=/tmp/shape-config DATA_DIR=/tmp/shape-data` after creating valid temporary `backend.env` and `.pgpass` | `CFG-AC-1`, `CFG-AC-3` | `env_file`, `.pgpass`, and all mutable volumes resolve to the intended directories | Passed 2026-09-21: in both layouts `env_file` and the read-only `.pgpass` mount resolved under `CONFIG_DIR`, and every mutable mount under `CONTAINER_DATA_DIR` |
| `V-3` | Shared loader parity | Source `container/scripts/load-env.sh` from the canonical checkout and invoke a lifecycle script; repeat with explicit temporary config/data overrides | `CFG-AC-1`, `CFG-AC-3` | Direct scripts and Make resolve identical absolute paths in both canonical and test layouts | Passed 2026-09-21: Make, the loader, and `scripts/down.sh` resolved identical paths in six layout and precedence scenarios |
| `V-4` | Compose mount contract | Inspect rendered Compose output and start a disposable container with test paths | `CFG-AC-3`, `CFG-AC-7` | Only `backend.env` and `.pgpass` are read from config; projects, state, logs, output, tmp, shared, and backups are data mounts | Passed 2026-09-21: a disposable container with temporary paths carried only `backend.env` and the read-only `.pgpass` from `CONFIG_DIR`, and every mutable mount from `CONTAINER_DATA_DIR` |
| `V-5` | Fresh setup | Run `make -C container setup CONFIG_DIR=<temp>/config DATA_DIR=<temp>/container-data` in a disposable home/layout | `CFG-AC-1`, `CFG-AC-5` | Config templates, runtime directories, and required modes are created outside the checkout | Passed 2026-09-21: an isolated layout received `config/` (mode 700) with `deployment.env`, `backend.env` (600) and `.pgpass/.pgpass` (600), the data subdirectories, and a report of the missing operator-provisioned authorization inputs; nothing was written into the checkout |
| `V-6` | Setup idempotence and preservation | Place sentinel content in config files, rerun setup, and compare hashes | `CFG-AC-5` | Existing deployment values and credentials are unchanged | Passed 2026-09-21: sentinel content in `deployment.env`, `backend.env`, `.pgpass/.pgpass`, and a file under `container-data/projects` survived a second run with identical hashes, and setup reported each file as already existing |
| `V-7` | Backup path check | Run the backup target with temporary config/data paths and inspect the resulting archive | `CFG-AC-7` | Runtime state remains under data; documented config files are backed up with safe permissions | Passed 2026-09-21: one archive held `projects`, `shared`, and `state` at its root plus `config/` with `deployment.env`, `backend.env`, and `.pgpass/.pgpass`; `config/` was mode 700 and the credential files kept mode 600 |
| `V-8` | Authorization wrapper path check | Run `container/scripts/authorization.sh --help` and controlled backup/restore dry-run commands with `CONFIG_DIR` and `DATA_DIR` overrides | `CFG-AC-3`, `CFG-AC-7` | Wrapper uses external backend env and data state paths | Partially run 2026-09-21: `--help` exits 0 and both `--env-file` arguments now resolve `CONFIG_DIR/backend.env` while temporary restore containers keep `DATA_DIR/state`; the restore path itself was not exercised because no deployment container is running on this host |
| `V-9` | Verification path check | Run verification scripts against a disposable deployment or inspect their generated Podman commands | `CFG-AC-7` | Rollback and credential-rotation checks use config credentials and data state | Passed 2026-09-21: `rollback_exercise.sh` reports a missing backend env against the configured `CONFIG_DIR`, passes `CONFIG_DIR` alongside `CONTAINER_DATA_DIR` to Compose, and uses `CONFIG_DIR/backend.env` in all three temporary containers; `verify_credential_rotation.sh` listed `config/.pgpass/.pgpass` and `config/backend.env`; `run_deployment_verification.sh` resolves `--config-dir` separately from `--data-dir` |
| `V-10` | Static stale-path scan | `rg -n 'container/\\.env|container-data/backend\\.env|secrets/\\.env|resources/authorization/test-initial-manifest|~/container-data/backend\\.env' container docs secrets` | `CFG-AC-2`, `CFG-AC-8` | No active instructions or code depend on retired paths; intentional migration-history references are labeled | Partially run 2026-09-21: no Area 1 or Area 2 file depends on a retired path; the remaining hits belong to `T3.1`/`T3.3` (bootstrap script, inventory and status records), `T4.1` (`build.sh` comments), and `T5.1`–`T5.3` (deploy helpers, `container/README.md`, `container/DEPLOYMENT.md`, `docs/OPERATIONS.md`). In `setup.sh` the only matches name the checkout template `container/.env.example`, which is intentional |
| `V-11` | Bootstrap shell validation | `bash -n container/scripts/deploy/bootstrap-authentication-and-authorization.sh && shellcheck container/scripts/deploy/bootstrap-authentication-and-authorization.sh` | `CFG-AC-4` | Script is syntactically valid and has no new ShellCheck findings | Passed 2026-09-21: `bash -n` reports no error and `shellcheck -f gcc` reports no findings for the rewritten script |
| `V-12` | Bootstrap missing-file negative test | Use a temporary `CONFIG_DIR` with missing `authorization.env` or manifest and invoke the script in a stubbed root/deployment environment | `CFG-AC-4`, `CFG-AC-5` | It fails before htpasswd, group installation, role grants, or manifest import | Passed 2026-09-21: six temporary `CONFIG_DIR` scenarios each stopped at the intended check in order — missing `authorization.env`, absent `AUTHORIZATION_MANIFEST`, unreadable manifest (reported as the path below `CONFIG_DIR`), unreadable group file, missing deployment directory, and finally the root gate. No htpasswd file, group file, role, or manifest was touched |
| `V-13` | Authorization manifest import | Set `SHAPE_SHIFTER_AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE=true` in temporary `backend.env`; run the configured wrapper import and `reconcile` against a disposable database | `CFG-AC-4`, `CFG-AC-7` | Reviewed YAML imports and reconciles with zero missing records; no repository-local secret path is used | Partially run 2026-09-21: with the approved manifest installed as `authorization-manifest.yaml` below a temporary `CONFIG_DIR` and the everyone setting enabled, `migrate` applied 32 resources, 3 administrators, and 32 grants to a disposable database and `reconcile` reported 0 missing records, with no repository secrets path involved. The container wrapper itself was not exercised because no deployment container is running on this host |
| `V-14` | Policy and inventory consistency | Compare `config/authorization-manifest.yaml` to the reviewed inventory; verify 3 administrators, 26 projects, 6 shared sources, 26 owner grants, and 6 authenticated reader grants | `CFG-AC-4`, `CFG-AC-8` | Counts and deferred collaborator decision remain unchanged | Passed 2026-09-21: the installed manifest holds 26 `project` and 6 `shared_data_source` resources, 26 `owner` grants on principals, 6 `reader` grants on `everyone`, and 3 `admin` application roles. No collaborator grant or group role was added |
| `V-15` | UCanAccess install path | Run `make -C container install-ucanaccess` and inspect files | `CFG-AC-6` | JARs are stored under `container/lib/ucanaccess`, the documented interim location | Passed 2026-09-21: the target downloaded 3.18 MB from SourceForge into `container/lib/ucanaccess`, and the resulting six-JAR set is byte-identical to the previous install. The installer now stages the download before replacing the installed copy, so a failed download no longer removes the dependency |
| `V-16` | Build modes | Run `make -C container build-local` and the configured GitHub/ref build with the required UCanAccess files under `container/lib/ucanaccess` | `CFG-AC-6` | Both builds succeed and the image contains the expected `/app/lib` dependency files | Passed 2026-09-21: `make build-local` and the configured `GIT_REF=main` GitHub build both succeeded with temporary image tags, and both images carry the six nested JARs under `/app/lib/ucanaccess`. With the repository-root copy removed beforehand, the workdir build staged the dependency from `container/lib/ucanaccess` into its build context and reproduced it byte-for-byte |
| `V-17` | Replacement test | Replace a disposable `container` checkout from the same release archive while retaining config/data, then run `make up`, health check, and authorization inspection | `CFG-AC-2`, `CFG-AC-6`, `CFG-AC-7` | Service starts with preserved configuration, data, database, and manifest policy | Passed 2026-09-21: a fresh copy of `container` with a separate `config` and `container-data` started through `make up`, answered `/api/v1/health` with `200`, and passed `authorization.sh integrity-check` against `container-data/state/authorization.sqlite3` while a sentinel file in the preserved data directory stayed in place. The disposable container, layout, and temporary images were removed afterwards |
| `V-18` | Deployment helper test | Run `deploy_single_environment.sh --no-build` for a disposable user/home and inspect resulting sibling directories | `CFG-AC-1`, `CFG-AC-2`, `CFG-AC-3` | Helper creates/preserves config and data and writes no live settings into container | Partially run 2026-09-21: `get-install.sh` was exercised end to end against a local release archive in a disposable home; it extracted the deployment files, recorded `GIT_REPO`, `GIT_REF`, and `IMAGE_NAME` in `~/config/deployment.env`, created no `container/.env`, and printed the new paths. The provisioning block of `deploy_single_environment.sh` then ran in the same layout and recorded `GIT_REPO`, `GIT_REF`, `IMAGE_NAME`, and `HOST_PORT` in `~/config/deployment.env` with all three sibling directories present. The root-only `sudo -u` wrapper was not executed because this account has no root access |
| `V-19` | Systemd/nginx path test | Render/install generated unit and nginx configuration with a temporary deployment config; inspect paths and port values | `CFG-AC-3`, `CFG-AC-7` | Services use the target config values and continue to execute code from container | Partially run 2026-09-21: `HOST_PORT` resolved to `8013` from a temporary `CONFIG_DIR/deployment.env`, and rendering `nginx-shape-shifter.conf.template` with that value produced `server 127.0.0.1:8013` for the requested domain. The systemd unit sets `WorkingDirectory=%h/container`, starts `scripts/up.sh`, stops `scripts/down.sh`, and defines no deployment value. Installing the vhost and the unit was not performed because those steps need root plus live NGINX and systemd sessions |
| `V-20` | Documentation/path review | Search deployment docs and execute every documented path-bearing command in a disposable environment | `CFG-AC-8` | Docs describe the three-directory layout and no retired path as current practice | Partially run 2026-09-21: in a disposable canonical layout, `make setup`, `make config`, `make validate`, and `make info` ran with the default `~/config` and `~/container-data`; the rendered Compose file took `env_file` from `~/config/backend.env` and the read-only `.pgpass` from `~/config/.pgpass/.pgpass`; every path the documentation names existed after setup; and `scripts/check_doc_links.sh` reported valid links. Steps that need root or a live deployment were not executed |
| `V-21` | Live target deployment verification | Run the safe post-deployment checks against `/data/test-shape-shifter.sead.se` and record authenticated access, reconciliation, cleanup, and rollback separately | `CFG-AC-3`, `CFG-AC-4`, `CFG-AC-7` | The running deployment is healthy, contained to loopback, uses the external layout, and passes authorization allow/deny, reconciliation, and rollback checks | Recorded on 2026-09-22 with the accepted same-LAN exception: loopback health returned `200`; the public protected route returned `401`; the backend listened only on `127.0.0.1:8012`; the container was running with loopback-only publication and expected mounts; authorization database integrity passed; manifest reconciliation reported `Missing: 0 resources, 0 administrators, 0 grants`; systemd was `active (exited)` and invoked `container/scripts/up.sh` with `--no-build`; `sudo nginx -t` passed; external `test-shape-shifter.sead.se:443` resolved to `130.239.34.54` and was open; privileged nftables inspection found default inbound drop with no `8012` accept rule; authenticated isolation passed for Bruno and Phil; cleanup deleted all four temporary projects with HTTP `204` responses; and rollback restored the recorded image and authorization backup, reconciled zero missing records, and returned health `200` |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| External configuration contract | `container/Makefile`, `container/scripts/load-env.sh`, `container/.env.example` | `T1.1`, `T1.2` | Make and scripts consume `CONFIG_DIR/deployment.env` |
| Runtime mount contract | `container/podman-compose.yml`, `container/service/shape-shifter.service` | `T1.3` | Compose and systemd use config/data separation |
| Setup and operations migration | `container/scripts/setup.sh`, lifecycle/backup/authorization/verify scripts | `T2.1`, `T2.2`, `T2.3` | Fresh and repeated setup plus operational checks pass |
| Authorization bootstrap migration | `container/scripts/deploy/bootstrap-authentication-and-authorization.sh` and target `~/config/authorization.*` procedure | `T3.1`, `T3.2` | Bootstrap uses only target config and imports the reviewed manifest |
| Inventory/status update | `secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md`, `secrets/STATUS_20260921.md` | `T3.3` | Records identify target config paths and preserve policy decisions |
| Checkout build dependency handling | `container/scripts/build.sh`, `container/scripts/install-ucanaccess.sh`, `container/Containerfile`, `container/lib/ucanaccess` | `T4.1`, `T4.2` | Replacement checkout builds with the documented UCanAccess files |
| Deployment helper migration | `container/scripts/deploy/*.sh`, `container/README.md`, `container/DEPLOYMENT.md`, `docs/OPERATIONS.md` | `T5.1`, `T5.2`, `T5.3` | Deployment and replacement workflow is target-environment-agnostic |
| Cutover plan linkage | `CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md` | Follow-up after this plan is approved | Phase 3 names this configuration migration as a prerequisite |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: External configuration contract | Done | None | `CONFIG_DIR`/`DATA_DIR` default to the home-root siblings, `resolve_path` in the Makefile matches `scripts/load-env.sh`, `container/.env` is never read, and Compose and systemd take runtime config from `CONFIG_DIR`. Validated with `V-1`–`V-4` |
| Area 2: Setup and runtime operations | Done | Area 1 | Setup provisions `config/` and `container-data/` from generic templates without writing into the checkout; backup keeps data under `DATA_DIR` and configuration under `CONFIG_DIR/config`, and the authorization, rollback, and credential-rotation checks read `CONFIG_DIR/backend.env` and `CONFIG_DIR/.pgpass/.pgpass`. Validated with `V-5`–`V-10`, of which `V-8` and `V-10` are partial (no running container on this host; remaining retired paths belong to Areas 3–5) |
| Area 3: Authorization bootstrap inputs | Done | Areas 1–2 | The bootstrap resolves `CONFIG_DIR` to the checkout's sibling, reads `authorization.env`, `authorization-manifest.yaml` and `groups.d/shape-shifter.conf` only from there, validates them before any change, and passes the same `CONFIG_DIR` to the wrapper. `container/resources/authorization.env.example` and the new *Authorization inputs* section in `container/DEPLOYMENT.md` document operator provisioning; the inventory and status records name the target paths. Validated with `V-11`–`V-14`, of which `V-13` is partial (the container wrapper needs a running deployment) |
| Area 4: Checkout build dependencies | Done | Area 1 | UCanAccess stays under `container/lib/ucanaccess` as the single installed copy. `build.sh` stages it into the repository-root build context when that context has no copy, so workdir and standalone builds use the same dependency, and it reads deployment settings from `CONFIG_DIR/deployment.env`. `install-ucanaccess.sh` now replaces the installed copy only after a successful download. `container/DEPLOYMENT.md` documents checkout replacement. Validated with `V-15`–`V-17` |
| Area 5: Deployment helpers and documentation | Done | Areas 1–4 | `deploy_single_environment.sh`, `deploy_all_environments.sh`, `get-install.sh`, and `rebuild-image.sh` provision `~/config` and keep it and `~/container-data` out of any checkout refresh; every helper that creates `~/config` now sets mode `700`, and `make validate` reports the mode so a wrong one is visible before the bootstrap needs it; `rebuild-image.sh` no longer defaults to a test deployment user and its `--dry-run` flag now reports instead of acting; the nginx and systemd helpers name the resolved config contract. `container/README.md`, `container/DEPLOYMENT.md`, and `docs/OPERATIONS.md` describe the three-directory layout and mark the old paths as retired. `V-18`–`V-20` remain partial because disposable root-only installation checks were unavailable; the live target evidence in `V-21` covers the deployed helper, systemd, NGINX, verification, firewall, authentication, cleanup, and rollback behavior |

**Follow-up after merge.** The deployment verification orchestrator writes its run directories to `CONTAINER_DATA_DIR/deployment-verification/` instead of `$PWD/deployment-verification/`, and operators copy its options file to `~/config/deployment-verification.options.yml`. Run output therefore stays out of the replaceable checkout and off the container's filesystem, which the container achieves by mounting only the enumerated data subdirectories.

## Definition Of Done

- [x] `CFG-AC-1` through `CFG-AC-8` have implementation and validation evidence.
- [x] No compatibility fallback reads `container/.env`, `secrets/.env`, or `container-data/backend.env`.
- [x] `container` can be replaced without changing `config` or `container-data`.
- [x] Makefile and Compose resolve paths for at least two distinct target layouts without source edits.
- [x] Setup is idempotent and applies documented permissions to credentials, policy, and runtime files.
- [x] Authorization bootstrap imports the reviewed YAML manifest from the target config directory and reconciliation passes.
- [x] Local and GitHub image builds preserve application content and UCanAccess support; UCanAccess remains the documented interim exception to the external configuration layout.
- [x] Runtime, backup, restore, systemd, nginx, and deployment verification checks pass on the target deployment; the unavailable same-LAN check is explicitly accepted by the release owner.
- [x] The cutover phase plan links this migration before Phase 3 is executed.
- [x] No project YAML, shared data, authorization policy, or unrelated worktree changes were modified by the migration.

**Closure note.** The plan is closed because all implementation deliverables and
target acceptance checks are complete. `V-18`–`V-20` retain their partial labels
for the unexecuted disposable root-only steps; this is a validation limitation,
not an identified implementation failure.

The live target checks in `V-21` confirm health, authentication denial and
positive grant enforcement, loopback publication, container configuration,
authorization database integrity, manifest reconciliation, NGINX syntax,
external HTTPS reachability, cleanup, rollback, and firewall policy. Same-LAN
testing is not available for this virtual server and is recorded as an accepted
environment limitation. Credential rotation and the source of the reviewed
project content remain operational follow-up; credential rotation is complete and
the project-content decision is outside this layout plan.

## Risks And Open Questions

- **Resolved interim decision — UCanAccess location:** Keep UCanAccess under `container/lib/ucanaccess` for the time being. This is a build dependency rather than target runtime configuration or mutable state. A future relocation can be planned separately after the three-directory runtime configuration change is stable.
- **Resolved decision — config ownership:** The deployment user owns all of `~/config`, including credentials, policy, group configuration, runtime environment, and PostgreSQL credential files. Keep restrictive file modes, such as `600` where group access is unnecessary, and ensure bootstrap, systemd, and backup operations run with the required deployment-user access.
- **Resolved decision — authorization manifest provisioning:** The reviewed manifest is currently a repository artifact under `resources/authorization/`, but the target copy must be installed under `~/config` and referenced by `authorization.env` through an operator-controlled provisioning step. Deployment tooling must not silently copy policy or invent credentials; the operator must explicitly provide or approve the reviewed manifest before bootstrap.
- **Resolved decision — phase-plan integration:** The master cutover plan now lists this task plan as supplemental Phase 2A. The configuration migration may follow the Phase 2 manifest review, but it must complete before Phase 3 applies or reconciles the manifest.
- **Resolved decision — Compose entry point:** Do not add a new wrapper for this change. Make targets and lifecycle scripts are the supported Compose entry points and must source `CONFIG_DIR/deployment.env` through the shared loader before invoking `podman-compose`. Raw direct `podman-compose` use is unsupported unless the operator explicitly exports the resolved host-side variables.
