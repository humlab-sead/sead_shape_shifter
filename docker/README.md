# Shape Shifter Docker Deployment

This directory contains Docker configuration for deploying Shape Shifter in production.

## Architecture

The Dockerfile uses a multi-stage build process:

1. **Stage 1 (frontend-builder)**: Builds the Vue 3 frontend using Node.js and pnpm
2. **Stage 2 (python-builder)**: Installs Python dependencies using uv
3. **Stage 3 (production)**: Creates the final minimal runtime image with both frontend and backend

The frontend is built as static files and served directly by the FastAPI backend using StaticFiles.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# 1. Set up configuration in docker/data directory
cd docker/data

# Copy environment templates
cp backend.env.example backend.env
cp frontend.env.example frontend.env
cp .pgpass.example .pgpass

# 2. Edit configuration files with your settings
nano backend.env    # Database credentials, app settings
nano frontend.env   # Frontend build variables
nano .pgpass        # PostgreSQL password (format: host:port:db:user:pass)

# Set .pgpass permissions
chmod 600 .pgpass

# 3. Return to docker directory and build
cd ..
docker compose up -d

# Or from project root
docker compose -f docker/docker-compose.yml up -d

# View logs
docker compose logs -f

# Stop the application
docker compose down
```

Access the application at: http://localhost:8012

### Using Docker Directly

```bash
# Build the image
docker build -f docker/Dockerfile -t shape-shifter:latest .

# Run the container
docker run -d \
  --name shape-shifter \
  -p 8012:8012 \
  -v shape-shifter-projects:/app/projects \
  -v shape-shifter-logs:/app/logs \
  -v shape-shifter-output:/app/output \
  -e ENVIRONMENT=production \
  shape-shifter:latest

# View logs
docker logs -f shape-shifter

# Stop the container
docker stop shape-shifter
docker rm shape-shifter
```

## Build Script

Use the provided build script for convenience:

```bash
# Make the script executable
chmod +x docker/build.sh

# Build the image
./docker/build.sh

# Build with a custom tag
./docker/build.sh my-registry.com/shape-shifter:v1.0.0
```

## Configuration

### Environment Files Location

All runtime configuration is stored in the **`docker/data/`** directory:

```
docker/data/
├── backend.env          # Backend runtime variables
├── frontend.env         # Frontend build-time variables
├── .pgpass             # PostgreSQL passwords (secure)
├── projects/           # Project files (persistent)
├── logs/               # Application logs (persistent)
├── output/             # Generated files (persistent)
├── backups/            # Config backups (persistent)
└── tmp/                # Temporary files (persistent)
```

### Initial Setup

```bash
cd docker/data

# Copy templates
cp backend.env.example backend.env
cp frontend.env.example frontend.env
cp .pgpass.example .pgpass

# Edit files with your configuration
nano backend.env
nano frontend.env
nano .pgpass

# Secure .pgpass
chmod 600 .pgpass
```

### Backend Variables (backend.env)

Runtime configuration loaded when container starts. Changes take effect after restarting container.

#### SEAD Database Connection

```bash
SEAD_HOST=db.example.com
SEAD_DBNAME=sead_production
SEAD_USER=sead_user
SEAD_PORT=5432
```

**Password:** Use `docker/data/.pgpass` file (see setup instructions above).

#### Application Settings
```bash
SHAPE_SHIFTER_PROJECT_NAME="Shape Shifter Configuration Editor"
SHAPE_SHIFTER_ENVIRONMENT=production
SHAPE_SHIFTER_PROJECTS_DIR=/app/projects
SHAPE_SHIFTER_BACKUPS_DIR=/app/backups
```

#### CORS Configuration
```bash
# Development with specific origins
SHAPE_SHIFTER_ALLOWED_ORIGINS='["http://localhost:5173","https://your-tunnel.devtunnels.ms"]'

# Production (recommended - specific domains only)
SHAPE_SHIFTER_ALLOWED_ORIGINS='["https://yourdomain.com","https://www.yourdomain.com"]'

# Development/Testing only (allow all)
SHAPE_SHIFTER_ALLOWED_ORIGINS=*
```

#### Frontend Build Variables (Vite)

These variables are embedded into the frontend bundle during Docker build:

```bash
# Leave empty for production (uses relative paths)
VITE_API_BASE_URL=

# Or specify absolute URL if needed
# VITE_API_BASE_URL=https://api.yourdomain.com

