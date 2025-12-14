# Sprint 8.1 Quick Start Guide

**Date**: December 14, 2025  
**Objective**: Integration testing and workflow polish  
**Duration**: 2 days

---

## Prerequisites ✅

- [x] Backend running on http://localhost:8000
- [x] Frontend running on http://localhost:5175
- [x] Test configurations available in `input/` and `tests/config/`
- [x] Sprint 7.1-7.4 complete (validation & auto-fix)

---

## Quick Start: Manual Integration Test

### Step 1: Access the Application

Open your browser and navigate to:
```
http://localhost:5175
```

### Step 2: Load a Test Configuration

**Option A: Load existing config**
- Use the configuration selector
- Choose `arbodat.yml` or `tests/config/config.yml`

**Option B: Create test config**
- Create new configuration
- Add test entity with intentional error (e.g., missing column)

### Step 3: Trigger Validation

1. Click "Validate Configuration" or "Run Validation"
2. Wait for validation to complete (should be < 30 seconds)
3. Observe ValidationPanel displaying issues

### Step 4: Test Auto-Fix Workflow

1. **Identify auto-fixable issue**:
   - Look for issues with "Apply Fix" button
   - Common examples:
     - COLUMN_NOT_FOUND (missing column in data)
     - TYPE_MISMATCH (data type incompatibility)

2. **Preview fixes**:
   - Click "Apply Fix" button
   - PreviewFixesModal should open
   - Verify:
     - ✓ Fixable count displayed
     - ✓ Action panels expandable
     - ✓ Color coding (green=add, red=remove)
     - ✓ Warnings for destructive operations

3. **Apply fixes**:
   - Review proposed changes
   - Click "Apply X Fixes"
   - Observe:
     - ✓ Loading state during application
     - ✓ Success notification with backup path
     - ✓ Modal closes automatically

4. **Verify results**:
   - Configuration should reload
   - Validation should re-run
   - Fixed issues should disappear
   - Backup file should exist

### Step 5: Verify Backup

```bash
# Check backup was created
ls -lt backups/ | head -5

# View backup content
cat backups/test_config.backup.TIMESTAMP.yml
```

---

## Quick Wins to Implement

### 1. Add Debouncing to Validation (5 minutes)

**File**: `frontend/src/composables/useDataValidation.ts`

Add debouncing to prevent excessive validation calls:

```typescript
import { debounce } from 'lodash-es'

// Debounce validation trigger
const debouncedValidate = debounce(async (configName: string) => {
  await validateConfiguration(configName)
}, 500) // 500ms delay
```

**Benefit**: Prevents validation spam during rapid edits

---

### 2. Add Tooltip to Apply Fix Button (10 minutes)

**File**: `frontend/src/components/validation/ValidationPanel.vue`

```vue
<v-tooltip location="top">
  <template v-slot:activator="{ props }">
    <v-btn 
      v-bind="props"
      color="primary" 
      size="small"
      @click="handleApplyFix(issue)"
    >
      Apply Fix
    </v-btn>
  </template>
  <span>Preview and apply automated fix with backup</span>
</v-tooltip>
```

**Benefit**: Better UX, explains what will happen

---

### 3. Add Loading Skeleton for ValidationPanel (15 minutes)

**File**: `frontend/src/components/validation/ValidationPanel.vue`

```vue
<v-skeleton-loader
  v-if="loading"
  type="list-item-three-line@3"
  class="mb-4"
/>
```

**Benefit**: Better perceived performance

---

### 4. Add Success Animation (10 minutes)

**File**: `frontend/src/views/ConfigurationDetailView.vue`

Use Vuetify's transition for success notification:

```vue
<v-scale-transition>
  <v-alert
    v-if="showSuccessAlert"
    type="success"
    closable
  >
    {{ successMessage }}
  </v-alert>
</v-scale-transition>
```

**Benefit**: More polished feel

---

### 5. Cache Validation Results (20 minutes)

**File**: `frontend/src/composables/useDataValidation.ts`

