<template>
  <v-alert
    type="error"
    variant="tonal"
    prominent
    border="start"
    class="preview-error"
  >
    <div class="d-flex align-start">
      <v-icon class="mr-3 mt-1">mdi-alert-circle-outline</v-icon>
      
      <div class="flex-grow-1">
        <div class="text-h6 mb-2">Preview Generation Failed</div>
        
        <div class="error-message mb-3">
          {{ errorMessage }}
        </div>

        <v-btn
          v-if="hasDetails"
          variant="text"
          size="small"
          @click="showDetails = !showDetails"
          class="px-0"
        >
          {{ showDetails ? 'Hide' : 'Show' }} Technical Details
          <v-icon end>{{ showDetails ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
        </v-btn>

        <v-expand-transition>
          <div v-if="showDetails" class="technical-details mt-3">
            <v-divider class="my-3"></v-divider>
            
            <div v-if="errorType" class="detail-section">
              <strong>Error Type:</strong> <code>{{ errorType }}</code>
            </div>

            <div v-if="validationErrors.length > 0" class="detail-section">
              <strong>Validation Errors:</strong>
              <ul class="mt-2">
                <li v-for="(err, idx) in validationErrors" :key="idx">
                  {{ err }}
                </li>
              </ul>
            </div>

            <div v-if="traceback" class="detail-section">
              <strong>Traceback:</strong>
              <pre class="traceback mt-2">{{ traceback }}</pre>
            </div>

            <div v-if="rawError" class="detail-section">
              <strong>Raw Error Data:</strong>
              <pre class="raw-error mt-2">{{ rawError }}</pre>
            </div>
          </div>
        </v-expand-transition>
      </div>
    </div>
  </v-alert>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  error: any
}

const props = defineProps<Props>()

const showDetails = ref(false)

const errorMessage = computed(() => {
  if (!props.error) return 'An unknown error occurred while generating the preview'

  // Handle string errors
  if (typeof props.error === 'string') return props.error

  // Handle structured error objects
  if (props.error.detail) return props.error.detail
  if (props.error.message) return props.error.message
  if (props.error.error) return props.error.error
  if (props.error.msg) return props.error.msg

  return 'An error occurred while generating the preview. See technical details below.'
})

const errorType = computed(() => {
  if (!props.error || typeof props.error !== 'object') return null
  return props.error.type || props.error.error_type || null
})

const validationErrors = computed(() => {
  if (!props.error || !Array.isArray(props.error.errors)) return []
  
  return props.error.errors.map((e: any) => {
    if (typeof e === 'string') return e
    if (e.msg) {
      const location = e.loc ? e.loc.join('.') : ''
      return location ? `${location}: ${e.msg}` : e.msg
    }
    return JSON.stringify(e)
  })
})

const traceback = computed(() => {
  if (!props.error || typeof props.error !== 'object') return null
  return props.error.traceback || props.error.stack || null
})

const rawError = computed(() => {
  if (!props.error) return null
  if (typeof props.error === 'string') return null
  
  // Only show raw error if we have a complex object with extra fields
  const { detail, message, error, msg, type, error_type, traceback, stack, errors, ...rest } = props.error
  
  if (Object.keys(rest).length > 0) {
    return JSON.stringify(rest, null, 2)
  }
  
  // Fallback for simple errors without extracted info
  if (!errorMessage.value || errorMessage.value.includes('unknown')) {
    return JSON.stringify(props.error, null, 2)
  }
  
  return null
})

const hasDetails = computed(() => {
  return !!(errorType.value || validationErrors.value.length > 0 || traceback.value || rawError.value)
})
</script>

<style scoped>
.preview-error {
  font-family: 'Roboto', sans-serif;
}

.error-message {
  font-size: 1rem;
  line-height: 1.5;
}

.technical-details {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
  padding: 12px;
}

.detail-section {
  margin-bottom: 12px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section strong {
  display: block;
  margin-bottom: 4px;
  color: rgba(0, 0, 0, 0.7);
}

.detail-section code {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

.detail-section ul {
  padding-left: 20px;
  margin: 0;
}

.detail-section li {
  margin-bottom: 4px;
}

.traceback,
.raw-error {
  background: rgba(0, 0, 0, 0.05);
  padding: 12px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
