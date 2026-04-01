<template>
  <v-card class="branch-editor">
    <v-card-title class="d-flex align-center justify-space-between py-2">
      <span class="text-body-2">Branches</span>
      <v-btn variant="text" size="x-small" prepend-icon="mdi-plus" @click="handleAddBranch"> Add Branch </v-btn>
    </v-card-title>

    <v-divider />

    <v-card-text class="pa-4">
      <v-expansion-panels v-if="branches.length > 0" variant="accordion" density="compact" class="mb-3">
        <v-expansion-panel v-for="(item, index) in branches" :key="index">
          <v-expansion-panel-title class="py-2">
            <div class="d-flex align-center justify-space-between flex-grow-1 mr-2">
              <div class="d-flex align-center ga-2">
                <v-chip size="x-small" color="primary" variant="tonal">{{ index + 1 }}</v-chip>
                <span class="text-caption font-weight-medium">{{ item.name || '(unnamed)' }}</span>
                <span v-if="item.source" class="text-caption text-medium-emphasis">← {{ item.source }}</span>
                <v-chip
                  v-if="getSourcePublicId(item.source)"
                  size="x-small"
                  color="secondary"
                  variant="tonal"
                  class="text-caption"
                >
                  FK: {{ getSourcePublicId(item.source) }}
                </v-chip>
              </div>
              <div class="d-flex ga-1">
                <v-btn
                  icon="mdi-arrow-up"
                  variant="text"
                  size="x-small"
                  :disabled="index === 0"
                  @click.stop="handleMoveBranch(index, -1)"
                />
                <v-btn
                  icon="mdi-arrow-down"
                  variant="text"
                  size="x-small"
                  :disabled="index === branches.length - 1"
                  @click.stop="handleMoveBranch(index, 1)"
                />
                <v-btn
                  icon="mdi-delete"
                  variant="text"
                  size="x-small"
                  color="error"
                  @click.stop="handleRemoveBranch(index)"
                />
              </div>
            </div>
          </v-expansion-panel-title>

          <v-expansion-panel-text class="pt-2">
            <v-row align="start">
              <!-- Branch Name -->
              <v-col cols="12" sm="4">
                <v-text-field
                  :model-value="item.name"
                  label="Branch Name *"
                  variant="outlined"
                  density="compact"
                  placeholder="e.g., abundance"
                  hint="Unique identifier for this branch (snake_case)"
                  persistent-hint
                  :rules="[
                    (v: string) => !!v || 'Branch name is required',
                    (v: string) => /^[a-z][a-z0-9_]*$/.test(v) || 'Must be snake_case (lowercase letters, digits, underscores)',
                    (v: string) => !isDuplicateName(v, index) || 'Branch names must be unique',
                  ]"
                  @update:model-value="handleBranchNameUpdate(index, $event)"
                />
              </v-col>

              <!-- Source Entity -->
              <v-col cols="12" sm="4">
                <v-autocomplete
                  :model-value="item.source"
                  :items="availableEntities"
                  label="Source Entity *"
                  variant="outlined"
                  density="compact"
                  hint="Entity providing rows for this branch"
                  persistent-hint
                  clearable
                  :rules="[(v: string) => !!v || 'Source entity is required']"
                  @update:model-value="handleBranchSourceUpdate(index, $event)"
                />
              </v-col>

              <!-- Business Keys -->
              <v-col cols="12" sm="4">
                <v-combobox
                  :model-value="item.keys"
                  :items="getSourceColumns(item.source)"
                  label="Branch Keys"
                  variant="outlined"
                  density="compact"
                  multiple
                  chips
                  closable-chips
                  persistent-hint
                  hint="Business keys for pre-merge validation (optional)"
                  @update:model-value="handleBranchKeysUpdate(index, $event)"
                />
              </v-col>
            </v-row>

            <!-- Auto-generated columns preview -->
            <v-alert v-if="item.source" type="info" variant="tonal" density="compact" class="mt-2">
              <div class="text-caption">
                <strong>Auto-generated columns for this branch:</strong>
                <ul class="mt-1 pl-4">
                  <li>
                    <code>{{ parentEntity }}_branch</code> = <em>"{{ item.name || '...' }}"</em>
                    (discriminator)
                  </li>
                  <li v-if="getSourcePublicId(item.source)">
                    <code>{{ getSourcePublicId(item.source) }}</code> = FK to
                    <code>{{ item.source }}.system_id</code>
                    (NULL for other branches)
                  </li>
                  <li v-else class="text-warning">
                    <v-icon size="x-small" color="warning">mdi-alert</v-icon>
                    Source entity <strong>{{ item.source }}</strong> has no <code>public_id</code> — FK column will be
                    <code>{{ item.source }}_id</code>
                  </li>
                </ul>
              </div>
            </v-alert>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <v-alert v-if="branches.length === 0" type="warning" variant="tonal" density="compact" class="mb-3">
        <strong>No branches configured.</strong> A merged entity requires at least one branch. Add a branch to define
        which source entities contribute rows.
      </v-alert>

      <!-- Summary of merged output -->
      <v-alert v-if="branches.length > 1" type="success" variant="tonal" density="compact" class="mt-3">
        <div class="text-caption">
          <strong>Merged output will include:</strong>
          <ul class="mt-1 pl-4">
            <li>
              <code>{{ parentEntity }}_branch</code> discriminator column (values:
              {{ branches.map((b) => `"${b.name}"`).join(', ') }})
            </li>
            <li v-for="b in branches.filter((b) => b.source)" :key="b.source">
              <code>{{ getSourcePublicId(b.source) || `${b.source}_id` }}</code> FK to
              <code>{{ b.source }}</code> (sparse)
            </li>
          </ul>
        </div>
      </v-alert>

      <v-alert type="info" variant="tonal" density="compact" class="mt-3 text-caption">
        <strong>Merged Entity</strong> combines rows from multiple source entities into a single table.
        <ul class="mt-2">
          <li>Each <strong>Branch</strong> contributes rows from one source entity</li>
          <li>A <strong>discriminator column</strong> (<code>{{ parentEntity }}_branch</code>) identifies the origin</li>
          <li>Sparse <strong>FK columns</strong> provide data lineage back to each branch source</li>
          <li>Columns are aligned by <strong>name</strong> — branch-only columns are null-filled for other branches</li>
        </ul>
        <div class="mt-2">
          Branch <strong>Keys</strong> are optional business keys used for pre-merge validation. They must be a subset
          of the source entity's columns.
        </div>
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { BranchConfig } from '@/types/entity'

