import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import ProjectDetailView from '../ProjectDetailView.vue'

const mockGraphState = vi.hoisted(() => {
  const removeNodeClass = vi.fn()
  const removeEdgeClass = vi.fn()
  const addRelatedBranchNodeClass = vi.fn()
  const addRelatedBranchEdgeClass = vi.fn()

  return {
    capturedOptions: null as any,
    removeNodeClass,
    removeEdgeClass,
    addRelatedBranchNodeClass,
    addRelatedBranchEdgeClass,
    render: vi.fn(),
    fit: vi.fn(),
    zoomIn: vi.fn(),
    zoomOut: vi.fn(),
    reset: vi.fn(),
    exportPNG: vi.fn(),
    getCurrentPositions: vi.fn(() => ({})),
    fetchDependencies: vi.fn(async () => undefined),
    fetchEntities: vi.fn(async () => undefined),
    validate: vi.fn(async () => undefined),
    validateEntity: vi.fn(async () => undefined),
    previewEntity: vi.fn(async () => null),
    selectProject: vi.fn(async () => undefined),
    clearProjectError: vi.fn(),
    fetchBackups: vi.fn(async () => undefined),
    restore: vi.fn(async () => undefined),
    markAsChanged: vi.fn(),
    startSession: vi.fn(async () => undefined),
    saveWithVersionCheck: vi.fn(async () => undefined),
    getLayout: vi.fn(async () => ({ layout: {}, has_custom_layout: false })),
    getNote: vi.fn(async () => ({ note: '', has_note: false })),
    removeNote: vi.fn(async () => ({ has_note: false })),
    setNote: vi.fn(async () => ({ has_note: false })),
  }
})

