# Handoff: UAT-Ready Authorization Deployment

**Status:** Phase 4 complete and closed on 2026-09-22. All four task areas are done and `PH4-AC-1` to `PH4-AC-5` are met. The corrected access-check script was merged to `dev` in PR #500 and reached the deployment host at 19:09, after both recorded runs. The post-fix re-run was skipped, and the residual risk is accepted; see *Post-Fix Re-Run Skipped (Accepted Risk)*.
**Opened:** 2026-09-22
**Environment:** host `humlabsead.srv.its.umu.se`, deployment user `test-shape-shifter.sead.se` (uid/gid 1021), container `shape-shifter` published on `127.0.0.1:8012`, proxy `https://test-shape-shifter.sead.se`
**Source plans:** [Phase 4 task plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md), [Phase 3 task plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_3_TASK_PLAN.md), [Centralized Authorization System Cutover Plan](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md)

## Purpose

Record the authorization-enabled deployment on the new server so that a user acceptance test can be run against it without reading the Phase 3 archive. This record states what is verified, what is not, and how a tester exercises the system. It does not decide acceptance; that belongs to Riia Chmielowski (`riia`), the user acceptance test owner.

## Current State

This deployment runs the authorization system from the outset. The old server continues to run the previous setup, and the two never mix, so no partially enforced or mixed-identity period exists here.

### Deployment identity

| Field | Value | How it was established |
|---|---|---|
| Host | `humlabsead.srv.its.umu.se` | Deployment configuration and operator output |
| Deployment user | `test-shape-shifter.sead.se` (uid/gid 1021) | `make info` |
| Container and port | `shape-shifter` on `127.0.0.1:8012` | `make info`, loopback health check |
| Proxy | `https://test-shape-shifter.sead.se` | Deployment configuration |
| Image | `shape-shifter:dev` | `make info` |
| Image ID | `6a487db722883da0eb0c3cfdc00444c07dea1edaf7d59b15643227576acc04a8` | `podman image inspect` |
| OCI source revision | `dbff5ab95459652354c040b9d4fec6e2ead94f96` | `podman image inspect` |
| OCI version and source | `dev`, from `github`, built 2026-09-22 10:55:15Z | `podman image inspect` |
| Configuration revision | `GIT_REF=dev`, `IMAGE_NAME=shape-shifter:dev`, `GIT_REPO=https://github.com/humlab-sead/sead_shape_shifter.git` | `~/config/deployment.env` |
| Config directory | `/data/test-shape-shifter.sead.se/config` | `make info` |
| Data directory | `/data/test-shape-shifter.sead.se/container-data` | `make info` |
| Rollback decision owner | Roger Mähler | Recorded 2026-09-22 |

**Provenance note:** these values were re-confirmed against the running container on 2026-09-22: `podman image inspect` returned the image ID and revision recorded above, and `make info` returned the configured values. The deployed manifest's SHA-256 is `43c03186f708164ce9334a001c45b80c4f206fb2efa06d413dff9ad4a2cafb90`, identical to the reviewed manifest in the repository, so the running policy is the reviewed policy. No credential values or `.pgpass` contents are recorded anywhere in this document.

### Recorded backups

| Backup | SHA-256 | Note |
|---|---|---|
| `authorization-20260922-095516.sqlite3` | `9ebf2f2229807cf56ce32cc2d2a7c7fe0c67f67553c3d606833dc71cd9ae8b3e` | Earliest backup of 2026-09-22 |
| `authorization-20260922-110641.sqlite3` | `9ebf2f2229807cf56ce32cc2d2a7c7fe0c67f67553c3d606833dc71cd9ae8b3e` | Readiness backup |
| `authorization-20260922-130050.sqlite3` | `9ebf2f2229807cf56ce32cc2d2a7c7fe0c67f67553c3d606833dc71cd9ae8b3e` | Byte-identical to the readiness backup, so authorization state did not change across the image switch |
| `authorization-20260922-164454.sqlite3` | `9ebf2f2229807cf56ce32cc2d2a7c7fe0c67f67553c3d606833dc71cd9ae8b3e` | Pre-rollback backup, taken immediately before `T4.7` |

**All four backups of 2026-09-22 are byte-identical.** The authorization database has therefore not changed since 09:55:16: no grant or application-role mutation occurred after that time, and the rollback restore was state-neutral by construction. All four sit in `/data/test-shape-shifter.sead.se/container-data/backups`.

**Rollback rule:** a rollback restores the database as it stood when the backup was taken, so grants added afterwards are lost. No grant change should happen inside the acceptance window.

## Completed Work

