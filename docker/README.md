# Shape Shifter Docker Deployment

Single-container deployment for Shape Shifter with FastAPI backend serving both API and Vue 3 frontend.

## Quick Start

### Prerequisites

**Important:** The container runs as a non-root user (shapeshifter) matching your host user's UID/GID.

**For most users (UID/GID auto-detected):**
```bash
# Makefile automatically detects $(id -u) and $(id -g)
make setup-volumes    # One-time setup
make docker-build
make docker-up
```

**Manual setup (if needed):**
```bash
mkdir -p data/{projects,logs,output,backups,tmp}
sudo chown -R $(id -u):$(id -g) data/{projects,logs,output,backups,tmp}
chmod -R 755 data/{projects,logs,output,backups,tmp}
```

**For specific user (e.g., UID 1002, GID 33):**
```bash
# Option 1: Export environment variables
export USER_UID=1002
export USER_GID=33
make setup-volumes && make docker-build && make docker-up

# Option 2: Inline per command
USER_UID=1002 USER_GID=33 make setup-volumes
USER_UID=1002 USER_GID=33 make docker-build
USER_UID=1002 USER_GID=33 make docker-up
```

### Using Make (Recommended)

```bash
# Complete first-time setup (volumes + env files)
make setup

# Or step by step:
make setup-volumes    # Create directories with proper permissions
make setup-env        # Copy .env files from examples
make docker-build     # Build the image
make docker-up        # Start the application

# From docker/ directory:
cd docker/
make setup
make docker-build
make docker-up

# View logs
make docker-logs
```

**All Available Make Targets:**
```bash
# Setup
make setup              # Complete setup (volumes + env files)
make setup-volumes      # Create data directories
make setup-env          # Copy environment file templates

# Build
make docker-build              # Build from local context
make docker-build-no-cache     # Build without cache
make docker-build-github       # Build from GitHub main
make docker-build-tag TAG=v1.0 # Build from specific tag

# Run
make docker-up          # Start containers
make docker-down        # Stop containers
make docker-restart     # Restart containers
make docker-rebuild     # Rebuild and restart

# Inspect
make docker-logs        # View logs (follow mode)
make docker-shell       # Open bash in container
make docker-health      # Check health endpoint
make docker-ps          # List containers

# Test & Validate
make docker-validate    # Validate configuration
make docker-test        # Full integration test

# Clean
make docker-clean       # Stop and remove everything
```

### Using Docker Compose Directly

```bash
# Setup directories first
make setup-volumes

# Start with Docker Compose
docker compose up -d --build

# View logs
docker compose logs -f
```

**Access:** http://localhost:8012

- Frontend: http://localhost:8012/
- API Docs: http://localhost:8012/api/v1/docs
- Health: http://localhost:8012/api/v1/health

## Architecture

Multi-stage build combining frontend and backend:
1. **Stage 0**: Resolves codebase source (local context or GitHub clone)
2. **Stage 1**: Builds Vue 3 frontend with Vite
3. **Stage 2**: Installs Python dependencies (uv)
4. **Stage 3**: Production runtime - FastAPI serves both API and static frontend on port 8012

## Configuration

### Environment Variables

Two types of variables:
- **🔧 Runtime** - Can change by restarting container
- **🏗️ Build-time** - Requires image rebuild to change

#### Backend/Runtime Variables

Edit `docker-compose.yml` or create `.env` file:

```yaml
environment:
  # Application
  - SHAPE_SHIFTER_ENVIRONMENT=production
  - SHAPE_SHIFTER_PROJECT_NAME=Shape Shifter
  - SHAPE_SHIFTER_VERSION=1.2.0
  - SHAPE_SHIFTER_API_V1_PREFIX=/api/v1
  - SHAPE_SHIFTER_PROJECTS_DIR=/app/projects
  - SHAPE_SHIFTER_BACKUPS_DIR=/app/backups
  
  # CORS (production - restrict origins)
  - SHAPE_SHIFTER_ALLOWED_ORIGINS=["https://yourdomain.com"]
  
  # SEAD Database
  - SEAD_HOST=db.example.com
  - SEAD_DBNAME=sead_production
  - SEAD_USER=sead_user
  - SEAD_PORT=5432
  
  # External Services (optional)
  - SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL=http://localhost:8000
```

