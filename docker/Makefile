SHELL := /bin/bash

# Path resolution: "." when run from docker/, "./docker" when included from root
# When running from docker/ directory, set DOCKER_DIR to "."
# When included from root Makefile, DOCKER_DIR is set to "./docker"
DOCKER_DIR ?= .
DEPLOY_DIR ?= /home/sead/sead-tools/sead_shape_shifter

# Temporary override for Roger's deployment
DEPLOY_SOURCE_DIR ?= /home/roger/source/sead_shape_shifter/docker

# Repository and build settings
GIT_REPO ?= https://github.com/humlab-sead/sead_shape_shifter.git
GIT_REF ?= main
BACKEND_PORT ?= 8012

# User ID settings for container (defaults to sead user)
# Override with: make docker-build USER_UID=1001 USER_GID=1001
USER_UID ?= $(shell id sead -u)
USER_GID ?= $(shell id www-data -g)

PGPASS_DIR := $(DOCKER_DIR)/data/.pgpass

REQUIRED_USER := sead

guard-user:
	@if [ "$$(whoami)" != "$(REQUIRED_USER)" ] && [ "$$(whoami)" != "root" ]; then \
		echo "❌ This target must be run as user '$(REQUIRED_USER)'"; \
		exit 1; \
	fi

guard-cwd:
	@if [ "$(CURDIR)" != "$(DEPLOY_DIR)" ]; then \
		echo "❌ This target must be run from $(DEPLOY_DIR)"; \
		echo "   Current directory: $(CURDIR)"; \
		exit 1; \
	fi

guard-docker-files-exists:
	@if [ ! -f "./docker-compose.yml" ] || [ ! -f "./Dockerfile" ]; then \
		echo "❌ docker-compose.yml not found in $(shell pwd)"; \
		exit 1; \
	fi

.PHONY: deploy-shell
deploy-shell:
	@cd $(DEPLOY_DIR)

################################################################################
# These are the main Docker build targets.
#
# Build modes (all use build.sh script):
#   - docker-build          : Build from local context (default, for development)
#   - docker-build-github   : Build from GitHub main (CI/CD, with cache invalidation)
#   - docker-build-tag TAG=v1.0.0 : Build from specific tag/branch (production)
################################################################################

update-deploy-scripts: guard-user
	@./rsync-to-sead-tools

.PHONY: docker-build
docker-build: guard-user guard-docker-files-exists docker-build-github

.PHONY: docker-build-github
docker-build-github: guard-user guard-docker-files-exists
	@pushd $(DEPLOY_DIR) \
		&& ./build.sh --git-ref main --user-uid $(USER_UID) --user-gid $(USER_GID) --git-repo $(GIT_REPO) \
		&& popd

.PHONY: build-and-deploy
build-and-deploy: docker-build docker-restart

################################################################################
# Build from specific GitHub tag/branch (no cache bust needed for tags)
# NOTE: Run from project root directory
################################################################################

.PHONY: docker-build-tag
docker-build-tag: guard-user guard-cwd guard-docker-files-exists
	@if [ -z "$(TAG)" ]; then \
		echo "❌ Error: TAG variable required. Usage: make docker-build-tag TAG=v1.2.0"; \
		exit 1; \
	fi
	@./build.sh --git-ref $(TAG) \
		--user-uid $(USER_UID) \
		--user-gid $(USER_GID) \
		--git-repo $(GIT_REPO)

################################################################################
# Docker runtime targets
# Run modes:
#   - docker-up             : Start containers
#   - docker-down           : Stop containers
#   - docker-logs           : View logs
#   - docker-shell          : Open shell in container
#   - docker-health         : Check application health
################################################################################

.PHONY: docker-up
docker-up:
	@echo "Starting Shape Shifter with Docker Compose..."
	@pushd $(DOCKER_DIR) && docker compose up -d && popd
	@echo "✓ Application started at http://localhost:$(BACKEND_PORT)"

.PHONY: docker-start
docker-start: docker-up

.PHONY: docker-down
docker-down:
	@echo "Stopping Shape Shifter containers..."
	@pushd $(DOCKER_DIR) && docker compose down && popd

.PHONY: docker-stop
docker-stop: docker-down

.PHONY: docker-logs
docker-logs:
	@pushd $(DOCKER_DIR) && docker compose logs -f && popd

.PHONY: docker-restart
docker-restart:
	@echo "Restarting Shape Shifter..."
	@pushd $(DEPLOY_DIR) \
		&& docker compose down \
		&& docker rm -f shape-shifter 2>/dev/null || true \
		&& docker compose up -d \
		&& popd
	@echo "✓ Application restarted at http://localhost:$(BACKEND_PORT)"

# .PHONY: docker-rebuild
# docker-rebuild: guard-dockerfisudole-exists
# 	@echo "Rebuilding and restarting Shape Shifter..."
# 	@docker compose down && docker compose up -d --build
# 	@echo "✓ Application rebuilt and started at http://localhost:$(BACKEND_PORT)"

.PHONY: docker-shell
docker-shell:
	@pushd $(DOCKER_DIR) \
		&& docker compose exec shape-shifter /bin/bash \
		&& popd

