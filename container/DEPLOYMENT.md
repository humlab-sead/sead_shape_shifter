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
make setup                # create ~/container-data/ and backend.env
nano ../container-data/backend.env
make build                # build the image from GitHub (GIT_REF=main)
make up
make healthcheck
```

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

`HOST_PORT` selects the published port; the container port stays `8012`.

---

## NGINX reverse proxy

Install an HTTPS vhost that forwards to the container:

```bash
sudo container/scripts/deploy/install_nginx_reverse_proxy.sh test-shape-shifter.sead.se 8012
```

The script renders `scripts/deploy/nginx-shape-shifter.conf.template` into
`/etc/nginx/sites-available/`, enables it and reloads NGINX.

The backend authenticates through a trusted proxy in production: NGINX must
populate `X-Authenticated-User` (the template forwards `$remote_user`). Enable an
authentication method such as `auth_basic` with an htpasswd file, or replace the
header with the value supplied by your SSO proxy. Without an authenticated user
the API returns `401`.

---

## Systemd integration

Install the user service so the container starts on boot:

```bash
sudo scripts/deploy/install_systemd_service.sh test-shape-shifter.sead.se
```

The unit runs `podman-compose up -d` from `~/container` and sets
`CONTAINER_DATA_DIR=~/container-data`. Control it with:

```bash
systemctl --user status shape-shifter
systemctl --user restart shape-shifter
```

From an admin account, target another user's session with
`systemctl --user -M user@ start shape-shifter`.

---

## Updating a deployment

```bash
# Refresh deployment files and rebuild the image from GitHub
sudo scripts/deploy/deploy_single_environment.sh test-shape-shifter.sead.se

# Or, as the deployment user
make build && make restart
```

`make build` uses `GIT_REF` (default `main`). Set `GIT_REF=v1.2.0` for a
release tag, or `make build-local` to build from a local checkout.

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