**Password Authentication:** Use `~/.pgpass` instead of environment variables:
```bash
# Format: hostname:port:database:username:password
echo "db.example.com:5432:sead_production:sead_user:password" > ~/.pgpass
chmod 600 ~/.pgpass
```

#### Frontend Build Variables

Set in `docker-compose.yml` under `build.args`:

```yaml
args:
  VITE_API_BASE_URL: ""              # Empty = same-origin (recommended)
  VITE_ENV: production
  VITE_ENABLE_ANALYTICS: "false"
  VITE_ENABLE_DEBUG: "false"
```

**Important:** Frontend variables are baked into JavaScript bundle - requires rebuild to change.

### Using .env Files

```bash
# 1. Create .env from template
cp docker/.env.example .env

# 2. Edit values
nano .env

# 3. Start (auto-loads .env)
docker-compose up -d

# Or use custom env file
docker-compose --env-file .env.production up -d
```

## Data Volumes

Persistent data mounts (auto-created):

```yaml
volumes:
  - ./projects:/app/projects       # YAML configurations
  - ./output:/app/output           # Generated outputs
  - ./backups:/app/backups         # Auto-fix backups
  - ./logs:/app/logs               # Application logs
```

## Common Commands

### Using Make (Preferred)

```bash
# Build
make docker-build                   # Build from local context
make docker-build-github            # Build from GitHub main (with cache bust)
make docker-build-tag TAG=v1.2.0    # Build from specific tag/branch
make docker-build-no-cache          # Build without cache

# Run
make docker-up                      # Start containers
make docker-down                    # Stop containers
make docker-restart                 # Restart containers
make docker-rebuild                 # Rebuild and restart

# Inspect
make docker-logs                    # View logs (follow mode)
make docker-ps                      # List running containers
make docker-health                  # Check application health
make docker-shell                   # Open bash shell in container

# Clean
make docker-clean                   # Stop containers and remove volumes
```

### Using Docker Compose Directly

```bash
# Stop
docker compose down

# Rebuild after changes
docker compose up -d --build

# Force rebuild (no cache)
docker compose build --no-cache && docker compose up -d

# Shell access
docker compose exec shape-shifter bash

# Clean everything
docker compose down -v
docker system prune -a
```

## Advanced Usage

### Build Source Modes

The Dockerfile supports two explicit build modes for optimal cache behavior:

#### 1. Local Context (Default - Development)
Uses source code from your local repository:

```bash
# From repository root
cd /path/to/sead_shape_shifter
docker build -f docker/Dockerfile -t shapeshifter:dev .

# Explicit local source
docker build -f docker/Dockerfile \
  --build-arg SOURCE=workdir \
  -t shapeshifter:dev .
```

#### 2. GitHub Clone (CI/CD / Production)
Clones source from GitHub repository:

```bash
# Build from main branch (uses cache if main hasn't changed)
docker build -f docker/Dockerfile \
  --build-arg SOURCE=github \
  --build-arg GIT_REF=main \
  -t shapeshifter:main .

# Build from main branch with cache invalidation (always pulls latest)
docker build -f docker/Dockerfile \
  --build-arg SOURCE=github \
  --build-arg GIT_REF=main \
  --build-arg CACHE_BUST=$(git ls-remote https://github.com/humlab-sead/sead_shape_shifter.git refs/heads/main | cut -f1) \
  -t shapeshifter:main .

# Alternative: Use timestamp for cache busting (simpler but always invalidates)
docker build -f docker/Dockerfile \
  --build-arg SOURCE=github \
  --build-arg GIT_REF=main \
  --build-arg CACHE_BUST=$(date +%s) \
  -t shapeshifter:main .

# Build from specific tag (recommended for production - uses cache efficiently)
docker build -f docker/Dockerfile \
  --build-arg SOURCE=github \
  --build-arg GIT_REF=v1.2.0 \
  -t shapeshifter:1.2.0 .

# Build from custom repository/branch
docker build -f docker/Dockerfile \
  --build-arg SOURCE=github \
  --build-arg GIT_REPO=https://github.com/yourorg/fork.git \
  --build-arg GIT_REF=feature-branch \
  -t shapeshifter:custom .
```

