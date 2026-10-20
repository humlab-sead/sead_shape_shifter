import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, reactive, toRefs } from 'vue'
import { shallowMount } from '@vue/test-utils'

import IngesterForm from '../IngesterForm.vue'
import type { IngestResponse, IngesterMetadata, ProjectIngesterRequest, ValidateResponse } from '@/types/ingester'

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
  validateProject: vi.fn(async () => {}),
  ingestProject: vi.fn(async () => {}),
  selectIngester: vi.fn((key: string) => {
    ingesterStore.selectedIngester = ingesterStore.ingesters.find((ingester) => ingester.key === key) ?? null
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
    return dataSourceStore.dataSources.find((dataSource) => dataSource.name === name) ?? null
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
  props: ['modelValue', 'label', 'rules', 'hint', 'type', 'readonly'],
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
  VBtn: { name: 'VBtn', props: ['disabled'], template: '<button><slot /></button>' },
  VIcon: true,
  VSpacer: true,
}

function mountForm(props: { excludedIngesterKeys?: string[]; projectName?: string; projectLoading?: boolean } = {}) {
  return shallowMount(IngesterForm, {
    props,
    global: {
      renderStubDefaultSlot: true,
      stubs,
    },
  })
}

function findTextField(wrapper: ReturnType<typeof mountForm>, label: string) {
  return wrapper.findAllComponents({ name: 'VTextField' }).find((node) => node.props('label') === label)
}

function findTextarea(wrapper: ReturnType<typeof mountForm>, label: string) {
  return wrapper.findAllComponents({ name: 'VTextarea' }).find((node) => node.props('label') === label)
}

describe('IngesterForm', () => {
  beforeEach(() => {
    ingesterStore.validate.mockClear()
    ingesterStore.ingest.mockClear()
    ingesterStore.validateProject.mockClear()
    ingesterStore.ingestProject.mockClear()
    projectStore.selectedProject = {
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
    }
    ingesterStore.ingesters = [
      {
        key: 'sead_change_request',
        name: 'SEAD Change Request',
        description: 'Emit an MVP Delivery change package',
        version: '1.0.0',
        supported_formats: [],
      },
    ]
    ingesterStore.selectedIngester = ingesterStore.ingesters[0] ?? null
    ingesterStore.validationResult = null
    ingesterStore.ingestionResult = null
    ingesterStore.error = null
  })

  it('uses project-only actions for Change Request and keeps pending-confirmation guidance', async () => {
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

    const wrapper = mountForm({ projectName: 'pilot_bugs' })
    const vm = wrapper.vm as unknown as {
      formValid: boolean
      canRunSelectedIngester: boolean
      selectedIngesterAllowed: boolean
      handleValidate: () => Promise<void>
      handleIngest: () => Promise<void>
      buildProjectRequest: () => ProjectIngesterRequest
    }
    vm.formValid = true
    await nextTick()

    ingesterStore.validate.mockClear()
    ingesterStore.ingest.mockClear()
    ingesterStore.validateProject.mockClear()
    ingesterStore.ingestProject.mockClear()

    expect(wrapper.text()).toContain('Change Request uses the normalized tables from this saved project.')
    expect(wrapper.text()).toContain('Binding Set Confirmation Required')
    expect(wrapper.text()).toContain('binding-123')
    expect(wrapper.text()).toContain('Confirm the Binding Set in SIMS')
    expect(wrapper.text()).toContain('Every tracked entity needs declared business keys')
    expect(findTextField(wrapper, 'Source File Path *')).toBeUndefined()
    expect(wrapper.text()).not.toContain('Ignore Columns')
    expect(wrapper.text()).not.toContain('Target Database:')

    const actionButtons = wrapper
      .findAllComponents({ name: 'VBtn' })
      .filter((button) => button.text().includes('Validate') || button.text().includes('Dispatch'))
    expect(actionButtons).toHaveLength(2)
    expect(vm.canRunSelectedIngester).toBe(true)
    expect(vm.selectedIngesterAllowed).toBe(true)
    expect(actionButtons.every((button) => !button.props('disabled'))).toBe(true)

    await vm.handleValidate()
    await vm.handleIngest()

    expect(ingesterStore.validateProject).toHaveBeenCalledWith(vm.buildProjectRequest())
    expect(ingesterStore.ingestProject).toHaveBeenCalledWith(vm.buildProjectRequest())
    expect(ingesterStore.validate).not.toHaveBeenCalled()
    expect(ingesterStore.ingest).not.toHaveBeenCalled()
  })

  it('renders deploy artifact summary and handoff guidance for successful change-package output', () => {
    ingesterStore.ingestionResult = {
      success: true,
      records_processed: 2,
      message: 'Deploy artifact emitted to output/pilot-bugs-001',
      output_path: 'output/pilot-bugs-001',
      scope_name: 'provider://mal/archeobotany/arbodat-pilot',
      run_id: 'run-abc-123',
      deploy_artifact: {
        metadata: {
          deploy_strategy: 'copy_csv',
          scope_name: 'provider://mal/archeobotany/arbodat-pilot',
          run_id: 'run-abc-123',
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
    expect(wrapper.text()).toContain('provider://mal/archeobotany/arbodat-pilot')
    expect(wrapper.text()).toContain('run-abc-123')
    expect(wrapper.text()).toContain('Review the emitted SQL, manifest, and compressed table payload files')
  })

  it('shows backend errors for blocked Change Request business keys', () => {
    ingesterStore.validationResult = {
      is_valid: false,
      errors: ["Entity 'sample' has duplicate values for declared business key 'sample_code'."],
      warnings: [],
      infos: [],
    }

    const wrapper = mountForm()

    expect(wrapper.text()).toContain("Entity 'sample' has duplicate values for declared business key 'sample_code'.")
  })

  it('prefills project-derived submission context fields and exposes backend-matched validation rules', async () => {
    const wrapper = mountForm({ projectName: 'pilot_bugs' })
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
    expect(wrapper.text()).toContain(
      'Auto-derived from the active project and selected datatype until you override it.'
    )
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

    const request = (
      wrapper.vm as unknown as { buildProjectRequest: () => ProjectIngesterRequest }
    ).buildProjectRequest()
    expect(request).toMatchObject({
      project_name: 'pilot_bugs',
      deploy_strategy: 'copy_csv',
      submission_context: {
        submission_name: 'pilot_bugs_mal',
        datatype: 'mal',
        identifier: 'PILOT_BUGS',
        description: 'Pilot bugs change package',
        author: 'SEAD Lab',
      },
    })
    expect(request).not.toHaveProperty('source')
    expect(request).not.toHaveProperty('config')
    expect(request.submission_context).not.toHaveProperty('project_name')
    expect(request.submission_context).not.toHaveProperty('data_provider_code')
  })

  it('enables Change Request actions only after the route project is loaded and matches', async () => {
    const wrapper = mountForm({ projectName: 'route_project', projectLoading: true })
    const vm = wrapper.vm as unknown as {
      formValid: boolean
      buildProjectRequest: () => ProjectIngesterRequest
    }
    vm.formValid = true
    await nextTick()

    const projectField = findTextField(wrapper, 'Project Name *')
    expect(projectField?.props('modelValue')).toBe('route_project')
    expect(projectField?.props('readonly')).toBe('')
    expect(vm.buildProjectRequest().project_name).toBe('route_project')
    const actionButtons = wrapper
      .findAllComponents({ name: 'VBtn' })
      .filter((button) => button.text().includes('Validate') || button.text().includes('Dispatch'))
    expect(actionButtons.every((button) => button.props('disabled'))).toBe(true)

    projectStore.selectedProject.metadata.name = 'route_project'
    await wrapper.setProps({ projectLoading: false })
    await nextTick()

    expect(vm.buildProjectRequest().project_name).toBe('route_project')
    expect(actionButtons.every((button) => !button.props('disabled'))).toBe(true)
  })

  it('keeps Change Request actions disabled when there is no route project', async () => {
    const wrapper = mountForm()
    const vm = wrapper.vm as unknown as { formValid: boolean; handleValidate: () => Promise<void> }
    vm.formValid = true
    await nextTick()

    const actionButtons = wrapper.findAllComponents({ name: 'VBtn' }).slice(0, 2)
    expect(actionButtons.every((button) => button.props('disabled'))).toBe(true)
    await vm.handleValidate()
    expect(ingesterStore.validateProject).not.toHaveBeenCalled()
  })

  it('filters excluded ingesters and keeps ordinary ingesters actionable', async () => {
    const ordinaryIngester: IngesterMetadata = {
      key: 'ordinary',
      name: 'Ordinary Ingester',
      description: 'Project-independent',
      version: '1.0.0',
      supported_formats: ['xlsx'],
    }
    ingesterStore.ingesters.push(ordinaryIngester)
    ingesterStore.selectedIngester = ordinaryIngester

    const wrapper = mountForm({ excludedIngesterKeys: ['sead_change_request'] })
    const vm = wrapper.vm as unknown as { formValid: boolean; form: { source: string } }
    vm.formValid = true
    vm.form.source = 'input.xlsx'
    await nextTick()

    const workflowSelector = wrapper.findComponent({ name: 'VSelect' })
    expect(workflowSelector.props('items')).toEqual([ordinaryIngester])

    await (wrapper.vm as unknown as { handleValidate: () => Promise<void> }).handleValidate()
    await (wrapper.vm as unknown as { handleIngest: () => Promise<void> }).handleIngest()

    expect(ingesterStore.validate).toHaveBeenCalledOnce()
    expect(ingesterStore.ingest).toHaveBeenCalledOnce()
    expect(ingesterStore.validate).toHaveBeenCalledWith(expect.objectContaining({ source: 'input.xlsx' }))
    expect(ingesterStore.ingest).toHaveBeenCalledWith(expect.objectContaining({ source: 'input.xlsx' }))
    expect(ingesterStore.validateProject).not.toHaveBeenCalled()
    expect(ingesterStore.ingestProject).not.toHaveBeenCalled()
  })
})
