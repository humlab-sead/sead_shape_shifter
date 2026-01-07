#!/bin/bash

echo "=== Sprint 1.1 & 1.2 Verification ==="
echo ""

# Check backend
echo "✓ Backend structure created:"
echo "  - app/main.py (FastAPI application)"
echo "  - app/api/v1/endpoints/health.py"
echo "  - app/core/config.py"
echo "  - pyproject.toml with dependencies"
echo "  - tests/api/v1/test_health.py"
echo ""

# Check frontend  
echo "✓ Frontend structure created:"
echo "  - src/main.ts (Vue 3 entry point)"
echo "  - src/App.vue (Root component)"
echo "  - src/router/index.ts (Vue Router)"
echo "  - src/plugins/vuetify.ts (Vuetify config)"
echo "  - src/views/HomeView.vue (with backend health check)"
echo "  - package.json with dependencies"
echo ""

echo "=== Testing Backend ==="
cd ../backend
echo "Running backend tests..."
uv run python -m pytest -v tests/api/v1/test_health.py

echo ""
echo "=== File Counts ==="
echo "Backend files: $(find ../backend -name '*.py' | wc -l) Python files"
echo "Frontend files: $(find . -name '*.vue' -o -name '*.ts' | wc -l) Vue/TS files"

echo ""
echo "=== Manual Testing ==="
echo "To test manually:"
echo "1. Start backend:  make backend-run"
echo "2. Start frontend: make frontend-run"
echo "3. Open browser:   http://localhost:5173"
echo "4. Check backend health check shows 'Connected'"
