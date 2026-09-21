SHELL := /bin/bash
.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Deployment defaults live in CONFIG_DIR/deployment.env so this Makefile,
# podman-compose.yml, and the scripts in scripts/ cannot drift apart. The
# canonical deployment layout keeps config and mutable data next to the
# checkout: ~/config and ~/container-data for the user that owns ~/container.
# Explicit path overrides remain available for tests and controlled alternate
# layouts. Nothing is read from, or written to, the checkout itself.
#
# Precedence for every value, highest first:
#   1. command line   make IMAGE_NAME=shape-shifter:dev up
#   2. environment    IMAGE_NAME=shape-shifter:dev make up
#   3. CONFIG_DIR/deployment.env
#   4. the fallbacks below
# The environment is captured before deployment.env is read, because a plain
# assignment in the included file would otherwise override the environment.
MAKEFILE_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
CHECKOUT_DIR := $(patsubst %/,%,$(MAKEFILE_DIR))
CHECKOUT_PARENT := $(dir $(CHECKOUT_DIR))

# Resolve a possibly relative path into an absolute one. A relative override
# names a path next to the checkout, so DATA_DIR=container-data means the
# sibling of the checkout directory. scripts/load-env.sh applies the same rule,
# and the two must stay in step or `make up` and a direct script call would use
# different directories.
resolve_path = $(if $(filter /%,$(1)),$(1),$(CHECKOUT_PARENT)$(patsubst ./%,%,$(1)))

ENV_CONFIG_DIR := $(CONFIG_DIR)
ENV_DATA_DIR := $(DATA_DIR)
ENV_CONTAINER_DATA_DIR := $(CONTAINER_DATA_DIR)
ENV_CONTAINER_NAME := $(CONTAINER_NAME)
ENV_IMAGE_NAME := $(IMAGE_NAME)
ENV_HOST_PORT := $(HOST_PORT)
ENV_COMPOSE_PROJECT_NAME := $(COMPOSE_PROJECT_NAME)
ENV_GIT_REPO := $(GIT_REPO)
ENV_GIT_REF := $(GIT_REF)

ENV_FILE ?= $(if $(ENV_CONFIG_DIR),$(call resolve_path,$(ENV_CONFIG_DIR))/deployment.env,$(HOME)/config/deployment.env)

-include $(ENV_FILE)

