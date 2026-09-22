# Handoff: Test Environment Authorization Cutover

**Status:** Authorization applied in the test target environment; safe deployment verification, systemd ownership, external HTTPS reachability, privileged firewall inspection, same-LAN exception acceptance, authenticated access, cleanup, and rollback passed
**Opened:** 2026-09-22
**Branch:** `authorization-system-cutover` (all commits pushed to `origin`)
**Environment:** host `humlabsead`, deployment user `test-shape-shifter.sead.se` (uid/gid 1021), container `shape-shifter` published on `127.0.0.1:8012`, proxy `https://test-shape-shifter.sead.se`
**Source plans:** [TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md](./TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md), [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md)

## Purpose

Record the live centralized-authorization cutover in the test target environment. The deployment layout, authorization behavior, cleanup, and rollback have been verified; the remaining operational follow-up is credential rotation and deciding whether the reviewed project content should be provisioned or the policy regenerated for this environment.

## Current State

The test host runs the three-directory layout: `~/container` for replaceable code, `~/config` for configuration and policy (mode `700`, files `600`), and `~/container-data` for mutable data. The image was built with source commit `d1b21b5d` (tags `shape-shifter:test` and `shape-shifter:authorization-system-cutover-20260922`); the later commit `d27b072c` changed only host scripts and comments, so the running image already contains the container-side behavior described below. `http://127.0.0.1:8012/api/v1/health` answered `200` with `{"status":"healthy","version":"2.1.0","environment":"production"}` on 2026-09-22.

| Item | State |
|---|---|
| Layout, image build, container health | Done |
| htpasswd accounts (11) and application roles (19) | Applied |
| Reviewed manifest import | Applied: `32 resources, 2 administrators, 32 grants` |
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

Facts recorded on 2026-09-22:

- Accounts: `admin`, `roger`, `riia`, `rebecka`, `mattias`, `ershad`, `phil`, `athena`, `victoria`, `bruno`, `rooster`.
- Application roles: `project_maintainer` for `roger`, `rebecka`, `riia`, `mattias`; `project_creator` and `operator` for `riia`, `phil`, `ershad`, `mattias`, `bruno`, `athena`, `victoria`; `admin` for `admin`.
- Reviewed manifest: [resources/authorization/test-initial-manifest.yaml](../../../resources/authorization/test-initial-manifest.yaml) holds 32 resources (26 project, 6 shared_data_source), 32 grants (26 `owner` for one principal each, 6 `reader` for `everyone`/`authenticated`), and 3 administrators (`admin`, `roger`, `rebecka`).
- `SHAPE_SHIFTER_AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE=true` is set in `~/config/backend.env` and is live in the container; without it the six `everyone` grants are refused at import time.
- Inventory before cleanup: `list-resources` returned 51 rows (36 with lifecycle `active`, 15 `deleted`) and `list-grants` returned 51 rows. The four temporary `project:verification-containment-<timestamp>` resources were then deleted through the application; they are now deleted lifecycle records and excluded from `export-manifest`.
- Project content: `container-data/projects` holds only `verification-projects/` (those four containment projects and `archived/`); `container-data/backups` is empty; a search under `/data` to depth 5 found none of the reviewed project names. The reviewed manifest therefore names 26 projects and 6 shared data sources that this deployment does not hold.
- Enforcement check, `container/scripts/verify/verify_authenticated_access.sh`, passed with Bruno and Phil using temporary colon-qualified projects: unauthenticated access returned `401`, each principal received `200` for its granted project, and each other project's request returned the concealed `404` response.

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
| [TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md](./TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md) | Layout work this cutover runs on; `V-21` records the live target result and accepted same-LAN exception |
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md) | Phase 2 authorization work and its acceptance criteria |
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

1. **Rotate exposed credentials.** Rotate the administrator and shared authentication credentials, then update the target `~/config/authorization.env`, NGINX htpasswd, and protected configuration without recording secret values.

2. **Decide where the project content comes from.** The reviewed manifest names 26 projects and 6 shared data sources that this deployment does not hold. Either provision that content under `container-data/projects` and `container-data/shared`, or regenerate the policy for the content this environment actually has.

3. **Retain the completed verification evidence.** The rollback evidence is under `container-data/backups/rollback-20260922-103540`; the same-LAN exception remains accepted because no second host is available on the target LAN.

## Risks

- `secrets/.env` holds the shared htpasswd password and the administrator password in plain text, and `secrets/` is gitignored. Never commit it, echo it, or paste it into a shared document or chat.
- Commands that act as the deployment user must start from a directory that user can read, and rootless podman needs `-H` plus `XDG_RUNTIME_DIR`. Without either, sudo fails with `cannot chdir` or podman reports a running container as absent.
- A change under `backend/` needs `make build` and `make restart` before it affects the container; a change under `container/scripts/` needs only `sync-to-deploy`.
- `make restart` can print `rootless netns: kill network process: permission denied` while removing the network. It is a teardown warning, `podman-compose down` still exits zero, and `up` recreates the network.
- The four containment resources were removed through the application and are now deleted lifecycle records; `export-manifest` excludes them.
- `verify_authenticated_access.sh` requires each project to be granted to exactly one principal, and neither principal may be a bootstrap administrator.
- The reviewed manifest still names project content that is not present in this deployment. The authenticated check used temporary colon-qualified projects and therefore verifies grant enforcement, not the availability of the reviewed project dataset.

## Open Decisions

- Where the 26 projects and 6 shared data sources come from, or whether this environment keeps a regenerated manifest instead.
- Whether `deleted`-lifecycle rows and the `@local` grants should be removed from the store or kept as history. Current state keeps them; `export-manifest` and `reconcile` ignore deleted resources.
- Whether the remaining work stays on `authorization-system-cutover` or moves to a new branch.

## Suggested Follow-Up Documents

- A task plan for bringing the project and shared-data content into the test environment, if that direction is chosen.
