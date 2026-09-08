# Shape Shifter - Operations Guide

Runbook for operators and maintainers of deployed Shape Shifter environments.

---

## Environments

| Environment | Purpose                      | Branch           | Port |
|-------------|------------------------------|------------------|------|
| Production  | Live service on `sead-tools` | `main`           | 8012 |
| Development | Local developer instances    | `dev` or feature | 8012 |

Production runs on the `sead-tools` host under the `sead` user. The canonical deploy directory is `/home/sead/sead-tools/sead_shape_shifter`.

---

## Operational Assumptions and Invariants

- **Single worker only.** The backend must run with `--workers 1`. In-memory state (project cache, singletons) is per-process; multiple workers each maintain independent caches and will silently serve stale data after writes. Multiple workers require a shared state backend (Redis or database) before they can be enabled.
- **Non-root container user.** The container runs as `shapeshifter` (UID 1002, GID 33 / `www-data`). Host volume mounts must be owned by the same UID/GID.
- **File-backed state.** All projects are YAML files on disk. There is no database for project state. Projects must not be edited simultaneously by more than one operator.
- **No built-in TLS.** TLS termination is expected upstream (reverse proxy or tunnel). The container exposes plain HTTP on port 8012.
- **Nginx is the authentication boundary.** Nginx must authenticate the user, overwrite `X-Authenticated-User` with `$remote_user`, and proxy to the loopback-only backend port. FastAPI rejects protected requests without this header and binds editing sessions to its value.
- **Health is the only unauthenticated API path.** `/api/v1/health` is allowed without the proxy identity for container health checks. Do not expose port 8012 beyond the nginx host.
- **Java required at runtime.** MS Access support (UCanAccess) requires a JRE (`default-jre-headless` is included in the production image).

---

## Configuration and Secrets

### Runtime environment variables

All backend settings use the `SHAPE_SHIFTER_` prefix and are loaded from `docker/data/backend.env` via `env_file` in `docker-compose.yml`.

Runtime variables:

