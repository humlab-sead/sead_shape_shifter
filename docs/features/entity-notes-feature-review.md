# Entity Notes Feature Review
**Date**: March 12, 2026  
**Reviewer**: GitHub Copilot  
**Branch**: dev  
**Feature Status**: Uncommitted changes

## Feature Description

The Entity Notes feature adds the ability for users to attach simple multiline text notes to individual entities within a Shape Shifter project. These notes are persisted independently from the main project configuration file in a sidecar YAML file (`shapeshifter.tasks.yml`), allowing users to document context, track issues, or remind themselves of entity-specific concerns without modifying the project structure.

### Key Capabilities
- **Add/Edit Notes**: Users can create or update multiline text notes for any entity
- **View Notes**: Notes are loaded and displayed through the UI
- **Remove Notes**: Notes can be explicitly deleted or auto-removed when set to empty/whitespace
- **Visual Indicators**: Entities with notes display a visual indicator (dot overlay) in the dependency graph
- **Sidecar Persistence**: Notes are stored alongside task list state in `shapeshifter.tasks.yml`

### User Experience Flow
1. Right-click on an entity node in the dependency graph
2. Select "Add Note" or "Edit Note" from the context menu
3. Enter multiline text in a modal dialog
4. Save to persist the note
5. The entity node displays a small dot indicator showing it has a note
6. Notes can be removed via context menu or by saving an empty note

## Implementation Review

### Backend Architecture

#### Data Model (`backend/app/models/task.py`)
- **`TaskNoteRequest`**: Request body containing note text
- **`TaskNoteResponse`**: Response with success status, entity name, note text, has_note flag, and optional message
- **`EntityTaskStatus`**: Extended with `has_note: bool` field to expose note status in task summaries

#### API Endpoints (`backend/app/api/v1/endpoints/tasks.py`)
Three RESTful endpoints following standard HTTP semantics:
- `GET /projects/{name}/tasks/{entity_name}/note` - Retrieve current note
- `PUT /projects/{name}/tasks/{entity_name}/note` - Create or update note
- `DELETE /projects/{name}/tasks/{entity_name}/note` - Remove note

All endpoints:
- Use consistent `TaskNoteResponse` model
- Apply `@handle_endpoint_errors` decorator for error handling
- Include structured logging
- Follow existing project conventions

#### Service Layer (`backend/app/services/task_service.py`)
Three service methods mirror the API endpoints:
- `get_note(project_name, entity_name)` - Delegates to sidecar manager
- `set_note(project_name, entity_name, note)` - Persists note via sidecar manager
- `remove_note(project_name, entity_name)` - Removes note via sidecar manager

**Integration with Task Status**:
- `compute_status()` method enhanced to load note entities from sidecar
- Note entities included in `all_entity_names` set to ensure entities with notes appear in task lists
- `_compute_entity_status()` receives `note_entities` set and marks `has_note` in `EntityTaskStatus`

#### Persistence Layer (`backend/app/services/task_list_sidecar_manager.py`)
Significant refactoring to support dual-purpose sidecar file:

**Core Methods**:
- `load_sidecar_data()` - Unified loader returning dict with `task_list` and `notes` sections
- `load_notes()` - Public method returning entity→note mapping
- `get_note(project_file_path, entity_name)` - Retrieve specific entity note
- `set_note(project_file_path, entity_name, note)` - Persist or remove note (if empty)
- `remove_note(project_file_path, entity_name)` - Explicitly delete note

