# ==============================================================================
# Multi-stage Dockerfile for Shape Shifter
# Builds frontend (Vue 3) and serves via FastAPI backend
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Frontend
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install pnpm
RUN npm install -g pnpm@9

# Copy package files
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./

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
FROM python:3.13-slim AS python-builder

WORKDIR /app

# Install uv for fast Python package installation
RUN pip install --no-cache-dir uv

# Copy Python dependency files
COPY pyproject.toml ./
COPY README.md ./

# Create empty uv.lock if it doesn't exist (optional)
RUN touch uv.lock || true

# Install Python dependencies (core + api)
RUN uv pip install --system --no-cache -e ".[api]"


# ------------------------------------------------------------------------------
# Stage 3: Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for UCanAccess (MS Access support)
    default-jre-headless \
    # Required for some database drivers
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=python-builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy application source
COPY src/ ./src/
COPY backend/ ./backend/

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy UCanAccess library for MS Access support
COPY lib/ ./lib/

# Copy scripts
COPY scripts/ ./scripts/

# Create required directories
RUN mkdir -p /app/projects /app/logs /app/output /app/backups /app/tmp

# Create required directories
RUN mkdir -p /app/projects /app/logs /app/output /app/backups /app/tmp

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PROJECTS_DIR=/app/projects \
    LOG_LEVEL=INFO

# Expose port
EXPOSE 8012

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8012/api/v1/health').read()"

# Run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8012", "--workers", "4"]
