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

################################################################################
# Docker Build 
#
# Usage:
#   From repository root: make docker-build
#   From docker/ folder:  make -f Makefile docker-build
#
# Build modes (all use build.sh script):
#   - docker-build          : Build from local context (default, for development)
#   - docker-build-github   : Build from GitHub main (CI/CD, with cache invalidation)
#   - docker-build-tag TAG=v1.0.0 : Build from specific tag/branch (production)
################################################################################

update-deploy-scripts:
	@echo "Update deploy scripts to $(DEPLOY_DIR)..."
	@for file in Makefile Dockerfile build.sh README.md BUILD_SCRIPT_GUIDE.md; do \
		sudo cp -f $(DEPLOY_SOURCE_DIR)/$$file $(DEPLOY_DIR)/$$file; \
		sudo chown sead:www-data $(DEPLOY_DIR)/$$file; \
	done
	@echo "✓ Deployment complete"

.PHONY: docker-build
docker-build: docker-build-github

.PHONY: docker-build-github
docker-build-github:
	@cd $(DOCKER_DIR) && ./build.sh --git-ref main \
		--user-uid $(USER_UID) \
		--user-gid $(USER_GID) \
		--git-repo $(GIT_REPO)

.PHONY: build-and-deploy
build-and-deploy: docker-build-github docker-restart

.PHONY: docker-build-local
docker-build-local:
	@cd $(DOCKER_DIR) && ./build.sh --local \
		--user-uid $(USER_UID) \
		--user-gid $(USER_GID)

# Build from specific GitHub tag/branch (no cache bust needed for tags)
# NOTE: Run from project root directory
.PHONY: docker-build-tag
docker-build-tag:
	@if [ -z "$(TAG)" ]; then \
		echo "❌ Error: TAG variable required. Usage: make docker-build-tag TAG=v1.2.0"; \
		exit 1; \
	fi
	@cd $(DOCKER_DIR) && ./build.sh --git-ref $(TAG) \
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
	@cd $(DOCKER_DIR) && docker compose up -d
	@echo "✓ Application started at http://localhost:$(BACKEND_PORT)"

.PHONY: docker-start
docker-start: docker-up

.PHONY: docker-down
docker-down:
	@echo "Stopping Shape Shifter containers..."
	@cd $(DOCKER_DIR) && docker compose down

.PHONY: docker-stop
docker-stop: docker-down

.PHONY: docker-logs
docker-logs:
	@cd $(DOCKER_DIR) && docker compose logs -f

.PHONY: docker-restart
docker-restart:
	@echo "Restarting Shape Shifter..."
	@cd $(DOCKER_DIR) && docker compose down
	@cd $(DOCKER_DIR) && docker compose up -d
	@echo "✓ Application restarted at http://localhost:$(BACKEND_PORT)"

.PHONY: docker-rebuild
docker-rebuild:
	@echo "Rebuilding and restarting Shape Shifter..."
	@cd $(DOCKER_DIR) && docker compose down
	@cd $(DOCKER_DIR) && docker compose up -d --build
	@echo "✓ Application rebuilt and started at http://localhost:$(BACKEND_PORT)"

.PHONY: docker-shell
docker-shell:
	@cd $(DOCKER_DIR) && docker compose exec shape-shifter /bin/bash

.PHONY: docker-clean
docker-clean:
	@echo "Cleaning up Docker resources..."
	@cd $(DOCKER_DIR) && docker compose down -v
	@docker image rm shape-shifter:latest 2>/dev/null || true
	@echo "✓ Cleanup complete"

.PHONY: docker-ps
docker-ps:
	@cd $(DOCKER_DIR) && docker compose ps

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
