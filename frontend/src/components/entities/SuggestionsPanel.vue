<template>
  <v-card v-if="suggestions && hasSuggestions" class="mb-4" variant="outlined" color="info">
    <v-card-title class="d-flex align-center bg-info-lighten-5">
      <v-icon icon="mdi-lightbulb-on" class="mr-2" color="info" />
      <span>Smart Suggestions</span>
      <v-spacer />
      <v-chip size="small" color="info" variant="flat">
        {{ totalSuggestions }} suggestions
      </v-chip>
    </v-card-title>

    <v-card-text class="pa-4">
      <!-- Foreign Key Suggestions -->
      <div v-if="suggestions.foreign_key_suggestions?.length > 0" class="mb-4">
        <div class="text-subtitle-2 font-weight-bold mb-2">
          <v-icon icon="mdi-link-variant" size="small" class="mr-1" />
          Foreign Key Relationships
        </div>

        <v-list density="compact" class="pa-0">
          <v-list-item
            v-for="(fk, index) in suggestions.foreign_key_suggestions"
            :key="index"
            class="px-2 py-1 mb-2 rounded"
            :style="{ backgroundColor: getConfidenceColor(fk.confidence, 0.05) }"
          >
            <template #prepend>
              <v-avatar
                :color="getConfidenceColor(fk.confidence)"
                size="32"
                class="mr-2"
              >
                <span class="text-caption font-weight-bold">
                  {{ Math.round(fk.confidence * 100) }}%
                </span>
              </v-avatar>
            </template>

            <v-list-item-title class="d-flex align-center flex-wrap">
              <code class="text-primary">{{ fk.local_keys.join(', ') }}</code>
              <v-icon icon="mdi-arrow-right" size="small" class="mx-2" />
              <code class="text-success">{{ fk.remote_entity }}.{{ fk.remote_keys.join(', ') }}</code>
              <v-chip
                v-if="fk.cardinality"
                size="x-small"
                variant="outlined"
                class="ml-2"
              >
                {{ fk.cardinality }}
              </v-chip>
            </v-list-item-title>

            <v-list-item-subtitle class="text-caption mt-1">
              {{ fk.reason }}
            </v-list-item-subtitle>

            <template #append>
              <div class="d-flex gap-2">
                <v-btn
                  v-if="!isAccepted(fk)"
                  icon="mdi-check"
                  size="x-small"
                  color="success"
                  variant="flat"
                  @click="acceptForeignKey(fk)"
                  title="Accept suggestion"
                />
                <v-btn
                  v-if="!isRejected(fk)"
                  icon="mdi-close"
                  size="x-small"
                  color="error"
                  variant="flat"
                  @click="rejectForeignKey(fk)"
                  title="Reject suggestion"
                />
              </div>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <!-- Dependency Suggestions -->
      <div v-if="suggestions.dependency_suggestions?.length > 0">
        <div class="text-subtitle-2 font-weight-bold mb-2">
          <v-icon icon="mdi-graph" size="small" class="mr-1" />
          Processing Dependencies
        </div>

        <v-list density="compact" class="pa-0">
          <v-list-item
            v-for="(dep, index) in suggestions.dependency_suggestions"
            :key="index"
            class="px-2 py-1 mb-2 rounded"
            :style="{ backgroundColor: getConfidenceColor(dep.confidence, 0.05) }"
          >
            <template #prepend>
              <v-avatar
                :color="getConfidenceColor(dep.confidence)"
                size="32"
                class="mr-2"
              >
                <span class="text-caption font-weight-bold">
                  {{ Math.round(dep.confidence * 100) }}%
                </span>
              </v-avatar>
            </template>

            <v-list-item-title>
              Depends on: <code class="text-primary">{{ dep.entity }}</code>
            </v-list-item-title>

            <v-list-item-subtitle class="text-caption mt-1">
              {{ dep.reason }}
            </v-list-item-subtitle>

            <template #append>
              <div class="d-flex gap-2">
                <v-btn
                  v-if="!isDependencyAccepted(dep)"
                  icon="mdi-check"
                  size="x-small"
                  color="success"
                  variant="flat"
                  @click="acceptDependency(dep)"
                  title="Accept suggestion"
                />
                <v-btn
                  v-if="!isDependencyRejected(dep)"
                  icon="mdi-close"
                  size="x-small"
                  color="error"
                  variant="flat"
                  @click="rejectDependency(dep)"
                  title="Reject suggestion"
                />
              </div>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <!-- Actions -->
      <v-divider class="my-3" />
      <div class="d-flex justify-end gap-2">
        <v-btn
          variant="text"
          size="small"
          @click="acceptAll"
          :disabled="allAccepted"
        >
          Accept All
        </v-btn>
        <v-btn
          variant="text"
          size="small"
          color="error"
          @click="rejectAll"
          :disabled="allRejected"
        >
          Reject All
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

interface ForeignKeySuggestion {
  remote_entity: string
  local_keys: string[]
  remote_keys: string[]
  confidence: number
  reason: string
  cardinality?: string
}

interface DependencySuggestion {
  entity: string
  reason: string
  confidence: number
}

interface EntitySuggestions {
  entity_name: string
  foreign_key_suggestions: ForeignKeySuggestion[]
  dependency_suggestions: DependencySuggestion[]
}

