#!/bin/bash
# ============================================================================
# Shape Shifter Podman Setup Script
# ============================================================================
# User-agnostic setup for deployment to any dedicated user account.
# Run as the dedicated user (e.g., test-shape-shifter.sead.se)
#
# Usage:
#   cd ~/container
#   bash setup.sh
#
# Or from deployment script:
#   sudo -u test-shape-shifter.sead.se bash setup.sh
#
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../container-data"
SERVICE_DIR="${SCRIPT_DIR}/service"

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

log_success() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    echo -e "${RED}✗${NC} $*"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

preflight_checks() {
    log_info "Running pre-flight checks..."
    
    # Check Podman installation
    if ! check_command podman; then
        log_error "Podman not found"
        echo "Install Podman:"
        echo "  Ubuntu/Debian: sudo apt-get install -y podman podman-compose"
        echo "  RHEL/CentOS:   sudo yum install -y podman podman-compose"
        return 1
    fi
    log_success "Podman $(podman --version)"
    
    # Check podman-compose installation
    if ! check_command podman-compose; then
        log_error "podman-compose not found"
        echo "Install podman-compose:"
        echo "  sudo apt-get install -y podman-compose"
        return 1
    fi
    log_success "podman-compose $(podman-compose --version)"
    
    # Check we're running as a regular user (not root)
    if [ "$EUID" -eq 0 ]; then
        log_warning "Running as root - container will run as root"
        log_info "Recommended: Run this script as the dedicated user instead"
    else
        log_success "Running as user: $(whoami)"
    fi
    
    # Check systemd user session
    if systemctl --user is-active --quiet user@$(id -u).service; then
        log_success "Systemd user session is active"
    else
        log_warning "Systemd user session may not be active"
        log_info "Enable lingering: sudo loginctl enable-linger $(whoami)"
    fi
    
    return 0
}

# ============================================================================
# Setup Functions
# ============================================================================

setup_directories() {
    log_info "Creating data directories..."
    
    mkdir -p "$DATA_DIR"/{projects,shared,logs,output,backups,tmp,.pgpass}
    chmod 755 "$DATA_DIR"
    chmod 700 "$DATA_DIR"/.pgpass  # Restrictive for credentials
    
    log_success "Data directory created: $DATA_DIR"
    log_success "Subdirectories: projects, shared, logs, output, backups, tmp"
}

setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [ -f "$DATA_DIR/backend.env" ]; then
        log_warning "backend.env already exists, skipping"
        log_info "Edit with: nano $DATA_DIR/backend.env"
    else
        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            cp "$SCRIPT_DIR/.env.example" "$DATA_DIR/backend.env"
            chmod 600 "$DATA_DIR/backend.env"
            log_success "Created backend.env from template"
            log_warning "Edit required: nano $DATA_DIR/backend.env"
        else
            log_error ".env.example not found at $SCRIPT_DIR/.env.example"
            log_info "Create manually: cp .env.example $DATA_DIR/backend.env"
            return 1
        fi
    fi
}

setup_service() {
    log_info "Setting up systemd user service..."
    
    if [ ! -f "$SERVICE_DIR/shape-shifter.service" ]; then
        log_warning "service/shape-shifter.service not found"
        log_info "To install systemd service later, run: make service-install"
        return 0
    fi
    
    mkdir -p ~/.config/systemd/user
    cp "$SERVICE_DIR/shape-shifter.service" ~/.config/systemd/user/
    
    # Reload systemd user daemon
    systemctl --user daemon-reload 2>/dev/null || {
        log_warning "Could not reload systemd (session may not be active yet)"
        log_info "After login, run: systemctl --user daemon-reload"
    }
    
    log_success "Systemd user service template installed"
    log_info "To enable auto-start: systemctl --user enable shape-shifter"
}

show_next_steps() {
    log_info "Setup complete!"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo ""
    echo "1. Edit environment configuration:"
    echo "   nano $DATA_DIR/backend.env"
    echo ""
    echo "2. Build container image:"
    echo "   cd $SCRIPT_DIR"
    echo "   make build"
    echo ""
    echo "3. Start the application:"
    echo "   make up"
    echo ""
    echo "4. Verify it's running:"
    echo "   curl http://localhost:8012/api/v1/health"
    echo ""
    echo -e "${BLUE}Optional: Enable Auto-Start${NC}"
    echo ""
    echo "5. Install systemd service (for auto-start on boot):"
    echo "   make service-install"
    echo "   systemctl --user enable shape-shifter"
    echo ""
    echo "6. Enable lingering (if not already enabled):"
    echo "   sudo loginctl enable-linger $(whoami)"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo ""
    echo "  make help          Show all available commands"
    echo "  make logs          Follow container logs"
    echo "  make shell         Enter container shell"
    echo "  make status        Show container status"
    echo "  make backup        Create data backup"
    echo ""
}

# ============================================================================
# Main
# ============================================================================

main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Shape Shifter Podman Setup${NC}                           ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Run setup stages
    preflight_checks || exit 1
    echo ""
    setup_directories
    echo ""
    setup_environment || log_warning "Environment setup incomplete"
    echo ""
    setup_service
    echo ""
    
    show_next_steps
}

main "$@"
