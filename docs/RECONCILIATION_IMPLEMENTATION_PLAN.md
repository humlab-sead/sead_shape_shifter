# Reconciliation Feature Implementation Plan

## Current State Analysis

### ✅ Already Implemented (Backend)
- Auto-reconciliation service with batch processing
- Reconciliation configuration CRUD endpoints
- Entity suggestion/autocomplete endpoint
- Service health check endpoint
- Manual mapping CRUD (add/remove mappings)
- Auto-accept threshold configuration
- CLI script for reconciliation (`scripts/auto_reconcile.py`)
- Comprehensive logging with `[RECON]` prefix

### ✅ Already Implemented (Frontend)
- Basic ReconciliationView component with entity selection
- ReconciliationGrid with AG Grid integration
- Service status indicator (online/offline)
- Auto-accept and review threshold sliders
- Candidate review dialog
- Statistics chips (auto-matched, needs review, unmatched)
- Save changes functionality

---

## Gap Analysis - Missing Features

Based on the [RECONCILIATION_WORKFLOW.md](RECONCILIATION_WORKFLOW.md) documentation, the following features are referenced but not yet implemented:

### Priority 1: Critical User Experience Features

#### 1.1 Status Filtering & Search
**Status:** Not implemented  
**Workflow Reference:** Steps 3.1, 4.1  
**Description:** Users need to filter reconciliation results by status categories

**Required:**
- Filter dropdown/chips for: All, Auto-Accepted, Needs Review, Unmatched
- Search box to find specific queries/values
- URL state persistence for filters

**Impact:** HIGH - Core navigation requirement

---

#### 1.2 Batch Review Actions
**Status:** Partially implemented (single item only)  
**Workflow Reference:** Step 4.2  
**Description:** Efficiently process multiple items

**Required:**
- Bulk accept button (accept all visible/selected)
- Bulk reject button
- Row selection (checkboxes)
- "Select all" functionality
- Confirm dialog for bulk operations

**Impact:** HIGH - Critical for large datasets

---

#### 1.3 Alternative Search / Manual Matching
**Status:** Not implemented  
**Workflow Reference:** Step 4.2, 5.2  
**Description:** Search for different candidates when auto-match fails

**Required:**
- "Search Alternatives" button per row
- Search dialog with text input
- Real-time suggestion as user types (using `/suggest` endpoint)
- Accept from search results
- History of search attempts

**Impact:** HIGH - Essential for unmatched items

---

#### 1.4 Mark as Unmatched / Will Not Match
**Status:** Not implemented  
**Workflow Reference:** Step 5.2  
**Description:** Explicitly mark items that should not be matched

**Required:**
- "Mark Unmatched" button
- "Will Not Match" status
- Optional notes/reason field
- Persist unmatched state in reconciliation config
- Visual indicator in grid (gray out or special icon)

**Impact:** MEDIUM - Important for workflow completion

---

#### 1.5 Notes & Documentation
**Status:** Not implemented  
**Workflow Reference:** Steps 5.1, 5.2  
**Description:** Document why items are unmatched or decisions made

**Required:**
- Notes field in reconciliation mapping model
- Notes column in grid (expandable)
- Edit notes dialog
- Timestamps for when notes were added
- User attribution (who made the decision)

**Impact:** MEDIUM - Important for auditability

---

### Priority 2: Enhanced User Experience

#### 2.1 Progress Indicators
**Status:** Not implemented  
**Workflow Reference:** Step 2.2  
**Description:** Show progress during long-running reconciliation

**Required:**
- Progress bar during auto-reconcile
- Status messages (e.g., "Processing 50/150 queries")
- Cancel button to abort operation
- WebSocket or polling for real-time updates
- Estimated time remaining

**Impact:** MEDIUM - Better UX for large datasets

---

#### 2.2 Quality Statistics Dashboard
**Status:** Partially implemented (basic chips only)  
**Workflow Reference:** Step 7.1  
**Description:** Overview of reconciliation quality metrics

