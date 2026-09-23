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

Each environment has three sibling directories in the deployment user's home:

```text
~/container/            # replaceable checkout: deployment files + build context
├── .env.example        # tracked template for deployment.env
├── Makefile            # build, lifecycle, diagnostic and service targets
├── podman-compose.yml  # service definition
├── Containerfile       # image build
├── scripts/            # build, setup, lifecycle and deploy helpers
├── service/            # systemd user unit
├── resources/          # generic templates: backend.env, .pgpass, authorization.env, NGINX vhosts
└── lib/                # UCanAccess JARs (untracked build dependency)

~/config/               # environment configuration, outside the checkout
├── deployment.env      # image, ref, port, compose name, path overrides
├── backend.env         # runtime environment for the container (chmod 600)
├── authorization.env   # authorization bootstrap credentials and rosters (chmod 600)
├── authorization-manifest.yaml  # approved authorization policy (chmod 600)
├── groups.d/shape-shifter.conf  # NGINX group membership (chmod 600)
└── .pgpass/.pgpass     # PostgreSQL credentials (chmod 600)

~/container-data/       # mutable runtime data
├── projects/  shared/  logs/  output/  backups/  tmp/
└── state/              # authorization SQLite database
```

`CONFIG_DIR` defaults to `~/config` and `DATA_DIR` to `~/container-data`. The
Makefile resolves both and exports `CONFIG_DIR` and `CONTAINER_DATA_DIR`, so
`podman-compose.yml` reads `backend.env` and the read-only `.pgpass` from
`CONFIG_DIR` and every mutable mount from `CONTAINER_DATA_DIR`.

This checkout holds no live configuration, so a release archive can replace it
without touching `~/config` or `~/container-data`. `make build-local` stages
`lib/ucanaccess` into the repository-root build context, which is the one
writable side effect, and it applies to development builds only.

## Quick Start

Run these as the deployment user from the `container/` directory:

```bash
make install-ucanaccess   # only needed for MS Access data sources
make setup                # create ~/config, ~/container-data and the templates
nano ~/config/deployment.env   # image, branch, port and frontend build arguments
nano ~/config/backend.env      # runtime settings
make build && make restart     # rebuild the image and recreate the running container
make healthcheck
```

`make setup` never overwrites an existing configuration file, and it reports the
authorization inputs that must be provisioned by hand before the authorization
bootstrap runs. See [Authorization inputs](DEPLOYMENT.md#authorization-inputs).

Use `make build && make restart` when rebuilding a running deployment so the
container is recreated with the newly built image.

The application is available at `http://localhost:8012/`. Set a different host
port when several environments share a host:

```bash
HOST_PORT=8013 make up
```

## Common Commands

| Command                  | Purpose                                             |
|--------------------------|-----------------------------------------------------|
| `make setup`             | Create `~/config`, the data directories and the template files |
| `make install-ucanaccess`| Download the UCanAccess JARs into `lib/ucanaccess`   |
| `make build`             | Build the image from GitHub (`GIT_REF`, `GIT_REPO`)  |
| `make build-local`       | Build the image from the local repository checkout   |
| `make up` / `make down`  | Start / stop the container                          |
| `make restart`           | Restart the container                               |
| `make logs`              | Follow container logs                               |
| `make status`            | Show container status and health                    |
| `make shell`             | Open a shell in the container                       |
| `make healthcheck`       | Check the health endpoint                           |
| `make validate`          | Validate Podman, the compose file, `~/config` and `~/container-data` |
| `make test`              | Build, start and check the endpoints                |
| `make backup`            | Back up data, configuration and state               |

Run `make help` for the complete list.

## Configuration

Configuration lives in the sibling `~/config` directory, not in this checkout.
`deployment.env` holds the deployment defaults shared by the Makefile, the
scripts and the compose file. `backend.env` holds the runtime settings the
container reads on every start. `authorization.env`, the manifest and the group
file hold the authorization inputs.

### Deployment defaults: `~/config/deployment.env`

`make setup` copies `.env.example` to `~/config/deployment.env` when that file
is absent. Edit the deployed copy rather than the scripts or the Makefile. It
sets the image, the git repository and branch, the host port, the configuration
and data path overrides, the compose project name, the container name, and the
frontend build arguments.

Values resolve with this precedence, highest first:

1. command line — `make IMAGE_NAME=shape-shifter:dev up`
2. environment — `IMAGE_NAME=shape-shifter:dev make up`
3. `~/config/deployment.env`
4. the fallbacks built into the Makefile

A relative `CONFIG_DIR` or `DATA_DIR` value names a path beside the checkout, so
`DATA_DIR=container-data` and `DATA_DIR=../container-data` both mean
`~/container-data`. Explicit overrides exist for tests and alternate layouts:
`make CONFIG_DIR=/tmp/shape-config DATA_DIR=/tmp/shape-data config`.

`make build` tags its output from the git ref when the ref is not a release
version, so `GIT_REF=dev` produces `shape-shifter:dev`. Set `IMAGE_NAME` to that
same tag: `make up` starts `IMAGE_NAME`, not the image that was just built, and
`make build` warns when the two differ. `GIT_REF` accepts a branch or a release
tag.

`~/config/deployment.env` is never tracked by git, and `container/.env.example`
is tracked and holds the defaults. There is no fallback to `container/.env` or
`container-data/backend.env`; those paths are retired.

### Image identity

Each build labels the image with the source commit
(`org.opencontainers.image.revision`), the ref, the repository and the build
date, and prints the commit and the image digest when it finishes. Check which
source a running container came from with:

```bash
podman inspect shape-shifter --format '{{index .Config.Labels "org.opencontainers.image.revision"}}'
```

A build from a GitHub ref records that ref commit. A `make build-local` build
records the checkout commit, and appends `-dirty` when the checkout has
uncommitted changes, because the commit alone would not describe the image.

### Runtime configuration: `~/config/backend.env`

Runtime configuration lives in `~/config/backend.env`. It is mounted as the
service `env_file`, so editing it only needs `make restart`.

Production settings raised by the backend configuration:

- `SHAPE_SHIFTER_ENVIRONMENT=production` requires
  `SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=true` and a non-empty
  `SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS`.
- The reverse proxy must send the authenticated username in the
  `X-Authenticated-User` header (see `scripts/deploy/nginx-shape-shifter.conf.template`).

Keep `backend.env` and `.pgpass/.pgpass` readable only by the deployment user:

```bash
chmod 600 ~/config/backend.env ~/config/.pgpass/.pgpass
```

`~/config` itself is mode `700` and owned by the deployment user, which covers
`authorization.env`, the manifest, and the group file as well. None of those are
mounted into the container.

### Rootless ownership

The compose service uses `userns_mode: "keep-id"`, which maps the deployment
user to the same UID/GID inside the container. `scripts/build.sh` passes
`USER_UID`/`USER_GID` from `id -u`/`id -g`, so the non-root container user owns
the bind-mounted data directories.

### Frontend build variables

`VITE_*` values are compiled into the JavaScript bundle and therefore require a
rebuild. They come from `~/config/deployment.env` and reach the build as
arguments (see `podman-compose.yml` and `Containerfile`); they are not read from
`backend.env`.

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md): initial deployment, multiple environments, NGINX and systemd.
- `make status`, `make healthcheck` and `make logs` are the first diagnostic steps.

**Podman:** 4.0+ (built and tested with 5.7)
**Platform:** Linux with systemd
