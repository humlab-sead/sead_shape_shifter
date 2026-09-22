# Handoff: Test Environment Authorization Cutover

**Status:** Authorization applied in the test target environment; release image rebuilt from `dev`; reviewed project and shared data content provisioned and listed by the application; safe deployment verification, systemd ownership, external HTTPS reachability, privileged firewall inspection, same-LAN exception acceptance, authenticated access, cleanup, and rollback passed
**Opened:** 2026-09-22
**Branch:** `authorization-system-cutover` (all commits pushed to `origin`)
**Environment:** host `humlabsead`, deployment user `test-shape-shifter.sead.se` (uid/gid 1021), container `shape-shifter` published on `127.0.0.1:8012`, proxy `https://test-shape-shifter.sead.se`
**Source plans:** [TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md](./done/TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md), [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md), [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_3_TASK_PLAN.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_3_TASK_PLAN.md)

> **Note added 2026-09-22 during the Phase 4 review.** The audit trail examined for [UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md](./done/UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md) does not corroborate the cleanup statements below: all 30 `resource_lifecycle_changed` events are dated 2026-09-18 and none is dated 2026-09-22, and four `verification-containment-*` resources are still active and absent from the reviewed manifest. A rollback restore that rewrote the store and its audit events is the most consistent explanation, but it is not proven. Treat the statements below that describe the 2026-09-22 cleanup as unconfirmed; the Phase 4 record holds the current account of the store. The `bulgaria-arbodat-lookup-options` follow-up named under *Purpose* was resolved on 2026-09-22 by removing the definition.

## Purpose

Record the live centralized-authorization cutover in the test target environment. The deployment layout, authorization behavior, cleanup, rollback, and in-scope credential rotation have been verified, and the reviewed project and shared data content is now provisioned. All six shared data sources are listed by the application, and `sead-options` is verified against the live database; the remaining follow-up is confirming whether `bulgaria-arbodat-lookup-options` is complete without a data file.

## Current State

The test host runs the three-directory layout: `~/container` for replaceable code, `~/config` for configuration and policy (mode `700`, files `600`), and `~/container-data` for mutable data. The deployed image is now the release build from merged `dev`; the earlier `d27b072c` baseline image remains on the host as the rollback target. `http://127.0.0.1:8012/api/v1/health` answered `200` with `{"status":"healthy","version":"2.1.0","environment":"production"}` on 2026-09-22, last confirmed at 10:59:17Z on the release image.

