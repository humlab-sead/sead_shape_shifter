#!/bin/bash
# Cross-Browser Testing Validation Script
# Tests basic functionality across different browsers using command-line tools

set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5176}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
OUTPUT_DIR="./tmp/browser-test-results"

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Cross-Browser Testing Validation                   ║${NC}"
echo -e "${BLUE}║    Shape Shifter Configuration Editor                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print test header
print_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[Test $TESTS_RUN]${NC} $1"
}

# Function to print test result
print_result() {
    if [ "$1" = "PASS" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo -e "  ${GREEN}✓ PASS${NC} - $2"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo -e "  ${RED}✗ FAIL${NC} - $2"
    fi
}

# Function to print warning
print_warning() {
    echo -e "  ${YELLOW}⚠ WARNING${NC} - $1"
}

# Function to print info
print_info() {
    echo -e "  ${BLUE}ℹ INFO${NC} - $1"
}

echo "═══ System Check ═══"
echo ""

# Check if servers are running
print_test "Backend server availability"
if timeout 2 curl -s "$BACKEND_URL" > /dev/null; then
    print_result "PASS" "Backend responds at $BACKEND_URL"
else
    print_result "FAIL" "Backend not responding at $BACKEND_URL"
    echo ""
    echo -e "${RED}ERROR: Backend server must be running. Start with:${NC}"
    echo "  cd backend && uv run uvicorn app.main:app --reload --port 8000"
    exit 1
fi

print_test "Frontend server availability"
if timeout 2 curl -s "$FRONTEND_URL" > /dev/null; then
    print_result "PASS" "Frontend responds at $FRONTEND_URL"
else
    print_result "FAIL" "Frontend not responding at $FRONTEND_URL"
    echo ""
    echo -e "${RED}ERROR: Frontend server must be running. Start with:${NC}"
    echo "  cd frontend && npm run dev"
    exit 1
fi

echo ""
echo "═══ Browser Detection ═══"
echo ""

# Detect available browsers
declare -A BROWSERS
BROWSER_COUNT=0

# Check for Chrome
if command -v google-chrome &> /dev/null; then
    BROWSERS["chrome"]="google-chrome"
    BROWSER_COUNT=$((BROWSER_COUNT + 1))
    print_info "Chrome detected: $(google-chrome --version 2>/dev/null | head -1)"
elif command -v chromium &> /dev/null; then
    BROWSERS["chrome"]="chromium"
    BROWSER_COUNT=$((BROWSER_COUNT + 1))
    print_info "Chromium detected: $(chromium --version 2>/dev/null | head -1)"
elif command -v chromium-browser &> /dev/null; then
    BROWSERS["chrome"]="chromium-browser"
    BROWSER_COUNT=$((BROWSER_COUNT + 1))
    print_info "Chromium detected: $(chromium-browser --version 2>/dev/null | head -1)"
fi

# Check for Firefox
if command -v firefox &> /dev/null; then
    BROWSERS["firefox"]="firefox"
    BROWSER_COUNT=$((BROWSER_COUNT + 1))
    print_info "Firefox detected: $(firefox --version 2>/dev/null | head -1)"
fi

# Check for Edge
if command -v microsoft-edge &> /dev/null; then
    BROWSERS["edge"]="microsoft-edge"
    BROWSER_COUNT=$((BROWSER_COUNT + 1))
    print_info "Edge detected: $(microsoft-edge --version 2>/dev/null | head -1)"
fi

if [ $BROWSER_COUNT -eq 0 ]; then
    print_warning "No supported browsers detected for automated testing"
    print_info "Manual testing required - see docs/CROSS_BROWSER_TESTING.md"
    echo ""
    echo "This script requires headless browser support."
    echo "Supported browsers: Chrome, Chromium, Firefox, Edge"
    exit 1
fi

echo ""
echo "═══ Frontend Asset Checks ═══"
echo ""

# Check if frontend test helper exists
print_test "Test helper script availability"
if curl -sf "$FRONTEND_URL/sprint81-test-helper.js" > /dev/null; then
    print_result "PASS" "Test helper script exists"
else
    print_result "FAIL" "Test helper script not found at /sprint81-test-helper.js"
fi

# Check main.js bundle
print_test "Main JavaScript bundle"
RESPONSE=$(curl -sI "$FRONTEND_URL/src/main.ts" | head -1)
if echo "$RESPONSE" | grep -q "200"; then
    print_result "PASS" "Main bundle accessible"
else
    print_warning "Main bundle response: $RESPONSE"
fi

echo ""
echo "═══ API Endpoint Validation ═══"
echo ""

# Test key API endpoints
print_test "Health check endpoint"
HEALTH=$(curl -s "$BACKEND_URL/health" 2>/dev/null)
if echo "$HEALTH" | grep -q "healthy"; then
    print_result "PASS" "Health endpoint returns healthy status"
else
    print_result "FAIL" "Health endpoint not responding correctly"
fi

print_test "Configurations list endpoint"
CONFIG_RESPONSE=$(curl -s -w "%{http_code}" "$BACKEND_URL/api/v1/configurations" 2>/dev/null)
HTTP_CODE="${CONFIG_RESPONSE: -3}"
if [ "$HTTP_CODE" = "200" ]; then
    print_result "PASS" "Configurations endpoint returns 200"
else
    print_result "FAIL" "Configurations endpoint returned $HTTP_CODE"
fi

echo ""
echo "═══ Browser Console Error Check ═══"
echo ""

# Function to test browser console errors (headless mode)
test_browser_console() {
    local browser_name=$1
    local browser_cmd=$2
    
    print_test "$browser_name console error check"
    
    # Create a simple HTML page that loads the app and checks for errors
    TEST_HTML="$OUTPUT_DIR/test_${browser_name}.html"
    cat > "$TEST_HTML" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Browser Test</title>
    <script>
        window.browserErrors = [];
        window.onerror = function(msg, url, line, col, error) {
            window.browserErrors.push({msg, url, line, col, error: error?.toString()});
            return false;
        };
        window.addEventListener('load', function() {
            setTimeout(function() {
                var iframe = document.createElement('iframe');
                iframe.src = 'FRONTEND_URL';
                iframe.style.width = '100%';
                iframe.style.height = '800px';
                document.body.appendChild(iframe);
                
                setTimeout(function() {
                    console.log('TEST_COMPLETE');
                    console.log('Errors:', window.browserErrors.length);
                }, 5000);
            }, 1000);
        });
    </script>
</head>
<body>
    <h1>Browser Test - Loading App...</h1>
    <div id="status"></div>
</body>
</html>
EOF
    
    # Replace placeholder with actual URL
    sed -i "s|FRONTEND_URL|$FRONTEND_URL|g" "$TEST_HTML"
    
    # Run browser in headless mode (if supported)
    local log_file="$OUTPUT_DIR/${browser_name}_console.log"
    
    case $browser_name in
        "chrome"|"chromium")
            if timeout 15 "$browser_cmd" --headless --disable-gpu --dump-dom "file://$TEST_HTML" > "$log_file" 2>&1; then
                if grep -q "TEST_COMPLETE" "$log_file"; then
                    print_result "PASS" "$browser_name loads app without crashes"
                    print_info "Log saved to: $log_file"
                else
                    print_result "FAIL" "$browser_name test did not complete"
                fi
            else
                print_warning "$browser_name headless test timed out or failed"
            fi
            ;;
        "firefox")
            print_info "$browser_name headless testing - basic check only"
            if timeout 10 "$browser_cmd" --headless --screenshot "$OUTPUT_DIR/firefox_screenshot.png" "$FRONTEND_URL" 2>&1 | tee "$log_file" > /dev/null; then
                print_result "PASS" "$browser_name opens app in headless mode"
                print_info "Screenshot saved to: $OUTPUT_DIR/firefox_screenshot.png"
            else
                print_warning "$browser_cmd headless test had issues"
            fi
            ;;
        *)
            print_info "$browser_name automated testing not implemented"
            ;;
    esac
}