| Check | Command | Result |
|---|---|---|
| Focused authorization suite, including the route-inventory and classification tests (`V-4.4`) | `.venv/bin/pytest backend/tests/authorization -q` | 192 passed, 1 skipped |
| Deployed revision matches this checkout | `git diff --stat dbff5ab9..HEAD -- backend src tests` | Only `container/DEPLOYMENT.md` differs, so the deployed revision's application code and tests are unchanged |
| Full backend regression | `.venv/bin/pytest backend/tests -q` | 1853 passed, 15 skipped, 1 warning (an unrelated JPype deprecation) |
| Loopback health | `curl -fsS --max-time 10 http://127.0.0.1:8012/api/v1/health` | `200`, `{"status":"healthy","version":"2.1.0","environment":"production"}`, last confirmed 2026-09-22 11:55:54Z |
| Inventory and reconciliation (Phase 3, still current) | `container/scripts/authorization.sh integrity-check` and `reconcile` | Integrity passed; `Missing: 0 resources, 0 administrators, 0 grants` |
| Provisioned content (Phase 3, still current) | Locator walk and `GET /api/v1/data-sources` | 26 of 26 project locators resolve; all 6 shared data sources listed |
| Shared data source connection (Phase 3, still current) | `POST /api/v1/data-sources/sead-options/test` | `success: true`, 167 tables, 112 ms |
| Audit-trail coverage (`V-4.6`) | `scripts/authorization.sh list-audit-events --json` | 144 events from 2026-09-17 19:08 to 2026-09-22 07:45: `grant_created` 53, `application_role_created` 43, `resource_lifecycle_changed` 30, `application_role_revoked` 18; every event `allowed` |
| Release identity re-confirmed (`V-4.1`, `V-4.2`) | `make info`, `podman image inspect` | Image `shape-shifter:dev`, ID `6a487db7...04a8`, revision `dbff5ab9...4f96`, `GIT_REF=dev`, container port `8012`, uid/gid `1021/1021` |
| Deployed manifest matches the reviewed manifest (`V-4.3`) | `sha256sum ~/config/authorization-manifest.yaml` | `43c03186f708164ce9334a001c45b80c4f206fb2efa06d413dff9ad4a2cafb90`, identical to the repository copy |
| Resource inventory and grants (`V-4.5`) | `scripts/authorization.sh list-resources --json` and `list-grants --json` | 51 resources (36 active, 15 deleted) and 53 grants (47 principal, 6 `everyone`). Every active resource has at least one grant, and no grant points at a missing resource |
| Access checks with reviewed projects (`V-4.7`) | `container/scripts/verify/verify_authenticated_access.sh` and the administrator probe | Unauthenticated `401`; `bruno` reading his own project `200`; `bruno` reading `Glykou_etal_2021` concealed `404`; `riia` reading her own project `200`; `admin` listing projects `200`. The remaining probe is invalid, not a defect: see *Access-check detail*. Both runs are filed as `<DATA_DIR>/deployment-verification/phase-4/verify-authenticated-access.log` |
| Live deployment roles (`V-4.7`) | `scripts/authorization.sh list-application-roles --json` | 3 administrators (`admin`, `roger`, `rebecka`), 4 `project_maintainer` principals (`roger`, `rebecka`, `riia`, `mattias`), 5 `project_creator` plus `operator` principals, and 4 temporary-project creators |
| Pre-rollback backup (`V-4.8`) | `scripts/authorization.sh backup`, then `sha256sum` | `authorization-20260922-164454.sqlite3`, SHA-256 `9ebf2f22…8b3e`, byte-identical to all three earlier backups of the day |
| Rollback exercise (`V-4.9`) | `scripts/verify/rollback_exercise.sh --image shape-shifter:dev --authorization-backup … --manifest ~/config/authorization-manifest.yaml --evidence-dir … --yes` | Passed: integrity passed, reconciliation `Missing: 0 resources, 0 administrators, 0 grants`, recorded image restarted, running image ID equals the recorded image ID, health `200` |
| Service supervision restored after the rollback | `make service-restart`, then loopback health | `Service restarted`; `{"status":"healthy","version":"2.1.0","environment":"production","timestamp":"2026-09-22T14:55:32.576269Z"}` |
| Probe-script role handling corrected | `bash -n`, `shellcheck -S warning`, a local harness against a stand-in proxy, and the extracted role-lookup snippet run against a real authorization store | See *Access-check detail*. The snippet returned `project_maintainer` for `riia`, nothing for `bruno`, and `admin` for `admin`, matching the deployment's role shape. The correction was merged to `dev` in PR #500 and synced to the target with `container/scripts/deploy/sync-to-deploy`, so the deployment host now carries the corrected script; no image rebuild was needed |
| Evidence logs filed | Copied from gitignored `tmp/` into the deployment evidence directory, plus the access-check transcript recovered from the session record | `list-audit-events.log`, `list-resources.log`, `list-grants.log`, and `verify-authenticated-access.log` are under `<DATA_DIR>/deployment-verification/phase-4/` |
| Tester accounts decided | Decision recorded 2026-09-22 | **No grant changes.** Testers use a gatekeeper account (`roger`, `rebecka`, `riia`, `mattias`, each seeing all 26 projects) or `bruno` (6). The four accounts that own no reviewed project are not used for content acceptance. This matches reviewed Decisions 7, 8, and 10, so the manifest checksum, the backup lineage, and the rollback position all stay valid |
| `bulgaria-arbodat-lookup-options` removed | `rm -f` on the deployment-host definition | The directory holds five definitions and the application lists five. See *Shared data source decision* |

