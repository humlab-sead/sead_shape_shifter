# Shape Shifter Docker Deployment

Single-container deployment for Shape Shifter with FastAPI backend serving both API and Vue 3 frontend.

## Quick Start

```bash
# Create data directories
mkdir -p projects input output backups logs

# Start with Docker Compose
docker-compose up -d --build

# View logs
docker-compose logs -f app
```

**Access:** http://localhost:8012

- Frontend: http://localhost:8012/
- API Docs: http://localhost:8012/api/v1/docs
- Health: http://localhost:8012/api/v1/health

## Architecture

Multi-stage build combining frontend and backend:
1. **Stage 1**: Builds Vue 3 frontend with Vite
2. **Stage 2**: Installs Python dependencies (uv)
3. **Stage 3**: Production runtime - FastAPI serves both API and static frontend on port 8012

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
  - SHAPE_SHIFTER_MAX_ENTITIES_PER_CONFIG=1000
  - SHAPE_SHIFTER_MAX_CONFIG_FILE_SIZE_MB=10
  
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
  - ./input:/app/input:ro          # Input data (read-only)
  - ./output:/app/output           # Generated outputs
  - ./backups:/app/backups         # Auto-fix backups
  - ./logs:/app/logs               # Application logs
```

## Common Commands

```bash
# Stop
docker-compose down

# Rebuild after changes
docker-compose up -d --build

# Force rebuild (no cache)
docker-compose build --no-cache && docker-compose up -d

# Shell access
docker-compose exec app bash

# Clean everything
docker-compose down -v
docker system prune -a
```

## Advanced Usage

### Manual Docker Build

```bash
docker build -f docker/Dockerfile -t shape-shifter:latest .

docker run -d \
  -p 8012:8012 \
  -v $(pwd)/projects:/app/projects \
  -v $(pwd)/input:/app/input:ro \
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
   chmod 755 projects input output backups logs
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

### Permission Issues
Troubleshooting

**View logs:**
```bash
docker-compose logs -f app
docker-compose logs --tail=100 app | grep ERROR
```

**Shell access:**
```bash
docker-compose exec app bash
ls -la /app/frontend/dist          # Check frontend build
curl http://localhost:8012/api/v1/health
```

**Frontend not loading:**
```bash
# Verify build
docker-compose exec app ls /app/frontend/dist

# Check logs
docker-compose logs app | grep "Serving frontend"
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