```typescript
// Add simple cache with 5-minute TTL
const validationCache = new Map<string, {
  result: ValidationError[]
  timestamp: number
}>()

const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

async function validateConfiguration(configName: string) {
  const cached = validationCache.get(configName)
  
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    errors.value = cached.result
    return
  }
  
  // ... existing validation code
  
  validationCache.set(configName, {
    result: errors.value,
    timestamp: Date.now()
  })
}
```

**Benefit**: Reduces API calls, faster response

---

## Performance Optimization Checklist

### Backend
- [ ] Check validation query performance (EXPLAIN ANALYZE)
- [ ] Add database indexes if needed
- [ ] Verify connection pooling configured
- [ ] Check memory usage during validation
- [ ] Profile slow endpoints

### Frontend
- [ ] Lazy load PreviewFixesModal component
- [ ] Use v-show instead of v-if for frequent toggles
- [ ] Optimize re-renders with computed properties
- [ ] Check bundle size (npm run build)
- [ ] Profile with Chrome DevTools

### Network
- [ ] Enable gzip compression on backend
- [ ] Check API response sizes
- [ ] Verify CORS headers efficient
- [ ] Consider API response caching headers

---

## Testing Shortcuts

### API Testing with curl

**Test validation endpoint:**
```bash
curl -s http://localhost:8000/api/v1/configurations/test_config/validate | jq
```

**Test preview fixes:**
```bash
curl -X POST http://localhost:8000/api/v1/configurations/test_config/fixes/preview \
  -H "Content-Type: application/json" \
  -d '[{
    "severity": "error",
    "code": "COLUMN_NOT_FOUND",
    "message": "Column test_col not found",
    "entity": "test_entity",
    "field": "test_col",
    "category": "data"
  }]' | jq
```

**Check backend health:**
```bash
curl -s http://localhost:8000/ | jq
```

### Browser DevTools

**Check Network Performance:**
1. Open DevTools (F12)
2. Go to Network tab
3. Trigger validation
4. Check request timing:
   - Should be < 500ms for small configs
   - Should be < 5s for large configs

**Check Console for Errors:**
```javascript
// No errors should appear during normal operation
// Look for:
// - 404s (missing endpoints)
// - 500s (server errors)
// - CORS errors
// - Vue warnings
```

**Memory Profiling:**
1. Open Performance tab
2. Start recording
3. Trigger validation multiple times
4. Stop recording
5. Check for memory leaks (memory should return to baseline)

---

## Common Issues & Solutions

### Issue: "Configuration not found"
**Solution**: Check configuration file path in backend settings

### Issue: Validation takes too long
**Solution**: 
- Check sample size (should be ~1000 rows)
- Verify database indexes
- Check network latency

### Issue: Preview modal doesn't open
**Solution**:
- Check browser console for errors
- Verify API endpoint returns valid response
- Check modal v-model binding

### Issue: Fixes don't apply
**Solution**:
- Check backup directory permissions
- Verify configuration file is writable
- Check API error response

---

## Success Criteria for Sprint 8.1

- [ ] All critical path tests pass (Tests 1-4)
- [ ] No blocking bugs found
- [ ] Performance within targets (<30s validation)
- [ ] At least 3 quick wins implemented
- [ ] UX issues documented
- [ ] Ready for Sprint 8.2 (Testing & Bug Fixes)

---

## Time Tracking

**Day 1** (4 hours):
- [ ] Manual integration testing (2 hours)
- [ ] Implement 2-3 quick wins (1.5 hours)
- [ ] Document findings (0.5 hours)

**Day 2** (4 hours):
- [ ] Performance profiling (1 hour)
- [ ] Implement remaining quick wins (2 hours)
- [ ] Create Sprint 8.1 completion doc (1 hour)

---

## Next: Sprint 8.2

After Sprint 8.1:
1. Fix bugs found in integration testing
2. Update auto-fix service tests (1/13 → 13/13)
3. Cross-browser testing
4. Accessibility audit
5. Complete test coverage

---

## Resources

- **Integration Test Plan**: SPRINT8.1_INTEGRATION_TEST_PLAN.md
- **Phase 2 Status**: PHASE2_STATUS.md
- **API Docs**: http://localhost:8000/api/v1/docs
- **Previous Sprint Docs**: SPRINT7.2-7.4_COMPLETE.md
