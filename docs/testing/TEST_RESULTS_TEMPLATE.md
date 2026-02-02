# Test Results Template - Shape Shifter

## Test Session Template

Use this template to document test results:

```markdown
## Frontend Manual Test Session - [Date]

**Tester**: [Your Name]
**Environment**: [OS, Browser versions]
**Backend Version**: [Backend version or commit]
**Frontend Version**: [Frontend version or commit]

### Test Summary

| Category | Tests Passed | Tests Failed | Notes |
|----------|--------------|--------------|-------|
| Core Application | 5/5 | 0 | All passed |
| Project Editor | 8/10 | 2 | Save occasionally slow |
| Entity Editor | 15/15 | 0 | All passed |
| Validation | 6/7 | 1 | Cache not invalidating |
| Execute Workflow | 9/9 | 0 | All passed |
| Error Handling | 5/5 | 0 | All passed |

### Detailed Results

#### Project Editor - Save Performance

**Issue**: Save button occasionally takes > 2 seconds

**Steps to Reproduce**:
1. Open large project (20+ entities)
2. Make small edit
3. Click Save

**Expected**: Save completes within 1 second
**Actual**: Save takes 2-3 seconds

**Severity**: Medium
**Browser**: Chrome 121, Firefox 115
**Priority**: P2

#### Validation - Cache Invalidation

**Issue**: Validation cache not invalidating after edit

**Steps to Reproduce**:
1. Run validation
2. Edit entity
3. Save
4. Run validation again

**Expected**: New validation request
**Actual**: Cached results returned

**Severity**: High
**Browser**: All
**Priority**: P1

### Issues Found

1. **[P1] Validation cache not invalidating** - See details above
2. **[P2] Save performance degradation** - See details above

### Recommendations

1. Investigate validation cache invalidation logic
2. Profile save operation for large configurations
3. Add integration tests for critical workflows

### Notes

- All critical functional paths working
- No blocking issues found
- Minor performance degradation in large projects
```

---

## Quick Test Checklists

### 5-Minute Smoke Test

Minimal test to verify basic functionality:

- [ ] Application loads without errors
- [ ] Can navigate between pages
- [ ] Can open a project
- [ ] Can edit and save YAML
- [ ] Can run validation
- [ ] Can open entity editor
- [ ] Can execute workflow
- [ ] Theme toggle works

### 15-Minute Regression Test

After code changes, verify core features:

- [ ] Load project list
- [ ] Create new project
- [ ] Edit existing project
- [ ] Save changes
- [ ] Run full validation
- [ ] View validation results
- [ ] Create new entity
- [ ] Edit entity (all tabs)
- [ ] Add foreign key
- [ ] Test foreign key join
- [ ] Load entity preview
- [ ] Apply auto-fix
- [ ] Execute workflow (Excel output)
- [ ] Download execution result
- [ ] Test error scenarios

### 45-Minute Full Functional Test

Comprehensive functional test:

- [ ] Complete all core sections in [Manual Testing Guide](../MANUAL_TESTING_GUIDE.md)
- [ ] Test error scenarios (see [Error Scenario Testing](ERROR_SCENARIO_TESTING.md))
- [ ] Verify all features work correctly
- [ ] Document any issues
- [ ] Fill out test results template

**For browser compatibility, performance, and accessibility testing, see [Non-Functional Testing Guide](NON_FUNCTIONAL_TESTING_GUIDE.md).**

---

## Issue Reporting Template

```markdown
## Bug Report - [Short Description]

**Reporter**: [Your Name]
**Date**: [Date]
**Environment**: [Browser/OS]
**Severity**: [Critical/High/Medium/Low]

### Description

[Clear description of the issue]

### Steps to Reproduce

1. [First step]
2. [Second step]
3. [...]

### Expected Behavior

[What should happen]

### Actual Behavior

[What actually happens]

### Screenshots/Videos

[Attach if applicable]

### Console Errors

```
[Paste console errors here]
```

### Additional Context

[Any other relevant information]
```

---

## Contact

For testing questions:
- File GitHub issue: https://github.com/humlab-sead/sead_shape_shifter/issues
- Include test results using this template
- Attach screenshots/videos if applicable
