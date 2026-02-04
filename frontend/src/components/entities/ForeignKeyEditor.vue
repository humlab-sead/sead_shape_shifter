<template>
  <v-card class="fk-editor-compact">
    <v-card-title class="d-flex align-center justify-space-between py-2">
      <span class="text-body-2">Foreign Keys</span>
      <v-btn variant="text" size="x-small" prepend-icon="mdi-plus" @click="handleAddForeignKey"> Add </v-btn>
    </v-card-title>

    <v-divider />

    <v-card-text class="pa-2">
      <v-expansion-panels v-if="foreignKeys.length > 0" variant="accordion" density="compact">
        <v-expansion-panel v-for="(fk, index) in foreignKeys" :key="index">
          <v-expansion-panel-title class="py-2">
            <div class="d-flex align-center justify-space-between flex-grow-1">
              <span class="text-caption">
                {{ getForeignKeyLabel(fk) }}
              </span>
              <v-btn icon="mdi-delete" variant="text" size="x-small" color="error"
                @click.stop="handleRemoveForeignKey(index)" />
            </div>
          </v-expansion-panel-title>

          <v-expansion-panel-text class="pt-2">
            <v-row class="mb-2">
              <v-col cols="12" md="5">
                <v-autocomplete v-model="fk.entity" :items="availableEntities" label="Target Entity" variant="outlined"
                  density="compact" hide-details prepend-inner-icon="mdi-link-variant" />
              </v-col>

              <v-col cols="12" md="2">
                <v-select v-model="fk.how" :items="joinTypes" label="Join Type" variant="outlined" density="compact"
                  hide-details />
              </v-col>

              <v-col cols="12" md="5" v-if="fk.constraints">
                <v-expansion-panels variant="accordion" density="compact">
                  <v-expansion-panel>
                    <v-expansion-panel-title class="py-1 text-caption"> Constraints </v-expansion-panel-title>
                    <v-expansion-panel-text class="pt-1">
                      <v-select v-model="fk.constraints.cardinality" :items="cardinalityTypes" label="Cardinality"
                        variant="outlined" density="compact" class="mb-1" />

                      <v-checkbox v-model="fk.constraints.require_unique_left" label="Require Unique Left"
                        density="compact" hide-details />

                      <v-checkbox v-model="fk.constraints.allow_null_keys" label="Allow Null Keys" density="compact"
                        hide-details />
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-col>
            </v-row>

            <v-row dense class="mb-2">
              <v-col cols="12" md="5">
                <v-combobox 
                  v-model="fk.local_keys" 
                  label="Local Keys" 
                  chips 
                  multiple 
                  variant="outlined"
                  density="compact" 
                  :items="localColumnItems[index]"
                  item-value="value"
                  :error="localKeyErrors[index] !== undefined"
                  :messages="localKeyErrors[index]"
                  @focus="loadLocalColumns(index)"
                  @update:model-value="validateLocalKeys(index)"
                >
                  <template v-slot:chip="{ item, props: chipProps }">
                    <v-chip v-bind="chipProps" size="x-small" closable>
                      {{ item.value }}
                    </v-chip>
                  </template>
                  <template v-slot:item="{ item, props: itemProps }">
                    <v-list-item v-bind="itemProps">
                      <template v-slot:title>
                        {{ item.raw.value }}
                      </template>
                      <template v-slot:subtitle>
                        <span class="text-caption text-grey">{{ item.raw.category }}</span>
                      </template>
                    </v-list-item>
                  </template>
                </v-combobox>
              </v-col>

              <v-col cols="12" md="2" class="d-flex align-center justify-center">
                <v-icon icon="mdi-arrow-right" size="small" />
              </v-col>

              <v-col cols="12" md="5">
                <v-combobox 
                  v-model="fk.remote_keys" 
                  label="Remote Keys" 
                  chips 
                  multiple 
                  variant="outlined"
                  density="compact" 
                  :items="remoteColumnItems[index]"
                  item-value="value"
                  :error="remoteKeyErrors[index] !== undefined"
                  :messages="remoteKeyErrors[index]"
                  @focus="loadRemoteColumns(index)"
                  @update:model-value="validateRemoteKeys(index)"
                >
                  <template v-slot:chip="{ item, props: chipProps }">
                    <v-chip v-bind="chipProps" size="x-small" closable>
                      {{ item.value }}
                    </v-chip>
                  </template>
                  <template v-slot:item="{ item, props: itemProps }">
                    <v-list-item v-bind="itemProps">
                      <template v-slot:title>
                        {{ item.raw.value }}
                      </template>
                      <template v-slot:subtitle>
                        <span class="text-caption text-grey">{{ item.raw.category }}</span>
                      </template>
                    </v-list-item>
                  </template>
                </v-combobox>
              </v-col>
            </v-row>

            <!-- Extra Columns Section -->
            <v-row dense class="mb-2">
              <v-col cols="12">
                <v-expansion-panels variant="accordion" density="compact">
                  <v-expansion-panel>
                    <v-expansion-panel-title class="py-1 text-caption">
                      <v-icon size="small" class="mr-1">mdi-table-column-plus-after</v-icon>
                      Extra Columns
                      <v-chip v-if="getExtraColumnsCount(fk) > 0" size="x-small" class="ml-2">
                        {{ getExtraColumnsCount(fk) }}
                      </v-chip>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text class="pt-2">
                      <div v-if="getExtraColumnsArray(fk).length > 0" class="mb-2">
                        <v-row
                          v-for="(extraCol, colIndex) in getExtraColumnsArray(fk)"
                          :key="colIndex"
                          dense
                          class="mb-2"
                        >
                          <v-col cols="5">
                            <v-text-field
                              v-model="extraCol.local"
                              label="Local Name"
                              variant="outlined"
                              density="compact"
                              hide-details
                              @update:model-value="updateExtraColumn(index, colIndex, extraCol.local, extraCol.remote)"
                            />
                          </v-col>
                          <v-col cols="1" class="d-flex align-center justify-center">
                            <v-icon size="small">mdi-arrow-left</v-icon>
                          </v-col>
                          <v-col cols="5">
                            <v-combobox
                              v-model="extraCol.remote"
                              label="Remote Column"
                              variant="outlined"
                              density="compact"
                              :items="remoteColumnItems[index]"
                              item-value="value"
                              hide-details
                              @focus="loadRemoteColumns(index)"
                              @update:model-value="updateExtraColumn(index, colIndex, extraCol.local, extraCol.remote)"
                            >
                              <template v-slot:item="{ item, props: itemProps }">
                                <v-list-item v-bind="itemProps">
                                  <template v-slot:title>
                                    {{ item.raw.value }}
                                  </template>
                                  <template v-slot:subtitle>
                                    <span class="text-caption text-grey">{{ item.raw.category }}</span>
                                  </template>
                                </v-list-item>
                              </template>
                            </v-combobox>
                          </v-col>
                          <v-col cols="1" class="d-flex align-center">
                            <v-btn
                              icon="mdi-delete"
                              variant="text"
                              size="x-small"
                              color="error"
                              @click="removeExtraColumn(index, colIndex)"
                            />
                          </v-col>
                        </v-row>
                      </div>
                      <v-btn
                        variant="outlined"
                        size="small"
                        prepend-icon="mdi-plus"
                        @click="addExtraColumn(index)"
                        block
                      >
                        Add Extra Column
                      </v-btn>
                      <div class="text-caption text-grey mt-2">
                        Extra columns are pulled from the remote entity during the join
                      </div>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-col>
            </v-row>

            <!-- Test Join Button -->
            <v-row dense>
              <v-col cols="12">
                <ForeignKeyTester :project-name="projectName" :entity-name="entityName" :foreign-key="fk"
                  :foreign-key-index="index" :disabled="!isEntitySaved" />
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <v-alert v-else type="info" variant="tonal" density="compact">
        No foreign keys defined. Click "Add" to create a relationship.
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ForeignKeyConfig } from '@/types'
import ForeignKeyTester from './ForeignKeyTester.vue'
import { useColumnIntrospection } from '@/composables/useColumnIntrospection'
import { useDirectiveValidation } from '@/composables/useDirectiveValidation'