**Required:**
- Summary card showing:
  - Total queries
  - Auto-accept rate (%)
  - Average confidence score
  - Completion percentage
  - Unmatched rate with benchmark comparison
- Score distribution chart (histogram)
- Status over time (if multiple reconciliation runs)
- Export statistics as CSV

**Impact:** MEDIUM - Helps assess data quality

---

#### 2.3 Reconciliation History / Audit Log
**Status:** Not implemented  
**Workflow Reference:** Step 6.2  
**Description:** Track changes and decisions over time

**Required:**
- History log of all reconciliation runs
- Before/after comparison
- User who ran reconciliation
- Timestamp of each run
- Ability to rollback to previous state
- View changes between versions

**Impact:** LOW - Nice to have for production

---

#### 2.4 Preview Matched Data
**Status:** Not implemented  
**Workflow Reference:** Step 6.3  
**Description:** Preview final output with matched IDs

**Required:**
- Preview table showing:
  - Original data
  - Matched SEAD ID
  - Matched name
  - Confidence score
- Filter to show only changed rows
- Export preview as CSV
- Compare with original entity data

**Impact:** MEDIUM - Validation before final export

---

### Priority 3: Advanced Features

#### 3.1 Multi-Entity Reconciliation
**Status:** Not implemented  
**Workflow Reference:** Advanced Workflows section  
**Description:** Reconcile multiple entities in sequence

**Required:**
- Entity selection: multi-select dropdown
- "Reconcile All" button
- Queue-based processing
- Individual entity progress tracking
- Stop/skip individual entities
- Summary across all entities

**Impact:** LOW - Convenience feature

---

#### 3.2 Reconciliation Templates / Presets
**Status:** Not implemented  
**Workflow Reference:** Step 1.1  
**Description:** Save and reuse common reconciliation configurations

**Required:**
- Template management UI
- Save current settings as template
- Load template to populate fields
- Default templates for common entity types
- Template library (site, taxon, location presets)

**Impact:** LOW - Productivity enhancement

---

#### 3.3 Smart Threshold Recommendations
**Status:** Not implemented  
**Workflow Reference:** Step 1.2  
**Description:** Suggest optimal threshold based on data

**Required:**
- Analyze score distribution after test run
- Recommend threshold based on:
  - Score gap between top candidates
  - Entity type characteristics
  - Historical match quality
- "Optimize Threshold" button
- Explanation of recommendation

**Impact:** LOW - Machine learning enhancement

---

#### 3.4 Conflict Detection & Resolution
**Status:** Not implemented  
**Workflow Reference:** Implicit in Step 4  
**Description:** Handle cases where multiple source items match same SEAD ID

**Required:**
- Detect 1:many and many:1 relationships
- Warning indicators in grid
- Conflict resolution dialog:
  - Show all items matching same ID
  - Suggest which to keep
  - Option to split or merge
- Validation before save

**Impact:** MEDIUM - Data integrity

---

#### 3.5 Batch Import/Export Mappings
**Status:** Not implemented  
**Workflow Reference:** Not documented  
**Description:** Import pre-existing mappings or export for external review

**Required:**
- Export current mappings as CSV/Excel
- Import mappings from file
- Mapping file format:
  - source_value, matched_id, matched_name, confidence, status, notes
- Validation on import
- Preview before applying

**Impact:** LOW - Integration with external tools

---

## Implementation Roadmap

### Phase 1: Core Usability (2-3 weeks)
**Goal:** Make reconciliation workflow functional for production use

| Feature | Priority | Estimate | Dependencies |
|---------|----------|----------|--------------|
| 1.1 Status Filtering & Search | P1 | 3 days | None |
| 1.3 Alternative Search | P1 | 5 days | Backend suggest endpoint (exists) |
| 1.4 Mark as Unmatched | P1 | 3 days | Backend model extension |
| 2.4 Preview Matched Data | P1 | 4 days | None |

**Deliverables:**
- Users can filter and search results
- Users can manually search for alternatives
- Users can mark items as unmatched
- Users can preview final output before export

---

### Phase 2: Productivity & Quality (2 weeks)
**Goal:** Improve efficiency for large datasets