| Item | State |
|---|---|
| Layout, image build, container health | Done |
| htpasswd accounts (11) and application roles (19) | Applied |
| Reviewed manifest import | Applied: `32 resources, 3 administrators, 32 grants` |
| Store matches the reviewed manifest | Confirmed for all 32 reviewed resources and 32 reviewed grants |
| Denial and concealment for non-granted projects | Confirmed: unauthenticated `401`, non-granted project `404` with `{"detail":"Resource not found"}` |
| Positive access for a granted project | Passed 2026-09-22 with Bruno and Phil using colon-qualified project locators |
| Cleanup of four leftover resources | Passed 2026-09-22: all four colon-qualified temporary projects were deleted through the application with HTTP `204` responses |
| Layout validations `V-18`, `V-19`, `V-20` | Partially run on 2026-09-21 in disposable environments; live target checks added 2026-09-22 |
| Live loopback health and protected-route denial | Verified 2026-09-22: loopback health `200`; public protected route `401` |
| Live port containment and container configuration | Verified 2026-09-22: backend on `127.0.0.1:8012` only; LAN bypass refused; configuration inspection passed |
| Live authorization database integrity | Verified 2026-09-22 through `authorization.sh integrity-check` |
| Live manifest reconciliation | Verified 2026-09-22: `Missing: 0 resources, 0 administrators, 0 grants` |
| NGINX syntax and external HTTPS reachability | Verified 2026-09-22: `sudo nginx -t` passed; `test-shape-shifter.sead.se` resolved to `130.239.34.54` and port `443` was open |
| Safe deployment verification and systemd ownership | Verified 2026-09-22: the bundle passed loopback health, loopback-only publication, container state and mount checks, authorization integrity, manifest reconciliation, and systemd `active (exited)` status; the loaded unit invokes `~/container/scripts/up.sh` with the prebuilt image and no build |
| Same-LAN connectivity check | Not available: the target is a virtual server and no computer on the target LAN is available; local loopback-only binding and external HTTPS checks were recorded instead |
| Same-LAN exception acceptance | Accepted 2026-09-22 by Roger Mähler: no second host is available on the target LAN; loopback-only publication, default-drop firewall policy, and external HTTPS reachability are the recorded compensating checks |
| Privileged firewall inspection | Passed 2026-09-22: nftables input policy is `drop`; approved rules expose proxy ports `80/443` only, and no rule accepts `8012` |
| Authenticated positive access | Passed 2026-09-22 with Bruno and Phil using colon-qualified project locators: each principal received `200` for its granted project and concealed `404` for the other project's request; unauthenticated access returned `401` |
| Rollback exercise | Passed 2026-09-22: the recorded image and authorization backup restored successfully, integrity and manifest reconciliation reported zero missing records, and the restarted service returned health `200` |
| In-scope credential rotation | Passed 2026-09-22: `ADMIN_AUTH_PASSWORD` and `AUTH_PASSWORD` were recorded as rotated. PostgreSQL rotation is out of scope by decision for every PostgreSQL database, including the SEAD database |
| Rollback and exception owner | Roger Mähler is the named rollback decision owner and approves exceptions for unavailable checks, recorded 2026-09-22 |

### Phase 3 closeout evidence

The following checks were run on 2026-09-22 without repeating the completed Phase 1, Phase 2, or Phase 2A migration and layout work:

| Check | Result |
|---|---|
| Full backend regression | Passed at `e38f4bc6` and rerun at the post-merge `dev` revision `dbff5ab95459652354c040b9d4fec6e2ead94f96`: `.venv/bin/pytest backend/tests -q`; all collected tests passed with the repository's existing skips and one unrelated JPype deprecation warning |
| Reviewed manifest identity | SHA-256 `43c03186f708164ce9334a001c45b80c4f206fb2efa06d413dff9ad4a2cafb90`; authoritative content is 3 administrators (`admin`, `roger`, `rebecka`), 32 resources, and 32 grants |
| Release image identity | `shape-shifter:dev`, image ID `6a487db722883da0eb0c3cfdc00444c07dea1edaf7d59b15643227576acc04a8`, built 2026-09-22 10:55:15Z from `github`, OCI source revision `dbff5ab95459652354c040b9d4fec6e2ead94f96`, OCI version `dev` |
| Release image source revision | `dbff5ab95459652354c040b9d4fec6e2ead94f96` equals the `dev` merge commit for PR #495 and the checkout revision where the focused authorization and full backend suites passed |
| Configuration revision | `GIT_REF=dev`, `IMAGE_NAME=shape-shifter:dev`, `GIT_REPO=https://github.com/humlab-sead/sead_shape_shifter.git`, recorded in `/data/test-shape-shifter.sead.se/config/deployment.env` by the deploy script |
| Baseline image identity (retained) | `localhost/shape-shifter:test`, image ID `4762be65496839738800b5034cf487faafaf4bda6c3dceb2e608d00fe5e4700b`, OCI source revision `d27b072c26e026fe9049a14558ffbaf0ffecda98`, built from checkout `e38f4bc67b289dd23f6995f38ff70ccc79a32bf0` |
| Authorization inventory | 51 retained resources: 36 active and 15 deleted; 53 retained grants; 25 application-role rows, including 3 `admin` roles. Historical/deleted rows explain why raw store totals exceed the 32 reviewed active records |
| Manifest reconciliation | Passed using a one-shot container with the host manifest mounted read-only: `Missing: 0 resources, 0 administrators, 0 grants` |
| Administrator access | Passed: `admin` received HTTP 200 for `GET /api/v1/projects` through `https://test-shape-shifter.sead.se`; credentials and response contents were not recorded |
| Release-image integrity and reconciliation | Passed on `shape-shifter:dev`: `authorization.sh integrity-check` reported `Authorization database integrity check passed`, and reconciliation against the reviewed manifest staged inside the container reported `Missing: 0 resources, 0 administrators, 0 grants` |
| Readiness backup | `authorization-20260922-110641.sqlite3`, SHA-256 `9ebf2f2229807cf56ce32cc2d2a7c7fe0c67f67553c3d606833dc71cd9ae8b3e`; writable-copy integrity check passed |
| Release-image backup | `authorization-20260922-130050.sqlite3`, SHA-256 `9ebf2f2229807cf56ce32cc2d2a7c7fe0c67f67553c3d606833dc71cd9ae8b3e`; byte-identical to the readiness backup, so authorization state did not change across the image switch |
| Provisioned target content | All 26 reviewed project locators resolve to a `shapeshifter.yml` under `container-data/projects`, and all 6 reviewed shared data sources are listed by `GET /api/v1/data-sources`: `arbodat-data-options`, `arbodat-lookup-options`, `bugscep_data_20250608`, `bulgaria-arbodat-lookup-options`, `digidiggie_tng-options`, and `sead-options` |
| Shared data source connection | `sead-options` verified on 2026-09-22: `POST /api/v1/data-sources/sead-options/test` returned `success: true`, 167 tables, 112 ms, with `SEAD_HOST=host.docker.internal` |

