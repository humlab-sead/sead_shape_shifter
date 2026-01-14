SHELL := /bin/bash

# Path resolution: "." when run from docker/, "./docker" when included from root
# When running from docker/ directory, set DOCKER_DIR to "."
# When included from root Makefile, DOCKER_DIR is set to "./docker"
DOCKER_DIR ?= .

# Repository and build settings
GIT_REPO ?= https://github.com/humlab-sead/sead_shape_shifter.git
BACKEND_PORT ?= 8012

################################################################################
# Docker Build & Runtime
#
# Usage:
#   From repository root: make docker-build
#   From docker/ folder:  make -f Makefile docker-build
#
# Build modes:
#   - docker-build          : Build from local context (default, for development)
#   - docker-build-github   : Build from GitHub main (CI/CD, with cache invalidation)
#   - docker-build-tag TAG=v1.0.0 : Build from specific tag/branch (production)
#
# Run modes:
#   - docker-up             : Start containers
#   - docker-down           : Stop containers
#   - docker-logs           : View logs
#   - docker-shell          : Open shell in container
#   - docker-health         : Check application health
################################################################################

# Default build - uses local context (SOURCE=workdir by default in Dockerfile)
.PHONY: docker-build
docker-build:
	@echo "Building Docker image from local context..."
	@docker compose -f $(DOCKER_DIR)/docker-compose.yml build

.PHONY: docker-build-no-cache
docker-build-no-cache:
	@echo "Building Docker image (no cache)..."
	@docker compose -f $(DOCKER_DIR)/docker-compose.yml build --no-cache

# Build from GitHub main branch (with cache invalidation)
.PHONY: docker-build-github
docker-build-github:
	@echo "Building Docker image from GitHub (main branch)..."
	@CACHE_BUST=$$(git ls-remote $(GIT_REPO) refs/heads/main | cut -f1) && \
	docker build -f $(DOCKER_DIR)/Dockerfile \
		--build-arg SOURCE=github \
		--build-arg GIT_REPO=$(GIT_REPO) \
		--build-arg GIT_REF=main \
		--build-arg CACHE_BUST=$$CACHE_BUST \
		-t shape-shifter:latest \
		$(DOCKER_DIR)/..
	@echo "✓ Built from GitHub main ($${CACHE_BUST:0:8})"

# Build from specific GitHub tag/branch (no cache bust needed for tags)
.PHONY: docker-build-tag
docker-build-tag:
	@if [ -z "$(TAG)" ]; then \
		echo "❌ Error: TAG variable required. Usage: make docker-build-tag TAG=v1.2.0"; \
		exit 1; \
	fi
	@echo "Building Docker image from GitHub tag/branch: $(TAG)..."
	@docker build -f $(DOCKER_DIR)/Dockerfile \
		--build-arg SOURCE=github \
		--build-arg GIT_REPO=$(GIT_REPO) \
		--build-arg GIT_REF=$(TAG) \
		-t shape-shifter:$(TAG) \
		$(DOCKER_DIR)/..
	@echo "✓ Built from GitHub tag/branch: $(TAG)"

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
