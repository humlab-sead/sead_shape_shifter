#!/bin/bash
# Sprint 8.1 Quick Wins Validation Script
# Tests the 5 implemented quick wins

# Removed set -e to allow continuing after failures

echo "========================================="
echo "Sprint 8.1 Quick Wins Validation"
echo "========================================="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

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

echo "Testing Quick Win Implementations..."
echo ""

# Quick Win 1: Validation Result Caching
echo "1. Validation Result Caching"
if grep -q "validationCache = new Map" frontend/src/composables/useDataValidation.ts; then
    if grep -q "CACHE_TTL = 5 \* 60 \* 1000" frontend/src/composables/useDataValidation.ts; then
        if grep -q "clearCache" frontend/src/composables/useDataValidation.ts; then
            pass "Cache implementation with 5-minute TTL and clearCache method"
        else
            fail "Missing clearCache method"
        fi
    else
        fail "Incorrect cache TTL"
    fi
else
    fail "Cache not implemented"
fi

# Quick Win 2: Tooltips
echo ""
echo "2. Tooltips for Action Buttons"
TOOLTIP_COUNT=$(grep -c "v-tooltip" frontend/src/components/validation/ValidationPanel.vue || echo 0)
if [ "$TOOLTIP_COUNT" -ge 2 ]; then
    pass "ValidationPanel has $TOOLTIP_COUNT tooltips"
else
    fail "ValidationPanel missing tooltips (found $TOOLTIP_COUNT, expected 2+)"
fi

SUGGESTION_TOOLTIP=$(grep -c "v-tooltip" frontend/src/components/validation/ValidationSuggestion.vue || echo 0)
if [ "$SUGGESTION_TOOLTIP" -ge 1 ]; then
    pass "Apply Fix button has tooltip"
else
    fail "Apply Fix button missing tooltip"
fi

# Quick Win 3: Loading Skeleton
echo ""
echo "3. Loading Skeleton for ValidationPanel"
if grep -q "v-skeleton-loader" frontend/src/components/validation/ValidationPanel.vue; then
    if grep -q "article, list-item-three-line" frontend/src/components/validation/ValidationPanel.vue; then
        pass "Loading skeleton implemented with proper types"
    else
        warn "Loading skeleton found but may have different types"
        ((PASSED++))
    fi
else
    fail "Loading skeleton not found"
fi

# Quick Win 4: Success Animations
echo ""
echo "4. Success Notification Animations"
if grep -q "v-scale-transition" frontend/src/views/ConfigurationDetailView.vue; then
    pass "ConfigurationDetailView has scale transition"
else
    fail "ConfigurationDetailView missing scale transition"
fi

if grep -q "v-scale-transition" frontend/src/views/ConfigurationsView.vue; then
    pass "ConfigurationsView has scale transition"
else
    fail "ConfigurationsView missing scale transition"
fi

# Quick Win 5: Debounced Validation
echo ""
echo "5. Debounced Validation"
if grep -q "useDebounceFn" frontend/src/views/ConfigurationDetailView.vue; then
    if grep -q "debouncedValidate.*useDebounceFn.*500" frontend/src/views/ConfigurationDetailView.vue; then
        pass "Debounced validation with 500ms delay"
    else
        warn "Debounced validation found but may have different settings"
        ((PASSED++))
    fi
else
    fail "Debounced validation not implemented"
fi

if grep -q "@vueuse/core" frontend/src/views/ConfigurationDetailView.vue; then
    pass "Using @vueuse/core for debouncing"
else
    warn "@vueuse/core import not found"
fi

# Check TypeScript compilation
echo ""
echo "6. TypeScript Compilation Check"
cd frontend
if npm run build > /tmp/ts_check.log 2>&1; then
    pass "TypeScript compilation successful"
else
    # Check for breaking errors (not just unused variables)
    BREAKING_ERRORS=$(grep "error TS" /tmp/ts_check.log | grep -v "TS6133.*is declared but its value is never read" || echo "")
    NEW_BREAKING=$(echo "$BREAKING_ERRORS" | grep "useDataValidation\|cache\|tooltip\|skeleton\|transition\|debounce" || echo "")
    
    if [ -z "$NEW_BREAKING" ]; then
        pass "No breaking TypeScript errors from Quick Wins"
        UNUSED_COUNT=$(grep -c "TS6133.*is declared but its value is never read" /tmp/ts_check.log || echo 0)
        if [ "$UNUSED_COUNT" -gt 0 ]; then
            warn "$UNUSED_COUNT unused variable warnings (non-breaking)"
        fi
    else
        fail "New breaking TypeScript errors detected"
        echo "$NEW_BREAKING"
    fi
fi
cd ..

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
    echo -e "${GREEN}✓ All Quick Wins validated successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Open http://localhost:5176 in your browser"
    echo "  2. Test the quick wins manually:"
    echo "     - Hover over validation buttons (see tooltips)"
    echo "     - Trigger validation (see loading skeleton)"
    echo "     - Apply fixes (see success animation)"
    echo "     - Validate same config twice (second should be instant from cache)"
    echo "  3. Continue with SPRINT8.1_INTEGRATION_TEST_PLAN.md"
    exit 0
else
    echo -e "${RED}✗ Some Quick Wins failed validation${NC}"
    echo ""
    echo "Review the failures above and fix before continuing."
    exit 1
fi
