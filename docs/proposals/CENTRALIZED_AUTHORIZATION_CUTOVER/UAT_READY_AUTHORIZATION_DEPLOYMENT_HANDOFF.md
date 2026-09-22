# Handoff: UAT-Ready Authorization Deployment

**Status:** Phase 4 complete on 2026-09-22. All four task areas are done and `PH4-AC-1` to `PH4-AC-5` are met. One step remains before this is treated as final: the corrected access-check script has not yet run on the deployment host, because the fix must first land on `dev` and reach the target through `sync-to-deploy`.
**Opened:** 2026-09-22
**Environment:** host `humlabsead.srv.its.umu.se`, deployment user `test-shape-shifter.sead.se` (uid/gid 1021), container `shape-shifter` published on `127.0.0.1:8012`, proxy `https://test-shape-shifter.sead.se`
**Source plans:** [Phase 4 task plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md), [Phase 3 task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_3_TASK_PLAN.md), [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md)

## Purpose

Record the authorization-enabled deployment on the new server so that a user acceptance test can be run against it without reading the Phase 3 archive. This record states what is verified, what is not, and how a tester exercises the system. It does not decide acceptance; that belongs to the user acceptance test owners.

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
| Access checks with reviewed projects (`V-4.7`) | `container/scripts/verify/verify_authenticated_access.sh` and the administrator probe | Unauthenticated `401`; `bruno` reading his own project `200`; `bruno` reading `Glykou_etal_2021` concealed `404`; `riia` reading her own project `200`; `admin` listing projects `200`. The remaining probe is invalid, not a defect: see *Access-check detail* |
| Live deployment roles (`V-4.7`) | `scripts/authorization.sh list-application-roles --json` | 3 administrators (`admin`, `roger`, `rebecka`), 4 `project_maintainer` principals (`roger`, `rebecka`, `riia`, `mattias`), 5 `project_creator` plus `operator` principals, and 4 temporary-project creators |
| Pre-rollback backup (`V-4.8`) | `scripts/authorization.sh backup`, then `sha256sum` | `authorization-20260922-164454.sqlite3`, SHA-256 `9ebf2f22…8b3e`, byte-identical to all three earlier backups of the day |
| Rollback exercise (`V-4.9`) | `scripts/verify/rollback_exercise.sh --image shape-shifter:dev --authorization-backup … --manifest ~/config/authorization-manifest.yaml --evidence-dir … --yes` | Passed: integrity passed, reconciliation `Missing: 0 resources, 0 administrators, 0 grants`, recorded image restarted, running image ID equals the recorded image ID, health `200` |
| Service supervision restored after the rollback | `make service-restart`, then loopback health | `Service restarted`; `{"status":"healthy","version":"2.1.0","environment":"production","timestamp":"2026-09-22T14:55:32.576269Z"}` |
| Probe-script role handling corrected | `bash -n`, `shellcheck -S warning`, a local harness against a stand-in proxy, and the extracted role-lookup snippet run against a real authorization store | See *Access-check detail*. The snippet returned `project_maintainer` for `riia`, nothing for `bruno`, and `admin` for `admin`, matching the deployment's role shape. Reaching the target needs a `dev` merge and a sync |
| Evidence logs filed | Copied from gitignored `tmp/` into the deployment evidence directory | `list-audit-events.log`, `list-resources.log`, and `list-grants.log` are under `<DATA_DIR>/deployment-verification/phase-4/` |

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

The check ran on 2026-09-22 through the proxy with `bruno` as principal A and `riia` as principal B, using reviewed projects `Bruno-Strucke-v2-test` and `Glykou_etal_2021`.

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

**The deployment host still runs the old script.** `~/container` is a synced copy maintained by `container/scripts/deploy/sync-to-deploy`, not a git checkout, and the deployment user cannot read this checkout, so the fix reaches the target only after it lands on `dev` and the tree is re-synced. A re-run on 2026-09-22 confirmed this: the output had no principal-scope block and repeated the original failure. No image rebuild is needed, because the script runs on the host.

### `T4.7` / `V-4.8`, `V-4.9` — backup and rollback exercise

Complete. The pre-rollback backup, its checksum, and the full exercise transcript are recorded in *Rollback detail*. The restore was state-neutral because the backup is byte-identical to the running database.

The supervision follow-up is done. `make service-restart` reported `Service restarted` and the loopback health check returned `{"status":"healthy","version":"2.1.0","environment":"production","timestamp":"2026-09-22T14:55:32.576269Z"}`, so the container is again aligned with the unit's own start path. A second health check at 14:59:14 returned the same healthy response.

