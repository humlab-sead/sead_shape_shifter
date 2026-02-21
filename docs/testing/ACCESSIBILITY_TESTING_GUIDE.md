# Accessibility Testing Guide - Shape Shifter

## Overview

This guide provides comprehensive accessibility testing procedures for the Shape Shifter Project Editor. Use this guide to ensure the application is usable by people with disabilities and complies with accessibility standards.

## Accessibility Standards

- **WCAG 2.1 Level AA** compliance target
- **Section 508** compliance for government use
- **ARIA** best practices for dynamic web applications

---

## Keyboard Navigation

### Tab Through Interface

**Test: Navigate All Interactive Elements**

1. Tab through all interactive elements
2. Note tab order

**Expected Results:**
- [ ] All buttons/links reachable via Tab
- [ ] Tab order logical (top-to-bottom, left-to-right)
- [ ] Focus indicators clearly visible
- [ ] Can activate with Enter/Space
- [ ] Can close dialogs with Escape
- [ ] No keyboard traps

### Form Navigation

**Test: Form Field Navigation**

1. Open entity editor
2. Tab through all form fields
3. Use arrow keys in dropdowns

**Expected Results:**
- [ ] Tab moves between fields logically
- [ ] Arrow keys navigate dropdowns
- [ ] Can submit form with Enter
- [ ] Can cancel with Escape

---

## Screen Reader Testing

### Tools

- **Windows**: NVDA (free) - https://www.nvaccess.org/
- **macOS**: VoiceOver (built-in)
- **Linux**: Orca

### Screen Reader Compatibility

**Test: Basic Screen Reader Navigation**

1. Enable screen reader
2. Navigate application
3. Fill out forms
4. Trigger notifications

**Expected Results:**
- [ ] All buttons have accessible labels
- [ ] Form fields have labels
- [ ] Errors announced
- [ ] Notifications announced
- [ ] Landmarks defined (nav, main, etc.)
- [ ] ARIA attributes appropriate

---

## Color Contrast

### Contrast Ratios

**Test: Check Color Contrast**

1. Install WAVE or axe DevTools extension
2. Run accessibility audit
3. Check color contrast

**Expected Results:**
- [ ] Normal text: 4.5:1 minimum
- [ ] Large text: 3:1 minimum
- [ ] UI components: 3:1 minimum
- [ ] No contrast failures

**Testing Tools:**
- WAVE Browser Extension
- axe DevTools
- Chrome Lighthouse
- WebAIM Contrast Checker

### Color Blindness

**Test: Color Blindness Simulation**

1. Use browser extension (e.g., "Colorblinding")
2. Simulate different types of color blindness:
   - Protanopia (red-blind)
   - Deuteranopia (green-blind)
   - Tritanopia (blue-blind)
   - Achromatopsia (total color blindness)
3. Verify UI still usable

**Expected Results:**
- [ ] Information not conveyed by color alone
- [ ] Icons/text labels used with colors
- [ ] Error/success states distinguishable
- [ ] All interactive elements identifiable

---

## Focus Management

### Focus Indicators

**Test: Visible Focus States**

1. Tab through interface
2. Observe focus rings/outlines

**Expected Results:**
- [ ] Focus indicator visible on all elements
- [ ] Focus indicator high contrast
- [ ] Custom focus styles maintain visibility
- [ ] Focus not hidden by CSS

### Modal Focus Trap

**Test: Dialog Focus Management**

1. Open entity editor dialog
2. Tab through dialog
3. Try to tab outside dialog

**Expected Results:**
- [ ] Focus trapped within dialog
- [ ] Tab cycles through dialog elements
- [ ] Focus returns to trigger on close
- [ ] Can close with Escape

---

## ARIA Implementation

### Semantic HTML

**Test: Proper HTML Structure**

1. Inspect page with DevTools
2. Review HTML structure
3. Check for semantic elements

**Expected Results:**
- [ ] Proper heading hierarchy (h1, h2, h3)
- [ ] Landmarks used (<nav>, <main>, <aside>)
- [ ] Lists marked up with <ul>, <ol>
- [ ] Forms use <form>, <label>, <input>

### ARIA Attributes

**Test: ARIA Usage**

1. Inspect interactive components
2. Check ARIA attributes
3. Verify ARIA states update

**Expected Results:**
- [ ] aria-label on icon-only buttons
- [ ] aria-describedby for help text
- [ ] aria-expanded on collapsible sections
- [ ] aria-live for dynamic content
- [ ] role attributes where appropriate

---

## Component-Specific Testing

### Data Tables

**Test: Table Accessibility**

1. Navigate to data preview/grid
2. Use screen reader on table
3. Navigate with keyboard

**Expected Results:**
- [ ] Table has caption or aria-label
- [ ] Column headers announced
- [ ] Row headers announced (if applicable)
- [ ] Cell content readable
- [ ] Can navigate cells with arrow keys

### Forms

**Test: Form Accessibility**

1. Fill out entity editor form
2. Trigger validation errors
3. Use screen reader

