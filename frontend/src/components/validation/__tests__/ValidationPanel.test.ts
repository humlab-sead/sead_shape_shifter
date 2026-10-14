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
})
