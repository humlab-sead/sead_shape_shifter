# Podman Deployment Record

- **Status:** In progress — Area 1 complete 2026-09-22: the release unit is frozen and its identity confirmed on the host. Areas 2–5 not started.
- **Source phase plan:** [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) - [Phase 5: Verify Podman Deployment And Update Security Record](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-5-verify-podman-deployment-and-update-security-record)
- **Source task plan:** [Phase 5 task plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_5_TASK_PLAN.md)
- **Predecessor records:** [UAT-ready deployment record](./done/UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md), [Podman deployment verification handoff](./DEPLOYMENT_VERIFICATION_HANDOFF.md), [test environment cutover handoff](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md)
- **Related, not required:** [Release Cycle Evidence And Locking](../RELEASE_CYCLE_EVIDENCE_AND_LOCKING/README.md)

## Purpose

Record the frozen release unit and the security results recorded for it, so a reader can tell what was verified about which artifact. This record grows as Phase 5 proceeds: Areas 1–5 each add a section. It does not decide acceptance.

## Freeze Declaration

Frozen on 2026-09-22 for the duration of Phase 5. The operator commits to:

- not rebuilding the image,
- not editing the authorization manifest in the reviewed repository or on the deployment host,
- not changing the deployment layout, the published port, or the proxy site.

The frozen unit is the image already verified in Phase 4 — confirmed on 2026-09-22 by the image ID, the OCI `revision` label, and the deployed manifest checksum — so the results recorded there stay citable and this phase keeps its small delta. **Reopening the release unit invalidates every result recorded here for it.**

## Release Unit

### Established in this checkout

| Field | Value | Check |
| --- | --- | --- |
| Source commit | `dbff5ab95459652354c040b9d4fec6e2ead94f96` — merge of PR #495, 2026-09-22 12:44:33 +0200 | `git log -1 dbff5ab9` (`V-5.1`) |
| Application code and tests at the frozen revision | No differences from the current branch head | `git diff --stat dbff5ab9..HEAD -- backend src tests` is empty (`V-5.1`) |
| Reviewed manifest | `resources/authorization/test-initial-manifest.yaml`, SHA-256 `43c03186f708164ce9334a001c45b80c4f206fb2efa06d413dff9ad4a2cafb90` | `sha256sum` in this checkout (`V-5.1`) |

The reviewed manifest checksum equals the value recorded for the deployed manifest under `V-4.3` in the UAT-ready deployment record. The reviewed manifest is therefore unchanged since that record, and the deployed copy was identical to it at that time.

### Confirmed on the deployment host

Read on 2026-09-22 as the deployment user. Every value below came from the commands in *Commands And Transcript*.

| Field | Value | Source |
| --- | --- | --- |
| Host | `humlabsead.srv.its.umu.se` | carried from the UAT-ready deployment record; not re-read |
| Deployment user | `test-shape-shifter.sead.se`, uid/gid `1021/1021` | `make info` |
| Container name | `shape-shifter` | `make info`, container inspect |
| Published port | `8012`, bound to `127.0.0.1` only | `make info`, container inspect |
| Proxy | `https://test-shape-shifter.sead.se` | carried from the UAT-ready deployment record; not re-read |
| Config directory | `/data/test-shape-shifter.sead.se/config` | `make info` |
| Data directory | `/data/test-shape-shifter.sead.se/container-data` | `make info` |
| Configuration revision | `GIT_REF=dev`, `IMAGE_NAME=shape-shifter:dev`, `GIT_REPO=https://github.com/humlab-sead/sead_shape_shifter.git`, `HOST_PORT=8012`, `CONTAINER_NAME=shape-shifter` | `config/deployment.env` |
| Deployed manifest | `config/authorization-manifest.yaml`, SHA-256 `43c03186f708164ce9334a001c45b80c4f206fb2efa06d413dff9ad4a2cafb90` | `sha256sum` on the host |
| Image ID (configuration digest) | `6a487db722883da0eb0c3cfdc00444c07dea1edaf7d59b15643227576acc04a8` | `podman image inspect` |
| Image manifest digest | `localhost/shape-shifter@sha256:7ff51b2b9af759f3cfa4e1d970e3acea025985aba1898e3263ae25fc8887474d` | `podman image inspect` `.RepoDigests` |
| OCI labels | revision `dbff5ab95459652354c040b9d4fec6e2ead94f96`, version `dev`, source `https://github.com/humlab-sead/sead_shape_shifter.git` | `podman image inspect` |
| Running container image | `6a487db722883da0eb0c3cfdc00444c07dea1edaf7d59b15643227576acc04a8`, equal to the image ID | `podman container inspect` |
| Runtime | Podman `5.7.0`, rootless | `make info` |