VITE_ENV=production
VITE_ENABLE_ANALYTICS=false
VITE_ENABLE_DEBUG=false
```

**Note:** Frontend variables are **build-time** only. They are compiled into the JavaScript bundle and cannot be changed after the image is built.

### Database Connections

Configure the application using environment variables in `docker-compose.yml` or when running containers:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Application environment | `production` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `PROJECTS_DIR` | Projects directory | `/app/projects` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `*` |
| `ALLOWED_ORIGIN_REGEX` | CORS regex pattern | `.*` |

### Database Connections

The primary SEAD database connection is configured via environment variables (see above). Additional database connections can be added:

```bash
# In .env file
DB_POSTGRES_HOST=postgres.example.com
DB_POSTGRES_PORT=5432
DB_POSTGRES_USER=myuser
DB_POSTGRES_PASSWORD=mypassword
```

### PostgreSQL Password File (.pgpass)

For secure password management, mount your `~/.pgpass` file:

```yaml
# In docker-compose.yml
volumes:
  - ~/.pgpass:/root/.pgpass:ro
```

Format of `.pgpass`:
```
hostname:port:database:username:password
db.example.com:5432:sead_production:sead_user:yourpassword
```

Set permissions: `chmod 600 ~/.pgpass`

### Volumes

The Docker Compose configuration creates persistent volumes for:

- **Projects**: `/app/projects` - YAML configuration files
- **Logs**: `/app/logs` - Application logs
- **Output**: `/app/output` - Generated output files
- **Backups**: `/app/backups` - Configuration backups

To use local directories instead of Docker volumes:

```yaml
volumes:
  - ./projects:/app/projects
  - ./logs:/app/logs
  - ./output:/app/output
  - ./backups:/app/backups
```

## Production Deployment

### Security Considerations

1. **Environment Files**: Protect sensitive configuration files
   ```bash
   chmod 600 docker/data/backend.env
   chmod 600 docker/data/frontend.env
   chmod 600 docker/data/.pgpass
   ```

2. **Never commit runtime files**: The `.gitignore` in `docker/data/` prevents this

3. **CORS Configuration**: Restrict allowed origins in production
   ```bash
   # In docker/data/backend.env
   SHAPE_SHIFTER_ALLOWED_ORIGINS='["https://yourdomain.com"]'
   ```

4. **Use .pgpass for passwords**: Don't put database passwords in environment files

### Performance Tuning

The default configuration uses 4 Uvicorn workers. Adjust based on your CPU cores:

```dockerfile
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8012", "--workers", "8"]
```

Or override in docker-compose:

```yaml
command: uvicorn backend.app.main:app --host 0.0.0.0 --port 8012 --workers 8
```

### Reverse Proxy Setup

When deploying behind a reverse proxy (nginx, traefik, etc.), configure proxy headers:

```nginx
location / {
    proxy_pass http://localhost:8012;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Health Checks

The container includes a health check that verifies the API is responding:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' shape-shifter

# View health check logs
docker inspect --format='{{json .State.Health}}' shape-shifter | jq
```

## Troubleshooting

### View Application Logs

```bash
# Docker Compose
docker compose -f docker/docker-compose.yml logs -f shape-shifter

# Docker
docker logs -f shape-shifter
```

### Access Container Shell

```bash
# Docker Compose
docker compose -f docker/docker-compose.yml exec shape-shifter /bin/bash

# Docker
docker exec -it shape-shifter /bin/bash
```

### Rebuild After Changes

```bash
# Force rebuild without cache
docker compose -f docker/docker-compose.yml build --no-cache

# Or with Docker directly
docker build --no-cache -f docker/Dockerfile -t shape-shifter:latest .
```

### Frontend Not Loading

If the frontend doesn't load:

1. Check that the frontend was built correctly:
   ```bash
   docker exec shape-shifter ls -la /app/frontend/dist
   ```

2. Check backend logs for static file serving errors:
   ```bash
   docker logs shape-shifter | grep -i frontend
   ```

## Image Size Optimization

The multi-stage build keeps the final image small:

- Frontend build artifacts (node_modules) are not included
- Only production Python packages are installed
- Python build tools are excluded from the final image

Check image size:
```bash
docker images shape-shifter:latest
```

## Development Mode

For development with hot-reload, use the local development setup instead:

```bash
# Backend
make backend-run

# Frontend (separate terminal)
make frontend-run
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Image

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: docker build -f docker/Dockerfile -t shape-shifter:${{ github.ref_name }} .
      
      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push shape-shifter:${{ github.ref_name }}
```

## Support

For issues or questions, refer to:
- Main README: `../README.md`
- System Documentation: `../docs/SYSTEM_DOCUMENTATION.md`
- Backend API Documentation: `../docs/BACKEND_API.md`
