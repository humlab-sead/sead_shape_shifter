# Shape Shifter Operations Guide

Runbook for operators and maintainers of deployed Shape Shifter environments. The supported deployment uses rootless Podman; setup, lifecycle commands, multi-environment deployment, NGINX, and systemd procedures are documented in [container/README.md](../container/README.md) and [container/DEPLOYMENT.md](../container/DEPLOYMENT.md).

## Operational Invariants

- Run one backend worker. Project caches and in-memory singletons are process-local; multiple workers can serve stale data after writes.
- Run the container as the deployment user with rootless Podman. `userns_mode: "keep-id"` maps the host UID/GID into the container for bind-mounted data.
- Project state is file-backed YAML. Do not edit one project concurrently from multiple operator sessions.
- The application serves plain HTTP. Terminate TLS at the NGINX reverse proxy or another trusted upstream.
- NGINX is the authentication boundary. It must authenticate the user, overwrite `X-Authenticated-User` with the verified identity, and proxy to the application port.
- `/api/v1/health` is the only unauthenticated API path. Keep the application port private to the proxy host.
- Java is required when projects use MS Access sources. Install UCanAccess with `make install-ucanaccess` from `container/` when the deployment image does not already contain the required JARs.

## Deployment Entry Points

Run the deployment as a dedicated Linux user from `~/container`. The persistent data directory defaults to `~/container-data` and is controlled by `DATA_DIR`. The supported first-start sequence is:

```bash
make setup
make build
make up
make healthcheck
```

Use [container/DEPLOYMENT.md](../container/DEPLOYMENT.md) for dedicated users, lingering, multiple environments, deployment helpers, NGINX installation, systemd services, and release or branch selection. Use [container/README.md](../container/README.md) for the complete Makefile command reference.

Each environment records its repository, ref, image, port, and data directory in `container/.env`. A build from `GIT_REF=dev` produces a `shape-shifter:dev` image; keep `IMAGE_NAME` aligned with that ref before `make up`. Image labels record the source commit, ref, repository, and build date.

## Runtime Configuration

Backend settings use the `SHAPE_SHIFTER_` prefix and are loaded from `../container-data/backend.env`. The authoritative defaults are defined in `backend/app/core/config.py`.

| Variable | Default | Purpose |
|---|---|---|
| `SHAPE_SHIFTER_ENVIRONMENT` | `development` | Runtime mode. Production requires trusted-proxy authentication and a bootstrap administrator. |
| `SHAPE_SHIFTER_APPLICATION_ROOT` | current directory | Base for relative paths. |
| `SHAPE_SHIFTER_API_V1_PREFIX` | `/api/v1` | API v1 route prefix. |
| `SHAPE_SHIFTER_PROJECTS_DIR` | `projects` | Project YAML and project-managed files. |
| `SHAPE_SHIFTER_GLOBAL_DATA_DIR` | `shared/shared-data` | Shared reference data. |
| `SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR` | `shared/data-sources` | Shared uploaded data sources. |
| `SHAPE_SHIFTER_LOG_DIR` | `logs` | Application logs. |
| `SHAPE_SHIFTER_LOG_LEVEL` | `INFO` | Loguru log level. |
| `SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED` | `false` | Require the identity forwarded by NGINX. |
| `SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_HEADER` | `X-Authenticated-User` | Verified proxy identity header. |
| `SHAPE_SHIFTER_TRUSTED_PROXY_GROUPS_ENABLED` | `false` | Accept verified group IDs from the proxy. |
| `SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH` | `state/authorization.sqlite3` | Authorization SQLite database. |
| `SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS` | `[]` | Initial administrator principal IDs; required in production. |
| `SHAPE_SHIFTER_AUTHORIZATION_MEMBERSHIP_LOOKUP_URL` | `null` | Trusted membership endpoint template. |
| `SHAPE_SHIFTER_AUTHORIZATION_MEMBERSHIP_PROVIDER` | `trusted-membership-provider` | Membership provider name recorded in reviews and audit events. |
| `SHAPE_SHIFTER_AUTHORIZATION_MEMBERSHIP_LOOKUP_TIMEOUT_SECONDS` | `5.0` | Membership lookup timeout. |
| `SHAPE_SHIFTER_ALLOWED_ORIGINS` | localhost origins | Explicit CORS origins for deployed UIs. |
| `SHAPE_SHIFTER_ALLOWED_ORIGIN_REGEX` | `null` | Optional controlled CORS pattern. |
| `SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL` | `http://localhost:8000` | Reconciliation service base URL. |
| `SHAPE_SHIFTER_SIMS_SERVICE_URL` | `http://localhost:8000` | SEAD authority/SIMS service base URL. |
| `SHAPE_SHIFTER_ENABLE_FK_SUGGESTIONS` | `false` | Foreign-key candidate suggestions. |
| `SHAPE_SHIFTER_INGESTER_PATHS` | `['ingesters']` | Ingester module directories. |
| `SHAPE_SHIFTER_ENABLED_INGESTERS` | `null` | Enabled ingester keys; null means all discovered ingesters. |
| `SHAPE_SHIFTER_MATERIALIZATION_INLINE_THRESHOLD` | `20` | Row threshold for inline materialized data. |

