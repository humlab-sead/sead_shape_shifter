SHELL := /bin/bash
.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONTAINER_NAME := shape-shifter
IMAGE_NAME ?= shape-shifter:latest
HOST_PORT ?= 8012

# Rootless Podman keeps the deployment user, so build with the current UID/GID.
USER_UID ?= $(shell id -u)
USER_GID ?= $(shell id -g)

# Persistent data lives beside the container directory.
DATA_DIR ?= ../container-data
CONTAINER_DATA_DIR := $(abspath $(DATA_DIR))

COMPOSE_PROJECT_NAME ?= shapeshifter
COMPOSE_FILE := podman-compose.yml
SCRIPTS_DIR := ./scripts
RESOURCES_DIR := ./resources

# Image source for `make build`. Use `make build-local` for a checkout build.
GIT_REPO ?= https://github.com/humlab-sead/sead_shape_shifter.git
GIT_REF ?= main

# podman-compose reads every path from CONTAINER_DATA_DIR.
export CONTAINER_DATA_DIR
export DATA_DIR
export HOST_PORT
export IMAGE_NAME
export USER_UID
export USER_GID
export GIT_REPO
export GIT_REF
export COMPOSE_PROJECT_NAME

RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m

.PHONY: help
help:
	@echo "$(BLUE)=== Shape Shifter Podman Deployment ===$(NC)"
	@echo ""
	@echo "$(GREEN)First-time setup:$(NC)"
	@echo "  make install-ucanaccess  Install UCanAccess JARs (MS Access support)"
	@echo "  make setup               Create directories and environment files"
	@echo ""
	@echo "$(GREEN)Build and run:$(NC)"
	@echo "  make build               Build image from GitHub (GIT_REF=$(GIT_REF))"
	@echo "  make build-local         Build image from the local checkout"
	@echo "  make up                  Start the container"
	@echo "  make down                Stop the container"
	@echo "  make restart             Restart the container"
	@echo ""
	@echo "$(GREEN)Diagnostics:$(NC)"
	@echo "  make logs                Follow container logs"
	@echo "  make status              Show container status"
	@echo "  make ps                  List containers"
	@echo "  make shell               Open a shell in the container"
	@echo "  make healthcheck         Check the health endpoint"
	@echo "  make config              Render the resolved compose file"
	@echo "  make validate            Validate the local setup"
	@echo "  make test                Build, start and check the endpoints"
	@echo ""
	@echo "$(GREEN)Maintenance:$(NC)"
	@echo "  make backup              Back up data, configuration and state"
	@echo "  make update-env          Edit the environment file"
	@echo "  make clean               Remove the container (keep data)"
	@echo "  make prune               Remove the container and image"
	@echo "  make system-prune        Full Podman system prune (removes all unused)"
	@echo ""
	@echo "$(GREEN)Systemd integration:$(NC)"
	@echo "  make service-install     Install the systemd user service"
	@echo "  make service-enable      Enable auto-start on boot"
	@echo "  make service-start       Start via systemd"
	@echo "  make service-stop        Stop via systemd"
	@echo "  make service-status      Show systemd status"
	@echo "  make service-disable     Disable auto-start"
	@echo "  make service-logs        Follow systemd logs"
	@echo ""
	@echo "$(YELLOW)Quick start:$(NC)"
	@echo "  make setup && make build && make up"
	@echo "  curl http://localhost:$(HOST_PORT)/api/v1/health"
	@echo ""

# ===========================================================================
# Pre-flight
# ===========================================================================

.PHONY: check-podman
check-podman:
	@command -v podman >/dev/null 2>&1 || { echo "$(RED)x Podman not found. Install: sudo apt-get install podman$(NC)"; exit 1; }
	@command -v podman-compose >/dev/null 2>&1 || { echo "$(RED)x podman-compose not found. Install: sudo apt-get install podman-compose$(NC)"; exit 1; }
	@echo "$(GREEN)+ Podman $(shell podman --version)$(NC)"
	@echo "$(GREEN)+ podman-compose $(shell podman-compose --version 2>/dev/null | head -n1)$(NC)"

# ===========================================================================
# Setup
# ===========================================================================

.PHONY: setup
setup: check-podman
	@DATA_DIR="$(CONTAINER_DATA_DIR)" $(SCRIPTS_DIR)/setup.sh

.PHONY: setup-directories
setup-directories: check-podman
	@mkdir -p "$(CONTAINER_DATA_DIR)"/{projects,shared,logs,output,backups,tmp,state}
	@chmod 755 "$(CONTAINER_DATA_DIR)"
	@echo "$(GREEN)+ Created data directories in $(CONTAINER_DATA_DIR)$(NC)"