| Feature | Priority | Estimate | Dependencies |
|---------|----------|----------|--------------|
| 1.2 Batch Review Actions | P1 | 4 days | Status filtering (1.1) |
| 1.5 Notes & Documentation | P2 | 3 days | Backend model extension |
| 2.1 Progress Indicators | P2 | 3 days | WebSocket or polling setup |
| 2.2 Quality Statistics | P2 | 3 days | None |

**Deliverables:**
- Users can process multiple items at once
- Users can document decisions
- Users see progress during long operations
- Users can assess data quality metrics

---

### Phase 3: Advanced Features (2-3 weeks)
**Goal:** Support complex scenarios and integrations

| Feature | Priority | Estimate | Dependencies |
|---------|----------|----------|--------------|
| 3.4 Conflict Detection | P2 | 5 days | None |
| 2.3 Audit Log | P3 | 4 days | Backend history tracking |
| 3.1 Multi-Entity Reconciliation | P3 | 4 days | None |
| 3.5 Import/Export Mappings | P3 | 3 days | None |

**Deliverables:**
- System detects and helps resolve conflicts
- Complete audit trail of changes
- Batch processing across entities
- Integration with external workflows

---

## Detailed Implementation Specs

### 1.1 Status Filtering & Search

#### Backend Changes
**None required** - filtering can be client-side

#### Frontend Changes

**ReconciliationGrid.vue:**
```typescript
// Add filter state
const statusFilter = ref<'all' | 'auto-accepted' | 'needs-review' | 'unmatched'>('all')
const searchQuery = ref('')

// Computed filtered data
const filteredRowData = computed(() => {
  let filtered = rowData.value
  
  // Status filter
  if (statusFilter.value !== 'all') {
    filtered = filtered.filter(row => {
      if (statusFilter.value === 'auto-accepted') return row.match && row.autoAccepted
      if (statusFilter.value === 'needs-review') return row.candidates.length > 0 && !row.match
      if (statusFilter.value === 'unmatched') return row.candidates.length === 0
      return true
    })
  }
  
  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(row => 
      getRowDisplayText(row).toLowerCase().includes(query)
    )
  }
  
  return filtered
})
```

**UI Components:**
```vue
<v-toolbar>
  <v-chip-group v-model="statusFilter" mandatory>
    <v-chip value="all">All</v-chip>
    <v-chip value="auto-accepted" color="success">Auto-Accepted</v-chip>
    <v-chip value="needs-review" color="warning">Needs Review</v-chip>
    <v-chip value="unmatched" color="error">Unmatched</v-chip>
  </v-chip-group>
  
  <v-spacer />
  
  <v-text-field
    v-model="searchQuery"
    prepend-inner-icon="mdi-magnify"
    placeholder="Search queries..."
    density="compact"
    clearable
    hide-details
  />
</v-toolbar>
```

**Testing:**
- Filter by each status
- Search with partial matches
- Combine filter + search
- Clear filters

---

### 1.3 Alternative Search

#### Backend Changes
**Endpoint exists:** `GET /projects/{project_name}/reconciliation/{entity_name}/suggest`

May need enhancement for POST with multiple search terms.

#### Frontend Changes

**New Component: `AlternativeSearchDialog.vue`**