Set `SEAD_HOST`, `SEAD_PORT`, `SEAD_DBNAME`, and `SEAD_USER` through the project data-source configuration when required. Keep PostgreSQL passwords in `../container-data/.pgpass/.pgpass` with mode `600`, not in project YAML or `backend.env`. `VITE_*` values are build-time settings in `container/.env` and require a new image build.

## Data Layout And Backups

`container/podman-compose.yml` mounts the following paths from `CONTAINER_DATA_DIR` into the application:

| Host path | Container path | Contents |
|---|---|---|
| `projects/` | `/app/projects/` | Project YAML files and project-local data. |
| `shared/` | `/app/shared/` | Shared reference data and data sources. |
| `logs/` | `/app/logs/` | Rotated application logs. |
| `output/` | `/app/output/` | Execution output. |
| `backups/` | `/app/backups/` | Pre-save project backups. |
| `.pgpass/.pgpass` | `/app/.pgpass:ro` | PostgreSQL credentials. |
| `state/` | `/app/state/` | Authorization SQLite database. |

The setup script also creates `tmp/` for disposable processing files and `backend.env` for runtime settings. Keep `backend.env` and `.pgpass/.pgpass` readable only by the deployment user. The authorization database is single-host state; do not place it on a shared network filesystem or use it from multiple application hosts.

Project saves create timestamped YAML backups before writing. Loading a project does not modify its file. Copy project backups to operator-controlled storage and retain the release, project, and backup identifiers together. Restore a project only while following the normal review and validation process.

For authorization administration, use `container/scripts/authorization.sh` from the deployment user's `container/` directory. The wrapper runs the tested CLI inside the deployed image and uses the persistent authorization database; do not edit SQLite directly because direct edits bypass audit records and final-owner protections.

Use these commands for routine review and backup:

```bash
./scripts/authorization.sh list-grants --json
./scripts/authorization.sh list-application-roles --json
./scripts/authorization.sh list-audit-events --json
./scripts/authorization.sh integrity-check
./scripts/authorization.sh backup
```

Backups are written to the persistent `backups/` directory with a timestamped
filename. Restore a backup by filename only:

```bash
./scripts/authorization.sh restore authorization-20260916-120000.sqlite3
```

Restore stops the application, restores the database in a one-shot container,
runs an integrity check, and starts the application only when both operations
succeed. If restore or validation fails, the application remains stopped for
operator review. After a successful restore, reconcile the reviewed
authorization manifest before reopening access.

## Release, Verification, And Rollback

The release workflow creates version tags and release notes but does not build or deploy images. An operator selects a branch or release tag in `container/.env`, runs `make build`, and restarts with `make restart`. Record the source ref, image digest, authorization database backup, manifest revision, and rollback owner in the deployment record.

After deployment:

```bash
make status
make healthcheck
make logs
curl -sf http://localhost:8012/api/v1/health
```

Confirm the UI loads, the project list is available, API documentation is reachable through the authenticated proxy, and an administrator, project owner, and ungranted principal receive the expected authorization results. Check the image revision label when source identity is uncertain:

```bash
podman inspect shape-shifter --format '{{index .Config.Labels "org.opencontainers.image.revision"}}'
```

### Firewall and network exposure verification

After each deployment, run `./scripts/verify_firewall.sh` from the deployment user's `container/` directory. The script prints the listeners, the firewall rules for the active backend, and the loopback and LAN-address connection checks, then prints the cross-host commands to run from a second machine. The firewall-listing step needs `sudo`; the script never changes rules or service state.

```bash
./scripts/verify_firewall.sh
```

The check fails when the backend listens on `0.0.0.0:8012` or any port other than the proxy is reachable from outside. Record the listener output, the firewall listing, and the cross-host result with the date and host.

### Container configuration re-inspection

After each deployment or image change, run `./scripts/verify_container_config.sh` from the deployment user's `container/` directory as that user, for example `sudo -u test-shape-shifter.sead.se -H bash ./scripts/verify_container_config.sh`. The script prints the mounts, the published ports, the environment variable names (never values), and the image labels and history scan, and fails on a non-loopback port, a sensitive host mount, or a writable `.pgpass` mount. It never changes the container, image, or configuration; record its output with the date and host.

To roll back, set `GIT_REF` and `IMAGE_NAME` to the last known-good release, rebuild or select the corresponding image, and run `make restart`. Keep the current authorization database unless the rollback explicitly requires restoring its recorded state. Re-run health, UI, authorization, and project-read checks after the rollback.

## Observability And References

Application logs are written under `logs/`, rotate at the configured size, and are retained according to `SHAPE_SHIFTER_LOG_RETENTION`. Fixed-entity load normalizations produce warning logs and a UI banner; inspect the listed entity, row, and column before saving normalized values. No alerting infrastructure is currently configured.

- [container/README.md](../container/README.md): Podman setup, configuration, lifecycle, and diagnostics.
- [container/DEPLOYMENT.md](../container/DEPLOYMENT.md): deployment hosts, multiple environments, NGINX, systemd, and updates.
- [DEVELOPMENT.md](DEVELOPMENT.md): local development and contributor workflow.
- [DESIGN.md](DESIGN.md): architecture and single-worker rationale.
- [DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](DATA_PROVIDER_SUBMISSION_LIFECYCLE.md): provider-submission lifecycle policy.
- [AGENTS.md](../AGENTS.md): repository commands and architecture rules.
