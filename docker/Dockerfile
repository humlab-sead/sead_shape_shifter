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
ARG USER_UID
ARG USER_GID
COPY --chown=${USER_UID}:${USER_GID} . /source-context/
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

# Copy codebase from source resolver
COPY --from=source-resolver /source /app

WORKDIR /app/frontend

# Install pnpm
RUN npm install -g pnpm@9

# Install dependencies
RUN pnpm install --frozen-lockfile

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

# Copy codebase from source resolver
COPY --from=source-resolver /source /app

WORKDIR /app

# Install uv for fast Python package installation
RUN pip install --no-cache-dir uv

# Create empty uv.lock if it doesn't exist (optional)
RUN touch uv.lock || true

# Install Python dependencies (core + api)
RUN uv pip install --system --no-cache -e ".[api]"


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
RUN groupadd -r shapeshifter --gid=${USER_GID} 2>/dev/null || groupmod -n shapeshifter $(getent group ${USER_GID} | cut -d: -f1) && \
    useradd -r -g shapeshifter --uid=${USER_UID} --home-dir=/app --shell=/bin/bash shapeshifter 2>/dev/null || usermod -l shapeshifter -d /app $(getent passwd ${USER_UID} | cut -d: -f1)

# Copy Python packages from builder
ARG PYTHON_VERSION
COPY --from=python-builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy application source from source resolver
COPY --from=source-resolver /source/src ./src/
COPY --from=source-resolver /source/backend ./backend/
COPY --from=source-resolver /source/scripts ./scripts/

# Copy lib directory from build context (not in git, must be provided separately)
COPY lib/ ./lib/

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create required directories and set ownership for ALL files
RUN mkdir -p /app/projects /app/logs /app/output /app/backups /app/tmp && \
    chown -R shapeshifter:shapeshifter /app && \
    chmod -R u+w /app

# Set environment variables
ENV PYTHONPATH=/app \
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

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8012", "--workers", "4"]