**Expected Results:**
- [ ] All fields have labels
- [ ] Required fields indicated
- [ ] Error messages associated with fields (aria-describedby)
- [ ] Field hints available to screen readers
- [ ] Error summary at top of form

### Dialogs/Modals

**Test: Dialog Accessibility**

1. Open various dialogs
2. Navigate with keyboard
3. Use screen reader

**Expected Results:**
- [ ] Dialog has role="dialog"
- [ ] aria-labelledby points to title
- [ ] Focus moves to dialog on open
- [ ] Escape key closes dialog
- [ ] Focus returns to trigger on close

### Notifications

**Test: Notification Accessibility**

1. Trigger various notifications (success, error, warning)
2. Use screen reader

**Expected Results:**
- [ ] Notifications have role="alert" or aria-live
- [ ] Screen reader announces notifications
- [ ] Notifications remain visible long enough
- [ ] Can dismiss with keyboard

---

## Automated Testing

### Tools

- **axe DevTools** - Browser extension for automated testing
- **Lighthouse** - Built into Chrome DevTools
- **WAVE** - Web accessibility evaluation tool
- **pa11y** - Command-line accessibility testing

### Running Automated Tests

**Using axe DevTools:**

1. Install axe DevTools extension
2. Open DevTools
3. Navigate to axe DevTools tab
4. Click "Scan ALL of my page"
5. Review violations

**Using Lighthouse:**

1. Open Chrome DevTools
2. Navigate to Lighthouse tab
3. Select "Accessibility" category
4. Click "Analyze page load"
5. Review accessibility score and issues

**Expected Results:**
- [ ] No critical violations
- [ ] Lighthouse score ≥ 90
- [ ] All issues documented and prioritized

---

## Manual Testing Checklist

### Keyboard-Only Navigation

Complete all core workflows using only keyboard:

- [ ] Navigate to Projects page
- [ ] Open a project
- [ ] Edit YAML
- [ ] Save changes
- [ ] Open entity editor
- [ ] Fill out all form fields
- [ ] Add foreign key
- [ ] Save entity
- [ ] Run validation
- [ ] Execute workflow
- [ ] Close all dialogs

### Screen Reader Workflow

Complete core workflow with screen reader:

- [ ] Navigate menu structure
- [ ] Open project from list
- [ ] Understand entity list
- [ ] Edit entity via form
- [ ] Understand validation results
- [ ] Execute workflow
- [ ] Understand success/error messages

---

## Known Issues and Workarounds

### Current Limitations

Document any known accessibility issues:

1. **Issue**: [Description]
   - **Impact**: [Who is affected]
   - **Workaround**: [Temporary solution]
   - **Status**: [Planned fix]

---

## Accessibility Testing Report Template

```markdown
## Accessibility Test Report - [Date]

**Tester**: [Your Name]
**Testing Tools**: [Tools used]
**Browser**: [Browser and version]
**Screen Reader**: [If applicable]

### Summary

| Category | Pass | Fail | Notes |
|----------|------|------|-------|
| Keyboard Navigation | X/Y | 0 | |
| Screen Reader | X/Y | 0 | |
| Color Contrast | X/Y | 0 | |
| Focus Management | X/Y | 0 | |
| ARIA Implementation | X/Y | 0 | |

### Automated Test Results

**axe DevTools:**
- Critical: 0
- Serious: 0
- Moderate: 0
- Minor: 0

**Lighthouse Score:** XX/100

### Issues Found

1. **[Severity] Issue Title**
   - **Location**: [Component/Page]
   - **WCAG Criterion**: [Success Criterion]
   - **Impact**: [Description]
   - **Steps to Reproduce**:
     1. Step 1
     2. Step 2
   - **Expected**: [Correct behavior]
   - **Actual**: [Current behavior]
   - **Recommendation**: [How to fix]

### Recommendations

1. [High-priority recommendation]
2. [Medium-priority recommendation]
3. [Low-priority recommendation]

### Sign-off

- [ ] Application meets WCAG 2.1 Level AA
- [ ] No critical accessibility barriers
- [ ] All issues documented
```

---

## Resources

### Standards and Guidelines

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Section 508 Standards](https://www.section508.gov/)

### Testing Tools

- [axe DevTools](https://www.deque.com/axe/devtools/)
- [WAVE](https://wave.webaim.org/)
- [NVDA Screen Reader](https://www.nvaccess.org/)
- [Color Contrast Analyzer](https://www.tpgi.com/color-contrast-checker/)

### Learning Resources

- [WebAIM](https://webaim.org/)
- [A11ycasts on YouTube](https://www.youtube.com/playlist?list=PLNYkxOF6rcICWx0C9LVWWVqvHlYJyqw7g)
- [Inclusive Components](https://inclusive-components.design/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)

---

## Contact

For accessibility questions or to report issues:
- File GitHub issue: https://github.com/humlab-sead/sead_shape_shifter/issues
- Tag with `accessibility` label
- Include test results and screenshots
