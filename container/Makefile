SHELL := /bin/bash
.DEFAULT_GOAL := help

# Podman container and image names
CONTAINER_NAME := shape-shifter
IMAGE_NAME := shape-shifter:latest

# Port configuration
HOST_PORT ?= 8012

# User ID settings for Podman rootless (defaults to current user)
USER_UID ?= $(shell id -u)
USER_GID ?= $(shell id -g)

# Data directory (relative to home, will be expanded by Makefile)
DATA_DIR ?= ../container-data

# Absolute path for podman-compose (required for rootless Podman)
PWD_ABS := $(shell pwd)
COMPOSE_PROJECT_NAME ?= shapeshifter

# Color output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m  # No Color

SCRIPTS_DIR := ./scripts

.PHONY: check-podman
check-podman:
	@command -v podman >/dev/null 2>&1 || { echo "$(RED)✗ Podman not found. Install: sudo apt-get install podman$(NC)"; exit 1; }
	@command -v podman-compose >/dev/null 2>&1 || { echo "$(RED)✗ podman-compose not found. Install: sudo apt-get install podman-compose$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Podman $(shell podman --version)$(NC)"
	@echo "$(GREEN)✓ podman-compose $(shell podman-compose --version)$(NC)"

.PHONY: help
help:
	@echo "$(BLUE)=== Shape Shifter Podman Setup ===$(NC)"
	@echo ""
	@echo "$(GREEN)First-time setup:$(NC)"
	@echo "  make setup              Create directories and environment files"
	@echo ""
	@echo "$(GREEN)Build & Run:$(NC)"
	@echo "  make build              Build container image"
	@echo "  make up                 Start container"
	@echo "  make down               Stop container"
	@echo "  make restart            Restart container"
	@echo ""
	@echo "$(GREEN)Diagnostics:$(NC)"
	@echo "  make logs               Follow container logs"
	@echo "  make status             Show container status"
	@echo "  make ps                 List containers"
	@echo "  make shell              Enter container shell"
	@echo "  make healthcheck        Manual health check"
	@echo ""
	@echo "$(GREEN)Maintenance:$(NC)"
	@echo "  make backup             Backup data directory"
	@echo "  make update-env         Update environment variables (edit then restart)"
	@echo "  make clean              Remove container (keep data)"
	@echo "  make prune              Remove container and dangling images"
	@echo "  make system-prune       Full Podman system prune (removes all unused)"
	@echo ""
	@echo "$(GREEN)Systemd integration:$(NC)"
	@echo "  make service-install    Install systemd user service"
	@echo "  make service-start      Start via systemd service"
	@echo "  make service-stop       Stop via systemd service"
	@echo "  make service-status     Check systemd service status"
	@echo "  make service-enable     Enable auto-start on boot"
	@echo "  make service-disable    Disable auto-start"
	@echo "  make service-logs       Follow systemd service logs"
	@echo ""
	@echo "$(YELLOW)Usage:$(NC)"
	@echo "  make setup"
	@echo "  make build"
	@echo "  make up"
	@echo "  curl http://localhost:$(HOST_PORT)/api/v1/health"
	@echo ""

# ============================================================================
# Setup Targets
# ============================================================================

.PHONY: setup
setup: check-podman
	@DATA_DIR="$(DATA_DIR)" ./scripts/setup.sh

.PHONY: setup-directories
setup-directories: check-podman
	@mkdir -p "$(DATA_DIR)"/{projects,shared,logs,output,backups,tmp}
	@chmod -R 755 "$(DATA_DIR)"
	@echo "$(GREEN)✓ Created data directories in $(DATA_DIR)$(NC)"

.PHONY: setup-env
setup-env: check-podman
	@if [ ! -f "$(DATA_DIR)/backend.env" ]; then \
		if [ -f "backend.env.example" ]; then \
			cp backend.env.example "$(DATA_DIR)/backend.env"; \
			echo "$(GREEN)✓ Created $(DATA_DIR)/backend.env from backend.env.example$(NC)"; \
			echo "$(YELLOW)  Edit this file and restart the container to apply changes$(NC)"; \
		else \
			echo "$(YELLOW)⚠ backend.env.example not found, create $(DATA_DIR)/backend.env manually$(NC)"; \
		fi \
	else \
		echo "$(GREEN)✓ $(DATA_DIR)/backend.env already exists$(NC)"; \
	fi

# ============================================================================
# Build Targets
# ============================================================================

.PHONY: build
build: check-podman
	@USER_UID="$(USER_UID)" USER_GID="$(USER_GID)" $(SCRIPTS_DIR)/build.sh

.PHONY: build-no-cache
build-no-cache: check-podman
	@echo "$(BLUE)Building container image (no cache)...$(NC)"
	podman-compose \
		-f podman-compose.yml \
		build \
		--no-cache \
		--build-arg USER_UID=$(USER_UID) \
		--build-arg USER_GID=$(USER_GID)
	@echo "$(GREEN)✓ Build complete$(NC)"

# ============================================================================
# Container Lifecycle
# ============================================================================

.PHONY: up
up: check-podman
	@HOST_PORT="$(HOST_PORT)" COMPOSE_PROJECT_NAME="$(COMPOSE_PROJECT_NAME)" $(SCRIPTS_DIR)/up.sh

.PHONY: down
down:
	@COMPOSE_PROJECT_NAME="$(COMPOSE_PROJECT_NAME)" $(SCRIPTS_DIR)/down.sh

.PHONY: restart
restart: down up
	@echo "$(GREEN)✓ Container restarted$(NC)"

# ============================================================================
# Diagnostics
# ============================================================================

.PHONY: logs
logs:
	@COMPOSE_PROJECT_NAME="$(COMPOSE_PROJECT_NAME)" $(SCRIPTS_DIR)/logs.sh

.PHONY: ps
ps:
	@podman ps --filter=name=$(CONTAINER_NAME)

.PHONY: status
status:
	@CONTAINER_NAME="$(CONTAINER_NAME)" $(SCRIPTS_DIR)/status.sh

.PHONY: shell
shell:
	@echo "$(BLUE)Entering container shell (type 'exit' to quit)...$(NC)"
	podman exec -it $(CONTAINER_NAME) bash

.PHONY: healthcheck
healthcheck:
	@CONTAINER_NAME="$(CONTAINER_NAME)" $(SCRIPTS_DIR)/healthcheck.sh

# ============================================================================
# Maintenance
# ============================================================================

.PHONY: backup
backup:
	@DATA_DIR="$(DATA_DIR)" $(SCRIPTS_DIR)/backup.sh

.PHONY: update-env
update-env:
	@echo "$(BLUE)Opening environment editor...$(NC)"
	@echo "$(YELLOW)After editing, run: make restart$(NC)"
	nano "$(DATA_DIR)/backend.env"

.PHONY: clean
clean: down
	@echo "$(BLUE)Removing container (keeping data)...$(NC)"
	podman rm -f $(CONTAINER_NAME) 2>/dev/null || true
	@echo "$(GREEN)✓ Container removed$(NC)"

.PHONY: prune
prune: clean
	@echo "$(BLUE)Removing images...$(NC)"
	podman rmi -f $(IMAGE_NAME) 2>/dev/null || true
	@echo "$(GREEN)✓ Images removed$(NC)"

.PHONY: system-prune
system-prune:
	@echo "$(YELLOW)WARNING: This removes all unused Podman resources$(NC)"
	@read -p "Continue? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		podman system prune -af; \
		echo "$(GREEN)✓ System pruned$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# ============================================================================
# Systemd User Service Integration
# ============================================================================

.PHONY: service-install
service-install:
	@$(SCRIPTS_DIR)/service-install.sh

.PHONY: service-enable
service-enable:
	systemctl --user enable shape-shifter
	@echo "$(GREEN)✓ Service enabled for auto-start$(NC)"

.PHONY: service-disable
service-disable:
	systemctl --user disable shape-shifter
	@echo "$(GREEN)✓ Service disabled$(NC)"

.PHONY: service-start
service-start:
	systemctl --user start shape-shifter
	@echo "$(GREEN)✓ Service started$(NC)"

.PHONY: service-stop
service-stop:
	systemctl --user stop shape-shifter
	@echo "$(GREEN)✓ Service stopped$(NC)"

.PHONY: service-status
service-status:
	systemctl --user status shape-shifter

.PHONY: service-logs
service-logs:
	journalctl --user -u shape-shifter -f

# ============================================================================
# Utilities
# ============================================================================

.PHONY: info
info:
	@echo "$(BLUE)=== Configuration ===$(NC)"
	@echo "Container Name: $(CONTAINER_NAME)"
	@echo "Image:          $(IMAGE_NAME)"
	@echo "Port:           $(HOST_PORT)"
	@echo "User UID:       $(USER_UID)"
	@echo "User GID:       $(USER_GID)"
	@echo "Data Dir:       $(DATA_DIR)"
	@echo ""
	@echo "$(BLUE)=== Podman Info ===$(NC)"
	@podman info --format "Rootless: {{.Host.Security.Rootless}}"
	@echo "Podman Version: $(shell podman --version)"
	@echo "Compose Version: $(shell podman-compose --version)"

.PHONY: version
version:
	@podman --version
	@podman-compose --version

.PHONY: env-vars
env-vars:
	@echo "$(BLUE)Current environment variables:$(NC)"
	@env | grep -E "^(USER_UID|USER_GID|HOST_PORT|DATA_DIR|PWD)" || echo "None set"

.PHONY: validate
validate: check-podman
	@echo "$(BLUE)Validating setup...$(NC)"
	@[ -d "$(DATA_DIR)" ] && echo "$(GREEN)✓ Data directory exists$(NC)" || echo "$(RED)✗ Data directory missing$(NC)"
	@[ -f "$(DATA_DIR)/backend.env" ] && echo "$(GREEN)✓ Environment file exists$(NC)" || echo "$(YELLOW)⚠ Environment file missing$(NC)"
	@echo "$(BLUE)Podman health:$(NC)"
	@podman info >/dev/null 2>&1 && echo "$(GREEN)✓ Podman socket accessible$(NC)" || echo "$(RED)✗ Podman socket not accessible$(NC)"
	@echo "$(GREEN)✓ Validation complete$(NC)"
