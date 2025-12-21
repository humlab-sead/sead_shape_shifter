# Frontend Session Management - Implementation Guide

## Overview

The frontend now supports multi-user configuration editing with session management, optimistic concurrency control, and real-time concurrent editor detection.

## Files Added

### 1. Types (`frontend/src/types/session.ts`)
```typescript
export interface SessionCreateRequest {
  config_name: string
  user_id?: string | null
}

export interface SessionResponse {
  session_id: string
  config_name: string
  user_id: string | null
  loaded_at: string
  last_accessed: string
  modified: boolean
  version: number
  concurrent_sessions: number
}
```

### 2. API Client (`frontend/src/api/sessions.ts`)
```typescript
import { sessionsApi } from '@/api/sessions'

// Create session
const session = await sessionsApi.create({ config_name: 'my_config' })

// Get current session
const current = await sessionsApi.getCurrent()

// Close session
await sessionsApi.close()

// List active sessions
const active = await sessionsApi.listActive('my_config')
```

### 3. Pinia Store (`frontend/src/stores/session.ts`)
```typescript
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()

// Create session
await sessionStore.createSession({ config_name: 'my_config' })

// Access state
sessionStore.hasActiveSession // boolean
sessionStore.version // number
sessionStore.isModified // boolean
sessionStore.hasConcurrentEdits // boolean

// Actions
sessionStore.markModified()
sessionStore.incrementVersion()
sessionStore.refreshActiveSessions()
await sessionStore.closeSession()

// Auto-refresh
sessionStore.startAutoRefresh(30000) // 30 seconds
sessionStore.stopAutoRefresh()
```

### 4. Composable (`frontend/src/composables/useSession.ts`)
High-level composable for components:
```typescript
import { useSession } from '@/composables'

const {
  hasActiveSession,
  version,
  isModified,
  hasConcurrentEdits,
  concurrentEditWarning,
  startSession,
  endSession,
  saveWithVersionCheck,
  markAsModified,
} = useSession()

// Start session
await startSession('my_config')

// Save with conflict detection
await saveWithVersionCheck()

// Watch for changes
watchConfigChanges(() => {
  console.log('Config changed')
})

// Cleanup
onUnmounted(() => {
  if (hasActiveSession.value) {
    await endSession()
  }
})
```

### 5. Updated Configuration Store
The configuration store now integrates with sessions:
```typescript
import { useConfigurationStore } from '@/stores/configuration'

const configStore = useConfigurationStore()

// Save (session-aware)
await configStore.saveConfiguration()
// Automatically includes version if session active
// Increments session version on success
// Throws 409 error on conflict

// Mark as changed
configStore.markAsChanged()
// Also marks session as modified
```

### 6. Demo Component (`frontend/src/components/SessionManager.vue`)
Complete example showing:
- Session lifecycle management
- Concurrent edit warnings
- Save with version checking
- Conflict resolution prompts
- Auto-cleanup on unmount

## Usage Examples

### Basic Component Integration

```vue
<template>
  <v-container>
    <v-alert v-if="concurrentEditWarning" type="warning">
      {{ concurrentEditWarning }}
    </v-alert>

    <v-btn 
      :disabled="!isModified" 
      @click="handleSave"
    >
      Save
    </v-btn>

    <!-- Your config editor -->
    <ConfigEditor v-model="config" />
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useSession } from '@/composables'
import { useConfigurationStore } from '@/stores'

const props = defineProps<{ configName: string }>()

const configStore = useConfigurationStore()
const {
  hasActiveSession,
  isModified,
  concurrentEditWarning,
  startSession,
  endSession,
  saveWithVersionCheck,
  watchConfigChanges,
} = useSession()

onMounted(async () => {
  // Start session
  await startSession(props.configName)
  
  // Load config
  await configStore.selectConfiguration(props.configName)
  
  // Watch for changes
  watchConfigChanges()
})

onUnmounted(async () => {
  if (hasActiveSession.value && isModified.value) {
    const shouldSave = confirm('Save changes?')
    if (shouldSave) {
      await handleSave()
    }
  }
  await endSession()
})

async function handleSave() {
  try {
    await saveWithVersionCheck()
  } catch (err: any) {
    if (err.message.includes('modified by another user')) {
      // Handle conflict
      alert('Conflict detected! Please reload and merge changes.')
    }
  }
}
</script>
```

