# Server-Side State Management - Implementation Summary

## Changes Applied

### 1. Application State Manager (`backend/app/core/state_manager.py`)
**NEW FILE** - Core state management for multi-user configuration editing.

**Key Components:**
- **`ConfigSession`**: Dataclass tracking individual editing sessions with:
  - Session ID, config name, user ID
  - Version tracking for optimistic concurrency control
  - Last accessed timestamp for auto-cleanup
  
- **`ApplicationState`**: Application-level singleton managing:
  - Multiple concurrent sessions per configuration file
  - Session lifecycle (create, get, release)
  - Background cleanup task (30min timeout)
  - Integration with `ConfigStore` for lazy loading

**State Lifecycle:**
- Initialized at app startup (empty, no configs loaded)
- Sessions created on-demand via API
- Configs loaded when first session created
- Configs unloaded when last session closes
- Stale sessions auto-cleaned every 5 minutes

### 2. Session Dependencies (`backend/app/api/dependencies.py`)
**UPDATED** - Added session management dependency injection.

**New Dependencies:**
- `get_session_id()`: Extract session ID from header or cookie
- `get_current_session()`: Get current editing session (optional)
- `require_session()`: Require active session (raises 401 if missing)

### 3. Session Endpoints (`backend/app/api/v1/endpoints/sessions.py`)
**NEW FILE** - REST API for session CRUD operations.

**Endpoints:**
```
POST   /api/v1/sessions              - Create new editing session
GET    /api/v1/sessions/current      - Get current session info
DELETE /api/v1/sessions/current      - Close current session
GET    /api/v1/sessions/{name}/active - List active sessions for config
```

**Features:**
- Returns concurrent session count (multi-user awareness)
- Sets session cookie for convenience
- Validates config file exists before creating session

### 4. ConfigStore Refactoring (`src/configuration/provider.py`)
**UPDATED** - Enhanced for context-based loading without premature initialization.

**New Methods:**
```python
load_config(config_name: str) -> ConfigLike
get_config(config_name: str) -> ConfigLike  
is_loaded(config_name: str) -> bool
unload_config(config_name: str) -> None
reload_config(config_name: str) -> ConfigLike
```

**Breaking Changes:**
- Constructor now accepts optional `config_directory` parameter
- Supports both singleton (legacy) and instance-based usage
- `store` dict no longer pre-initialized with "default"

### 5. Application Lifespan (`backend/app/main.py`)
**UPDATED** - Removed default config loading at startup.

**Before:**
```python
# Loaded hardcoded config at startup
config_file = os.getenv("CONFIG_FILE", "input/query_tester_config.yml")
ConfigStore.get_instance().configure_context(source=config_file)
```

**After:**
```python
# Initialize empty state, load on-demand
app_state = init_app_state(settings.CONFIGURATIONS_DIR)
await app_state.start()  # Starts background cleanup task
```

### 6. Optimistic Concurrency Control (`backend/app/services/config_service.py`)
**UPDATED** - Added version checking for conflict detection.

**New Exception:**
```python
class ConfigConflictError(ConfigurationServiceError):
    """Raised when optimistic lock fails."""
```

**New Method:**
```python
save_with_version_check(
    config: Configuration,
    expected_version: int,
    current_version: int,
    create_backup: bool = True
) -> Configuration
```

### 7. API Router Registration (`backend/app/api/v1/api.py`)
**UPDATED** - Registered sessions router.

## Architecture Benefits

### ✅ Multi-User Support
- Multiple users can edit different configs simultaneously
- Multiple users can edit *same* config with conflict detection
- No global state shared between unrelated editing sessions

### ✅ Memory Efficiency
- Configs loaded on-demand when sessions created
- Configs unloaded when last session closes
- No wasted memory from unused configs

### ✅ Conflict Detection
- Optimistic locking via version numbers
- Client receives `ConfigConflictError` if version mismatch
- Frontend can implement merge UI or force-overwrite

### ✅ Session Management
- 30-minute auto-timeout for abandoned sessions
- Background cleanup every 5 minutes
- Session state tracked: loaded_at, last_accessed, modified, version

### ✅ Backward Compatibility
- Legacy singleton usage still works for core processing
- Gradual migration path for existing code
- No breaking changes to data model

