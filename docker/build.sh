#!/bin/bash
# Build script for Shape Shifter Docker image

set -e

# Default image name and tag
IMAGE_NAME="${1:-shape-shifter:latest}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Shape Shifter Docker Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the project root (parent of docker directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}Project root:${NC} $PROJECT_ROOT"
echo -e "${YELLOW}Image name:${NC} $IMAGE_NAME"
echo ""

# Check for environment files in docker/data/
if [ ! -f "$SCRIPT_DIR/data/backend.env" ]; then
    echo -e "${YELLOW}Warning: docker/data/backend.env not found${NC}"
    echo -e "${YELLOW}Copy docker/data/backend.env.example to docker/data/backend.env and customize it${NC}"
    echo ""
fi

if [ ! -f "$SCRIPT_DIR/data/frontend.env" ]; then
    echo -e "${YELLOW}Warning: docker/data/frontend.env not found${NC}"
    echo -e "${YELLOW}Frontend will use default build settings${NC}"
    echo -e "${YELLOW}To customize: cp docker/data/frontend.env.example docker/data/frontend.env${NC}"
    echo ""
fi

# Change to project root
cd "$PROJECT_ROOT"

# Build the Docker image
echo -e "${BLUE}Building Docker image...${NC}"
docker build \
  -f docker/Dockerfile \
  -t "$IMAGE_NAME" \
  .

echo ""
echo -e "${GREEN}✓ Build completed successfully!${NC}"
echo ""

# Show image info
echo -e "${BLUE}Image details:${NC}"
docker images "$IMAGE_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Configure environment (if not already done):"
echo "     cd docker/data"
echo "     cp backend.env.example backend.env"
echo "     cp frontend.env.example frontend.env"
echo "     nano backend.env frontend.env"
echo ""
echo "  2. Run with Docker Compose:"
echo "     docker compose -f docker/docker-compose.yml up -d"
echo ""
echo "  Or run directly:"
echo "    docker run -d -p 8012:8012 \\"
echo "      --env-file docker/data/backend.env \\"
echo "      -v \$PWD/docker/data/projects:/app/projects \\"
echo "      --name shape-shifter $IMAGE_NAME"
echo ""
echo "  3. Access the application:"
echo "     http://localhost:8012"
echo ""
