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
| Area 2: Exposure, container configuration, grants | *Area 2* below | Passed, with an accepted exception for the cross-host probe |
| Area 3: Proxy identity handling and access behavior | *Area 3* below | `T5.7` and `T5.9` passed; `T5.8` prepared |
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

Run 2026-09-22 from `/tmp`, as root for the firewall check and as the deployment user for the other two. Transcripts: `exposure-configuration-grants.log` and `postgres-grants.log` under `<DATA_DIR>/deployment-verification/phase-5/`.

### `T5.3` / `V-5.3` — network exposure and the proxy boundary: passed, host side

| Check | Result |
| --- | --- |
| Listeners | `0.0.0.0:80`, `0.0.0.0:443`, `[::]:80`, `[::]:443`, and `127.0.0.1:8012`. The backend is loopback-only |
| Firewall | nftables, `chain input` policy `drop`. Ports `80` and `443` are accepted from `172.18.134.40` only, and no rule mentions `8012` |
| Loopback health | `200` |
| LAN refusal | `172.18.134.53:8012` refused |

**The cross-host probe: accepted exception.** No second host is available for an off-host probe. The project has already accepted this case once, in the test environment cutover record under *Same-LAN exception acceptance*: accepted 2026-09-22 by Roger Mähler, who is also the named approver for exceptions to unavailable checks, on the grounds that loopback-only publication, a default-drop firewall policy, and external HTTPS reachability are the compensating checks. The same terms apply here, with these results for the frozen unit:

| Compensating check | Result |
| --- | --- |
| Backend published on loopback only | `ss -ltn` shows `127.0.0.1:8012` and no listener on `172.18.134.53`; the container publishes `{"8012/tcp":[{"HostIp":"127.0.0.1","HostPort":"8012"}]}` |
| LAN probe from the host | `172.18.134.53:8012` refused |
| Firewall policy | nftables input policy `drop`, ending in `reject with icmp admin-prohibited`, with no rule naming `8012` |
| External reachability | `test-shape-shifter.sead.se` resolves to `130.239.34.54`; HTTPS reachability was verified on 2026-09-22 in the Phase 3 record |

Accepted 2026-09-23 by Roger Mähler. `PH5-AC-2` is met by the listener, firewall, and LAN-refusal results above; the off-host probe is an additional confirmation, not the criterion.

**What the exception does not prove, and why the printed probe is weak anyway.** The script's probe targets `172.18.134.53:8012`, but `8012` is bound to loopback only, so a refusal from any source is explained by the binding rather than by the firewall. Running it from a second LAN host would not isolate the firewall rule. The probe that *would* isolate it needs a source on the target LAN other than `172.18.134.40`, because `443` is bound on every interface and accepted from that address alone. Neither source is available here.

**Topology, observed 2026-09-23.** This host is `172.18.134.53/27` on `ens33`; `172.18.134.40` is a directly attached neighbour and the only permitted source for `80` and `443`; and `test-shape-shifter.sead.se` resolves to `130.239.34.54`, which is not on this host. The public path therefore reaches nginx here through the campus NAT at `172.18.134.40` — the deployed site file names it as such — and an internal LAN probe does not exercise the public path at all.

**How to retire the exception.** No second LAN host is needed for the strongest substitute: probe the public address from an off-LAN machine — the health route for `200`, a protected route for `401`, and `nc -zvw5 130.239.34.54 8012` for a refusal. File that transcript and this exception can be replaced by a result.

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

### `T5.5` / `V-5.5` — PostgreSQL grants and store placement: passed

Run 2026-09-22 as the deployment user, host-side against `127.0.0.1:9023`.

| Check | Result |
| --- | --- |
| Role `sead_ro` in `sead_staging`, schema `public` | Read-only. `SELECT` works on every relation, and the role has no elevated attributes (`rolsuper`, `rolcreatedb`, `rolcreaterole`, `rolreplication`, `rolbypassrls` are all false), no memberships, no owned objects, and no write or privilege-management access |
| `rolinherit` | `t`, inert while the account holds no memberships, matching the Phase 3 record |
| Authorization store | `container-data/state/authorization.sqlite3`, owner `test-shape-shifter.sead.se` (1021), mode `600`, size 106496 bytes, inside the data directory |

**The first attempt failed on a command error, and the reason is worth keeping.** `verify_postgres_grants.sh` ran from the host with no `--host` or `--port`, so libpq used a local Unix socket, where no server listens. `config/backend.env` sets `SEAD_HOST=host.docker.internal`, which resolves only inside the container, so a host-side run needs the address this host uses for the same server. The host listens on `9023`, and libpq matches a password-file entry on host, port, database, and user, so the retry used `--host 127.0.0.1 --port 9023` with a temporary password-file copy whose host field was rewritten from `host.docker.internal`. Nothing about the deployment changed.

