#!/bin/bash
# Sprint 8.1 Integration Test Runner
# Quick health check for the Shape Shifter system

# Removed set -e to allow continuing after failures

echo "========================================="
echo "Shape Shifter Integration Health Check"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: Backend API is running
echo "Testing backend API..."
if curl -s -f http://localhost:8000/ > /dev/null 2>&1; then
    pass "Backend API is accessible (http://localhost:8000)"
else
    fail "Backend API is not responding"
fi

# Test 2: Backend docs are accessible
echo "Testing API documentation..."
if curl -s -f http://localhost:8000/api/v1/docs > /dev/null 2>&1; then
    pass "API documentation is accessible (/api/v1/docs)"
else
    fail "API documentation is not accessible"
fi

# Test 3: Frontend is running
echo "Testing frontend server..."
if timeout 2 curl -s -f http://localhost:5175 > /dev/null 2>&1; then
    pass "Frontend is accessible (http://localhost:5175)"
else
    warn "Frontend is not responding (expected on port 5175)"
fi

# Test 4: Configuration files exist
echo "Testing configuration files..."
if [ -f "input/arbodat.yml" ]; then
    pass "Test configuration exists (input/arbodat.yml)"
else
    fail "Test configuration not found"
fi

if [ -f "tests/config/config.yml" ]; then
    pass "Unit test configuration exists (tests/config/config.yml)"
else
    warn "Unit test configuration not found"
fi

# Test 5: Test validation endpoint
echo "Testing validation endpoint..."
if curl -s -f "http://localhost:8000/api/v1/configurations/" > /dev/null 2>&1; then
    pass "Configurations endpoint is accessible"
else
    fail "Configurations endpoint failed"
fi

# Test 6: Check backend logs for errors
echo "Checking for recent backend errors..."
if docker-compose logs --tail=50 backend 2>/dev/null | grep -i "error" > /dev/null; then
    warn "Found errors in backend logs (check docker-compose logs backend)"
else
    pass "No recent errors in backend logs"
fi

# Test 7: Check Python environment
echo "Testing Python environment..."
if command -v uv &> /dev/null; then
    pass "UV package manager available"
else
    warn "UV package manager not found"
fi

# Test 8: Check Node environment
echo "Testing Node environment..."
if [ -d "frontend/node_modules" ]; then
    pass "Frontend dependencies installed"
else
    warn "Frontend node_modules not found"
fi

# Test 9: Check backup directory
echo "Testing backup system..."
if [ -d "backups" ]; then
    BACKUP_COUNT=$(ls -1 backups/*.yml 2>/dev/null | wc -l)
    pass "Backup directory exists ($BACKUP_COUNT backups)"
else
    warn "Backup directory not found"
fi

# Test 10: Database connection (if configured)
echo "Testing database connectivity..."
if docker-compose ps | grep -q "postgres.*running"; then
    pass "PostgreSQL database is running"
else
    warn "PostgreSQL not running (may not be needed)"
fi

echo ""
echo "========================================="
echo "Summary"
echo "========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
fi
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ System is ready for integration testing${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Open http://localhost:5175 in your browser"
    echo "  2. Follow SPRINT8.1_QUICKSTART.md"
    echo "  3. Use SPRINT8.1_INTEGRATION_TEST_PLAN.md as checklist"
    exit 0
else
    echo -e "${RED}✗ Some tests failed - please fix before continuing${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Backend: docker-compose up -d backend"
    echo "  - Frontend: cd frontend && npm run dev"
    echo "  - Logs: docker-compose logs -f backend"
    exit 1
fi