### Resource inventory detail

All 32 reviewed manifest locators (26 project, 6 shared data source) are active, so no reviewed resource is missing. Four further resources are active that are **not** in the reviewed manifest:

- `verification-containment-20260918121347-3074400`
- `verification-containment-20260918122102-3084527`
- `verification-containment-20260918122806-3094124`
- `verification-containment-20260918123353-3101909`

They are temporary verification projects from 2026-09-18 that were never removed. Nineteen `verification-containment-*` resources exist in total; fifteen are deleted and these four are active.

**Ownership holds.** Every active resource has at least one grant: the 26 reviewed projects each have one `owner` grant, the 6 shared data sources each have an `everyone`/`authenticated` `reader` grant, and each of the four leftovers has an `owner` grant to its artificial `…-creator@local` principal. Two of the four also carry `viewer` grants to `bruno` and `riia`, which are the two later mutations the audit trail records. No active resource is unowned, so `PH4-AC-5` is not violated.

**The four leftovers are invisible to every principal, administrators included.** The stored locator is the bare name `verification-containment-20260918121347-3074400`, but the project on disk sits at `verification-projects/verification-containment-20260918121347-3074400`, and `ProjectNameMapper.to_api_name` turns that path into `verification-projects:verification-containment-20260918121347-3074400`. `ProjectService.list_authorized_projects` looks the resource up by that name, finds nothing, and omits the project from the list for everyone. `GET /api/v1/projects/{name}` uses the same lookup, so the colon-qualified name returns `404` and the bare name resolves authorization but has no project content to load. The four records are therefore inert orphan authorization records that grant access to a project name no project uses. They are not visible clutter, and no action is needed for acceptance.

**Audit trail and the cleanup claim.** All 30 `resource_lifecycle_changed` events are dated 2026-09-18, and none is dated 2026-09-22. The current audit trail therefore does not corroborate the Phase 3 handoff's statement that four temporary projects were deleted on 2026-09-22. A rollback restore rewrites the whole database, so a later restore could have reverted both the deletions and their audit events; the sequence is not reconstructed here, and the observable state is what this record uses.

### Audit-trail detail

- **Migration is covered.** Actor `migration` wrote 34 events in a 78 ms window at 2026-09-22T05:48:04: 26 `owner` grants, 6 `reader` grants, and 2 administrator role creations. The 26 owner and 6 reader grants match the reviewed manifest exactly, and the 2 role creations together with the earlier bootstrap-created administrator are consistent with the three recorded administrators.
- **Later mutations are covered.** Two `grant_created` events by actor `verification-check` at 07:44 to 07:45 recorded the temporary-project grants used by the earlier access check.

### Access-check detail

The check ran twice on 2026-09-22 through the proxy with `bruno` as principal A and `riia` as principal B, using reviewed projects `Bruno-Strucke-v2-test` and `Glykou_etal_2021`: at 16:37 local from a terminal prompt, and at 17:01 local with the passwords supplied through the environment. Both runs produced identical output. The raw transcript of both is filed as `<DATA_DIR>/deployment-verification/phase-4/verify-authenticated-access.log`. It predates the corrected script, which reached the host at 19:09.

| Probe | Status | Expected |
|---|---|---|
| Unauthenticated read of `Bruno-Strucke-v2-test` | `401` | `401` |
| `bruno` reads his own project | `200` | `200` |
| `bruno` reads `Glykou_etal_2021` | `404` | `404` |
| `riia` reads her own project | `200` | `200` |
| `riia` reads `Bruno-Strucke-v2-test` | `200` | `404` |
| `admin` lists projects | `200` | `200` |

**The one failing probe is a test-selection error, not an access defect.** `riia` holds the deployment role `project_maintainer`, created 2026-09-22T05:30:34 by the bootstrap actor. In `backend/app/authorization/policy.py`, `DEPLOYMENT_ROLE_ACTIONS[ApplicationRole.PROJECT_MAINTAINER]` grants `READ`, `EDIT`, and `EXECUTE`, and `AuthorizationService.is_allowed()` in `backend/app/authorization/service.py` returns `True` as soon as any deployment role allows the action, before resource grants are consulted. A maintainer therefore reads every active project by design. `bruno` holds only `project_creator` and `operator`, neither of which grants project `READ`, which is why his denial is concealed as `404` and why the check passed in that direction.

