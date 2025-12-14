# Cross-Browser Testing Guide - Shape Shifter Editor

## Overview

This guide provides comprehensive instructions for testing the Shape Shifter Configuration Editor across different browsers to ensure consistent user experience and functionality.

## Supported Browsers

| Browser | Minimum Version | Testing Priority | Notes |
|---------|----------------|------------------|-------|
| Chrome  | 120+          | **High**         | Primary development browser |
| Firefox | 115+          | **High**         | Second most used |
| Edge    | 120+          | **Medium**       | Chromium-based, similar to Chrome |
| Safari  | 16+           | **Medium**       | macOS/iOS users |

## Quick Start

### 1. Start Development Servers

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend  
cd frontend
npm run dev
```

Frontend should be available at: **http://localhost:5176**

### 2. Load Test Helper (Optional)

Open browser DevTools Console (F12) and run:

```javascript
// Load test helper
const script = document.createElement('script');
script.src = '/sprint81-test-helper.js';
document.head.appendChild(script);

// After loaded, run quick wins tests
testQuickWins.runAll();
```

## Manual Testing Checklist

### Core Functionality (All Browsers)

- [ ] **Configuration List View**
  - Page loads without errors
  - Configurations display correctly
  - Search/filter works
  - Create new configuration button visible

- [ ] **Configuration Detail View**
  - YAML editor loads and displays content
  - Syntax highlighting works
  - Line numbers display correctly
  - Editor is editable

- [ ] **Validation Panel**
  - Panel displays validation results
  - Structural/Data tabs switch correctly
  - Error counts show correctly
  - Expand/collapse works

### Sprint 8.1 Quick Wins Testing

#### 1. Validation Result Caching

**Test Steps:**
1. Open a configuration
2. Click "Validate All" button
3. Note the request time in Network tab (Dev Tools → Network)
4. Immediately click "Validate All" again
5. Check Network tab - should show no new request (cached)
6. Wait 5+ minutes
7. Click "Validate All" again
8. Should make a new API request (cache expired)

**Expected Results:**
- First validation: API request made
- Second validation (< 5 min): No API request, instant response
- Third validation (> 5 min): New API request made

**Browser-Specific Notes:**
- Chrome: Check "Preserve log" in Network tab
- Firefox: Network tab auto-clears on reload
- Safari: Network tab under "Develop" menu

#### 2. Tooltips

**Test Steps:**
1. Navigate to Configuration Detail view
2. Hover over "Validate All" button
3. Hover over "Structural" tab button
4. Hover over "Data" tab button
5. Hover over "Validate Entity" button (if entity selected)
6. Hover over "Apply Fix" button in validation suggestions

**Expected Results:**
- Tooltip appears within 500ms of hovering
- Tooltip text is readable and descriptive
- Tooltip disappears when mouse moves away
- Tooltips don't overlap with other UI elements

**Browser-Specific Notes:**
- Safari: Tooltips may appear slower
- Firefox: Check tooltip positioning near viewport edges
- All: Test with different zoom levels (Ctrl/Cmd +/-)

#### 3. Loading Skeleton

**Test Steps:**
1. Navigate to Configuration Detail view
2. Click "Validate All" (or artificially slow network in DevTools)
3. Observe validation panel during loading

**Expected Results:**
- Skeleton loader appears immediately on validation start
- Skeleton has realistic content structure (multi-line, article-style)
- Skeleton animates smoothly (pulsing effect)
- Skeleton is replaced instantly when results arrive
- No flash of empty content

**Browser-Specific Notes:**
- Chrome: Throttle to "Slow 3G" to see skeleton longer
- Firefox: Use "Network Throttling" in DevTools
- Safari: Use "Develop → Network Link Conditioner"

#### 4. Success Animations

**Test Steps:**
1. Make a change to configuration YAML
2. Save the configuration
3. Observe the success snackbar animation

**Expected Results:**
- Snackbar scales in smoothly (v-scale-transition)
- Animation duration ~300ms
- No jank or stuttering
- Snackbar auto-dismisses after 3 seconds
- Animation works on repeated saves

**Browser-Specific Notes:**
- All browsers: Check frame rate in Performance tab
- Firefox: May have slightly different easing
- Safari: Animation should be GPU-accelerated

#### 5. Debounced Validation

**Test Steps:**
1. Navigate to Configuration Detail view
2. Type rapidly in the YAML editor
3. Observe validation panel and Network tab

**Expected Results:**
- Validation does NOT trigger on every keystroke
- Validation waits 500ms after last keystroke
- Only one validation request after typing stops
- No "validation storm" in Network tab
- Typing feels responsive, not laggy

**Browser-Specific Notes:**
- Chrome: Check "Timeline" for debounce timing
- Firefox: Monitor console for debounce logs
- All: Test with rapid copy-paste operations

## Browser-Specific Testing

### Chrome (Primary)

**DevTools Shortcuts:**
- Open DevTools: `F12` or `Ctrl+Shift+I` (Windows/Linux) / `Cmd+Option+I` (Mac)
- Network tab: `Ctrl+Shift+E` / `Cmd+Option+E`
- Console: `Ctrl+Shift+J` / `Cmd+Option+J`

**Key Features to Test:**
- Console warnings/errors
- Network request timing
- Vue DevTools extension (if installed)
- Performance profiling

### Firefox

**DevTools Shortcuts:**
- Open DevTools: `F12` or `Ctrl+Shift+I` (Windows/Linux) / `Cmd+Option+I` (Mac)
- Network tab: `Ctrl+Shift+E` / `Cmd+Option+E`
- Console: `Ctrl+Shift+K` / `Cmd+Option+K`

**Key Features to Test:**
- CSS Grid Inspector (for layout issues)
- Accessibility inspector
- Storage inspector (for cache verification)

**Common Issues:**
- CSS variable interpolation differences
- Flexbox rendering quirks
- Different default font rendering

### Edge

**DevTools:** Same as Chrome (Chromium-based)

**Key Features to Test:**
- Windows-specific rendering
- High DPI scaling issues
- Touch input (if applicable)

**Common Issues:**
- Usually similar to Chrome
- May have different default settings
- Check Edge-specific extensions don't interfere

### Safari

**Enable Developer Tools:**
1. Safari → Settings → Advanced
2. Check "Show Develop menu in menu bar"

**DevTools Shortcuts:**
- Open DevTools: `Cmd+Option+I`
- Network tab: `Cmd+Option+N`
- Console: `Cmd+Option+C`

**Key Features to Test:**
- WebKit-specific rendering
- Touch gesture simulation
- Mobile Safari simulation

**Common Issues:**
- CSS Grid gaps may render differently
- Flexbox `gap` property support
- Backdrop filters may have visual differences
- Date/time input rendering
- ScrollBar styling differences

## Performance Testing

### Metrics to Check (All Browsers)

1. **Initial Page Load**
   - Target: < 2 seconds
   - Check: Network → Performance timing

2. **Validation Response**
   - Target: < 5 seconds
   - Check: Network → individual API requests

3. **UI Responsiveness**
   - Target: 60 FPS during animations
   - Check: Performance tab during transitions

4. **Memory Usage**
   - Target: < 100MB after 10 minutes of use
   - Check: Performance Monitor (Chrome) / about:memory (Firefox)

### Performance Testing Steps

```javascript
// In DevTools Console
performance.mark('validation-start');
// Click "Validate All"
// After validation completes:
performance.mark('validation-end');
performance.measure('validation', 'validation-start', 'validation-end');
console.table(performance.getEntriesByType('measure'));
```

## Accessibility Testing

### Keyboard Navigation (All Browsers)

- [ ] Tab through all interactive elements
- [ ] Enter/Space activate buttons
- [ ] Arrow keys navigate lists
- [ ] Escape closes modals/dropdowns
- [ ] Focus indicators are visible

### Screen Reader Testing

**Windows:**
- NVDA (Firefox) - Free
- JAWS (Chrome/Edge) - Commercial

**macOS:**
- VoiceOver (Safari) - Built-in
  - Enable: `Cmd+F5`
  - Navigate: `Ctrl+Option+Arrow`

**Test Checklist:**
- [ ] All buttons have accessible labels
- [ ] Form inputs have labels
- [ ] Validation errors are announced
- [ ] Loading states are announced
- [ ] Success messages are announced

## Automated Cross-Browser Testing

### Using Playwright (Future)

```bash
# Install
npm install -D @playwright/test