Facts recorded on 2026-09-22:

- Accounts: `admin`, `roger`, `riia`, `rebecka`, `mattias`, `ershad`, `phil`, `athena`, `victoria`, `bruno`, `rooster`.
- Application roles: `project_maintainer` for `roger`, `rebecka`, `riia`, `mattias`; `project_creator` and `operator` for `riia`, `phil`, `ershad`, `mattias`, `bruno`, `athena`, `victoria`; `admin` for `admin`.
- Reviewed manifest: [resources/authorization/test-initial-manifest.yaml](../../../resources/authorization/test-initial-manifest.yaml) holds 32 resources (26 project, 6 shared_data_source), 32 grants (26 `owner` for one principal each, 6 `reader` for `everyone`/`authenticated`), and 3 administrators (`admin`, `roger`, `rebecka`).
- `SHAPE_SHIFTER_AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE=true` is set in `~/config/backend.env` and is live in the container; without it the six `everyone` grants are refused at import time.
- Inventory before cleanup: `list-resources` returned 51 rows (36 with lifecycle `active`, 15 `deleted`) and `list-grants` returned 51 rows. The four temporary `project:verification-containment-<timestamp>` resources were then deleted through the application; they are now deleted lifecycle records and excluded from `export-manifest`.
- Target content: all 26 reviewed project locators resolve to a `shapeshifter.yml`, and all 6 reviewed shared data sources appear in the application's listing. `arbodat-data-options`, `arbodat-lookup-options`, `bugscep_data_20250608`, and `digidiggie_tng-options` reference `ArchBotDaten.mdb`, `ArchBotStrukDat.mdb`, `bugsdata_20250608.mdb`, and `Digidiggie_v7_kbw.accdb`, all present in `container-data/shared/shared-data`. `bulgaria-arbodat-lookup-options` is accepted with the `access` driver and no `filename`, and `sead-options` resolves `${SEAD_HOST}`, `${SEAD_PORT}`, `${SEAD_DBNAME}`, and `${SEAD_USER}` from `config/backend.env`, where `SEAD_HOST` is `host.docker.internal` because the container cannot reach the host's LAN address.
- Enforcement check, `container/scripts/verify/verify_authenticated_access.sh`, passed with Bruno and Phil using temporary colon-qualified projects: unauthenticated access returned `401`, each principal received `200` for its granted project, and each other project's request returned the concealed `404` response.
- Credential rotation check passed with exit code `0`; the final record marked `authorization:ADMIN_AUTH_PASSWORD` and `authorization:AUTH_PASSWORD` as rotated. That record is an operator attestation: the check lists labels and never verifies that a value changed. On 2026-09-22 PostgreSQL rotation was decided out of scope for every PostgreSQL database, including the SEAD database, so no PostgreSQL credential is rotated or re-checked.