Three identifiers agree with the UAT-ready deployment record: the image ID, the OCI `revision` label, and the deployed manifest checksum. **The frozen release unit is therefore the same artifact Phase 4 verified**, so the results listed under *Checks And Results* stay citable.

**A manifest digest exists, and it is locally computed.** Phase 5 planning assumed a locally built image would report an empty `.RepoDigests`. It does not, so no substitute identity is needed and none is recorded.

Podman reports `localhost/shape-shifter@sha256:7ff51b2b9af759f3cfa4e1d970e3acea025985aba1898e3263ae25fc8887474d`, a digest over the image manifest. It differs from the image ID `6a487db7…04a8`, which is the digest of the image configuration. The identity therefore carries three identifiers: the configuration digest, the manifest digest, and the OCI `revision` label `dbff5ab9…4f96` naming the source commit.

What a registry would add is provenance, not the digest's existence. The `localhost/` repository prefix shows the image was never pushed, so nothing outside this host vouches for the manifest, and a manifest digest computed on a different host is not guaranteed to match. Treat the manifest digest as local evidence about this deployment, and the `revision` label as the identity that travels across hosts.

## Commands And Transcript

Run on 2026-09-22 as a sudo-capable operator, from `/tmp`. They cannot run from this checkout: the deployment user cannot read `/data/roger`, so `sudo -u` fails with `cannot chdir`.

The raw transcript is filed as `<DATA_DIR>/deployment-verification/phase-5/release-unit-identity.log`, next to the three `list-*.log` files filed under `phase-4/`. The working copy was `tmp/p5.1.log`, which is gitignored.

```bash
cd /tmp

# Configuration revision and the deployment target
sudo -u test-shape-shifter.sead.se -H bash -lc 'cd ~/container && make info'
sudo -u test-shape-shifter.sead.se -H cat /data/test-shape-shifter.sead.se/config/deployment.env

# Deployed manifest checksum; must equal the reviewed copy above
sudo -u test-shape-shifter.sead.se -H sha256sum /data/test-shape-shifter.sead.se/config/authorization-manifest.yaml

# Image identity: ID, digests, and the OCI labels
sudo -u test-shape-shifter.sead.se -H env XDG_RUNTIME_DIR=/run/user/1021 \
  podman image inspect shape-shifter:dev --format \
  '{{.Id}}{{"\n"}}{{json .RepoDigests}}{{"\n"}}{{index .Config.Labels "org.opencontainers.image.revision"}}{{"\n"}}{{index .Config.Labels "org.opencontainers.image.version"}}{{"\n"}}{{index .Config.Labels "org.opencontainers.image.source"}}'

# The running container must use that image, on the loopback port only
sudo -u test-shape-shifter.sead.se -H env XDG_RUNTIME_DIR=/run/user/1021 \
  podman container inspect shape-shifter --format \
  '{{.Image}}{{"\n"}}{{.Config.Image}}{{"\n"}}{{json .NetworkSettings.Ports}}'
```

Record identifiers only. Never record credential values, `.pgpass` contents, or the contents of `config/deployment.env` beyond `GIT_REF`, `IMAGE_NAME`, and `GIT_REPO`.

## Checks And Results

Each section is filled by the area that owns it.

| Area | Section | Status |
| --- | --- | --- |
| Area 1: Release unit and image identity | *Release Unit* above | Done |
| Area 2: Exposure, container configuration, grants | *Area 2* below | Partly: exposure and container configuration passed; the grant check did not run |
| Area 3: Proxy identity handling and access behavior | Not yet recorded | Not started |
| Area 4: Backup, restore, and rollback | Not yet recorded | Not started |
| Area 5: Log review and security record | Not yet recorded | Not started |

The frozen image identity matches image ID `6a487db7…04a8` from the UAT-ready deployment record, so the following results recorded there are citable for this frozen unit, and only the genuinely new checks need to run:

| Result | Where recorded |
| --- | --- |
| Route inventory and classification: 192 passed, 1 skipped | *Completed Work* (`V-4.4`) |
| Resource and grant inventory: 36 active resources, 53 grants, every active resource owned | *Resource inventory detail* (`V-4.5`) |
| Audit coverage: 144 events, 34 from actor `migration` | *Audit-trail detail* (`V-4.6`) |
| Access checks: `401`, owner `200`, concealed `404`, administrator `200` | *Access-check detail* (`V-4.7`) |
| Rollback exercise: integrity passed, reconciliation zero-missing, health `200` | *Rollback detail* (`V-4.9`) |