## What Is Not Verified

- **Symmetric cross-resource isolation.** Only one of the two directions was verified, because `riia` holds `project_maintainer`. The other direction is an expected privileged read. Nothing here shows that two scope-limited principals cannot reach each other's projects, because the deployment has no such pair.
- **The corrected probe script against the live deployment.** The target's `~/container` is a synced copy updated by `container/scripts/deploy/sync-to-deploy`, not a git checkout, so the fix reaches it only after it lands on `dev` and the tree is re-synced. Until then the target runs the old script, which reports a privileged read as an isolation failure. The logic and the role-lookup snippet are verified locally, but the `podman exec` invocation of the snippet has not run on the target.
- **`bulgaria-arbodat-lookup-options`.** It cannot connect as deployed, and that failure is expected until the data source is removed or its file is provisioned.
- **Functional correctness of the application.** This record covers authorization behaviour and operator procedures. Whether transformations, ingesters, and loaders produce correct output is not assessed here and belongs to the acceptance owners.
- **Production.** Nothing here was verified on the production host, and the production flip is out of scope.
- **PostgreSQL credential rotation.** Out of scope by decision.

## How To Exercise The Deployment

1. Open the proxy URL `https://test-shape-shifter.sead.se`. The proxy prompts for credentials, and the username is the principal ID, which is case-sensitive and must match the grant exactly. The container itself is reachable only on `127.0.0.1:8012` and rejects requests that carry no proxy identity, so every authenticated request goes through the proxy.
2. Open the project list. It shows only projects the principal may read. A principal holding a read-granting deployment role sees every project; a scope-limited principal sees only what it owns or was granted.
3. Open a project to see its entities. A project the principal cannot read returns `404` and not `403`, so an unreadable project is indistinguishable from a missing one by design.
4. Open a shared data source and run its connection test. `sead-options` is verified against the live `sead_staging` database and reports 167 tables; `bulgaria-arbodat-lookup-options` fails for the reason above.
5. Report what you observe against the acceptance criteria you were given. This record supplies evidence and does not decide acceptance.

## Key References

| Reference | Use |
|---|---|
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md) | Task and validation IDs this record satisfies |
| [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md) | Full Phase 3 evidence, for detail this record condenses |
| [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md) | The out-of-scope production move, its owners, and its open questions |
| [container/DEPLOYMENT.md](../../../container/DEPLOYMENT.md) | Operator procedures: build, service lifecycle, health, logs, host-service access |
| [docs/OPERATIONS.md](../../../OPERATIONS.md) | Runtime configuration and operational invariants |

## Next Actions

1. **Land the probe-script fix on `dev`, sync the target tree, then re-run the access check.** `~/container` is a synced copy, so the fix must reach `dev` and be synced with `container/scripts/deploy/sync-to-deploy` before the target can use it. No image rebuild is needed. Record the new transcript as the `V-4.7` evidence; it should report the principal scope and `1 of 2` isolation directions.
2. **Settle the tester accounts, then apply any grants before the window opens.** Decide which account each tester uses, apply the grants, re-record the manifest checksum, and take a fresh backup. A rollback discards anything granted after the backup, so this must finish before acceptance starts.
3. **Correct or confirm the Phase 3 cleanup statement.** The audit trail does not show the 2026-09-22 deletions it describes.
4. **Decide `bulgaria-arbodat-lookup-options`.** Remove it or provision the missing file; it cannot connect as deployed.
5. **Hand this record to the user acceptance test owners.** It states what is verified and what is not; acceptance criteria are theirs to author and apply.
6. **Do not repoint production DNS or the reverse proxy.** The flip is a separate decision with its own proposal and owners.

## Risks

