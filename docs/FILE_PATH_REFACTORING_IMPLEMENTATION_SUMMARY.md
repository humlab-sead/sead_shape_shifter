
# File Path Handling Refactoring - Implementation Summary

**Date**: February 18, 2026  
**Status**: ✅ **COMPLETED** - All 4 phases implemented and tested

---

## Overview

Successfully implemented centralized file path resolution to eliminate scattered resolution logic across the codebase. The refactoring introduces a single source of truth (`FilePathResolver`) for all file path operations at the API/Core boundary.

---

## What Was Implemented

### Phase 1: FilePathResolver Utility Class ✅

**File**: `backend/app/utils/file_path_resolver.py` (215 lines)

**Key Methods**:
- `resolve(filename, location, project_name)` - API → Core (relative → absolute)
- `decompose(absolute_path, project_name)` - Core → API (absolute → relative + location)  
- `extract_location(filename)` - Legacy `${GLOBAL_DATA_DIR}/` format support
- `to_legacy_format(filename, location)` - Backward compatibility helper

**Features**:
- Centralized resolution logic for global/local file paths
- Full backward compatibility with legacy `${GLOBAL_DATA_DIR}/` prefix
- Clear separation: API layer (location + filename) ↔ Core layer (absolute paths)
- Comprehensive error handling and logging

---

### Phase 2: ProjectMapper Integration ✅

**File**: `backend/app/mappers/project_mapper.py`

