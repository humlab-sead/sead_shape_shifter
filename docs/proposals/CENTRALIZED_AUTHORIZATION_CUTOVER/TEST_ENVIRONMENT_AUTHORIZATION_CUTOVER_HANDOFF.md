# Handoff: Test Environment Authorization Cutover

**Status:** Authorization applied in the test target environment; safe deployment verification, systemd ownership, and external HTTPS reachability passed; authenticated access, cleanup, rollback, and privileged firewall inspection remain open
**Opened:** 2026-09-22
**Branch:** `authorization-system-cutover` (all commits pushed to `origin`)
**Environment:** host `humlabsead`, deployment user `test-shape-shifter.sead.se` (uid/gid 1021), container `shape-shifter` published on `127.0.0.1:8012`, proxy `https://test-shape-shifter.sead.se`
**Source plans:** [TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md](./TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md), [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md)

## Purpose

Continue the live centralized-authorization cutover in the test target environment from another machine. Three things are open: remove the leftover verification resources, settle where the project and shared-data content comes from, and finish the authenticated-access check that shows per-resource grants work for ordinary principals.

## Current State

The test host runs the three-directory layout: `~/container` for replaceable code, `~/config` for configuration and policy (mode `700`, files `600`), and `~/container-data` for mutable data. The image was built with source commit `d1b21b5d` (tags `shape-shifter:test` and `shape-shifter:authorization-system-cutover-20260922`); the later commit `d27b072c` changed only host scripts and comments, so the running image already contains the container-side behavior described below. `http://127.0.0.1:8012/api/v1/health` answered `200` with `{"status":"healthy","version":"2.1.0","environment":"production"}` on 2026-09-22.

| Item | State |
|---|---|
| Layout, image build, container health | Done |
| htpasswd accounts (11) and application roles (19) | Applied |
| Reviewed manifest import | Applied: `32 resources, 2 administrators, 32 grants` |
| Store matches the reviewed manifest | Confirmed for all 32 reviewed resources and 32 reviewed grants |
| Denial and concealment for non-granted projects | Confirmed: unauthenticated `401`, non-granted project `404` with `{"detail":"Resource not found"}` |
| Positive access for a granted project | Blocked: the granted projects do not exist in this deployment |
| Cleanup of four leftover resources | Pending |
| Layout validations `V-18`, `V-19`, `V-20` | Partially run on 2026-09-21 in disposable environments; live target checks added 2026-09-22 |
| Live loopback health and protected-route denial | Verified 2026-09-22: loopback health `200`; public protected route `401` |
| Live port containment and container configuration | Verified 2026-09-22: backend on `127.0.0.1:8012` only; LAN bypass refused; configuration inspection passed |
| Live authorization database integrity | Verified 2026-09-22 through `authorization.sh integrity-check` |
| Live manifest reconciliation | Verified 2026-09-22: `Missing: 0 resources, 0 administrators, 0 grants` |
| NGINX syntax and external HTTPS reachability | Verified 2026-09-22: `sudo nginx -t` passed; `test-shape-shifter.sead.se` resolved to `130.239.34.54` and port `443` was open |
| Safe deployment verification and systemd ownership | Verified 2026-09-22: the bundle passed loopback health, loopback-only publication, container state and mount checks, authorization integrity, manifest reconciliation, and systemd `active (exited)` status; the loaded unit invokes `~/container/scripts/up.sh` with the prebuilt image and no build |
| Same-LAN connectivity check | Not available: the target is a virtual server and no computer on the target LAN is available; local loopback-only binding and external HTTPS checks were recorded instead |

Facts recorded on 2026-09-22:

