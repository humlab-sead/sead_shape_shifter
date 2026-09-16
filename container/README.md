# Shape Shifter Podman Deployment

Deployment files for running Shape Shifter as a rootless Podman container. The
container serves the FastAPI backend and the built Vue 3 frontend on one port
(default `8012`). This directory is also the standalone build context used on
deployment hosts, so it carries everything the build needs except the
(git-ignored) UCanAccess JARs in `lib/`.

## Prerequisites

- Linux with Podman 4.0 or later and `podman-compose`
- systemd user services, with lingering enabled for the deployment user
- A dedicated user account per environment
- `make`, `curl` and `tar` on the host

```bash
sudo apt-get update && sudo apt-get install -y podman podman-compose make curl
sudo loginctl enable-linger <deployment-user>
```

## Layout

```text
~/container/            # this directory (deployment files + build context)
~/container-data/       # persistent runtime data and configuration
├── projects/
├── shared/
├── logs/
├── output/
├── backups/
├── tmp/
├── state/              # authorization SQLite database
├── backend.env         # runtime environment (chmod 600)
└── .pgpass/.pgpass     # PostgreSQL credentials (chmod 600)
```

The location is controlled by `DATA_DIR` (default `../container-data`). The
Makefile exports the absolute path as `CONTAINER_DATA_DIR`, and
`podman-compose.yml` reads every mount and the `env_file` from that variable.

## Quick Start

Run these as the deployment user from the `container/` directory:

```bash
make install-ucanaccess   # only needed for MS Access data sources
make setup                # create .env, container-data/ and backend.env
nano .env                 # image, branch, port and frontend build arguments
nano ../container-data/backend.env
make build                # build the image from GitHub (repository and ref from .env)
make up
make healthcheck
```

The application is available at `http://localhost:8012/`. Set a different host
port when several environments share a host:

```bash
HOST_PORT=8013 make up
```

## Common Commands

| Command                  | Purpose                                             |
|--------------------------|-----------------------------------------------------|
| `make setup`             | Create data directories and environment files       |
| `make install-ucanaccess`| Download the UCanAccess JARs into `lib/ucanaccess`   |
| `make build`             | Build the image from GitHub (`GIT_REF`, `GIT_REPO`)  |
| `make build-local`       | Build the image from the local repository checkout   |
| `make up` / `make down`  | Start / stop the container                          |
| `make restart`           | Restart the container                               |
| `make logs`              | Follow container logs                               |
| `make status`            | Show container status and health                    |
| `make shell`             | Open a shell in the container                       |
| `make healthcheck`       | Check the health endpoint                           |
| `make validate`          | Validate Podman, the compose file and the data dirs |
| `make test`              | Build, start and check the endpoints                |
| `make backup`            | Back up data, configuration and state               |

Run `make help` for the complete list.

## Configuration

Two files hold configuration. `container/.env` holds the deployment defaults
shared by the Makefile, the scripts and the compose file. `backend.env` holds
the runtime settings that the container reads on every start.

### Deployment defaults: `container/.env`

`make setup` copies `.env.example` to `.env` when `.env` is absent. Edit `.env`
rather than the scripts or the Makefile. It sets the image, the git repository
and branch, the host port, the data directory, the compose project name, the
container name, and the frontend build arguments.

Values resolve with this precedence, highest first:

1. command line — `make IMAGE_NAME=shape-shifter:dev up`
2. environment — `IMAGE_NAME=shape-shifter:dev make up`
3. `container/.env`
4. the fallbacks built into the Makefile

`make build` tags its output from the git ref when the ref is not a release
version, so `GIT_REF=dev` produces `shape-shifter:dev`. Set `IMAGE_NAME` to that
same tag, otherwise `make up` starts the previous image.

`.env` is not tracked by git; `.env.example` is tracked and holds the defaults.

### Runtime configuration: `../container-data/backend.env`

Runtime configuration lives in `../container-data/backend.env`. It is loaded by
the container on every start, so editing it only needs `make restart`.

Production settings raised by the backend configuration:

- `SHAPE_SHIFTER_ENVIRONMENT=production` requires
  `SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=true` and a non-empty
  `SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS`.
- The reverse proxy must send the authenticated username in the
  `X-Authenticated-User` header (see `scripts/deploy/nginx-shape-shifter.conf.template`).

Keep `backend.env` and `.pgpass/.pgpass` readable only by the deployment user:

```bash
chmod 600 ../container-data/backend.env ../container-data/.pgpass/.pgpass
```

### Rootless ownership

The compose service uses `userns_mode: "keep-id"`, which maps the deployment
user to the same UID/GID inside the container. `scripts/build.sh` passes
`USER_UID`/`USER_GID` from `id -u`/`id -g`, so the non-root container user owns
the bind-mounted data directories.

### Frontend build variables

`VITE_*` values are compiled into the JavaScript bundle and therefore require a
rebuild. They come from `container/.env` and reach the build as arguments (see
`podman-compose.yml` and `Containerfile`); they are not read from
`backend.env`.

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md): initial deployment, multiple environments, NGINX and systemd.
- `make status`, `make healthcheck` and `make logs` are the first diagnostic steps.

**Podman:** 4.0+ (built and tested with 5.7)
**Platform:** Linux with systemd
