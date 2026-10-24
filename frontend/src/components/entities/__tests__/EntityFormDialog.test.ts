import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import type { ColumnAvailabilityResponse, EntityResponse } from '@/api/entities'
import type { ValidationResult } from '@/types'
import EntityFormDialog from '../EntityFormDialog.vue'
import { getExtraColumnDiagnostics } from '../extraColumnsEditorUtils'

const mockState = vi.hoisted(() => ({
  entities: [] as EntityResponse[],
  previewData: null as any,
  previewLoading: false,
  previewError: null as any,
  previewLastRefresh: new Date('2026-03-31T12:00:00Z'),
  create: vi.fn(),
  update: vi.fn(),
  previewEntity: vi.fn(async () => mockState.previewData),
  debouncedPreviewEntity: vi.fn(),
  getSuggestionsForEntity: vi.fn(),
  columnAvailability: null as ColumnAvailabilityResponse | null,
  refreshColumnAvailability: vi.fn(),
  showError: vi.fn(),
  showWarning: vi.fn(),
  getValidDirectives: vi.fn(async () => []),
  getEntity: vi.fn(),
  getValues: vi.fn(),
  updateValues: vi.fn(),
  retryFixedEntityMapping: vi.fn(),
  setMappingSyncPending: vi.fn(),
  introspectQueryColumns: vi.fn(async () => []),
  syncCachedEntity: vi.fn(),
  validateEntityDraft: vi.fn(),
}))

vi.mock('@/composables', async () => {
  const vue = await import('vue')

  return {
    useEntities: () => ({
      entities: vue.ref(mockState.entities),
      create: mockState.create,
      update: mockState.update,
    }),
    useSuggestions: () => ({
      getSuggestionsForEntity: mockState.getSuggestionsForEntity,
      loading: vue.ref(false),
    }),
    useColumnAvailability: () => ({
      availability: vue.ref(mockState.columnAvailability),
      loading: vue.ref(false),
      error: vue.ref(null),
      refresh: mockState.refreshColumnAvailability,
    }),
    useEntityPreview: () => ({
      previewData: vue.ref(mockState.previewData),
      loading: vue.ref(mockState.previewLoading),
      error: vue.ref(mockState.previewError),
      lastRefresh: vue.ref(mockState.previewLastRefresh),
      previewEntity: mockState.previewEntity,
      debouncedPreviewEntity: mockState.debouncedPreviewEntity,
      clearPreview: vi.fn(),
    }),
    useSettings: () => ({
      enableFkSuggestions: vue.ref(false),
    }),
  }
})

vi.mock('@/composables/useNotification', () => ({
  useNotification: () => ({
    error: mockState.showError,
    warning: mockState.showWarning,
  }),
}))

vi.mock('@/stores', () => ({
  useProjectStore: () => ({
    selectedProject: { options: { data_sources: {} } },
    currentProjectName: 'arbodat',
  }),
  useEntityStore: () => ({
    overlayInitialTab: 'form',
    syncCachedEntity: mockState.syncCachedEntity,
    setMappingSyncPending: mockState.setMappingSyncPending,
    mappingSyncPending: null,
  }),
}))

vi.mock('@/api', () => ({
  api: {
    entities: {
      get: mockState.getEntity,
      getValues: mockState.getValues,
      updateValues: mockState.updateValues,
      retryFixedEntityMapping: mockState.retryFixedEntityMapping,
    },
    dataSources: {
      getEntityTypes: vi.fn(async () => []),
    },
    excelMetadata: {
      fetch: vi.fn(async () => ({ sheets: [], columns: [] })),
    },
  },
}))

vi.mock('@/api/query', () => ({
  queryApi: {
    introspectQueryColumns: mockState.introspectQueryColumns,
  },
}))

vi.mock('@/api/validation', () => ({
  validationApi: { validateEntityDraft: mockState.validateEntityDraft },
}))

const vuetify = createVuetify({ components, directives })

const childStubs = {
  teleport: true,
  VDialog: {
    props: ['modelValue'],
    template: '<div class="v-dialog-stub"><slot /></div>',
  },
  VTabs: {
    template: '<div class="v-tabs-stub"><slot /></div>',
  },
  VTab: {
    name: 'VTab',
    props: ['value', 'disabled'],
    template:
      '<button type="button" class="v-tab-stub" :data-tab-value="value" :data-disabled="String(disabled)"><slot /></button>',
  },
  VWindow: {
    template: '<div class="v-window-stub"><slot /></div>',
  },
  VWindowItem: {
    props: ['value'],
    template: '<div class="v-window-item-stub" :data-window-value="value"><slot /></div>',
  },
  VTooltip: {
    template: '<div><slot name="activator" :props="{}" /><slot /></div>',
  },
  VOverlay: {
    template: '<div><slot /></div>',
  },
  VProgressCircular: {
    template: '<div class="v-progress-circular-stub" />',
  },
  VSelect: {
    name: 'VSelect',
    props: ['modelValue', 'label', 'items', 'disabled'],
    template: '<div class="v-select-stub" :data-label="label" :data-disabled="String(disabled)"><slot /></div>',
  },
  VAutocomplete: {
    name: 'VAutocomplete',
    props: ['modelValue', 'label', 'items', 'disabled'],
    template: '<div class="v-autocomplete-stub" :data-label="label" :data-disabled="String(disabled)"><slot /></div>',
  },
  VCombobox: {
    name: 'VCombobox',
    props: ['modelValue', 'label', 'items', 'disabled'],
    template: '<div class="v-combobox-stub" :data-label="label" :data-disabled="String(disabled)"><slot /></div>',
  },
  ColumnReferenceCombobox: {
    name: 'ColumnReferenceCombobox',
    props: [
      'modelValue',
      'items',
      'label',
      'disabled',
      'projectName',
      'entityName',
      'entityDraft',
      'editedFieldPath',
      'preferredEntity',
      'rules',
      'validationIssues',
      'validationLoading',
      'validationError',
    ],
    emits: ['update:modelValue', 'inspect-reference', 'replace-reference'],
    template: '<div class="column-reference-combobox-stub" :data-label="label"><slot /></div>',
  },
  YamlEditor: {
    name: 'YamlEditor',
    props: ['modelValue'],
    emits: ['update:modelValue', 'change', 'validate'],
    template: '<div data-testid="yaml-editor" />',
  },
  SqlEditor: { template: '<div data-testid="sql-editor" />' },
  ForeignKeyEditor: {
    name: 'ForeignKeyEditor',
    props: ['modelValue', 'columnCandidates', 'entityDraft', 'referenceControlsDisabled'],
    emits: ['update:modelValue', 'inspect-reference', 'replace-reference'],
    template: '<div data-testid="foreign-key-editor" />',
  },
  FiltersEditor: { template: '<div data-testid="filters-editor" />' },
  UnnestEditor: {
    name: 'UnnestEditor',
    props: [
      'modelValue',
      'idVarColumns',
      'valueVarColumns',
      'projectName',
      'entityName',
      'entityDraft',
      'referenceControlsDisabled',
      'idVarValidationIssues',
      'valueVarValidationIssues',
      'validationLoading',
      'validationError',
    ],
    emits: ['update:modelValue', 'inspect-reference', 'replace-reference'],
    template: '<div data-testid="unnest-editor" />',
  },
  AppendEditor: { template: '<div data-testid="append-editor" />' },
  BranchEditor: { template: '<div data-testid="branch-editor" />' },
  ExtraColumnsEditor: {
    name: 'ExtraColumnsEditor',
    props: ['availableColumns', 'reservedNames'],
    template: '<div data-testid="extra-columns-editor" />',
  },
  ReplacementsEditor: {
    name: 'ReplacementsEditor',
    props: ['modelValue', 'availableColumns'],
    template: '<div data-testid="replacements-editor" />',
  },
  FixedValuesGrid: {
    name: 'FixedValuesGrid',
    props: ['modelValue', 'columns', 'publicId', 'columnTypes'],
    template: '<div data-testid="fixed-values-grid" />',
  },
  SuggestionsPanel: { template: '<div data-testid="suggestions-panel" />' },
  MaterializeDialog: { name: 'MaterializeDialog', template: '<div data-testid="materialize-dialog" />' },
  UnmaterializeDialog: { name: 'UnmaterializeDialog', template: '<div data-testid="unmaterialize-dialog" />' },
  AgGridVue: { template: '<div data-testid="preview-grid" />' },
}