```vue
<template>
  <v-dialog v-model="show" max-width="600">
    <v-card>
      <v-card-title>Search for Alternative Match</v-card-title>
      <v-card-subtitle>Original: {{ originalQuery }}</v-card-subtitle>
      
      <v-card-text>
        <v-text-field
          v-model="searchTerm"
          label="Search for alternatives"
          prepend-inner-icon="mdi-magnify"
          autofocus
          @input="debouncedSearch"
          :loading="searching"
        />
        
        <v-list v-if="suggestions.length > 0">
          <v-list-item
            v-for="suggestion in suggestions"
            :key="suggestion.id"
            @click="selectSuggestion(suggestion)"
          >
            <template #prepend>
              <v-avatar :color="getScoreColor(suggestion.score)">
                {{ Math.round(suggestion.score * 100) }}
              </v-avatar>
            </template>
            <v-list-item-title>{{ suggestion.name }}</v-list-item-title>
            <v-list-item-subtitle>{{ suggestion.description }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
        
        <v-alert v-else-if="searched && suggestions.length === 0" type="info">
          No matches found. Try different search terms.
        </v-alert>
      </v-card-text>
      
      <v-card-actions>
        <v-spacer />
        <v-btn @click="show = false">Cancel</v-btn>
        <v-btn color="primary" :disabled="!selectedSuggestion" @click="accept">
          Accept
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { reconciliationApi } from '@/api/reconciliation'

const props = defineProps<{
  projectName: string
  entityName: string
  originalQuery: string
}>()

const emit = defineEmits<{
  accept: [candidate: ReconciliationCandidate]
}>()

const show = ref(false)
const searchTerm = ref('')
const searching = ref(false)
const searched = ref(false)
const suggestions = ref<ReconciliationCandidate[]>([])
const selectedSuggestion = ref<ReconciliationCandidate | null>(null)

const searchAlternatives = async () => {
  if (!searchTerm.value || searchTerm.value.length < 2) {
    suggestions.value = []
    return
  }
  
  searching.value = true
  try {
    suggestions.value = await reconciliationApi.suggest(
      props.projectName,
      props.entityName,
      searchTerm.value
    )
    searched.value = true
  } finally {
    searching.value = false
  }
}

const debouncedSearch = useDebounceFn(searchAlternatives, 300)

function accept() {
  if (selectedSuggestion.value) {
    emit('accept', selectedSuggestion.value)
    show.value = false
  }
}

defineExpose({ show })
</script>
```

**Integration in ReconciliationGrid:**
```vue
<!-- Add button in cell renderer -->
<v-btn size="small" @click="openAlternativeSearch(row)">
  Search Alternatives
</v-btn>

<alternative-search-dialog
  ref="searchDialog"
  :project-name="projectName"
  :entity-name="entityName"
  :original-query="selectedRow?.queryText"
  @accept="handleAlternativeAccept"
/>
```

**Testing:**
- Search with valid terms
- Search with no results
- Accept suggestion
- Cancel search
- Debounce behavior

---

### 1.4 Mark as Unmatched

#### Backend Changes

**Extend ReconciliationMapping model:**
```python
# backend/app/models/reconciliation.py
class ReconciliationMapping(BaseModel):
    """Mapping of source query to matched entity."""
    
    query_text: str
    matched_id: str | None = None
    matched_name: str | None = None
    confidence: float | None = None
    match: bool = False
    auto_accepted: bool = False
    will_not_match: bool = False  # NEW
    notes: str | None = None        # NEW (for Phase 2)
    last_modified: datetime | None = None  # NEW (for audit)
```

**New endpoint:**
```python
@router.post("/projects/{project_name}/reconciliation/{entity_name}/mark-unmatched")
async def mark_as_unmatched(
    project_name: str,
    entity_name: str,
    query_keys: list[tuple],
    notes: str | None = None,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> dict:
    """Mark one or more queries as will not match."""
    # Implementation in service
    return service.mark_unmatched(project_name, entity_name, query_keys, notes)
```

#### Frontend Changes