.PHONY: setup-env
setup-env: check-podman
	@if [ ! -f "$(CONTAINER_DATA_DIR)/backend.env" ]; then \
		if [ -f "$(RESOURCES_DIR)/backend.env.example" ]; then \
			cp "$(RESOURCES_DIR)/backend.env.example" "$(CONTAINER_DATA_DIR)/backend.env"; \
			chmod 600 "$(CONTAINER_DATA_DIR)/backend.env"; \
			echo "$(GREEN)+ Created $(CONTAINER_DATA_DIR)/backend.env$(NC)"; \
			echo "$(YELLOW)  Edit this file and restart the container to apply changes$(NC)"; \
		else \
			echo "$(YELLOW)! $(RESOURCES_DIR)/backend.env.example not found$(NC)"; \
		fi \
	else \
		echo "$(GREEN)+ $(CONTAINER_DATA_DIR)/backend.env already exists$(NC)"; \
	fi

.PHONY: install-ucanaccess
install-ucanaccess:
	@$(SCRIPTS_DIR)/install-ucanaccess.sh

# ===========================================================================
# Build
# ===========================================================================

.PHONY: build
build: check-podman
	@GIT_REPO="$(GIT_REPO)" GIT_REF="$(GIT_REF)" USER_UID="$(USER_UID)" USER_GID="$(USER_GID)" \
		$(SCRIPTS_DIR)/build.sh --git-ref "$(GIT_REF)" --git-repo "$(GIT_REPO)"

.PHONY: build-local
build-local: check-podman
	@USER_UID="$(USER_UID)" USER_GID="$(USER_GID)" $(SCRIPTS_DIR)/build.sh --local

.PHONY: build-no-cache
build-no-cache: check-podman
	@USER_UID="$(USER_UID)" USER_GID="$(USER_GID)" \
		$(SCRIPTS_DIR)/build.sh --git-ref "$(GIT_REF)" --git-repo "$(GIT_REPO)" --no-cache

# ===========================================================================
# Container lifecycle
# ===========================================================================

.PHONY: up
up: check-podman
	@DATA_DIR="$(CONTAINER_DATA_DIR)" HOST_PORT="$(HOST_PORT)" IMAGE_NAME="$(IMAGE_NAME)" \
		COMPOSE_PROJECT_NAME="$(COMPOSE_PROJECT_NAME)" $(SCRIPTS_DIR)/up.sh

.PHONY: down
down:
	@DATA_DIR="$(CONTAINER_DATA_DIR)" COMPOSE_PROJECT_NAME="$(COMPOSE_PROJECT_NAME)" $(SCRIPTS_DIR)/down.sh

.PHONY: restart
restart: down up
	@echo "$(GREEN)+ Container restarted$(NC)"

# ===========================================================================
# Diagnostics
# ===========================================================================

.PHONY: logs
logs:
	@DATA_DIR="$(CONTAINER_DATA_DIR)" COMPOSE_PROJECT_NAME="$(COMPOSE_PROJECT_NAME)" $(SCRIPTS_DIR)/logs.sh

.PHONY: ps
ps:
	@podman ps -a --filter=name=$(CONTAINER_NAME)

.PHONY: status
status:
	@CONTAINER_NAME="$(CONTAINER_NAME)" $(SCRIPTS_DIR)/status.sh

.PHONY: shell
shell:
	@echo "$(BLUE)Entering container shell (type 'exit' to quit)...$(NC)"
	podman exec -it $(CONTAINER_NAME) bash

.PHONY: healthcheck
healthcheck:
	@CONTAINER_NAME="$(CONTAINER_NAME)" HOST_PORT="$(HOST_PORT)" $(SCRIPTS_DIR)/healthcheck.sh

.PHONY: config
config:
	@CONTAINER_DATA_DIR="$(CONTAINER_DATA_DIR)" podman-compose -f $(COMPOSE_FILE) config

# ===========================================================================
# Validation
# ===========================================================================

.PHONY: validate
validate: check-podman
	@echo "$(BLUE)Validating setup...$(NC)"
	@test -f Containerfile && echo "$(GREEN)+ Containerfile present$(NC)" || { echo "$(RED)x Containerfile missing$(NC)"; exit 1; }
	@test -f $(COMPOSE_FILE) && echo "$(GREEN)+ $(COMPOSE_FILE) present$(NC)" || { echo "$(RED)x $(COMPOSE_FILE) missing$(NC)"; exit 1; }
	@CONTAINER_DATA_DIR="$(CONTAINER_DATA_DIR)" podman-compose -f $(COMPOSE_FILE) config >/dev/null && echo "$(GREEN)+ Compose configuration is valid$(NC)"
	@test -d "$(CONTAINER_DATA_DIR)" && echo "$(GREEN)+ Data directory exists$(NC)" || echo "$(YELLOW)! Data directory missing (run make setup)$(NC)"
	@test -f "$(CONTAINER_DATA_DIR)/backend.env" && echo "$(GREEN)+ Environment file exists$(NC)" || echo "$(YELLOW)! Environment file missing (run make setup)$(NC)"
	@test -d "$(CONTAINER_DATA_DIR)/.pgpass" -a -f "$(CONTAINER_DATA_DIR)/.pgpass/.pgpass" && echo "$(GREEN)+ .pgpass file exists$(NC)" || echo "$(YELLOW)! .pgpass file missing (run make setup)$(NC)"
	@test -d lib/ucanaccess && echo "$(GREEN)+ UCanAccess JARs present$(NC)" || echo "$(YELLOW)! lib/ucanaccess missing (run make install-ucanaccess)$(NC)"
	@podman info >/dev/null 2>&1 && echo "$(GREEN)+ Podman is accessible$(NC)" || { echo "$(RED)x Podman is not accessible$(NC)"; exit 1; }
	@echo "$(GREEN)+ Validation complete$(NC)"

