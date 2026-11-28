# Container Host Tooling

This source-only tree holds the host-side tools, release-policy checks, and
regression tests for the Shape Shifter container release. Its scripts run from a
repository checkout as root; they are not shipped to a deployment user.

- `deploy/` — host provisioning and installer tools: `deploy_environment.sh`,
  the systemd and NGINX installers, the authorization bootstrap, the host
  prerequisite check (`get-install.sh`), the deployment file sync tool
  (`sync-to-deploy`), and the project sync tool (`sync_projects.py`). The retired release manager
  (`manage_container_release.sh`) is kept only as a reference.
- `verify/` — the read-only release-policy checker used by the
  `container-release` workflow, and its [README](verify/README.md).
- `tests/` — shell regression suites for the tools above.

Runtime verification is owned by SEAD operations. The
[SEAD Runtime Verification Handoff](../../docs/proposals/done/CONTAINER_SETUP_SIMPLIFICATION/OPERATIONS_VERIFICATION_HANDOFF.md)
lists the required operational outcomes without prescribing tools.

## Create the proxy secret

NGINX sends this secret with each request, and the backend rejects requests
without it. The compose file mounts the app file into the container. See
[Proxy Secret](../../docs/OPERATIONS.md#proxy-secret) for the setup order.

Run once for each site. `DEPLOY_USER` is the host user that runs the site's
container; that user's primary group can read the app file. It defaults to
`DOMAIN`, so leave it out when the user is named after the domain:

```bash
sudo deployment/container-host/deploy/bootstrap-proxy-secret.sh <DOMAIN> [DEPLOY_USER]
```

It writes `/etc/shape-shifter/<DOMAIN>/proxy-secret` for the app and
`/etc/nginx/shape-shifter-secrets/<DOMAIN>.conf` for NGINX.

- **New or reinstalled site:** the installer's HTTPS template has the include.
  Run this script before the installer. If the secret file is missing,
  `nginx -t` fails and the installer removes the site's enabled link, even if the
  site was enabled before.
- **Existing site file:** to add the header without running the installer, add
  `include /etc/nginx/shape-shifter-secrets/<DOMAIN>.conf;` in the `location`
  block that has `proxy_pass`, then run
  `sudo nginx -t && sudo systemctl reload nginx`. `nginx -t` also passes when the
  line is missing.
- **Replace the secret:** delete the app file, run the script again, then right
  away reload NGINX and, as the deploy user, run `make restart` in `~/container`.
  Requests get `401` between the two steps.
- **If `nginx -t` or the reload fails:** the new files stay. Fix the problem
  before NGINX is reloaded or the container is recreated.
- **Keep it private:** `nginx -T` prints the secret. Do not paste or log its
  output, and do not commit or back up either file.

## Copy projects between deployments on one host

`sync_projects.py` copies projects in one direction between two deployment users
on the same host. Both containers must be running so the script can read their
authorization records. Run it as root from a repository checkout:

```bash
sudo python3 deployment/container-host/deploy/sync_projects.py \
  --source-user test-shape-shifter.sead.se \
  --target-user shape-shifter.sead.se --dry-run
sudo python3 deployment/container-host/deploy/sync_projects.py \
  --source-user test-shape-shifter.sead.se \
  --target-user shape-shifter.sead.se
```

To start tracking a project that already exists on the target, name it with
`--enroll-existing` using its API locator (for example, `arbodat:P`). First
run with `--dry-run`, then repeat without it. The command requires the same
single named owner on both deployments and keeps the replaced target folder
under the target data directory's `backups/project-sync-*` for review. Repeat the option
for each project to enroll.

The script uses each user's installed `~/container/scripts/_load-env.sh` to
resolve the mounted data directory. Pass `--source-config-dir` or
`--target-config-dir` when a deployment uses a configuration directory other
than `~/config`.

For a new project, it copies the complete project folder and adopts it on the
target with the source project's single named owner. Existing source projects
must have exactly one owner grant. For a project copied on an earlier run, it
replaces the target folder's contents and keeps the target authorization resource
and grants. A target project edited after the last copy causes a conflict; the
script leaves it untouched. A same-named project that was not copied by this
script also causes a conflict unless named with `--enroll-existing`. Nested
project folders are not supported because replacing a parent folder could
remove a separate project. The sync records successful copies in the
target's `state/project-sync/<source-user>.json` file. Keep this file with the
target's persistent state.

Run the sync when neither deployment is editing the affected projects. The
script checks that source content stays unchanged while it is copied and
restarts the target container after a batch that changed projects, clearing
its project caches. If the source no longer has a project, the target copy and
its grants remain. Removed files *within* a project disappear when that project
is updated. The script copies only project folders; arrange any required shared
data, data sources, external connections, and credentials separately. Both
deployments may use the same NGINX htpasswd file; the script does not change
NGINX accounts or group membership.

If adoption or a restart fails, review the reported project and the target's
authorization records before retrying. A project folder whose authorization
record was created but whose sync state was not recorded will be reported as a
name collision. Resolve that state deliberately before another run.

## Why it is outside `deployment/container/`

Release archives are built with
`git archive --format=tar.gz --prefix=container/ HEAD:deployment/container`, which
can only reach tracked files under `deployment/container/`. Because
`deployment/container-host/` is a sibling, nothing in it can enter a release
archive: an archive carries only deployment-user runtime contents, and host
tooling never reaches a deployment user. The `container-release` workflow runs
the checker here against the source tree and the built archive. The release
manager that once validated a downloaded archive with its own trusted code is
retired: environments now keep a manual copy of `deployment/container/` in
`~/container`, refreshed with `sync-to-deploy`, until images are published to
GHCR (see `docs/proposals/GHCR_IMAGE_RELEASE.md`).

## See also

- [../container/DEPLOYMENT.md](../container/DEPLOYMENT.md) — the operator
  workflow for placing and refreshing deployment files.
- [verify/README.md](verify/README.md) — the release-policy checks.