function createEntity(name: string, entity_data: Record<string, unknown>): EntityResponse {
  return {
    name,
    entity_data,
    etag: `etag-${name}`,
  }
}

function makeMappingPending(overrides: Record<string, unknown> = {}) {
  return {
    status: 'pending' as const,
    rows_saved: true,
    project: 'arbodat',
    entity: 'method',
    storage_kind: 'inline' as const,
    local_key: 'label',
    public_id: 'method_id',
    operations: [
      {
        op: 'upsert' as const,
        key: 'Sampling',
        target_id: 54,
        expected_row_present: true,
        expected_saved_id: 54,
        prior_link: null,
        row_index: 0,
      },
    ],
    entry: null,
    expected_row_version: 'rows-v1',
    expected_sidecar_version: 'sidecar-v1',
    ...overrides,
  }
}

const mergedEntity = createEntity('analysis_entity', {
  type: 'merged',
  public_id: 'analysis_entity_id',
  keys: ['sample_name'],
  columns: ['sample_name', 'dating_value'],
  branches: [
    { name: 'abundance', source: 'abundance_source', keys: ['sample_name'] },
    { name: 'relative_dating', source: 'relative_dating_source', keys: ['sample_name'] },
  ],
})

const fixedEntity: EntityResponse = {
  name: 'method',
  etag: 'etag-method',
  fixed_schema: {
    full_columns: ['system_id', 'method_id', 'label', 'created_at'],
    editable_columns: ['label', 'created_at'],
    identity_columns: ['system_id', 'method_id'],
    key_columns: ['label'],
    order_source: 'stored',
  },
  entity_data: {
    type: 'fixed',
    public_id: 'method_id',
    keys: ['label'],
    columns: ['system_id', 'method_id', 'label', 'created_at'],
    column_types: {
      label: 'string',
      created_at: 'date',
    },
    values: [[1, 53, 'Sampling', '2026-05-19']],
  },
}

// Backend metadata order differs from the business-key order: the produced key
// `label` follows `created_at` in the authoritative full schema.
const orderedFixedEntity: EntityResponse = {
  name: 'method',
  etag: 'etag-method-ordered',
  fixed_schema: {
    full_columns: ['system_id', 'method_id', 'created_at', 'label'],
    editable_columns: ['created_at'],
    identity_columns: ['system_id', 'method_id'],
    key_columns: ['label'],
    order_source: 'stored',
  },
  entity_data: {
    type: 'fixed',
    public_id: 'method_id',
    keys: ['label'],
    columns: ['created_at', 'label'],
    column_types: {
      label: 'string',
      created_at: 'date',
    },
    values: [[1, 53, '2026-05-19', 'Sampling']],
  },
}

// A fixed entity whose values live in external storage.
const externalFixedEntity: EntityResponse = {
  name: 'method',
  etag: 'etag-method-external',
  fixed_schema: {
    full_columns: ['system_id', 'method_id', 'created_at', 'label'],
    editable_columns: ['created_at'],
    identity_columns: ['system_id', 'method_id'],
    key_columns: ['label'],
    order_source: 'stored',
  },
  entity_data: {
    type: 'fixed',
    public_id: 'method_id',
    keys: ['label'],
    columns: ['created_at', 'label'],
    values: '@load:materialized/method.parquet',
  },
}

const sourceEntities = [
  createEntity('abundance_source', {
    type: 'entity',
    public_id: 'abundance_id',
    columns: ['sample_name', 'abundance_value'],
    keys: ['sample_name'],
  }),
  createEntity('relative_dating_source', {
    type: 'entity',
    public_id: 'relative_dating_id',
    columns: ['sample_name', 'dating_value'],
    keys: ['sample_name'],
  }),
  mergedEntity,
]

function mountEntityFormDialog(props: Partial<InstanceType<typeof EntityFormDialog>['$props']> = {}) {
  return mount(EntityFormDialog, {
    props: {
      modelValue: true,
      projectName: 'arbodat',
      mode: 'create',
      ...props,
    },
    global: {
      plugins: [vuetify],
      stubs: childStubs,
    },
  })
}

function findSelectByLabel(wrapper: ReturnType<typeof mountEntityFormDialog>, label: string) {
  return wrapper.findAllComponents({ name: 'VSelect' }).find((component) => component.props('label') === label)
}

function findComboboxByLabel(wrapper: ReturnType<typeof mountEntityFormDialog>, label: string) {
  return (
    wrapper
      .findAllComponents({ name: 'ColumnReferenceCombobox' })
      .find((component) => component.props('label') === label) ??
    wrapper.findAllComponents({ name: 'VCombobox' }).find((component) => component.props('label') === label)
  )
}

function editEntityName(wrapper: ReturnType<typeof mountEntityFormDialog>, name: string) {
  const nameField = wrapper
    .findAllComponents({ name: 'VTextField' })
    .find((component) => component.props('label') === 'Entity Name *')
  nameField?.vm.$emit('update:modelValue', name)
}

function findTabByValue(wrapper: ReturnType<typeof mountEntityFormDialog>, value: string) {
  return wrapper.findAllComponents({ name: 'VTab' }).find((component) => component.props('value') === value)
}