### Commands that act as the deployment user

Run them from a directory the deployment user can read, and give rootless podman that user's runtime directory:

```
cd /tmp && sudo -u test-shape-shifter.sead.se -H env XDG_RUNTIME_DIR=/run/user/1021 bash -lc 'cd ~/container && ./scripts/authorization.sh <command>'
```

From the checkout, `sudo -u test-shape-shifter.sead.se` fails with `cannot chdir` because `/data/roger` is not readable by that user.

## Completed Work

- Areas 1–5 of the layout task plan: three-directory layout, path resolution, operator-provisioned authorization inputs, deployment helpers, and documentation.
- Live migration of the test host to the new layout, including `~/config/deployment.env`, `~/config/backend.env`, and `~/config/.pgpass/.pgpass` (mode `600` inside a `700` directory) and correction of a migrated `../container-data` spelling that resolved one level too high.
- Five host-discovered defects fixed in the repository:
  - `15c89c46` run the bootstrap in the deployment user's podman context (`-H` and `XDG_RUNTIME_DIR`), otherwise podman reports the running container as absent.
  - `2b8fbee3` switch to the deployment directory before running as its user, because `sudo` keeps the caller's working directory.
  - `fe47d0f5` read htpasswd passwords from stdin with `-i`; without it htpasswd prompts on the terminal and ignores the here-string.
  - `d1b21b5d` detect the manifest format from content when the path has no recognised extension, with a test for the extension-less case.
  - `d27b072c` place the imported manifest inside the container, because `migrate` reads it twice and a stdin stream cannot be read twice.
- Bootstrap run to completion on 2026-09-22: htpasswd accounts, nginx group file, 19 application-role grants, and the manifest import, ending with `Authorization database ready: /app/state/authorization.sqlite3`.
- Post-deployment checks re-run on 2026-09-22: loopback health returned `200`, the public protected route returned `401`, the backend listener was loopback-only, container configuration passed, authorization database integrity passed, manifest reconciliation reported no missing records, `sudo nginx -t` passed, and external HTTPS port `443` was open. The safe verification bundle also confirmed the container was running, published only `127.0.0.1:8012`, and was owned by the systemd user service through `scripts/up.sh` with `--no-build`. Authenticated isolation passed for Bruno and Phil; cleanup then deleted all four temporary projects through the application with HTTP `204` responses. The privileged nftables inspection passed with default inbound drop and no `8012` accept rule. The rollback exercise restored the recorded image and authorization backup, reconciled zero missing records, and returned health `200`. Same-LAN testing is unavailable for this virtual server and the exception was accepted by Roger Mähler on 2026-09-22.
- Repository memory (`/memories/repo/container-deployment-layout.md`) records the host-specific lessons: working directory for `sudo -u`, `XDG_RUNTIME_DIR`, `htpasswd -i`, the two-read manifest import, and which kind of change needs an image rebuild.

## Key References