# Run tests
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

### Using BrowserStack (Cloud Testing)

For testing on real devices and older browser versions:
- https://www.browserstack.com/
- Supports 2000+ real devices and browsers
- Free for open source projects

## Common Issues & Solutions

### Issue: CORS Errors
**Browsers:** All  
**Solution:** Check backend CORS configuration in `backend/app/main.py`

### Issue: Fonts Not Loading
**Browsers:** Firefox, Safari  
**Solution:** Verify font MIME types in server configuration

### Issue: Animations Stuttering
**Browsers:** All  
**Solution:** Check frame rate, reduce animation complexity, use `will-change` CSS

### Issue: Cache Not Working
**Browsers:** All  
**Solution:** Check browser cache settings, verify cache headers, clear browser cache

### Issue: Tooltips Not Appearing
**Browsers:** Safari  
**Solution:** Check Vuetify version, verify `:disabled="false"` on tooltip wrappers

### Issue: Skeleton Loader Not Showing
**Browsers:** All  
**Solution:** Check loading state reactivity, verify v-if/v-show conditions

## Reporting Issues

When reporting a browser-specific issue, include:

1. **Browser & Version**
   - Get from: `chrome://version`, `about:support`, etc.

2. **Steps to Reproduce**
   - Exact sequence of actions

