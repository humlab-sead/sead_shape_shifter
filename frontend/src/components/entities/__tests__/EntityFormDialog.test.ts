import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import type { EntityResponse } from '@/api/entities'
import EntityFormDialog from '../EntityFormDialog.vue'

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
  showError: vi.fn(),
  getValidDirectives: vi.fn(async () => []),
  getEntity: vi.fn(),
  getValues: vi.fn(),
  updateValues: vi.fn(),
  introspectQueryColumns: vi.fn(async () => []),
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
  }),
}))

vi.mock('@/composables/useDirectiveValidation', () => ({
  useDirectiveValidation: () => ({
    getValidDirectives: mockState.getValidDirectives,
  }),
}))

vi.mock('@/stores', () => ({
  useProjectStore: () => ({
    selectedProject: { options: { data_sources: {} } },
    currentProjectName: 'arbodat',
  }),
  useEntityStore: () => ({
    overlayInitialTab: 'form',
  }),
}))

vi.mock('@/api', () => ({
  api: {
    entities: {
      get: mockState.getEntity,
      getValues: mockState.getValues,
      updateValues: mockState.updateValues,
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
    template: '<button type="button" class="v-tab-stub" :data-tab-value="value" :data-disabled="String(disabled)"><slot /></button>',
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
  YamlEditor: { template: '<div data-testid="yaml-editor" />' },
  SqlEditor: { template: '<div data-testid="sql-editor" />' },
  ForeignKeyEditor: { template: '<div data-testid="foreign-key-editor" />' },
  FiltersEditor: { template: '<div data-testid="filters-editor" />' },
  UnnestEditor: { template: '<div data-testid="unnest-editor" />' },
  AppendEditor: { template: '<div data-testid="append-editor" />' },
  BranchEditor: { template: '<div data-testid="branch-editor" />' },
  ExtraColumnsEditor: { template: '<div data-testid="extra-columns-editor" />' },
  ReplacementsEditor: { template: '<div data-testid="replacements-editor" />' },
  SuggestionsPanel: { template: '<div data-testid="suggestions-panel" />' },
  MaterializeDialog: { template: '<div data-testid="materialize-dialog" />' },
  UnmaterializeDialog: { template: '<div data-testid="unmaterialize-dialog" />' },
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
        { name: 'analysis_entity_branch', data_type: 'string', nullable: false, is_key: false, is_derived: true, derived_from: null },
        { name: 'abundance_id', data_type: 'int', nullable: true, is_key: false, is_derived: true, derived_from: null },
        { name: 'relative_dating_id', data_type: 'int', nullable: true, is_key: false, is_derived: true, derived_from: null },
        { name: 'sample_name', data_type: 'string', nullable: false, is_key: true, is_derived: false, derived_from: null },
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
    mockState.showError.mockReset()
    mockState.getEntity.mockReset()
    mockState.getValues.mockReset()
    mockState.updateValues.mockReset()
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

  it('shows the columns picker for merged entities and seeds it with branch-union columns', async () => {
    const wrapper = mountEntityFormDialog({
      mode: 'edit',
      entity: mergedEntity,
    })

    await flushPromises()
    await nextTick()

    const columnsCombobox = wrapper.findAllComponents({ name: 'VCombobox' }).find((component) => component.props('label') === 'Columns')

    expect(columnsCombobox).toBeTruthy()
    expect(columnsCombobox?.props('items')).toEqual(
      expect.arrayContaining([
        'analysis_entity_branch',
        'sample_name',
        'abundance_value',
        'dating_value',
        'abundance_id',
        'relative_dating_id',
      ])
    )
    expect(wrapper.text()).toContain('Available post-merge: columns')
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
})