.PHONY: test
test: validate up
	@echo ""
	@echo "$(BLUE)Waiting for the health endpoint (max 60s)...$(NC)"
	@for i in {1..60}; do \
		if curl -sf "http://localhost:$(HOST_PORT)/api/v1/health" >/dev/null 2>&1; then \
			echo "$(GREEN)+ Application is healthy$(NC)"; break; \
		fi; \
		if [ $$i -eq 60 ]; then \
			echo "$(RED)x Health check timed out$(NC)"; podman logs shape-shifter --tail 50; exit 1; \
		fi; \
		sleep 1; \
	done
	@curl -sf "http://localhost:$(HOST_PORT)/" >/dev/null && echo "$(GREEN)+ Frontend responding$(NC)" || echo "$(RED)x Frontend failed$(NC)"
	@curl -sf "http://localhost:$(HOST_PORT)/api/v1/docs" >/dev/null && echo "$(GREEN)+ API docs responding$(NC)" || echo "$(YELLOW)! API docs not accessible$(NC)"
	@echo ""
	@echo "  Frontend: http://localhost:$(HOST_PORT)/"
	@echo "  API docs: http://localhost:$(HOST_PORT)/api/v1/docs"
	@echo "  Health:   http://localhost:$(HOST_PORT)/api/v1/health"

# ===========================================================================
# Maintenance
# ===========================================================================

.PHONY: backup
backup:
	@DATA_DIR="$(CONTAINER_DATA_DIR)" $(SCRIPTS_DIR)/backup.sh

.PHONY: update-env
update-env:
	@echo "$(BLUE)Opening environment file...$(NC)"
	@echo "$(YELLOW)After editing, run: make restart$(NC)"
	${EDITOR:-nano} "$(CONTAINER_DATA_DIR)/backend.env"

.PHONY: clean
clean: down
	@echo "$(BLUE)Removing container (keeping data)...$(NC)"
	@podman rm -f $(CONTAINER_NAME) 2>/dev/null || true
	@echo "$(GREEN)+ Container removed$(NC)"

.PHONY: prune
prune: clean
	@echo "$(BLUE)Removing image...$(NC)"
	@podman rmi -f $(IMAGE_NAME) 2>/dev/null || true
	@echo "$(GREEN)+ Image removed$(NC)"

.PHONY: system-prune
system-prune:
	@echo "$(YELLOW)WARNING: this removes all unused Podman resources$(NC)"
	@read -p "Continue? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		podman system prune -af; \
		echo "$(GREEN)+ System pruned$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# ===========================================================================
# Systemd user service
# ===========================================================================

.PHONY: service-install
service-install:
	@$(SCRIPTS_DIR)/service-install.sh

.PHONY: service-enable
service-enable:
	systemctl --user enable shape-shifter
	@echo "$(GREEN)+ Service enabled for auto-start$(NC)"

.PHONY: service-disable
service-disable:
	systemctl --user disable shape-shifter
	@echo "$(GREEN)+ Service disabled$(NC)"

.PHONY: service-start
service-start:
	systemctl --user start shape-shifter
	@echo "$(GREEN)+ Service started$(NC)"

.PHONY: service-stop
service-stop:
	systemctl --user stop shape-shifter
	@echo "$(GREEN)+ Service stopped$(NC)"

.PHONY: service-status
service-status:
	systemctl --user status shape-shifter

.PHONY: service-logs
service-logs:
	journalctl --user -u shape-shifter -f

# ===========================================================================
# Utilities
# ===========================================================================

.PHONY: info
info:
	@echo "$(BLUE)=== Configuration ===$(NC)"
	@echo "Container name: $(CONTAINER_NAME)"
	@echo "Image:          $(IMAGE_NAME)"
	@echo "Port:           $(HOST_PORT)"
	@echo "User UID/GID:   $(USER_UID)/$(USER_GID)"
	@echo "Data dir:       $(CONTAINER_DATA_DIR)"
	@echo "Git ref:        $(GIT_REF)"
	@echo ""
	@echo "$(BLUE)=== Podman ===$(NC)"
	@podman info --format "Rootless: {{.Host.Security.Rootless}}"
	@echo "Podman:  $(shell podman --version)"
	@echo "Compose: $(shell podman-compose --version 2>/dev/null | head -n1)"

.PHONY: version
version:
	@podman --version
	@podman-compose --version

.PHONY: env-vars
env-vars:
	@echo "$(BLUE)Current environment variables:$(NC)"
	@env | grep -E "^(USER_UID|USER_GID|HOST_PORT|DATA_DIR|CONTAINER_DATA_DIR|IMAGE_NAME|GIT_REF|PWD)" || echo "None set"
