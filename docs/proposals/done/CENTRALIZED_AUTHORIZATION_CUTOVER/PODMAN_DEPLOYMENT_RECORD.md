# Podman Deployment Record

- **Status:** Complete 2026-09-23 — all five areas done: the release unit is frozen with its identity confirmed on the host, and the exposure, container-configuration, grant, proxy-identity, access, route-classification, log-review, and rollback results are recorded, with two approved exceptions. [SECURITY_CHECK.md](../../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md) carries the release result.
- **Source phase plan:** [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) - [Phase 5: Verify Podman Deployment And Update Security Record](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-5-verify-podman-deployment-and-update-security-record)
- **Source task plan:** [Phase 5 task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_5_TASK_PLAN.md)
- **Predecessor records:** [UAT-ready deployment record](./done/UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md), [Podman deployment verification handoff](./DEPLOYMENT_VERIFICATION_HANDOFF.md), [test environment cutover handoff](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md)
- **Related, not required:** [Release Cycle Evidence And Locking](../../RELEASE_CYCLE_EVIDENCE_AND_LOCKING/README.md)

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
| Area 3: Proxy identity handling and access behavior | *Area 3* below | Done |
| Area 4: Backup, restore, and rollback | *Area 4* below | Done — cited from the matching Phase 4 exercise |
| Area 5: Log review and security record | *Area 5* below | Done — with an approved exception for the PostgreSQL server log |

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

Run 2026-09-23. All three tasks passed.

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

### `T5.8` / `V-5.8` — corrected access check: passed

Run 2026-09-23 as the deployment user, with the principal password read from `~/config/authorization.env`. Transcript: `<DATA_DIR>/deployment-verification/phase-5/authenticated-access.log`.

The principal-scope block, the in-container role lookup, and the outcome:

```
== Principal scope ==
bruno holds no deployment role that grants read
riia holds project_maintainer, which grants read on every project

[denied-B] GET /api/v1/projects/Bruno-Strucke-v2-test
  as B  -> HTTP 200 (expect 200)  PASS
    note: expected privileged read through project_maintainer

Authenticated access passed.
Cross-resource isolation was verified in 1 of 2 directions.
```

All five probes behave as intended: `401` unauthenticated, `200` for the owner on his own project, concealed `404` for the other principal, `200` for a privileged read that the script now labels instead of reporting as a failure, and the administrator probe already recorded under `V-4.7`.

**This retires the Phase 4 accepted risk.** The corrected script's in-container role lookup had never executed on this host; it now has, and it produced the principal scope and the `1 of 2` count the Phase 4 record predicted. The UAT-ready deployment record carries a dated update saying so.

**Symmetric isolation is still not demonstrated**, and the script says why: `riia` holds `project_maintainer`, which reads every project by policy, so the second direction is an expected privileged read rather than evidence of isolation. That matches the Phase 4 record. Testing it needs two principals that hold no read-granting deployment role.

## Area 4: Backup, Restore, And Rollback

### `T5.10` / `V-5.10`, `V-5.11` — rollback result for the frozen unit: cited

The frozen release unit equals image ID `6a487db7…04a8`, so the exercise recorded in the UAT-ready deployment record applies to this unit and nothing has to be re-run. A result normally carries no weight for a different image; this one carries its weight because the identity matches.

| Item | Value |
| --- | --- |
| Exercise | 2026-09-22 16:48:11, from the deployment host |
| Image | `6a487db7…04a8`, revision `dbff5ab9…4f96`, equal to the running image after the exercise |
| Authorization database | restored from `authorization-20260922-164454.sqlite3`, SHA-256 `9ebf2f22…8b3e` |
| Integrity check | passed |
| Reconciliation | `Missing: 0 resources, 0 administrators, 0 grants` |
| Health after restart | `http://127.0.0.1:8012/api/v1/health` returned `200` |
| Transcript | `<DATA_DIR>/backups/rollback-exercise.log` |

**The restore was state-neutral.** The pre-rollback backup is byte-identical to the three earlier backups of the same day, so the database the exercise restored is the database that was already running. The procedure is demonstrated; authorization state did not change.

