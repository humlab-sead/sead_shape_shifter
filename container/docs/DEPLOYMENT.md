# Podman Deployment Guide

High-level guide for deploying Shape Shifter to production. For detailed tool documentation, see the Makefile and `scripts/setup.sh`.

## Quick Navigation

- **Single environment**: [Quick Deploy](#quick-single-deploy)
- **Multiple environments**: repeat the single-environment setup for each dedicated user
- **NGINX setup**: [NGINX Reverse Proxy](#nginx-reverse-proxy)
- **Auto-start**: [Systemd Integration](#systemd-integration)
- **Diagnostics**: `make status`, `make healthcheck`, and `make logs`

---

## Prerequisites

System-level setup (one-time per server):

```bash
# 1. Install Podman
sudo apt-get update && sudo apt-get install -y podman podman-compose

# 2. Verify user namespaces enabled
podman unshare id

# 3. For each environment, create a dedicated user
USER="shapeshifter-test"  # Change to your environment name
sudo useradd -r -m -s /bin/bash "$USER"

# 4. Enable lingering (containers persist after logout)
sudo loginctl enable-linger "$USER"
```

---

## Quick Single Deploy

Run the setup as the dedicated environment user from the repository's `container/` directory:

```bash
bash scripts/setup.sh
make build
make up
```

After setup, edit the environment file and verify the service:

```bash
sudo -u shapeshifter-test nano ~/container-data/backend.env
sudo -u shapeshifter-test curl http://localhost:8012/api/v1/health
```

Repeat these steps for each environment. Set a different `HOST_PORT` when environments share a host:

```bash
HOST_PORT=8013 make up
```

See `make help` for other commands (logs, status, backup, restart, and service control).

---

## NGINX Reverse Proxy

Configure NGINX to proxy HTTPS traffic to Podman using the provided helper and template:

```bash
sudo container/scripts/deploy/install_nginx_reverse_proxy.sh shapeshifter.example.com 8012
```

The script renders the config from [container/scripts/deploy/nginx-shape-shifter.conf.template](../scripts/deploy/nginx-shape-shifter.conf.template), installs it under `/etc/nginx/sites-available/`, and reloads NGINX. For a custom domain or port, pass the values as arguments.

---

## Systemd Integration

Auto-start containers on boot using systemd user services with the helper script:

```bash
container/scripts/deploy/install_systemd_service.sh shapeshifter-test
```

This installs and enables the user-level `shape-shifter` service. See [container/scripts/deploy/install_systemd_service.sh](../scripts/deploy/install_systemd_service.sh). Then use standard `systemctl --user -M <USER>@ ...` commands for runtime control.

---

## Common Operations

All operations via Makefile. Run from `~/container`:

| Task          | Command                                              |
|---------------|------------------------------------------------------|
| View logs     | `make logs`                                          |
| Check health  | `make healthcheck`                                   |
| Create backup | `make backup`                                        |
| Restart       | `nano ../container-data/backend.env && make restart` |
| Status        | `make status`                                        |
| Shell access  | `make shell`                                         |

See `make help` for complete list.

---

## Reference

- **scripts/setup.sh** - Automates initial setup (pre-flight checks, directories, env files)
- **Makefile** - 25+ targets (build, start, logs, backup, systemd, etc.)
- **backend.env.example** - Committed template listing all configurable environment variables (placeholders only)
- **Podman documentation** - Host-level container diagnostics and administration

---

**Last Updated**: 2026-09-10  
**Podman**: 4.0+  
**Platform**: Linux with systemd