**Adjacent observation, outside `PH5-AC-2`.** The host has a wildcard listener on the database port: `ss -ltn` reported `LISTEN 0 4096 *:9023 *:*`, and the check connected to it successfully as `sead_ro` against `sead_staging`. The input chain drops by default, accepts loopback, and contains no rule for `9023`, so the port is reachable only over loopback from the host, and the container reaches it as `host.docker.internal:9023`. The firewall is therefore the only control shielding a database port that is bound on every interface; the exact packet path the container uses was not traced here, and the intended posture is worth confirming.

## Area 3: Proxy Identity Handling And Access Behavior

Started 2026-09-23. `T5.7` and `T5.9` passed; `T5.8` is prepared and waits on the principal passwords.

### `T5.7` / `V-5.7` — proxy replaces the identity header: passed

The deployed site is `/etc/nginx/sites-available/test-shape-shifter.sead.se`, and `/etc/nginx/sites-enabled/test-shape-shifter.sead.se` is a symlink to it, so the reviewed file is the enabled one. Read as the operator on 2026-09-23. The two steps of `V-5.7` that need root, `nginx -t` and `nginx -T`, were not run.

| Finding | Detail |
| --- | --- |
| Authentication | `auth_basic "Shape Shifter"` with `auth_basic_user_file /etc/nginx/htpasswd/shape-shifter`, on the whole `443` server block, so `/api/v1/docs` and `/api/v1/openapi.json` are covered. The only `auth_basic off` is the ACME location on the plain-HTTP block, which serves certificate renewal and proxies nothing |
| Identity header | `proxy_set_header X-Authenticated-User $remote_user;` — `$remote_user` is set by `auth_basic`, so the value is server-derived, and `proxy_set_header` replaces a client-supplied header of the same name |
| Group header | `proxy_set_header X-Authenticated-Groups $authz_groups;` — `$authz_groups` comes from `map $remote_user { include /etc/nginx/authz/groups.d/*.conf; }`, so the key is the authenticated user again, not the request |
| Upstream | `upstream shape_shifter_test { server 127.0.0.1:8012; }` |
| Elsewhere | A recursive search of `/etc/nginx` found no other reference to either header. Two files could not be read: `authz/groups.d/shape-shifter.conf` and `ssl/selfsigned.key`. The first is included inside a `map` block and can hold only map entries; the second is a private key. Neither can carry `proxy_set_header` |
| Other | TLS 1.2 and 1.3 only; HSTS, `X-Content-Type-Options: nosniff`, and `X-Frame-Options: SAMEORIGIN` on every response |

**What this establishes.** A client cannot choose the identity the backend trusts: both headers the backend reads are replaced from server-side values on every proxied request, which is what `PH5-AC-3` asks for.

**What it does not establish.** The effective configuration as nginx resolves it. `sudo nginx -t` and `sudo nginx -T` remain available if a reviewer wants that dump; the symlink and the exhaustive search above already show that no other file overrides these headers.

### `T5.9` / `V-5.9` — route classification at the frozen revision: passed

`.venv/bin/pytest backend/tests/authorization -q` returned 192 passed, 1 skipped, 0 failed, exit 0. It ran at branch head rather than at `dbff5ab9`, which is equivalent here because `git diff --stat dbff5ab9..HEAD -- backend src tests` is empty, so the tested code and tests are identical to the frozen revision.

### `T5.8` / `V-5.8` — corrected access check: prepared

The corrected script takes the principal passwords through `PRINCIPAL_A_PASSWORD` and `PRINCIPAL_B_PASSWORD`. They are readable on the deployment host in `~/config/authorization.env`: `AUTH_PASSWORD` covers the principals named in `AUTH_USERS`, and `ADMIN_AUTH_PASSWORD` covers the administrator. That supersedes the Phase 4 conclusion that the passwords were unavailable — they are unavailable from the workstation, not from the host — so this run can retire the Phase 4 accepted risk instead of carrying it forward.

## Limitations

- **Two values are carried, not re-read.** `make info` returned the container, port, user, and directories, but the hostname and the proxy configuration were not re-read in this pass; they come from the UAT-ready deployment record.
- **The manifest digest is locally computed.** It carries no external provenance; see the note under *Release Unit*.
- **The freeze is an operator commitment**, not a technical control. Nothing prevents a rebuild; the record relies on the operator not performing one.