| Variable                                         | Default                 | Purpose                                                              |
|--------------------------------------------------|-------------------------|----------------------------------------------------------------------|
| `SHAPE_SHIFTER_APPLICATION_ROOT`                 | __cwd__                 | Root Folder for resolving relative paths                             |
| `SHAPE_SHIFTER_ENVIRONMENT`                      | `development`           | Environment mode: `development`, `production`, or `test`             |
| `SHAPE_SHIFTER_API_V1_PREFIX`                    | `/api/v1`               | URL prefix for API v1 endpoints                                      |
| `SHAPE_SHIFTER_PROJECTS_DIR`                     | `projects`              | Folder for project YAML files (resolved under `APPLICATION_ROOT`)    |
| `SHAPE_SHIFTER_GLOBAL_DATA_DIR`                  | `shared/shared-data`    | Folder for shared reference data (resolved under `APPLICATION_ROOT`) |
| `SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR`           | `shared/data-sources`   | Folder for shared data sources (resolved under `APPLICATION_ROOT`)   |
| `SHAPE_SHIFTER_LOG_DIR`                          | `logs`                  | Folder for log files (resolved under `APPLICATION_ROOT`)             |
| `SHAPE_SHIFTER_LOG_LEVEL`                        | `INFO`                  | Loguru log level                                                     |
| `SHAPE_SHIFTER_LOG_FILE_ENABLED`                 | `true`                  | Enable file-based logging                                            |
| `SHAPE_SHIFTER_LOG_CONSOLE_ENABLED`              | `true`                  | Enable console logging                                               |
| `SHAPE_SHIFTER_LOG_ROTATION`                     | `10 MB`                 | Log file rotation size                                               |
| `SHAPE_SHIFTER_LOG_RETENTION`                    | `30 days`               | Log file retention period                                            |
| `SHAPE_SHIFTER_LOG_COMPRESSION`                  | `zip`                   | Log file compression format                                          |
| `SHAPE_SHIFTER_LOG_FILTER_FRAMEWORK_FRAMES`      | `true`                  | Filter framework frames from tracebacks                              |
| `SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED`        | `false`                 | Require an identity forwarded by nginx; enabled by Docker deployment  |
| `SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_HEADER`         | `X-Authenticated-User` | Header containing the nginx-authenticated username                    |
| `SHAPE_SHIFTER_TRUSTED_PROXY_GROUPS_ENABLED`     | `false`                | Accept verified group IDs from the trusted proxy; disabled until a trusted group source is configured |
| `SHAPE_SHIFTER_TRUSTED_PROXY_GROUPS_HEADER`      | `X-Authenticated-Groups` | Comma-separated group IDs supplied by the trusted proxy              |
| `SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH`       | `state/authorization.sqlite3` | SQLite authorization database, relative to `APPLICATION_ROOT` unless absolute |
| `SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS` | `[]` | JSON array of initial administrator principal IDs; required but not automatically applied in production |
| `SHAPE_SHIFTER_AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE` | `false` | Explicitly enable authenticated-`everyone` grants; keep disabled unless approved |
| `SHAPE_SHIFTER_AUTHORIZATION_MEMBERSHIP_LOOKUP_URL` | `null` | Trusted membership endpoint template containing `{group_id}`; required for effective group review |
| `SHAPE_SHIFTER_AUTHORIZATION_MEMBERSHIP_PROVIDER` | `trusted-membership-provider` | Provider name recorded in membership review output and audit events |
| `SHAPE_SHIFTER_AUTHORIZATION_MEMBERSHIP_LOOKUP_TIMEOUT_SECONDS` | `5.0` | Timeout for each trusted membership lookup |
| `SHAPE_SHIFTER_ALLOWED_ORIGINS`                  | _(localhost only)_      | CORS origin whitelist (JSON array); set explicitly for deployed UI    |
| `SHAPE_SHIFTER_ALLOWED_ORIGIN_REGEX`             | `null`                  | Optional CORS regex; leave unset unless a controlled wildcard is required |
| `SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL`       | `http://localhost:8000` | OpenRefine reconciliation service URL                                |
| `SHAPE_SHIFTER_SIMS_SERVICE_URL`                 | `http://localhost:8000` | SEAD authority/SIMS service URL                                      |
| `SHAPE_SHIFTER_ENABLE_FK_SUGGESTIONS`            | `false`                 | Enable foreign key candidate suggestions                             |
| `SHAPE_SHIFTER_INGESTER_PATHS`                   | `["ingesters"]`         | Directories to scan for ingester modules                             |
| `SHAPE_SHIFTER_ENABLED_INGESTERS`                | `null` (all)            | Comma-separated list of ingester keys to enable (filters ingesters)  |
| `SHAPE_SHIFTER_MATERIALIZATION_INLINE_THRESHOLD` | `20`                    | Row count below which materialized data is stored inline in YAML     |

Database connection variables (used in project YAML via `${VAR}` syntax, not prefixed with `SHAPE_SHIFTER_`):

| Variable      | Default  | Purpose            |
|---------------|----------|--------------------|
| `SEAD_HOST`   | _(none)_ | SEAD database host |
| `SEAD_DBNAME` | _(none)_ | SEAD database name |
| `SEAD_USER`   | _(none)_ | SEAD database user |
| `SEAD_PORT`   | _(none)_ | SEAD database port |

### Database passwords

Use `~/.pgpass` instead of environment variables. Mount the file read-only into the container:

```
docker/data/.pgpass/.pgpass  →  /app/.pgpass:ro
```

Format: `hostname:port:database:username:password`

```
db.example.com:5432:sead_production:sead_user:password
```

### Authorization SQLite store

Configure the authorization database outside the project, log, and shared-data directories. The default value, `state/authorization.sqlite3`, resolves to `/app/state/authorization.sqlite3` in the Docker container and persists through the `docker/data/state/` bind mount.

Set these values in `docker/data/backend.env` before the first production startup:

```dotenv
SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH=state/authorization.sqlite3
SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS=["<administrator-principal-id>"]
```

The administrator principal ID must exactly match the case-sensitive identity forwarded by nginx. Production startup rejects an empty bootstrap-administrator setting, a development principal, or an authorization database path below a project, log, or shared-data directory.