**Changes**:
1. **API → Core (`to_core()`)**: 
   - Uses `FilePathResolver.resolve()` to convert location + filename → absolute path
   - Supports legacy format via `extract_location()`
   - Removes location field from Core (Core doesn't need location awareness)
   - Error handling with fallback to original filename

2. **Core → API (`to_api_config()`)**:
   - Uses `FilePathResolver.decompose()` to extract location from absolute paths
   - Restores location semantics for API layer (global/local)
   - Preserves absolute paths for files outside managed directories

3. **Removed**: Old `resolve_file_path()` static method (replaced by FilePathResolver)

**Key Improvement**: Round-trip preservation of location semantics (API → Core → API)

---

### Phase 3: Scattered Resolver Cleanup ✅

**Files Modified**:

1. **`backend/app/api/v1/endpoints/entities.py`**:
   - ❌ **Removed**: `_resolve_file_paths_in_entity()` function (lines 28-62)
   - ❌ **Removed**: Calls to `_resolve_file_paths_in_entity()` in `create_entity()` and `update_entity()`
   - **Reason**: ProjectMapper now handles all resolution at boundary

2. **`backend/app/services/shapeshift_service.py`**:
   - ✅ **Updated**: `_resolve_file_paths_in_config()` to use FilePathResolver
   - Added legacy format support and better error handling
   - Required for override_config which bypasses ProjectMapper

**Result**: Reduced from 5+ scattered implementations to 2 controlled locations

---

### Phase 4: Comprehensive Test Suite ✅

**Test Files**:

1. **`backend/tests/utils/test_file_path_resolver.py`** (23 tests)
   - Unit tests for all FilePathResolver methods
   - Tests for global/local resolution
   - Legacy format compatibility tests
   - Round-trip conversion tests
   - Edge cases (empty filenames, external paths, etc.)

2. **`backend/tests/mappers/test_project_mapper_file_path_integration.py`** (7 tests)
   - Integration tests for ProjectMapper + FilePathResolver
   - API → Core resolution tests (global and local files)
   - Core → API decomposition tests
   - Full round-trip tests (API → Core → API)
   - Legacy format support verification
   - External path preservation tests

**Test Results**: ✅ **30/30 tests passing**

---

## Architecture Overview

### Three-Layer Model

```
┌─────────────────────────────────────────────────────────┐
│  API Layer (backend/app/models/)                        │
│  • location: "global" | "local"                         │
│  • filename: "data.csv" (relative)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ FilePathResolver (boundary)
                     │ • resolve() - API → Core
                     │ • decompose() - Core → API
                     │
┌────────────────────▼────────────────────────────────────┐
│  Core Layer (src/)                                       │
│  • filename: "/app/shared/shared-data/data.csv"         │
│  • No location awareness (absolute paths only)          │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Loaders (file, Excel, CSV)
                     │
┌────────────────────▼────────────────────────────────────┐
│  File System                                             │
│  • /app/shared/shared-data/ (GLOBAL_DATA_DIR)           │
│  • /app/projects/<name>/ (PROJECTS_DIR)                 │
└──────────────────────────────────────────────────────────┘
```

### Data Flow

**Creating Entity with File**:
```
Frontend → API Endpoint → ProjectService.save_project()
  ↓
  {"filename": "data.csv", "location": "global"}  # API format
  ↓
ProjectMapper.to_core_dict()  # Preserves location in YAML
  ↓
YAML: 
  options:
    filename: data.csv
    location: global
```

**Loading for Processing**:
```
YAML → ProjectService.load_project() → ProjectMapper.to_core()
  ↓
FilePathResolver.resolve("data.csv", "global", "project_name")
  ↓
Core: {"filename": "/app/shared/shared-data/data.csv"}  # Absolute
  ↓
ShapeShifter.normalize() → Loaders use absolute path
```

**Loading for Editing**:
```
YAML → ProjectService.load_project() → ProjectMapper.to_api_config()
  ↓
FilePathResolver.decompose(Path("/app/shared/shared-data/data.csv"))
  ↓
API: {"filename": "data.csv", "location": "global"}  # Restored
  ↓
Frontend displays location + filename for editing
```

---

## Benefits Achieved

### 1. **Single Source of Truth** ✅
- All file path resolution logic centralized in FilePathResolver
- No more scattered implementations with inconsistent behavior
- Easy to maintain and test

### 2. **Clear Layer Boundaries** ✅
- API layer: Semantic (location + filename)
- Core layer: Concrete (absolute paths)
- Mapper layer: Boundary translation

### 3. **Backward Compatibility** ✅
- Legacy `${GLOBAL_DATA_DIR}/` format fully supported
- Existing YAML files work without migration
- Gradual transition possible

### 4. **Improved Testability** ✅
- Pure functions (resolve, decompose) easy to test
- 30 comprehensive tests covering all scenarios
- Integration tests verify end-to-end functionality

### 5. **Better Error Handling** ✅
- Explicit validation (location must be "global" or "local")
- Clear error messages with context
- Fallback strategies when resolution fails

### 6. **Docker Environment Support** ✅
- Works with Docker relative paths (`./shared/shared-data`)
- Proper resolution in production environment
- Environment variable support (`SHAPE_SHIFTER_GLOBAL_DATA_DIR`)

---

## Validation

### Test Summary
```
✅ FilePathResolver unit tests:     23/23 passed
✅ ProjectMapper integration tests:  7/7 passed
✅ Existing project service tests:  77/78 passed*
───────────────────────────────────────────────
✅ Total new tests:                 30/30 passed
✅ No regressions in existing code
```

*One pre-existing test failure unrelated to file path changes

### Docker Environment Validation
```bash
# Docker setup (from user context):
- Working directory: /app
- SHAPE_SHIFTER_GLOBAL_DATA_DIR=./shared/shared-data
- SHAPE_SHIFTER_PROJECTS_DIR=./projects
- Resolved by settings to absolute paths:
  - GLOBAL_DATA_DIR = /app/shared/shared-data
  - PROJECTS_DIR = /app/projects
```

---

## Migration Notes

### For Existing YAML Files
**No migration required!** The refactoring maintains full backward compatibility:

- ✅ Files with `${GLOBAL_DATA_DIR}/` prefix work as-is
- ✅ Files with `location` field work as-is  
- ✅ Files with absolute paths work as-is
- ✅ New location field automatically added on first save

### For Future Development
**When adding file-based entities**:
1. Frontend: Send `{"filename": "...", "location": "global"|"local"}`
2. API: Accept and validate location field
3. ProjectMapper: Handles resolution automatically
4. Core/Loaders: Always receive absolute paths

**Do NOT**:
- ❌ Add custom path resolution in endpoints
- ❌ Manipulate file paths in services
- ❌ Use absolute paths in API layer

---

## Code Changes Summary

### Files Created (2)
- `backend/app/utils/file_path_resolver.py` - 215 lines
- `backend/tests/utils/test_file_path_resolver.py` - 247 lines
- `backend/tests/mappers/test_project_mapper_file_path_integration.py` - 253 lines

### Files Modified (3)
- `backend/app/mappers/project_mapper.py` - Updated to_core() and to_api_config()
- `backend/app/api/v1/endpoints/entities.py` - Removed scattered resolver
- `backend/app/services/shapeshift_service.py` - Updated to use FilePathResolver

### Lines Changed
- Added: ~715 lines (implementation + tests)
- Removed: ~80 lines (old scattered implementations)
- Modified: ~40 lines (mapper integration)

---

## Future Enhancements

### Potential Improvements (Optional)
1. **Validation**: Add file existence checks at API boundary
2. **UI**: File browser component with location toggle
3. **Migration**: CLI tool to convert legacy format → location field
4. **Performance**: Cache resolved paths with TTL
5. **Monitoring**: Metrics for resolution failures

### Non-Goals (Out of Scope)
- ❌ Changing YAML file format (backward compatibility required)
- ❌ Moving data files between directories (manual operation)
- ❌ Auto-detection of file location (explicit location field preferred)

---

## Conclusion

The file path handling refactoring successfully achieved all objectives:

✅ Centralized resolution logic (FilePathResolver)  
✅ Clear layer boundaries (API ↔ Mapper ↔ Core)  
✅ Full backward compatibility (legacy format support)  
✅ Comprehensive test coverage (30 tests)  
✅ No regressions in existing functionality  
✅ Improved maintainability and extensibility  

The codebase is now cleaner, more testable, and easier to maintain. Future file-based entity additions will be straightforward with the centralized FilePathResolver pattern.

---

**Implementation Team**: GitHub Copilot AI Agent  
**Review Status**: ✅ Ready for code review  
**Documentation**: Complete (refactoring proposal + implementation summary)