const props = defineProps<{
  suggestions: EntitySuggestions | null
}>()

const emit = defineEmits<{
  'accept-foreign-key': [fk: ForeignKeySuggestion]
  'reject-foreign-key': [fk: ForeignKeySuggestion]
  'accept-dependency': [dep: DependencySuggestion]
  'reject-dependency': [dep: DependencySuggestion]
  'accept-all': []
  'reject-all': []
}>()

const acceptedForeignKeys = ref<Set<string>>(new Set())
const rejectedForeignKeys = ref<Set<string>>(new Set())
const acceptedDependencies = ref<Set<string>>(new Set())
const rejectedDependencies = ref<Set<string>>(new Set())

const hasSuggestions = computed(() => {
  if (!props.suggestions) return false
  return (
    props.suggestions.foreign_key_suggestions?.length > 0 ||
    props.suggestions.dependency_suggestions?.length > 0
  )
})

const totalSuggestions = computed(() => {
  if (!props.suggestions) return 0
  return (
    (props.suggestions.foreign_key_suggestions?.length || 0) +
    (props.suggestions.dependency_suggestions?.length || 0)
  )
})

const allAccepted = computed(() => {
  if (!props.suggestions) return true
  const totalFks = props.suggestions.foreign_key_suggestions?.length || 0
  const totalDeps = props.suggestions.dependency_suggestions?.length || 0
  return (
    acceptedForeignKeys.value.size === totalFks &&
    acceptedDependencies.value.size === totalDeps
  )
})

const allRejected = computed(() => {
  if (!props.suggestions) return true
  const totalFks = props.suggestions.foreign_key_suggestions?.length || 0
  const totalDeps = props.suggestions.dependency_suggestions?.length || 0
  return (
    rejectedForeignKeys.value.size === totalFks &&
    rejectedDependencies.value.size === totalDeps
  )
})

function getForeignKeyId(fk: ForeignKeySuggestion): string {
  return `${fk.remote_entity}:${fk.local_keys.join(',')}:${fk.remote_keys.join(',')}`
}

function getDependencyId(dep: DependencySuggestion): string {
  return dep.entity
}

function isAccepted(fk: ForeignKeySuggestion): boolean {
  return acceptedForeignKeys.value.has(getForeignKeyId(fk))
}

function isRejected(fk: ForeignKeySuggestion): boolean {
  return rejectedForeignKeys.value.has(getForeignKeyId(fk))
}

function isDependencyAccepted(dep: DependencySuggestion): boolean {
  return acceptedDependencies.value.has(getDependencyId(dep))
}

function isDependencyRejected(dep: DependencySuggestion): boolean {
  return rejectedDependencies.value.has(getDependencyId(dep))
}

function acceptForeignKey(fk: ForeignKeySuggestion) {
  const id = getForeignKeyId(fk)
  acceptedForeignKeys.value.add(id)
  rejectedForeignKeys.value.delete(id)
  emit('accept-foreign-key', fk)
}

function rejectForeignKey(fk: ForeignKeySuggestion) {
  const id = getForeignKeyId(fk)
  rejectedForeignKeys.value.add(id)
  acceptedForeignKeys.value.delete(id)
  emit('reject-foreign-key', fk)
}

function acceptDependency(dep: DependencySuggestion) {
  const id = getDependencyId(dep)
  acceptedDependencies.value.add(id)
  rejectedDependencies.value.delete(id)
  emit('accept-dependency', dep)
}

function rejectDependency(dep: DependencySuggestion) {
  const id = getDependencyId(dep)
  rejectedDependencies.value.add(id)
  acceptedDependencies.value.delete(id)
  emit('reject-dependency', dep)
}

function acceptAll() {
  if (!props.suggestions) return
  
  props.suggestions.foreign_key_suggestions?.forEach(fk => {
    if (!isAccepted(fk)) {
      acceptForeignKey(fk)
    }
  })
  
  props.suggestions.dependency_suggestions?.forEach(dep => {
    if (!isDependencyAccepted(dep)) {
      acceptDependency(dep)
    }
  })
  
  emit('accept-all')
}

function rejectAll() {
  if (!props.suggestions) return
  
  props.suggestions.foreign_key_suggestions?.forEach(fk => {
    if (!isRejected(fk)) {
      rejectForeignKey(fk)
    }
  })
  
  props.suggestions.dependency_suggestions?.forEach(dep => {
    if (!isDependencyRejected(dep)) {
      rejectDependency(dep)
    }
  })
  
  emit('reject-all')
}

function getConfidenceColor(confidence: number, alpha?: number): string {
  // High confidence: green, medium: orange, low: red
  const alphaStr = alpha ? `, ${alpha}` : ''
  if (confidence >= 0.7) {
    return `rgba(76, 175, 80${alphaStr})` // green
  } else if (confidence >= 0.5) {
    return `rgba(255, 152, 0${alphaStr})` // orange
  } else {
    return `rgba(244, 67, 54${alphaStr})` // red
  }
}
</script>

<style scoped>
code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.875rem;
}

.bg-info-lighten-5 {
  background-color: rgba(33, 150, 243, 0.05);
}
</style>
