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

**Provenance note:** these values were observed from the running deployment on 2026-09-22 by the operator, before the most recent service restart. `V-4.1` and `V-4.2` re-confirm them against the currently running container. No credential values or `.pgpass` contents are recorded anywhere in this document.

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

## Pending Verification

Each item below needs the deployment user or an authenticated administrator. Commands are read-only unless stated.

### `T4.1` / `T4.2` — re-confirm identity and record the deployed manifest checksum

```bash
sudo -iu test-shape-shifter.sead.se
cd ~/container
make info
podman image inspect shape-shifter:dev --format '{{.Id}}'
podman image inspect shape-shifter:dev --format '{{index .Config.Labels "org.opencontainers.image.revision"}}'
sha256sum ~/config/authorization-manifest.yaml
```

### `T4.4` / `V-4.5` — resource and grant review

```bash
scripts/authorization.sh list-resources --json
scripts/authorization.sh list-grants --json
```

Record the counts, and explain any retained `deleted` rows rather than omitting them. Every active resource must have a grant, with no active locator conflict.

### `T4.5` / `V-4.6` — audit-trail coverage

```bash
scripts/authorization.sh list-audit-events --json
```

Record the event count and the `event_type` distribution. Migration events appear with actor `migration`; later administrative mutations appear with the acting principal.

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

1. **Complete the pending verification above.** Nothing in this record should be treated as acceptance evidence until each command has been run against the currently running container and its output pasted back here.
2. **Hand this record to the user acceptance test owners.** It states what is verified and what is not; acceptance criteria are theirs to author and apply.
3. **Do not repoint production DNS or the reverse proxy.** The flip is a separate decision with its own proposal and owners.

## Risks

- **`bulgaria-arbodat-lookup-options` remains unproven.** The application lists it, but it declares the `access` driver with no data file. Whether that is intentional is unconfirmed, and UAT users may notice it before we do.
- **The rollback discards later grants.** Any grant added inside the acceptance window is lost on restore.
- **Reviewed projects may lack owners for real users.** `bruno` and `riia` own reviewed projects, but the wider user population may not. If a tester's principal owns nothing, they will see denied responses that are correct but unhelpful.
- **Shared-source grants are broad.** Every authenticated principal can read the six shared data sources. That is intended for the current manifest and worth confirming for the acceptance population.
- **Host services are reachable only as `host.docker.internal`.** A host-side connection check to a host database succeeds while the container fails, which misleads diagnosis.
- **PostgreSQL credential rotation is out of scope** by decision, covering every PostgreSQL database including the SEAD database.

## Open Decisions

- Who owns and executes user acceptance testing, and against which criteria?
- Whether `bulgaria-arbodat-lookup-options` is complete as provisioned.
- Whether the reviewed projects need owners assigned for the acceptance population, or whether access is exercised through `bruno` and `riia` only.

## Suggested Follow-Up Documents

- The user acceptance test record, owned outside this project.
- A Phase 5 task plan for the Podman deployment verification and the updated security record, once this record is complete.
