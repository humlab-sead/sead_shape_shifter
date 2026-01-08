# Environment Variables Reference

This document describes all environment variables used by Shape Shifter in Docker deployments.

## File Locations

- **Backend/Runtime Variables**: `/.env` (project root)
- **Frontend Build Variables**: `/.env` (project root, passed as build args)
- **Frontend Development**: `/frontend/.env.development` or `/frontend/.env.development.local`

## Variable Types

### 🔧 Runtime Variables
Loaded when the container starts. Can be changed by restarting the container.

### 🏗️ Build-Time Variables  
Embedded into the frontend JavaScript bundle during `docker build`. Requires rebuilding the image to change.

---

## Backend Variables (Runtime)

### SEAD Database Connection

```bash
# Database host (required)
SEAD_HOST=db.example.com

# Database name (required)
SEAD_DBNAME=sead_production

# Database username (required)
SEAD_USER=sead_user

# Database port (required)
SEAD_PORT=5432
```

**Password Authentication:**  
Use `~/.pgpass` file instead of environment variables for security.

Format: `hostname:port:database:username:password`

Mount in Docker: `-v ~/.pgpass:/root/.pgpass:ro`

---

### Application Settings

```bash
# Application display name
SHAPE_SHIFTER_PROJECT_NAME="Shape Shifter Configuration Editor"

# Application version
SHAPE_SHIFTER_VERSION="1.2.0"

# Environment: development, staging, production
SHAPE_SHIFTER_ENVIRONMENT=production

# API path prefix
SHAPE_SHIFTER_API_V1_PREFIX=/api/v1

# Projects directory path
SHAPE_SHIFTER_PROJECTS_DIR=/app/projects

# Backups directory path
SHAPE_SHIFTER_BACKUPS_DIR=/app/backups

# Maximum entities per configuration
SHAPE_SHIFTER_MAX_ENTITIES_PER_CONFIG=1000

# Maximum config file size in MB
SHAPE_SHIFTER_MAX_CONFIG_FILE_SIZE_MB=10
```

---

### CORS Configuration

```bash
# Allowed origins (JSON array or '*' for all)
# Development example:
SHAPE_SHIFTER_ALLOWED_ORIGINS='["http://localhost:5173","https://tunnel.devtunnels.ms"]'

# Production example (recommended):
SHAPE_SHIFTER_ALLOWED_ORIGINS='["https://yourdomain.com","https://www.yourdomain.com"]'

# Development/Testing only (NOT recommended for production):
SHAPE_SHIFTER_ALLOWED_ORIGINS=*
```

**Important:** In production, always specify exact origins for security.

---

### External Services

```bash
# Reconciliation service URL (optional)
SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL=http://localhost:8000
```

---

## Frontend Variables (Build-Time)

These variables are compiled into the JavaScript bundle during `docker build`.

### API Configuration

```bash
# Backend API base URL
# For production with same-origin, leave empty or use relative path:
VITE_API_BASE_URL=

# For separate backend server:
# VITE_API_BASE_URL=https://api.yourdomain.com

# For development:
# VITE_API_BASE_URL=http://localhost:8012
```

**Default Behavior:**  
- Empty or not set: Uses same origin (relative path `/api/v1`)
- Set to URL: Makes cross-origin requests to that URL

---

### Environment and Features

```bash
# Environment name (informational)
VITE_ENV=production

# Enable analytics (boolean)
VITE_ENABLE_ANALYTICS=false

# Enable debug mode (boolean)
VITE_ENABLE_DEBUG=false
```

---

## Docker Compose Usage

### Option 1: Using .env File (Recommended)

```bash
# 1. Copy template
cp docker/.env.example .env

# 2. Edit .env with your values
nano .env

# 3. Start (automatically loads .env)
docker compose -f docker/docker-compose.yml up -d
```

### Option 2: Environment File Override

```bash
# Use custom env file
docker compose -f docker/docker-compose.yml --env-file .env.production up -d
```

### Option 3: Command Line Override

