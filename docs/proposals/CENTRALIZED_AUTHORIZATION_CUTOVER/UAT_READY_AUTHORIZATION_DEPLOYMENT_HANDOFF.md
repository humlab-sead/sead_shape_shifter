# Handoff: UAT-Ready Authorization Deployment

**Status:** Phase 4 in progress. Deployment identity recorded; target-side re-verification and procedure exercises pending.
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
| `authorization-20260922-110641.sqlite3` | `9ebf2f2229807cf56ce32cc2d2a7c7fe0c67f67553c3d606833dc71cd9ae8b3e` | Readiness backup |
| `authorization-20260922-130050.sqlite3` | `9ebf2f2229807cf56ce32cc2d2a7c7fe0c67f67553c3d606833dc71cd9ae8b3e` | Byte-identical to the readiness backup, so authorization state did not change across the image switch |

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
| Resource inventory (`V-4.5`, grants pending) | `scripts/authorization.sh list-resources --json` | 51 records: 36 active (30 project, 6 shared data source), 15 deleted. All 32 reviewed manifest locators are active |

### Resource inventory detail

All 32 reviewed manifest locators (26 project, 6 shared data source) are active, so no reviewed resource is missing. Four further resources are active that are **not** in the reviewed manifest:

- `verification-containment-20260918121347-3074400`
- `verification-containment-20260918122102-3084527`
- `verification-containment-20260918122806-3094124`
- `verification-containment-20260918123353-3101909`

They are temporary verification projects from 2026-09-18 that were never removed. Nineteen `verification-containment-*` resources exist in total; fifteen are deleted and these four are active. Whether case users should see them, and whether to remove them, is an open decision below.

**Audit trail and the cleanup claim.** All 30 `resource_lifecycle_changed` events are dated 2026-09-18, and none is dated 2026-09-22. The current audit trail therefore does not corroborate the Phase 3 handoff's statement that four temporary projects were deleted on 2026-09-22. A rollback restore rewrites the whole database, so a later restore could have reverted both the deletions and their audit events; the sequence is not reconstructed here, and the observable state is what this record uses.

### Audit-trail detail

- **Migration is covered.** Actor `migration` wrote 34 events in a 78 ms window at 2026-09-22T05:48:04: 26 `owner` grants, 6 `reader` grants, and 2 administrator role creations. The 26 owner and 6 reader grants match the reviewed manifest exactly, and the 2 role creations together with the earlier bootstrap-created administrator are consistent with the three recorded administrators.
- **Later mutations are covered.** Two `grant_created` events by actor `verification-check` at 07:44 to 07:45 recorded the temporary-project grants used by the earlier access check.

## Pending Verification

Each item below needs the deployment user or an authenticated administrator. Commands are read-only unless stated.

### `T4.1` / `T4.2` — deployment identity

Complete. See *Deployment identity* and *Completed Work* above. The deployed manifest checksum matches the reviewed manifest.

### `T4.4` / `V-4.5` — grant review

Resource review is complete; grant review remains:

```bash
scripts/authorization.sh list-grants --json
```

Confirm that each of the four active `verification-containment-*` resources above carries at least one grant, so that no active resource is unowned.

### `T4.5` / `V-4.6` — audit-trail coverage

Complete. See *Audit-trail detail* above. Run `scripts/authorization.sh list-application-roles` if you need to confirm which principal holds each application role, since role events do not record it.

### `T4.6` / `V-4.7` — access checks with reviewed projects

`bruno` and `riia` both own reviewed projects and neither is a bootstrap administrator, so they satisfy the script's requirement:

```bash
sudo -u test-shape-shifter.sead.se -H bash container/scripts/verify/verify_authenticated_access.sh \
  --base-url https://test-shape-shifter.sead.se \
  --principal-a bruno --principal-b riia \
  --project-a Bruno-Strucke-v2-test --project-b Glykou_etal_2021
```

Then the administrator probe:

```bash
curl -fsS -u admin https://test-shape-shifter.sead.se/api/v1/projects -o /dev/null -w '%{http_code}\n'
```

Expected: unauthenticated `401`, allowed `200`, concealed denied `404`, administrator `200`.

### `T4.7` / `V-4.8`, `V-4.9` — backup and rollback exercise

