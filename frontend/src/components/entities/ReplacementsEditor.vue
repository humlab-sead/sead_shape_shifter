<template>
  <div class="pa-4">
    <v-row dense>
      <!-- Columns list -->
      <v-col cols="12" md="4">
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-2">Columns</v-card-title>
          <v-divider />
          <v-card-text class="py-2">
            <v-list density="compact">
              <v-list-item
                v-for="col in availableColumnsList"
                :key="col"
                :active="col === selectedColumn"
                @click="selectColumn(col)"
              >
                <v-list-item-title>{{ col }}</v-list-item-title>
                <template #append>
                  <v-chip size="x-small" variant="outlined">
                    {{ ruleCountForColumn(col) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>

            <v-alert v-if="availableColumnsList.length === 0" type="info" variant="tonal" density="compact">
              Add columns in the Basic tab to configure replacements.
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Rules editor -->
      <v-col cols="12" md="8">
        <v-card variant="outlined">
          <v-card-title class="d-flex align-center justify-space-between">
            <span class="text-subtitle-2">Replacements</span>
            <v-btn
              size="small"
              variant="outlined"
              prepend-icon="mdi-plus"
              :disabled="!selectedColumn"
              @click="addRule"
            >
              Add rule
            </v-btn>
          </v-card-title>
          <v-divider />

          <v-card-text>
            <v-alert v-if="!selectedColumn" type="info" variant="tonal" density="compact">
              Select a column to edit replacements.
            </v-alert>

            <template v-else>
              <v-alert v-if="showConversionWarning" type="warning" variant="tonal" density="compact" class="mb-3">
                This column uses a legacy replacement format. Editing here will convert it to the ordered rule-list format.
              </v-alert>

              <div v-if="rules.length === 0" class="text-caption text-medium-emphasis">
                No rules configured for <strong>{{ selectedColumn }}</strong>.
              </div>

              <v-list v-else class="px-0" density="compact">
                <v-list-item v-for="(rule, index) in rules" :key="rule.id" class="px-0 mb-2">
                  <v-card variant="outlined" class="w-100">
                    <v-card-text>
                      <v-row dense>
                        <v-col cols="12" md="4">
                          <v-select
                            v-model="rule.op"
                            :items="opItems"
                            :label="rule.op === 'transform' ? 'Operation' : 'Match'"
                            variant="outlined"
                            density="compact"
                            hide-details
                          />
                        </v-col>
                        <v-col cols="12" md="2" class="d-flex align-center">
                          <v-switch
                            v-model="rule.negate"
                            label="Not"
                            density="compact"
                            hide-details
                            :disabled="!supportsNegate(rule.op)"
                          />
                        </v-col>
                        <v-col cols="12" md="6" class="d-flex justify-end">
                          <v-btn
                            icon="mdi-arrow-up"
                            variant="text"
                            size="small"
                            :disabled="index === 0"
                            @click="moveRule(index, -1)"
                          />
                          <v-btn
                            icon="mdi-arrow-down"
                            variant="text"
                            size="small"
                            :disabled="index === rules.length - 1"
                            @click="moveRule(index, +1)"
                          />
                          <v-btn icon="mdi-content-copy" variant="text" size="small" @click="duplicateRule(index)" />
                          <v-btn icon="mdi-delete" variant="text" size="small" color="error" @click="removeRule(index)" />
                        </v-col>
                      </v-row>

                      <v-row dense class="mt-1">
                        <template v-if="rule.op === 'blank_out'">
                          <v-col cols="12" md="6">
                            <v-combobox
                              v-model="rule.blankValues"
                              label="Values"
                              variant="outlined"
                              density="compact"
                              multiple
                              chips
                              closable-chips
                              hide-details
                            />
                          </v-col>
                          <v-col cols="12" md="3">
                            <v-select
                              v-model="rule.fill"
                              :items="fillItems"
                              label="Fill"
                              variant="outlined"
                              density="compact"
                              hide-details
                            />
                          </v-col>
                          <v-col cols="12" md="3">
                            <v-text-field
                              v-model="rule.fillConstant"
                              label="Constant"
                              variant="outlined"
                              density="compact"
                              hide-details
                              :disabled="rule.fill !== 'constant'"
                            />
                          </v-col>
                        </template>

                        <template v-else-if="rule.op === 'map'">
                          <v-col cols="12">
                            <div class="d-flex align-center justify-space-between mb-2">
                              <div class="text-caption text-medium-emphasis">Map</div>
                              <v-btn size="x-small" variant="outlined" prepend-icon="mdi-plus" @click="addMapPair(rule)">
                                Add pair
                              </v-btn>
                            </div>

                            <v-alert v-if="rule.mapPairs.length === 0" type="info" variant="tonal" density="compact">
                              Add at least one mapping pair.
                            </v-alert>

                            <v-row v-for="(pair, pIndex) in rule.mapPairs" :key="pIndex" dense class="mb-1">
                              <v-col cols="12" md="5">
                                <v-text-field
                                  v-model="pair.from"
                                  label="From"
                                  variant="outlined"
                                  density="compact"
                                  hide-details
                                />
                              </v-col>
                              <v-col cols="12" md="5">
                                <v-text-field
                                  v-model="pair.to"
                                  label="To"
                                  variant="outlined"
                                  density="compact"
                                  hide-details
                                />
                              </v-col>
                              <v-col cols="12" md="2" class="d-flex align-center justify-end">
                                <v-btn
                                  icon="mdi-delete"
                                  variant="text"
                                  size="small"
                                  color="error"
                                  @click="removeMapPair(rule, pIndex)"
                                />
                              </v-col>
                            </v-row>
                          </v-col>
                        </template>

                        <template v-else-if="rule.op === 'in'">
                          <v-col cols="12" md="6">
                            <v-combobox
                              v-model="rule.fromList"
                              label="From (list)"
                              variant="outlined"
                              density="compact"
                              multiple
                              chips
                              closable-chips
                              hide-details
                            />
                          </v-col>
                          <v-col cols="12" md="6">
                            <v-text-field
                              v-model="rule.to"
                              label="To"
                              variant="outlined"
                              density="compact"
                              hide-details
                            />
                          </v-col>
                        </template>

                        <template v-else-if="rule.op === 'transform'">
                          <v-col cols="12">
                            <v-alert type="info" variant="tonal" density="compact">
                              Transform rule applies normalize/coerce operations to <strong>all values</strong> without filtering.
                              Configure normalize and/or coerce options below.
                            </v-alert>
                          </v-col>
                        </template>

                        <template v-else>
                          <v-col cols="12" md="6">
                            <v-text-field
                              v-model="rule.from"
                              :label="rule.op === 'regex' ? 'Pattern' : 'From'"
                              variant="outlined"
                              density="compact"
                              hide-details
                            />
                          </v-col>
                          <v-col cols="12" md="6">
                            <v-text-field
                              v-model="rule.to"
                              label="To"
                              variant="outlined"
                              density="compact"
                              hide-details
                            />
                          </v-col>
                        </template>
                      </v-row>

                      <v-row dense class="mt-1">
                        <v-col cols="12" md="6">
                          <v-combobox
                            v-model="rule.normalize"
                            :items="normalizeItems"
                            label="Normalize"
                            variant="outlined"
                            density="compact"
                            multiple
                            chips
                            closable-chips
                            hide-details
                          />
                        </v-col>
                        <v-col cols="12" md="3">
                          <v-checkbox
                            v-model="rule.ignorecase"
                            label="Ignore case"
                            density="compact"
                            hide-details
                            :disabled="!supportsIgnoreCase(rule.op)"
                          />
                        </v-col>
                        <v-col cols="12" md="3">
                          <v-select
                            v-model="rule.coerce"
                            :items="coerceItems"
                            label="Coerce"
                            variant="outlined"
                            density="compact"
                            clearable
                            hide-details
                          />
                        </v-col>
                      </v-row>
                    </v-card-text>
                  </v-card>
                </v-list-item>
              </v-list>
            </template>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type RuleOp = 'equals' | 'contains' | 'startswith' | 'endswith' | 'regex' | 'in' | 'blank_out' | 'map' | 'transform'
type BlankFill = 'forward' | 'backward' | 'none' | 'constant'

interface UiRule {
  id: string
  op: RuleOp
  negate: boolean
  from: string
  fromList: string[]
  to: string
  blankValues: string[]
  fill: BlankFill
  fillConstant: string
  mapPairs: Array<{ from: string; to: string }>
  normalize: string[]
  ignorecase: boolean
  coerce: string | null
}

interface Props {
  modelValue?: Record<string, any>
  availableColumns?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: undefined,
  availableColumns: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any> | undefined]
}>()

const opItems = [
  { title: 'transform (all values)', value: 'transform' },
  { title: 'equals', value: 'equals' },
  { title: 'contains', value: 'contains' },
  { title: 'startswith', value: 'startswith' },
  { title: 'endswith', value: 'endswith' },
  { title: 'in', value: 'in' },
  { title: 'regex', value: 'regex' },
  { title: 'blank_out', value: 'blank_out' },
  { title: 'map', value: 'map' },
]

const fillItems = [
  { title: 'forward', value: 'forward' },
  { title: 'backward', value: 'backward' },
  { title: 'none', value: 'none' },
  { title: 'constant', value: 'constant' },
]

const normalizeItems = ['strip', 'lower', 'upper', 'collapse_ws']

const coerceItems = [
  { title: 'string', value: 'string' },
  { title: 'int', value: 'int' },
  { title: 'float', value: 'float' },
]

const availableColumnsList = computed(() => (props.availableColumns || []).filter((c) => typeof c === 'string' && c.length > 0))

const selectedColumn = ref<string | null>(null)
function deepClone<T>(value: T): T {
  try {
    // @ts-expect-error - structuredClone may not exist in some TS lib configs.
    return structuredClone(value)
  } catch {
    return JSON.parse(JSON.stringify(value))
  }
}

const rawReplacements = ref<Record<string, any>>(deepClone(props.modelValue || {}))
const rules = ref<UiRule[]>([])
const showConversionWarning = ref(false)
const isLoadingColumn = ref(false)  // Prevent infinite loop between watchers
const isPersisting = ref(false)  // Track when we're persisting to prevent reload loop

function supportsNegate(op: RuleOp): boolean {
  return ['equals', 'contains', 'startswith', 'endswith', 'in', 'regex'].includes(op)
}

function supportsIgnoreCase(op: RuleOp): boolean {
  return ['equals', 'contains', 'startswith', 'endswith', 'in', 'regex'].includes(op)
}

function newId(): string {
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function ruleCountForColumn(col: string): number {
  const v = rawReplacements.value?.[col]
  if (Array.isArray(v)) return v.length
  if (v && typeof v === 'object') return 1
  if (v != null) return 1
  return 0
}

function selectColumn(col: string) {
  selectedColumn.value = col
  loadColumn(col)
}

function loadColumn(col: string) {
  isLoadingColumn.value = true  // Prevent rules watcher from triggering persist
  
  const spec = rawReplacements.value?.[col]

  showConversionWarning.value = false

  // Only fully support the advanced list-of-rule-dicts format for now.
  if (Array.isArray(spec) && spec.every((r) => r && typeof r === 'object' && !Array.isArray(r))) {
    rules.value = spec
      .filter((r: any) => r && typeof r === 'object')
      .map((r: any) => fromRuleDict(r))
      .filter((r) => r !== null) as UiRule[]
    isLoadingColumn.value = false  // Done loading
    return
  }

  // Legacy formats (mapping, scalar/list blank-out) are preserved unless user edits.
  if (spec !== undefined) {
    showConversionWarning.value = true
  }
  rules.value = []
  isLoadingColumn.value = false  // Done loading
}

function fromRuleDict(rule: Record<string, any>): UiRule | null {
  if ('blank_out' in rule) {
    const fillRaw = rule.fill
    let fill: BlankFill = 'forward'
    let fillConstant = ''
    if (fillRaw === null || fillRaw === false || String(fillRaw).toLowerCase() === 'none') {
      fill = 'none'
    } else if (String(fillRaw).toLowerCase() === 'backward') {
      fill = 'backward'
    } else if (String(fillRaw).toLowerCase() === 'forward') {
      fill = 'forward'
    } else if (fillRaw && typeof fillRaw === 'object' && 'constant' in fillRaw) {
      fill = 'constant'
      fillConstant = fillRaw.constant != null ? String(fillRaw.constant) : ''
    }

    const values = Array.isArray(rule.blank_out)
      ? rule.blank_out.map((v: any) => String(v))
      : rule.blank_out != null
        ? [String(rule.blank_out)]
        : []

    return {
      id: newId(),
      op: 'blank_out',
      negate: false,
      from: '',
      fromList: [],
      to: '',
      blankValues: values,
      fill,
      fillConstant,
      mapPairs: [],
      normalize: Array.isArray(rule.normalize) ? rule.normalize.map((x: any) => String(x)) : [],
      ignorecase: false,
      coerce: rule.coerce != null ? String(rule.coerce).toLowerCase() : null,
    }
  }

  if ('map' in rule && rule.map && typeof rule.map === 'object' && !Array.isArray(rule.map)) {
    const entries = Object.entries(rule.map as Record<string, any>).map(([k, v]) => ({ from: String(k), to: v != null ? String(v) : '' }))
    return {
      id: newId(),
      op: 'map',
      negate: false,
      from: '',
      fromList: [],
      to: '',
      blankValues: [],
      fill: 'forward',
      fillConstant: '',
      mapPairs: entries,
      normalize: Array.isArray(rule.normalize) ? rule.normalize.map((x: any) => String(x)) : [],
      ignorecase: false,
      coerce: rule.coerce != null ? String(rule.coerce).toLowerCase() : null,
    }
  }

  // Transform rule: has normalize/coerce but no match/from/map/blank_out
  const hasTransformOps = (Array.isArray(rule.normalize) && rule.normalize.length > 0) || rule.coerce
  const hasMatchCondition = 'match' in rule || 'from' in rule
  if (hasTransformOps && !hasMatchCondition) {
    return {
      id: newId(),
      op: 'transform',
      negate: false,
      from: '',
      fromList: [],
      to: '',
      blankValues: [],
      fill: 'forward',
      fillConstant: '',
      mapPairs: [],
      normalize: Array.isArray(rule.normalize) ? rule.normalize.map((x: any) => String(x)) : [],
      ignorecase: false,
      coerce: rule.coerce != null ? String(rule.coerce).toLowerCase() : null,
    }
  }

  const match = String(rule.match || 'equals').toLowerCase()

  const negate = match.startsWith('not_')
  const base = (negate ? match.slice(4) : match) as RuleOp
  if (!['equals', 'contains', 'startswith', 'endswith', 'in', 'regex'].includes(base)) {
    return null
  }

  const flags = Array.isArray(rule.flags) ? rule.flags.map((f: any) => String(f).toLowerCase()) : []

  const fromList = base === 'in'
    ? (Array.isArray(rule.from) ? rule.from.map((v: any) => String(v)) : rule.from != null ? [String(rule.from)] : [])
    : []

  return {
    id: newId(),
    op: base,
    negate,
    from: base === 'in' ? '' : (rule.from != null ? String(rule.from) : ''),
    fromList,
    to: rule.to != null ? String(rule.to) : '',
    blankValues: [],
    fill: 'forward',
    fillConstant: '',
    mapPairs: [],
    normalize: Array.isArray(rule.normalize) ? rule.normalize.map((x: any) => String(x)) : [],
    ignorecase: flags.includes('ignorecase') || flags.includes('i'),
    coerce: rule.coerce != null ? String(rule.coerce).toLowerCase() : null,
  }
}

function toRuleDict(rule: UiRule): Record<string, any> {
  if (rule.op === 'blank_out') {
    const out: Record<string, any> = {
      blank_out: rule.blankValues,
    }
    if (rule.fill === 'none') {
      out.fill = 'none'
    } else if (rule.fill === 'forward') {
      out.fill = 'forward'
    } else if (rule.fill === 'backward') {
      out.fill = 'backward'
    } else if (rule.fill === 'constant') {
      out.fill = { constant: rule.fillConstant }
    }

    if (rule.normalize && rule.normalize.length > 0) {
      out.normalize = rule.normalize
    }
    if (rule.coerce) {
      out.coerce = rule.coerce
    }
    return out
  }

  if (rule.op === 'map') {
    const map: Record<string, any> = {}
    for (const pair of rule.mapPairs || []) {
      if (pair.from === '') continue
      map[pair.from] = pair.to
    }
    const out: Record<string, any> = { map }
    if (rule.normalize && rule.normalize.length > 0) {
      out.normalize = rule.normalize
    }
    if (rule.coerce) {
      out.coerce = rule.coerce
    }
    return out
  }

  if (rule.op === 'transform') {
    const out: Record<string, any> = {}
    // Transform rules only have normalize/coerce, no match/from
    if (rule.normalize && rule.normalize.length > 0) {
      out.normalize = rule.normalize
    }
    if (rule.coerce) {
      out.coerce = rule.coerce
    }
    return out
  }

  const match = rule.negate ? (`not_${rule.op}` as const) : rule.op
  const out: Record<string, any> = {
    match,
    from: rule.op === 'in' ? rule.fromList : rule.from,
    to: rule.to,
  }

  if (rule.normalize && rule.normalize.length > 0) {
    out.normalize = rule.normalize
  }

  const flags: string[] = []
  if (rule.ignorecase) flags.push('ignorecase')
  if (flags.length > 0) {
    out.flags = flags
  }

  if (rule.coerce) {
    out.coerce = rule.coerce
  }

  return out
}

function addRule() {
  if (!selectedColumn.value) return

  // Default to transform rule (applies to all values)
  const rule: UiRule = {
    id: newId(),
    op: 'transform',
    negate: false,
    from: '',
    fromList: [],
    to: '',
    blankValues: [],
    fill: 'forward',
    fillConstant: '',
    mapPairs: [],
    normalize: [],
    ignorecase: false,
    coerce: null,
  }

  rules.value.push(rule)
  persist()
}

function removeRule(index: number) {
  rules.value.splice(index, 1)
  persist()
}

function duplicateRule(index: number) {
  const r = rules.value[index]
  if (!r) return
  rules.value.splice(index + 1, 0, { ...deepClone(r), id: newId() })
  persist()
}

function moveRule(index: number, delta: number) {
  const next = index + delta
  if (next < 0 || next >= rules.value.length) return
  const copy = [...rules.value]
  const [item] = copy.splice(index, 1)
  copy.splice(next, 0, item)
  rules.value = copy
  persist()
}

function addMapPair(rule: UiRule) {
  rule.mapPairs.push({ from: '', to: '' })
  persist()
}

function removeMapPair(rule: UiRule, index: number) {
  rule.mapPairs.splice(index, 1)
  persist()
}

function persist() {
  if (!selectedColumn.value) return

  isPersisting.value = true  // Set flag before emitting
  
  // Convert to rule-list format (advanced rules)
  rawReplacements.value[selectedColumn.value] = rules.value.map(toRuleDict)

  // Drop empty object
  const keys = Object.keys(rawReplacements.value)
  if (keys.length === 0) {
    emit('update:modelValue', undefined)
  } else {
    emit('update:modelValue', rawReplacements.value)
  }
  
  // Clear flag on next tick after parent has processed the update
  setTimeout(() => {
    isPersisting.value = false
  }, 0)
}

watch(
  () => props.modelValue,
  (newValue) => {
    // If we just persisted, skip reload to prevent infinite loop
    if (isPersisting.value) {
      return
    }
    
    rawReplacements.value = deepClone(newValue || {})

    // Keep current column selection if still present
    if (selectedColumn.value && rawReplacements.value[selectedColumn.value] !== undefined) {
      loadColumn(selectedColumn.value)
      return
    }

    // Auto-select first column for convenience
    selectedColumn.value = availableColumnsList.value[0] || null
    if (selectedColumn.value) {
      loadColumn(selectedColumn.value)
    } else {
      rules.value = []
    }
  },
  { deep: true, immediate: true }
)

watch(
  rules,
  () => {
    // Skip persist if we're loading column data (prevents infinite loop)
    if (isLoadingColumn.value) {
      return
    }
    
    // Persist whenever rules change through v-model bindings.
    // (Operations like add/move/delete already call persist, but edits do not.)
    if (selectedColumn.value) {
      persist()
    }
  },
  { deep: true }
)
</script>