The SQLite repository enables foreign keys, WAL mode, and a 5-second busy timeout, and runs schema migrations when it opens the database. It is supported for one application host only. Do not place the database on a shared network filesystem or use it from multiple application hosts; replace the repository implementation before a multi-host deployment.

The bootstrap setting is a production guard, not an automatic assignment. The repository can create bootstrap administrators only while no application roles exist, but the deployment does not invoke that method automatically. Initial administrators, resource records, and grants must be applied through the reviewed migration workflow. That procedure is documented separately before authorization enforcement cutover.

### Authorization ownership and recovery

Run authorization administration commands from the `docker/` directory. The commands operate on `/app/state/authorization.sqlite3` unless `--database` supplies another path.

#### Initial ownership assignment

Prepare a reviewed JSON manifest outside project YAML. Principal IDs must exactly match the identities supplied by nginx. Include each deployed project and shared data source, their current locators, and the required grants.

```json
{
   "administrators": ["<administrator-principal-id>"],
   "resources": [
      {
         "resource_type": "project",
         "locator": "<project-locator>",
         "grants": [{"principal_id": "<project-owner-principal-id>", "role": "owner"}]
      },
      {
         "resource_type": "shared_data_source",
         "locator": "<shared-source-locator>",
         "grants": [{"principal_id": "<shared-source-reader-principal-id>", "role": "reader"}]
      }
   ]
}
```

Copy the approved manifest to `docker/data/state/authorization-manifest.json`, then inspect it without changing the database:

```bash
docker compose exec shape-shifter python -m backend.app.scripts.authorization migrate \
   --manifest /app/state/authorization-manifest.json --dry-run
```

After review, apply it and confirm the stored records match the manifest:

```bash
docker compose exec shape-shifter python -m backend.app.scripts.authorization migrate \
   --manifest /app/state/authorization-manifest.json
docker compose exec shape-shifter python -m backend.app.scripts.authorization reconcile \
   /app/state/authorization-manifest.json
```

Manifest application is idempotent. It creates missing resource records, administrator roles, and grants without changing existing matching records. Typed grants may use `subject_type` and `subject_id`; supported types are `principal`, `group`, and authenticated `everyone` with subject ID `authenticated`. The legacy `principal_id` form remains supported for direct-principal grants.

#### Grant review and revocation

The reviewed manifest is the supported workflow for initial project ownership, shared-data-source access, and administrator access. Use `reconcile` to review whether the database contains every assignment required by that manifest. Review current typed resource grants with:

```bash
docker compose exec shape-shifter python -m backend.app.scripts.authorization list-grants
```

Assign or revoke a grant with an explicit actor and typed subject. Both commands support `--dry-run`:

```bash
docker compose exec shape-shifter python -m backend.app.scripts.authorization grant \
   --resource-type project --locator <project-locator> \
   --subject-type group --subject-id <verified-group-id> --role editor --actor <operator-principal-id>
docker compose exec shape-shifter python -m backend.app.scripts.authorization revoke \
   --resource-type project --locator <project-locator> \
   --subject-type group --subject-id <verified-group-id> --role editor --actor <operator-principal-id> --yes
```

The application does not infer group membership from request fields. Group grants remain inert until `SHAPE_SHIFTER_TRUSTED_PROXY_GROUPS_ENABLED=true` and the proxy supplies the configured group header. Authenticated-`everyone` grants remain disabled until `SHAPE_SHIFTER_AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE=true`. Broad subjects cannot receive `owner`.

For operator review, configure a trusted membership endpoint and use an explicit actor. The endpoint must return a JSON object with a `members` array of principal IDs:

```bash
docker compose exec shape-shifter python -m backend.app.scripts.authorization list-grants \
   --effective --actor <operator-principal-id> --json
```

