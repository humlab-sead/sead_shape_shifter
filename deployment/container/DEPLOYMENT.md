# Podman Deployment Guide

Deploy Shape Shifter as a rootless Podman container on a Linux host with
systemd. For the command reference, see [README.md](README.md); for the
container lifecycle helpers, see the Makefile and `scripts/`.

## Quick Navigation

- **Deployment files**: [Place the deployment files](#place-the-deployment-files)
- **Single environment**: [Single environment deploy](#single-environment-deploy)
- **Multiple environments**: repeat the single-environment steps with
  `deployment/container-host/deploy/deploy_environment.sh`
- **NGINX**: [NGINX reverse proxy](#nginx-reverse-proxy)
- **Authorization inputs**: [Authorization inputs](#authorization-inputs)
- **Auto-start**: [Systemd integration](#systemd-integration)
- **Diagnostics**: `make status`, `make healthcheck`, `make logs`

---

## Prerequisites

One-time, per server:

```bash
# 1. Install Podman and its compose provider
sudo apt-get update && sudo apt-get install -y podman podman-compose make curl

# 2. Verify user namespaces are enabled
podman unshare id

# 3. Create a dedicated user for each environment
USER_NAME="test-shape-shifter.sead.se"
sudo useradd -r -m -s /bin/bash "$USER_NAME"

# 4. Enable lingering so containers survive logout and start on boot
sudo loginctl enable-linger "$USER_NAME"
```

The deployment user's home directory holds three sibling directories:

```text
~/container/         deployment files (manual copy or sync)
~/config/            environment configuration, credentials and policy
~/container-data/    persistent runtime data and state
```

Place the deployment files before running the commands below; see
[Place the deployment files](#place-the-deployment-files).

---

## Place the deployment files

Until container images are published to GHCR (see
[GHCR_IMAGE_RELEASE.md](../../docs/proposals/GHCR_IMAGE_RELEASE.md)), each
environment keeps a manual copy of the `deployment/container/` tree in the
deployment user's `~/container`. The `shape-shifter-container-release` manager
and its `container-vX.Y.Z` release archives are retired: no host installs the
manager any more, and the host tools in this guide accept a real `~/container`
directory.

Place the tree from a reviewed repository checkout, as root:

```bash
# First install: copy the tree and fix ownership
sudo rsync --archive --no-group --exclude=/.env deployment/container/ \
  ~USER/container/
sudo chown -R USER:USER ~USER/container

# Later refreshes: sync the tree (also installs the systemd unit)
deployment/container-host/deploy/sync-to-deploy --deploy-user USER
```

`sync-to-deploy` mirrors `deployment/container/` into `~/container`, removes
files deleted locally, fixes ownership, installs the systemd user unit, and
reloads the daemon. It never touches `~/config` or `~/container-data`, and it
does not restart or enable the service. It refuses a symlinked target so a
sync cannot overwrite an older manager selection.

After placing or refreshing the files, build and start as the deployment user:

```bash
sudo -u USER -H bash -lc 'cd ~/container && make build && make up && make healthcheck'
```

### Paths and permissions

`CONFIG_DIR` defaults to `~/config` and `DATA_DIR` to `~/container-data`. A
relative override in `~/config/deployment.env` names a path under the deployment
user's home, so `DATA_DIR=container-data` and `DATA_DIR=./container-data` both
mean `~/container-data`; an absolute value is used unchanged. Relative overrides
resolve from the user's home, not from `~/container`, so configuration,
credentials, and runtime data stay outside the deployment files.
`CONTAINER_DATA_DIR`, which `podman-compose.yml` mounts, follows `DATA_DIR` unless
it is set explicitly. `scripts/_load-env.sh` and the Makefile implement the same
rule, so a direct script call and a Make target agree.

### Curated provider registry

The provider-schema registry is reviewed data, not runtime data. Reviewed files
live in `deployment/container/resources/data-providers/`, which `sync-to-deploy`
copies with the rest of the deployment tree to `~/container/resources/data-providers`.
`podman-compose.yml` mounts that directory read-only over
`/app/shared/data-providers`, so the writable `~/container-data/shared` mount
never supplies or receives provider records.

The default `SHAPE_SHIFTER_GLOBAL_DATA_PROVIDER_DIR=shared/data-providers`
resolves to `/app/shared/data-providers` because `SHAPE_SHIFTER_APPLICATION_ROOT`
is `/app`. Do not override it inside a container; the reviewed directory is the
only source. Refresh it with the existing sync workflow and verify the effective
mount after a restart:

```bash
podman inspect shape-shifter --format '{{json .Mounts}}'
```

The listed mounts must show `/app/shared/data-providers` with `RW: false`.
For local development, set `SHAPE_SHIFTER_GLOBAL_DATA_PROVIDER_DIR` to the
absolute path of the reviewed directory instead of mounting it.

---

## Single environment deploy

Run as the deployment user, from `~/container`:

```bash
make setup                # create ~/config, ~/container-data and the templates
nano ~/config/deployment.env   # image, branch, port and frontend build arguments
nano ~/config/backend.env      # runtime settings
make build                # build the image from GitHub (repository and ref from ~/config/deployment.env)
make up
make healthcheck
```

`~/config/deployment.env` holds the deployment defaults shared by the Makefile,
the scripts and the compose file: the image, the git repository and branch, the
host port, the path overrides and the frontend build arguments. `make setup`
creates it from `deployment/container/.env.example` and leaves an existing file
alone. To build from a branch, set both values so the build and the start agree:

```bash
GIT_REF=dev
IMAGE_NAME=shape-shifter:dev
```

The deploy helper described below records these values from its `--repo`,
`--ref` and `--host-port` options. `--ref` selects the application image ref to
build (a branch or an application release tag); `--branch` is accepted as an
alias.

Before the first start, edit `~/config/backend.env` and set:

- `SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=true`
- `SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS=["admin@example.com"]`
- `SHAPE_SHIFTER_ALLOWED_ORIGINS` for the public host name
- `SEAD_HOST`, `SEAD_PORT`, `SEAD_DBNAME`, `SEAD_USER` for the database

PostgreSQL passwords belong in `~/config/.pgpass/.pgpass` (mode 600), not in
`backend.env`. The authorization inputs described below belong in the same
directory.

To configure the application image settings from an admin account, use the
deploy helper. The user must already have deployment files in `~/container`;
the helper does not fetch or replace them:

```bash
sudo deployment/container-host/deploy/deploy_environment.sh test-shape-shifter.sead.se
sudo deployment/container-host/deploy/deploy_environment.sh test-shape-shifter.sead.se --host-port 8013 --ref v2.3.0
```

### Multiple environments

Give each environment its own user and host port, then run the
single-environment command once per environment:

```bash
sudo deployment/container-host/deploy/deploy_environment.sh test-shape-shifter.sead.se --host-port 8012
sudo deployment/container-host/deploy/deploy_environment.sh prod-shape-shifter.sead.se --host-port 8013
```

Each target user must already have its own deployment files in `~/container`.
Place them first; the deploy helper never fetches or replaces them.

`HOST_PORT` selects the published port; the container port stays `8012`. Each
deployment records its repository, application ref, port, and matching image name
in its own `~/config/deployment.env`, so later builds keep the source that was
configured.

---

## NGINX reverse proxy

Install an HTTPS vhost that forwards to the container. A certificate must
exist before the HTTPS vhost can be enabled, so install the HTTP-only
bootstrap vhost first and obtain the certificate with it:

```bash
sudo deployment/container-host/deploy/install_nginx_reverse_proxy.sh --bootstrap test-shape-shifter.sead.se
sudo certbot certonly --webroot -w /var/www/html -d test-shape-shifter.sead.se
sudo deployment/container-host/deploy/install_nginx_reverse_proxy.sh test-shape-shifter.sead.se 8012
```

Issuing the certificate requires the domain to already resolve to this host
(or to its NAT address). While the DNS record still points at another
machine, HTTP-01 validation reaches that machine instead, and the webroot
method fails; issue with a DNS-01 plugin first or coordinate the DNS change
with these steps.

The upstream port defaults to `HOST_PORT` from the invoking user's
`~/config/deployment.env`, so omit the second argument when the deployment
already uses its configured port. Run the helper as the deployment user
(`sudo -u <user>`) or name that user's configuration directory with
`CONFIG_DIR=/data/<user>/config`.

The script renders
`deployment/container-host/deploy/nginx-shape-shifter.conf.template` into
`/etc/nginx/sites-available/`, enables it and reloads NGINX. It refuses to
enable the HTTPS vhost while the certificate is missing, and it removes the
enable symlink again when `nginx -t` fails, so a broken vhost never breaks
the next reload. The shared maps (`$connection_upgrade`, `$authz_groups`) are
installed once to `/etc/nginx/conf.d/shape-shifter-maps.conf`, which lets a
second Shape Shifter site on the same host enable without duplicate-map
errors.

The backend authenticates through a trusted proxy in production: NGINX must
populate `X-Authenticated-User` (the template forwards `$remote_user`). Enable an
authentication method such as `auth_basic` with an htpasswd file, or replace the
header with the value supplied by your SSO proxy. Without an authenticated user
the API returns `401`.

Group grants need a second header. `auth_basic` supplies no group claim, so the
template derives `X-Authenticated-Groups` from `$remote_user` and the membership
file `/etc/nginx/authz/groups.d/*.conf`. Create that directory and file on the
proxy host, set `SHAPE_SHIFTER_TRUSTED_PROXY_GROUPS_ENABLED=true` and
`SHAPE_SHIFTER_TRUSTED_PROXY_GROUPS_HEADER=X-Authenticated-Groups` in
`~/config/backend.env`, then run `sudo nginx -t` before reloading. See
[NGINX group header](../../docs/OPERATIONS.md#nginx-group-header) for the file
format and the limits of this approach.

The site files under `resources/` use one password file per site,
`/etc/nginx/htpasswd/shape-shifter`, and give it mode `640` with `root:www-data`
ownership. Create and maintain those accounts with the commands in
`container/scripts/authorization.sh --help`; the account name is the principal ID
the application records.

---

## Host services from the container

The container reaches services that run on the host through
`host.docker.internal`. `podman-compose.yml` declares the alias with
`extra_hosts: "host.docker.internal:host-gateway"`, and any configuration that
points at a host service must use it:

```dotenv
SEAD_HOST=host.docker.internal
```

Do not point container configuration at the host's own LAN address. The
container's network namespace cannot reach that address, so the connection is
refused even though the same address works from the host. The host-side check is
the misleading part: `psql -h <host-lan-name>` from the host succeeds while the
container fails, so a host-side success does not prove that the container can
connect. When the address is unreachable, the API reports a generic
`Connection failed. Correlation ID: ...` and the container reports
`Connection refused`, which reads like a credentials problem.

`.pgpass` matches on the host string exactly as it is used, so a value that
switches to `host.docker.internal` needs its own entry:

```
host.docker.internal:9023:sead_staging:sead_ro:<password>
```

The alias resolves only inside the container, so host-facing values are
deployment-specific: host-side tools still need the LAN hostname.

---

## Authorization inputs

`deployment/container-host/deploy/bootstrap-authentication-and-authorization.sh`
reads every input
from the deployment user's configuration directory, `~/config`, and never from
the checkout or a repository secrets folder:

| File | Contents | Mode |
| --- | --- | --- |
| `~/config/authorization.env` | NGINX credentials, principal rosters, audit actor, manifest filename | `600` |
| `~/config/authorization-manifest.yaml` | Approved authorization policy | `600` |
| `~/config/groups.d/shape-shifter.conf` | NGINX group membership | `600` |

The deployment user owns all of `~/config`, which has mode `700`, so only that
user and root can read the files. `authorization.env` contains credentials and is
never mounted into the container: the container receives `backend.env` and
`.pgpass/.pgpass` only.

Provision the inputs by hand. Deployment tooling deliberately does not copy
policy or generate passwords, so the operator installs the approved files:

```bash
sudo -u test-shape-shifter.sead.se -H bash
cd ~/config
mkdir -p groups.d
install -m 600 ~/container/resources/authorization.env.example authorization.env
install -m 600 /path/to/approved-manifest.yaml authorization-manifest.yaml
install -m 600 /path/to/shape-shifter.conf groups.d/shape-shifter.conf
```

Edit `authorization.env` so `AUTHORIZATION_MANIFEST` names the installed
manifest. A relative name resolves inside `~/config`; an absolute path is only
for a deliberate alternate layout.

The manifest is policy data, while `authorization.env` holds the credentials that
bootstrap NGINX accounts and deployment roles.

Before running the bootstrap, set
`SHAPE_SHIFTER_AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE=true` in
`~/config/backend.env`, because the reviewed manifest grants `everyone` reader
access to the shared data sources.

Then run the bootstrap as root. It validates `authorization.env`, the manifest,
and the group file before it writes the htpasswd file, installs group membership,
or assigns roles, so a missing or unreadable input stops the run without changing
any account or policy:

```bash
sudo CONFIG_DIR=$HOME/config deployment/container-host/deploy/bootstrap-authentication-and-authorization.sh
```

The reviewed manifest is authored in the repository under
`resources/authorization/`. Install the approved revision under `~/config`; the
bootstrap never reads the repository copy.

---

## Systemd integration

Install the user service so the container starts on boot:

```bash
sudo deployment/container-host/deploy/install_systemd_service.sh test-shape-shifter.sead.se
```

The unit starts the container through `scripts/container.sh up` and stops it
with `scripts/container.sh down`, the same dispatcher an operator runs, so a
systemd start and a manual `make up` resolve `~/config/deployment.env`
identically. The unit sets no deployment configuration of its own: a value in
the unit environment would override the deployment file, because the compose
tools prefer the environment over the file. The unit only fixes
`WorkingDirectory=%h/container`, so the code that runs is the code in
`~/container`.

Control it with the `service-*` targets, which dispatch through
`scripts/container.sh service <action>`:

```bash
make service-status
make service-restart
make service-logs
```

The dispatcher takes one service action: `install`, `enable`, `disable`, `start`,
`stop`, `restart`, `status` or `logs`. It holds the unit name, so
`SERVICE_NAME=shape-shifter-dev scripts/container.sh service status` inspects a
unit with another name.

From an admin account, target another user's session with
`systemctl --user -M user@ start shape-shifter`.

After changing `service/shape-shifter.service`, reinstall it and restart:

```bash
make service-install
make service-restart
```

`make service-install` copies the unit file and runs `systemctl --user
daemon-reload`, so no separate reload is needed.

---

## Updating a deployment

To refresh an environment's deployment files, sync the reviewed tree from a
repository checkout (see [Place the deployment files](#place-the-deployment-files)):

```bash
deployment/container-host/deploy/sync-to-deploy --deploy-user USER
```

Configuration, credentials, project data, logs, backups, and authorization
state are unchanged; only the files under `~/container` are replaced, and the
systemd unit is reinstalled. Restart the service afterwards to run the new
scripts:

```bash
systemctl --user -M USER@ restart shape-shifter
```

To rebuild the application image from the configured application ref:

```bash
sudo -u USER -H bash -lc 'cd ~/container && make build && make restart && make healthcheck'
```

The deploy helper configures those application image settings from its `--repo`,
`--ref`, and `--host-port` options; it does not fetch or replace container files.

`make build` takes the repository and application ref from
`~/config/deployment.env`, defaulting to
`GIT_REPO=https://github.com/humlab-sead/sead_shape_shifter.git` and
`GIT_REF=main`. Set `GIT_REF=v1.2.0` for an application release tag, or
`make build-local` to build from a local checkout. A `VAR=value make build`
override takes precedence over `~/config/deployment.env`.

`make build` tags a branch build after the ref, so `GIT_REF=dev` produces
`shape-shifter:dev`. Keep `IMAGE_NAME` in `~/config/deployment.env` in step with
`GIT_REF`, otherwise `make restart` starts the previous image.

Before the first build on a host, check prerequisites with
`deployment/container-host/deploy/get-install.sh`: it verifies Podman,
`podman-compose`, lingering, and rootless user namespaces, and writes nothing
into `~/container`.

### Isolated local development

To test deployment files without touching an environment, synchronize to a
separate directory instead of the environment's `~/container`:

```bash
deployment/container-host/deploy/sync-to-deploy --remote-dir container-dev
```

`sync-to-deploy` refuses a symlinked target and any target that resolves into
`/opt/shape-shifter/<user>/`, the storage of a retired manager selection, so an
isolated sync cannot overwrite either.

### Migrating from an older deployment copy

An old `~/container` copy can predate the consolidated dispatcher, in which case
it still contains `scripts/up.sh`, `scripts/down.sh`, `scripts/logs.sh`, and
`scripts/status.sh`. Those four scripts no longer exist: the dispatcher
`scripts/container.sh` provides `up`, `down`, `restart`, `logs`, and `status`
through the Make targets. Refresh the tree with `sync-to-deploy` (it removes the
stale scripts), then reinstall and restart the unit:

```bash
deployment/container-host/deploy/sync-to-deploy --deploy-user USER
sudo -u USER -H bash -lc 'cd ~/container && make service-install'
sudo -u USER -H bash -lc 'cd ~/container && make service-restart'
```

`~/config` and `~/container-data` are untouched by every step. An environment
whose `~/container` is still a symlink into `/opt/shape-shifter/` (a retired
manager selection) must be moved first: an administrator reviews and removes the
symlink, then the steps above place a real directory.

### Migrating from the retired two-directory layout

Earlier deployments kept their settings in `container/.env`, where `DATA_DIR` was
spelled relative to the checkout, so the file held `DATA_DIR=../container-data`.
In `~/config/deployment.env` a relative value names a path under the deployment
user's home, so the same directory drops the leading `../`:

```text
container/.env                  ~/config/deployment.env
DATA_DIR=../container-data  ->  DATA_DIR=container-data
```

Keeping the old spelling resolves one level above the home directory, and
`make up` then stops with a missing data directory. Migrate by moving
`container/.env` to `~/config/deployment.env`, moving `container-data/backend.env`
and `container-data/.pgpass/.pgpass` into `~/config`, and rewriting any relative
override that still starts with `../` or `./`.

---

## Diagnostics

| Task           | Command                                   |
|----------------|-------------------------------------------|
| Container logs | `make logs`                               |
| Health         | `make healthcheck`                        |
| Status         | `make status`                             |
| Shell access   | `make shell`                              |
| Configuration  | `make config`                             |
| Validation     | `make validate`                           |
| Backup         | `make backup`                             |

If a container fails to start, check `podman logs shape-shifter --tail 100`. The
backend refuses to start when `SHAPE_SHIFTER_ENVIRONMENT=production` without
trusted-proxy authentication and a bootstrap administrator.

---

**Platform:** Linux with systemd
**Podman:** 4.0+ (built and tested with 5.7)