interface Props {
  modelValue: ForeignKeyConfig[]
  availableEntities?: string[]
  projectName: string
  entityName: string
  isEntitySaved?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  availableEntities: () => [],
  isEntitySaved: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: ForeignKeyConfig[]]
}>()

const foreignKeys = ref<ForeignKeyConfig[]>([...props.modelValue])
const { getAvailableColumns, flattenColumns } = useColumnIntrospection()
const { validateDirective, isDirective } = useDirectiveValidation()

// Cache for column suggestions per entity
const columnCache = ref<Map<string, Array<{ value: string; category: string }>>>(new Map())

// Items for comboboxes (indexed by FK index)
const localColumnItems = ref<Array<Array<{ title: string; value: string; category: string }>>>([])
const remoteColumnItems = ref<Array<Array<{ title: string; value: string; category: string }>>>([])

// Validation errors for directive values (indexed by FK index)
const localKeyErrors = ref<Array<string | undefined>>([])
const remoteKeyErrors = ref<Array<string | undefined>>([])

/**
 * Validate local keys for directive references.
 */
async function validateLocalKeys(fkIndex: number) {
  const fk = foreignKeys.value[fkIndex]
  if (!fk) return
  if (!fk.local_keys || fk.local_keys.length === 0) {
    localKeyErrors.value[fkIndex] = undefined
    return
  }

  // Check if any key is a directive
  const directiveKey = fk.local_keys.find(key => isDirective(key))
  if (!directiveKey) {
    localKeyErrors.value[fkIndex] = undefined
    return
  }

  // Validate the directive
  const result = await validateDirective(props.projectName, directiveKey as string, {
    localEntity: props.entityName,
    remoteEntity: fk.entity,
    isLocalKeys: true,
  })

  if (result && !result.is_valid) {
    let errorMsg = result.error || 'Invalid @value directive'
    if (result.suggestions.length > 0) {
      errorMsg += `. Try: ${result.suggestions.slice(0, 2).join(', ')}`
    }
    localKeyErrors.value[fkIndex] = errorMsg
  } else {
    localKeyErrors.value[fkIndex] = undefined
  }
}

