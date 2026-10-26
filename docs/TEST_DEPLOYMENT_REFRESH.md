# Refresh the Shape Shifter Test Deployment

Runbook to bring the `test-shape-shifter.sead.se` deployment in line with the
current `dev` branch of this repository, without losing existing configuration.

Verified state on 2026-10-16 (host `humlabsead`):

- Deployment user: `test-shape-shifter.sead.se` (uid 1021), home
  `/data/test-shape-shifter.sead.se`; `/data/test-shape-shifter.sead.se` is a
  symlink to that home folder.
- `~/container/` is a **real directory** from the old layout (fetched by the
  retired `get-install.sh` flow from the `security-regression-and-release-verification`
  branch). It has drifted from `dev`: `load-env.sh` renamed to `_load-env.sh`,
  `up.sh`/`down.sh`/`service.sh` replaced by `container.sh`, `project.sh` added,
  `scripts/deploy/` and `scripts/verify/` moved out to `deployment/container-host/`.
  The `container-v0.1.0` release tag does not match `dev` either.
- `~/config/` (`deployment.env`, `backend.env`, `authorization.env`,
  `authorization-manifest.yaml`, `groups.d/`, `.pgpass/`) and `~/container-data/`
  (projects, state, backups, logs, output, shared, tmp) are **compatible with
  the new layout**: the new scripts read the same paths, and the deployed
  `deployment.env` keys are a complete subset of the new `.env.example`
  (no missing keys). Nothing in `~/config` or `~/container-data` needs to change.
- The systemd user unit is installed but references the old
  `scripts/up.sh`/`down.sh`; nginx upstream points at `127.0.0.1:8012`, matching
  `HOST_PORT=8012` — the port stays valid.
- The `lib/ucanaccess/` JARs in the old tree are no longer needed: the new
  `Containerfile` downloads UCanAccess at build time.

**Recommendation: no full reinstall.** The `dev` branch ships
`deployment/container-host/deploy/sync-to-deploy`, which rsyncs
`deployment/container/` into the deployment user's `~/container`, fixes
ownership, installs the new systemd unit, and reloads the daemon — while never
touching `~/config` or `~/container-data`. (The administrator-managed release
path under `/opt/shape-shifter` with `shape-shifter-container-release` installs
only from `container-vX.Y.Z` tags, and no tag matches `dev` yet, so it cannot
track `dev` today. Keep it for the future production path.)

## Step 1 — Back up (as `roger`, from the repo)

```bash
sudo tar -C /data/test-shape-shifter.sead.se -czf ~/test-deploy-backup-$(date +%Y%m%d).tar.gz config container
```

This captures the old scripts and all config. Rollback is just untarring it
back into the home folder.

## Step 2 — Stop the running deployment

Run while the old scripts still exist:

```bash
sudo su - test-shape-shifter.sead.se -c 'export XDG_RUNTIME_DIR=/run/user/$(id -u); cd ~/container && make down'
```

## Step 3 — Sync the dev container tree

The working tree must match `origin/dev` for the deployment folders (verify
with `git diff origin/dev -- deployment/container deployment/container-host`,
which should print nothing):

```bash
cd /data/roger/source/sead_shape_shifter
git checkout dev && git pull
deployment/container-host/deploy/sync-to-deploy --dry-run   # review the change list
deployment/container-host/deploy/sync-to-deploy
```

What this does:

- Replaces `~/container/` with the dev `deployment/container/` tree
  (`--delete` removes the obsolete `up.sh`, `down.sh`, `scripts/deploy/`, etc.).
- Excludes `lib/` from the transfer and removes any stale `~/container/lib/`
  (UCanAccess JARs) from the target — the `Containerfile` downloads UCanAccess
  at build time, so the JARs no longer travel with the deployment.
- Copies `service/shape-shifter.service` (now pointing at
  `scripts/container.sh`) into `~/.config/systemd/user/`.
- Runs `systemctl --user daemon-reload`.
- Excludes `.env` and `deployment-verification`; never touches `~/config` or
  `~/container-data`.

## Step 4 — Run setup as the deployment user

Idempotent; preserves existing config:

```bash
sudo su - test-shape-shifter.sead.se
export XDG_RUNTIME_DIR=/run/user/$(id -u)
cd ~/container
make setup
```

`make setup` only creates files that are missing — the existing
`deployment.env`, `backend.env`, `authorization.env`, manifest, and `.pgpass`
are left untouched. Confirm it reports the existing files as already present.

## Step 5 — Rebuild and start

```bash
make build        # builds shape-shifter:dev from GIT_REF=dev, per deployment.env
make up
make healthcheck
make status
```

The first build downloads UCanAccess inside the image build, so the deleted
`lib/` JARs do not matter.

## Step 6 — Re-enable auto-start

The unit is currently disabled:

```bash
systemctl --user enable shape-shifter.service
systemctl --user status shape-shifter.service
```

## Step 7 — Verify externally

```bash
curl -sI https://test-shape-shifter.sead.se/ | head -3
```

No nginx change is needed — the upstream port (8012) is unchanged.

## Step 8 — Clean up once healthy

```bash
# old 848 MB source tarball and stale container backup in the home folder
sudo rm -f /data/test-shape-shifter.sead.se/sead_shape_shifter.tar /data/test-shape-shifter.sead.se/container-20260916.tar
```

Keep `~/test-deploy-backup-*.tar.gz` until the deployment is confirmed working.

## Caveats and follow-ups

- The old `~/container` tree had script edits relative to the `container-v0.1.0`
  tag, but those are an older branch snapshot, not hand-maintained config. All
  real customization lives in `~/config`, which this flow preserves.
- To move the test environment onto the administrator-managed release path
  (`/opt/shape-shifter` + `shape-shifter-container-release`), first cut a
  `container-v0.2.0` tag from `dev` via the `container-release` branch
  (see `.github/workflows/container-release.yml`), then follow
  `deployment/container/DEPLOYMENT.md`, which requires moving the real
  `~/container` directory aside before `activate` will create the symlink.