.PHONY: docker-clean
docker-clean:
	@echo "Cleaning up Docker resources..."
	@pushd $(DOCKER_DIR) \
		&& docker compose down -v \
		&& docker image rm shape-shifter:latest 2>/dev/null || true @echo  \
		&& popd  \
		&& echo "✓ Cleanup complete" \

.PHONY: docker-ps
docker-ps:
	@pushd $(DOCKER_DIR) && docker compose ps && popd

.PHONY: docker-health
docker-health:
	@echo "Checking application health..."
	@curl -sf http://localhost:$(BACKEND_PORT)/api/v1/health | jq . || echo "❌ Health check failed"

# Validate Docker configuration before building
.PHONY: docker-validate
docker-validate:
	@echo "Validating Docker configuration..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker not installed"; exit 1; }
	@echo "✓ Docker is installed"
	@command -v docker compose >/dev/null 2>&1 || { echo "❌ Docker Compose not installed"; exit 1; }
	@echo "✓ Docker Compose is installed"
	@test -f $(DOCKER_DIR)/Dockerfile || { echo "❌ Dockerfile not found"; exit 1; }
	@echo "✓ Dockerfile exists"
	@docker compose -f $(DOCKER_DIR)/docker-compose.yml config >/dev/null || { echo "❌ docker-compose.yml is invalid"; exit 1; }
	@echo "✓ docker-compose.yml is valid"
	@echo "✓ All validations passed"

# Full integration test
.PHONY: docker-test
docker-test: docker-validate
	@echo ""
	@echo "Starting integration test..."
	@echo "Building image..."
	@$(MAKE) docker-build
	@echo ""
	@echo "Starting container..."
	@$(MAKE) docker-up
	@echo ""
	@echo "Waiting for health check (max 60s)..."
	@for i in {1..60}; do \
		if curl -sf http://localhost:$(BACKEND_PORT)/api/v1/health >/dev/null 2>&1; then \
			echo "✓ Application is healthy"; \
			break; \
		fi; \
		if [ $$i -eq 60 ]; then \
			echo "❌ Health check timeout"; \
			$(MAKE) docker-logs | tail -50; \
			exit 1; \
		fi; \
		sleep 1; \
		echo -n "."; \
	done
	@echo ""
	@echo "Testing endpoints..."
	@curl -sf http://localhost:$(BACKEND_PORT)/ >/dev/null && echo "✓ Frontend responding" || echo "❌ Frontend failed"
	@curl -sf http://localhost:$(BACKEND_PORT)/api/v1/docs >/dev/null && echo "✓ API docs responding" || echo "⚠ API docs not accessible"
	@echo ""
	@echo "✓ Integration test passed!"
	@echo ""
	@echo "Access points:"
	@echo "  Frontend:  http://localhost:$(BACKEND_PORT)/"
	@echo "  API Docs:  http://localhost:$(BACKEND_PORT)/api/v1/docs"
	@echo "  Health:    http://localhost:$(BACKEND_PORT)/api/v1/health"

################################################################################
# Complete setup: directories + env files
################################################################################

.PHONY: setup
setup: setup-volumes setup-env
	@echo ""
	@echo "✓ Complete setup finished!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit configuration: nano $(DOCKER_DIR)/data/backend.env"
	@echo "  2. Build image: make docker-build"
	@echo "  3. Start application: make docker-up"

# Setup host directories with correct permissions
.PHONY: setup-volumes
setup-volumes:
	@echo "Setting up host directories with UID=$(USER_UID) GID=$(USER_GID)..."
	@mkdir -p $(DOCKER_DIR)/data/{projects,logs,output,backups,tmp}
	@sudo chown -R $(USER_UID):$(USER_GID) $(DOCKER_DIR)/data/{projects,logs,output,backups,tmp}
	@chmod -R 755 $(DOCKER_DIR)/data/{projects,logs,output,backups,tmp}
	@echo "✓ Volume directories created with proper permissions"

# Setup environment files from examples
.PHONY: setup-env
setup-env:
	@echo "Setting up environment files..."
	@if [ ! -f "$(DOCKER_DIR)/data/backend.env" ] && [ -f "$(DOCKER_DIR)/data/backend.env.example" ]; then \
		cp $(DOCKER_DIR)/data/backend.env.example $(DOCKER_DIR)/data/backend.env; \
		echo "✓ Created backend.env from template"; \
	else \
		echo "✓ backend.env already exists"; \
	fi
	@if [ ! -f "$(PGPASS_DIR)/.pgpass" ] && [ -f "$(PGPASS_DIR)/.pgpass.example" ]; then \
		cp $(PGPASS_DIR)/.pgpass.example $(PGPASS_DIR)/.pgpass; \
		chmod 600 $(PGPASS_DIR)/.pgpass; \
		echo "✓ Created .pgpass from template (permissions: 600)"; \
	else \
		echo "✓ .pgpass already exists or template not found"; \
	fi

setup-permissions:
	@chmod g+s $(DEPLOY_DIR) \
		&& setfacl -d -m g::rwX $(DEPLOY_DIR)
	@echo usermod -aG www-data ${USER}