Use `--membership-url` for a one-off endpoint override. Use `--strict` when automation must fail if any group is unavailable or not found. Human-readable output reports resolved principals, provider, fetch time, and lookup errors; JSON output reports the same status fields. Lookup results are recorded as audit events. The trusted provider remains authoritative, and the application does not expand memberships into grant rows or use review results for runtime authorization. This phase queries the provider directly and does not cache membership snapshots; reconsider a review-only cache if provider availability or review latency becomes an operational problem.

Do not edit the SQLite database directly. Direct changes bypass the authorization repository's audit records and final-owner and final-administrator protections.

List resources, application roles, and audit events for review:

```bash
docker compose exec shape-shifter python -m backend.app.scripts.authorization list-resources --json
docker compose exec shape-shifter python -m backend.app.scripts.authorization list-application-roles --json
docker compose exec shape-shifter python -m backend.app.scripts.authorization list-audit-events --json
```

Assign or revoke deployment-wide roles with an explicit actor. Supported roles include `project_creator`, `operator`, and `admin`; use `--dry-run` before applying changes. Revocations require `--yes` or `--non-interactive`:

```bash
docker compose exec shape-shifter python -m backend.app.scripts.authorization grant-application-role \
   --principal-id <principal-id> --role operator --actor <admin-principal-id>
docker compose exec shape-shifter python -m backend.app.scripts.authorization revoke-application-role \
   --principal-id <principal-id> --role operator --actor <admin-principal-id> --yes
```

The repository records every mutation and prevents removal of the final project owner or application administrator. Unknown and deleted resources cannot be selected by locator for grant mutations.

#### Enforcement cutover

Authorization enforcement has no runtime toggle. A release containing protected routes enforces their requirements when the application starts. Do not cut over until all of these conditions are met:

1. The route inventory has classified every sensitive route and no required resource is unowned.
2. The reviewed manifest has been applied and `reconcile` reports no missing administrators, resources, or grants.
3. A consistent authorization database backup has been created and copied to operator-controlled storage.
4. The exact release commit, manifest revision, database backup location, and rollback decision owner are recorded in the deployment record.
5. Post-deployment checks confirm allowed and denied access for an administrator, a project owner, and a principal without grants.

#### Backup and recovery

Create backups with SQLite's backup API; do not copy a live `.sqlite3` file directly. Store backups outside `docker/data/state/` and project-managed data.

```bash
docker compose exec shape-shifter python -m backend.app.scripts.authorization backup \
   /app/state/authorization-$(date +%Y%m%d-%H%M%S).sqlite3
docker compose exec shape-shifter python -m backend.app.scripts.authorization integrity-check
```

Copy the backup to operator-controlled storage after the command completes. To restore a backup, stop the service first, run a one-off container that has the state bind mount, restart the service, and check integrity:

```bash
docker compose down
docker compose run --rm shape-shifter python -m backend.app.scripts.authorization restore \
   /app/state/<authorization-backup>.sqlite3
docker compose up -d
docker compose exec shape-shifter python -m backend.app.scripts.authorization integrity-check
```

Restore changes grants, application roles, resource records, and authorization audit history to the selected backup. Reconcile the reviewed manifest and repeat access smoke checks before considering recovery complete.

#### Rollback

