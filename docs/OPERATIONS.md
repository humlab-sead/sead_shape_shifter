# Shape Shifter - Operations Guide

Runbook for operators and maintainers of deployed Shape Shifter environments.

---

## Environments

| Environment | Purpose | Branch | Port |
|-------------|---------|--------|------|
| Production | Live service on `sead-tools` | `main` | 8012 |
| Development | Local developer instances | `dev` or feature | 8012 |

Production runs on the `sead-tools` host under the `sead` user. The canonical deploy directory is `/home/sead/sead-tools/sead_shape_shifter`.

---

## Operational Assumptions and Invariants

- **Single worker only.** The backend must run with `--workers 1`. In-memory state (project cache, singletons) is per-process; multiple workers each maintain independent caches and will silently serve stale data after writes. Multiple workers require a shared state backend (Redis or database) before they can be enabled.
- **Non-root container user.** The container runs as `shapeshifter` (UID 1002, GID 33 / `www-data`). Host volume mounts must be owned by the same UID/GID.
- **File-backed state.** All projects are YAML files on disk. There is no database for project state. Projects must not be edited simultaneously by more than one operator.
- **No built-in TLS.** TLS termination is expected upstream (reverse proxy or tunnel). The container exposes plain HTTP on port 8012.
- **Java required at runtime.** MS Access support (UCanAccess) requires a JRE (`default-jre-headless` is included in the production image).

---

## Configuration and Secrets

### Runtime environment variables

All backend settings use the `SHAPE_SHIFTER_` prefix and are loaded from `docker/data/backend.env` via `env_file` in `docker-compose.yml`.

Key runtime variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SHAPE_SHIFTER_ENVIRONMENT` | `production` | Enables production-mode logging and CORS |
| `SHAPE_SHIFTER_PROJECTS_DIR` | `/app/projects` | Mounted project YAML root |
| `SHAPE_SHIFTER_LOG_LEVEL` | `INFO` | Loguru log level |
| `SHAPE_SHIFTER_ALLOWED_ORIGINS` | _(dev defaults)_ | CORS whitelist |
| `SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL` | `http://localhost:8000` | SEAD reconciliation service |
| `SHAPE_SHIFTER_SIMS_SERVICE_URL` | `http://localhost:8000` | SEAD authority/SIMS service |
| `SEAD_HOST` / `SEAD_DBNAME` / `SEAD_USER` / `SEAD_PORT` | _(none)_ | SEAD database connection (resolved in project YAML via `${VAR}`) |

### Database passwords

Use `~/.pgpass` instead of environment variables. Mount the file read-only into the container:

```
docker/data/.pgpass/.pgpass  →  /app/.pgpass:ro
```

Format: `hostname:port:database:username:password`

```
db.example.com:5432:sead_production:sead_user:password
```

### Build-time variables (baked into frontend bundle)

These are set at image build time and require a rebuild to change:

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `""` (same-origin) | API base URL for the frontend |
| `VITE_ENV` | `production` | Frontend environment flag |
| `VITE_ENABLE_ANALYTICS` | `false` | Analytics toggle |
| `VITE_ENABLE_DEBUG` | `false` | Debug overlay toggle |

---

## Data Layout

Persistent data is mounted from `docker/data/` on the host into `/app/` in the container:

| Host path | Container path | Contents |
|-----------|---------------|---------|
| `docker/data/projects/` | `/app/projects/` | Project YAML files |
| `docker/data/shared/` | `/app/shared/` | Shared data sources and reference data |
| `docker/data/logs/` | `/app/logs/` | Application logs (JSON, rotated at 10 MB, kept 30 days) |
| `docker/data/output/` | `/app/output/` | Execution output files |
| `docker/data/backups/` | `/app/backups/` | Automatic pre-save YAML backups |
| `docker/data/.pgpass/` | `/app/.pgpass:ro` | PostgreSQL password file |

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

### Alerting

TBD — no alerting infrastructure is currently configured.

---

## Backup and Recovery

### Automatic project backups

The application writes a timestamped backup of each project YAML to `/app/backups/` before every save. These are accessible on the host at `docker/data/backups/`. No retention policy is enforced automatically; prune old backups manually as needed.

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
- [docs/DESIGN.md](DESIGN.md) — Architecture, layer boundaries, and single-worker constraint rationale
- [AGENTS.md](../AGENTS.md) — Quick-reference commands and workflow conventions