| Reference | Use |
|---|---|
| [TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md](./done/TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md) | Layout work this cutover runs on; `V-21` records the live target result and accepted same-LAN exception |
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md) | Phase 2 authorization work and its acceptance criteria |
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) | Overall cutover phases and release disposition |
| [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md) | Earlier deployment verification record |
| [container/DEPLOYMENT.md](../../../container/DEPLOYMENT.md) | Layout, authorization inputs, replacing the checkout, image build |
| [container/scripts/authorization.sh](../../../container/scripts/authorization.sh) | Operator wrapper: `import-manifest`, `export-manifest`, `backup`, `restore`, and pass-through CLI commands |
| [container/scripts/deploy/bootstrap-authentication-and-authorization.sh](../../../container/scripts/deploy/bootstrap-authentication-and-authorization.sh) | Accounts, nginx group file, application roles, manifest import |
| [container/scripts/verify/verify_authenticated_access.sh](../../../container/scripts/verify/verify_authenticated_access.sh) | Enforcement check used for the result above |
| [container/scripts/verify/run_deployment_verification.sh](../../../container/scripts/verify/run_deployment_verification.sh) | Orchestrated verification runs; `--authenticated` enables the check above |
| [resources/authorization/test-initial-manifest.yaml](../../../resources/authorization/test-initial-manifest.yaml) | Reviewed policy that was imported |
| `secrets/` (local only, gitignored) | `TEST_DEPLOYMENT_RESOURCE_INVENTORY.md`, `STATUS_20260921.md`, and `.env` with the htpasswd passwords |

## Next Actions

1. **Confirm the remaining configuration-dependent data source.** `sead-options` is verified against the live database. `bulgaria-arbodat-lookup-options` still declares the `access` driver with no data file, so confirm whether that is intentional.

2. **Retain the completed verification evidence.** The rollback evidence is under `container-data/backups/rollback-20260922-103540`; the credential-rotation output records the two in-scope passwords as rotated and PostgreSQL rotation is out of scope by decision, and the same-LAN exception remains accepted because no second host is available on the target LAN.

## Risks

- `secrets/.env` holds the shared htpasswd password and the administrator password in plain text, and `secrets/` is gitignored. Never commit it, echo it, or paste it into a shared document or chat.
- Commands that act as the deployment user must start from a directory that user can read, and rootless podman needs `-H` plus `XDG_RUNTIME_DIR`. Without either, sudo fails with `cannot chdir` or podman reports a running container as absent.
- A change under `backend/` needs `make build` and `make restart` before it affects the container; a change under `container/scripts/` needs only `sync-to-deploy`.
- `make restart` can print `rootless netns: kill network process: permission denied` while removing the network. It is a teardown warning, `podman-compose down` still exits zero, and `up` recreates the network.
- The four containment resources were removed through the application and are now deleted lifecycle records; `export-manifest` excludes them.
- `verify_authenticated_access.sh` requires each project to be granted to exactly one principal, and neither principal may be a bootstrap administrator.
- `bulgaria-arbodat-lookup-options` remains unproven in use: the application lists it, but it declares the `access` driver with no `filename`. The authenticated access check used temporary colon-qualified projects, so it verifies grant enforcement rather than access to the reviewed dataset.
- **Container-to-host services need the gateway alias.** The container cannot reach the host's LAN address, so host services must be addressed as `host.docker.internal`. Host-side checks against the LAN address succeed and therefore give a false positive. See [container/DEPLOYMENT.md](../../../container/DEPLOYMENT.md).
- The release image is built from merged `dev` at `dbff5ab95459652354c040b9d4fec6e2ead94f96`, so its recorded source revision matches the checkout where the focused and full backend suites passed. The earlier `d27b072c` image built from checkout `e38f4bc6` remains on the host as the rollback target and is no longer the running image.

## Open Decisions

- Whether the recorded rotation of the NGINX and application passwords is an acceptable evidence level, given the check records labels and the operator's assertion rather than verifying a value changed, and no rotated value is retained in the repository. PostgreSQL rotation is settled: out of scope by decision.
- Whether `deleted`-lifecycle rows and the `@local` grants should be removed from the store or kept as history. Current state keeps them; `export-manifest` and `reconcile` ignore deleted resources.
- Whether the remaining work stays on `authorization-system-cutover` or moves to a new branch.

## Suggested Follow-Up Documents

- A Phase 4 task plan for post-cutover operations, including the `bulgaria-arbodat-lookup-options` data-file confirmation and the access checks on the release image.
