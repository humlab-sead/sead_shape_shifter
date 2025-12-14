# Sprint 8.1 Integration Testing Checklist

**Date**: December 14, 2025  
**Sprint**: 8.1 - Integration & Workflows  
**Duration**: 2 days  
**Servers**: Backend (localhost:8000) ✅ | Frontend (localhost:5175) ✅

---

## Integration Test Plan

### Phase 1: Auto-Fix Workflow (Critical Path)

#### Test 1: Basic Auto-Fix Flow
- [ ] Navigate to http://localhost:5175
- [ ] Load or create a test configuration
- [ ] Trigger validation
- [ ] Verify ValidationPanel displays issues
- [ ] Click "Apply Fix" on an auto-fixable issue
- [ ] Verify PreviewFixesModal opens
- [ ] Review proposed changes
- [ ] Click "Apply Fixes"
- [ ] Verify success notification with backup path
- [ ] Verify configuration reloads
- [ ] Verify validation re-runs
- [ ] **Expected**: Complete workflow without errors

#### Test 2: Preview Modal Functionality
- [ ] Open preview modal for multiple fixes
- [ ] Verify fixable count is correct
- [ ] Expand action panels
- [ ] Verify color coding (green/red/warning)
- [ ] Check warning messages for destructive ops
- [ ] Verify "Apply X Fixes" button count matches
- [ ] Cancel and verify no changes applied
- [ ] **Expected**: All UI elements functional

#### Test 3: Backup & Rollback
- [ ] Note current configuration state
- [ ] Apply fixes and note backup path
- [ ] Verify backup file exists at path
- [ ] Manually corrupt a fix (simulate error)
- [ ] Verify rollback occurs on error
- [ ] Check configuration state unchanged
- [ ] **Expected**: Backup created, rollback works

#### Test 4: Non-Fixable Issues
- [ ] Trigger validation with non-fixable issues
- [ ] Verify these are shown in preview
- [ ] Verify labeled as "Manual fix required"
- [ ] Verify not included in fix count
- [ ] Verify suggestions provided
- [ ] **Expected**: Clear distinction between fixable/non-fixable

### Phase 2: Validation Panel Integration

#### Test 5: Category Grouping
- [ ] Trigger validation with mixed issue types
- [ ] Verify issues grouped by category (Config/Data/Structure)
- [ ] Verify severity indicators (error/warning/info)
- [ ] Expand/collapse category groups
- [ ] **Expected**: Clear organization

#### Test 6: Validation Performance
- [ ] Run validation on large configuration
- [ ] Note time to complete
- [ ] Verify progress indicators show
- [ ] Check memory usage doesn't spike
- [ ] **Expected**: < 30 seconds for typical config

#### Test 7: Real-time Validation
- [ ] Make configuration change
- [ ] Verify validation triggers automatically
- [ ] Verify debouncing works (no excessive calls)
- [ ] **Expected**: Responsive, not overwhelming

### Phase 3: API Integration

#### Test 8: Preview Endpoint
```bash
# Test preview fixes API
curl -X POST http://localhost:8000/api/v1/configurations/{name}/fixes/preview \
  -H "Content-Type: application/json" \
  -d '[{
    "severity": "error",
    "code": "COLUMN_NOT_FOUND",
    "message": "Column missing_col not found",
    "entity": "test_entity",
    "field": "missing_col",
    "category": "data"
  }]'
```
- [ ] Verify response structure correct
- [ ] Verify fixable_count accurate
- [ ] Verify actions list populated
- [ ] **Expected**: Valid JSON response

#### Test 9: Apply Endpoint
```bash
# Test apply fixes API
curl -X POST http://localhost:8000/api/v1/configurations/{name}/fixes/apply \
  -H "Content-Type: application/json" \
  -d '[...]'
```
- [ ] Verify backup path returned
- [ ] Verify fixes_applied count
- [ ] Verify updated_config returned
- [ ] Check backup file created
- [ ] **Expected**: Fixes applied, backup created

### Phase 4: Error Handling