Still new in Phase 5 regardless of the match: the proxy identity-header evidence (`T5.7`), the corrected access-check script's first host run (`T5.8`), and the host-log review disposition (`T5.11`).

**Superseded by Area 2.** The loopback binding observed here was confirmed as a check result by `verify_firewall.sh` and `verify_container_config.sh`; see *Area 2* below.

## Area 2: Exposure, Container Configuration, And Grants

Run 2026-09-22 from `/tmp`, as root for the firewall check and as the deployment user for the other two. Transcript: `<DATA_DIR>/deployment-verification/phase-5/exposure-configuration-grants.log`.

### `T5.3` / `V-5.3` — network exposure and the proxy boundary: passed, host side

| Check | Result |
| --- | --- |
| Listeners | `0.0.0.0:80`, `0.0.0.0:443`, `[::]:80`, `[::]:443`, and `127.0.0.1:8012`. The backend is loopback-only |
| Firewall | nftables, `chain input` policy `drop`. Ports `80` and `443` are accepted from `172.18.134.40` only, and no rule mentions `8012` |
| Loopback health | `200` |
| LAN refusal | `172.18.134.53:8012` refused |

**Still outstanding: the cross-host leg.** The transcript prints `nc -zvw5 172.18.134.53 8012` (expect refused or timed out) and `nc -zvw5 172.18.134.53 443`. Run both from a second host. Note that `443` is accepted only from `172.18.134.40`, so a host outside that address will time out on `443` as well; run the proxy leg from `172.18.134.40`, or record that source restriction as the reason the leg cannot be exercised from an arbitrary host.

### `T5.4` / `V-5.4` — container configuration, mounts, secrets, environment: passed

| Check | Result |
| --- | --- |
| Container | `shape-shifter`, state `running`, image `localhost/shape-shifter:dev` |
| Port publication | `{"8012/tcp":[{"HostIp":"127.0.0.1","HostPort":"8012"}]}`, loopback-only |
| Mounts | Eight, matching the documented set: `projects`, `shared`, `logs`, `output`, `backups`, `tmp`, and `state` read-write, and `.pgpass` read-only. No unexpected mount, and no sensitive host path mounted writable |
| Image labels | revision `dbff5ab9…4f96`, created `2026-09-22T10:54:49Z`, title `shape-shifter`, version `dev`, source repository, built with buildah `1.42.1` |
| Image history | No credential-like text |
| Environment | Variable names listed, values never printed |

**The one warning is a false positive.** The scan flags `GPG_KEY` as a credential-like variable name. It is one of the standard variables of the official Python base image, alongside `PYTHON_VERSION` and `PYTHON_SHA256`, and is used to verify the Python source tarball during the image build. It is not a deployment credential and holds no project secret. It appears in the image environment and therefore in the container's, which is expected for an inherited base-image variable. No action needed; recorded so the warning is not raised again as a finding.

### `T5.5` / `V-5.5` — PostgreSQL grants and store placement: partly done

The authorization store checks passed: `container-data/state/authorization.sqlite3`, owner `test-shape-shifter.sead.se` (1021), mode `600`, size 106496 bytes. It sits inside the data directory, not in the project, log, or shared-data trees.

The role verification did not run:

```
psql: error: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: No such file or directory
```

**That is a command error, not a deployment finding.** `verify_postgres_grants.sh` ran on the host with no `--host` or `--port`, so libpq defaulted to a local Unix socket, where no PostgreSQL server listens. The database is reached over the network, and the deployment passes `SEAD_HOST`, `SEAD_PORT`, and `SEAD_DBNAME` to the container through `config/backend.env`.

Two ways to close it:

1. Re-run with the database's host-visible address and port, and point `PGPASSFILE` at `<CONFIG_DIR>/.pgpass/.pgpass`. The password file matches on host, port, database, and user, and wildcards are allowed in every field except the password, so use the host string the file is keyed on.
2. If the database is administered separately, the database administrator's grant result is an acceptable input. The phase plan's task-plan handoff permits it, and grants live in the database rather than in the image, so the result does not depend on the frozen image identity.

## Limitations

- **Two values are carried, not re-read.** `make info` returned the container, port, user, and directories, but the hostname and the proxy configuration were not re-read in this pass; they come from the UAT-ready deployment record.
- **The manifest digest is locally computed.** It carries no external provenance; see the note under *Release Unit*.
- **The freeze is an operator commitment**, not a technical control. Nothing prevents a rebuild; the record relies on the operator not performing one.
