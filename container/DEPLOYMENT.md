# Podman Deployment Guide

Deploy Shape Shifter as a rootless Podman container on a Linux host with
systemd. For the command reference, see [README.md](README.md); for the
container lifecycle helpers, see the Makefile and `scripts/`.

## Quick Navigation

- **Single environment**: [Single environment deploy](#single-environment-deploy)
- **Multiple environments**: repeat the single-environment steps, or use
  `scripts/deploy/deploy_all_environments.sh`
- **NGINX**: [NGINX reverse proxy](#nginx-reverse-proxy)
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

The deployment user's home directory holds two folders:

```text
~/container/         deployment files and build context
~/container-data/    persistent data and configuration
```

---

## Single environment deploy

Run as the deployment user, from `~/container`:

```bash
make install-ucanaccess   # only needed for MS Access data sources
make setup                # create .env, ~/container-data/ and backend.env
nano .env                 # image, branch, port and frontend build arguments
nano ../container-data/backend.env
make build                # build the image from GitHub (repository and ref from .env)
make up
make healthcheck
```

`container/.env` holds the deployment defaults shared by the Makefile, the
scripts and the compose file: the image, the git repository and branch, the host
port, the data directory and the frontend build arguments. `make setup` creates
it from `.env.example`. To build from a branch, set both values so the build and
the start agree:

```bash
GIT_REF=dev
IMAGE_NAME=shape-shifter:dev
```

The deploy helper described below records these values automatically from its
`--repo`, `--ref` and `--host-port` options. The ref may be a branch or a
release tag; `--branch` is accepted as an alias.

Before the first start, edit `~/container-data/backend.env` and set:

- `SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=true`
- `SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS='["admin@example.com"]'`
- `SHAPE_SHIFTER_ALLOWED_ORIGINS` for the public host name
- `SEAD_HOST`, `SEAD_PORT`, `SEAD_DBNAME`, `SEAD_USER` for the database

PostgreSQL passwords belong in `~/container-data/.pgpass/.pgpass` (mode 600),
not in `backend.env`.

To run the whole flow from an admin account, use the deploy helper:

```bash
sudo scripts/deploy/deploy_single_environment.sh test-shape-shifter.sead.se
sudo scripts/deploy/deploy_single_environment.sh test-shape-shifter.sead.se --host-port 8013
```

### Multiple environments

Give each environment its own user and host port, then repeat:

```bash
sudo scripts/deploy/deploy_all_environments.sh \
  test-shape-shifter.sead.se:8012 \
  prod-shape-shifter.sead.se:8013
```

Environments come from the arguments first, then from `DEPLOY_ENVIRONMENTS`,
which can be exported or set in `container/.env`. There is no built-in
environment list, so a run with neither stops instead of deploying somewhere
unrequested:

```bash
DEPLOY_ENVIRONMENTS='test-shape-shifter.sead.se:8012 prod-shape-shifter.sead.se:8013' \
  sudo -E scripts/deploy/deploy_all_environments.sh
```

`HOST_PORT` selects the published port; the container port stays `8012`. Each
deployment records its repository, branch, port, and matching image name in
`~/container/.env`, so later builds keep the source that was deployed.

---

## NGINX reverse proxy

Install an HTTPS vhost that forwards to the container:

```bash
sudo container/scripts/deploy/install_nginx_reverse_proxy.sh test-shape-shifter.sead.se 8012
```

The upstream port defaults to `HOST_PORT` from `container/.env`, so omit the
second argument when the deployment already uses its configured port.

The script renders `scripts/deploy/nginx-shape-shifter.conf.template` into
`/etc/nginx/sites-available/`, enables it and reloads NGINX.

The backend authenticates through a trusted proxy in production: NGINX must
populate `X-Authenticated-User` (the template forwards `$remote_user`). Enable an
authentication method such as `auth_basic` with an htpasswd file, or replace the
header with the value supplied by your SSO proxy. Without an authenticated user
the API returns `401`.

The site files under `resources/` use one password file per site,
`/etc/nginx/htpasswd/shape-shifter`, and give it mode `640` with `root:www-data`
ownership. Create and maintain those accounts as described in
[Nginx Basic-auth users](../docs/OPERATIONS.md#nginx-basic-auth-users); the
account name is the principal ID the application records.

---

## Systemd integration

Install the user service so the container starts on boot:

```bash
sudo scripts/deploy/install_systemd_service.sh test-shape-shifter.sead.se
```

The unit starts the container through `scripts/up.sh` and stops it with
`scripts/down.sh`, the same scripts an operator runs, so a systemd start and a
manual `make up` resolve `container/.env` identically. The unit sets no
deployment configuration of its own: a value in the unit environment would
override `container/.env`, because the compose tools prefer the environment over
the file.

Control it with the `service-*` targets, which call `scripts/service.sh`:

```bash
make service-status
make service-restart
make service-logs
```

The script takes one action: `install`, `enable`, `disable`, `start`, `stop`,
`restart`, `status` or `logs`. It holds the unit name, so
`SERVICE_NAME=shape-shifter-dev scripts/service.sh status` inspects a unit with
another name.

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

```bash
# Refresh deployment files and rebuild the image from GitHub
sudo scripts/deploy/deploy_single_environment.sh test-shape-shifter.sead.se

# Or, as the deployment user
make build && make restart
```

`make build` takes the repository and ref from `container/.env`, defaulting to
`GIT_REPO=https://github.com/humlab-sead/sead_shape_shifter.git` and
`GIT_REF=main`. Set `GIT_REF=v1.2.0` for a release tag, or `make build-local` to
build from a local checkout. A `VAR=value make build` override takes precedence
over `.env`.

`make build` tags a branch build after the ref, so `GIT_REF=dev` produces
`shape-shifter:dev`. Keep `IMAGE_NAME` in `.env` in step with `GIT_REF`,
otherwise `make restart` starts the previous image.

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
