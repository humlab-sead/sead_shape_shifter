# Non-Functional Testing Guide - Shape Shifter

## Overview

This guide covers non-functional testing requirements for Shape Shifter, including browser compatibility, performance benchmarks, and accessibility compliance. Use this guide in conjunction with the [Testing Guide](../TESTING.md) for comprehensive coverage.

## Table of Contents

- [Cross-Browser Testing](#cross-browser-testing)
- [Feature-Specific Behavior](#feature-specific-behavior)
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

**Quick Checklist:**

- [ ] All interactive elements reachable via keyboard
- [ ] Focus indicators visible and high contrast
- [ ] Screen reader announces content correctly
- [ ] Color contrast meets WCAG 2.1 Level AA (4.5:1)
- [ ] Form validation errors announced to screen readers
- [ ] Modals trap focus and return focus on close
- [ ] Information not conveyed by color alone

---
