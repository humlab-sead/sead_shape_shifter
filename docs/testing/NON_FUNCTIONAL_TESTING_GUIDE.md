# Non-Functional Testing Guide - Shape Shifter

## Overview

This guide covers non-functional testing requirements for Shape Shifter, including browser compatibility, performance benchmarks, and accessibility compliance. Use this guide in conjunction with the [Testing Guide](../TESTING_GUIDE.md) for comprehensive coverage.

## Table of Contents

- [Cross-Browser Testing](#cross-browser-testing)
- [Performance Testing](#performance-testing)
- [Feature-Specific Behavior](#feature-specific-behavior)
- [Accessibility Testing](#accessibility-testing)
- [Test Results Template](#test-results-template)

---

## Cross-Browser Testing

### Supported Browsers

- **Chrome 120+** (primary)
- **Firefox 115+**
- **Edge 120+**
- **Safari 16+** (macOS only)

### Core Functionality Checklist

Verify in each browser:

**Application Loading:**
- [ ] Loads within 2 seconds
- [ ] No console errors
- [ ] Navigation functional
- [ ] Theme toggle works

**Project Editor:**
- [ ] YAML editor displays correctly
- [ ] Syntax highlighting works
- [ ] Edit and save functional
- [ ] Validation runs
- [ ] Execute dialog opens

**Entity Editor:**
- [ ] Dialog opens/closes
- [ ] All tabs functional
- [ ] Forms submit correctly
- [ ] Preview loads

**Execute Workflow:**
- [ ] Dialog opens correctly
- [ ] Dispatcher selection works
- [ ] Workflow executes
- [ ] Download button functional
- [ ] Success/error messages display

**Visual Elements:**
- [ ] Fonts render correctly
- [ ] Icons display
- [ ] Colors appropriate (light/dark)
- [ ] Spacing consistent

### Browser-Specific Testing

#### Chrome DevTools

1. Open DevTools (F12)
2. Check Console for errors
3. Monitor Network tab during operations
4. Use Performance tab for profiling

**Expected:**
- [ ] No errors/warnings
- [ ] API requests < 500ms
- [ ] UI interactions < 50ms
- [ ] 60 FPS animations

#### Firefox DevTools

1. Open DevTools (F12)
2. Use CSS Grid Inspector
3. Check Accessibility inspector
4. Monitor Storage tab

**Expected:**
- [ ] CSS Grid layout correct
- [ ] Accessibility tree valid
- [ ] LocalStorage/SessionStorage working
- [ ] No CSS variable issues

#### Safari (macOS)

1. Enable Develop menu: Safari → Settings → Advanced
2. Open Web Inspector (Cmd+Option+I)
3. Test touch gestures (trackpad)
4. Check WebKit-specific rendering

**Expected:**
- [ ] Flexbox/Grid rendering correct
- [ ] Backdrop filters work
- [ ] Scrollbar styling acceptable
- [ ] Touch gestures responsive

### Performance Targets (All Browsers)

- **Initial Page Load**: < 2 seconds
- **Validation Response**: < 5 seconds
- **UI Responsiveness**: 60 FPS
- **Memory Usage**: < 100MB (10 minutes)

**Measuring Performance:**

```javascript
// In DevTools Console
performance.mark('validation-start');
// Click "Validate All"
performance.mark('validation-end');
performance.measure('validation', 'validation-start', 'validation-end');
console.table(performance.getEntriesByType('measure'));
```

---

## Performance Testing

### Frontend Performance Metrics

**Initial Load Time:**

1. Open DevTools Performance tab
2. Clear cache and hard reload (Ctrl+Shift+R)
3. Record load time

**Expected:**
- [ ] First Contentful Paint < 1s
- [ ] Time to Interactive < 2s
- [ ] Total load time < 2s
- [ ] No render-blocking resources

**Component Render Performance:**

1. Open large project (10+ entities)
2. Open DevTools Performance tab
3. Record actions (open entity editor, switch tabs)
4. Analyze

**Expected:**
- [ ] Component render < 100ms
- [ ] 60 FPS during animations
- [ ] No long tasks (> 50ms)
- [ ] Smooth scrolling

**Memory Usage:**

1. Open DevTools Memory tab
2. Take heap snapshot (baseline)
3. Use app for 10 minutes
4. Take another snapshot
5. Compare

**Expected:**
- [ ] Memory usage < 100MB
- [ ] No detached DOM nodes
- [ ] No memory leaks
- [ ] Memory released after closing dialogs

### API Response Times

Measure with DevTools Network tab:

**Expected Response Times:**
- [ ] Health check < 50ms
- [ ] Load project < 500ms
- [ ] Validate < 5s
- [ ] Preview entity < 2s
- [ ] Execute workflow < 15s
- [ ] Load schema < 500ms
- [ ] Download initiates immediately

---

## Feature-Specific Behavior

### Validation Result Caching

1. Open project
2. Click "Validate All"
3. Note request time in Network tab
4. Click "Validate All" again immediately
5. **Expected**: No new API request (cached)
6. Wait 5+ minutes
7. Click "Validate All" again
8. **Expected**: New API request (cache expired)

**Browser Notes:**
- Chrome: Check "Preserve log" in Network tab
- Firefox: Network tab auto-clears on reload
- Safari: Network tab under "Develop" menu

### Tooltips

1. Hover over "Validate All" button
2. Hover over validation tabs
3. Hover over entity validation buttons
4. Hover over "Apply Fix" buttons

**Expected:**
- [ ] Appears within 500ms
- [ ] Text readable
- [ ] Disappears on mouse-out
- [ ] No overlapping elements

**Safari Note**: Tooltips may appear slower

### Loading Indicators

1. Click "Validate All"
2. Observe loading skeleton

**Expected:**
- [ ] Appears immediately
- [ ] Realistic multi-line structure
- [ ] Smooth pulsing animation
- [ ] Instant replacement when data loads
- [ ] No flash of empty content

**Performance Tip**: Throttle to "Slow 3G" to observe skeleton

### Success Animations

1. Make YAML change
2. Save project
3. Observe success notification

**Expected:**
- [ ] Smooth scale-in (~300ms)
- [ ] No stuttering
- [ ] Auto-dismiss after 3s
- [ ] GPU-accelerated (no jank)

### Debounced Validation

1. Type rapidly in YAML editor
2. Monitor Network tab

**Expected:**
- [ ] Validation waits 500ms after last keystroke
- [ ] Only one request after typing stops
- [ ] No "validation storm"
- [ ] Typing remains responsive

### ag-Grid Data Preview

1. Load entity preview
2. Observe ag-grid

**Expected:**
- [ ] Renders with proper styling
- [ ] Good text contrast
- [ ] Appropriate row/header height
- [ ] Readable font size (10-11px)
- [ ] Smooth scrolling
- [ ] Columns resizable
- [ ] Sorting works

### Fixed Values Grid

1. Create entity with type `fixed`
2. Add keys and columns
3. Interact with grid (add row, edit, delete)

**Expected:**
- [ ] Grid displays with correct columns
- [ ] Rows addable
- [ ] Cells editable (click to edit)
- [ ] Checkbox selection works
- [ ] Delete removes selected rows
- [ ] Data saves to YAML correctly
- [ ] Grid compact (small fonts, padding)

---

## Accessibility Testing

For comprehensive accessibility testing, see **[Accessibility Testing Guide](ACCESSIBILITY_TESTING_GUIDE.md)**.

**Quick Checklist:**

- [ ] All interactive elements reachable via keyboard
- [ ] Focus indicators visible and high contrast
- [ ] Screen reader announces content correctly
- [ ] Color contrast meets WCAG 2.1 Level AA (4.5:1)
- [ ] Form validation errors announced to screen readers
- [ ] Modals trap focus and return focus on close
- [ ] Information not conveyed by color alone

---

## Test Results Template

### Non-Functional Test Report

```markdown
## Non-Functional Test Report - [Date]

**Tester**: [Name]
**Environment**: [OS, Browser versions]
**Backend**: [Version/commit]
**Frontend**: [Version/commit]

### Browser Compatibility Matrix

| Feature | Chrome 121 | Firefox 115 | Edge 121 | Safari 16 |
|---------|-----------|-------------|----------|-----------|
| Application Load | ✅ | ✅ | ✅ | ⚠️ Slow |
| YAML Editor | ✅ | ✅ | ✅ | ✅ |
| Entity Editor | ✅ | ✅ | ✅ | ✅ |
| Validation | ✅ | ✅ | ✅ | ❌ Cache |
| Execute Workflow | ✅ | ✅ | ✅ | ✅ |
| Download | ✅ | ✅ | ✅ | ✅ |
| Data Sources | ✅ | ✅ | ✅ | ✅ |
| Animations | ✅ | ✅ | ✅ | ⚠️ Jank |

**Legend:**
- ✅ Pass
- ⚠️ Minor Issue
- ❌ Fail
- ⏸️ Blocked

### Performance Metrics

| Metric | Chrome | Firefox | Edge | Safari | Target |
|--------|--------|---------|------|--------|--------|
| Initial Load | 1.2s | 1.5s | 1.3s | 1.8s | < 2s |
| Project Load | 450ms | 500ms | 480ms | 600ms | < 500ms |
| Validation | 3.2s | 3.5s | 3.3s | 4.1s | < 5s |
| Execute | 8.5s | 9.1s | 8.7s | 10.2s | < 15s |
| Memory (10min) | 85MB | 92MB | 87MB | 105MB | < 100MB |

### Accessibility Audit

**Automated Testing (axe DevTools):**
- Critical: 0
- Serious: 0
- Moderate: 2
- Minor: 1

**Manual Testing:**
- [ ] Keyboard navigation - Pass
- [ ] Screen reader - Pass
- [ ] Color contrast - Pass
- [ ] Focus management - Pass

**Issues:**
1. Minor: Some icon-only buttons missing aria-label

### Issues Found

**[P2] Safari Animation Performance**
- Stuttering in theme transitions
- Only affects Safari 16
- Minor UX impact

**[P3] Validation Cache Edge Case**
- Rare cache invalidation delay
- Workaround: Manual refresh

### Recommendations

1. Optimize Safari CSS animations
2. Add aria-labels to icon-only buttons
3. Review validation cache TTL logic

### Sign-off

- [x] All critical browsers tested
- [x] Performance targets met
- [x] No blocking accessibility issues
- [ ] Minor issues documented for future fix
```

---

## Appendix

### Useful Keyboard Shortcuts

**Application:**
- `Ctrl/Cmd + S` - Save project
- `Ctrl/Cmd + K` - Command palette
- `Ctrl/Cmd + /` - Toggle comments

**DevTools:**
- `F12` - Open/close DevTools
- `Ctrl/Cmd + Shift + C` - Element picker
- `Ctrl/Cmd + Shift + M` - Responsive mode
- `Ctrl/Cmd + Shift + P` - Command menu

### Common Performance Issues

**Slow Initial Load:**
- Check network throttling disabled
- Clear browser cache
- Verify backend running

**High Memory Usage:**
- Check for memory leaks in DevTools
- Close unused dialogs/components
- Verify ag-Grid row virtualization

**Animation Jank:**
- Enable GPU acceleration
- Check CSS will-change property
- Monitor frame rate in Performance tab

### Resources

- [Chrome DevTools Docs](https://developer.chrome.com/docs/devtools/)
- [Firefox Developer Tools](https://firefox-source-docs.mozilla.org/devtools-user/)
- [WebKit Web Inspector](https://webkit.org/web-inspector/)
- [Web Performance Working Group](https://www.w3.org/webperf/)

---

## Contact

For non-functional testing questions:
- File GitHub issue: https://github.com/humlab-sead/sead_shape_shifter/issues
- Tag with `performance`, `browser-compatibility`, or `accessibility`
- Include browser version and test results