The script's documented precondition is only "neither principal is a bootstrap administrator". It predates `project_maintainer` and does not check the condition it states.

**No well-formed pair exists on the reviewed roster.** The script needs two projects, each readable by exactly one principal, with neither principal holding a role that grants read. Reviewed project owners are `bruno` (6 projects), `riia` (10), `roger` (9), and `rebecka` (1). `roger` and `rebecka` hold `admin` and `riia` holds `project_maintainer`, so `bruno` is the only reviewed owner who is not a global reader, and a pair needs two.

Live roles, confirmed from the store:

| Principal | Deployment roles |
|---|---|
| `admin` | `admin` |
| `roger` | `project_maintainer`, `admin` |
| `rebecka` | `project_maintainer`, `admin` |
| `riia` | `project_maintainer`, `project_creator`, `operator` |
| `mattias` | `project_maintainer`, `project_creator`, `operator` |
| `athena`, `bruno`, `ershad`, `phil`, `victoria` | `project_creator`, `operator` |
| four `verification-containment-…-creator@local` | `project_creator` |

`roger` and `rebecka` each hold both `project_maintainer` and `admin`. The `admin` grant is the one the reviewed manifest applies, so the `project_maintainer` grant is redundant for them.

Symmetric isolation was therefore not demonstrated with reviewed projects. The direction that matters for enforcement was: a non-privileged owner is denied another principal's project with a concealed `404`. The reverse direction is masked by an intentional global role rather than by a missing check.

`complete_test_deployment_verification.sh` provides the fixture path for a fully symmetric transcript. With `--grant-access` it grants `viewer` on two *temporary* projects, which is what produced the two `verification-check` mutations above, so it does not touch reviewed grants. It proves enforcement rather than dataset availability, and leaves two temporary projects and two fixture grants to remove afterwards. It was not run for this record.

### Rollback detail

The exercise ran on 2026-09-22 at 16:48:11 from the deployment host. Transcript: `container-data/backups/rollback-exercise.log`.

| Step | Result |
|---|---|
| Recorded image identity | `6a487db7…04a8`, revision `dbff5ab9…4f96` |
| Stop current deployment | Container removed |
| Restore authorization database | `/app/state/authorization.sqlite3` restored from the pre-rollback backup |
| Integrity check | Passed |
| Manifest reconciliation | `Missing: 0 resources, 0 administrators, 0 grants` |
| Start recorded image | Started |
| Running image ID | `6a487db7…04a8`, equal to the recorded image |
| Container state | `running` |
| Health | `http://127.0.0.1:8012/api/v1/health` returned `200` |

**The restore was state-neutral.** The pre-rollback backup is byte-identical to every other backup taken that day, so the database the exercise restored is the database that was already running. The exercise demonstrates that the procedure works without having altered authorization state.

Two messages in the transcript are expected and already documented elsewhere in this record:

- `rootless netns: kill network process: permission denied` while removing the network. `podman-compose down` still succeeds, and `up` recreates the network.
- `curl: (56) Recv failure: connection reset by peer` four times while the service was still starting. The retry loop then recorded the health check passing.

**The script does not restore service supervision.** `rollback_exercise.sh` starts the container with `podman-compose up -d` directly rather than through `shape-shifter.service`. `run_deployment_verification.sh` compensates by stopping and restarting the user service around the rollback, but running the script standalone leaves the unit untouched. The unit is `Type=oneshot` with `RemainAfterExit=yes`, so systemd continues to report it active even though the running container was recreated outside it. A service restart realigns the container with the unit's own start path.

### Tester accounts

No grant changes were made. The reviewed roster already describes who can reach what, and Decision 10 gives the SEAD core gatekeepers `project_maintainer` deliberately:

| Principal | Deployment roles | Reviewed projects visible |
|---|---|---|
| `admin`, `roger` | `admin` (plus `project_maintainer` for `roger`) | 26 |
| `rebecka` | `admin`, `project_maintainer` | 26 |
| `riia` | `project_creator`, `operator`, `project_maintainer` | 26 |
| `mattias` | `project_creator`, `operator`, `project_maintainer` | 26 |
| `bruno` | `project_creator`, `operator` | 6 |
| `phil`, `ershad`, `athena`, `victoria` | `project_creator`, `operator` | none |

The four accounts at the bottom own no reviewed project because Decisions 7 and 8 deferred collaborator grants, and because `operator` grants project-creation but no project access. They can create a project and act on it as its owner, but they cannot see the reviewed dataset, so acceptance content is exercised through a gatekeeper or through `bruno`.