**What the citation does not cover.** The exercise ran against the same image but before this phase, so it is cited rather than repeated — if the release unit is reopened for any reason, the rollback check has to run again. And `rollback_exercise.sh` starts the container outside `shape-shifter.service`, so a standalone run leaves the unit reporting `active (exited)` while the container was recreated; `make service-restart` realigned it on 2026-09-22, and the same step would follow any future standalone run.

## Area 5: Log Review And Security Record

Swept 2026-09-23 from `/tmp`, as root. Transcripts: `log-review.log` for the sweep and `log-review-candidates.log` for the review of its candidates, both under `<DATA_DIR>/deployment-verification/phase-5/`.

### `T5.11` / `V-5.12` — host-log review: three sources clear, the PostgreSQL server log excepted

Four sources were swept for credentials, connection strings, SQL text, and filesystem paths over a 30-day window:

| Source | Lines collected | Candidate matches | Disposition |
| --- | --- | --- | --- |
| Shape Shifter container log | 1598 | 0 | Swept, no matches |
| nginx access log | 27 | 0 | Swept, no matches |
| nginx error log | 5 | 5 | All five reviewed; all non-findings |
| PostgreSQL server log | 0 | — | Not swept; approved exception below |

**The container log is the source that matters here**, because a database connection string would appear there, and it holds nothing across 1598 lines. The nginx access log is also clear.

**The five nginx error candidates are non-findings.** Each match is the word `password` inside nginx's own message `user "admin": password mismatch`, which nginx writes when it rejects a login. The word is part of the message text, not a credential, and no value follows it. The review counted zero `bearer` or `basic` token forms and zero cases of a keyword followed by `=` or `:`. The five lines, the word counts, and those two counts are filed in `log-review-candidates.log`.

The five entries are failed logins for the principal `admin` from `172.18.134.40`, the campus address the firewall admits, between 2026-09-22T10:26 and 2026-09-22T14:08. A rejected login is the expected response to a wrong password, and the entries agree with the access behaviour recorded under *Area 3*.

#### Approved exception: the PostgreSQL server log

| Field | Value |
| --- | --- |
| Owner of the excluded source | `super.sead.se`, the account that runs `supersead-postgresql-1` |
| Approved by | The Shape Shifter deployment operator, 2026-09-23 |
| Reason | The database server is shared infrastructure outside this deployment, so reading its log would mean reading other applications' queries |
| Residual risk | Limited to SQL text. The excluded source cannot carry this deployment's database password, except in the one case named below |

**Why the source sits outside this deployment.** `sead_staging` is served by `supersead-postgresql-1`, a container owned by `super.sead.se` and shared by the whole `supersead-*` stack. The Shape Shifter deployment reaches that server over the network; it does not own it. The server log therefore holds the activity of every application using the database, and sweeping it for Shape Shifter credentials would mean reading other applications' queries. It is deliberately left unread.

**Why the residual risk is limited to SQL text.** PostgreSQL does not write a password when authentication fails. It writes `FATAL: password authentication failed for user "<name>"`, which names the user and not the secret. The one way a password could reach that log is a statement that sets one, such as `ALTER ROLE ... PASSWORD ...` during a credential rotation, being captured by `log_statement`. Whether that setting is on, and whether such a statement ran inside the window, are both unverified, because the log was not read.

**What was read and what was not.** The container uses the `journald` log driver, so `podman logs` is the right tool for its output, and it returned nothing over 30 days. The server configuration is not at the image default: `/var/lib/postgresql/data/postgresql.conf` and `/var/lib/postgresql/data/log` do not exist, while `/var/log/postgresql` does exist and is owned by `root:postgres`. Those paths were identified and then deliberately left unread, by the decision recorded above.

## Limitations

- **Two values are carried, not re-read.** `make info` returned the container, port, user, and directories, but the hostname and the proxy configuration were not re-read in this pass; they come from the UAT-ready deployment record.
- **The manifest digest is locally computed.** It carries no external provenance; see the note under *Release Unit*.
- **The freeze is an operator commitment**, not a technical control. Nothing prevents a rebuild; the record relies on the operator not performing one.
- **The PostgreSQL server log was not read**, by decision. The approved exception under *Area 5* names the owner, the reason, and the residual risk.