```bash
cd ~/container
scripts/authorization.sh backup
sha256sum /data/test-shape-shifter.sead.se/container-data/backups/<new-backup>.sqlite3
scripts/verify/rollback_exercise.sh \
  --image shape-shifter:dev \
  --authorization-backup <retained-backup>.sqlite3 \
  --manifest ~/config/authorization-manifest.yaml \
  --evidence-dir /data/test-shape-shifter.sead.se/container-data/backups \
  --yes
```

The script leaves the service stopped when a step fails. Redeploy the recorded release afterwards and confirm health.

## Key References

| Reference | Use |
|---|---|
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md) | Task and validation IDs this record satisfies |
| [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md) | Full Phase 3 evidence, for detail this record condenses |
| [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md) | The out-of-scope production move, its owners, and its open questions |
| [container/DEPLOYMENT.md](../../../container/DEPLOYMENT.md) | Operator procedures: build, service lifecycle, health, logs, host-service access |
| [docs/OPERATIONS.md](../../../OPERATIONS.md) | Runtime configuration and operational invariants |

## Next Actions

1. **Decide the four active verification projects.** Remove them, or record why UAT should tolerate them, and say which. This is the first item because it is visible to testers.
2. **Complete the pending verification above**, starting with `list-grants --json`. Nothing in this record should be treated as acceptance evidence until each command has been run against the currently running container and its output recorded here.
3. **Correct or confirm the Phase 3 cleanup statement.** The audit trail does not show the 2026-09-22 deletions it describes.
4. **Hand this record to the user acceptance test owners.** It states what is verified and what is not; acceptance criteria are theirs to author and apply.
5. **Do not repoint production DNS or the reverse proxy.** The flip is a separate decision with its own proposal and owners.

## Risks

- **Four stale verification projects are active.** `verification-containment-20260918121347-3074400`, `...122102-3084527`, `...122806-3094124`, and `...123353-3101909` are active but are not in the reviewed manifest. Testers will see them, and they carry grants to artificial `@local` principals and to `bruno` and `riia`. Resolve or explicitly accept them before the acceptance run.
- **The Phase 3 cleanup claim is not corroborated by the audit trail.** No `resource_lifecycle_changed` event is dated 2026-09-22. Correct the Phase 3 handoff or explain the difference before relying on it as evidence.
- **`bulgaria-arbodat-lookup-options` remains unproven.** The application lists it, but it declares the `access` driver with no data file. Whether that is intentional is unconfirmed, and UAT users may notice it before we do.
- **The rollback discards later grants.** Any grant added inside the acceptance window is lost on restore.
- **Reviewed projects may lack owners for real users.** `bruno` and `riia` own reviewed projects, but the wider user population may not. If a tester's principal owns nothing, they will see denied responses that are correct but unhelpful.
- **Shared-source grants are broad.** Every authenticated principal can read the six shared data sources. That is intended for the current manifest and worth confirming for the acceptance population.
- **Host services are reachable only as `host.docker.internal`.** A host-side connection check to a host database succeeds while the container fails, which misleads diagnosis.
- **Audit events carry no correlation ID.** All 144 events have `correlation_id: null`, so an event cannot be tied to the request that caused it.
- **Application-role events do not record the principal.** `application_role_created` and `application_role_revoked` record the role as `action` and the acting principal, but leave `subject_id` null. `backend/app/authorization/repository.py::add_application_role` and `remove_application_role` confirm this, so the trail cannot answer who received or lost a role.
- **The trail records mutations, not access decisions.** Every event is an `allowed` mutation; denied requests are not audited, so the trail cannot be used to review refusals. Testers asking "can you show who was denied" will find no answer here.
- **PostgreSQL credential rotation is out of scope** by decision, covering every PostgreSQL database including the SEAD database.

## Open Decisions

- Whether the four active `verification-containment-*` projects should be deleted before acceptance, or accepted as visible clutter.
- Who owns and executes user acceptance testing, and against which criteria?
- Whether `bulgaria-arbodat-lookup-options` is complete as provisioned.
- Whether the reviewed projects need owners assigned for the acceptance population, or whether access is exercised through `bruno` and `riia` only.

## Suggested Follow-Up Documents

- The user acceptance test record, owned outside this project.
- A Phase 5 task plan for the Podman deployment verification and the updated security record, once this record is complete.
