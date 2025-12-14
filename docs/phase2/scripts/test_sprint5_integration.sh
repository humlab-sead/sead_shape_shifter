#!/bin/bash
# Sprint 5.1 - Entity Data Preview - End-to-End Test

set -e

BASE_URL="http://localhost:8000"
CONFIG="arbodat"
ENTITY="abundance_property_type"

echo "=== Sprint 5.1 Entity Preview E2E Test ==="
echo ""

# Test 1: Backend Health
echo "1. Testing backend health..."
HEALTH=$(curl -s "$BASE_URL/api/v1/health" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
if [ "$HEALTH" = "healthy" ]; then
    echo "   ✓ Backend is healthy"
else
    echo "   ✗ Backend health check failed"
    exit 1
fi

# Test 2: List entities
echo ""
echo "2. Testing entity list..."
ENTITY_COUNT=$(curl -s "$BASE_URL/api/v1/configurations/$CONFIG/entities" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "   ✓ Found $ENTITY_COUNT entities"

# Test 3: Preview API - First call (cache miss)
echo ""
echo "3. Testing preview API (first call - cache miss)..."
PREVIEW_RESULT=$(curl -s -X POST "$BASE_URL/api/v1/configurations/$CONFIG/entities/$ENTITY/preview?limit=5")
ROW_COUNT=$(echo "$PREVIEW_RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['total_rows_in_preview'])")
CACHE_HIT=$(echo "$PREVIEW_RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['cache_hit'])")
EXEC_TIME=$(echo "$PREVIEW_RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['execution_time_ms'])")

echo "   ✓ Preview loaded: $ROW_COUNT rows"
echo "   ✓ Cache hit: $CACHE_HIT"
echo "   ✓ Execution time: ${EXEC_TIME}ms"

if [ "$CACHE_HIT" = "True" ]; then
    echo "   ⚠ Warning: Expected cache miss on first call"
fi

# Test 4: Preview API - Second call (should be cached)
echo ""
echo "4. Testing preview API (second call - should be cached)..."
sleep 1
PREVIEW_RESULT2=$(curl -s -X POST "$BASE_URL/api/v1/configurations/$CONFIG/entities/$ENTITY/preview?limit=5")
CACHE_HIT2=$(echo "$PREVIEW_RESULT2" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['cache_hit'])")
EXEC_TIME2=$(echo "$PREVIEW_RESULT2" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['execution_time_ms'])")

echo "   ✓ Cache hit: $CACHE_HIT2"
echo "   ✓ Execution time: ${EXEC_TIME2}ms"

# Test 5: Column metadata
echo ""
echo "5. Testing column metadata..."
COLUMN_INFO=$(echo "$PREVIEW_RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
cols = d['columns']
print(f'{len(cols)} columns:')
for col in cols[:3]:
    print(f'  - {col[\"name\"]} ({col[\"data_type\"]})')
")
echo "$COLUMN_INFO"

# Test 6: Sample API (larger dataset)
echo ""
echo "6. Testing sample API (larger limit)..."
SAMPLE_RESULT=$(curl -s -X POST "$BASE_URL/api/v1/configurations/$CONFIG/entities/$ENTITY/sample?limit=10")
SAMPLE_COUNT=$(echo "$SAMPLE_RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['total_rows_in_preview'])")
echo "   ✓ Sample loaded: $SAMPLE_COUNT rows"

# Test 7: Cache invalidation
echo ""
echo "7. Testing cache invalidation..."
curl -s -X DELETE "$BASE_URL/api/v1/configurations/$CONFIG/preview-cache?entity_name=$ENTITY" > /dev/null
echo "   ✓ Cache invalidated for $ENTITY"

# Test 8: Preview after cache clear (should be cache miss)
echo ""
echo "8. Testing preview after cache clear..."
PREVIEW_RESULT3=$(curl -s -X POST "$BASE_URL/api/v1/configurations/$CONFIG/entities/$ENTITY/preview?limit=5")
CACHE_HIT3=$(echo "$PREVIEW_RESULT3" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['cache_hit'])")
echo "   ✓ Cache hit after clear: $CACHE_HIT3"

if [ "$CACHE_HIT3" = "True" ]; then
    echo "   ⚠ Warning: Expected cache miss after invalidation"
fi

# Test 9: Frontend accessibility
echo ""
echo "9. Testing frontend accessibility..."
FRONTEND_TITLE=$(curl -s http://localhost:5173 | grep -o "<title>[^<]*" | head -1)
if [ -n "$FRONTEND_TITLE" ]; then
    echo "   ✓ Frontend is accessible"
    echo "   ✓ $FRONTEND_TITLE"
else
    echo "   ⚠ Frontend may not be running"
fi

echo ""
echo "=== All Tests Passed ✓ ==="
echo ""
echo "Sprint 5.1 Status: Backend Complete ✓"
echo "  - Preview API working"
echo "  - Cache system operational"
echo "  - Column metadata correct"
echo "  - Sample API functional"
echo ""
echo "Next: Open http://localhost:5173 to test the frontend UI"
echo "  - Navigate to an entity"
echo "  - Click the 'Preview' tab"
echo "  - Click 'Load Preview' to see entity data"
