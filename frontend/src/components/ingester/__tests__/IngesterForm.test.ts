import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, reactive, toRefs } from 'vue'
import { shallowMount } from '@vue/test-utils'

import IngesterForm from '../IngesterForm.vue'
import type { IngestResponse, IngesterMetadata, ValidateRequest, ValidateResponse } from '@/types/ingester'

vi.mock('pinia', async () => {
  const actual = await vi.importActual<typeof import('pinia')>('pinia')

  return {
    ...actual,
    storeToRefs: (store: object) => toRefs(store),
  }
})

const ingesterStore = reactive({
  ingesters: [] as IngesterMetadata[],
  selectedIngester: null as IngesterMetadata | null,
  validationResult: null as ValidateResponse | null,
  ingestionResult: null as IngestResponse | null,
  error: null as string | null,
  isValidating: false,
  isIngesting: false,
  fetchIngesters: vi.fn(async () => {}),
  validate: vi.fn(async () => {}),
  ingest: vi.fn(async () => {}),
  selectIngester: vi.fn((key: string) => {
    ingesterStore.selectedIngester = ingesterStore.ingesters.find(ingester => ingester.key === key) ?? null
  }),
  clearError: vi.fn(() => {
    ingesterStore.error = null
  }),
  clearValidation: vi.fn(() => {
    ingesterStore.validationResult = null
  }),
  clearIngestion: vi.fn(() => {
    ingesterStore.ingestionResult = null
  }),
})

const dataSourceStore = reactive({
  dataSources: [{ name: 'sead_staging', host: 'db.local', port: 5432, database: 'sead_staging' }],
  fetchDataSources: vi.fn(async () => {}),
  dataSourceByName: vi.fn((name: string) => {
    return dataSourceStore.dataSources.find(dataSource => dataSource.name === name) ?? null
  }),
})

const projectStore = reactive({
  selectedProject: {
    metadata: {
      name: 'pilot_bugs',
      description: 'Pilot bugs change package',
      data_provider_code: 'SEAD',
    },
    options: {
      ingesters: {
        sead_change_request: {
          data_source: 'sead_staging',
          defaults: {
            datatype: 'mal',
            deploy_strategy: 'copy_csv',
            author: 'SEAD Lab',
          },
          options: {
            ignore_columns: ['date_updated'],
          },
        },
      },
    },
  },
})

vi.mock('@/stores/ingester', () => ({
  useIngesterStore: () => ingesterStore,
}))

vi.mock('@/stores/data-source', () => ({
  useDataSourceStore: () => dataSourceStore,
}))

vi.mock('@/stores/project', () => ({
  useProjectStore: () => projectStore,
}))

const slotStub = (name: string) => ({
  name,
  template: '<div><slot /></div>',
})

const textFieldStub = {
  name: 'VTextField',
  props: ['modelValue', 'label', 'rules', 'hint', 'type'],
  template: '<div class="v-text-field-stub" />',
}

const textareaStub = {
  name: 'VTextarea',
  props: ['modelValue', 'label', 'rules', 'hint'],
  template: '<div class="v-textarea-stub" />',
}

const selectStub = {
  name: 'VSelect',
  props: ['modelValue', 'label', 'items', 'rules', 'hint'],
  template: '<div class="v-select-stub" />',
}

const stubs = {
  VCard: slotStub('VCard'),
  VCardTitle: slotStub('VCardTitle'),
  VCardText: slotStub('VCardText'),
  VCardActions: slotStub('VCardActions'),
  VAlert: slotStub('VAlert'),
  VSelect: selectStub,
  VForm: slotStub('VForm'),
  VTextField: textFieldStub,
  VTextarea: textareaStub,
  VExpansionPanels: slotStub('VExpansionPanels'),
  VExpansionPanel: slotStub('VExpansionPanel'),
  VExpansionPanelText: slotStub('VExpansionPanelText'),
  VSwitch: slotStub('VSwitch'),
  VBtn: slotStub('VBtn'),
  VIcon: true,
  VSpacer: true,
}

function mountForm() {
  return shallowMount(IngesterForm, {
    global: {
      renderStubDefaultSlot: true,
      stubs,
    },
  })
}

function findTextField(wrapper: ReturnType<typeof mountForm>, label: string) {
  return wrapper.findAllComponents({ name: 'VTextField' }).find(node => node.props('label') === label)
}

function findTextarea(wrapper: ReturnType<typeof mountForm>, label: string) {
  return wrapper.findAllComponents({ name: 'VTextarea' }).find(node => node.props('label') === label)
}