Two consequences follow. Isolation cannot be experienced by any available pair while the gatekeepers hold `project_maintainer`, which is already recorded. And every non-administrator holds `operator`, which permits `manage_shared_sources` and `run_ingesters`, so acceptance can change shared data; the reviewed inventory accepts that capability explicitly.

### Shared data source decision

`bulgaria-arbodat-lookup-options` was removed on 2026-09-22 as a deployment-owner decision, after review.

- **It could not connect, and no data existed for it.** `driver: access` is valid, but the driver schema marks `filename` as `required=True` and the definition omitted it, so the loader produced a connection string with no database. The legacy data-file enumeration of 2026-09-18 lists nine files and no Bulgarian database, so the deficiency was inherited from the legacy deployment rather than introduced by the migration. Provisioning would have required a dataset that does not exist here.
- **Nothing referenced it.** Every project declares `data_sources: {}`, and no file under `container-data/projects` names the locator, so removal cannot break a project.
- **Every authenticated principal could read it** through an `everyone`/`authenticated` `reader` grant, so the deployment presented a broken source to every user.

The definition file was deleted from `container-data/shared/data-sources`; the directory now holds five definitions and the application lists five.

**Residual state.** Three records still name it, and none was changed:

- `resources/authorization/test-initial-manifest.yaml` still declares the resource and its grant.
- The deployed manifest at `~/config/authorization-manifest.yaml` is unchanged, so the manifest checksum recorded for `V-4.3` still matches the reviewed copy.
- `secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md` still lists the row.

The authorization resource is therefore an inert orphan, in the same class as the four `verification-containment-*` records, because the administration CLI has no delete or lifecycle command. Removing the three records together is a deliberate follow-up rather than part of this change: editing the manifest would invalidate the checksum this record relies on as acceptance evidence, and the archived Phase 3 record states the previous value. The Phase 3 statement that six shared data sources are listed is superseded; the deployment lists five by this decision.

## Pending Verification

Each item below needs the deployment user or an authenticated administrator. Commands are read-only unless stated.

### `T4.1` / `T4.2` — deployment identity

Complete. See *Deployment identity* and *Completed Work* above. The deployed manifest checksum matches the reviewed manifest.

### `T4.4` / `V-4.5` — resource and grant review

Complete. See *Resource inventory detail* above. Every active resource carries a grant and no grant points at a missing resource.

### `T4.5` / `V-4.6` — audit-trail coverage

Complete. See *Audit-trail detail* above. Run `scripts/authorization.sh list-application-roles` if you need to confirm which principal holds each application role, since role events do not record it.

### `T4.6` / `V-4.7` — access checks with reviewed projects

Complete. The four required outcomes are recorded in *Access-check detail*: unauthenticated `401`, owner `200`, concealed denied `404`, and administrator `200`. The script's symmetric-isolation probe reports one failure that is a test-selection error caused by `project_maintainer`, not an access defect, and no reviewed pair can supply a well-formed probe.

The probe script was corrected in the same session. It now reads each principal's deployment roles from the deployed policy before probing, prints them as a principal-scope block, expects `200` for a denied probe when the principal holds a role that grants read, labels that probe as an expected privileged read, and states how many isolation directions were actually verified. When the roles cannot be read it says so and keeps the `404` expectation, so a privileged principal still fails rather than passing silently.

The corrections passed `bash -n`, `shellcheck -S warning`, a local harness that exercised three cases (a privileged principal as B, two unprivileged principals, and an unreadable scope), and the extracted role-lookup snippet run against a real authorization store, where it returned `project_maintainer` for `riia`, nothing for `bruno`, and `admin` for `admin`.

**The deployment host now carries the corrected script.** The fix was merged to `dev` in PR #500 and synced with `container/scripts/deploy/sync-to-deploy`, so `~/container` holds it. The last host transcript is the pre-fix re-run on 2026-09-22, which had no principal-scope block and repeated the original failure. No post-fix re-run has been made, so the in-container role lookup is still unconfirmed on the target. No image rebuild is needed, because the script runs on the host.

### `T4.7` / `V-4.8`, `V-4.9` — backup and rollback exercise

Complete. The pre-rollback backup, its checksum, and the full exercise transcript are recorded in *Rollback detail*. The restore was state-neutral because the backup is byte-identical to the running database.

The supervision follow-up is done. `make service-restart` reported `Service restarted` and the loopback health check returned `{"status":"healthy","version":"2.1.0","environment":"production","timestamp":"2026-09-22T14:55:32.576269Z"}`, so the container is again aligned with the unit's own start path. A second health check at 14:59:14 returned the same healthy response.

## Post-Fix Re-Run Skipped (Accepted Risk)

The corrected access-check script (commit `5ea5e534`) was merged to `dev` in PR #500 and reached the deployment host at 2026-09-22 19:09:21, after both recorded runs. The post-fix re-run was **skipped**: the script prompts for the principal passwords, and the operator has no access to them from the workstation used for this work.

