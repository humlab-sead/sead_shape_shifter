#!/usr/bin/env bash
# Prepare the Podman deployment: directories, environment file and .pgpass.
# Safe to run more than once; existing files are left untouched.
set -euo pipefail

# Load container/.env values that the environment has not already set.
# shellcheck source=load-env.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/load-env.sh"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="${DATA_DIR:-$ROOT_DIR/../container-data}"
SERVICE_DIR="${ROOT_DIR}/service"
RESOURCES_DIR="${ROOT_DIR}/resources"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}i${NC} $*"; }
log_success() { echo -e "${GREEN}+${NC} $*"; }
log_warning() { echo -e "${YELLOW}!${NC} $*"; }
log_error() { echo -e "${RED}x${NC} $*"; }

check_command() { command -v "$1" >/dev/null 2>&1; }

log_info "Running pre-flight checks..."
if ! check_command podman; then
  log_error "Podman not found"
  echo "Install Podman: sudo apt-get install -y podman podman-compose"
  exit 1
fi
log_success "Podman $(podman --version)"

if ! check_command podman-compose; then
  log_error "podman-compose not found"
  echo "Install podman-compose: sudo apt-get install -y podman-compose"
  exit 1
fi
log_success "podman-compose $(podman-compose --version 2>/dev/null | head -n1)"

if [ "$EUID" -eq 0 ]; then
  log_error "Run setup as the dedicated environment user, not root."
  exit 1
else
  log_success "Running as user: $(whoami) (uid $(id -u), gid $(id -g))"
fi

if systemctl --user is-active --quiet "user@$(id -u).service"; then
  log_success "Systemd user session is active"
else
  log_warning "Systemd user session may not be active"
  log_info "Enable lingering: sudo loginctl enable-linger $(whoami)"
fi

echo
log_info "Creating data directories..."
mkdir -p "$DATA_DIR"/{projects,shared,logs,output,backups,tmp,state}
chmod 755 "$DATA_DIR"
chmod 755 "$DATA_DIR"/{projects,shared,logs,output,backups,tmp,state}
runtime_owner="$(id -u):$(id -g)"
if ! chown -R "$runtime_owner" "$DATA_DIR"/{projects,shared,logs,output,backups,tmp,state}; then
  log_error "Could not assign writable data to $runtime_owner"
  log_error "Fix ownership as an administrator, then rerun setup as $(whoami)."
  exit 1
fi
log_success "Data directory ready: $DATA_DIR"
log_success "Subdirectories: projects, shared, logs, output, backups, tmp, state"
log_success "Writable bind mounts owned by $runtime_owner for userns keep-id"

echo
log_info "Setting up deployment defaults..."
if [ -f "$ROOT_DIR/.env" ]; then
  log_warning "container/.env already exists, leaving it unchanged"
  log_info "Edit with: nano $ROOT_DIR/.env"
else
  if [ -f "$ROOT_DIR/.env.example" ]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    log_success "Created container/.env from container/.env.example"
    log_warning "Review the image, branch, port and frontend build args in it"
  else
    log_warning "container/.env.example not found, the Makefile defaults apply"
  fi
fi

echo
log_info "Setting up environment configuration..."
if [ -f "$DATA_DIR/backend.env" ]; then
  log_warning "backend.env already exists, leaving it unchanged"
  log_info "Edit with: nano $DATA_DIR/backend.env"
else
  if [ -f "$RESOURCES_DIR/backend.env.example" ]; then
    cp "$RESOURCES_DIR/backend.env.example" "$DATA_DIR/backend.env"
    chmod 600 "$DATA_DIR/backend.env"
    log_success "Created backend.env from resources/backend.env.example"
    log_warning "Edit required: nano $DATA_DIR/backend.env"
  else
    log_error "resources/backend.env.example not found at $RESOURCES_DIR/backend.env.example"
    exit 1
  fi
fi

echo
log_info "Setting up PostgreSQL password file..."
mkdir -p "$DATA_DIR/.pgpass"
chmod 700 "$DATA_DIR/.pgpass"
if [ -f "$DATA_DIR/.pgpass/.pgpass" ]; then
  log_warning ".pgpass already exists, leaving it unchanged"
else
  if [ -f "$RESOURCES_DIR/.pgpass.example" ]; then
    cp "$RESOURCES_DIR/.pgpass.example" "$DATA_DIR/.pgpass/.pgpass"
  else
    touch "$DATA_DIR/.pgpass/.pgpass"
  fi
  chmod 600 "$DATA_DIR/.pgpass/.pgpass"
  log_success "Created $DATA_DIR/.pgpass/.pgpass"
fi

echo
log_info "Checking UCanAccess JARs..."
if [ -d "$ROOT_DIR/lib/ucanaccess" ]; then
  log_success "UCanAccess found at $ROOT_DIR/lib/ucanaccess"
else
  log_warning "Missing $ROOT_DIR/lib/ucanaccess"
  log_info "MS Access data sources need it. Install with: make install-ucanaccess"
fi

echo
log_info "Setting up systemd user service..."
if [ ! -f "$SERVICE_DIR/shape-shifter.service" ]; then
  log_warning "service/shape-shifter.service not found, skipping"
else
  mkdir -p ~/.config/systemd/user
  cp "$SERVICE_DIR/shape-shifter.service" ~/.config/systemd/user/
  systemctl --user daemon-reload 2>/dev/null || \
    log_warning "Could not reload systemd yet; run 'systemctl --user daemon-reload' after login"
  log_success "Systemd user service installed"
  log_info "Enable auto-start with: systemctl --user enable shape-shifter"
fi

echo
log_success "Setup complete"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Edit the environment file:  nano $DATA_DIR/backend.env"
echo "2. Build the image:            make build"
echo "3. Start the container:        make up"
echo "4. Check health:               make healthcheck"