describe('IngesterForm', () => {
  beforeEach(() => {
    ingesterStore.ingesters = [
      {
        key: 'sead_change_request',
        name: 'SEAD Change Request',
        description: 'Emit a Delivery 1 change package',
        version: '1.0.0',
        supported_formats: ['xlsx'],
      },
    ]
    ingesterStore.selectedIngester = ingesterStore.ingesters[0] ?? null
    ingesterStore.validationResult = null
    ingesterStore.ingestionResult = null
    ingesterStore.error = null
  })

  it('renders the dedicated sead_change_request workflow and pending confirmation guidance', () => {
    ingesterStore.validationResult = {
      is_valid: false,
      errors: [],
      warnings: [],
      infos: [],
      pending_confirmation_report: {
        submission_name: 'bugs_delivery_1',
        project_name: 'pilot_bugs',
        binding_set_uuid: 'binding-123',
        binding_set_state: 'proposed',
        blocked_entities: ['sample'],
        blocked_rows: 2,
        outstanding_step: 'Confirm the Binding Set before change-package generation can continue',
        operator_action: 'Confirm the Binding Set in SIMS, then rerun the ingester with the same submission context',
        rerun_instruction: 'Rerun bugs_delivery_1 after confirmation',
      },
    }

    const wrapper = mountForm()

    expect(wrapper.text()).toContain('This workflow collects the operator context needed')
    expect(wrapper.text()).toContain('Binding Set Confirmation Required')
    expect(wrapper.text()).toContain('binding-123')
    expect(wrapper.text()).toContain('Confirm the Binding Set in SIMS')
  })

  it('renders deploy artifact summary and handoff guidance for successful change-package output', () => {
    ingesterStore.ingestionResult = {
      success: true,
      records_processed: 2,
      message: 'Deploy artifact emitted to output/pilot-bugs-001',
      output_path: 'output/pilot-bugs-001',
      deploy_artifact: {
        metadata: {
          deploy_strategy: 'copy_csv',
          binding_set_uuid: 'binding-123',
          change_request_name: 'CR-2026-001',
          non_revertible: true,
        },
        metadata_artifact: {
          cr_name: 'pilot-bugs-001',
          issue_identifier: '455',
        },
        bundle_files: {
          'payload/sample.tsv.gz': 'content',
        },
      },
    }

    const wrapper = mountForm()

    expect(wrapper.text()).toContain('Deploy strategy:')
    expect(wrapper.text()).toContain('copy_csv')
    expect(wrapper.text()).toContain('Bundle name:')
    expect(wrapper.text()).toContain('pilot-bugs-001')
    expect(wrapper.text()).toContain('Review the emitted SQL, manifest, and compressed table payload files')
  })

  it('prefills project-derived submission context fields and exposes backend-matched validation rules', async () => {
    const wrapper = mountForm()
    await nextTick()

    const projectField = findTextField(wrapper, 'Project Name *')
    const submissionNameField = findTextField(wrapper, 'Submission Name *')
    const identifierField = findTextField(wrapper, 'Submission Identifier *')
    const timestampField = findTextField(wrapper, 'Dispatch Timestamp *')
    const descriptionField = findTextarea(wrapper, 'Description')

    expect(projectField?.props('modelValue')).toBe('pilot_bugs')
    expect(submissionNameField?.props('modelValue')).toBe('pilot_bugs_mal')
    expect(findTextField(wrapper, 'Submission Identifier *')?.props('modelValue')).toBe('PILOT_BUGS')
    expect(descriptionField?.props('modelValue')).toBe('Pilot bugs change package')
    expect(wrapper.text()).toContain('Auto-derived from the active project and selected datatype until you override it.')
    expect(wrapper.text()).toContain('Auto-derived from the active project.')
    expect(wrapper.text()).toContain('Auto-derived from the active project name until you override it.')
    expect(wrapper.text()).toContain('Auto-derived from project metadata until you override it.')
    expect(wrapper.text()).toContain('Operator-entered for this run.')
    expect(wrapper.text()).toContain('Operator-selected for this run.')

    const identifierRules = identifierField!.props('rules') as Array<(value: string) => boolean | string>
    const timestampRules = timestampField!.props('rules') as Array<(value: string) => boolean | string>
    const descriptionRules = descriptionField!.props('rules') as Array<(value: string) => boolean | string>

    expect(identifierRules[1]?.('bad-id')).toBe('Use only A-Z, 0-9, and _; max 39 characters')
    expect(identifierRules[1]?.('pilot_bugs')).toBe(true)
    expect(timestampRules[1]?.('not-a-date')).toBe('Enter a valid ISO-8601 local datetime')
    expect(descriptionRules[0]?.('line one\nline two')).toBe('Use a single line shorter than 80 characters')

    const request = (wrapper.vm as unknown as { buildValidateRequest: () => ValidateRequest }).buildValidateRequest()
    expect(request.deploy_strategy).toBe('copy_csv')
    expect(request.submission_context).toMatchObject({
      data_provider_code: 'SEAD',
      datatype: 'mal',
      author: 'SEAD Lab',
    })
  })
})