**Normalization & Backwards Compatibility**:
- `_normalize_notes_data()` - Validates note data structure, strips trailing whitespace
- Supports both legacy (flat task state at root) and modern (structured sections) sidecar formats
- Opportunistic normalization on read with auto-rewrite for consistency
- Preserves existing sections when updating (notes don't overwrite task_list and vice versa)

**Key Design Decisions**:
1. **Empty note removal**: Whitespace-only notes are automatically removed instead of persisted
2. **Section preservation**: When saving task_list, existing notes are preserved (and vice versa)
3. **Multiline formatting**: Notes are stored using YAML literal block scalar (`|`) for readability
4. **Atomic operations**: Each note operation loads, modifies, and saves the entire sidecar

### Frontend Architecture

#### API Client (`frontend/src/api/tasks.ts`)
- `TaskNoteResponse` interface matches backend model
- Three async methods: `getNote()`, `setNote()`, `removeNote()`
- Uses standard `apiClient` with proper REST endpoints

#### UI Components

**ProjectDetailView (`frontend/src/views/ProjectDetailView.vue`)**:
- Modal dialog (`v-dialog`) for note editing with:
  - Title showing entity name
  - Multiline textarea (`v-textarea`) with auto-grow
  - Loading and saving states
  - Error display
  - Hint text explaining empty-save removes note
- Three handler methods:
  - `handleEditNote()` - Opens dialog and loads existing note
  - `handleRemoveNote()` - Removes note and refreshes UI
  - `handleSaveNote()` - Persists note and updates task status
- Task status refresh after note operations to update visual indicators
- Added "Has note" legend item in the graph legend

**GraphNodeContextMenu (`frontend/src/components/dependencies/GraphNodeContextMenu.vue`)**:
- "Add Note" / "Edit Note" menu item (label changes based on `has_note` status)
- "Remove Note" menu item (disabled when no note exists)
- Emits `edit-note` and `remove-note` events to parent
- Tooltip explains note functionality

#### Visual Indicators (`frontend/src/config/cytoscapeStyles.ts`)
- `task-has-note` CSS class for nodes
- SVG data URI rendering a white circle with dark border
- Positioned at node center as overlay indicator
- 24% size relative to node (subtle but visible)

#### Graph Integration
- `applyTaskStatusToNodes()` enhanced to apply `task-has-note` class
- Node classes cleaned before reapplying to ensure proper state
- Color-by-task mode respects note indicators

### Test Coverage

#### Backend Tests

**Sidecar Manager Tests** (`backend/tests/services/test_task_list_sidecar_manager.py`):
- ✅ `test_save_task_list_preserves_existing_notes` - Notes survive task list updates
- ✅ `test_load_notes_returns_note_mapping` - Notes load independently of task_list
- ✅ `test_set_note_persists_multiline_note` - Multiline notes stored correctly with YAML literal blocks
- ✅ `test_set_note_removes_blank_note` - Whitespace-only notes are removed
- ✅ `test_remove_note_deletes_notes_section_when_empty` - Empty notes section cleanup

**Task Service Tests** (`backend/tests/services/test_task_service.py`):
- ✅ `test_compute_status_marks_entities_with_notes` - `has_note` flag propagates to task status
- ✅ `test_get_note_returns_existing_note` - Service correctly retrieves notes
- ✅ `test_set_note_persists_note` - Service delegates to sidecar manager
- ✅ `test_remove_note_clears_note` - Service handles note removal

**Coverage Assessment**:
- Core persistence logic well-tested
- Service delegation tested
- Error paths not explicitly tested (rely on existing error handling)
- No frontend tests included (UI validation manual)

## Architecture Analysis

### Strengths

1. **Separation of Concerns**
   - Notes stored in sidecar file, not polluting main project configuration
   - Clear layering: API → Service → Persistence
   - Sidecar manager handles all file I/O complexity

2. **Data Integrity**
   - Normalization ensures consistent sidecar format
   - Atomic read-modify-write operations prevent corruption
   - Empty notes automatically cleaned up

3. **User Experience**
   - Simple, intuitive UI with visual indicators
   - Context menu integration feels natural
   - Multiline support adequate for note-taking use case

4. **Backwards Compatibility**
   - Supports legacy flat sidecar format
   - Opportunistic normalization maintains consistency
   - Existing projects without notes continue to work

5. **RESTful API Design**
   - Standard HTTP methods (GET/PUT/DELETE)
   - Consistent response models
   - Proper endpoint naming

6. **Test Coverage**
   - Core persistence logic comprehensively tested
   - Edge cases covered (empty notes, multiline, section preservation)
   - Mocking strategy appropriate for unit tests

### Design Considerations

1. **Sidecar File Structure**
   - YAML structure is flat: `{task_list: {...}, notes: {...}}`
   - Simple and effective for current needs
   - Future: Could support note metadata (created_at, author) if needed

2. **File I/O Pattern**
   - Each note operation reads, modifies, and writes entire sidecar
   - Acceptable for current scale (small files, infrequent updates)
   - Could become bottleneck if notes grow very large or updates are frequent

3. **Concurrency**
   - No explicit file locking mechanism
   - Last-write-wins behavior
   - Acceptable for single-user desktop application
   - Would need addressing for multi-user server deployment

4. **Note Text Constraints**
   - No maximum length enforced
   - No format validation (could contain anything)
   - Frontend textarea auto-grows (could be issue for very large notes)

5. **Visual Indicator**
   - Small dot overlay is subtle
   - May not be discoverable for new users
   - No indication of note content from graph view

### Potential Improvements

#### High Priority
1. **Frontend Tests**: Add Vitest/Playwright tests for dialog interaction and note operations
2. **API Error Messages**: Enhance error responses with specific failure reasons
3. **Note Preview**: Show note content in tooltip on hover over entity node
4. **Undo/Redo**: Consider supporting undo for note changes

#### Medium Priority
5. **Note Search**: Allow searching entities by note content
6. **Note History**: Track note changes over time (version history)
7. **Note Export**: Include notes in project export/reporting
8. **Character Limit**: Consider soft/hard limits on note length with UI feedback

#### Low Priority
9. **Rich Text**: Support basic markdown formatting in notes
10. **Note Categories**: Allow tagging notes (e.g., "blocker", "question", "resolved")
11. **File Locking**: Implement proper file locking for concurrent access safety
12. **Bulk Operations**: Add/remove notes for multiple entities at once

### Integration Points

The feature integrates cleanly with existing systems:
- ✅ Task status system (has_note flag)
- ✅ Dependency graph (visual indicators)
- ✅ Context menu actions
- ✅ Sidecar file management (shares infrastructure with task_list)
- ⚠️ Not integrated with validation system (notes not validated or reported in validation results)
- ⚠️ Not integrated with search (can't search by note content)
- ⚠️ Not integrated with export (notes not included in exported data)

## Code Quality Assessment

### Positive Aspects
- **Consistent naming**: Methods, variables, and types follow project conventions
- **Type safety**: Full TypeScript types on frontend, Pydantic models on backend
- **Documentation**: Docstrings explain purpose and behavior
- **Logging**: Appropriate debug/info logging for troubleshooting
- **Error handling**: Uses existing error handling infrastructure

### Minor Issues
1. **Error messages**: Generic error messages in frontend handlers could be more specific
2. **Duplication**: Some normalization logic could be further extracted
3. **Constants**: Magic strings ("notes", "task_list") could be constants
4. **Async consistency**: Service methods are async but don't await anything (could be sync)

### Style & Conventions
- ✅ Follows existing code patterns
- ✅ Uses project's error handling decorators
- ✅ Adheres to linting rules (pylint, black, isort)
- ✅ Matches existing UI component structure

## Risk Assessment

### Low Risk
- Feature is self-contained and isolated
- Uses existing proven sidecar file infrastructure
- No changes to core processing pipeline
- No database schema changes
- Backwards compatible

### Medium Risk
- File I/O without explicit locking (acceptable for current use case)
- No frontend test coverage (manual testing required)
- Visual indicator may not be immediately discoverable

### No Identified High Risks

## Deployment Considerations

1. **Database Migration**: None required (file-based storage)
2. **API Versioning**: No breaking changes to existing endpoints
3. **Frontend Build**: Standard build process, no special requirements
4. **Documentation**: User guide should explain note feature
5. **Release Notes**: Feature should be documented in CHANGELOG

## Summary

### Overview
The Entity Notes feature is a **well-implemented, self-contained addition** that adds valuable user functionality without disrupting existing architecture. The implementation demonstrates good software engineering practices with clear separation of concerns, appropriate abstraction layers, and reasonable test coverage.

### Strengths Summary
- ✅ Clean architecture following project patterns
- ✅ RESTful API design
- ✅ Solid test coverage for backend
- ✅ User-friendly UI integration
- ✅ Backwards compatible
- ✅ Low risk implementation

### Areas for Enhancement
- ⚠️ Add frontend test coverage
- ⚠️ Enhance note discoverability (preview on hover)
- ⚠️ Consider note search functionality
- ⚠️ Document feature in user guide

### Recommendation
**Approved for merge** with recommendation to add:
1. Frontend tests before release
2. User documentation
3. Release notes entry

The feature is production-ready from a backend perspective and provides immediate value to users. The identified improvements are enhancements rather than blockers.

### Metrics
- **Files Changed**: 14
- **Lines Added**: ~565
- **Lines Removed**: ~28
- **Backend Tests Added**: 8
- **Frontend Tests Added**: 0
- **API Endpoints Added**: 3
- **New UI Components**: 1 dialog, 2 context menu items, 1 legend item

### Next Steps
1. Add frontend test suite (Vitest for unit, Playwright for E2E)
2. Update user documentation (USER_GUIDE.md)
3. Add feature to CHANGELOG.md
4. Consider adding note preview on hover (quick win for discoverability)
5. Merge to dev branch
6. Include in next release

---
*Generated by code review on March 12, 2026*
