#!/bin/bash
# Docker build and test script
set -e

echo "======================================"
echo "Shape Shifter Docker Build Test"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo "Step 1: Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found: $(docker --version)${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found: $(docker-compose --version)${NC}"
echo ""

# Step 2: Create required directories
echo "Step 2: Creating required directories..."
mkdir -p projects input output backups logs
chmod 755 projects input output backups logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Step 3: Build the image
echo "Step 3: Building Docker image..."
echo -e "${YELLOW}This may take several minutes on first build...${NC}"
if docker-compose build --progress=plain; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
echo ""

# Step 4: Check image size
echo "Step 4: Checking image size..."
docker images shapeshifter-app --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
echo ""

# Step 5: Start the container
echo "Step 5: Starting container..."
if docker-compose up -d; then
    echo -e "${GREEN}✓ Container started${NC}"
else
    echo -e "${RED}✗ Failed to start container${NC}"
    exit 1
fi
echo ""

# Step 6: Wait for health check
echo "Step 6: Waiting for application to be healthy..."
echo -e "${YELLOW}Waiting up to 60 seconds...${NC}"
for i in {1..60}; do
    sleep 1
    if docker inspect shapeshifter-app --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
        echo -e "${GREEN}✓ Application is healthy${NC}"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${RED}✗ Health check timeout${NC}"
        echo "Container logs:"
        docker-compose logs --tail=50 app
        exit 1
    fi
    echo -n "."
done
echo ""

# Step 7: Test endpoints
echo "Step 7: Testing endpoints..."

# Test health endpoint
if curl -f http://localhost:8012/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Health endpoint responding${NC}"
else
    echo -e "${RED}✗ Health endpoint not responding${NC}"
    docker-compose logs --tail=20 app
    exit 1
fi

# Test frontend
if curl -f http://localhost:8012/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend serving${NC}"
else
    echo -e "${RED}✗ Frontend not serving${NC}"
    docker-compose logs --tail=20 app
    exit 1
fi

# Test API docs
if curl -f http://localhost:8012/api/v1/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API docs accessible${NC}"
else
    echo -e "${YELLOW}⚠ API docs not accessible (may redirect)${NC}"
fi
echo ""

# Step 8: Show running containers
echo "Step 8: Container status..."
docker-compose ps
echo ""

# Step 9: Show logs
echo "Step 9: Recent logs..."
docker-compose logs --tail=20 app
echo ""

# Success
echo "======================================"
echo -e "${GREEN}✓ All tests passed!${NC}"
echo "======================================"
echo ""
echo "Access points:"
echo "  Frontend:  http://localhost:8012/"
echo "  API Docs:  http://localhost:8012/api/v1/docs"
echo "  Health:    http://localhost:8012/api/v1/health"
echo ""
echo "Useful commands:"
echo "  View logs:      docker-compose logs -f app"
echo "  Stop:           docker-compose down"
echo "  Restart:        docker-compose restart app"
echo "  Shell access:   docker-compose exec app bash"
echo ""