For an application release rollback, deploy the previous image as described in [Rollback](#rollback). Keep the current authorization database unless the rollback also requires restoring its recorded grants and resource state. When restoring the database, use the recovery procedure above and record the chosen backup and reason.

### Build-time variables (baked into frontend bundle)

These are set at image build time and require a rebuild to change:

| Variable                | Default            | Purpose                       |
|-------------------------|--------------------|-------------------------------|
| `VITE_API_BASE_URL`     | `""` (same-origin) | API base URL for the frontend |
| `VITE_ENV`              | `production`       | Frontend environment flag     |
| `VITE_ENABLE_ANALYTICS` | `false`            | Analytics toggle              |
| `VITE_ENABLE_DEBUG`     | `false`            | Debug overlay toggle          |

---

## Data Layout

Persistent data is mounted from `docker/data/` on the host into `/app/` in the container:

| Host path               | Container path    | Contents                                                |
|-------------------------|-------------------|---------------------------------------------------------|
| `docker/data/projects/` | `/app/projects/`  | Project YAML files                                      |
| `docker/data/shared/`   | `/app/shared/`    | Shared data sources and reference data                  |
| `docker/data/logs/`     | `/app/logs/`      | Application logs (JSON, rotated at 10 MB, kept 30 days) |
| `docker/data/output/`   | `/app/output/`    | Execution output files                                  |
| `docker/data/backups/`  | `/app/backups/`   | Automatic pre-save YAML backups                         |
| `docker/data/.pgpass/`  | `/app/.pgpass:ro` | PostgreSQL password file                                |
| `docker/data/state/`    | `/app/state/`     | Authorization SQLite database                            |

Create these directories before first startup:

```bash
make setup-volumes   # from docker/ or repo root
```

---

## Build Artifacts

The build produces a single Docker image (`shape-shifter`) from a multi-stage `Dockerfile`:

1. **Stage 0 – Source resolver**: clones from GitHub or uses local working directory context.
2. **Stage 1 – Frontend builder**: runs `pnpm install` and `pnpm run build:skip-check` with Vite.
3. **Stage 2 – Python dependencies**: installs locked runtime dependencies via `uv sync --frozen --no-dev --extra api`.
4. **Stage 3 – Runtime**: Python slim image with JRE, `shapeshifter` user, and `uvicorn` entrypoint on port 8012.

Image tags follow semantic versioning (`v1.2.3`). When `main` matches the latest tag, both `v1.2.3` and `latest` are applied automatically by `build.sh`.

---

## Deployment Flow

Production deployments run on the `sead-tools` host as the `sead` user from `/home/sead/sead-tools/sead_shape_shifter`.

### One-time setup

```bash
# On deploy host as sead user
make setup-volumes     # create data directories
make setup-env         # copy .env templates → edit backend.env
```

### Update deploy scripts from repository

Run from the developer's local machine (copies `Dockerfile`, `Makefile`, `build.sh`, and supporting files to the deploy host):

```bash
# From docker/ in the repository
./rsync-to-sead-tools
```

Or via the Makefile:

```bash
make update-deploy-scripts
```

### Build and deploy

```bash
# From deploy host (as sead user, from /home/sead/sead-tools/sead_shape_shifter)
make docker-build        # clones from GitHub main + builds image
make docker-restart      # stops, removes old container, starts new one
```

Or combined:

```bash
make build-and-deploy
```

To deploy a specific tag or branch:

```bash
GIT_REF=v1.2.0 make docker-build
make docker-restart
```

---

## CI Pipeline

Defined in `.github/workflows/release.yml`. Triggers on push to `main` and on manual `workflow_dispatch`.

Steps:
1. Checkout with full history (`fetch-depth: 0`).
2. Install `semantic-release` and plugins.
3. Run `semantic-release` — analyses commit messages, bumps version, updates `CHANGELOG.md`, creates GitHub Release, and tags the commit.
4. Upload draft user-facing release notes from `docs/whats-new/v*.md` as a build artifact.

The workflow does **not** build or push a Docker image. Image builds are performed manually on the deploy host (see Deployment Flow).

---

## CD Triggers and Release Process

There is no automated continuous deployment pipeline. The release process is:

1. Merge PRs into `dev`, then merge `dev` into `main`.
2. `semantic-release` runs on the CI pipeline and creates a versioned GitHub Release.
3. An operator SSHs into the deploy host and runs `make build-and-deploy` (or `make docker-build && make docker-restart`).

Semantic-release uses conventional commit prefixes (`feat:`, `fix:`, `BREAKING CHANGE:`) to determine the version bump.

---

## Post-Deployment Verification

```bash
# From deploy host or any host with access
make docker-health                    # polls /api/v1/health via curl + jq
curl -sf http://localhost:8012/api/v1/health | jq .

# Check container is running
make docker-ps

# Tail recent logs
make docker-logs                      # follows; Ctrl-C to exit
docker logs shape-shifter --tail 50
```

Smoke-check the UI by opening `http://<host>:8012/` in a browser. Confirm the project list loads and the API docs are reachable at `http://<host>:8012/api/v1/docs`.

For projects that include fixed entities, open at least one representative project after deployment and check for a `Load-Time Normalizations Detected` warning banner in the project detail view. That banner means the backend normalized coercible fixed-entity values in memory during load, typically string values in `_id` columns such as `"53" -> 53`.

If the banner appears:

- review the listed entity, row, and column details before making other changes
- confirm the normalization is expected for that project
- save the project only if you want the normalized values written back to YAML

Project files are not mutated on load. Normalized values are written only on explicit save, and the normal pre-save backup flow still applies.

---

## Rollback

The container is stateless (all data in mounted volumes). To roll back:

1. Identify the last known-good image tag (e.g., `shape-shifter:v1.1.0`).
2. Edit `docker-compose.yml` `image:` field to pin the previous tag, or rebuild from the previous tag:

   ```bash
   GIT_REF=v1.1.0 make docker-build
   make docker-restart
   ```

3. Verify with `make docker-health`.

Project YAML files are not altered by a container restart; they persist in the mounted volume. If a bad deployment wrote corrupted projects, restore from `docker/data/backups/`.

---

## Health Checks and Observability

### Health endpoint

```
GET /api/v1/health
```

Returns HTTP 200 when the application is ready. The container health check polls this endpoint every 30 s with a 10 s timeout and 3 retries (start period 40 s).

### Logs

Loguru writes structured logs to `docker/data/logs/`. Log files rotate at 10 MB, kept for 30 days, and compressed as `.zip`.

```bash
make docker-logs           # follow live log stream
docker logs shape-shifter  # container stdout
```

Log level is controlled by `SHAPE_SHIFTER_LOG_LEVEL` (default `INFO`).

### Fixed-entity normalization signals

When a project load encounters coercible fixed-entity values, the backend emits a warning-level log entry beginning with `Fixed entity normalization on load`. Each entry includes:

- project name
- source file path
- entity name
- row number
- column name
- original value
- normalized value
- target type

These warnings are also returned to the frontend and shown in the project detail view as a `Load-Time Normalizations Detected` banner.

Operational meaning:

- warning present: the load succeeded, but the in-memory project differs from the YAML file for the listed fixed-entity values
- no banner and no warning log: no successful fixed-entity normalization was needed during that load
- invalid non-coercible values are not converted into warnings; they continue to fail through the normal validation and save paths

Operator response:

- inspect the warning list in the UI or the matching log entries
- decide whether the normalization is expected
- save the project to persist the corrected values, or restore/edit the YAML manually if the values should not be normalized

### Alerting

TBD — no alerting infrastructure is currently configured.

---

## Backup and Recovery

### Automatic project backups

The application writes a timestamped backup of each project YAML to `/app/backups/` before every save. These are accessible on the host at `docker/data/backups/`. No retention policy is enforced automatically; prune old backups manually as needed.

This includes explicit saves performed after load-time fixed-entity normalizations. Loading a project does not create a backup by itself because no file is modified until an operator saves.

### Manual backup

```bash
# Copy all project files off the host
cp -r /home/sead/sead-tools/sead_shape_shifter/data/projects /backup/$(date +%Y%m%d)-projects
```

### Recovery

To restore a project from backup:

```bash
cp docker/data/backups/<project>-<timestamp>.yml docker/data/projects/<project>.yml
```

The running container picks up the restored file on the next API read (no restart required, as the cache TTL is 300 s).

---

## References

- [docker/README.md](../docker/README.md) — Docker setup, volume layout, and all `make` targets
- [docker/BUILD_SCRIPT_GUIDE.md](../docker/BUILD_SCRIPT_GUIDE.md) — `build.sh` options and cache invalidation
- [docs/DEVELOPMENT.md](DEVELOPMENT.md) — Local development setup and contributor workflow
- [docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](DATA_PROVIDER_SUBMISSION_LIFECYCLE.md) — Durable lifecycle policy for provider-submitted data changes and review outcomes
- [docs/DESIGN.md](DESIGN.md) — Architecture, layer boundaries, and single-worker constraint rationale
- [AGENTS.md](../AGENTS.md) — Quick-reference commands and workflow conventions
