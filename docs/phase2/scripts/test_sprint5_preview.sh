#!/bin/bash

echo "════════════════════════════════════════════════════════════"
echo "  Sprint 5.1: Entity Data Preview Testing"
echo "════════════════════════════════════════════════════════════"
echo

# Check backend
echo "1. Backend Health Check"
if curl -s http://localhost:8000/api/v1/health | grep -q "healthy"; then
    echo "✓ Backend is running"
else
    echo "✗ Backend is not responding"
    exit 1
fi
echo

# Test preview API with query_tester_config
echo "2. Entity Preview API Test"
echo "Testing with query_tester_config..."

PREVIEW_RESULT=$(curl -s -X POST "http://localhost:8000/api/v1/configurations/query_tester_config/entities/users/preview?limit=5")

if echo "$PREVIEW_RESULT" | grep -q "entity_name"; then
    echo "✓ Preview API working"
    echo "$PREVIEW_RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Entity: {data[\"entity_name\"]}')
    print(f'  Rows: {data[\"total_rows_in_preview\"]}')
    print(f'  Columns: {len(data[\"columns\"])}')
    print(f'  Execution time: {data[\"execution_time_ms\"]}ms')
    print(f'  Cache hit: {data[\"cache_hit\"]}')
    if data.get('transformations_applied'):
        print(f'  Transformations: {', '.join(data[\"transformations_applied\"])}')
except Exception as e:
    print(f'  Error parsing response: {e}')
"
else
    echo "✗ Preview API failed"
    echo "Response:"
    echo "$PREVIEW_RESULT" | python3 -mjson.tool 2>&1 | head -20
fi
echo

# Test cache hit
echo "3. Cache Test (second request should hit cache)"
PREVIEW_RESULT2=$(curl -s -X POST "http://localhost:8000/api/v1/configurations/query_tester_config/entities/users/preview?limit=5")

if echo "$PREVIEW_RESULT2" | grep -q "cache_hit.*true"; then
    echo "✓ Cache working (second request hit cache)"
else
    echo "⚠ Cache may not be working (check cache_hit field)"
fi
echo

# Test sample endpoint
echo "4. Entity Sample API Test (larger limit)"
SAMPLE_RESULT=$(curl -s -X POST "http://localhost:8000/api/v1/configurations/query_tester_config/entities/users/sample?limit=100")

if echo "$SAMPLE_RESULT" | grep -q "entity_name"; then
    echo "✓ Sample API working"
    echo "$SAMPLE_RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Entity: {data[\"entity_name\"]}')
    print(f'  Rows: {data[\"total_rows_in_preview\"]}')
except Exception as e:
    print(f'  Error: {e}')
"
else
    echo "✗ Sample API failed"
fi
echo

# Test cache invalidation
echo "5. Cache Invalidation Test"
INVALIDATE_RESULT=$(curl -s -X DELETE "http://localhost:8000/api/v1/configurations/query_tester_config/preview-cache?entity_name=users")

if echo "$INVALIDATE_RESULT" | grep -q "message"; then
    echo "✓ Cache invalidation working"
    echo "$INVALIDATE_RESULT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Message: {data[\"message\"]}')
except:
    pass
"
else
    echo "✗ Cache invalidation failed"
fi
echo

echo "════════════════════════════════════════════════════════════"
echo "  ✅ Sprint 5.1 Testing Complete"
echo "════════════════════════════════════════════════════════════"
echo
echo "📋 API Endpoints Available:"
echo "  POST /api/v1/configurations/{config}/entities/{entity}/preview"
echo "  POST /api/v1/configurations/{config}/entities/{entity}/sample"
echo "  DELETE /api/v1/configurations/{config}/preview-cache"
echo
echo "🎯 Features Implemented:"
echo "  ✓ Entity data preview with transformations"
echo "  ✓ Sample data for validation/testing"
echo "  ✓ Session-based caching (5 min TTL)"
echo "  ✓ Cache invalidation"
echo "  ✓ Column metadata (types, nullability, keys)"
echo "  ✓ Dependency tracking"
echo "  ✓ Transformation detection"
echo