The residual risk is accepted, for these reasons:

- `PH4-AC-2` does not depend on it. The four required outcomes are demonstrated by two raw runs, filed as `<DATA_DIR>/deployment-verification/phase-4/verify-authenticated-access.log`.
- The untested part is the correction, not the deployment's access behaviour. Only the in-container role lookup is unexercised — the part that turns the expected `200` on the `denied-B` probe into a labelled privileged read.
- The correction cannot fail silently. When the role lookup fails, the script reports that the roles could not be read and keeps the `404` expectation, so a privileged principal still reports a failure rather than passing.
- The change affects evidence reporting only. It alters no authorization policy, grant, route, or image, so the recorded release identity, manifest checksum, and backup lineage are unaffected.

Accepted 2026-09-22 by Roger Mähler. A later run would only make the transcript self-labelling; it would not change a recorded result.

> **Update 2026-09-23: the risk is retired.** The corrected script was run against this deployment during Phase 5 (`T5.8`), using the principal password from `~/config/authorization.env` on the host. It passed, printed the principal scope, and reported `1 of 2` isolation directions — the in-container role lookup executed for the first time on this target. The transcript is filed as `<DATA_DIR>/deployment-verification/phase-5/authenticated-access.log`, and the result is recorded in [PODMAN_DEPLOYMENT_RECORD.md](../PODMAN_DEPLOYMENT_RECORD.md) *Area 3*. Nothing else in this record changes; the accepted risk is simply discharged.

## What Is Not Verified

- **Symmetric cross-resource isolation.** Only one of the two directions was verified, because `riia` holds `project_maintainer`. The other direction is an expected privileged read. Nothing here shows that two scope-limited principals cannot reach each other's projects, because the deployment has no such pair.
- **The corrected probe script against the live deployment.** The fix was merged to `dev` in PR #500 and reached the target at 19:09. Neither filed run used it: both pre-fix runs finished by 17:01, and the proxy recorded no request after 18:38, so the corrected script never executed against the deployment. No transcript therefore shows the in-container role lookup, the principal-scope block, or the `1 of 2` isolation-direction count. The re-run was skipped and the risk accepted; see *Post-Fix Re-Run Skipped (Accepted Risk)*. **Superseded 2026-09-23:** the run was performed in Phase 5 and the corrected script executed on the target; see the update under that section.
- **The five-source listing through the API.** The definition file is gone from `container-data/shared/data-sources`, which is the directory `GET /api/v1/data-sources` enumerates, but the listing itself was not re-run after the removal.
- **Functional correctness of the application.** This record covers authorization behaviour and operator procedures. Whether transformations, ingesters, and loaders produce correct output is not assessed here and belongs to the acceptance owners.
- **Production.** Nothing here was verified on the production host, and the production flip is out of scope.
- **PostgreSQL credential rotation.** Out of scope by decision.

## How To Exercise The Deployment

1. Open the proxy URL `https://test-shape-shifter.sead.se`. The proxy prompts for credentials, and the username is the principal ID, which is case-sensitive and must match the grant exactly. The container itself is reachable only on `127.0.0.1:8012` and rejects requests that carry no proxy identity, so every authenticated request goes through the proxy.
2. Open the project list. It shows only projects the principal may read. A principal holding a read-granting deployment role sees every project; a scope-limited principal sees only what it owns or was granted.
3. Open a project to see its entities. A project the principal cannot read returns `404` and not `403`, so an unreadable project is indistinguishable from a missing one by design.
4. Open a shared data source and run its connection test. `sead-options` is verified against the live `sead_staging` database and reports 167 tables. The application lists five sources: `bulgaria-arbodat-lookup-options` was removed on 2026-09-22 because it declared no data file.
5. Report what you observe against the acceptance criteria you were given. This record supplies evidence and does not decide acceptance.

## Key References

| Reference | Use |
|---|---|
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md) | Task and validation IDs this record satisfies |
| [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](../TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md) | Full Phase 3 evidence, for detail this record condenses |
| [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md) | The out-of-scope production move, its owners, and its open questions |
| [container/DEPLOYMENT.md](../../../../container/DEPLOYMENT.md) | Operator procedures: build, service lifecycle, health, logs, host-service access |
| [docs/OPERATIONS.md](../../../OPERATIONS.md) | Runtime configuration and operational invariants |

## Next Actions