- **Four orphan authorization resources exist and are inert.** `verification-containment-20260918121347-3074400`, `...122102-3084527`, `...122806-3094124`, and `...123353-3101909` are active and owned, but their stored locators are bare names while the projects on disk map to `verification-projects:…`. That mismatch hides them from the project list for every principal, administrators included, so they cannot be seen or used. They are tidiness debt rather than an acceptance problem. Cleaning them up means deleting the projects through the application, outside the acceptance window, because the CLI has no lifecycle command.
- **The Phase 3 cleanup claim is not corroborated by the audit trail.** No `resource_lifecycle_changed` event is dated 2026-09-22. The most consistent explanation is a restore rather than a missing deletion: the database has been byte-identical since 09:55:16, and a rollback restore at `rollback-20260922-103540` rewrote it before that, so a deletion made between 09:55 and 10:35 would have been reverted together with its audit events and never reapplied. That reconstruction fits the observation but is not proven, so correct the Phase 3 handoff or explain the difference before relying on it as evidence.
- **A standalone rollback exercise leaves the service unit out of step.** The script drives `podman-compose` directly, so the container is recreated outside `shape-shifter.service` while the unit still reports `active (exited)`. Run `make service-restart` afterwards, or use `run_deployment_verification.sh`, which manages the unit itself.
- **`bulgaria-arbodat-lookup-options` cannot connect.** Its `driver: access` is valid, because `src/loaders/sql_loaders.py` registers `key=["ucanaccess", "access"]`. The driver schema marks `filename` as `required=True` however, the deployed file omits it, and the loader falls back to an empty path, so `create_db_uri()` produces `jdbc:ucanaccess://` with no file. No Bulgarian Access database exists in `shared-data/` either; the only Access files there are `ArchBotDaten.mdb`, `ArchBotStrukDat.mdb`, `Digidiggie_v7_kbw.accdb`, and `bugsdata_20250608.mdb`. Every sibling data source declares `filename`. A tester who opens this source will see a failure, so remove it or provision the file.
- **The rollback discards later grants.** Any grant added inside the acceptance window is lost on restore.
- **Most accounts see either everything or nothing.** `roger`, `rebecka`, `riia`, and `mattias` hold `project_maintainer` and read every project, so a tester using one of those accounts cannot experience isolation. The remaining accounts (`bruno`, `athena`, `ershad`, `phil`, `victoria`) hold only `project_creator` and `operator`, and of those only `bruno` owns any reviewed project, so the other four would see an empty project list. Choose the account for each tester deliberately.
- **The probe script previously misreported a privileged read as an isolation failure.** Corrected on 2026-09-22. `verify_authenticated_access.sh` now reads each principal's deployment roles from the deployed policy, prints a principal-scope block, expects `200` and adds a note for a denied probe whose principal holds a read-granting role, and reports how many isolation directions were verified. It still fails when the roles cannot be read and a principal turns out to be privileged. Locally tested only; the in-container lookup needs a deployment-host run to confirm.
- **Shared-source grants are broad.** Every authenticated principal can read the six shared data sources. That is intended for the current manifest and worth confirming for the acceptance population.
- **Host services are reachable only as `host.docker.internal`.** A host-side connection check to a host database succeeds while the container fails, which misleads diagnosis.
- **Audit events carry no correlation ID.** All 144 events have `correlation_id: null`, so an event cannot be tied to the request that caused it.
- **Application-role events do not record the principal.** `application_role_created` and `application_role_revoked` record the role as `action` and the acting principal, but leave `subject_id` null. `backend/app/authorization/repository.py::add_application_role` and `remove_application_role` confirm this, so the trail cannot answer who received or lost a role.
- **The trail records mutations, not access decisions.** Every event is an `allowed` mutation; denied requests are not audited, so the trail cannot be used to review refusals. Testers asking "can you show who was denied" will find no answer here.
- **PostgreSQL credential rotation is out of scope** by decision, covering every PostgreSQL database including the SEAD database.

## Open Decisions

Resolved on 2026-09-22:

- **The four `verification-containment-*` resources need no action.** They are inert orphan records hidden by a locator/name mismatch; see *Resource inventory detail*.
- **The probe script is fixed.** It reads deployment roles, labels a privileged read, and states how many isolation directions were verified.
- **No symmetric isolation transcript is required.** The four required outcomes are recorded. If reviewers ask for one, produce it with real scoped grants on two reviewed projects rather than the temporary-project fixture path, which would add to the orphan pile.
- **Grant sequencing.** Settle the tester list first, then grant, re-record the manifest checksum, and take a fresh backup; only then open the acceptance window, because a rollback discards anything granted afterwards.

Still open:

- Which account each tester uses. Maintainer accounts read every project, and `athena`, `ershad`, `phil`, and `victoria` own nothing and would see an empty list, so only `bruno` currently sees a scoped, non-empty view.
- Whether to remove `bulgaria-arbodat-lookup-options` or provision its missing file. This needs the data owner.
- Who owns and executes user acceptance testing, and against which criteria? Unassigned as of 2026-09-22; this record names Roger Mähler as the rollback owner only.
- Whether to raise the audit-tooling gaps as an issue: null `correlation_id` on every event, role events that omit the principal, and unaudited denials. The organization's OAuth restrictions block issue creation from the coding agent, so an operator must file it.

## Suggested Follow-Up Documents

- The user acceptance test record, owned outside this project.
- A Phase 5 task plan for the Podman deployment verification and the updated security record, once this record is complete.
