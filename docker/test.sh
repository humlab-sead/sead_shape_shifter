#!/bin/bash
# Test script for Docker deployment

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Shape Shifter Docker Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        exit 1
    fi
}

# Test 1: Check if Docker is installed
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v docker &> /dev/null
print_status $? "Docker is installed"

command -v docker compose &> /dev/null
print_status $? "Docker Compose is installed"

# Test 2: Check if Dockerfile exists
test -f "$SCRIPT_DIR/Dockerfile"
print_status $? "Dockerfile exists"

# Test 3: Check if docker-compose.yml exists
test -f "$SCRIPT_DIR/docker-compose.yml"
print_status $? "docker-compose.yml exists"

# Test 4: Validate Dockerfile syntax
echo ""
echo -e "${YELLOW}Validating Dockerfile...${NC}"
docker build -f "$SCRIPT_DIR/Dockerfile" -t shape-shifter:test --target python-builder "$PROJECT_ROOT" &> /dev/null
print_status $? "Dockerfile syntax is valid"

# Test 5: Check for frontend source
echo ""
echo -e "${YELLOW}Checking project structure...${NC}"
test -d "$PROJECT_ROOT/frontend"
print_status $? "Frontend directory exists"

test -f "$PROJECT_ROOT/frontend/package.json"
print_status $? "Frontend package.json exists"

# Test 6: Check for backend source
test -d "$PROJECT_ROOT/backend"
print_status $? "Backend directory exists"

test -f "$PROJECT_ROOT/backend/app/main.py"
print_status $? "Backend main.py exists"

# Test 7: Check for core source
test -d "$PROJECT_ROOT/src"
print_status $? "Core source directory exists"

# Test 8: Validate docker-compose configuration
echo ""
echo -e "${YELLOW}Validating docker-compose configuration...${NC}"
docker compose -f "$SCRIPT_DIR/docker-compose.yml" config &> /dev/null
print_status $? "docker-compose.yml is valid"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All tests passed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Ready to build and deploy:${NC}"
echo "  1. Build the image:"
echo "     ./docker/build.sh"
echo ""
echo "  2. Start the application:"
echo "     docker compose -f docker/docker-compose.yml up -d"
echo ""
echo "  3. Access the application:"
echo "     http://localhost:8012"
echo ""