1. **Do not treat the post-fix re-run as a closing condition.** It was skipped because the principal passwords are not available from the workstation used for this work, and the residual risk is accepted; see *Post-Fix Re-Run Skipped (Accepted Risk)*. If the passwords become available while the deployment is still in the acceptance window, running the check would replace the labelled `FAIL` line with a principal-scope block, but no acceptance criterion depends on it.
2. **Take a fresh backup when the window opens.** No grant changes follow from the tester-account decision, but acceptance can still change shared data, because every non-administrator holds `operator`. Record a backup at the point acceptance starts and add no grants during it; the existing backups are already byte-identical, so this is a checkpoint rather than a repair.
3. **Correct or confirm the Phase 3 cleanup statement.** The audit trail does not show the 2026-09-22 deletions it describes.
4. **Drop `bulgaria-arbodat-lookup-options` from the three records that still name it.** The reviewed manifest, the deployed manifest, and the inventory should lose the entry together as one reviewed change, so a future import cannot recreate the resource. This was left out of the removal deliberately, because editing the manifest invalidates the checksum acceptance relies on.
5. **Hand this record to the user acceptance test owner, Riia Chmielowski (`riia`).** It states what is verified and what is not; acceptance criteria are hers to author and apply.
6. **Do not repoint production DNS or the reverse proxy.** The flip is a separate decision with its own proposal and owners.

## Risks

- **Four orphan authorization resources exist and are inert.** `verification-containment-20260918121347-3074400`, `...122102-3084527`, `...122806-3094124`, and `...123353-3101909` are active and owned, but their stored locators are bare names while the projects on disk map to `verification-projects:…`. That mismatch hides them from the project list for every principal, administrators included, so they cannot be seen or used. They are tidiness debt rather than an acceptance problem. Cleaning them up means deleting the projects through the application, outside the acceptance window, because the CLI has no lifecycle command; see *Cleanup Deferred Until After Acceptance*.
- **The Phase 3 cleanup claim is not corroborated by the audit trail.** No `resource_lifecycle_changed` event is dated 2026-09-22. The most consistent explanation is a restore rather than a missing deletion: the database has been byte-identical since 09:55:16, and a rollback restore at `rollback-20260922-103540` rewrote it before that, so a deletion made between 09:55 and 10:35 would have been reverted together with its audit events and never reapplied. That reconstruction fits the observation but is not proven, so correct the Phase 3 handoff or explain the difference before relying on it as evidence.
- **A standalone rollback exercise leaves the service unit out of step.** The script drives `podman-compose` directly, so the container is recreated outside `shape-shifter.service` while the unit still reports `active (exited)`. Run `make service-restart` afterwards, or use `run_deployment_verification.sh`, which manages the unit itself.
- **`bulgaria-arbodat-lookup-options` was removed, but three records still name it.** The definition was deleted on 2026-09-22, so the application lists five shared data sources, yet the reviewed manifest, the deployed manifest, and the inventory still declare the resource and its grant. The authorization resource is an inert orphan, and a future manifest import would not remove it. See *Shared data source decision*.
- **Acceptance is not read-only against shared data.** Every non-administrator holds `operator`, which permits `manage_shared_sources` and `run_ingesters`, so a tester can change shared data sources. Take the backup after any grant change and before the window opens.
- **The rollback discards later grants.** Any grant added inside the acceptance window is lost on restore.
- **Most accounts see either everything or nothing, by decision.** `roger`, `rebecka`, `riia`, and `mattias` hold `project_maintainer` and read every project, so a tester using one of those accounts cannot experience isolation. The remaining accounts (`bruno`, `athena`, `ershad`, `phil`, `victoria`) hold only `project_creator` and `operator`, and of those only `bruno` owns any reviewed project, so the other four would see an empty list. Acceptance content is exercised through a gatekeeper account or through `bruno`; see *Tester accounts*.
- **The probe script previously misreported a privileged read as an isolation failure.** Corrected on 2026-09-22, merged to `dev` in PR #500, and synced to the target. `verify_authenticated_access.sh` now reads each principal's deployment roles from the deployed policy, prints a principal-scope block, expects `200` and adds a note for a denied probe whose principal holds a read-granting role, and reports how many isolation directions were verified. It still fails when the roles cannot be read and a principal turns out to be privileged. The corrected script is deployed but was never run on the target, so its in-container role lookup is unconfirmed there; the re-run was skipped and the risk accepted on 2026-09-22, see *Post-Fix Re-Run Skipped (Accepted Risk)*.
- **Shared-source grants are broad.** Every authenticated principal can read the five remaining shared data sources. That is intended for the current manifest and worth confirming for the acceptance population.
- **Host services are reachable only as `host.docker.internal`.** A host-side connection check to a host database succeeds while the container fails, which misleads diagnosis.
- **Audit events carry no correlation ID.** All 144 events have `correlation_id: null`, so an event cannot be tied to the request that caused it.
- **Application-role events do not record the principal.** `application_role_created` and `application_role_revoked` record the role as `action` and the acting principal, but leave `subject_id` null. `backend/app/authorization/repository.py::add_application_role` and `remove_application_role` confirm this, so the trail cannot answer who received or lost a role.
- **The trail records mutations, not access decisions.** Every event is an `allowed` mutation; denied requests are not audited, so the trail cannot be used to review refusals. Testers asking "can you show who was denied" will find no answer here.
- **PostgreSQL credential rotation is out of scope** by decision, covering every PostgreSQL database including the SEAD database.

