<template>
  <v-dialog v-model="dialogVisible" max-width="700" @update:model-value="onDialogChange">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" color="primary">mdi-magnify</v-icon>
        Search for Alternative Match
      </v-card-title>
      
      <v-card-subtitle v-if="originalQuery" class="mt-2">
        <span class="text-grey">Original:</span>
        <v-chip size="small" class="ml-2">{{ originalQuery }}</v-chip>
      </v-card-subtitle>

      <v-card-text>
        <v-text-field
          v-model="searchTerm"
          label="Search for alternatives"
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="comfortable"
          autofocus
          :loading="searching"
          placeholder="Type to search SEAD records..."
          clearable
          @update:model-value="onSearchInput"
          hint="Type at least 2 characters to search"
          persistent-hint
        />

        <!-- Search Results -->
        <div v-if="searched" class="mt-4">
          <v-list v-if="suggestions.length > 0" density="compact">
            <v-list-subheader>{{ suggestions.length }} Results</v-list-subheader>
            
            <v-list-item
              v-for="(suggestion, idx) in suggestions"
              :key="idx"
              :value="suggestion.id"
              @click="selectSuggestion(suggestion)"
              :class="{ 'bg-blue-lighten-5': selectedSuggestion?.id === suggestion.id }"
              class="suggestion-item"
            >
              <template #prepend>
                <v-avatar :color="getScoreColor((suggestion.score ?? 0) * 100)" size="40">
                  <span class="text-white font-weight-bold">
                    {{ Math.round((suggestion.score ?? 0) * 100) }}
                  </span>
                </v-avatar>
              </template>

              <v-list-item-title class="font-weight-medium">
                {{ suggestion.name }}
              </v-list-item-title>

              <v-list-item-subtitle v-if="suggestion.description">
                {{ suggestion.description }}
              </v-list-item-subtitle>

              <template #append>
                <v-chip size="small" variant="outlined" color="primary">
                  ID: {{ extractIdFromUri(suggestion.id) }}
                </v-chip>
              </template>
            </v-list-item>
          </v-list>

          <v-alert v-else type="info" variant="tonal" class="mt-4">
            <v-alert-title>No matches found</v-alert-title>
            Try different search terms or broader keywords.
          </v-alert>
        </div>

        <!-- Search Hint -->
        <v-alert v-if="!searchTerm || searchTerm.length < 2" type="info" variant="text" class="mt-4">
          <v-icon start>mdi-lightbulb-outline</v-icon>
          <span class="text-caption">
            Try using broader terms, alternative spellings, or removing special characters.
          </span>
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="cancel">Cancel</v-btn>
        <v-btn 
          color="primary" 
          variant="tonal"
          :disabled="!selectedSuggestion" 
          @click="accept"
          prepend-icon="mdi-check"
        >
          Accept Match
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { apiClient } from '@/api/client'
import type { ReconciliationCandidate } from '@/types'

interface Props {
  modelValue: boolean
  projectName: string
  entityName: string
  targetField: string
  originalQuery?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  originalQuery: '',
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  accept: [candidate: ReconciliationCandidate]
}>()

const dialogVisible = ref(props.modelValue)
const searchTerm = ref('')
const searching = ref(false)
const searched = ref(false)
const suggestions = ref<ReconciliationCandidate[]>([])
const selectedSuggestion = ref<ReconciliationCandidate | null>(null)

// Watch for external model value changes
watch(() => props.modelValue, (newValue) => {
  dialogVisible.value = newValue
  if (newValue) {
    // Reset on open
    searchTerm.value = props.originalQuery || ''
    selectedSuggestion.value = null
    searched.value = false
    suggestions.value = []
  }
})

// Dialog visibility change
function onDialogChange(value: boolean) {
  console.log('[AlternativeSearchDialog] Dialog visibility changed to:', value)
  emit('update:modelValue', value)
}

// Search for alternatives
async function searchAlternatives() {
  if (!searchTerm.value || searchTerm.value.length < 2) {
    suggestions.value = []
    searched.value = false
    return
  }

  searching.value = true
  searched.value = false

  try {
    // Call the reconciliation suggest endpoint using apiClient
    const response = await apiClient.get(
      `/projects/${props.projectName}/reconciliation/${props.entityName}/${props.targetField}/suggest`,
      { params: { query: searchTerm.value } }
    )

    suggestions.value = response.data.candidates || response.data || []
    searched.value = true
  } catch (error) {
    console.error('Alternative search failed:', error)
    suggestions.value = []
    searched.value = true
  } finally {
    searching.value = false
  }
}

// Debounced search input
const onSearchInput = useDebounceFn(() => {
  searchAlternatives()
}, 400)

// Select a suggestion
function selectSuggestion(suggestion: ReconciliationCandidate) {
  selectedSuggestion.value = suggestion
}

// Get score color
function getScoreColor(score: number): string {
  if (score >= 95) return 'success'
  if (score >= 80) return 'warning'
  return 'info'
}

// Extract ID from URI
function extractIdFromUri(uri: string): number | string {
  const match = uri.match(/\/(\d+)$/)
  return match?.[1] ? parseInt(match[1]) : uri
}

// Accept selected suggestion
function accept() {
  console.log('[AlternativeSearchDialog] Accept clicked, selectedSuggestion:', selectedSuggestion.value)
  if (selectedSuggestion.value) {
    emit('accept', selectedSuggestion.value)
    dialogVisible.value = false
    console.log('[AlternativeSearchDialog] Dialog closed, emitting update:modelValue(false)')
    emit('update:modelValue', false)
  }
}

// Cancel
function cancel() {
  console.log('[AlternativeSearchDialog] Cancel clicked')
  dialogVisible.value = false
  console.log('[AlternativeSearchDialog] Dialog closed, emitting update:modelValue(false)')
  emit('update:modelValue', false)
}
</script>

<style scoped>
.suggestion-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.suggestion-item:hover {
  background-color: rgba(33, 150, 243, 0.08);
}
</style>