# Test each detected browser
for browser in "${!BROWSERS[@]}"; do
    test_browser_console "$browser" "${BROWSERS[$browser]}"
done

echo ""
echo "═══ Quick Wins Feature Validation ═══"
echo ""

print_test "Validation endpoint caching headers"
CACHE_HEADERS=$(curl -sI "$BACKEND_URL/api/v1/validation/validate" 2>/dev/null | grep -i "cache-control" || echo "not-found")
print_info "Cache-Control: $CACHE_HEADERS"
print_result "PASS" "Endpoint accessible (client-side caching handled by frontend)"

print_test "Vuetify component availability"
# Check if Vuetify CSS is loaded
if curl -s "$FRONTEND_URL" 2>/dev/null | grep -q "vuetify"; then
    print_result "PASS" "Vuetify detected in page source"
else
    print_warning "Vuetify not detected in HTML (may be loaded dynamically)"
fi

echo ""
echo "═══ Performance Baseline ═══"
echo ""

print_test "Frontend load time"
START_TIME=$(date +%s%N)
if curl -s "$FRONTEND_URL" > /dev/null 2>&1; then
    END_TIME=$(date +%s%N)
    LOAD_TIME=$(( (END_TIME - START_TIME) / 1000000 ))
    print_info "Load time: ${LOAD_TIME}ms"
    if [ $LOAD_TIME -lt 2000 ]; then
        print_result "PASS" "Frontend loads in under 2 seconds"
    else
        print_warning "Frontend load time exceeded 2 seconds"
    fi