/**
 * Validate remote keys for directive references.
 */
async function validateRemoteKeys(fkIndex: number) {
  const fk = foreignKeys.value[fkIndex]
  if (!fk) return
  if (!fk.remote_keys || fk.remote_keys.length === 0) {
    remoteKeyErrors.value[fkIndex] = undefined
    return
  }

  // Check if any key is a directive
  const directiveKey = fk.remote_keys.find(key => isDirective(key))
  if (!directiveKey) {
    remoteKeyErrors.value[fkIndex] = undefined
    return
  }

  // Validate the directive
  const result = await validateDirective(props.projectName, directiveKey as string, {
    localEntity: props.entityName,
    remoteEntity: fk.entity,
    isLocalKeys: false,
  })

  if (result && !result.is_valid) {
    let errorMsg = result.error || 'Invalid @value directive'
    if (result.suggestions.length > 0) {
      errorMsg += `. Try: ${result.suggestions.slice(0, 2).join(', ')}`
    }
    remoteKeyErrors.value[fkIndex] = errorMsg
  } else {
    remoteKeyErrors.value[fkIndex] = undefined
  }
}

/**
 * Get column suggestions for an entity.
 */
async function getColumnSuggestions(entityName: string): Promise<Array<{ value: string; category: string }>> {
  if (columnCache.value.has(entityName)) {
    return columnCache.value.get(entityName)!
  }

  const result = await getAvailableColumns(props.projectName, entityName)
  if (!result) {
    return []
  }

  const suggestions = flattenColumns(result.local_columns)
  columnCache.value.set(entityName, suggestions)
  return suggestions
}