## Open Decisions

Resolved on 2026-09-22:

- **The four `verification-containment-*` resources need no action.** They are inert orphan records hidden by a locator/name mismatch; see *Resource inventory detail*.
- **The probe script is fixed, merged, and deployed.** It reads deployment roles, labels a privileged read, and states how many isolation directions were verified. It was merged to `dev` in PR #500 and reached the target at 19:09.
- **The post-fix re-run is skipped and its risk accepted.** The principal passwords are not available from the workstation used for this work, so the correction has never executed against the deployment. The residual risk is accepted; see *Post-Fix Re-Run Skipped (Accepted Risk)*. Superseded 2026-09-23: the run was performed in Phase 5 and the risk is retired.
- **No symmetric isolation transcript is required.** The four required outcomes are recorded. If reviewers ask for one, produce it with real scoped grants on two reviewed projects rather than the temporary-project fixture path, which would add to the orphan pile.
- **Tester accounts: no grant changes.** Acceptance content is exercised through a gatekeeper account (`roger`, `rebecka`, `riia`, `mattias`) or `bruno`; the four accounts that own no reviewed project are not used for it. This matches reviewed Decisions 7, 8, and 10, and keeps the manifest checksum, the backup lineage, and the rollback position valid. See *Tester accounts*.
- **`bulgaria-arbodat-lookup-options` is removed, not provisioned.** The legacy file enumeration contains no Bulgarian dataset and nothing referenced the source. See *Shared data source decision*.
- **Grant sequencing, should grants ever be added.** Settle the list, grant, re-record the manifest checksum, take a fresh backup, and only then open the acceptance window, because a rollback discards anything granted afterwards.
- **User acceptance testing is owned by Riia Chmielowski (`riia`).** Assigned 2026-09-22. `riia` holds `project_maintainer`, `project_creator`, and `operator`, so that account reads every project and cannot experience cross-project isolation; see *Tester accounts*. Roger Mähler remains the rollback decision owner.

Still open:

- Whether to drop `bulgaria-arbodat-lookup-options` from the reviewed manifest, the deployed manifest, and the inventory as one reviewed change, so a future import cannot recreate the resource. Deferred until after the acceptance window, because editing the manifest changes the checksum `V-4.3` relies on; see *Cleanup Deferred Until After Acceptance*.
- Which acceptance criteria apply, and who reviews the observed results against them. Outside this record: the owner is assigned (Riia Chmielowski, `riia`), and the criteria are hers to author and apply.
- Whether to raise the audit-tooling gaps as an issue: null `correlation_id` on every event, role events that omit the principal, and unaudited denials. Not raised at this time; recorded here so the gap is not lost.

## Cleanup Deferred Until After Acceptance

Two cleanups are deliberately deferred, because each would invalidate evidence this record relies on. Run them after the acceptance window closes, never during it.

| Cleanup | Action | Evidence it would disturb |
|---|---|---|
| The four `verification-containment-*` temporary projects and their authorization records | Delete the projects through the application, then drop the orphan authorization resources | The audit trail (144 events, none dated 2026-09-22), the resource counts (`V-4.5`), and the byte-identical backup lineage (`V-4.8`) |
| `bulgaria-arbodat-lookup-options` in the reviewed manifest (`resources/authorization/test-initial-manifest.yaml`), the deployed manifest (`~/config/authorization-manifest.yaml`), and `secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md` | Drop the entry from all three together | `V-4.3`, which records the deployed manifest checksum `43c03186…fb90` as identical to the reviewed copy |

**No low-risk cleanup is available now.** Every option above either writes to the authorization store or changes a manifest checksum, so each one invalidates evidence recorded for acceptance.

**Post-acceptance sequence**

1. Close the acceptance window and stop changing shared data.
2. Take a fresh backup with `container/scripts/authorization.sh backup`, and record its path and checksum.
3. Delete the four temporary projects through the application.
4. Drop `bulgaria-arbodat-lookup-options` from the three records, so a future import cannot recreate it. This does not remove the existing orphan authorization resource: the CLI has no delete or lifecycle command, and a manifest import does not remove resources. Removing the orphan needs a direct write to the authorization store, which is why it stays deferred.
5. Re-record the manifest checksum, the resource and grant counts, and the audit-event count in this record.

## Suggested Follow-Up Documents

- The user acceptance test record, owned by Riia Chmielowski (`riia`) and kept separate from this record.
- A Phase 5 task plan for the Podman deployment verification and the updated security record, once this record is complete.