```bash
# Override specific variables
SHAPE_SHIFTER_ENVIRONMENT=staging \
SEAD_HOST=staging-db.example.com \
docker compose -f docker/docker-compose.yml up -d
```

---

## Development vs Production

### Development Setup

**Backend** (`docker/data/backend.env`):
```bash
SHAPE_SHIFTER_ENVIRONMENT=development
SHAPE_SHIFTER_ALLOWED_ORIGINS='["http://localhost:5173","http://localhost:3000"]'
SEAD_HOST=localhost
SEAD_PORT=5432
```

**Frontend** (`/frontend/.env.development.local`):
```bash
VITE_API_BASE_URL=http://localhost:8012
VITE_ENV=development
VITE_ENABLE_DEBUG=true
```

### Production Setup

**Backend** (`docker/data/backend.env`):
```bash
SHAPE_SHIFTER_ENVIRONMENT=production
SHAPE_SHIFTER_ALLOWED_ORIGINS='["https://yourdomain.com"]'
SEAD_HOST=db.example.com
SEAD_PORT=5432
```

**Frontend** (build-time, `docker/data/frontend.env`):
```bash
VITE_API_BASE_URL=
VITE_ENV=production
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_DEBUG=false
```

---

## Rebuild Requirements

| Variable Type | Change Method | Rebuild Required? |
|--------------|---------------|-------------------|
| Backend runtime | Edit `.env` + restart container | ❌ No |
| Frontend build-time | Edit `.env` + rebuild image | ✅ Yes |

**To rebuild after changing frontend variables:**

```bash
# Rebuild image
docker compose -f docker/docker-compose.yml build

# Restart with new image
docker compose -f docker/docker-compose.yml up -d
```

---

## Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Use `.pgpass` for database passwords** - Don't put passwords in env vars
3. **Restrict CORS origins in production** - Never use `*` in production
4. **Mount `.pgpass` read-only** - Use `:ro` flag in volume mounts
5. **Use Docker secrets for sensitive data** - For orchestration platforms

### Using Docker Secrets (Swarm/Kubernetes)

```yaml
secrets:
  db_password:
    external: true

services:
  shape-shifter:
    secrets:
      - db_password
```

---

## Troubleshooting

### Variables Not Loading

```bash
# Check what values Docker Compose is using
docker compose -f docker/docker-compose.yml config

# Check environment inside running container
docker exec shape-shifter env | grep SHAPE_SHIFTER
docker exec shape-shifter env | grep SEAD
docker exec shape-shifter env | grep VITE
```

### Frontend Build Variables Not Applied

Frontend variables are **build-time only**. After changing them:

```bash
# Must rebuild the image
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d
```

### CORS Errors

Check that `SHAPE_SHIFTER_ALLOWED_ORIGINS` includes your frontend URL:

```bash
# View current CORS setting
docker exec shape-shifter env | grep ALLOWED_ORIGINS

# Test API access
curl -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     http://localhost:8012/api/v1/health
```

---

## Complete Example

**docker/data/backend.env:**
```bash
# SEAD Database
SEAD_HOST=db.example.com
SEAD_DBNAME=sead_production
SEAD_USER=sead_user
SEAD_PORT=5432

# Application
SHAPE_SHIFTER_PROJECT_NAME="Shape Shifter - Production"
SHAPE_SHIFTER_ENVIRONMENT=production
SHAPE_SHIFTER_PROJECTS_DIR=/app/projects
SHAPE_SHIFTER_BACKUPS_DIR=/app/backups

# CORS (production)
SHAPE_SHIFTER_ALLOWED_ORIGINS='["https://shapeshifter.example.com"]'

# Frontend build variables
VITE_API_BASE_URL=
VITE_ENV=production
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_DEBUG=false
```

**Build and run:**
```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
```

**Mount `.pgpass` for authentication:**
```bash
# Ensure .pgpass has correct format and permissions
chmod 600 ~/.pgpass

# Starts with .pgpass mounted
docker compose -f docker/docker-compose.yml up -d
```