const mockProjectState = vi.hoisted(() => ({
  selectedProjectRef: null as any,
  refreshProject: vi.fn(async () => undefined),
  getRawYaml: vi.fn(async () => ({ yaml_content: 'metadata: {}\nentities: {}\n' })),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { name: 'arbodat' }, query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/composables', async () => {
  const vue = await import('vue')

  const selectedProject = vue.ref({ metadata: {}, options: {} })
  mockProjectState.selectedProjectRef = selectedProject

  return {
    useProjects: () => ({
      selectedProject,
      loading: vue.ref(false),
      error: vue.ref(null),
      hasUnsavedChanges: vue.ref(false),
      backups: vue.ref([]),
      select: mockGraphState.selectProject,
      refresh: mockProjectState.refreshProject,
      clearError: mockGraphState.clearProjectError,
      fetchBackups: mockGraphState.fetchBackups,
      restore: mockGraphState.restore,
      markAsChanged: mockGraphState.markAsChanged,
    }),
    useEntities: () => ({
      entityCount: vue.ref(2),
      entities: vue.ref([
        { name: 'analysis_entity', entity_data: { type: 'merged', public_id: 'analysis_entity_id' }, etag: '1' },
        { name: 'abundance_source', entity_data: { type: 'entity', public_id: 'abundance_id' }, etag: '2' },
      ]),
      fetch: mockGraphState.fetchEntities,
    }),
    useDependencies: () => ({
      dependencyGraph: vue.ref({
        nodes: [
          { name: 'analysis_entity', depends_on: ['abundance_source'], depth: 1, type: 'merged' },
          { name: 'abundance_source', depends_on: [], depth: 0, type: 'entity' },
        ],
        edges: [
          {
            source: 'abundance_source',
            target: 'analysis_entity',
            type: 'provides',
            label: 'abundance',
            branch_name: 'abundance',
            is_branch_dependency: true,
          },
        ],
        has_cycles: false,
        cycles: [],
        topological_order: ['abundance_source', 'analysis_entity'],
        source_nodes: [],
        source_edges: [],
      }),
      loading: vue.ref(false),
      error: vue.ref(null),
      hasCircularDependencies: vue.ref(false),
      cycles: vue.ref([]),
      statistics: vue.ref({ nodeCount: 2, edgeCount: 1, sourceNodeCount: 0, sourceEdgeCount: 0 }),
      fetch: mockGraphState.fetchDependencies,
      isInCycle: vi.fn(() => false),
      clearError: vi.fn(),
    }),
    useValidation: () => ({
      validationResult: vue.ref(null),
      loading: vue.ref(false),
      hasErrors: vue.ref(false),
      hasWarnings: vue.ref(false),
      errorCount: vue.ref(0),
      warningCount: vue.ref(0),
      validate: mockGraphState.validate,
      validateEntity: mockGraphState.validateEntity,
    }),
    useCytoscape: (options: any) => {
      mockGraphState.capturedOptions = options

      const fakeNodeCollection = Object.assign(
        [
          {
            id: () => 'analysis_entity',
            addClass: vi.fn(),
            removeClass: vi.fn(),
          },
        ],
        {
          removeClass: mockGraphState.removeNodeClass,
        }
      )

      const fakeBranchEdges = {
        addClass: mockGraphState.addRelatedBranchEdgeClass,
        sources: () => ({ addClass: mockGraphState.addRelatedBranchNodeClass }),
      }

      const fakeCy = {
        nodes: () => fakeNodeCollection,
        edges: () => ({
          removeClass: mockGraphState.removeEdgeClass,
          filter: () => fakeBranchEdges,
        }),
        getElementById: () => ({
          length: 1,
          data: (key: string) => (key === 'type' ? 'merged' : null),
        }),
      }

      return {
        cy: vue.ref(fakeCy),
        fit: mockGraphState.fit,
        zoomIn: mockGraphState.zoomIn,
        zoomOut: mockGraphState.zoomOut,
        reset: mockGraphState.reset,
        render: mockGraphState.render,
        exportPNG: mockGraphState.exportPNG,
        getCurrentPositions: mockGraphState.getCurrentPositions,
      }
    },
  }
})

vi.mock('@/composables/useDataValidation', () => ({
  useDataValidation: () => ({
    loading: ref(false),
    result: ref(null),
    validateData: vi.fn(async () => undefined),
    previewFixes: vi.fn(async () => undefined),
    applyFixes: vi.fn(async () => undefined),
    autoFixableIssues: ref([]),
  }),
}))

vi.mock('@/composables/useConformanceValidation', () => ({
  useConformanceValidation: () => ({
    loading: ref(false),
    result: ref(null),
    validateConformance: vi.fn(async () => undefined),
  }),
}))

vi.mock('@/composables/useEntityPreview', () => ({
  useEntityPreview: () => ({
    previewEntity: mockGraphState.previewEntity,
  }),
}))

vi.mock('@/composables/useSession', () => ({
  useSession: () => ({
    startSession: mockGraphState.startSession,
    saveWithVersionCheck: mockGraphState.saveWithVersionCheck,
    hasActiveSession: ref(false),
  }),
}))

vi.mock('@/stores', () => ({
  useProjectStore: () => ({}),
}))

vi.mock('@/stores/entity', () => ({
  useEntityStore: () => ({
    entities: [
      { name: 'analysis_entity', entity_data: { type: 'merged' } },
      { name: 'abundance_source', entity_data: { type: 'entity' } },
    ],
    showEditorOverlay: false,
    overlayEntityName: null,
    overlayInitialTab: 'form',
    openEditorOverlay: vi.fn(),
    closeEditorOverlay: vi.fn(),
    createEntity: vi.fn(async () => undefined),
    updateEntity: vi.fn(async () => undefined),
    deleteEntity: vi.fn(async () => undefined),
  }),
}))

vi.mock('@/stores/taskStatus', () => ({
  useTaskStatusStore: () => ({
    taskStatus: {
      completion_stats: {
        total: 0,
        done: 0,
        ignored: 0,
        todo: 0,
        required_total: 0,
        required_done: 0,
        required_todo: 0,
        completion_percentage: 0,
      },
    },
    getEntityStatus: vi.fn(() => null),
    refresh: vi.fn(async () => undefined),
    initialize: vi.fn(async () => undefined),
    setEntityHasNote: vi.fn(),
    markComplete: vi.fn(async () => true),
    markIgnored: vi.fn(async () => true),
    markOngoing: vi.fn(async () => true),
    resetStatus: vi.fn(async () => true),
    markTodo: vi.fn(async () => true),
    error: null,
  }),
}))

vi.mock('@/api', () => ({
  api: {
    projects: {
      getLayout: mockGraphState.getLayout,
      saveLayout: vi.fn(async () => undefined),
      clearLayout: vi.fn(async () => undefined),
      getRawYaml: mockProjectState.getRawYaml,
      updateRawYaml: vi.fn(async () => undefined),
      getTargetModelYaml: vi.fn(async () => ({ content: '' })),
      updateTargetModelYaml: vi.fn(async () => undefined),
      downloadTargetModelDocs: vi.fn(async () => new Blob()),
    },
    tasks: {
      initialize: vi.fn(async () => ({ created: 0 })),
      getNote: mockGraphState.getNote,
      removeNote: mockGraphState.removeNote,
      setNote: mockGraphState.setNote,
    },
  },
}))

const vuetify = createVuetify({ components, directives })

function mountProjectDetailView() {
  return mount(ProjectDetailView, {
    global: {
      plugins: [vuetify],
      stubs: {
        VTabs: { template: '<div><slot /></div>' },
        VTab: { template: '<button type="button"><slot /></button>' },
        VWindow: { template: '<div><slot /></div>' },
        VWindowItem: { template: '<div><slot /></div>' },
        VNavigationDrawer: { template: '<aside data-testid="navigation-drawer"><slot /></aside>' },
        VProgressCircular: { template: '<div data-testid="progress-circular" />' },
        EntityListCard: { template: '<div data-testid="entity-list-card" />' },
        EntityFormDialog: { template: '<div data-testid="entity-form-dialog" />' },
        ValidationPanel: { template: '<div data-testid="validation-panel" />' },
        PreviewFixesModal: { template: '<div data-testid="preview-fixes-modal" />' },
        ProjectDataSources: { template: '<div data-testid="project-data-sources" />' },
        SessionIndicator: { template: '<div data-testid="session-indicator" />' },
        CircularDependencyAlert: { template: '<div data-testid="circular-dependency-alert" />' },
        GraphNodeContextMenu: { template: '<div data-testid="graph-context-menu" />' },
        TaskFilterDropdown: { template: '<div data-testid="task-filter-dropdown" />' },
        GraphDisplayOptionsDropdown: { template: '<div data-testid="graph-display-options" />' },
        GraphLayoutDropdown: { template: '<div data-testid="graph-layout-dropdown" />' },
        ReconciliationView: { template: '<div data-testid="reconciliation-view" />' },
        MetadataEditor: { template: '<div data-testid="metadata-editor" />' },
        YamlEditor: { template: '<div data-testid="yaml-editor" />' },
        MonacoTextEditor: { template: '<div data-testid="monaco-text-editor" />' },
        ExecuteDialog: { template: '<div data-testid="execute-dialog" />' },
        IngesterForm: { template: '<div data-testid="ingester-form" />' },
        ProjectFileUploadCard: { template: '<div data-testid="project-file-upload" />' },
      },
    },
  })
}

describe('ProjectDetailView', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.localStorage.setItem('shapeshifter.graph.colorBy.arbodat', 'type')
    mockProjectState.selectedProjectRef.value = { metadata: {}, options: {} }
    mockProjectState.refreshProject.mockReset()
    mockProjectState.getRawYaml.mockReset()
    mockProjectState.getRawYaml.mockResolvedValue({ yaml_content: 'metadata: {}\nentities: {}\n' })
    mockGraphState.capturedOptions = null
    mockGraphState.removeNodeClass.mockReset()
    mockGraphState.removeEdgeClass.mockReset()
    mockGraphState.addRelatedBranchNodeClass.mockReset()
    mockGraphState.addRelatedBranchEdgeClass.mockReset()
    mockGraphState.render.mockReset()
    mockGraphState.getNote.mockClear()
  })

  it('captures graph options and opens the details drawer on node click', async () => {
    const wrapper = mountProjectDetailView()

    await flushPromises()
    ;(wrapper.vm as any).colorByMode = 'type'
    await flushPromises()

    expect(mockGraphState.capturedOptions).toBeTruthy()

    await mockGraphState.capturedOptions.onNodeClick('analysis_entity')
    await flushPromises()

    expect((wrapper.vm as any).selectedNode).toBe('analysis_entity')
    expect((wrapper.vm as any).showDetailsDrawer).toBe(true)
  })

  it('reloads raw project yaml when the selected project changes after yaml was loaded', async () => {
    const wrapper = mountProjectDetailView()

    await flushPromises()
    mockProjectState.getRawYaml.mockClear()

    ;(wrapper.vm as any).rawYamlContent = 'stale yaml'
    ;(wrapper.vm as any).originalYamlContent = 'stale yaml'
    ;(wrapper.vm as any).yamlHasChanges = false

    mockProjectState.selectedProjectRef.value = { metadata: { name: 'arbodat' }, options: {}, entities: {} }
    await nextTick()
    await flushPromises()

    expect(mockProjectState.getRawYaml).toHaveBeenCalledWith('arbodat')
  })
})