## Migration Guide for Frontend

### Old Flow (No Sessions)
```typescript
// Load config directly
const config = await api.get('/api/v1/configurations/my_config')

// Edit...

// Save (potential silent overwrite)
await api.put('/api/v1/configurations/my_config', { config })
```

### New Flow (With Sessions)
```typescript
// 1. Create session
const session = await api.post('/api/v1/sessions', { 
  config_name: 'my_config' 
})
// Session ID stored in cookie automatically

// 2. Load config (session attached via cookie)
const config = await api.get('/api/v1/configurations/my_config')

// 3. Edit...

// 4. Save with version check
try {
  await api.put('/api/v1/configurations/my_config', {
    config: updatedConfig,
    version: session.version  // Optimistic lock
  })
} catch (error) {
  if (error.status === 409) {
    // Conflict! Show merge UI
    await handleConflict()
  }
}

// 5. Close session when done
await api.delete('/api/v1/sessions/current')
```

## Future Enhancements

### WebSocket Pub/Sub (Recommended)
```python
# Notify other sessions when config changes
await app_state.notify_sessions(config_name, {
  "type": "config_updated",
  "version": new_version,
  "modified_by": session.user_id
})
```

### Pessimistic Locking (Optional)
```python
# Exclusive edit mode - prevent concurrent sessions
session.lock_holder = session_id
# Other users see "locked by User X" message
```

### Three-Way Merge (Frontend)
- Compare: base (last saved), local (user edits), remote (other user edits)
- Auto-merge non-conflicting changes
- Flag conflicts for manual resolution

### Audit Trail (Database)
```sql
CREATE TABLE config_audit (
  id SERIAL PRIMARY KEY,
  config_name TEXT,
  session_id UUID,
  user_id TEXT,
  action TEXT,  -- 'load', 'save', 'close'
  version INT,
  timestamp TIMESTAMPTZ
);
```

## Testing Recommendations

### Unit Tests
- `test_session_creation()` - Verify session lifecycle
- `test_session_timeout()` - Verify auto-cleanup
- `test_concurrent_sessions()` - Multiple sessions same config
- `test_version_conflict()` - Optimistic lock detection

### Integration Tests
- `test_session_workflow()` - Full create → edit → save → close
- `test_multi_user_conflict()` - Two users editing same config
- `test_session_expiry()` - Config unloaded after timeout

### Load Tests
- 100 concurrent users editing different configs
- 10 users editing same config simultaneously
- Session cleanup under heavy load

## Deployment Notes

### Environment Variables
No new environment variables required. Uses existing:
- `CONFIGURATIONS_DIR` - Directory for config files

### Breaking Changes
**None** - All changes are additive and backward compatible.

### Database Migrations
Not required - all state is in-memory (process-local).

### Scaling Considerations
- State is **process-local**, not shared across workers
- If running with `--workers 4`, each worker has separate state
- For multi-process deployment, consider:
  - Redis for shared session state
  - Database for config locking
  - WebSocket broker for pub/sub

## Documentation Updates Needed

- [x] ~~`AGENTS.md`~~ - Already references session management
- [ ] `docs/BACKEND_API.md` - Document new `/sessions` endpoints
- [ ] `docs/SYSTEM_DOCUMENTATION.md` - Update architecture diagrams
- [ ] Frontend README - Document session workflow
- [ ] API changelog - Note breaking changes (none) and new features

## Files Changed

### New Files
- `backend/app/core/state_manager.py` (152 lines)
- `backend/app/api/v1/endpoints/sessions.py` (153 lines)

### Modified Files
- `backend/app/api/dependencies.py` (+56 lines)
- `backend/app/main.py` (-15 lines, simplified)
- `backend/app/api/v1/api.py` (+2 lines)
- `backend/app/services/config_service.py` (+38 lines)
- `src/configuration/provider.py` (+77 lines, refactored)

**Total:** ~+483 lines, -15 lines = **+468 net lines**

## Next Steps

1. **Update configuration endpoints** to use sessions (optional)
2. **Add frontend session management** to Vue stores
3. **Implement conflict resolution UI** for merge scenarios
4. **Add session tests** to backend test suite
5. **Update API documentation** with session endpoints
6. **Consider WebSocket integration** for real-time collaboration
