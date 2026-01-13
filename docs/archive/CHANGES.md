# Docker Setup Review - Changes Summary

## Overview

Updated the Docker configuration to serve the frontend via the backend in a unified single-service architecture.

## Changes Made

### 1. Updated `docker-compose.yml`

**Before**: Separate `backend` and `frontend` services (2 containers)
**After**: Single `app` service (1 container)

Key changes:
- Single service named `app` instead of separate `backend` and `frontend`
- Build context changed from `./backend` to `.` (project root)
- Dockerfile path: `docker/Dockerfile`
- Removed frontend service entirely (now served by backend)
- Single port exposure: `8012` (instead of 8012 + 80)
- Updated health check to use `/api/v1/health` endpoint
- Added proper volume mounts:
  - `./projects:/app/projects` - Project YAML files
  - `./input:/app/input:ro` - Input data (read-only)
  - `./output:/app/output` - Output files
  - `./backups:/app/backups` - Auto-fix backups
  - `./logs:/app/logs` - Application logs
- Build args for frontend configuration (VITE_API_BASE_URL, etc.)

### 2. Updated `docker/Dockerfile`

Fixes and improvements:
- Fixed Python dependency installation to handle missing `uv.lock`
- Added `README.md` copy (required by pyproject.toml setup)
- Proper handling of lib directory for UCanAccess
- Updated health check to use correct API endpoint: `/api/v1/health`
- Increased health check start period from 5s to 40s
- Maintained multi-stage build:
  1. Frontend builder (Node.js + pnpm)
  2. Python dependencies (uv)
  3. Production runtime (Python 3.13-slim)

### 3. Created `.dockerignore`

Added comprehensive `.dockerignore` file to optimize build:
- Excludes development files (node_modules, .venv, etc.)
- Excludes IDE configurations
- Excludes git and CI/CD files
- Excludes temporary and output directories
- Reduces build context size significantly

### 4. Updated `docker/README.md`

Complete rewrite to reflect new architecture:
- Updated Quick Start section
- Single service deployment instructions
- Simplified configuration (no separate frontend.env needed)
- Updated all commands to use new service name (`app`)
- Added comprehensive troubleshooting section
- Updated port information (single port 8012)
- Added debugging and maintenance sections
- Removed references to separate frontend container

### 5. Created `DOCKER.md`

New quick-start guide at project root:
- Simple 3-step deployment process
- Common commands reference
- Troubleshooting quick tips
- Links to detailed documentation
- Development vs production guidance

## Architecture

### Before (2 Services)
```
┌─────────────┐         ┌─────────────┐
│   Frontend  │         │   Backend   │
│   (nginx)   │────────▶│   (FastAPI) │
│   Port 80   │         │   Port 8012 │
└─────────────┘         └─────────────┘
```

### After (1 Service)
```
┌──────────────────────────┐
│      App Container       │
│  ┌────────────────────┐  │
│  │  FastAPI Backend   │  │
│  │  ┌──────────────┐  │  │
│  │  │   Frontend   │  │  │
│  │  │    (static)  │  │  │
│  │  └──────────────┘  │  │
│  └────────────────────┘  │
│       Port 8012          │
└──────────────────────────┘
```

## Benefits

1. **Simplified Deployment**: Single container instead of two
2. **Reduced Resource Usage**: One service means less memory and CPU overhead
3. **Easier Configuration**: No need to configure nginx or manage CORS between services
4. **Unified Logging**: All logs in one place
5. **Better Development/Production Parity**: Backend already serves frontend in development
6. **Simpler Networking**: No need for container networking between frontend/backend
7. **Faster Startup**: Single health check, no service dependencies

## Testing

To test the new setup:

```bash
# 1. Ensure required directories exist
mkdir -p projects input output backups logs lib

# 2. Build and start
docker-compose up --build

# 3. Access application
open http://localhost:8012

# 4. Check health
curl http://localhost:8012/api/v1/health

# 5. View logs
docker-compose logs -f app
```

## Migration from Old Setup

If you have the old two-service setup running:

```bash
# Stop old containers
docker-compose down

# Remove old images (optional)
docker rmi shapeshifter-backend shapeshifter-frontend

# Start new unified service
docker-compose up -d --build
```

## Backward Compatibility

The backend (`backend/app/main.py`) already had code to serve static frontend files:

```python
# Serve static frontend files (production mode)
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and frontend_dist.is_dir():
    logger.info(f"Serving frontend from: {frontend_dist}")
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
```

So the Docker setup now matches the application's built-in capability.

## Production Deployment

For production:

1. Set environment variables in `docker-compose.yml`:
   ```yaml
   environment:
     - ENVIRONMENT=production
     - LOG_LEVEL=info
     - SHAPE_SHIFTER_ALLOWED_ORIGINS=["https://yourdomain.com"]
   ```

2. Use a reverse proxy (nginx/traefik) for SSL/TLS:
   ```nginx
   location / {
       proxy_pass http://localhost:8012;
       proxy_set_header Host $host;
       # ... other headers
   }
   ```

3. Consider resource limits:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '4'
         memory: 8G
   ```

## References

- Main Docker Compose: `/docker-compose.yml`
- Dockerfile: `/docker/Dockerfile`
- Docker README: `/docker/README.md`
- Quick Start: `/DOCKER.md`
- Backend serving logic: `/backend/app/main.py` (lines 70-87)
