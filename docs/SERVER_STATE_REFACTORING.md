# Server State Management Refactoring

## Summary

Refactored backend architecture to eliminate ConfigStore confusion and implement clean separation between editing state (API) and execution state (Core).

## Changes Implemented

### 1. ApplicationState Refactoring ([backend/app/core/state_manager.py](backend/app/core/state_manager.py))

**Before:** Used `ConfigStore` singleton for both editing and execution
**After:** Simple `dict[str, Configuration]` for editing sessions

**Key Changes:**
- Removed `ConfigStore` dependency
- Added `_active_configs: dict[str, Configuration]` for editing state
- Added `_config_versions: dict[str, int]` for cache invalidation
- Added `_config_dirty: dict[str, bool]` for unsaved change tracking
- New methods:
  - `get_active_configuration()` - Get current editing session
  - `get_configuration(name)` - Get specific config from active sessions
  - `set_active_configuration(config)` - Update editing state + increment version
  - `mark_saved(name)` - Clear dirty flag after save
  - `is_dirty(name)` - Check for unsaved changes (prevents reconciliation)
  - `get_version(name)` - Get version for cache invalidation

### 2. ConfigMapper ([backend/app/mappers/config_mapper.py](backend/app/mappers/config_mapper.py))

**New bidirectional mapper between API and Core representations:**

- `to_api_config(cfg_dict, name)` - Core dict → API `Configuration`
- `to_core_dict(api_config)` - API `Configuration` → Core dict
- `_dict_to_api_entity()` - Entity conversion (sparse structure)
- `_api_entity_to_dict()` - Entity conversion (sparse structure)

**Key Feature:** Preserves sparse YAML structure - only includes non-None/non-empty fields

### 3. ConfigurationService Updates ([backend/app/services/config_service.py](backend/app/services/config_service.py))

**`load_configuration(name)`:**
- Checks `ApplicationState` first for active configs (editing session)
- Falls back to disk if not active
- Uses `ConfigMapper.to_api_config()` for conversion

**`save_configuration(config)`:**
- Converts via `ConfigMapper.to_core_dict()` (sparse structure)
- Auto-updates `ApplicationState` if config is active
- Marks as saved (clear dirty flag)

**`activate_configuration(name)`:**
- Loads config into `ApplicationState` as active editing session
- No more `ConfigStore` usage
- Returns API `Configuration`

**`save_with_version_check()`:**
- Uses `ApplicationState.get_version()` for optimistic locking
- Simplified signature (no manual version passing)

### 4. PreviewService with ShapeShiftConfig Caching ([backend/app/services/preview_service.py](backend/app/services/preview_service.py))

**New Caching Strategy:**
- `_shapeshift_cache: dict[str, ShapeShiftConfig]` - Cached core configs
- `_shapeshift_versions: dict[str, int]` - Version tracking per config

**`_get_shapeshift_config(config_name)`:**
- Checks `ApplicationState` version vs cached version
- Cache hit → Returns cached `ShapeShiftConfig` (fast!)
- Cache miss/stale → Converts from API `Configuration` via `ConfigMapper`
- Fallback → Loads from disk if not in active session

**Performance Benefit:**
- REPL editing: Only converts changed entity, reuses cached `ShapeShiftConfig`
- Version-based invalidation ensures fresh data after edits

### 5. Reconciliation Router ([backend/app/api/v1/api.py](backend/app/api/v1/api.py))

- Re-enabled reconciliation router registration
- Ready for three-tier reconciliation architecture (future PR)

## Architecture Flow

### Editing Flow (REPL)
```
1. User opens config → activate_configuration(name)
   ↓
2. Loads from disk → ApplicationState (version=0, dirty=false)
   ↓
3. User edits entity → update_entity()
   ↓
4. set_active_configuration(config) → version++ → dirty=true
   ↓
5. Preview request → _get_shapeshift_config()
   ↓
6. Version check → Cache VALID → Fast preview
   ↓
7. User saves → save_configuration()
   ↓
8. Writes to disk → Updates ApplicationState → mark_saved() → dirty=false
```

### Preview Performance
```
Configuration edit:
├─ First preview: Convert full config → Cache ShapeShiftConfig
├─ Entity edit: version++ 
├─ Second preview: Version mismatch → Re-convert (cheap)
└─ Third preview (same entity): Version match → Cache hit (instant)
```

### Reconciliation Guard
```
Start reconciliation:
├─ Check app_state.is_dirty(config_name)
├─ If dirty → Error: "Save changes first"
├─ If clean → Load fresh ShapeShiftConfig from disk (read-only)
└─ Proceed with reconciliation workflow
```

## Benefits

1. **Semantic Clarity:**
   - `ApplicationState` = Editing sessions (API models)
   - `ShapeShiftConfig` = Execution (Core models)
   - No more `Config`/`ConfigStore` confusion

2. **Performance:**
   - ShapeShiftConfig caching with version tracking
   - REPL: Fast previews after initial load
   - Only re-converts on actual changes

3. **Safety:**
   - Version-based cache invalidation
   - Dirty tracking prevents stale data issues
   - Optimistic locking for concurrent edits

4. **Simplicity:**
   - No singleton ConfigStore management
   - Simple `dict` for editing state
   - Clear boundaries: API ↔ Mapper ↔ Core

## Migration Notes

**Breaking Changes:**
- `ConfigStore` no longer used in backend services
- Preview/Query/Reconciliation services now use `ApplicationState` → `ShapeShiftConfig`
- Removed `ConfigFactory` dependency from ConfigurationService

**Backward Compatibility:**
- YAML structure unchanged (sparse format preserved)
- API endpoints unchanged
- Configuration model schema unchanged

## Testing

**Updated Tests Required:**
- `test_config_service.py` - ApplicationState integration
- `test_preview_service.py` - ShapeShiftConfig caching
- `test_state_manager.py` - New methods

**New Tests:**
- `test_config_mapper.py` - Bidirectional conversion
- `test_cache_invalidation.py` - Version tracking

## Future Work

1. **Reconciliation Three-Tier Architecture:**
   - Specs: Read-only, reusable YAML
   - Mappings: Separate YAML per config
   - Guard: Prevent reconciliation if config dirty

2. **Entity-Level Incremental Updates:**
   - Optimize ShapeShiftConfig updates for single entity
   - Avoid full config re-conversion in REPL

3. **Session Management:**
   - WebSocket for live collaboration
   - Conflict resolution UI
   - Real-time dirty state broadcast