/**
 * Load local columns for a specific FK.
 */
async function loadLocalColumns(fkIndex: number) {
  const existingItems = localColumnItems.value[fkIndex]
  if (existingItems && existingItems.length > 0) {
    return // Already loaded
  }

  const suggestions = await getColumnSuggestions(props.entityName)
  localColumnItems.value[fkIndex] = suggestions.map(s => ({
    title: s.value,
    value: s.value,
    category: s.category,
  }))
}

/**
 * Load remote columns for a specific FK.
 */
async function loadRemoteColumns(fkIndex: number) {
  const fk = foreignKeys.value[fkIndex]
  if (!fk) return
  if (!fk.entity) {
    remoteColumnItems.value[fkIndex] = []
    return
  }

  const existingItems = remoteColumnItems.value[fkIndex]
  if (existingItems && existingItems.length > 0) {
    return // Already loaded
  }

  const suggestions = await getColumnSuggestions(fk.entity)
  remoteColumnItems.value[fkIndex] = suggestions.map(s => ({
    title: s.value,
    value: s.value,
    category: s.category,
  }))
}

// Watch for entity changes to reload remote columns
watch(
  () => foreignKeys.value.map(fk => fk.entity),
  (newEntities, oldEntities) => {
    newEntities.forEach((entity, index) => {
      if (entity !== oldEntities[index]) {
        // Entity changed, clear remote columns cache for this FK
        remoteColumnItems.value[index] = []
      }
    })
  },
  { deep: true }
)

const joinTypes = [
  { title: 'Inner Join', value: 'inner' },
  { title: 'Left Join', value: 'left' },
  { title: 'Right Join', value: 'right' },
  { title: 'Outer Join', value: 'outer' },
  { title: 'Cross Join', value: 'cross' },
]

const cardinalityTypes = [
  { title: 'One to One', value: 'one_to_one' },
  { title: 'One to Many', value: 'one_to_many' },
  { title: 'Many to One', value: 'many_to_one' },
]

function getForeignKeyLabel(fk: ForeignKeyConfig): string {
  const entity = fk.entity || 'Unnamed Entity'
  const localKeys = Array.isArray(fk.local_keys) && fk.local_keys.length > 0
    ? fk.local_keys.join(', ')
    : '?'
  const remoteKeys = Array.isArray(fk.remote_keys) && fk.remote_keys.length > 0
    ? fk.remote_keys.join(', ')
    : '?'

  return `${entity}: ${localKeys} → ${remoteKeys}`
}

function handleAddForeignKey() {
  foreignKeys.value.push({
    entity: '',
    local_keys: [],
    remote_keys: [],
    how: 'inner',
    constraints: {
      cardinality: 'many_to_one',
      require_unique_left: false,
      allow_null_keys: false,
    },
  })
}

function handleRemoveForeignKey(index: number) {
  foreignKeys.value.splice(index, 1)
}

/**
 * Get count of extra columns for a foreign key.
 */
function getExtraColumnsCount(fk: ForeignKeyConfig): number {
  if (!fk.extra_columns) return 0
  if (Array.isArray(fk.extra_columns)) return fk.extra_columns.length
  if (typeof fk.extra_columns === 'object') return Object.keys(fk.extra_columns).length
  return 0
}

/**
 * Convert extra_columns to array format for editing.
 */
function getExtraColumnsArray(fk: ForeignKeyConfig): Array<{ local: string; remote: string }> {
  if (!fk.extra_columns) return []
  
  if (Array.isArray(fk.extra_columns)) {
    // If it's an array of strings, assume they map to themselves
    return fk.extra_columns.map(col => ({ local: col, remote: col }))
  }
  
  if (typeof fk.extra_columns === 'object' && fk.extra_columns !== null) {
    // Convert object to array of { local, remote } pairs
    return Object.entries(fk.extra_columns).map(([local, remote]) => ({
      local,
      remote: remote as string,
    }))
  }
  
  return []
}