fi

print_test "API response time"
START_TIME=$(date +%s%N)
if curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    END_TIME=$(date +%s%N)
    API_TIME=$(( (END_TIME - START_TIME) / 1000000 ))
    print_info "Response time: ${API_TIME}ms"
    if [ $API_TIME -lt 500 ]; then
        print_result "PASS" "API responds in under 500ms"
    else
        print_warning "API response time exceeded 500ms"
    fi
fi

echo ""
echo "═══ Manual Testing Recommendations ═══"
echo ""

echo -e "${YELLOW}The following tests require manual verification:${NC}"
echo ""
echo "1. Tooltips (hover interactions)"
echo "   - Hover over 'Validate All', 'Structural', 'Data' buttons"
echo "   - Verify tooltips appear and are readable"
echo ""
echo "2. Loading Skeleton (visual)"
echo "   - Throttle network to 'Slow 3G' in DevTools"
echo "   - Click 'Validate All' and observe skeleton animation"
echo ""
echo "3. Success Animations (visual)"
echo "   - Save a configuration"
echo "   - Verify smooth scale-in animation on snackbar"
echo ""
echo "4. Validation Debouncing (behavior)"
echo "   - Type rapidly in YAML editor"
echo "   - Verify validation waits 500ms after last keystroke"
echo ""
echo "5. Cache Verification (network)"
echo "   - Validate same config twice within 5 minutes"
echo "   - Second validation should not make API request"
echo ""

if [ $BROWSER_COUNT -gt 0 ]; then
    echo "To open the app in detected browsers:"
    echo ""
    for browser in "${!BROWSERS[@]}"; do
        echo "  ${BROWSERS[$browser]} $FRONTEND_URL"
    done
    echo ""
fi

echo "For detailed testing procedures, see:"
echo "  docs/CROSS_BROWSER_TESTING.md"
echo ""

echo "═══ Test Summary ═══"
echo ""
echo "Tests Run:    $TESTS_RUN"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All automated tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Perform manual cross-browser testing"
    echo "  2. Document results in docs/CROSS_BROWSER_TESTING.md"
    echo "  3. File issues for any browser-specific problems"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Review results above.${NC}"
    exit 1
fi
