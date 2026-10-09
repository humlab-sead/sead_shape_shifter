import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import type { ColumnAvailabilityResponse, EntityResponse } from '@/api/entities'
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
  introspectQueryColumns: vi.fn(async () => []),
  syncCachedEntity: vi.fn(),
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
  }),
}))

vi.mock('@/api', () => ({
  api: {
    entities: {
      get: mockState.getEntity,
      getValues: mockState.getValues,
      updateValues: mockState.updateValues,
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
  YamlEditor: {
    name: 'YamlEditor',
    props: ['modelValue'],
    template: '<div data-testid="yaml-editor" />',
  },
  SqlEditor: { template: '<div data-testid="sql-editor" />' },
  ForeignKeyEditor: {
    name: 'ForeignKeyEditor',
    props: ['modelValue', 'columnCandidates'],
    template: '<div data-testid="foreign-key-editor" />',
  },
  FiltersEditor: { template: '<div data-testid="filters-editor" />' },
  UnnestEditor: {
    name: 'UnnestEditor',
    props: ['idVarColumns', 'valueVarColumns'],
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
    mockState.syncCachedEntity.mockReset()
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

    const columnsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns')
    const keysCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Business Keys *')
    const dedupeCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Deduplication Columns')
    const emptyRowsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns to Check for Empty Values')
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

    const keysCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Business Keys *')
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

  it('remaps inline fixed values by name when a produced column is reordered', async () => {
    mockState.update.mockResolvedValue(createEntity('method', orderedFixedEntity.entity_data))

    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: orderedFixedEntity,
    })

    await flushPromises()
    await nextTick()

    const columnsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns')
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
    expect(saveButton?.element.disabled).toBe(true)
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

    const columnsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns')
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
})