- Accounts: `admin`, `roger`, `riia`, `rebecka`, `mattias`, `ershad`, `phil`, `athena`, `victoria`, `bruno`, `rooster`.
- Application roles: `project_maintainer` for `roger`, `rebecka`, `riia`, `mattias`; `project_creator` and `operator` for `riia`, `phil`, `ershad`, `mattias`, `bruno`, `athena`, `victoria`; `admin` for `admin`.
- Reviewed manifest: [resources/authorization/test-initial-manifest.yaml](../../../resources/authorization/test-initial-manifest.yaml) holds 32 resources (26 project, 6 shared_data_source), 32 grants (26 `owner` for one principal each, 6 `reader` for `everyone`/`authenticated`), and 3 administrators (`admin`, `roger`, `rebecka`).
- `SHAPE_SHIFTER_AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE=true` is set in `~/config/backend.env` and is live in the container; without it the six `everyone` grants are refused at import time.
- Inventory: `list-resources` returns 51 rows (36 with lifecycle `active`, 15 `deleted`) and `list-grants` returns 51 rows. `export-manifest` reports `Exported: 36 resources, 3 administrators, 36 grants`. The 36 active resources are the reviewed 32 plus four `project:verification-containment-<timestamp>` resources, each with a `principal:verification-containment-<timestamp>-creator@local owner` grant left behind by interrupted 2026-09-18 containment runs.
- Project content: `container-data/projects` holds only `verification-projects/` (those four containment projects and `archived/`); `container-data/backups` is empty; a search under `/data` to depth 5 found none of the reviewed project names. The reviewed manifest therefore names 26 projects and 6 shared data sources that this deployment does not hold.
- Enforcement check, `container/scripts/verify/verify_authenticated_access.sh` with `bruno`/`Brunos_copy_Riia_Strucke_v8` and `riia`/`Riia_Strucke_v8`: `proxy-auth` `401` PASS, `denied-A` and `denied-B` `404` with the concealed body PASS, `allowed-A` and `allowed-B` `404` FAIL with the project service's `ResourceNotFoundError` and `Project not found: …`. The differing bodies show authorization allowed those two requests and the project lookup failed afterwards, so the two failures come from missing project content, not from the grant model.

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
- Post-deployment checks re-run on 2026-09-22: loopback health returned `200`, the public protected route returned `401`, the backend listener was loopback-only, container configuration passed, authorization database integrity passed, manifest reconciliation reported no missing records, `sudo nginx -t` passed, and external HTTPS port `443` was open. The safe verification bundle also confirmed the container was running, published only `127.0.0.1:8012`, and was owned by the systemd user service through `scripts/up.sh` with `--no-build`. Same-LAN testing is unavailable for this virtual server; the firewall rule listing still needs an operator with `sudo` access.
- Repository memory (`/memories/repo/container-deployment-layout.md`) records the host-specific lessons: working directory for `sudo -u`, `XDG_RUNTIME_DIR`, `htpasswd -i`, the two-read manifest import, and which kind of change needs an image rebuild.

## Key References

| Reference | Use |
|---|---|
| [TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md](./TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md) | Layout work this cutover runs on; `V-18`, `V-19`, and `V-20` remain partially run |
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md) | Phase 2 authorization work and its acceptance criteria |
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) | Overall cutover phases and release disposition |
| [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md) | Earlier deployment verification record; authenticated access and the rollback exercise are still listed as not run |
| [container/DEPLOYMENT.md](../../../container/DEPLOYMENT.md) | Layout, authorization inputs, replacing the checkout, image build |
| [container/scripts/authorization.sh](../../../container/scripts/authorization.sh) | Operator wrapper: `import-manifest`, `export-manifest`, `backup`, `restore`, and pass-through CLI commands |
| [container/scripts/deploy/bootstrap-authentication-and-authorization.sh](../../../container/scripts/deploy/bootstrap-authentication-and-authorization.sh) | Accounts, nginx group file, application roles, manifest import |
| [container/scripts/verify/verify_authenticated_access.sh](../../../container/scripts/verify/verify_authenticated_access.sh) | Enforcement check used for the result above |
| [container/scripts/verify/run_deployment_verification.sh](../../../container/scripts/verify/run_deployment_verification.sh) | Orchestrated verification runs; `--authenticated` enables the check above |
| [resources/authorization/test-initial-manifest.yaml](../../../resources/authorization/test-initial-manifest.yaml) | Reviewed policy that was imported |
| `secrets/` (local only, gitignored) | `TEST_DEPLOYMENT_RESOURCE_INVENTORY.md`, `STATUS_20260921.md`, and `.env` with the htpasswd passwords |

## Next Actions