**Cache Invalidation Explained:**
- When using branch names (`main`, `develop`), Docker caches the git clone
- Use `CACHE_BUST` with remote commit SHA to invalidate cache when branch updates
- For specific tags (`v1.2.0`), cache invalidation isn't needed - tags don't change
- In CI/CD, always use `CACHE_BUST=$(git ls-remote ...)` to get latest commits

**Note:** When using `SOURCE=github`, local context is ignored. This prevents cache invalidation from local file changes and ensures reproducible builds.

#### Version Selection
```bash
# Use different Python/Node versions
docker build -f docker/Dockerfile \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg NODE_VERSION=18 \
  -t shapeshifter:py312 .
```

### Manual Docker Build (Basic)

```bash
docker build -f docker/Dockerfile -t shape-shifter:latest .

docker run -d \
  -p 8012:8012 \
  -v $(pwd)/projects:/app/projects \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/backups:/app/backups \
  -v $(pwd)/logs:/app/logs \
  -e ENVIRONMENT=production \
  -e LOG_LEVEL=info \
  --name shape-shifter \
  shape-shifter:latest
```

### Performance Tuning

**Uvicorn Workers** - Adjust based on CPU cores:

```yaml
# In docker-compose.yml
command: uvicorn backend.app.main:app --host 0.0.0.0 --port 8012 --workers 8
```

Recommended: `workers = (2 × CPU cores) + 1`

