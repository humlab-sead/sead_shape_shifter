#!/usr/bin/env bash
# Prepare the Podman deployment: configuration directory, data directories,
# deployment settings, runtime environment and PostgreSQL credentials.
#
# Configuration is written to CONFIG_DIR (default ~/config) and mutable data to
# DATA_DIR (default ~/container-data). Nothing is written into this checkout.
# Safe to run more than once; existing files are left untouched.
set -euo pipefail

# Load CONFIG_DIR/deployment.env values that the environment has not already
# set, and resolve the CONFIG_DIR and DATA_DIR defaults.
# shellcheck source=load-env.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/load-env.sh"

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
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
log_info "Creating configuration directory..."
mkdir -p "$CONFIG_DIR"
chmod 700 "$CONFIG_DIR"
log_success "Configuration directory ready: $CONFIG_DIR"

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
if [ -f "$CONFIG_DIR/deployment.env" ]; then
  log_warning "deployment.env already exists, leaving it unchanged"
  log_info "Edit with: nano $CONFIG_DIR/deployment.env"
else
  if [ -f "$ROOT_DIR/.env.example" ]; then
    cp "$ROOT_DIR/.env.example" "$CONFIG_DIR/deployment.env"
    log_success "Created $CONFIG_DIR/deployment.env from container/.env.example"
    log_warning "Review the image, branch, port and frontend build args in it"
  else
    log_warning "container/.env.example not found, the Makefile defaults apply"
  fi
fi

echo
log_info "Setting up environment configuration..."
if [ -f "$CONFIG_DIR/backend.env" ]; then
  log_warning "backend.env already exists, leaving it unchanged"
  log_info "Edit with: nano $CONFIG_DIR/backend.env"
else
  if [ -f "$RESOURCES_DIR/backend.env.example" ]; then
    cp "$RESOURCES_DIR/backend.env.example" "$CONFIG_DIR/backend.env"
    chmod 600 "$CONFIG_DIR/backend.env"
    log_success "Created $CONFIG_DIR/backend.env from resources/backend.env.example"
    log_warning "Edit required: nano $CONFIG_DIR/backend.env"
  else
    log_error "resources/backend.env.example not found at $RESOURCES_DIR/backend.env.example"
    exit 1
  fi
fi

echo
log_info "Setting up PostgreSQL password file..."
mkdir -p "$CONFIG_DIR/.pgpass"
chmod 700 "$CONFIG_DIR/.pgpass"
if [ -f "$CONFIG_DIR/.pgpass/.pgpass" ]; then
  log_warning ".pgpass already exists, leaving it unchanged"
else
  if [ -f "$RESOURCES_DIR/.pgpass.example" ]; then
    cp "$RESOURCES_DIR/.pgpass.example" "$CONFIG_DIR/.pgpass/.pgpass"
  else
    touch "$CONFIG_DIR/.pgpass/.pgpass"
  fi
  chmod 600 "$CONFIG_DIR/.pgpass/.pgpass"
  log_success "Created $CONFIG_DIR/.pgpass/.pgpass"
fi

echo
log_info "Checking authorization inputs..."
# The authorization bootstrap imports credentials, policy and group membership
# that the operator provisions by hand. Setup reports what is missing and never
# generates or copies those files.
missing_authorization_files=false
for authorization_file in authorization.env authorization-manifest.yaml groups.d/shape-shifter.conf; do
  if [ -f "$CONFIG_DIR/$authorization_file" ]; then
    log_success "Found $CONFIG_DIR/$authorization_file"
  else
    missing_authorization_files=true
    log_warning "Missing $CONFIG_DIR/$authorization_file"
  fi
done
if [ "$missing_authorization_files" = true ]; then
  log_info "Provision these before running the authorization bootstrap."
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
echo "1. Review deployment settings:    nano $CONFIG_DIR/deployment.env"
echo "2. Edit the runtime environment:  nano $CONFIG_DIR/backend.env"
echo "3. Edit PostgreSQL credentials:   nano $CONFIG_DIR/.pgpass/.pgpass"
echo "4. Provision authorization:       $CONFIG_DIR/authorization.env"
echo "                                   $CONFIG_DIR/authorization-manifest.yaml"
echo "                                   $CONFIG_DIR/groups.d/shape-shifter.conf"
echo "5. Build the image:                make build"
echo "6. Start the container:            make up"
echo "7. Check health:                   make healthcheck"