1. **Clean up the four leftover active resources.** Read what the application sees first, because some manifest locators use a `group:project` form:

   ```
   read -rsp 'admin password: ' PW; echo
   curl -sS -u "admin:$PW" -o /tmp/live-projects.json -w 'http=%{http_code}\n' https://test-shape-shifter.sead.se/api/v1/projects
   unset PW
   ```

   Then delete those four projects through the application, which removes the directory and marks the resource `deleted` (`AuthorizationService` updates the resource lifecycle on project deletion):

   ```
   read -rsp 'admin password: ' PW; echo
   for p in <the four names>; do
     curl -sS -u "admin:$PW" -X DELETE -o /dev/null -w "$p -> %{http_code}\n" "https://test-shape-shifter.sead.se/api/v1/projects/$p"
   done
   unset PW
   ```

   Expect `204` for each. Verify with `list-resources` (the four become `deleted`) and `export-manifest` (which should drop from 36/3/36 to 32/3/32).

2. **Decide where the project content comes from.** The reviewed manifest names 26 projects and 6 shared data sources that this deployment does not hold. Either bring that content into `container-data/projects` and `container-data/shared`, then re-run the enforcement check against real projects, or regenerate the policy for the content this environment actually has (`export-manifest` writes the current active set).

3. **Finish the authenticated-access check.** Prepare two projects and grant each to exactly one ordinary principal. Administrators (`admin`, `roger`, `rebecka`) must not be used, because they bypass denial:

   ```
   cd /tmp && sudo -u test-shape-shifter.sead.se -H env XDG_RUNTIME_DIR=/run/user/1021 bash -lc 'cd ~/container && ./scripts/authorization.sh grant \
     --resource-type project --locator <project> --subject-type principal --subject-id <principal> --role viewer --actor test-shape-shifter.sead.se'
   ```

   Then run:

   ```
   cd /tmp && sudo -u test-shape-shifter.sead.se -H bash /data/test-shape-shifter.sead.se/container/scripts/verify/verify_authenticated_access.sh \
     --base-url https://test-shape-shifter.sead.se \
     --principal-a <principal> --project-a <project> \
     --principal-b <principal> --project-b <project>
   ```

   Keeping two of the four containment projects instead of deleting all four gives a working positive test with the least effort.

4. **Update the tracked plan.** Record the 2026-09-22 host result, and the state of `V-18`, `V-19`, and `V-20`, in the layout task plan's Progress Tracker and Definition Of Done.

5. **Complete `V-18`, `V-19`, and `V-20`** (deployment helper, systemd/nginx rendering, and documentation sweep) in disposable users and homes.

6. **Record the outcome** in the Phase 2 task plan and, when the release disposition needs it, in the cutover plan.

## Risks

- `secrets/.env` holds the shared htpasswd password and the administrator password in plain text, and `secrets/` is gitignored. Never commit it, echo it, or paste it into a shared document or chat.
- Commands that act as the deployment user must start from a directory that user can read, and rootless podman needs `-H` plus `XDG_RUNTIME_DIR`. Without either, sudo fails with `cannot chdir` or podman reports a running container as absent.
- A change under `backend/` needs `make build` and `make restart` before it affects the container; a change under `container/scripts/` needs only `sync-to-deploy`.
- `make restart` can print `rootless netns: kill network process: permission denied` while removing the network. It is a teardown warning, `podman-compose down` still exits zero, and `up` recreates the network.
- The four active containment resources look like reviewed policy until they are removed, and `export-manifest` includes them.
- `verify_authenticated_access.sh` requires each project to be granted to exactly one principal, and neither principal may be a bootstrap administrator.
- The two recorded enforcement failures come from missing project content. Do not record the cutover as verified on positive access until that check passes.

## Open Decisions

- Where the 26 projects and 6 shared data sources come from, or whether this environment keeps a regenerated manifest instead.
- Whether to keep two containment projects as enforcement fixtures instead of deleting all four.
- Whether `deleted`-lifecycle rows and the `@local` grants should be removed from the store or kept as history. Current state keeps them; `export-manifest` and `reconcile` ignore deleted resources.
- Whether the remaining work stays on `authorization-system-cutover` or moves to a new branch.

## Suggested Follow-Up Documents

- A task plan for bringing the project and shared-data content into the test environment, if that direction is chosen.
- An update to the layout task plan's Progress Tracker and Definition Of Done with the 2026-09-22 host result and the outstanding `V-` items.
- An update to the authenticated-access row of [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md) once the check passes.
