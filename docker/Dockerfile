# ==============================================================================
# Multi-stage Dockerfile for Shape Shifter
# Builds frontend (Vue 3) and serves via FastAPI backend
#
# Build Modes:
#   1. From local context (default - recommended for development):
#      docker build -f docker/Dockerfile -t shapeshifter .
#
#   2. From GitHub repository (recommended for CI/CD):
#      docker build -f docker/Dockerfile \
#                   --build-arg SOURCE=github \
#                   --build-arg GIT_REF=main \
#                   -t shapeshifter .
#
#   3. From GitHub with cache invalidation (when branch has new commits):
#      docker build -f docker/Dockerfile \
#                   --build-arg SOURCE=github \
#                   --build-arg GIT_REF=main \
#                   --build-arg CACHE_BUST=$(git ls-remote https://github.com/humlab-sead/sead_shape_shifter.git refs/heads/main | cut -f1) \
#                   -t shapeshifter .
#
# NOTE: Auto-detection removed to follow Docker best practices.
#       Explicit SOURCE mode prevents cache invalidation issues.
# ==============================================================================

# Global build arguments (available to all stages)
ARG PYTHON_VERSION=3.13
ARG NODE_VERSION=20
ARG ALPINE_VERSION=3.19
ARG USER_UID=1002
ARG USER_GID=33

# ------------------------------------------------------------------------------
# Stage 0: Resolve Codebase Source
# ------------------------------------------------------------------------------
ARG ALPINE_VERSION
FROM alpine:${ALPINE_VERSION} AS source-resolver

ARG SOURCE=workdir
ARG GIT_REPO=https://github.com/humlab-sead/sead_shape_shifter.git
ARG GIT_REF=main
# Cache bust arg - set to commit SHA or timestamp to invalidate cache when branch updates
# Example: --build-arg CACHE_BUST=$(git rev-parse HEAD)
# Example: --build-arg CACHE_BUST=$(date +%s)
ARG CACHE_BUST=1

WORKDIR /source

# Clone from GitHub or use local context based on SOURCE argument
# Split into separate paths for better cache utilization
RUN if [ "$SOURCE" = "github" ]; then \
        echo "Cloning from GitHub: ${GIT_REPO} (ref: ${GIT_REF})..."; \
        echo "Cache bust value: ${CACHE_BUST}"; \
        apk add --no-cache git && \
        git clone --depth 1 --branch "${GIT_REF}" "${GIT_REPO}" /source && \
        cd /source && \
        echo "Cloned commit: $(git rev-parse HEAD)"; \
    else \
        echo "Preparing for local context copy..."; \
        mkdir -p /source; \
    fi

# Copy local context when SOURCE=workdir
# When SOURCE=github, this will copy whatever is in the build context (should be empty/minimal)
COPY . /source-context/
RUN if [ "$SOURCE" = "workdir" ]; then \
        echo "Using local context"; \
        cp -r /source-context/* /source/ 2>/dev/null || true; \
    else \
        echo "Using GitHub clone (ignoring build context)"; \
    fi && \
    rm -rf /source-context


# ------------------------------------------------------------------------------
# Stage 1: Build Frontend
# ------------------------------------------------------------------------------
ARG NODE_VERSION
FROM node:${NODE_VERSION}-alpine AS frontend-builder

WORKDIR /app/frontend

# Install pnpm
RUN npm install -g pnpm@9

# Copy dependency manifests first so application source edits do not invalidate
# the pnpm install layer.
COPY --from=source-resolver /source/frontend/package.json ./package.json
COPY --from=source-resolver /source/frontend/pnpm-lock.yaml ./pnpm-lock.yaml

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source after dependencies are installed.
COPY --from=source-resolver /source/frontend ./

# Build-time environment variables for Vite
ARG VITE_API_BASE_URL
ARG VITE_ENV=production
ARG VITE_ENABLE_ANALYTICS=false
ARG VITE_ENABLE_DEBUG=false

# Create production .env file for build
RUN echo "VITE_API_BASE_URL=${VITE_API_BASE_URL}" > .env.production && \
    echo "VITE_ENV=${VITE_ENV}" >> .env.production && \
    echo "VITE_ENABLE_ANALYTICS=${VITE_ENABLE_ANALYTICS}" >> .env.production && \
    echo "VITE_ENABLE_DEBUG=${VITE_ENABLE_DEBUG}" >> .env.production

# Build frontend for production (skip TypeScript checking for faster builds)
RUN pnpm run build:skip-check


# ------------------------------------------------------------------------------
# Stage 2: Python Dependencies
# ------------------------------------------------------------------------------
ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim AS python-builder

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Install uv for fast Python package installation
RUN pip install --no-cache-dir uv

# Copy dependency metadata first so normal source edits do not force a full
# Python dependency reinstall.
COPY --from=source-resolver /source/pyproject.toml ./pyproject.toml
COPY --from=source-resolver /source/uv.lock ./uv.lock
COPY --from=source-resolver /source/README.md ./README.md

# Install only locked runtime dependencies into a dedicated virtual environment.
RUN uv sync --frozen --no-dev --extra api --no-install-project


# ------------------------------------------------------------------------------
# Stage 3: Production Runtime
# ------------------------------------------------------------------------------
ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for UCanAccess (MS Access support)
    default-jre-headless \
    # Required for some database drivers
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
# UID/GID can be overridden via build args to match host user
ARG USER_UID
ARG USER_GID

RUN GROUP_NAME=$(getent group ${USER_GID} | cut -d: -f1) && \
    if [ -z "$GROUP_NAME" ]; then \
        groupadd -r shapeshifter --gid=${USER_GID}; \
        GROUP_NAME=shapeshifter; \
    fi && \
    useradd --uid ${USER_UID} -g ${USER_GID} --home-dir=/app --shell=/bin/bash shapeshifter

# Copy the dedicated Python environment from builder
COPY --from=python-builder /opt/venv /opt/venv

# Copy application source from source resolver
COPY --from=source-resolver /source/src ./src/
COPY --from=source-resolver /source/backend ./backend/
COPY --from=source-resolver /source/docs ./docs/
COPY --from=source-resolver /source/scripts ./scripts/
COPY --from=source-resolver /source/ingesters ./ingesters/

# Copy lib directory from build context (not in git, must be provided separately)
COPY lib/ ./lib/

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create only the writable runtime directories with the correct ownership.
RUN mkdir -p /app/projects /app/logs /app/output /app/backups /app/tmp && \
    chown ${USER_UID}:${USER_GID} /app/projects /app/logs /app/output /app/backups /app/tmp && \
    chmod 775 /app/projects /app/logs /app/output /app/backups /app/tmp

# Set environment variables
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PROJECTS_DIR=/app/projects \
    LOG_LEVEL=INFO

# Switch to non-root user
USER shapeshifter

EXPOSE 8012

# Health check using wget (more lightweight than Python)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8012/api/v1/health').read()"

# IMPORTANT: Must use --workers 1 because ApplicationState (in-memory project
# cache) is per-process. Multiple workers each get independent caches, causing
# entity CRUD in one worker to be invisible to others — leading to silent data
# loss when a stale worker handles the next request.
# To use multiple workers, implement shared state (e.g., Redis) first.
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8012", "--workers", "1", "--timeout-keep-alive", "120"]
