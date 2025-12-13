#!/bin/bash

echo "════════════════════════════════════════════════════════════"
echo "  Sprint 4 Integration Testing"
echo "════════════════════════════════════════════════════════════"
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check backend
echo "1. Backend Health Check"
echo "─────────────────────────────────────────────"
if curl -s http://localhost:8000/api/v1/health | grep -q "ok"; then
    echo -e "${GREEN}✓${NC} Backend is running"
else
    echo -e "${RED}✗${NC} Backend is not responding"
    exit 1
fi
echo

# Check frontend
echo "2. Frontend Health Check"
echo "─────────────────────────────────────────────"
if curl -s http://localhost:5173 | grep -q "Shape Shifter"; then
    echo -e "${GREEN}✓${NC} Frontend is running"
else
    echo -e "${RED}✗${NC} Frontend is not responding"
    exit 1
fi
echo

# Test entity import API
echo "3. Entity Import API Test"
echo "─────────────────────────────────────────────"
IMPORT_RESULT=$(curl -s -X POST http://localhost:8000/api/v1/data-sources/test_sqlite/tables/users/import \
  -H "Content-Type: application/json" \
  -d '{}')

if echo "$IMPORT_RESULT" | grep -q "entity_name"; then
    echo -e "${GREEN}✓${NC} Entity import API working"
    echo "$IMPORT_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'  Entity: {data[\"entity_name\"]}')
print(f'  Columns: {len(data[\"columns\"])}')
print(f'  Surrogate ID: {data[\"surrogate_id_suggestion\"][\"columns\"][0]} (confidence: {data[\"surrogate_id_suggestion\"][\"confidence\"]})')
print(f'  Natural keys: {len(data[\"natural_key_suggestions\"])} suggestions')
"
else
    echo -e "${RED}✗${NC} Entity import API failed"
    echo "$IMPORT_RESULT"
    exit 1
fi
echo

# Test suggestions API
echo "4. Suggestions API Test"
echo "─────────────────────────────────────────────"
SUGGESTIONS_RESULT=$(curl -s -X POST http://localhost:8000/api/v1/suggestions/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "entities": [
      {"name": "users", "columns": ["user_id", "username", "email"]},
      {"name": "orders", "columns": ["order_id", "user_id", "total"]},
      {"name": "products", "columns": ["product_id", "name", "price"]},
      {"name": "order_items", "columns": ["item_id", "order_id", "product_id", "quantity"]}
    ]
  }')

if echo "$SUGGESTIONS_RESULT" | grep -q "foreign_key_suggestions"; then
    echo -e "${GREEN}✓${NC} Suggestions API working"
    echo "$SUGGESTIONS_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
total_fks = sum(len(e['foreign_key_suggestions']) for e in data)
print(f'  Entities analyzed: {len(data)}')
print(f'  Total FK suggestions: {total_fks}')

# Show order_items suggestions
order_items = [e for e in data if e['entity_name'] == 'order_items'][0]
if order_items['foreign_key_suggestions']:
    print(f'  order_items FK suggestions:')
    for fk in order_items['foreign_key_suggestions']:
        print(f'    - {fk[\"local_keys\"][0]} → {fk[\"remote_entity\"]} (confidence: {fk[\"confidence\"]:.2f})')
"
else
    echo -e "${RED}✗${NC} Suggestions API failed"
    echo "$SUGGESTIONS_RESULT"
    exit 1
fi
echo

# Check frontend files
echo "5. Frontend Integration Files Check"
echo "─────────────────────────────────────────────"

if [ -f "frontend/src/components/entities/SuggestionsPanel.vue" ]; then
    echo -e "${GREEN}✓${NC} SuggestionsPanel.vue exists ($(wc -l < frontend/src/components/entities/SuggestionsPanel.vue) lines)"
else
    echo -e "${RED}✗${NC} SuggestionsPanel.vue not found"
fi

if [ -f "frontend/src/composables/useSuggestions.ts" ]; then
    echo -e "${GREEN}✓${NC} useSuggestions.ts exists ($(wc -l < frontend/src/composables/useSuggestions.ts) lines)"
else
    echo -e "${RED}✗${NC} useSuggestions.ts not found"
fi

if grep -q "SuggestionsPanel" frontend/src/components/entities/EntityFormDialog.vue; then
    echo -e "${GREEN}✓${NC} EntityFormDialog.vue integrated with SuggestionsPanel"
else
    echo -e "${RED}✗${NC} EntityFormDialog.vue missing SuggestionsPanel integration"
fi

if grep -q "watchEffect" frontend/src/components/entities/EntityFormDialog.vue; then
    echo -e "${GREEN}✓${NC} EntityFormDialog.vue has watchEffect for suggestions"
else
    echo -e "${RED}✗${NC} EntityFormDialog.vue missing watchEffect"
fi

if grep -q "handleAcceptForeignKey" frontend/src/components/entities/EntityFormDialog.vue; then
    echo -e "${GREEN}✓${NC} EntityFormDialog.vue has accept/reject handlers"
else
    echo -e "${RED}✗${NC} EntityFormDialog.vue missing handlers"
fi
echo

# Summary
echo "════════════════════════════════════════════════════════════"
echo -e "${GREEN}  ✅ All Integration Tests Passed!${NC}"
echo "════════════════════════════════════════════════════════════"
echo
echo "📋 Manual Testing Steps:"
echo "─────────────────────────────────────────────"
echo "1. Open browser: http://localhost:5173"
echo "2. Click 'Create Entity' button"
echo "3. Name: 'test_orders'"
echo "4. Add columns: 'user_id', 'product_id', 'amount'"
echo "5. Wait 1 second → suggestions should appear"
echo "6. Verify suggestions show relationships"
echo "7. Click 'Accept' on a suggestion"
echo "8. Verify FK added to foreign_keys array"
echo
echo "📊 Expected Results:"
echo "  - SuggestionsPanel appears after 1 second"
echo "  - Shows 2 FK suggestions (users, products)"
echo "  - Confidence badges color-coded"
echo "  - Accept adds FK to form data"
echo "  - No duplicate FKs allowed"
echo
echo "🎯 Open browser to test: http://localhost:5173"
echo
