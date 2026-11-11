import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ValidationPanel from '../ValidationPanel.vue'
import type { ValidationResult } from '@/types'

const vuetify = createVuetify({ components, directives })

function mountValidationPanel(validationResult: ValidationResult | null) {
  return mount(ValidationPanel, {
    global: {
      plugins: [vuetify],
      stubs: {
        DataValidationConfig: {
          template: '<div data-testid="data-validation-config" />',
        },
        VTabs: {
          template: '<div data-testid="tabs"><slot /></div>',
        },
        VTab: {
          template: '<button type="button"><slot /></button>',
        },
        VWindow: {
          template: '<div data-testid="window"><slot /></div>',
        },
        VWindowItem: {
          template: '<div><slot /></div>',
        },
      },
    },
    props: {
      projectName: 'arbodat',
      validationResult,
      loading: false,
      availableEntities: ['analysis_entity'],
    },
  })
}

describe('ValidationPanel', () => {
  it('forwards the column focus from a direct-FK issue', async () => {
    const message = {
      severity: 'error' as const,
      entity: 'sample',
      field: 'dataset_id',
      code: 'DIRECT_FK_OUTPUT_COLUMN_MISSING',
      message: "Entity 'sample' must output target FK column 'dataset_id'.",
    }
    const wrapper = mountValidationPanel({
      is_valid: false,
      errors: [message],
      warnings: [],
      info: [],
      error_count: 1,
      warning_count: 0,
    })

    await wrapper.find('tbody > tr.v-data-table__tr').trigger('click')
    await wrapper.find('.direct-fk-column-action').trigger('click')

    expect(wrapper.emitted('open-entity')?.[0]).toEqual(['sample', { field: 'columns', column: 'dataset_id' }])
  })

  it('forwards troubleshooter actions from validation messages', async () => {
    const warning = {
      severity: 'warning' as const,
      entity: 'orders',
      message: 'Link changed the row count.',
      code: 'ROW_COUNT_MISMATCH',
      metadata: {
        fk_index: 0,
        fk_signature: 'saved-signature',
        link_pass: 'initial',
        join_type: 'inner',
      },
    }
    const wrapper = mountValidationPanel({
      is_valid: true,
      errors: [],
      warnings: [warning],
      info: [],
      error_count: 0,
      warning_count: 1,
    })

    await wrapper.find('tbody > tr.v-data-table__tr').trigger('click')
    await wrapper.find('.link-troubleshooter-action').trigger('click')

    expect(wrapper.emitted('troubleshoot')?.[0]).toEqual([warning])
  })

  it('turns off link troubleshooting for sample data results', async () => {
    const warning = {
      severity: 'warning' as const,
      entity: 'orders',
      message: 'Link changed the row count.',
      code: 'ROW_COUNT_MISMATCH',
      metadata: {
        fk_index: 0,
        fk_signature: 'saved-signature',
        link_pass: 'initial',
        join_type: 'inner',
      },
    }
    const wrapper = mountValidationPanel({
      is_valid: true,
      errors: [],
      warnings: [warning],
      info: [],
      error_count: 0,
      warning_count: 1,
      validation_mode: 'sample',
    })

    await wrapper.find('tbody > tr.v-data-table__tr').trigger('click')

    expect(wrapper.find('.link-troubleshooter-action').exists()).toBe(false)
    expect(wrapper.find('.integrity-troubleshoot-refusal').text()).toContain('turned off for sample data')
  })

  it('renders merged-entity issues grouped by entity and branch', async () => {
    const validationResult: ValidationResult = {
      is_valid: false,
      errors: [
        {
          severity: 'error',
          entity: 'analysis_entity',
          branch_name: 'abundance',
          branch_source: 'abundance_source',
          message: 'Branch issue',
          code: 'MERGED_BRANCH_SOURCE_NOT_FOUND',
          category: 'structural',
          priority: 'high',
        },
      ],
      warnings: [
        {
          severity: 'warning',
          entity: 'analysis_entity',
          message: 'Entity-level warning',
          code: 'MERGED_WARNING',
          category: 'structural',
          priority: 'medium',
        },
      ],
      error_count: 1,
      warning_count: 1,
      info: [
        {
          severity: 'info',
          entity: 'location',
          message: 'Conditional foreign key is awaiting reconciliation',
          code: 'CONDITIONAL_FK_AWAITING_RECONCILIATION',
          category: 'conformance',
          priority: 'high',
        },
      ],
    }

    const wrapper = mountValidationPanel(validationResult)

    expect(wrapper.text()).toContain('analysis_entity')
    expect(wrapper.text()).toContain('abundance (abundance_source)')
    expect(wrapper.text()).toContain('Branch issue')
    expect(wrapper.text()).toContain('Entity-level warning')
    expect(wrapper.text()).toContain('Conditional foreign key is awaiting reconciliation')
    expect(wrapper.text()).toContain('1 informational message')
    expect(wrapper.text()).toContain('All Issues 3')
    expect(wrapper.text()).toContain('Validation Failed')
    expect(wrapper.find('button[value="execution"]').exists()).toBe(false)
  })

  it('shows an informational conditional result without calling it passed', () => {
    const wrapper = mountValidationPanel({
      is_valid: true,
      errors: [],
      warnings: [],
      info: [
        {
          severity: 'info',
          entity: 'location',
          message: 'Conditional foreign key is awaiting reconciliation',
          code: 'CONDITIONAL_FK_AWAITING_RECONCILIATION',
          category: 'conformance',
        },
      ],
      error_count: 0,
      warning_count: 0,
    })

    expect(wrapper.text()).toContain('Conditional checks await reconciliation')
    expect(wrapper.text()).toContain('Conditional foreign key is awaiting reconciliation')
    expect(wrapper.text()).not.toContain('Validation Passed')
  })

  it('shows the selected mode and completed execution separately from findings', () => {
    const wrapper = mountValidationPanel({
      is_valid: false,
      errors: [
        {
          severity: 'error',
          entity: 'sample',
          message: 'A data quality issue',
          category: 'data',
        },
      ],
      warnings: [],
      info: [],
      error_count: 1,
      warning_count: 0,
      validation_mode: 'sample',
      status: 'completed',
      entity_statuses: {
        sample: { status: 'completed' },
      },
    })

    const executionTab = wrapper.find('button[value="execution"]')
    const executionPanel = wrapper.find('div[value="execution"]')

    expect(executionTab.exists()).toBe(true)
    expect(executionPanel.text()).toContain('Data Validation Execution')
    expect(executionPanel.text()).toContain('Mode: Sample')
    expect(wrapper.text()).toContain('Mode: Sample')
    expect(wrapper.text()).toContain('Run status: completed')
    expect(wrapper.text()).not.toContain('Validation Findings')
    expect(wrapper.text()).toContain('Validation Failed')
  })

  it('shows failed and skipped entity reasons for a partial run', () => {
    const wrapper = mountValidationPanel({
      is_valid: false,
      errors: [],
      warnings: [],
      info: [],
      error_count: 0,
      warning_count: 0,
      validation_mode: 'complete',
      status: 'partial',
      status_reason: 'One or more entity checks failed or were skipped.',
      entity_statuses: {
        root: { status: 'failed', reason: 'Preview failed' },
        dependent: { status: 'skipped', reason: 'Skipped because root failed.' },
        independent: { status: 'completed' },
      },
    })

    expect(wrapper.text()).toContain('Mode: Complete')
    expect(wrapper.text()).toContain('Run status: partial')
    expect(wrapper.text()).toContain('One or more entity checks failed or were skipped.')
    expect(wrapper.text()).toContain('Preview failed')
    expect(wrapper.text()).toContain('Skipped because root failed.')
    expect(wrapper.text()).toContain('Data quality checks incomplete')
  })

  it.each([
    ['failed', 'Full normalization failed'],
    ['skipped', 'Structural errors prevent data validation'],
  ] as const)('shows the %s data validation reason', (status, reason) => {
    const wrapper = mountValidationPanel({
      is_valid: false,
      errors: [],
      warnings: [],
      info: [],
      error_count: 0,
      warning_count: 0,
      validation_mode: 'complete',
      status,
      status_reason: reason,
      entity_statuses: {
        sample: { status: status === 'failed' ? 'failed' : 'skipped', reason },
      },
    })

    expect(wrapper.text()).toContain(`Run status: ${status}`)
    expect(wrapper.text()).toContain(reason)
  })
})