3. **Expected vs Actual**
   - What should happen vs what actually happens

4. **Screenshots/Video**
   - Use browser's screenshot tool or screen recorder

5. **Console Errors**
   - Copy any errors from DevTools Console

6. **Network Activity**
   - Export HAR file if applicable (DevTools → Network → Export HAR)

## Test Results Template

```markdown
### Cross-Browser Test Results - [Date]

**Tester:** [Name]

| Feature | Chrome | Firefox | Edge | Safari | Notes |
|---------|--------|---------|------|--------|-------|
| Config List | ✅ | ✅ | ✅ | ⚠️ | Safari: Slow loading |
| YAML Editor | ✅ | ✅ | ✅ | ✅ | - |
| Validation Cache | ✅ | ✅ | ✅ | ❌ | Safari: Cache not working |
| Tooltips | ✅ | ✅ | ✅ | ⚠️ | Safari: Delayed appearance |
| Loading Skeleton | ✅ | ✅ | ✅ | ✅ | - |
| Success Animation | ✅ | ✅ | ✅ | ✅ | - |
| Debounced Validation | ✅ | ✅ | ✅ | ✅ | - |

**Legend:**
- ✅ Pass - Works as expected
- ⚠️ Minor Issue - Works but with minor problems
- ❌ Fail - Does not work
- ⏸️ Blocked - Cannot test (e.g., browser not available)
```

## Resources

### Browser Documentation
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)
- [Firefox DevTools](https://firefox-source-docs.mozilla.org/devtools-user/)
- [Safari Web Inspector](https://webkit.org/web-inspector/)
- [Edge DevTools](https://docs.microsoft.com/en-us/microsoft-edge/devtools-guide-chromium/)

### Testing Tools
- [Can I Use](https://caniuse.com/) - Browser support tables
- [BrowserStack](https://www.browserstack.com/) - Cloud testing
- [LambdaTest](https://www.lambdatest.com/) - Cloud testing
- [Playwright](https://playwright.dev/) - Automated testing

### Accessibility
- [WAVE](https://wave.webaim.org/) - Accessibility checker
- [axe DevTools](https://www.deque.com/axe/devtools/) - Browser extension
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

## Next Steps

After completing manual cross-browser testing:

1. Document all issues found
2. Prioritize fixes (Critical → High → Medium → Low)
3. Create tickets for each issue
4. Consider setting up automated cross-browser testing
5. Schedule regular cross-browser testing (e.g., before each release)

