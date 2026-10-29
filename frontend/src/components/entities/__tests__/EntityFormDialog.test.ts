import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick, type Component } from 'vue'
import { createVuetify } from 'vuetify'
import { load as loadYaml } from 'js-yaml'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import type { ColumnAvailabilityResponse, EntityResponse } from '@/api/entities'
import type { TargetModelEntityOption } from '@/api/projects'
import EntityFormDialog from '../EntityFormDialog.vue'
import { getExtraColumnDiagnostics } from '../extraColumnsEditorUtils'

const mockState = vi.hoisted(() => ({
  entities: [] as EntityResponse[],
  referenceEntities: null as EntityResponse[] | null,
  currentProjectName: 'arbodat',
  getCompletedEntitiesFor: vi.fn(),
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
  getTargetModelEntityOptions: vi.fn(),
  getEntityTypes: vi.fn(),
  getValidDirectives: vi.fn(async () => []),
  getEntity: vi.fn(),
  getValues: vi.fn(),
  updateValues: vi.fn(),
  retryFixedEntityMapping: vi.fn(),
  setMappingSyncPending: vi.fn(),
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
    currentProjectName: mockState.currentProjectName,
  }),
  useEntityStore: () => ({
    overlayInitialTab: 'form',
    syncCachedEntity: mockState.syncCachedEntity,
    getCompletedEntitiesFor: mockState.getCompletedEntitiesFor,
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
    projects: {
      getTargetModelEntityOptions: mockState.getTargetModelEntityOptions,
    },
    dataSources: {
      getEntityTypes: mockState.getEntityTypes,
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
    props: ['modelValue', 'location', 'offset', 'height'],
    template:
      '<div class="v-dialog-stub" :data-location="location" :data-offset="offset" :data-height="height"><slot /></div>',
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
    props: ['modelValue', 'label', 'items', 'disabled', 'clearable', 'loading', 'itemTitle', 'itemValue'],
    template: '<div class="v-autocomplete-stub" :data-label="label" :data-disabled="String(disabled)"><slot /></div>',
  },
  VCombobox: {
    name: 'VCombobox',
    props: ['modelValue', 'label', 'items', 'disabled'],
    template:
      '<div class="v-combobox-stub" :data-label="label" :data-disabled="String(disabled)"><slot v-for="(item, index) in modelValue" name="chip" :item="{ raw: item, title: item }" :props="{ closable: true }" :key="index" /><slot /></div>',
  },
  ValueReferenceChip: {
    name: 'ValueReferenceChip',
    props: ['value', 'chipProps', 'entities'],
    template: '<span data-testid="value-reference-chip">{{ value }}</span>',
  },
  VMenu: {
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: `<div>
      <slot name="activator" :props="{ onClick: () => $emit('update:modelValue', true) }" />
      <div v-if="modelValue"><slot /></div>
    </div>`,
  },
  YamlEditor: {
    name: 'YamlEditor',
    props: ['modelValue'],
    template: '<div data-testid="yaml-editor" />',
  },
  SqlEditor: { template: '<div data-testid="sql-editor" />' },
  ForeignKeyEditor: {
    name: 'ForeignKeyEditor',
    props: ['modelValue', 'columnCandidates', 'referenceEntities', 'referenceSuggestions'],
    template: '<div data-testid="foreign-key-editor" />',
  },
  FiltersEditor: { template: '<div data-testid="filters-editor" />' },
  UnnestEditor: {
    name: 'UnnestEditor',
    props: ['modelValue', 'idVarColumns', 'valueVarColumns', 'referenceEntities', 'referenceSuggestions'],
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

function mountEntityFormDialog(
  props: Partial<InstanceType<typeof EntityFormDialog>['$props']> = {},
  stubs: Record<string, boolean | Component> = childStubs
) {
  return mount(EntityFormDialog, {
    props: {
      modelValue: true,
      projectName: 'arbodat',
      mode: 'create',
      ...props,
    },
    global: {
      plugins: [vuetify],
      stubs,
    },
  })
}

function findSelectByLabel(wrapper: ReturnType<typeof mountEntityFormDialog>, label: string) {
  return wrapper.findAllComponents({ name: 'VSelect' }).find((component) => component.props('label') === label)
}

function findTabByValue(wrapper: ReturnType<typeof mountEntityFormDialog>, value: string) {
  return wrapper.findAllComponents({ name: 'VTab' }).find((component) => component.props('value') === value)
}

function findAutocompleteByLabel(wrapper: ReturnType<typeof mountEntityFormDialog>, label: string) {
  return wrapper.findAllComponents({ name: 'VAutocomplete' }).find((component) => component.props('label') === label)
}

function findComboboxItemsByLabel(wrapper: ReturnType<typeof mountEntityFormDialog>, label: string) {
  return wrapper
    .findAllComponents({ name: 'VCombobox' })
    .find((component) => component.props('label') === label)
    ?.props('items')
}

function findTextFieldByLabel(wrapper: ReturnType<typeof mountEntityFormDialog>, label: string) {
  return wrapper.findAllComponents({ name: 'VTextField' }).find((component) => component.props('label') === label)
}

function createTargetModelEntityOption(overrides: Partial<TargetModelEntityOption> = {}): TargetModelEntityOption {
  return {
    name: 'target_fact',
    role: 'fact',
    required: true,
    description: 'Target fact',
    target_table: 'tbl_target_fact',
    public_id: 'target_fact_id',
    required_columns: [],
    required_links: [],
    ...overrides,
  }
}

async function setTextFieldValue(wrapper: ReturnType<typeof mountEntityFormDialog>, label: string, value: string) {
  const field = findTextFieldByLabel(wrapper, label)
  if (!field) throw new Error(`Missing text field: ${label}`)

  field.vm.$emit('update:modelValue', value)
  await flushPromises()
  await nextTick()
}

describe('EntityFormDialog', () => {
  beforeEach(() => {
    mockState.entities = [...sourceEntities]
    mockState.referenceEntities = null
    mockState.currentProjectName = 'arbodat'
    mockState.getCompletedEntitiesFor.mockReset()
    mockState.getCompletedEntitiesFor.mockImplementation((projectName: string) =>
      mockState.currentProjectName === projectName ? mockState.referenceEntities : null
    )
    mockState.create.mockReset()
    mockState.create.mockResolvedValue(undefined)
    mockState.update.mockReset()
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
    mockState.getTargetModelEntityOptions.mockReset()
    mockState.getTargetModelEntityOptions.mockResolvedValue({ configured: false, entities: [] })
    mockState.getEntityTypes.mockReset()
    mockState.getEntityTypes.mockResolvedValue([
      { value: 'entity', title: 'Entity', subtitle: 'Derived from another entity' },
      { value: 'fixed', title: 'Fixed values', subtitle: 'Static values' },
      { value: 'sql', title: 'SQL', subtitle: 'Query a data source' },
      { value: 'csv', title: 'CSV', subtitle: 'Read a CSV file' },
    ])
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
  })

  it('loads target options when create mode opens but not in edit mode', async () => {
    mockState.getTargetModelEntityOptions.mockResolvedValue({
      configured: true,
      entities: [createTargetModelEntityOption()],
    })

    const createWrapper = mountEntityFormDialog({ modelValue: false })
    await flushPromises()
    expect(mockState.getTargetModelEntityOptions).not.toHaveBeenCalled()

    await createWrapper.setProps({ modelValue: true })
    await flushPromises()

    expect(mockState.getTargetModelEntityOptions).toHaveBeenCalledTimes(1)
    expect(mockState.getTargetModelEntityOptions).toHaveBeenCalledWith('arbodat')
    expect(findAutocompleteByLabel(createWrapper, 'Start from target model')).toBeTruthy()
    createWrapper.unmount()

    const editWrapper = mountEntityFormDialog({ mode: 'edit', entity: sourceEntities[0] })
    await flushPromises()
    expect(mockState.getTargetModelEntityOptions).toHaveBeenCalledTimes(1)
    expect(findAutocompleteByLabel(editWrapper, 'Start from target model')).toBeUndefined()
  })

  it('hides the target picker when the model is unconfigured or has no missing entities', async () => {
    const unconfiguredWrapper = mountEntityFormDialog()
    await flushPromises()
    expect(findAutocompleteByLabel(unconfiguredWrapper, 'Start from target model')).toBeUndefined()
    unconfiguredWrapper.unmount()

    mockState.getTargetModelEntityOptions.mockResolvedValue({ configured: true, entities: [] })
    const emptyWrapper = mountEntityFormDialog()
    await flushPromises()
    expect(findAutocompleteByLabel(emptyWrapper, 'Start from target model')).toBeUndefined()
  })

  it('keeps manual creation usable when no target model is configured', async () => {
    const wrapper = mountEntityFormDialog()
    await flushPromises()

    expect(findAutocompleteByLabel(wrapper, 'Start from target model')).toBeUndefined()
    await setTextFieldValue(wrapper, 'Entity Name *', 'manual_entity')
    await setTextFieldValue(wrapper, 'Public ID *', 'manual_entity_id')

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton).toBeTruthy()
    expect(saveButton!.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.create).toHaveBeenCalledTimes(1)
    expect(mockState.create).toHaveBeenCalledWith({
      name: 'manual_entity',
      entity_data: expect.objectContaining({
        type: 'entity',
        public_id: 'manual_entity_id',
      }),
    })
  })

  it('shows a safe picker error and keeps manual creation usable when options fail to load', async () => {
    mockState.getTargetModelEntityOptions.mockRejectedValue(new Error('Parser details must not be shown'))
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const wrapper = mountEntityFormDialog()
    await flushPromises()

    expect(wrapper.text()).toContain('Target-model entities could not be loaded.')
    expect(wrapper.text()).toContain('You can still create an entity manually.')
    expect(wrapper.text()).not.toContain('Parser details must not be shown')
    expect(findAutocompleteByLabel(wrapper, 'Start from target model')).toBeUndefined()

    await setTextFieldValue(wrapper, 'Entity Name *', 'manual_entity')
    await setTextFieldValue(wrapper, 'Public ID *', 'manual_entity_id')
    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.create).toHaveBeenCalledTimes(1)
    expect(mockState.create).toHaveBeenCalledWith({
      name: 'manual_entity',
      entity_data: expect.objectContaining({
        type: 'entity',
        public_id: 'manual_entity_id',
      }),
    })
    consoleError.mockRestore()
  })

  it('prefills target identity, locks the name, and preserves values when the picker is cleared', async () => {
    mockState.getTargetModelEntityOptions.mockResolvedValue({
      configured: true,
      entities: [createTargetModelEntityOption()],
    })
    const wrapper = mountEntityFormDialog()
    await flushPromises()

    const picker = findAutocompleteByLabel(wrapper, 'Start from target model')
    expect(picker).toBeTruthy()
    expect(picker?.props('clearable')).toBe('')
    picker!.vm.$emit('update:modelValue', 'target_fact')
    await flushPromises()

    const nameField = findTextFieldByLabel(wrapper, 'Entity Name *')
    const publicIdField = findTextFieldByLabel(wrapper, 'Public ID *')
    expect(nameField?.props('modelValue')).toBe('target_fact')
    expect(nameField?.props('readonly')).toBe(true)
    expect(publicIdField?.props('modelValue')).toBe('target_fact_id')
    expect(mockState.create).not.toHaveBeenCalled()
    expect(mockState.update).not.toHaveBeenCalled()

    picker!.vm.$emit('update:modelValue', null)
    await flushPromises()

    expect(picker?.props('modelValue')).toBeNull()
    expect(nameField?.props('readonly')).toBe(false)
    expect(nameField?.props('modelValue')).toBe('target_fact')
    expect(publicIdField?.props('modelValue')).toBe('target_fact_id')
  })

  it('leaves a missing target public ID for the user to enter', async () => {
    mockState.getTargetModelEntityOptions.mockResolvedValue({
      configured: true,
      entities: [createTargetModelEntityOption({ name: 'unidentified_target', public_id: null })],
    })
    const wrapper = mountEntityFormDialog()
    await flushPromises()

    const picker = findAutocompleteByLabel(wrapper, 'Start from target model')
    picker!.vm.$emit('update:modelValue', 'unidentified_target')
    await flushPromises()

    const nameField = findTextFieldByLabel(wrapper, 'Entity Name *')
    const publicIdField = findTextFieldByLabel(wrapper, 'Public ID *')
    expect(nameField?.props('modelValue')).toBe('unidentified_target')
    expect(nameField?.props('readonly')).toBe(true)
    expect(publicIdField?.props('modelValue')).toBe('')

    await setTextFieldValue(wrapper, 'Public ID *', 'unidentified_target_id')
    picker!.vm.$emit('update:modelValue', null)
    await flushPromises()

    expect(nameField?.props('readonly')).toBe(false)
    expect(publicIdField?.props('modelValue')).toBe('unidentified_target_id')
  })

  it('confirms replacement of edited identity and preserves the current selection on cancellation', async () => {
    mockState.getTargetModelEntityOptions.mockResolvedValue({
      configured: true,
      entities: [
        createTargetModelEntityOption(),
        createTargetModelEntityOption({
          name: 'second_target',
          public_id: 'second_target_id',
        }),
      ],
    })
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = mountEntityFormDialog()
    await flushPromises()

    const picker = findAutocompleteByLabel(wrapper, 'Start from target model')
    picker!.vm.$emit('update:modelValue', 'target_fact')
    await flushPromises()
    await setTextFieldValue(wrapper, 'Entity Name *', 'edited_name')
    await setTextFieldValue(wrapper, 'Public ID *', 'edited_public_id')

    picker!.vm.$emit('update:modelValue', 'second_target')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(picker?.props('modelValue')).toBe('target_fact')
    expect(findTextFieldByLabel(wrapper, 'Entity Name *')?.props('modelValue')).toBe('edited_name')
    expect(findTextFieldByLabel(wrapper, 'Public ID *')?.props('modelValue')).toBe('edited_public_id')

    confirmSpy.mockReturnValue(true)
    picker!.vm.$emit('update:modelValue', 'second_target')
    await flushPromises()

    expect(picker?.props('modelValue')).toBe('second_target')
    expect(findTextFieldByLabel(wrapper, 'Entity Name *')?.props('modelValue')).toBe('second_target')
    expect(findTextFieldByLabel(wrapper, 'Public ID *')?.props('modelValue')).toBe('second_target_id')
    expect(mockState.create).not.toHaveBeenCalled()
    expect(mockState.update).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('requires an explicit source type for selected targets and saves through the create action', async () => {
    mockState.getTargetModelEntityOptions.mockResolvedValue({
      configured: true,
      entities: [createTargetModelEntityOption()],
    })
    const wrapper = mountEntityFormDialog()
    await flushPromises()

    const picker = findAutocompleteByLabel(wrapper, 'Start from target model')
    picker!.vm.$emit('update:modelValue', 'target_fact')
    await flushPromises()

    const typeSelect = findSelectByLabel(wrapper, 'Type *')
    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(typeSelect?.props('modelValue')).toBeNull()
    expect(wrapper.text()).toContain('The default entity value does not count as a selection.')
    expect(saveButton?.element.disabled).toBe(true)
    expect(mockState.create).not.toHaveBeenCalled()

    typeSelect!.vm.$emit('update:modelValue', 'entity')
    await flushPromises()
    expect(typeSelect?.props('modelValue')).toBe('entity')
    expect(saveButton?.element.disabled).toBe(false)

    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.create).toHaveBeenCalledTimes(1)
    expect(mockState.create).toHaveBeenCalledWith({
      name: 'target_fact',
      entity_data: expect.objectContaining({
        type: 'entity',
        public_id: 'target_fact_id',
      }),
    })
    expect(mockState.update).not.toHaveBeenCalled()
  })

  it('shows target requirements as reference data without adding them to the create payload', async () => {
    mockState.getTargetModelEntityOptions.mockResolvedValue({
      configured: true,
      entities: [
        createTargetModelEntityOption({
          description: 'Target fact description',
          target_table: 'tbl_target_fact',
          required_columns: ['target_name'],
          required_links: [
            { path: ['parent'], missing_entities: ['parent'], required_when_has_new_rows: null },
            { path: ['bridge', 'destination'], missing_entities: ['bridge'], required_when_has_new_rows: null },
            {
              path: ['conditional_target'],
              missing_entities: ['conditional_target'],
              required_when_has_new_rows: 'source_entity',
            },
          ],
        }),
      ],
    })
    const wrapper = mountEntityFormDialog()
    await flushPromises()

    const picker = findAutocompleteByLabel(wrapper, 'Start from target model')
    picker!.vm.$emit('update:modelValue', 'target_fact')
    await flushPromises()

    const requirements = wrapper.find('[data-testid="target-model-requirements"]')
    const requirementText = requirements.text().replace(/\s+/g, ' ')
    expect(requirementText).toContain('Role: fact')
    expect(requirementText).toContain('Target fact description')
    expect(requirementText).toContain('tbl_target_fact')
    expect(requirementText).toContain('Required columns')
    expect(requirementText).toContain('target_name')
    expect(requirementText).toContain('Required links')
    expect(requirementText).toContain('Target: parent (not in project)')
    expect(requirementText).toContain('Path: bridge (not in project) → destination')
    expect(requirementText).toContain('Conditional')
    expect(requirementText).toContain('source_entity')
    expect(requirementText).toContain('one or more rows from source_entity for insertion')
    expect(mockState.create).not.toHaveBeenCalled()
    expect(mockState.update).not.toHaveBeenCalled()

    const columnsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns')
    const keysCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Business Keys *')
    columnsCombobox!.vm.$emit('update:modelValue', ['source_name', 'source_key'])
    keysCombobox!.vm.$emit('update:modelValue', ['source_key'])
    findSelectByLabel(wrapper, 'Type *')!.vm.$emit('update:modelValue', 'entity')
    await flushPromises()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.create).toHaveBeenCalledWith({
      name: 'target_fact',
      entity_data: expect.objectContaining({
        type: 'entity',
        columns: ['source_name', 'source_key'],
        keys: ['source_key'],
      }),
    })
    expect(mockState.create.mock.calls[0]?.[0].entity_data).not.toHaveProperty('foreign_keys')
    expect(mockState.update).not.toHaveBeenCalled()
  })

  it('refreshes target options when create mode reopens after a save', async () => {
    mockState.getTargetModelEntityOptions
      .mockResolvedValueOnce({
        configured: true,
        entities: [createTargetModelEntityOption()],
      })
      .mockResolvedValueOnce({
        configured: true,
        entities: [createTargetModelEntityOption({ name: 'remaining_target' })],
      })
    const wrapper = mountEntityFormDialog()
    await flushPromises()

    findAutocompleteByLabel(wrapper, 'Start from target model')!.vm.$emit('update:modelValue', 'target_fact')
    await flushPromises()
    findSelectByLabel(wrapper, 'Type *')!.vm.$emit('update:modelValue', 'entity')
    await flushPromises()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()
    expect(mockState.getTargetModelEntityOptions).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('saved')?.at(-1)).toEqual(['target_fact'])

    const savedEntity = createEntity('target_fact', {
      type: 'entity',
      public_id: 'target_fact_id',
      keys: ['source_key'],
      columns: ['source_key'],
    })
    await wrapper.setProps({ modelValue: false, mode: 'edit', entity: savedEntity })
    await flushPromises()
    await wrapper.setProps({ modelValue: true, mode: 'create', entity: undefined })
    await flushPromises()

    expect(mockState.getTargetModelEntityOptions).toHaveBeenCalledTimes(2)
    expect(findAutocompleteByLabel(wrapper, 'Start from target model')?.props('items')).toEqual([
      createTargetModelEntityOption({ name: 'remaining_target' }),
    ])
    expect(wrapper.text()).not.toContain('target_fact')
  })

  it('limits selected classifiers to explicit fixed or sql types', async () => {
    mockState.getTargetModelEntityOptions.mockResolvedValue({
      configured: true,
      entities: [createTargetModelEntityOption({ name: 'target_classifier', role: 'classifier' })],
    })
    const wrapper = mountEntityFormDialog()
    await flushPromises()

    const picker = findAutocompleteByLabel(wrapper, 'Start from target model')
    picker!.vm.$emit('update:modelValue', 'target_classifier')
    await flushPromises()

    const typeSelect = findSelectByLabel(wrapper, 'Type *')
    const availableTypes = (typeSelect?.props('items') as Array<{ value: string }>).map(({ value }) => value)
    expect(availableTypes).toEqual(['fixed', 'sql'])
    expect(wrapper.text()).toContain('Classifiers must use fixed values or an sql query.')

    typeSelect!.vm.$emit('update:modelValue', 'entity')
    await flushPromises()
    expect(typeSelect?.props('modelValue')).toBeNull()
    expect(wrapper.findAll('button').find((button) => button.text().trim() === 'Save')?.element.disabled).toBe(true)

    typeSelect!.vm.$emit('update:modelValue', 'sql')
    await flushPromises()
    expect(typeSelect?.props('modelValue')).toBe('sql')

    typeSelect!.vm.$emit('update:modelValue', 'fixed')
    await flushPromises()
    expect(typeSelect?.props('modelValue')).toBe('fixed')
    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.create).toHaveBeenCalledWith({
      name: 'target_classifier',
      entity_data: expect.objectContaining({
        type: 'fixed',
        public_id: 'target_fact_id',
      }),
    })
    expect(mockState.update).not.toHaveBeenCalled()
  })

  it('keeps the editor below the app bar and within a short viewport', async () => {
    const originalWidth = window.innerWidth
    const originalHeight = window.innerHeight
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1440 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 650 })

    const wrapper = mountEntityFormDialog()

    try {
      await nextTick()

      const dialog = wrapper.find('.v-dialog-stub')
      expect(dialog.attributes('data-location')).toBe('top')
      expect(dialog.attributes('data-offset')).toBe('56')
      expect(dialog.attributes('data-height')).toBe('578px')
    } finally {
      wrapper.unmount()
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: originalWidth })
      Object.defineProperty(window, 'innerHeight', { configurable: true, value: originalHeight })
    }
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

  it('adds active completed-cache references after field-specific candidates and excludes fixed columns', async () => {
    const references = ['@value: entities.site.keys', '@value: entities.site.columns']
    mockState.referenceEntities = [
      createEntity('site', { keys: ['site_id'], columns: ['site_id', 'site_name'] }),
      createEntity('broken', { keys: ['broken_id', ['nested']] }),
    ]
    mockState.columnAvailability = {
      columns: ['ordinary_column'],
      business_keys: ['ordinary_key'],
      replacements: [],
      drop_duplicates: ['ordinary_deduplication'],
      drop_empty_rows: ['ordinary_empty_check'],
      extra_columns: { sources: [] },
      filters: { extract: [] },
      foreign_keys: [],
      unnest: { id_vars: ['ordinary_id'], value_vars: ['ordinary_value'] },
    }

    const entity = createEntity('sample', {
      type: 'entity',
      public_id: 'sample_id',
      keys: ['@value: entities.site.keys'],
      columns: ['@value: entities.site.columns'],
      foreign_keys: [{ entity: 'site', local_keys: [], remote_keys: [], how: 'left' }],
      unnest: { id_vars: [], value_vars: [], var_name: 'variable', value_name: 'value' },
      drop_duplicates: ['@value: entities.site.keys'],
      drop_empty_rows: ['@value: entities.site.columns'],
    })
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()

    const comboboxItems = (label: string) =>
      wrapper
        .findAllComponents({ name: 'VCombobox' })
        .find((component) => component.props('label') === label)
        ?.props('items')
    expect(comboboxItems('Business Keys *')).toEqual(['ordinary_key', ...references])
    expect(comboboxItems('Columns')).toEqual(['ordinary_column', ...references])
    expect(comboboxItems('Deduplication Columns')).toEqual(['ordinary_deduplication', ...references])
    expect(comboboxItems('Columns to Check for Empty Values')).toEqual(['ordinary_empty_check', ...references])

    const foreignKeyEditor = wrapper.findComponent({ name: 'ForeignKeyEditor' })
    expect(foreignKeyEditor.props('referenceSuggestions')).toEqual(references)
    expect(foreignKeyEditor.props('referenceEntities')).toBe(mockState.referenceEntities)
    const unnestEditor = wrapper.findComponent({ name: 'UnnestEditor' })
    expect(unnestEditor.props('idVarColumns')).toEqual(['ordinary_id'])
    expect(unnestEditor.props('valueVarColumns')).toEqual(['ordinary_value'])
    expect(unnestEditor.props('referenceSuggestions')).toEqual(references)
    expect(unnestEditor.props('referenceEntities')).toBe(mockState.referenceEntities)
    expect(wrapper.findAllComponents({ name: 'ValueReferenceChip' })).toHaveLength(4)
    wrapper.unmount()

    mockState.referenceEntities = null
    const pendingWrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()
    expect(findComboboxItemsByLabel(pendingWrapper, 'Business Keys *')).toEqual(['ordinary_key'])
    expect(pendingWrapper.findComponent({ name: 'ForeignKeyEditor' }).props('referenceSuggestions')).toEqual([])
    pendingWrapper.unmount()

    mockState.referenceEntities = [
      createEntity('site', { keys: ['site_id'], columns: ['site_id', 'site_name'] }),
      createEntity('broken', { keys: ['broken_id', ['nested']] }),
    ]
    mockState.currentProjectName = 'another-project'
    const mismatchedWrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()
    expect(findComboboxItemsByLabel(mismatchedWrapper, 'Business Keys *')).toEqual(['ordinary_key'])
    expect(mismatchedWrapper.findComponent({ name: 'ForeignKeyEditor' }).props('referenceSuggestions')).toEqual([])
    mismatchedWrapper.unmount()

    mockState.currentProjectName = 'arbodat'
    mockState.referenceEntities = []
    const emptyWrapper = mountEntityFormDialog({ mode: 'edit', entity })
    await flushPromises()
    expect(findComboboxItemsByLabel(emptyWrapper, 'Business Keys *')).toEqual(['ordinary_key'])
    emptyWrapper.unmount()

    mockState.referenceEntities = [createEntity('site', { keys: ['site_id'], columns: ['site_name'] })]
    const fixedWrapper = mountEntityFormDialog({ mode: 'edit', entity: fixedEntity })
    await flushPromises()
    expect(findComboboxItemsByLabel(fixedWrapper, 'Columns')).toEqual(['ordinary_column'])
    expect(fixedWrapper.findAllComponents({ name: 'ValueReferenceChip' })).toHaveLength(0)
    fixedWrapper.unmount()
  })

  it('keeps an unavailable preview read-only and allows unrelated edits to save', async () => {
    mockState.update.mockResolvedValue({ warnings: [] })
    mockState.referenceEntities = [createEntity('site', { keys: ['site_id'] })]
    const entity = createEntity('preview_entity', {
      type: 'entity',
      public_id: 'preview_entity_id',
      keys: '@value: entities.missing.keys',
      columns: ['preview_entity_id'],
    })
    const previewChipStubs = {
      ...childStubs,
      ValueReferenceChip: false,
    }
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity }, previewChipStubs)
    await flushPromises()
    await nextTick()

    await wrapper.get('button[aria-label="Preview value reference"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Preview unavailable')
    expect(wrapper.text()).toContain('@value: entities.missing.keys')

    const columnsCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Columns')!
    columnsCombobox.vm.$emit('update:modelValue', ['preview_entity_id', 'unrelated_column'])
    await flushPromises()
    await nextTick()

    const yamlEditor = wrapper.findComponent({ name: 'YamlEditor' })
    expect((loadYaml(yamlEditor.props('modelValue') as string) as Record<string, any>).keys).toBe(
      '@value: entities.missing.keys'
    )
    expect(wrapper.findAll('button').find((button) => button.text().trim() === 'Save')?.element.disabled).toBe(false)
    expect(mockState.showError).not.toHaveBeenCalled()

    await wrapper
      .findAll('button')
      .find((button) => button.text().trim() === 'Save')!
      .trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith(
      'preview_entity',
      expect.objectContaining({
        entity_data: expect.objectContaining({
          keys: '@value: entities.missing.keys',
          columns: ['preview_entity_id', 'unrelated_column'],
        }),
      })
    )
  })

  it('preserves unchanged reference field shapes through form edits and invalid YAML', async () => {
    mockState.update.mockResolvedValue({ warnings: [] })
    const rawDropEmptyRows = ['@value: entities.site.columns', "@value: entities.site.keys + ['other']"]
    const rawUnnest = {
      id_vars: '@value: entities.site.keys',
      value_vars: ['sample_id', '@value: entities.site.columns'],
      var_name: 'variable',
      value_name: 'value',
    }
    const entity = createEntity('round_trip_entity', {
      type: 'entity',
      public_id: 'round_trip_id',
      keys: '@value: entities.site.keys',
      columns: ['@value: entities.site.columns'],
      foreign_keys: [
        {
          entity: 'site',
          local_keys: '@value: entities.site.keys',
          remote_keys: ['@value: entities.site.keys'],
          how: 'left',
        },
        {
          entity: 'other',
          local_keys: ['local_id'],
          remote_keys: "@value: entities.other.keys + ['other_id']",
          how: 'inner',
        },
      ],
      unnest: rawUnnest,
      drop_duplicates: '@value: entities.site.keys',
      drop_empty_rows: rawDropEmptyRows,
    })
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity })

    await flushPromises()
    await nextTick()

    const initialYaml = loadYaml(wrapper.findComponent({ name: 'YamlEditor' }).props('modelValue') as string) as Record<
      string,
      any
    >
    expect(initialYaml.keys).toBe('@value: entities.site.keys')
    expect(initialYaml.columns).toEqual(['@value: entities.site.columns'])
    expect(initialYaml.foreign_keys[0].local_keys).toBe('@value: entities.site.keys')
    expect(initialYaml.foreign_keys[1].remote_keys).toBe("@value: entities.other.keys + ['other_id']")
    expect(initialYaml.unnest).toEqual(rawUnnest)
    expect(initialYaml.drop_duplicates).toBe('@value: entities.site.keys')
    expect(initialYaml.drop_empty_rows).toEqual(rawDropEmptyRows)

    const foreignKeyEditor = wrapper.findComponent({ name: 'ForeignKeyEditor' })
    const foreignKeys = foreignKeyEditor.props('modelValue') as Array<Record<string, unknown>>
    expect(foreignKeys[0]?.local_keys).toEqual(['@value: entities.site.keys'])
    expect(foreignKeys[0]?.remote_keys).toEqual(['@value: entities.site.keys'])
    expect(foreignKeys[1]?.local_keys).toEqual(['local_id'])
    expect(foreignKeys[1]?.remote_keys).toEqual(["@value: entities.other.keys + ['other_id']"])

    const unnestEditor = wrapper.findComponent({ name: 'UnnestEditor' })
    expect(unnestEditor.props('modelValue')).toEqual({
      ...rawUnnest,
      id_vars: ['@value: entities.site.keys'],
    })
    foreignKeyEditor.vm.$emit('update:modelValue', foreignKeys)
    unnestEditor.vm.$emit('update:modelValue', unnestEditor.props('modelValue'))

    const yamlEditor = wrapper.findComponent({ name: 'YamlEditor' })
    yamlEditor.vm.$emit('update:modelValue', 'name: [broken')
    yamlEditor.vm.$emit('change', 'name: [broken')
    yamlEditor.vm.$emit('validate', false, 'Invalid YAML')
    await flushPromises()

    await setTextFieldValue(wrapper, 'Public ID *', 'round_trip_public_id')
    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith(
      'round_trip_entity',
      expect.objectContaining({
        entity_data: expect.objectContaining({
          public_id: 'round_trip_public_id',
          keys: '@value: entities.site.keys',
          columns: ['@value: entities.site.columns'],
          foreign_keys: [
            expect.objectContaining({
              local_keys: '@value: entities.site.keys',
              remote_keys: ['@value: entities.site.keys'],
            }),
            expect.objectContaining({
              local_keys: ['local_id'],
              remote_keys: "@value: entities.other.keys + ['other_id']",
            }),
          ],
          unnest: rawUnnest,
          drop_duplicates: '@value: entities.site.keys',
          drop_empty_rows: rawDropEmptyRows,
        }),
      })
    )
  })

  it('uses the shape of a valid YAML edit for subsequent saves', async () => {
    mockState.update.mockResolvedValue({ warnings: [] })
    const entity = createEntity('yaml_shape_entity', {
      type: 'entity',
      public_id: 'yaml_shape_id',
      keys: ['@value: entities.site.keys'],
      columns: ['sample_id'],
    })
    const wrapper = mountEntityFormDialog({ mode: 'edit', entity, initialTab: 'yaml' })

    await flushPromises()
    await nextTick()

    const yamlEditor = wrapper.findComponent({ name: 'YamlEditor' })
    const editedYaml = [
      'name: yaml_shape_entity',
      'type: entity',
      'system_id: system_id',
      'public_id: yaml_shape_id',
      'keys: "@value: entities.site.keys"',
      'columns:',
      '  - sample_id',
    ].join('\n')
    yamlEditor.vm.$emit('update:modelValue', editedYaml)
    yamlEditor.vm.$emit('change', editedYaml)
    yamlEditor.vm.$emit('validate', true)
    await flushPromises()

    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton?.element.disabled).toBe(false)
    await saveButton!.trigger('click')
    await flushPromises()

    expect(mockState.update).toHaveBeenCalledWith(
      'yaml_shape_entity',
      expect.objectContaining({
        entity_data: expect.objectContaining({
          keys: '@value: entities.site.keys',
          columns: ['sample_id'],
        }),
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

    const keysCombobox = wrapper
      .findAllComponents({ name: 'VCombobox' })
      .find((component) => component.props('label') === 'Business Keys *')
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
    expect(mockState.syncCachedEntity).toHaveBeenCalledWith(freshEntity, 'arbodat')
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
    expect(mockState.syncCachedEntity).toHaveBeenCalledWith(freshEntity, 'arbodat')
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