### View-Level Integration

```vue
<template>
  <SessionManager>
    <!-- Your config editing views -->
    <router-view />
  </SessionManager>
</template>

<script setup lang="ts">
import SessionManager from '@/components/SessionManager.vue'
</script>
```

### Router Guard for Sessions

```typescript
// router/index.ts
import { useSessionStore } from '@/stores/session'

router.beforeEach((to, from, next) => {
  const sessionStore = useSessionStore()
  
  if (to.meta.requiresSession && !sessionStore.hasActiveSession) {
    // Redirect to session creation
    next({ name: 'SelectConfig' })
  } else {
    next()
  }
})

router.beforeRouteLeave((to, from, next) => {
  const sessionStore = useSessionStore()
  
  if (sessionStore.isModified) {
    const answer = window.confirm('You have unsaved changes. Leave anyway?')
    if (answer) {
      sessionStore.closeSession()
      next()
    } else {
      next(false)
    }
  } else {
    next()
  }
})
```

## Key Features

### 1. Optimistic Concurrency Control
```typescript
// Version is automatically included in save requests
await configStore.saveConfiguration()

// On conflict (409 error):
// - Error message shown
// - User prompted to reload or merge
// - Session version NOT incremented
```

### 2. Concurrent Editor Detection
```typescript
// Check for other editors
const { hasConcurrent, count, sessions } = checkConcurrentEditors()

// Auto-refresh every 30 seconds
sessionStore.startAutoRefresh(30000)

// Warning message
if (concurrentEditWarning.value) {
  // "2 other users are currently editing this configuration"
}
```

### 3. Session Lifecycle
```typescript
// Create → Load → Edit → Save → Close
await startSession('my_config')           // 1. Create
await configStore.selectConfiguration()   // 2. Load
configStore.markAsChanged()               // 3. Edit
await saveWithVersionCheck()              // 4. Save
await endSession()                        // 5. Close
```

### 4. Auto-Cleanup
```typescript
// Component cleanup
onUnmounted(() => {
  sessionStore.stopAutoRefresh()
})

// Server-side timeout: 30 minutes
// Auto-refresh interval: 30 seconds (extends timeout)
```

## API Changes

### Updated Configuration Store Methods

**`saveConfiguration()`**
- Now session-aware
- Includes `version` in request if session active
- Increments session version on success
- Throws descriptive error on 409 conflict

**`markAsChanged()`**
- Marks both config and session as modified
- Triggers auto-save prompts

### New API Client Configuration

**Cookie Support Enabled**
```typescript
// frontend/src/api/client.ts
withCredentials: true // Session cookies work
```

## Error Handling

### Version Conflict (409)
```typescript
try {
  await saveWithVersionCheck()
} catch (err: any) {
  if (err?.response?.status === 409) {
    // Conflict detected
    const serverVersion = err.response.data?.current_version
    
    // Options:
    // 1. Reload and lose changes
    // 2. Force overwrite (if supported)
    // 3. Show merge UI (future)
  }
}
```

### Session Expired (404)
```typescript
try {
  await sessionStore.refreshSession()
} catch (err: any) {
  if (err?.response?.status === 404) {
    // Session expired (30min timeout)
    sessionStore.currentSession = null
    // Redirect to session creation
  }
}
```

## Testing Recommendations

### Unit Tests
```typescript
// stores/session.spec.ts
describe('SessionStore', () => {
  it('creates session and stores state', async () => {
    const store = useSessionStore()
    await store.createSession({ config_name: 'test' })
    expect(store.hasActiveSession).toBe(true)
  })

  it('marks as modified', () => {
    const store = useSessionStore()
    store.markModified()
    expect(store.isModified).toBe(true)
  })

  it('increments version on save', () => {
    const store = useSessionStore()
    const oldVersion = store.version
    store.incrementVersion()
    expect(store.version).toBe(oldVersion + 1)
  })
})
```