#### Test 10: Network Errors
- [ ] Stop backend server temporarily
- [ ] Try to run validation
- [ ] Verify error message shown
- [ ] Restart backend
- [ ] Retry validation
- [ ] **Expected**: Graceful error handling

#### Test 11: Invalid Data
- [ ] Try to apply fixes with invalid error format
- [ ] Verify appropriate error message
- [ ] Verify no partial changes applied
- [ ] **Expected**: Validation prevents bad requests

#### Test 12: Concurrent Operations
- [ ] Start validation
- [ ] Try to apply fixes during validation
- [ ] Verify operations don't conflict
- [ ] **Expected**: Proper operation queuing or blocking

### Phase 5: UX & Accessibility

#### Test 13: Loading States
- [ ] Trigger operations with network throttling
- [ ] Verify loading spinners appear
- [ ] Verify buttons disabled during operations
- [ ] Verify loading text descriptive
- [ ] **Expected**: Clear feedback during operations

#### Test 14: Keyboard Navigation
- [ ] Tab through validation panel
- [ ] Use Enter to apply fixes
- [ ] Use Escape to close modal
- [ ] **Expected**: Full keyboard accessibility

#### Test 15: Screen Reader
- [ ] Enable screen reader
- [ ] Navigate validation results
- [ ] Verify ARIA labels present
- [ ] Verify status announcements
- [ ] **Expected**: Accessible to screen readers

### Phase 6: Cross-Browser Testing

#### Test 16: Browser Compatibility
- [ ] Chrome/Chromium (latest)
- [ ] Firefox (latest)
- [ ] Safari (if available)
- [ ] Edge (latest)
- [ ] **Expected**: Consistent behavior

---

## Performance Benchmarks

### Target Metrics
- Validation time: < 30 seconds for typical config
- Preview modal open: < 500ms
- Apply fixes: < 2 seconds
- Config reload: < 1 second
- Re-validation: < 5 seconds

### Actual Measurements
```
Configuration: ____________
Entities: ____
Validation time: ________ seconds
Preview modal open: ________ ms
Apply fixes: ________ seconds
Config reload: ________ seconds
Re-validation: ________ seconds
```

---

## Issues Found

### Critical (Blocking)
_None yet_

### High Priority
_None yet_

### Medium Priority
_None yet_

### Low Priority / Enhancement
_None yet_

---

## Quick Wins Identified

### UI Polish Opportunities
- [ ] Add tooltip to "Apply Fix" button explaining workflow
- [ ] Add keyboard shortcut hint to modal
- [ ] Improve loading skeleton for validation panel
- [ ] Add animation to success notification
- [ ] Add "What's this?" help icon for auto-fix

### Performance Optimizations
- [ ] Cache validation results for 5 minutes
- [ ] Debounce validation triggers (500ms)
- [ ] Lazy load PreviewFixesModal component
- [ ] Optimize validation query (add indexes)
- [ ] Add request caching for preview endpoint

### Documentation Needs
- [ ] Tooltip explaining backup files
- [ ] Help text for non-fixable issues
- [ ] Link to troubleshooting guide
- [ ] Example workflow in UI
- [ ] "Learn More" links

---

## Test Execution Log

### Date: ____________

**Tester**: ____________

**Tests Completed**: ____ / 16

**Pass Rate**: ____%

**Critical Issues**: ____

**Time Spent**: ____ hours

### Notes
```
[Add testing notes here]
```

---

## Next Steps

After completing this checklist:

1. **Document findings** in Sprint 8.1 completion doc
2. **Create bug tickets** for issues found
3. **Implement quick wins** identified
4. **Move to Sprint 8.2** (Testing & Bug Fixes)

---

## Reference

- **Frontend URL**: http://localhost:5175
- **Backend API**: http://localhost:8000/api/v1
- **API Docs**: http://localhost:8000/api/v1/docs
- **Sprint Docs**: SPRINT7.4_COMPLETE.md, SPRINT7.4_SUMMARY.md
- **Architecture**: docs/BACKEND_INTEGRATION.md
