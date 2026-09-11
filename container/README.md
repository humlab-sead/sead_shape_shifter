# Shape Shifter Podman Deployment

This directory contains the Podman deployment for Shape Shifter. It supports rootless containers, systemd user services, dedicated environment users, and NGINX as an HTTPS reverse proxy.

## Prerequisites

- Linux with Podman 4.0 or later
- `podman-compose`
- systemd user services
- A dedicated user account for each deployed environment
- Sufficient disk space for projects, logs, outputs, and backups

Install the packages on Debian or Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y podman podman-compose
sudo loginctl enable-linger "$USER"
podman unshare id
```

## Quick Start

Run these commands as the environment user from the repository's `container/` directory:

```bash
make setup
nano ../container-data/backend.env
make build
make up
make healthcheck
```

The application is available at `http://localhost:8012/` by default. Set `HOST_PORT` when another host port is required:

```bash
HOST_PORT=8013 make up
```

For deployment to dedicated users, multiple environments, NGINX, and systemd installation, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Common Commands

Run these from `container/`:

| Command                | Purpose                                          |
|------------------------|--------------------------------------------------|
| `make setup`           | Create data directories and the environment file |
| `make build`           | Build the image                                  |
| `make up`              | Start the container                              |
| `make down`            | Stop the container                               |
| `make restart`         | Restart the container                            |
| `make logs`            | Follow container logs                            |
| `make status`          | Show container status                            |
| `make shell`           | Open a shell in the container                    |
| `make healthcheck`     | Check the health endpoint                        |
| `make backup`          | Create a data backup                             |
| `make service-install` | Install the systemd user service                 |

Run `make help` for the complete target list.

## Data and Configuration

Persistent data is stored beside the container directory:

```text
../container-data/
├── projects/
├── shared/
├── logs/
├── output/
├── backups/
├── tmp/
├── backend.env
└── .pgpass/
```

Keep `backend.env` and `.pgpass` readable only by the environment user. Edit `backend.env` and restart the container when runtime settings change:

```bash
chmod 600 ../container-data/backend.env ../container-data/.pgpass/.pgpass
make restart
```

## Documentation

- [Deployment guide](DEPLOYMENT.md): initial deployment, multiple environments, NGINX, and systemd.
- For diagnosis, start with `make status`, `make healthcheck`, and `make logs`, then use the standard Podman and systemd tools for the host environment.

The deployment helpers are in `scripts/deploy/`, and the container lifecycle helpers are in `scripts/`.

## Support Checks

```bash
podman ps
make status
make healthcheck
make logs
```

**Podman version:** 4.0+
**Platform:** Linux with systemd