```vue
<!-- In ReconciliationGrid -->
<v-btn 
  size="small" 
  color="grey"
  @click="markUnmatched(row)"
>
  <v-icon start>mdi-cancel</v-icon>
  Mark Unmatched
</v-btn>

<!-- Confirmation dialog -->
<v-dialog v-model="unmatchedDialog" max-width="500">
  <v-card>
    <v-card-title>Mark as Unmatched?</v-card-title>
    <v-card-text>
      <p>This will mark the following item as "will not match":</p>
      <v-chip class="my-2">{{ selectedRow?.queryText }}</v-chip>
      
      <v-textarea
        v-model="unmatchedNotes"
        label="Notes (optional)"
        hint="Explain why this item won't be matched"
        rows="3"
      />
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn @click="unmatchedDialog = false">Cancel</v-btn>
      <v-btn color="primary" @click="confirmMarkUnmatched">Confirm</v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

**Grid styling:**
```typescript
function getRowStyle(params) {
  if (params.data.willNotMatch) {
    return { 
      backgroundColor: '#f5f5f5', 
      color: '#999',
      textDecoration: 'line-through'
    }
  }
  // ... existing logic
}
```

**Testing:**
- Mark single item as unmatched
- Add notes
- Visual indication in grid
- Persist state
- Undo unmatched marking

---

## Technical Considerations

### 1. State Management
**Challenge:** Reconciliation state is complex (mappings, candidates, filters, selections)

**Solution:**
- Create dedicated Pinia store: `useReconciliationStore()`
- Manage:
  - Current reconciliation config
  - Grid data with candidates
  - Filter/search state
  - Pending changes
  - Save status

### 2. Performance
**Challenge:** Large datasets (1000+ rows) may cause UI lag

**Solutions:**
- AG Grid already supports virtual scrolling
- Implement pagination (100 rows per page)
- Server-side filtering for very large datasets
- Lazy load candidates (only when row expanded)
- Consider web workers for heavy computations

### 3. Real-time Updates
**Challenge:** Long-running reconciliation needs progress feedback

**Solutions:**
- **Option A:** WebSocket connection for live updates
- **Option B:** Polling with exponential backoff
- **Option C:** Server-Sent Events (SSE)

**Recommendation:** Start with polling (simpler), upgrade to WebSocket if needed

### 4. Offline/Error Handling
**Challenge:** Service unavailable or network issues

**Solutions:**
- Graceful degradation (show cached results)
- Retry with exponential backoff
- Clear error messages with actionable steps
- Allow manual data entry if service down

### 5. Data Validation
**Challenge:** Prevent invalid mappings

**Solutions:**
- Validate ID format before accepting
- Check for duplicate mappings (multiple sources → same ID)
- Warn on low confidence accepts
- Validate against SEAD schema if available

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ Users can complete full reconciliation workflow without CLI
- ✅ 90% of matches can be handled without custom code
- ✅ < 5 clicks to resolve typical "needs review" item
- ✅ Zero data loss on page refresh

### Phase 2 Success Criteria
- ✅ Batch operations reduce time by 50% for large datasets
- ✅ Quality metrics help identify data issues proactively
- ✅ Progress indicators reduce user uncertainty

### Phase 3 Success Criteria
- ✅ Multi-entity reconciliation saves 80% of time vs sequential
- ✅ Audit log enables debugging of issues
- ✅ Import/export enables external review workflows

---

## Resources Required

### Development Team
- 1x Frontend Developer (Vue 3, AG Grid)
- 1x Backend Developer (Python, FastAPI)
- 0.5x UX Designer (for complex workflows)

### Timeline Estimate
- **Phase 1:** 2-3 weeks
- **Phase 2:** 2 weeks
- **Phase 3:** 2-3 weeks
- **Total:** 6-8 weeks

### Dependencies
- AG Grid Community (already in use)
- VueUse for utilities (may need to add)
- Chart.js or similar for statistics (Phase 2)

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| AG Grid performance issues | High | Medium | Implement pagination, virtual scrolling |
| Complex state management bugs | Medium | High | Comprehensive unit tests, Pinia store isolation |
| Service downtime during reconciliation | Medium | Low | Save progress frequently, allow resume |
| User confusion with workflow | High | Medium | In-app tooltips, guided tour, documentation |
| Conflicting concurrent edits | Low | Low | Optimistic locking, conflict detection UI |

---

## Next Steps

1. **Review & Prioritize:** Stakeholder review of this plan
2. **Spike Work:** Test AG Grid performance with large datasets (1000+ rows)
3. **Design Review:** UX review of Alternative Search and Batch Actions
4. **Backend API Contracts:** Finalize API changes for Phase 1
5. **Begin Phase 1:** Start with 1.1 Status Filtering (lowest risk)

---

**Document Version:** 1.0  
**Last Updated:** January 3, 2026  
**Author:** Shape Shifter Development Team