/**
 * Add a new extra column entry.
 */
function addExtraColumn(fkIndex: number) {
  const fk = foreignKeys.value[fkIndex]
  if (!fk) return
  
  // Initialize as object if not exists
  if (!fk.extra_columns || typeof fk.extra_columns !== 'object' || Array.isArray(fk.extra_columns)) {
    fk.extra_columns = {}
  }
  
  // Add new empty entry
  const newKey = `column_${Object.keys(fk.extra_columns).length + 1}`
  fk.extra_columns[newKey] = ''
}

/**
 * Update an extra column entry.
 */
function updateExtraColumn(fkIndex: number, colIndex: number, localName: string, remoteName: string) {
  const fk = foreignKeys.value[fkIndex]
  if (!fk) return
  
  // Ensure extra_columns is an object
  if (!fk.extra_columns || typeof fk.extra_columns !== 'object' || Array.isArray(fk.extra_columns)) {
    fk.extra_columns = {}
  }
  
  // Get current entries
  const entries = Object.entries(fk.extra_columns)
  
  if (colIndex >= 0 && colIndex < entries.length) {
    const entry = entries[colIndex]
    if (!entry) return
    
    const [oldKey] = entry
    
    // If local name changed, remove old key and add new one
    if (oldKey !== localName) {
      delete fk.extra_columns[oldKey]
    }
    
    // Set new/updated mapping
    if (localName && remoteName) {
      fk.extra_columns[localName] = remoteName
    }
  }
}

/**
 * Remove an extra column entry.
 */
function removeExtraColumn(fkIndex: number, colIndex: number) {
  const fk = foreignKeys.value[fkIndex]
  if (!fk) return
  
  if (!fk.extra_columns || typeof fk.extra_columns !== 'object' || Array.isArray(fk.extra_columns)) return
  
  const entries = Object.entries(fk.extra_columns)
  
  if (colIndex >= 0 && colIndex < entries.length) {
    const entry = entries[colIndex]
    if (!entry) return
    
    const [key] = entry
    delete fk.extra_columns[key]
    
    // Clean up if empty
    if (Object.keys(fk.extra_columns).length === 0) {
      fk.extra_columns = undefined
    }
  }
}

// Emit changes
watch(
  foreignKeys,
  (newValue) => {
    emit('update:modelValue', newValue)
  },
  { deep: true }
)

// Sync with prop changes (only when not editing)
watch(
  () => props.modelValue,
  (newValue) => {
    // Deep comparison to avoid overwriting user edits
    if (JSON.stringify(foreignKeys.value) !== JSON.stringify(newValue)) {
      foreignKeys.value = newValue.map((fk) => ({
        ...fk,
        constraints: fk.constraints || {
          cardinality: 'many_to_one',
          require_unique_left: false,
          allow_null_keys: false,
        },
      }))
    }
  }
)
</script>
<style scoped>
.fk-editor-compact :deep(.v-field__input) {
  font-size: 11px;
  padding-top: 2px;
  padding-bottom: 2px;
}

.fk-editor-compact :deep(.v-field__prepend-inner) {
  padding-top: 2px;
}

.fk-editor-compact :deep(.v-label) {
  font-size: 11px;
}

.fk-editor-compact :deep(.v-chip) {
  font-size: 10px;
  height: 20px;
}

.fk-editor-compact :deep(.v-checkbox .v-label) {
  font-size: 11px;
}

.fk-editor-compact :deep(.v-field) {
  --v-field-padding-top: 2px;
  --v-field-padding-bottom: 2px;
}

.fk-editor-compact :deep(.v-field--variant-outlined .v-field__outline) {
  --v-field-border-opacity: 0.3;
}

.fk-editor-compact :deep(.v-expansion-panel-title) {
  min-height: 32px;
  font-size: 11px;
}

.fk-editor-compact :deep(.v-expansion-panel-text__wrapper) {
  padding: 4px 8px;
}

.fk-editor-compact :deep(.v-btn) {
  font-size: 11px;
}
</style>
