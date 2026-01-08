#!/bin/bash
# Setup script for Docker data directory

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Shape Shifter Docker Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create data directory if it doesn't exist
if [ ! -d "$DATA_DIR" ]; then
    echo -e "${YELLOW}Creating data directory...${NC}"
    mkdir -p "$DATA_DIR"
fi

# Create subdirectories
echo -e "${YELLOW}Creating data subdirectories...${NC}"
mkdir -p "$DATA_DIR"/{projects,logs,output,backups,tmp}

# Copy backend.env if it doesn't exist
if [ ! -f "$DATA_DIR/backend.env" ]; then
    if [ -f "$DATA_DIR/backend.env.example" ]; then
        echo -e "${YELLOW}Creating backend.env from template...${NC}"
        cp "$DATA_DIR/backend.env.example" "$DATA_DIR/backend.env"
        echo -e "${GREEN}✓${NC} Created backend.env"
        echo -e "${YELLOW}  Please edit docker/data/backend.env with your settings${NC}"
    else
        echo -e "${YELLOW}Warning: backend.env.example not found${NC}"
    fi
else
    echo -e "${GREEN}✓${NC} backend.env already exists"
fi

# Copy frontend.env if it doesn't exist
if [ ! -f "$DATA_DIR/frontend.env" ]; then
    if [ -f "$DATA_DIR/frontend.env.example" ]; then
        echo -e "${YELLOW}Creating frontend.env from template...${NC}"
        cp "$DATA_DIR/frontend.env.example" "$DATA_DIR/frontend.env"
        echo -e "${GREEN}✓${NC} Created frontend.env"
    else
        echo -e "${YELLOW}Warning: frontend.env.example not found${NC}"
    fi
else
    echo -e "${GREEN}✓${NC} frontend.env already exists"
fi

# Copy .pgpass if it doesn't exist
if [ ! -f "$DATA_DIR/.pgpass" ]; then
    if [ -f "$DATA_DIR/.pgpass.example" ]; then
        echo -e "${YELLOW}Creating .pgpass from template...${NC}"
        cp "$DATA_DIR/.pgpass.example" "$DATA_DIR/.pgpass"
        chmod 600 "$DATA_DIR/.pgpass"
        echo -e "${GREEN}✓${NC} Created .pgpass with permissions 600"
        echo -e "${YELLOW}  Please edit docker/data/.pgpass with your database password${NC}"
    else
        echo -e "${YELLOW}Warning: .pgpass.example not found${NC}"
    fi
else
    echo -e "${GREEN}✓${NC} .pgpass already exists"
    # Check permissions
    PGPASS_PERMS=$(stat -c "%a" "$DATA_DIR/.pgpass" 2>/dev/null || stat -f "%Lp" "$DATA_DIR/.pgpass" 2>/dev/null)
    if [ "$PGPASS_PERMS" != "600" ]; then
        echo -e "${YELLOW}  Warning: .pgpass has permissions $PGPASS_PERMS (should be 600)${NC}"
        echo -e "${YELLOW}  Run: chmod 600 docker/data/.pgpass${NC}"
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "  1. Edit configuration files:"
echo "     nano docker/data/backend.env"
echo "     nano docker/data/.pgpass"
echo ""
echo "  2. Build and start:"
echo "     docker compose -f docker/docker-compose.yml build"
echo "     docker compose -f docker/docker-compose.yml up -d"
echo ""
echo "  Or use Makefile shortcuts:"
echo "     make docker-build"
echo "     make docker-up"
echo ""
echo -e "${YELLOW}Data directories created in docker/data/:${NC}"
echo "  - projects/  (YAML configuration files)"
echo "  - logs/      (Application logs)"
echo "  - output/    (Generated files)"
echo "  - backups/   (Configuration backups)"
echo "  - tmp/       (Temporary files)"
echo ""