describe('EntityFormDialog', () => {
  beforeEach(() => {
    mockState.entities = [...sourceEntities]
    mockState.create.mockResolvedValue(undefined)
    mockState.update.mockResolvedValue(undefined)
    mockState.previewData = {
      entity_name: 'analysis_entity',
      rows: [
        {
          analysis_entity_branch: 'abundance',
          abundance_id: 1,
          relative_dating_id: null,
          sample_name: 'S1',
        },
      ],
      columns: [
        {
          name: 'analysis_entity_branch',
          data_type: 'string',
          nullable: false,
          is_key: false,
          is_derived: true,
          derived_from: null,
        },
        { name: 'abundance_id', data_type: 'int', nullable: true, is_key: false, is_derived: true, derived_from: null },
        {
          name: 'relative_dating_id',
          data_type: 'int',
          nullable: true,
          is_key: false,
          is_derived: true,
          derived_from: null,
        },
        {
          name: 'sample_name',
          data_type: 'string',
          nullable: false,
          is_key: true,
          is_derived: false,
          derived_from: null,
        },
      ],
      total_rows_in_preview: 1,
      estimated_total_rows: 1,
      execution_time_ms: 5,
      has_dependencies: true,
      dependencies_loaded: ['abundance_source', 'relative_dating_source'],
      cache_hit: false,
      validation_issues: [],
    }
    mockState.previewLoading = false
    mockState.previewError = null
    mockState.previewEntity.mockClear()
    mockState.debouncedPreviewEntity.mockClear()
    mockState.getSuggestionsForEntity.mockReset()
    mockState.columnAvailability = null
    mockState.refreshColumnAvailability.mockReset()
    mockState.showError.mockReset()
    mockState.showWarning.mockReset()
    mockState.getEntity.mockReset()
    mockState.getValues.mockReset()
    mockState.updateValues.mockReset()
    mockState.retryFixedEntityMapping.mockReset()
    mockState.setMappingSyncPending.mockReset()
    mockState.syncCachedEntity.mockReset()
    mockState.validateEntityDraft.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('loads persisted replacements into the ReplacementsEditor when the edit dialog opens', async () => {
    const entityWithReplacements = createEntity('locations', {
      type: 'entity',
      public_id: 'location_id',
      keys: ['location_name'],
      columns: ['socken', 'landskap'],
      replacements: {
        landskap: [{ map: { Bo: 'Bohuslan', Vg: 'Vastergotland' } }],
      },
    })

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: entityWithReplacements })
    await flushPromises()
    await nextTick()

    const replacementsEditor = wrapper.findComponent({ name: 'ReplacementsEditor' })
    expect(replacementsEditor.props('modelValue')).toEqual({
      landskap: [{ map: { Bo: 'Bohuslan', Vg: 'Vastergotland' } }],
    })
  })

  it('passes one current serialized draft and field path to each in-scope picker', async () => {
    const entity = createEntity('reference_form', {
      type: 'entity',
      public_id: 'reference_form_id',
      keys: '@value: entities.site.keys',
      columns: ['sample_name'],
      drop_duplicates: ['sample_name'],
      drop_empty_rows: ['sample_name'],
      foreign_keys: [{ entity: 'site', local_keys: ['site_name'], remote_keys: ['site_id'], how: 'left' }],
      unnest: { id_vars: ['sample_name'], value_vars: ['sample_value'], var_name: 'variable', value_name: 'value' },
    })
    mockState.entities = [...sourceEntities, createEntity('site', { type: 'entity', columns: ['site_id'] })]

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()
    await nextTick()

    const referenceInputs = wrapper.findAllComponents({ name: 'ColumnReferenceCombobox' })
    const paths = referenceInputs.map((input) => input.props('editedFieldPath'))
    expect(paths).toEqual([
      'entities.reference_form.keys',
      'entities.reference_form.columns',
      'entities.reference_form.drop_duplicates',
      'entities.reference_form.drop_empty_rows',
    ])
    expect(
      referenceInputs.every((input) => input.props('entityDraft') === referenceInputs[0]?.props('entityDraft'))
    ).toBe(true)
    expect(referenceInputs[0]?.props('entityDraft')).toMatchObject({
      keys: '@value: entities.site.keys',
      columns: ['sample_name'],
      foreign_keys: [{ entity: 'site', local_keys: ['site_name'], remote_keys: ['site_id'] }],
    })

    const foreignKeyEditor = wrapper.findComponent({ name: 'ForeignKeyEditor' })
    const unnestEditor = wrapper.findComponent({ name: 'UnnestEditor' })
    expect(foreignKeyEditor.props('entityDraft')).toBe(referenceInputs[0]?.props('entityDraft'))
    expect(unnestEditor.props('entityDraft')).toBe(referenceInputs[0]?.props('entityDraft'))
    expect(unnestEditor.props('projectName')).toBe('arbodat')
    expect(unnestEditor.props('entityName')).toBe('reference_form')

    editEntityName(wrapper, 'renamed_reference_form')
    await nextTick()
    expect(wrapper.findAllComponents({ name: 'ColumnReferenceCombobox' })[0]?.props('editedFieldPath')).toBe(
      'entities.renamed_reference_form.keys'
    )
    expect(wrapper.findAllComponents({ name: 'ColumnReferenceCombobox' })[0]?.props('entityName')).toBe(
      'renamed_reference_form'
    )
    await wrapper.setProps({ modelValue: false })
    expect(
      wrapper.findAllComponents({ name: 'ColumnReferenceCombobox' }).every((input) => input.props('disabled') === true)
    ).toBe(true)
  })

  it('keeps Fixed Entity Columns on the plain combobox', async () => {
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: fixedEntity })
    await flushPromises()
    await nextTick()

    expect(
      wrapper.findAllComponents({ name: 'ColumnReferenceCombobox' }).some((input) => input.props('label') === 'Columns')
    ).toBe(false)
    expect(wrapper.findAllComponents({ name: 'VCombobox' }).some((input) => input.props('label') === 'Columns')).toBe(
      true
    )
  })

  it('labels saved structural findings and does not pass them as current draft annotations', async () => {
    const entity = createEntity('saved_findings', {
      type: 'entity',
      public_id: 'saved_findings_id',
      keys: ['missing'],
      columns: ['present'],
    })
    const savedValidationResult: ValidationResult = {
      is_valid: false,
      errors: [
        {
          severity: 'error',
          entity: entity.name,
          field: 'keys',
          message: "Entity 'saved_findings': key column(s) ['missing'] are not produced by this entity.",
          code: 'BUSINESS_KEY_NOT_PRODUCED',
          related_columns: ['missing'],
        },
      ],
      warnings: [],
      info: [],
      error_count: 1,
      warning_count: 0,
    }

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity, savedValidationResult })
    await flushPromises()

    expect(wrapper.get('[data-testid="saved-project-findings"]').text()).toContain('Saved project findings')
    expect(wrapper.get('[data-testid="saved-project-findings"]').text()).toContain('are not produced')
    const keys = findComboboxByLabel(wrapper, 'Business Keys *')
    expect(keys?.props('validationIssues')).toEqual([])
  })

  it('requests draft findings on inspection and clears annotations after an edit', async () => {
    vi.useFakeTimers()
    const reference = '@value: entities.site.keys'
    const entity = createEntity('draft_findings', {
      type: 'entity',
      public_id: 'draft_findings_id',
      keys: reference,
      columns: ['shared'],
      unnest: { id_vars: ['shared'], value_vars: [reference], var_name: 'kind', value_name: 'value' },
    })
    const result: ValidationResult = {
      is_valid: false,
      errors: [
        {
          severity: 'error',
          entity: entity.name,
          field: 'keys',
          message: 'The business key is not produced.',
          code: 'BUSINESS_KEY_NOT_PRODUCED',
          related_columns: ['missing'],
        },
      ],
      warnings: [
        {
          severity: 'warning',
          entity: entity.name,
          field: 'unnest.value_vars',
          message: 'ID and Value Variables overlap.',
          code: 'UNNEST_VARIABLE_OVERLAP',
          related_columns: ['shared'],
        },
      ],
      info: [],
      error_count: 1,
      warning_count: 1,
    }
    mockState.validateEntityDraft.mockResolvedValue(result)

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()
    const keys = findComboboxByLabel(wrapper, 'Business Keys *')
    keys?.vm.$emit('inspect-reference')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    expect(mockState.validateEntityDraft).toHaveBeenCalledWith('arbodat', entity.name, {
      entity_draft: expect.objectContaining({ keys: reference, columns: ['shared'] }),
      original_entity_name: entity.name,
    })
    expect(keys?.props('validationIssues')).toEqual([result.errors[0]])
    const unnestEditor = wrapper.findComponent({ name: 'UnnestEditor' })
    expect(unnestEditor.props('idVarValidationIssues')).toEqual([result.warnings[0]])
    expect(unnestEditor.props('valueVarValidationIssues')).toEqual([result.warnings[0]])

    keys?.vm.$emit('update:modelValue', ['changed_key'])
    await nextTick()
    expect(keys?.props('validationIssues')).toEqual([])
    expect(unnestEditor.props('valueVarValidationIssues')).toEqual([])
  })

  it('replaces and undoes one reference in each control group while preserving untouched storage on Save', async () => {
    const reference = '@value: entities.site.keys'
    const manualReference = '@value: entities.site.manual_columns'
    const legacyExpression = "'literal' + @value: entities.site.keys"
    const entity = createEntity('reference_replacement', {
      type: 'entity',
      public_id: 'reference_replacement_id',
      keys: reference,
      columns: [manualReference, reference],
      drop_duplicates: ['before_duplicate', reference, 'after_duplicate'],
      drop_empty_rows: [legacyExpression, reference],
      foreign_keys: [{ entity: 'site', local_keys: [reference, 'local_manual'], remote_keys: reference, how: 'left' }],
      unnest: {
        id_vars: reference,
        value_vars: ['manual_value', reference],
        var_name: 'variable',
        value_name: 'value',
      },
    })
    mockState.update.mockResolvedValue({ name: entity.name, warnings: [] })

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()
    await nextTick()
    const resolvedColumns = ['expanded_a', 'expanded_b', 'expanded_a']
    const basePath = 'entities.reference_replacement'

    async function replaceDirectField(fieldPath: string, keepReplacement = false) {
      const picker = wrapper
        .findAllComponents({ name: 'ColumnReferenceCombobox' })
        .find((candidate) => candidate.props('editedFieldPath') === fieldPath)
      expect(picker).toBeDefined()
      const before = picker!.props('modelValue') as string[]
      const index = before.indexOf(reference)
      expect(index).toBeGreaterThanOrEqual(0)
      const after = [...before]
      after.splice(index, 1, ...resolvedColumns)
      picker!.vm.$emit('update:modelValue', after)
      picker!.vm.$emit('replace-reference', { fieldPath, before, after })
      await nextTick()
      expect(wrapper.find('[data-testid="reference-replacement-undo"]').exists()).toBe(true)
      if (!keepReplacement) {
        await wrapper.get('[data-testid="undo-reference-replacement"]').trigger('click')
        await flushPromises()
        const restored = wrapper
          .findAllComponents({ name: 'ColumnReferenceCombobox' })
          .find((candidate) => candidate.props('editedFieldPath') === fieldPath)
        expect(restored?.props('modelValue')).toEqual(before)
        expect(wrapper.find('[data-testid="reference-replacement-undo"]').exists()).toBe(false)
      }
      return { before, after }
    }

    const initialDraft = wrapper
      .findAllComponents({ name: 'ColumnReferenceCombobox' })[0]
      ?.props('entityDraft') as Record<string, unknown>
    expect(initialDraft).toMatchObject({
      keys: reference,
      columns: [manualReference, reference],
      drop_duplicates: ['before_duplicate', reference, 'after_duplicate'],
      drop_empty_rows: [legacyExpression, reference],
    })

    for (const field of ['keys', 'columns', 'drop_duplicates']) {
      await replaceDirectField(`${basePath}.${field}`)
    }

    const foreignKeyEditor = wrapper.findComponent({ name: 'ForeignKeyEditor' })
    for (const keyName of ['local_keys', 'remote_keys']) {
      const currentKeys = foreignKeyEditor.props('modelValue') as Array<Record<string, any>>
      const before = currentKeys[0]?.[keyName] as string[]
      const after = [...before]
      after.splice(after.indexOf(reference), 1, ...resolvedColumns)
      const updatedForeignKeys = [{ ...currentKeys[0], [keyName]: after }]
      const fieldPath = `${basePath}.foreign_keys.0.${keyName}`
      foreignKeyEditor.vm.$emit('update:modelValue', updatedForeignKeys)
      foreignKeyEditor.vm.$emit('replace-reference', { fieldPath, before, after })
      expect((wrapper.vm as any).$.setupState.referenceReplacement).toMatchObject({ fieldPath, before, after })
      await flushPromises()
      expect(wrapper.find('[data-testid="reference-replacement-undo"]').exists()).toBe(true)
      await wrapper.get('[data-testid="undo-reference-replacement"]').trigger('click')
      await flushPromises()
      expect((foreignKeyEditor.props('modelValue') as Array<Record<string, any>>)[0]?.[keyName]).toEqual(before)
    }

    const unnestEditor = wrapper.findComponent({ name: 'UnnestEditor' })
    for (const keyName of ['id_vars', 'value_vars']) {
      const currentUnnest = unnestEditor.props('modelValue') as Record<string, any>
      const before = currentUnnest[keyName] as string[]
      const after = [...before]
      after.splice(after.indexOf(reference), 1, ...resolvedColumns)
      const fieldPath = `${basePath}.unnest.${keyName}`
      unnestEditor.vm.$emit('update:modelValue', { ...currentUnnest, [keyName]: after })
      unnestEditor.vm.$emit('replace-reference', { fieldPath, before, after })
      await flushPromises()
      expect(wrapper.find('[data-testid="reference-replacement-undo"]').exists()).toBe(true)
      await wrapper.get('[data-testid="undo-reference-replacement"]').trigger('click')
      await flushPromises()
      expect((unnestEditor.props('modelValue') as Record<string, any>)[keyName]).toEqual(before)
    }

    const { before, after } = await replaceDirectField(`${basePath}.drop_empty_rows`, true)
    expect(after).toEqual([legacyExpression, ...resolvedColumns])
    ;(wrapper.vm as any).$.setupState.activeTab = 'relationships'
    await nextTick()
    expect(wrapper.find('[data-testid="undo-reference-replacement"]').exists()).toBe(true)

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    const savedData = mockState.update.mock.calls.at(-1)?.[1].entity_data
    expect(savedData).toMatchObject({
      keys: reference,
      columns: [manualReference, reference],
      drop_duplicates: ['before_duplicate', reference, 'after_duplicate'],
      drop_empty_rows: [legacyExpression, ...resolvedColumns],
      foreign_keys: [{ entity: 'site', local_keys: [reference, 'local_manual'], remote_keys: reference, how: 'left' }],
      unnest: {
        id_vars: reference,
        value_vars: ['manual_value', reference],
        var_name: 'variable',
        value_name: 'value',
      },
    })
    expect(savedData.drop_empty_rows).not.toEqual(before)
    expect(wrapper.find('[data-testid="reference-replacement-undo"]').exists()).toBe(false)
  })

  it('preserves every saved column-list field shape after an unrelated edit and child editor updates', async () => {
    const rawDropDuplicates = ['before', '@value: entities.site.columns', 'after']
    const rawUnnest = {
      id_vars: '@value: entities.site.keys',
      value_vars: ['manual_value', '@value: entities.site.columns'],
      var_name: 'variable',
      value_name: 'value',
      keep_empty: true,
    }
    const entity = createEntity('reference_columns', {
      type: 'entity',
      public_id: 'reference_columns_id',
      keys: '  @value: entities.site.keys  ',
      columns: ['@value: entities.site.columns', 'manual_column'],
      drop_duplicates: rawDropDuplicates,
      drop_empty_rows: '@value: entities.site.keys + @value: entities.site.columns',
      foreign_keys: [
        {
          entity: 'site',
          local_keys: "['local_first'] + @value: entities.site.keys",
          remote_keys: ['@value: entities.site.columns'],
          how: 'left',
        },
      ],
      unnest: rawUnnest,
    })
    mockState.update.mockResolvedValue({ name: entity.name, warnings: [] })

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()
    await nextTick()

    expect(findComboboxByLabel(wrapper, 'Business Keys *')?.props('modelValue')).toEqual(['@value: entities.site.keys'])
    expect(findComboboxByLabel(wrapper, 'Columns')?.props('modelValue')).toEqual([
      '@value: entities.site.columns',
      'manual_column',
    ])
    expect(findComboboxByLabel(wrapper, 'Deduplication Columns')?.props('modelValue')).toEqual(rawDropDuplicates)
    expect(findComboboxByLabel(wrapper, 'Columns to Check for Empty Values')?.props('modelValue')).toEqual([
      '@value: entities.site.keys + @value: entities.site.columns',
    ])

    const foreignKeyEditor = wrapper.findComponent({ name: 'ForeignKeyEditor' })
    const foreignKeyFormValue = foreignKeyEditor.props('modelValue') as Array<Record<string, any>>
    expect(foreignKeyFormValue[0]).toMatchObject({
      local_keys: ["['local_first'] + @value: entities.site.keys"],
      remote_keys: ['@value: entities.site.columns'],
    })
    const unnestEditor = wrapper.findComponent({ name: 'UnnestEditor' })
    const unnestFormValue = unnestEditor.props('modelValue') as Record<string, any>
    expect(unnestFormValue).toMatchObject({
      id_vars: ['@value: entities.site.keys'],
      value_vars: ['manual_value', '@value: entities.site.columns'],
      keep_empty: true,
    })

    foreignKeyEditor.vm.$emit('update:modelValue', foreignKeyFormValue)
    unnestEditor.vm.$emit('update:modelValue', unnestFormValue)
    editEntityName(wrapper, 'reference_columns_edited')
    await flushPromises()
    await nextTick()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    const savedData = mockState.update.mock.calls.at(-1)?.[1].entity_data
    expect(savedData).toMatchObject({
      keys: '  @value: entities.site.keys  ',
      columns: ['@value: entities.site.columns', 'manual_column'],
      drop_duplicates: rawDropDuplicates,
      drop_empty_rows: '@value: entities.site.keys + @value: entities.site.columns',
      check_functional_dependency: true,
      foreign_keys: [
        {
          entity: 'site',
          local_keys: "['local_first'] + @value: entities.site.keys",
          remote_keys: ['@value: entities.site.columns'],
          how: 'left',
        },
      ],
      unnest: rawUnnest,
    })
    expect(JSON.stringify(savedData)).not.toContain('__columnListOrigins')

    const reloaded = mountEntityFormDialog({ mode: 'edit', entity: createEntity(entity.name, savedData) })
    await flushPromises()
    await nextTick()
    expect(findComboboxByLabel(reloaded, 'Columns to Check for Empty Values')?.props('modelValue')).toEqual([
      '@value: entities.site.keys + @value: entities.site.columns',
    ])
  })

  it('preserves YAML-entered scalar and list shapes through Save & Close', async () => {
    const entity = createEntity('yaml_references', {
      type: 'entity',
      public_id: 'yaml_references_id',
      keys: ['existing_key'],
      columns: ['existing_column'],
    })
    mockState.update.mockResolvedValue({ name: entity.name, warnings: [] })
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()
    await nextTick()

    const yamlEditor = wrapper.findComponent({ name: 'YamlEditor' })
    const editedYaml = `name: yaml_references
type: entity
system_id: system_id
public_id: yaml_references_id
keys: "@value: entities.site.keys + @value: entities.site.columns"
columns: "['literal_first'] + @value: entities.site.keys"
drop_duplicates: "@value: entities.site.columns"
drop_empty_rows:
  - "@value: entities.site.keys"
foreign_keys:
  - entity: site
    local_keys: "['local_first'] + @value: entities.site.keys"
    remote_keys:
      - "@value: entities.site.columns"
    how: left
unnest:
  id_vars: "@value: entities.site.keys"
  value_vars:
    - manual_value
    - "@value: entities.site.columns"
  var_name: variable
  value_name: value
`
    yamlEditor.vm.$emit('update:modelValue', editedYaml)
    yamlEditor.vm.$emit('change', editedYaml)
    await flushPromises()
    await nextTick()

    expect(findComboboxByLabel(wrapper, 'Business Keys *')?.props('modelValue')).toEqual([
      '@value: entities.site.keys + @value: entities.site.columns',
    ])
    expect(findComboboxByLabel(wrapper, 'Columns')?.props('modelValue')).toEqual([
      "['literal_first'] + @value: entities.site.keys",
    ])
    expect(findComboboxByLabel(wrapper, 'Deduplication Columns')?.props('modelValue')).toEqual([
      '@value: entities.site.columns',
    ])

    const unnestEditor = wrapper.findComponent({ name: 'UnnestEditor' })
    unnestEditor.vm.$emit('update:modelValue', unnestEditor.props('modelValue'))
    editEntityName(wrapper, 'yaml_references_edited')
    await flushPromises()
    await nextTick()

    const saveAndCloseButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save & Close')
    expect(saveAndCloseButton?.element.disabled).toBe(false)
    await saveAndCloseButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith(
      'yaml_references',
      expect.objectContaining({
        entity_data: expect.objectContaining({
          keys: '@value: entities.site.keys + @value: entities.site.columns',
          columns: "['literal_first'] + @value: entities.site.keys",
          drop_duplicates: '@value: entities.site.columns',
          drop_empty_rows: ['@value: entities.site.keys'],
          foreign_keys: [
            {
              entity: 'site',
              local_keys: "['local_first'] + @value: entities.site.keys",
              remote_keys: ['@value: entities.site.columns'],
              how: 'left',
            },
          ],
          unnest: {
            id_vars: '@value: entities.site.keys',
            value_vars: ['manual_value', '@value: entities.site.columns'],
            var_name: 'variable',
            value_name: 'value',
          },
        }),
      })
    )
    const savedData = mockState.update.mock.calls.at(-1)?.[1].entity_data
    expect(JSON.stringify(savedData)).not.toContain('__columnListOrigins')
  })

  it('uses values from the last successful save as the next shape-preservation origin', async () => {
    const entity = createEntity('saved_origin', {
      type: 'entity',
      public_id: 'saved_origin_id',
      keys: ['saved_key'],
      columns: ['@value: entities.site.columns'],
    })
    mockState.update.mockResolvedValue({ name: entity.name, warnings: [] })
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()
    await nextTick()

    const columns = findComboboxByLabel(wrapper, 'Columns')
    columns!.vm.$emit('update:modelValue', ['@value: entities.site.updated_columns'])
    editEntityName(wrapper, 'saved_origin_first_edit')
    await flushPromises()
    await nextTick()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    await saveButton!.trigger('click')
    await flushPromises()
    expect(mockState.update.mock.calls.at(-1)?.[1].entity_data.columns).toBe('@value: entities.site.updated_columns')

    columns!.vm.$emit('update:modelValue', ['@value: entities.site.columns'])
    editEntityName(wrapper, 'saved_origin_second_edit')
    await flushPromises()
    await nextTick()
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update.mock.calls.at(-1)?.[1].entity_data.columns).toBe('@value: entities.site.columns')
  })

  it('shows the branches tab when type changes to merged, enables it in create mode, and hides append', async () => {
    const wrapper = mountEntityFormDialog()

    expect(findTabByValue(wrapper, 'branches')).toBeUndefined()
    expect(findTabByValue(wrapper, 'append')).toBeTruthy()

    const typeSelect = findSelectByLabel(wrapper, 'Type *')
    expect(typeSelect).toBeTruthy()

    typeSelect!.vm.$emit('update:modelValue', 'merged')
    await flushPromises()
    await nextTick()

    const branchesTab = findTabByValue(wrapper, 'branches')
    expect(branchesTab).toBeTruthy()
    expect(branchesTab?.props('disabled')).toBe(false)
    expect(findTabByValue(wrapper, 'append')).toBeUndefined()
    expect(wrapper.text()).toContain('Merged entity configuration')
    expect(wrapper.text()).toContain('Use the Branches tab as the primary configuration surface')
  })

  it('renders the branches tab enabled for an existing merged entity in edit mode', async () => {
    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: mergedEntity,
    })

    await flushPromises()
    await nextTick()

    const branchesTab = findTabByValue(wrapper, 'branches')
    expect(branchesTab).toBeTruthy()
    expect(branchesTab?.props('disabled')).toBe(false)
  })

  it('enables the source field when switching an existing merged entity to the derived entity type', async () => {
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: mergedEntity })
    await flushPromises()
    await nextTick()

    const findSourceField = () =>
      wrapper
        .findAllComponents({ name: 'VAutocomplete' })
        .find((component) => component.props('label') === 'Source Entity')

    // A merged entity has no top-level source field.
    expect(findSourceField()).toBeUndefined()

    const typeSelect = findSelectByLabel(wrapper, 'Type *')
    expect(typeSelect).toBeTruthy()
    typeSelect!.vm.$emit('update:modelValue', 'entity')
    await flushPromises()
    await nextTick()

    const sourceField = findSourceField()
    expect(sourceField).toBeTruthy()
    expect(sourceField?.props('disabled')).not.toBe(true)
  })

  it('keeps the source field locked for an already-derived entity in edit mode', async () => {
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: sourceEntities[0]! })
    await flushPromises()
    await nextTick()

    const sourceField = wrapper
      .findAllComponents({ name: 'VAutocomplete' })
      .find((component) => component.props('label') === 'Source Entity')

    expect(sourceField).toBeTruthy()
    expect(sourceField?.props('disabled')).toBe(true)
  })

  it('focuses the entity name field when the create dialog opens', async () => {
    const wrapper = mountEntityFormDialog({ modelValue: false, mode: 'create' })
    await flushPromises()

    const nameField = wrapper
      .findAllComponents({ name: 'VTextField' })
      .find((component) => component.props('label') === 'Entity Name *')
    expect(nameField).toBeTruthy()

    const focusSpy = vi.spyOn(nameField!.find('input').element as HTMLInputElement, 'focus')

    await wrapper.setProps({ modelValue: true })
    await flushPromises()
    await nextTick()

    expect(focusSpy).toHaveBeenCalled()
  })

  it('does not move focus to the entity name field when the edit dialog opens', async () => {
    const wrapper = mountEntityFormDialog({ modelValue: false, mode: 'edit', entity: sourceEntities[0]! })
    await flushPromises()

    const nameField = wrapper
      .findAllComponents({ name: 'VTextField' })
      .find((component) => component.props('label') === 'Entity Name *')
    expect(nameField).toBeTruthy()

    const focusSpy = vi.spyOn(nameField!.find('input').element as HTMLInputElement, 'focus')

    await wrapper.setProps({ modelValue: true })
    await flushPromises()
    await nextTick()

    expect(focusSpy).not.toHaveBeenCalled()
  })

  it('maps operation-specific candidates and saves values absent from suggestions', async () => {
    mockState.update.mockResolvedValue({ warnings: [] })
    mockState.columnAvailability = {
      columns: ['server_column'],
      business_keys: ['server_key'],
      replacements: ['replacement_column'],
      drop_duplicates: ['dedupe_column'],
      drop_empty_rows: ['empty_check_column'],
      extra_columns: { sources: ['extra_source_column'] },
      filters: { extract: ['filter_column'] },
      foreign_keys: [
        {
          index: 0,
          entity: 'abundance_source',
          local_keys_before_unnest: ['child_key'],
          local_keys_after_unnest: ['measurement_type'],
          remote_keys: ['sample_name', 'system_id'],
          extra_column_sources: ['source_value'],
        },
      ],
      unnest: { id_vars: ['id_candidate'], value_vars: ['value_candidate'] },
    }
    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: mergedEntity,
    })

    await flushPromises()
    await nextTick()

    const columnsCombobox = findComboboxByLabel(wrapper, 'Columns')
    const keysCombobox = findComboboxByLabel(wrapper, 'Business Keys *')
    const dedupeCombobox = findComboboxByLabel(wrapper, 'Deduplication Columns')
    const emptyRowsCombobox = findComboboxByLabel(wrapper, 'Columns to Check for Empty Values')
    const unnestEditor = wrapper.findComponent({ name: 'UnnestEditor' })
    const extraColumnsEditor = wrapper.findComponent({ name: 'ExtraColumnsEditor' })
    const replacementsEditor = wrapper.findComponent({ name: 'ReplacementsEditor' })

    expect(columnsCombobox).toBeTruthy()
    expect(columnsCombobox?.props('items')).toEqual(['server_column'])
    expect(keysCombobox?.props('items')).toEqual(['server_key'])
    expect(dedupeCombobox?.props('items')).toEqual(['dedupe_column'])
    expect(emptyRowsCombobox?.props('items')).toEqual(['empty_check_column'])
    expect(unnestEditor.props('idVarColumns')).toEqual(['id_candidate'])
    expect(unnestEditor.props('valueVarColumns')).toEqual(['value_candidate'])
    expect(extraColumnsEditor.props('availableColumns')).toEqual(['extra_source_column'])
    expect(replacementsEditor.props('availableColumns')).toEqual(['replacement_column'])
    expect(wrapper.text()).toContain('Available post-merge: columns')

    const foreignKeyEditor = wrapper.findComponent({ name: 'ForeignKeyEditor' })
    expect(foreignKeyEditor.props('columnCandidates')).toEqual(mockState.columnAvailability.foreign_keys)
    foreignKeyEditor.vm.$emit('update:modelValue', [
      { entity: 'abundance_source', local_keys: ['sample_name'], remote_keys: ['sample_name'] },
    ])
    columnsCombobox!.vm.$emit('update:modelValue', ['unlisted_column'])
    await flushPromises()
    await nextTick()

    const latestRequest = mockState.refreshColumnAvailability.mock.calls.at(-1)
    expect(latestRequest?.[2].entity_draft.foreign_keys).toEqual([
      expect.objectContaining({ entity: 'abundance_source' }),
    ])
    expect(latestRequest?.[2].entity_draft.columns).toEqual(['unlisted_column'])
    expect(columnsCombobox?.props('modelValue')).toEqual(['unlisted_column'])

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith(
      'analysis_entity',
      expect.objectContaining({
        entity_data: expect.objectContaining({ columns: ['unlisted_column'] }),
      })
    )
  })

  it('does not treat a business key as a reserved extra-column name', async () => {
    // Regression for #506: an extra column may also be used as a business key.
    const entity = createEntity('sample', {
      type: 'entity',
      public_id: 'sample_id',
      columns: ['sample_name'],
      keys: ['sample_name', 'derived_key'],
      extra_columns: { derived_key: 'sample_name' },
      unnest: {
        id_vars: ['sample_name'],
        value_vars: ['reading'],
        var_name: 'measurement_type',
        value_name: 'measurement_value',
      },
    })

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity,
    })

    await flushPromises()
    await nextTick()

    const reservedNames = wrapper.findComponent({ name: 'ExtraColumnsEditor' }).props('reservedNames') as string[]

    // Real result columns stay reserved.
    expect(reservedNames).toEqual(
      expect.arrayContaining(['system_id', 'sample_id', 'sample_name', 'measurement_type', 'measurement_value'])
    )
    // The business key must not be reserved, because keys add no result column.
    expect(reservedNames).not.toContain('derived_key')

    const diagnostics = getExtraColumnDiagnostics([{ column: 'derived_key', source: 'sample_name' }], 0, {
      reservedNames,
      availableColumns: ['sample_name'],
    })
    expect(diagnostics.some((diagnostic) => diagnostic.severity === 'error')).toBe(false)
  })

  it('supports toggling preview between merged rows and branch source rows', async () => {
    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: mergedEntity,
    })

    await flushPromises()
    await nextTick()

    const previewTargetSelect = findSelectByLabel(wrapper, 'Preview')
    expect(previewTargetSelect).toBeTruthy()

    previewTargetSelect!.vm.$emit('update:modelValue', 'source')
    await flushPromises()
    await nextTick()

    expect(mockState.previewEntity).toHaveBeenCalledWith('arbodat', 'abundance_source', 100)
    expect(wrapper.text()).toContain('Previewing source rows for abundance')
    expect(wrapper.text()).toContain('abundance_source')
  })

  it('loads fixed entity column_types into the grid and persists updates on save', async () => {
    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: fixedEntity,
    })

    await flushPromises()
    await nextTick()

    const fixedValuesGrid = wrapper.findComponent({ name: 'FixedValuesGrid' })
    expect(fixedValuesGrid.exists()).toBe(true)
    expect(fixedValuesGrid.props('columnTypes')).toEqual({
      label: 'string',
      created_at: 'date',
    })

    fixedValuesGrid.vm.$emit('update:columnTypes', {
      label: 'int',
      created_at: 'date',
    })

    await flushPromises()
    await nextTick()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton).toBeTruthy()

    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith('method', {
      entity_data: expect.objectContaining({
        column_types: {
          label: 'int',
          created_at: 'date',
        },
      }),
    })
  })

  it('hydrates the fixed grid with backend metadata order, not business-key order', async () => {
    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: orderedFixedEntity,
    })

    await flushPromises()
    await nextTick()

    const fixedValuesGrid = wrapper.findComponent({ name: 'FixedValuesGrid' })
    expect(fixedValuesGrid.props('columns')).toEqual(['system_id', 'method_id', 'created_at', 'label'])
    expect(fixedValuesGrid.props('modelValue')).toEqual([[1, 53, '2026-05-19', 'Sampling']])
  })

  it('does not create a fixed grid column when a business key has no produced field', async () => {
    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: orderedFixedEntity,
    })

    await flushPromises()
    await nextTick()

    const keysCombobox = findComboboxByLabel(wrapper, 'Business Keys *')
    expect(keysCombobox).toBeTruthy()
    keysCombobox!.vm.$emit('update:modelValue', ['label', 'ghost_key'])
    await flushPromises()
    await nextTick()

    const fixedValuesGrid = wrapper.findComponent({ name: 'FixedValuesGrid' })
    expect(fixedValuesGrid.props('columns')).toEqual(['system_id', 'method_id', 'created_at', 'label'])
    expect(fixedValuesGrid.props('modelValue')).toEqual([[1, 53, '2026-05-19', 'Sampling']])
  })

  it('derives fixed grid columns from stored columns, not keys, when metadata is absent', async () => {
    const legacyFixedEntity = createEntity('legacy_fixed', {
      type: 'fixed',
      public_id: 'legacy_id',
      keys: ['ghost_key'],
      columns: ['sample_name', 'abundance_value'],
      values: [['S1', 12]],
    })

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: legacyFixedEntity,
    })

    await flushPromises()
    await nextTick()

    const fixedValuesGrid = wrapper.findComponent({ name: 'FixedValuesGrid' })
    expect(fixedValuesGrid.props('columns')).toEqual(['system_id', 'legacy_id', 'sample_name', 'abundance_value'])
    expect(fixedValuesGrid.props('columns')).not.toContain('ghost_key')
    expect(fixedValuesGrid.props('modelValue')).toEqual([[1, null, 'S1', 12]])
  })

  it('saves fixed config as produced data columns and external values in full order', async () => {
    mockState.getValues.mockResolvedValue({
      columns: ['system_id', 'method_id', 'created_at', 'label'],
      values: [[1, 53, '2026-05-19', 'Sampling']],
      format: 'parquet',
      row_count: 1,
      etag: 'values-etag',
    })
    mockState.updateValues.mockResolvedValue({ etag: 'new-values-etag' })
    mockState.update.mockResolvedValue(createEntity('method', externalFixedEntity.entity_data))

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: externalFixedEntity,
    })

    await flushPromises()
    await nextTick()

    const fixedValuesGrid = wrapper.findComponent({ name: 'FixedValuesGrid' })
    fixedValuesGrid.vm.$emit('update:modelValue', [[1, 53, '2026-05-20', 'Sampling']])
    await flushPromises()
    await nextTick()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith('method', {
      entity_data: expect.objectContaining({
        columns: ['created_at', 'label'],
      }),
    })
    expect(mockState.updateValues).toHaveBeenCalledWith(
      'arbodat',
      'method',
      {
        columns: ['system_id', 'method_id', 'created_at', 'label'],
        values: [[1, 53, '2026-05-20', 'Sampling']],
      },
      'values-etag'
    )
  })

  it('keeps fixed columns and positional values in order after an unrelated edit', async () => {
    mockState.update.mockResolvedValue({ name: 'method_edited', warnings: [] })

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: orderedFixedEntity })
    await flushPromises()
    await nextTick()

    expect(findComboboxByLabel(wrapper, 'Columns')?.props('modelValue')).toEqual(['created_at', 'label'])
    const fixedValuesGrid = wrapper.findComponent({ name: 'FixedValuesGrid' })
    expect(fixedValuesGrid.props('columns')).toEqual(['system_id', 'method_id', 'created_at', 'label'])
    expect(fixedValuesGrid.props('modelValue')).toEqual([[1, 53, '2026-05-19', 'Sampling']])

    editEntityName(wrapper, 'method_edited')
    await flushPromises()
    await nextTick()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith(
      'method',
      expect.objectContaining({
        new_name: 'method_edited',
        entity_data: expect.objectContaining({
          columns: ['created_at', 'label'],
          values: [[1, 53, '2026-05-19', 'Sampling']],
        }),
      })
    )
  })

  it('saves external values in full order through Save & Close', async () => {
    mockState.getValues.mockResolvedValue({
      columns: ['system_id', 'method_id', 'created_at', 'label'],
      values: [[1, 53, '2026-05-19', 'Sampling']],
      format: 'parquet',
      row_count: 1,
      etag: 'values-etag',
    })
    mockState.updateValues.mockResolvedValue({ etag: 'new-values-etag' })
    mockState.update.mockResolvedValue(createEntity('method', externalFixedEntity.entity_data))

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: externalFixedEntity,
    })

    await flushPromises()
    await nextTick()

    const fixedValuesGrid = wrapper.findComponent({ name: 'FixedValuesGrid' })
    fixedValuesGrid.vm.$emit('update:modelValue', [[1, 53, '2026-05-20', 'Sampling']])
    await flushPromises()
    await nextTick()

    const saveAndCloseButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save & Close')
    expect(saveAndCloseButton?.element.disabled).toBe(false)
    await saveAndCloseButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith('method', {
      entity_data: expect.objectContaining({
        columns: ['created_at', 'label'],
      }),
    })
    expect(mockState.updateValues).toHaveBeenCalledWith(
      'arbodat',
      'method',
      {
        columns: ['system_id', 'method_id', 'created_at', 'label'],
        values: [[1, 53, '2026-05-20', 'Sampling']],
      },
      'values-etag'
    )
  })

  it('round-trips a materialized fixed entity through open, edit, save, and reopen', async () => {
    const fullOrder = ['system_id', 'method_id', 'created_at', 'label']
    const savedEntity: EntityResponse = {
      name: 'method',
      etag: 'etag-method-saved',
      fixed_schema: externalFixedEntity.fixed_schema,
      entity_data: { ...externalFixedEntity.entity_data },
    }

    mockState.getValues.mockResolvedValueOnce({
      columns: fullOrder,
      values: [[1, 53, '2026-05-19', 'Sampling']],
      format: 'parquet',
      row_count: 1,
      etag: 'values-etag',
    })
    mockState.updateValues.mockResolvedValue({ etag: 'new-values-etag' })
    mockState.update.mockResolvedValue(savedEntity)

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: externalFixedEntity,
    })

    await flushPromises()
    await nextTick()

    // Open: the grid hydrates from backend metadata in the authoritative order.
    const fixedValuesGrid = wrapper.findComponent({ name: 'FixedValuesGrid' })
    expect(fixedValuesGrid.props('columns')).toEqual(fullOrder)
    expect(fixedValuesGrid.props('modelValue')).toEqual([[1, 53, '2026-05-19', 'Sampling']])

    // Edit one named field: created_at changes, the label value stays with its own column.
    fixedValuesGrid.vm.$emit('update:modelValue', [[1, 53, '2026-05-20', 'Sampling']])
    await flushPromises()
    await nextTick()

    const keysCombobox = findComboboxByLabel(wrapper, 'Business Keys *')
    expect(keysCombobox).toBeTruthy()
    keysCombobox!.vm.$emit('update:modelValue', ['label', 'ghost_key'])
    await flushPromises()
    await nextTick()

    // Selecting a key that no producer creates must not add a grid position.
    expect(fixedValuesGrid.props('columns')).toEqual(fullOrder)

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    // The saved config keeps produced columns only; the request uses full order and the GET ETag.
    expect(mockState.update).toHaveBeenCalledWith('method', {
      entity_data: expect.objectContaining({
        columns: ['created_at', 'label'],
      }),
    })
    expect(mockState.updateValues).toHaveBeenCalledWith(
      'arbodat',
      'method',
      {
        columns: fullOrder,
        values: [[1, 53, '2026-05-20', 'Sampling']],
      },
      'values-etag'
    )

    // Reopen from the returned entity and the values the backend would return next.
    mockState.getValues.mockResolvedValueOnce({
      columns: fullOrder,
      values: [[1, 53, '2026-05-20', 'Sampling']],
      format: 'parquet',
      row_count: 1,
      etag: 'new-values-etag',
    })
    const reopened = mountEntityFormDialog({
      mode: 'edit',
      entity: savedEntity,
    })

    await flushPromises()
    await nextTick()

    const reopenedGrid = reopened.findComponent({ name: 'FixedValuesGrid' })
    expect(reopenedGrid.props('columns')).toEqual(fullOrder)
    expect(reopenedGrid.props('modelValue')).toEqual([[1, 53, '2026-05-20', 'Sampling']])
  })

  it('remaps inline fixed values by name when a produced column is reordered', async () => {
    mockState.update.mockResolvedValue(createEntity('method', orderedFixedEntity.entity_data))

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: orderedFixedEntity,
    })

    await flushPromises()
    await nextTick()

    const columnsCombobox = findComboboxByLabel(wrapper, 'Columns')
    expect(columnsCombobox).toBeTruthy()
    columnsCombobox!.vm.$emit('update:modelValue', ['label', 'created_at'])
    await flushPromises()
    await nextTick()

    // Values follow their column names, not their old positions.
    const fixedValuesGrid = wrapper.findComponent({ name: 'FixedValuesGrid' })
    expect(fixedValuesGrid.props('columns')).toEqual(['system_id', 'method_id', 'label', 'created_at'])
    expect(fixedValuesGrid.props('modelValue')).toEqual([[1, 53, 'Sampling', '2026-05-19']])

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith('method', {
      entity_data: expect.objectContaining({
        columns: ['label', 'created_at'],
        values: [[1, 53, 'Sampling', '2026-05-19']],
      }),
    })
  })

  it('rejects external fixed values whose columns do not match the active full order', async () => {
    const updateCallsBefore = mockState.update.mock.calls.length
    const valuesUpdateCallsBefore = mockState.updateValues.mock.calls.length

    mockState.getValues.mockResolvedValue({
      columns: ['system_id', 'method_id', 'label', 'created_at'],
      values: [[1, 53, 'Sampling', '2026-05-19']],
      format: 'parquet',
      row_count: 1,
      etag: 'bad-etag',
    })

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: externalFixedEntity,
    })

    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('do not match the entity schema')
    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    // Save is disabled while the fetched order is unsafe, so no write can be sent.
    expect(saveButton?.element.disabled).toBe(true)
    expect(mockState.update.mock.calls.length).toBe(updateCallsBefore)
    expect(mockState.updateValues.mock.calls.length).toBe(valuesUpdateCallsBefore)
  })

  it('submits an edited entity name as a guarded rename', async () => {
    const sourceEntity = sourceEntities[0]!
    const renamedEntity = createEntity('renamed_source', sourceEntity.entity_data)
    const warning =
      "Entity 'renamed_source' was saved, but its note could not be moved from 'abundance_source'. The note remains under the old name."
    mockState.update.mockResolvedValue({ ...renamedEntity, warnings: [warning] })
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: sourceEntity })

    await flushPromises()
    const nameField = wrapper
      .findAllComponents({ name: 'VTextField' })
      .find((component) => component.props('label') === 'Entity Name *')
    expect(nameField).toBeTruthy()
    expect(nameField?.props('disabled')).not.toBe(true)
    nameField!.vm.$emit('update:modelValue', 'renamed_source')
    await flushPromises()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith('abundance_source', {
      entity_data: expect.any(Object),
      new_name: 'renamed_source',
    })
    expect(mockState.showWarning).toHaveBeenCalledWith(warning)
    expect(wrapper.emitted('saved')?.at(-1)).toEqual(['renamed_source'])
  })

  it('shows dependent entities and manual rename guidance on a rename conflict', async () => {
    mockState.update.mockRejectedValue({
      response: {
        data: {
          detail: {
            message: "Cannot rename entity 'abundance_source' because other entities refer to it.",
            context: { conflict_type: 'entity_has_dependents', dependent_entities: ['analysis_entity'] },
          },
        },
      },
    })
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: sourceEntities[0]! })

    await flushPromises()
    const nameField = wrapper
      .findAllComponents({ name: 'VTextField' })
      .find((component) => component.props('label') === 'Entity Name *')
    nameField!.vm.$emit('update:modelValue', 'renamed_source')
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text().trim() === 'Save')!
      .trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('analysis_entity')
    expect(wrapper.text()).toContain('update the matching task sidecar keys')
  })

  it('syncs corrected YAML before saving when the previous YAML was invalid', async () => {
    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: sourceEntities[0],
      initialTab: 'yaml',
    })

    await flushPromises()
    await nextTick()

    const columnsCombobox = findComboboxByLabel(wrapper, 'Columns')
    columnsCombobox!.vm.$emit('update:modelValue', ['sample_name', 'form_only_edit'])
    await flushPromises()

    const yamlEditor = wrapper.findComponent({ name: 'YamlEditor' })
    yamlEditor.vm.$emit('update:modelValue', 'name: [broken')
    yamlEditor.vm.$emit('change', 'name: [broken')
    yamlEditor.vm.$emit('validate', false, 'Invalid YAML')
    await flushPromises()

    const correctedYaml = [
      'name: abundance_source',
      'type: entity',
      'public_id: abundance_id',
      'keys:',
      '  - sample_name',
      'columns:',
      '  - sample_name',
      '  - yaml_corrected',
    ].join('\n')
    yamlEditor.vm.$emit('update:modelValue', correctedYaml)
    yamlEditor.vm.$emit('change', correctedYaml)
    yamlEditor.vm.$emit('validate', true)
    await flushPromises()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton).toBeTruthy()
    expect(saveButton!.element.disabled).toBe(false)

    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith('abundance_source', {
      entity_data: expect.objectContaining({
        columns: ['sample_name', 'yaml_corrected'],
      }),
    })
  })

  it('syncs the entity store cache after materialization reload', async () => {
    const freshEntity = createEntity('abundance_source', {
      type: 'fixed',
      public_id: 'abundance_id',
      columns: ['sample_name', 'abundance_value'],
      keys: ['sample_name'],
      values: [[1, 2]],
      materialized: { enabled: true },
    })
    freshEntity.etag = 'fresh-materialized-etag'
    mockState.getEntity.mockResolvedValue(freshEntity)

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: sourceEntities[0],
    })

    await flushPromises()

    wrapper.findComponent({ name: 'MaterializeDialog' }).vm.$emit('materialized')
    await flushPromises()

    expect(mockState.getEntity).toHaveBeenCalledWith('arbodat', 'abundance_source')
    expect(mockState.syncCachedEntity).toHaveBeenCalledWith(freshEntity)
  })

  it('syncs the entity store cache after unmaterialization reload', async () => {
    const materializedEntity = createEntity('abundance_source', {
      type: 'fixed',
      public_id: 'abundance_id',
      columns: ['sample_name', 'abundance_value'],
      keys: ['sample_name'],
      values: [[1, 2]],
      materialized: { enabled: true },
    })

    const freshEntity = createEntity('abundance_source', {
      type: 'sql',
      public_id: 'abundance_id',
      columns: ['sample_name', 'abundance_value'],
      keys: ['sample_name'],
      query: 'select * from abundance',
    })
    freshEntity.etag = 'fresh-unmaterialized-etag'
    mockState.getEntity.mockResolvedValue(freshEntity)

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: materializedEntity,
    })

    await flushPromises()

    wrapper.findComponent({ name: 'UnmaterializeDialog' }).vm.$emit('unmaterialized', ['abundance_source'])
    await flushPromises()

    expect(mockState.getEntity).toHaveBeenCalledWith('arbodat', 'abundance_source')
    expect(mockState.syncCachedEntity).toHaveBeenCalledWith(freshEntity)
  })

  it('reports a partial save and offers retry when the inline save returns pending mapping', async () => {
    const pending = makeMappingPending()
    mockState.update.mockResolvedValue({
      ...createEntity('method', orderedFixedEntity.entity_data),
      mapping_sync: pending,
    })

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: orderedFixedEntity })
    await flushPromises()
    await nextTick()

    const columnsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns')
    columnsCombobox!.vm.$emit('update:modelValue', ['label', 'created_at'])
    await flushPromises()
    await nextTick()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    await saveButton!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Rows saved; mapping changes pending')
    expect(wrapper.text()).not.toContain('Saved successfully')
    expect(wrapper.emitted('saved')?.at(-1)).toEqual(['method', true])
    expect(wrapper.findAll('button').some((button) => button.text().trim() === 'Retry mapping')).toBe(true)
    expect(mockState.setMappingSyncPending).toHaveBeenCalledWith(pending)
  })

  it('retries only the pending mapping changes without resubmitting rows', async () => {
    const pending = makeMappingPending()
    mockState.update.mockResolvedValue({
      ...createEntity('method', orderedFixedEntity.entity_data),
      mapping_sync: pending,
    })
    mockState.retryFixedEntityMapping.mockResolvedValue({
      status: 'applied',
      rows_saved: true,
      changed: true,
      sidecar_version: 'sidecar-v2',
      changed_keys: [],
    })

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: orderedFixedEntity })
    await flushPromises()
    await nextTick()

    const columnsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns')
    columnsCombobox!.vm.$emit('update:modelValue', ['label', 'created_at'])
    await flushPromises()
    await nextTick()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    await saveButton!.trigger('click')
    await flushPromises()

    const updateCallsAfterSave = mockState.update.mock.calls.length
    const valuesCallsAfterSave = mockState.updateValues.mock.calls.length

    const retryButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Retry mapping')
    await retryButton!.trigger('click')
    await flushPromises()

    expect(mockState.retryFixedEntityMapping).toHaveBeenCalledTimes(1)
    expect(mockState.retryFixedEntityMapping).toHaveBeenCalledWith('arbodat', 'method', pending)
    expect(mockState.update.mock.calls.length).toBe(updateCallsAfterSave)
    expect(mockState.updateValues.mock.calls.length).toBe(valuesCallsAfterSave)
    expect(wrapper.text()).not.toContain('Rows saved; mapping changes pending')
    expect(wrapper.text()).toContain('Saved successfully')
  })

  it('shows the changed keys when a retry reports a conflict', async () => {
    const pending = makeMappingPending()
    mockState.update.mockResolvedValue({
      ...createEntity('method', orderedFixedEntity.entity_data),
      mapping_sync: pending,
    })
    mockState.retryFixedEntityMapping.mockRejectedValue({
      response: { status: 409, data: { detail: { context: { changed_keys: ['Sampling'] } } } },
    })

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: orderedFixedEntity })
    await flushPromises()
    await nextTick()

    const columnsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns')
    columnsCombobox!.vm.$emit('update:modelValue', ['label', 'created_at'])
    await flushPromises()
    await nextTick()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    await saveButton!.trigger('click')
    await flushPromises()

    const retryButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Retry mapping')
    await retryButton!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Sampling')
    expect(wrapper.text()).toContain('Rows saved; mapping changes pending')
  })

  it('keeps the dialog open when Save & Close leaves mapping changes pending', async () => {
    const pending = makeMappingPending()
    mockState.update.mockResolvedValue({
      ...createEntity('method', orderedFixedEntity.entity_data),
      mapping_sync: pending,
    })

    const wrapper = mountEntityFormDialog({ mode: 'edit', entity: orderedFixedEntity })
    await flushPromises()
    await nextTick()

    const columnsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns')
    columnsCombobox!.vm.$emit('update:modelValue', ['label', 'created_at'])
    await flushPromises()
    await nextTick()

    const saveAndCloseButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save & Close')
    await saveAndCloseButton!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Rows saved; mapping changes pending')
    expect(wrapper.emitted('saved')?.at(-1)).toEqual(['method', true])
    const closeEmits = (wrapper.emitted('update:modelValue') ?? []).map((args) => args[0])
    expect(closeEmits).not.toContain(false)
  })
})