CONFIG_DIR := $(or $(ENV_CONFIG_DIR),$(CONFIG_DIR),$(HOME)/config)
CONTAINER_NAME := $(or $(ENV_CONTAINER_NAME),$(CONTAINER_NAME),shape-shifter)
IMAGE_NAME := $(or $(ENV_IMAGE_NAME),$(IMAGE_NAME),shape-shifter:latest)
HOST_PORT := $(or $(ENV_HOST_PORT),$(HOST_PORT),8012)
DATA_DIR := $(or $(ENV_DATA_DIR),$(DATA_DIR),$(HOME)/container-data)
COMPOSE_PROJECT_NAME := $(or $(ENV_COMPOSE_PROJECT_NAME),$(COMPOSE_PROJECT_NAME),shapeshifter)
GIT_REPO := $(or $(ENV_GIT_REPO),$(GIT_REPO),https://github.com/humlab-sead/sead_shape_shifter.git)
GIT_REF := $(or $(ENV_GIT_REF),$(GIT_REF),main)

# Rootless Podman keeps the deployment user, so build with the current UID/GID.
USER_UID ?= $(shell id -u)
USER_GID ?= $(shell id -g)

# Resolve the deployment paths, then export them. `override` is required because
# a command-line variable cannot otherwise be reassigned from a makefile.
# CONTAINER_DATA_DIR is the name podman-compose.yml mounts: it follows DATA_DIR
# unless the caller set it explicitly.
override CONFIG_DIR := $(call resolve_path,$(CONFIG_DIR))
override DATA_DIR := $(call resolve_path,$(DATA_DIR))
override CONTAINER_DATA_DIR := $(call resolve_path,$(or $(ENV_CONTAINER_DATA_DIR),$(CONTAINER_DATA_DIR),$(DATA_DIR)))

COMPOSE_FILE := podman-compose.yml
SCRIPTS_DIR := ./scripts
RESOURCES_DIR := ./resources
ENV_EXAMPLE := $(MAKEFILE_DIR).env.example

# podman-compose reads runtime configuration from CONFIG_DIR and mutable data
# from CONTAINER_DATA_DIR.
export CONFIG_DIR
export CONTAINER_DATA_DIR
export DATA_DIR
export HOST_PORT
export IMAGE_NAME
export USER_UID
export USER_GID
export GIT_REPO
export GIT_REF
export COMPOSE_PROJECT_NAME
export CONTAINER_NAME

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
	@echo "  make setup               Create config, data directories and environment files"
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
	@echo "  make update-env          Edit the runtime environment file"
	@echo "  make clean               Remove the container (keep data)"
	@echo "  make prune               Remove the container and image"
	@echo "  make system-prune        Full Podman system prune (removes all unused)"
	@echo ""
	@echo "$(GREEN)Systemd integration:$(NC)"
	@echo "  make service-install     Install the systemd user service"
	@echo "  make service-enable      Enable auto-start on boot"
	@echo "  make service-start       Start via systemd"
	@echo "  make service-stop        Stop via systemd"
	@echo "  make service-restart     Restart via systemd"
	@echo "  make service-status      Show systemd status"
	@echo "  make service-disable     Disable auto-start"
	@echo "  make service-logs        Follow systemd logs"
	@echo ""
	@echo "$(GREEN)Configuration$(NC) (make info shows the resolved values):"
	@echo "  Config dir       $(CONFIG_DIR)"
	@echo "  Data dir         $(CONTAINER_DATA_DIR)"
	@echo "  Deployment env   $(CONFIG_DIR)/deployment.env"
	@echo "  Runtime env      $(CONFIG_DIR)/backend.env"
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
	@CONFIG_DIR="$(CONFIG_DIR)" DATA_DIR="$(CONTAINER_DATA_DIR)" $(SCRIPTS_DIR)/setup.sh

.PHONY: setup-directories
setup-directories: check-podman
	@mkdir -p "$(CONFIG_DIR)" "$(CONTAINER_DATA_DIR)"/{projects,shared,logs,output,backups,tmp,state}
	@chmod 700 "$(CONFIG_DIR)"
	@chmod 755 "$(CONTAINER_DATA_DIR)"
	@echo "$(GREEN)+ Created config directory in $(CONFIG_DIR)$(NC)"
	@echo "$(GREEN)+ Created data directories in $(CONTAINER_DATA_DIR)$(NC)"

.PHONY: setup-env
setup-env: check-podman
	@mkdir -p "$(CONFIG_DIR)"; \
	chmod 700 "$(CONFIG_DIR)"; \
	if [ ! -f "$(CONFIG_DIR)/deployment.env" ]; then \
		if [ -f "$(ENV_EXAMPLE)" ]; then \
			cp "$(ENV_EXAMPLE)" "$(CONFIG_DIR)/deployment.env"; \
			echo "$(GREEN)+ Created $(CONFIG_DIR)/deployment.env$(NC)"; \
			echo "$(YELLOW)  Review the image, branch, port and frontend build args$(NC)"; \
		else \
			echo "$(YELLOW)! $(ENV_EXAMPLE) not found, the built-in defaults apply$(NC)"; \
		fi \
	else \
		echo "$(GREEN)+ $(CONFIG_DIR)/deployment.env already exists$(NC)"; \
	fi
	@if [ ! -f "$(CONFIG_DIR)/backend.env" ]; then \
		if [ -f "$(RESOURCES_DIR)/backend.env.example" ]; then \
			cp "$(RESOURCES_DIR)/backend.env.example" "$(CONFIG_DIR)/backend.env"; \
			chmod 600 "$(CONFIG_DIR)/backend.env"; \
			echo "$(GREEN)+ Created $(CONFIG_DIR)/backend.env$(NC)"; \
			echo "$(YELLOW)  Edit this file and restart the container to apply changes$(NC)"; \
		else \
			echo "$(YELLOW)! $(RESOURCES_DIR)/backend.env.example not found$(NC)"; \
		fi \
	else \
		echo "$(GREEN)+ $(CONFIG_DIR)/backend.env already exists$(NC)"; \
	fi
	@mkdir -p "$(CONFIG_DIR)/.pgpass"; \
	chmod 700 "$(CONFIG_DIR)/.pgpass"; \
	if [ ! -f "$(CONFIG_DIR)/.pgpass/.pgpass" ]; then \
		if [ -f "$(RESOURCES_DIR)/.pgpass.example" ]; then \
			cp "$(RESOURCES_DIR)/.pgpass.example" "$(CONFIG_DIR)/.pgpass/.pgpass"; \
		else \
			touch "$(CONFIG_DIR)/.pgpass/.pgpass"; \
		fi; \
		chmod 600 "$(CONFIG_DIR)/.pgpass/.pgpass"; \
		echo "$(GREEN)+ Created $(CONFIG_DIR)/.pgpass/.pgpass$(NC)"; \
		echo "$(YELLOW)  Edit this file with the PostgreSQL credentials$(NC)"; \
	else \
		echo "$(GREEN)+ $(CONFIG_DIR)/.pgpass/.pgpass already exists$(NC)"; \
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
	@CONFIG_DIR="$(CONFIG_DIR)" CONTAINER_DATA_DIR="$(CONTAINER_DATA_DIR)" podman-compose -f $(COMPOSE_FILE) config

# ===========================================================================
# Validation
# ===========================================================================

.PHONY: validate
validate: check-podman
	@echo "$(BLUE)Validating setup...$(NC)"
	@test -f Containerfile && echo "$(GREEN)+ Containerfile present$(NC)" || { echo "$(RED)x Containerfile missing$(NC)"; exit 1; }
	@test -f $(COMPOSE_FILE) && echo "$(GREEN)+ $(COMPOSE_FILE) present$(NC)" || { echo "$(RED)x $(COMPOSE_FILE) missing$(NC)"; exit 1; }
	@CONFIG_DIR="$(CONFIG_DIR)" CONTAINER_DATA_DIR="$(CONTAINER_DATA_DIR)" podman-compose -f $(COMPOSE_FILE) config >/dev/null && echo "$(GREEN)+ Compose configuration is valid$(NC)"
	@test -d "$(CONFIG_DIR)" && echo "$(GREEN)+ Config directory exists$(NC)" || echo "$(YELLOW)! Config directory missing (run make setup)$(NC)"
	@mode=$$(stat -c '%a' "$(CONFIG_DIR)" 2>/dev/null || true); \
	if [ "$$mode" = "700" ]; then \
		echo "$(GREEN)+ Config directory is private (700)$(NC)"; \
	elif [ -n "$$mode" ]; then \
		echo "$(YELLOW)! Config directory mode is $$mode; credentials need 700: chmod 700 $(CONFIG_DIR)$(NC)"; \
	fi
	@test -f "$(CONFIG_DIR)/deployment.env" && echo "$(GREEN)+ Deployment settings exist$(NC)" || echo "$(YELLOW)! $(CONFIG_DIR)/deployment.env missing (the built-in defaults apply)$(NC)"
	@test -d "$(CONTAINER_DATA_DIR)" && echo "$(GREEN)+ Data directory exists$(NC)" || echo "$(YELLOW)! Data directory missing (run make setup)$(NC)"
	@test -f "$(CONFIG_DIR)/backend.env" && echo "$(GREEN)+ Environment file exists$(NC)" || echo "$(YELLOW)! Environment file missing (run make setup)$(NC)"
	@test -d "$(CONFIG_DIR)/.pgpass" -a -f "$(CONFIG_DIR)/.pgpass/.pgpass" && echo "$(GREEN)+ .pgpass file exists$(NC)" || echo "$(YELLOW)! .pgpass file missing (run make setup)$(NC)"
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
	@CONFIG_DIR="$(CONFIG_DIR)" DATA_DIR="$(CONTAINER_DATA_DIR)" $(SCRIPTS_DIR)/backup.sh

.PHONY: update-env
update-env:
	@echo "$(BLUE)Opening environment file...$(NC)"
	@echo "$(YELLOW)After editing, run: make restart$(NC)"
	${EDITOR:-nano} "$(CONFIG_DIR)/backend.env"

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

# Every target delegates to scripts/service.sh, which owns the unit name and the
# systemd command for each action. Edit that script to change either.

.PHONY: service-install
service-install:
	@$(SCRIPTS_DIR)/service.sh install

.PHONY: service-enable
service-enable:
	@$(SCRIPTS_DIR)/service.sh enable

.PHONY: service-disable
service-disable:
	@$(SCRIPTS_DIR)/service.sh disable

.PHONY: service-start
service-start:
	@$(SCRIPTS_DIR)/service.sh start

.PHONY: service-stop
service-stop:
	@$(SCRIPTS_DIR)/service.sh stop

.PHONY: service-restart
service-restart:
	@$(SCRIPTS_DIR)/service.sh restart

.PHONY: service-status
service-status:
	@$(SCRIPTS_DIR)/service.sh status

.PHONY: service-logs
service-logs:
	@$(SCRIPTS_DIR)/service.sh logs

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
	@echo "Config dir:     $(CONFIG_DIR)"
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
	@env | grep -E "^(USER_UID|USER_GID|HOST_PORT|CONFIG_DIR|DATA_DIR|CONTAINER_DATA_DIR|IMAGE_NAME|GIT_REF|PWD)" || echo "None set"