interface Props {
  modelValue?: BranchConfig[]
  availableEntities?: string[]
  parentEntity?: string
  sourceEntityColumns?: Record<string, string[]>
  sourceEntityPublicIds?: Record<string, string | null>
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  availableEntities: () => [],
  parentEntity: 'entity',
  sourceEntityColumns: () => ({}),
  sourceEntityPublicIds: () => ({}),
})

const emit = defineEmits<{
  'update:modelValue': [value: BranchConfig[]]
}>()

const branches = ref<BranchConfig[]>([])
const lastEmittedValue = ref<string>('[]')

function normalizeForEmit(): BranchConfig[] | undefined {
  const cleaned = branches.value.map((b) => {
    const out: BranchConfig = { name: b.name, source: b.source }
    if (b.keys && b.keys.length > 0) out.keys = [...b.keys]
    return out
  })

  return cleaned.length > 0 ? cleaned : undefined
}

function initializeBranches(): void {
  branches.value = (props.modelValue ?? []).map((branch) => ({
    ...branch,
    keys: branch.keys ?? [],
  }))
}

function handleAddBranch() {
  branches.value = [...branches.value, { name: '', source: '', keys: [] }]
}

function handleRemoveBranch(index: number) {
  branches.value = branches.value.filter((_, branchIndex) => branchIndex !== index)
}

function handleMoveBranch(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= branches.value.length) return

  const updatedBranches = [...branches.value]
  const temp = updatedBranches[index]!
  updatedBranches[index] = updatedBranches[target]!
  updatedBranches[target] = temp
  branches.value = updatedBranches
}

function handleBranchNameUpdate(index: number, value: string) {
  const branch = branches.value[index]
  if (!branch) return

  branches.value[index] = {
    ...branch,
    name: value,
  }
}

function handleBranchSourceUpdate(index: number, value: string) {
  const branch = branches.value[index]
  if (!branch) return

  branches.value[index] = {
    ...branch,
    source: value,
  }
}

function handleBranchKeysUpdate(index: number, value: string[] | undefined) {
  const branch = branches.value[index]
  if (!branch) return

  branches.value[index] = {
    ...branch,
    keys: Array.isArray(value) ? [...value] : [],
  }
}

function getSourceColumns(source: string | undefined): string[] {
  if (!source) return []
  return props.sourceEntityColumns[source] ?? []
}

function getSourcePublicId(source: string | undefined): string | null {
  if (!source) return null
  return props.sourceEntityPublicIds[source] ?? null
}

function isDuplicateName(name: string, currentIndex: number): boolean {
  if (!name) return false
  return branches.value.some((b, i) => i !== currentIndex && b.name === name)
}

watch(
  branches,
  () => {
    const emitValue = normalizeForEmit()
    lastEmittedValue.value = JSON.stringify(emitValue)
    emit('update:modelValue', emitValue ?? [])
  },
  { deep: true }
)

watch(
  () => props.modelValue,
  (incoming) => {
    const serialized = JSON.stringify(incoming ?? [])
    if (serialized !== lastEmittedValue.value) {
      initializeBranches()
    }
  },
  { immediate: true, deep: true }
)
</script>

<style scoped>
.branch-editor {
  width: 100%;
}
</style>