**Resource Limits:**

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
```

### Reverse Proxy (Nginx)

```nginx
location / {
    proxy_pass http://localhost:8012;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Data Directory Setup

Create `docker/data/` structure for advanced configuration:

```
docker/data/
├── backend.env          # Runtime environment variables
├── frontend.env         # Build-time environment variables
├── .pgpass             # PostgreSQL passwords (chmod 600)
├── projects/           # Project YAML files
├── logs/               # Application logs
├── output/             # Generated files
└── backups/            # Configuration backups
```

**backend.env** (runtime - can change and restart):
```bash
SEAD_HOST=db.example.com
SEAD_DBNAME=sead_production
SEAD_USER=sead_user
SEAD_PORT=5432
SHAPE_SHIFTER_ALLOWED_ORIGINS='["https://yourdomain.com"]'
```

**frontend.env** (build-time - requires rebuild):
```bash
VITE_API_BASE_URL=
VITE_ENV=production
VITE_ENABLE_DEBUG=false
```

**.pgpass** (PostgreSQL authentication):
```
db.example.com:5432:sead_production:sead_user:password
```

**Important:** `chmod 600 docker/data/.pgpass`

## Production Security

1. **Restrict CORS:**
   ```yaml
   - SHAPE_SHIFTER_ALLOWED_ORIGINS=["https://yourdomain.com"]
   ```

2. **File permissions:**
   ```bash
   chmod 600 docker/data/.pgpass docker/data/*.env
   chmod 755 projects output backups logs
   ```

3. **Never commit:**
   - `docker/data/*.env`
   - `docker/data/.pgpass`
   - Data directories content## Debugging

### View Application Logs

```bash
# All logs
docker-compose logs -f

# Application logs only
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail=100 app

# Follow specific keywords
docker-compose logs -f app | grep ERROR
```

### Access Container Shell

```bash
# Interactive bash shell
docker-compose exec app bash

# Or with standalone docker
docker exec -it shapeshifter-app bash

# Once inside, useful commands:
ls -la /app/frontend/dist     # Check frontend build
python -c "import sys; print(sys.version)"  # Check Python version
pip list                       # List installed packages
curl http://localhost:8012/api/v1/health   # Test API
```

### Rebuild After Changes

```bash
# Remove containers and rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up

# Or quick rebuild (uses cache)
docker-compose up --build
```

### Frontend Not Loading

If the frontend doesn't load at http://localhost:8012:

1. Check that frontend was built correctly:
   ```bash
   docker-compose exec app ls -la /app/frontend/dist
   ```
   You should see `index.html`, `assets/`, etc.

2. Check backend logs for static file serving:
   ```bash
   docker-compose logs app | grep "Serving frontend"
   ```
   Should show: "Serving frontend from: /app/frontend/dist"

3. Verify files inside container:
   ```bash
   docker-compose exec app cat /app/frontend/dist/index.html
   ```

4. Test API separately:
   ```bash
   curl http://localhost:8012/api/v1/health
   ```

### Port Already in Use

If port 8012 is busy:

```yaml
# In docker-compose.yml
ports:
  - "8080:8012"  # Use different host port
```

## Troubleshooting

### Permission Issues

**Problem:** Container cannot write to mounted volumes (projects, logs, output, backups, tmp)

**Solution:**
```bash
# 1. Check your user ID
id -u  # Should match container's UID (default 1000)
id -g  # Should match container's GID (default 1000)

# 2. If your UID/GID is 1000 (most common), just fix directory permissions:
make setup-volumes

# 3. If your UID/GID is NOT 1000, rebuild with custom UID/GID:
USER_UID=$(id -u) USER_GID=$(id -g) make docker-build
USER_UID=$(id -u) USER_GID=$(id -g) make docker-up

# 4. Manual fix (alternative):
sudo chown -R $(id -u):$(id -g) docker/data/{projects,logs,output,backups,tmp}
chmod -R 755 docker/data/{projects,logs,output,backups,tmp}
```

**Check permissions inside container:**
```bash
docker compose exec shape-shifter id                    # Check user UID/GID
docker compose exec shape-shifter ls -la /app/projects  # Check directory ownership
docker compose exec shape-shifter touch /app/logs/test  # Test write access
```

### General Troubleshooting

**View logs:**
```bash
docker compose logs -f shape-shifter
docker compose logs --tail=100 shape-shifter | grep ERROR
```

**Shell access:**
```bash
docker compose exec shape-shifter bash
ls -la /app/frontend/dist          # Check frontend build
curl http://localhost:8012/api/v1/health
```

**Frontend not loading:**
```bash
# Verify build
docker compose exec shape-shifter ls /app/frontend/dist

# Check logs
docker compose logs shape-shifter | grep "Serving frontend"
```

**Port in use:**
```yaml
ports:
  - "8080:8012"  # Use different host port
```

**CORS errors:**
```bash
# Check CORS setting
docker exec shape-shifter env | grep ALLOWED_ORIGINS

# Test CORS
curl -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS http://localhost:8012/api/v1/health
```

**Variables not loading:**
```bash
# See what Docker Compose will use
docker-compose config

# Check inside container
docker exec shape-shifter env | grep SHAPE_SHIFTER
docker exec shape-shifter env | grep SEAD
```

**Frontend variables not applied:**
```bash
# Frontend vars require rebuild
docker-compose build --no-cache
docker-compose up -d
```

## Maintenance

**Backup:**
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz projects/ output/ backups/
```

**Update:**
```bash
git pull
docker-compose down
docker-compose up -d --build
```

**Cleanup:**
```bash
docker system prune -a          # Remove unused images
docker volume prune             # Remove unused volumes (CAREFUL!)
```

## Development Mode

For development with hot-reload, **use local setup instead of Docker:**

```bash
make install
make backend-run      # Terminal 1
make frontend-run     # Terminal 2
```

- Frontend: http://localhost:5173 (Vite dev server)
- Backend: http://localhost:8012 (auto-reload)

## Documentation

- [README.md](../README.md) - Project overview
- [docs/SYSTEM_DOCUMENTATION.md](../docs/SYSTEM_DOCUMENTATION.md) - Architecture
- [docs/BACKEND_API.md](../docs/BACKEND_API.md) - API reference
- [docs/CONFIGURATION_GUIDE.md](../docs/CONFIGURATION_GUIDE.md) - YAML config