### Integration Tests
```typescript
// composables/useSession.spec.ts
it('saves with version check', async () => {
  const { saveWithVersionCheck } = useSession()
  
  await expect(saveWithVersionCheck()).resolves.toBe(true)
})

it('throws on version conflict', async () => {
  // Mock 409 response
  vi.spyOn(api.configurations, 'update').mockRejectedValue({
    response: { status: 409, data: { current_version: 5 } }
  })
  
  const { saveWithVersionCheck } = useSession()
  
  await expect(saveWithVersionCheck()).rejects.toThrow('modified by another user')
})
```

### E2E Tests
```typescript
// e2e/session.spec.ts
it('creates session, edits, and saves', async () => {
  await page.goto('/configurations')
  await page.click('text=my_config')
  
  // Session created
  await expect(page.locator('[data-testid=session-status]')).toBeVisible()
  
  // Edit
  await page.fill('[data-testid=entity-name]', 'new_value')
  
  // Save
  await page.click('text=Save')
  await expect(page.locator('text=Saved successfully')).toBeVisible()
})
```

## Migration Guide

### Existing Components

**Before:**
```vue
<script setup lang="ts">
const configStore = useConfigurationStore()

onMounted(async () => {
  await configStore.selectConfiguration('my_config')
})

async function save() {
  await configStore.updateConfiguration('my_config', {...})
}
</script>
```

**After:**
```vue
<script setup lang="ts">
const configStore = useConfigurationStore()
const { startSession, endSession, saveWithVersionCheck } = useSession()

onMounted(async () => {
  await startSession('my_config')
  await configStore.selectConfiguration('my_config')
})

onUnmounted(async () => {
  await endSession()
})

async function save() {
  await saveWithVersionCheck() // Uses configStore internally
}
</script>
```

## Performance Considerations

### Auto-Refresh Interval
```typescript
// Default: 30 seconds (balances freshness vs load)
sessionStore.startAutoRefresh(30000)

// High-traffic: increase interval
sessionStore.startAutoRefresh(60000) // 1 minute

// Low-latency: decrease interval
sessionStore.startAutoRefresh(10000) // 10 seconds
```

### Session Timeout
Server-side: 30 minutes (configurable in backend)

Frontend should:
- Auto-refresh to extend timeout
- Warn user before expiry
- Handle 404 gracefully

## Future Enhancements

### WebSocket Real-Time Updates
```typescript
// Notify when other users save
socket.on('config:updated', ({ config_name, version, user }) => {
  if (sessionStore.configName === config_name) {
    // Show notification
    notify(`${user} saved changes (v${version})`)
    
    // Optional: auto-reload
    if (!sessionStore.isModified) {
      configStore.selectConfiguration(config_name)
    }
  }
})
```

### Three-Way Merge UI
```vue
<MergeDialog
  :base="originalConfig"
  :local="localChanges"
  :remote="remoteChanges"
  @resolve="handleMerge"
/>
```

### Offline Support
```typescript
// Queue saves while offline
const { saveWithVersionCheck } = useSession({ offline: true })

// Auto-retry when online
window.addEventListener('online', () => {
  sessionStore.retrySave()
})
```

## Troubleshooting

### Session Cookie Not Sent
Ensure `withCredentials: true` in axios config:
```typescript
// frontend/src/api/client.ts
withCredentials: true
```

### CORS Issues
Backend must allow credentials:
```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,  # Required for cookies
    allow_origins=["http://localhost:5173"],
)
```

### Session Expires Too Quickly
Increase auto-refresh frequency or server timeout:
```typescript
// Frontend: refresh every 10 minutes
sessionStore.startAutoRefresh(600000)

// Backend: increase timeout to 60 minutes
# backend/app/core/state_manager.py
stale_threshold = datetime.now().timestamp() - 3600
```

## Summary

The frontend session management provides:
- ✅ Multi-user support with conflict detection
- ✅ Optimistic concurrency control via versioning
- ✅ Real-time concurrent editor awareness
- ✅ Auto-refresh to prevent session expiry
- ✅ Graceful error handling and recovery
- ✅ Easy component integration via composables
- ✅ Full backward compatibility

All components using `useSession()` automatically benefit from these features without requiring significant code changes.
