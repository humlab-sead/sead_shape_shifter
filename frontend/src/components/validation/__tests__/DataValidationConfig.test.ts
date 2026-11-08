import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import DataValidationConfig from '../DataValidationConfig.vue'

const vuetify = createVuetify({ components, directives })

function mountConfig() {
  return mount(DataValidationConfig, {
    global: {
      plugins: [vuetify],
    },
    props: {
      availableEntities: ['orders'],
      loading: false,
    },
  })
}

describe('DataValidationConfig', () => {
  it('describes the empty-result check as a warning about entities with no data', () => {
    const wrapper = mountConfig()

    expect(wrapper.text()).toContain('Warn on Empty Results')
    expect(wrapper.text()).toContain('Warn when an entity returns no data')
    expect(wrapper.text()).not.toContain('Non-Empty Result')
  })

  it('runs every selectable check by default', async () => {
    const wrapper = mountConfig()

    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('run')).toEqual([
      [
        {
          validationMode: 'complete',
          validators: ['column_exists', 'natural_key_uniqueness', 'non_empty_result'],
        },
      ],
    ])
  })

  it('omits a check the user unchecks from the run request', async () => {
    const wrapper = mountConfig()

    await wrapper.find('input[type="checkbox"][value="non_empty_result"]').setValue(false)
    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('run')?.[0]?.[0]).toMatchObject({
      validators: ['column_exists', 'natural_key_uniqueness'],
    })
  })

  it('sends an empty check list when every selectable check is unchecked', async () => {
    const wrapper = mountConfig()

    for (const value of ['column_exists', 'natural_key_uniqueness', 'non_empty_result']) {
      await wrapper.find(`input[type="checkbox"][value="${value}"]`).setValue(false)
    }
    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('run')?.[0]?.[0]).toMatchObject({ validators: [] })
  })

  it('restores every check on reset', async () => {
    const wrapper = mountConfig()

    await wrapper.find('input[type="checkbox"][value="non_empty_result"]').setValue(false)
    const resetButton = wrapper.findAll('button').find((button) => button.text().includes('Reset to Defaults'))
    await resetButton?.trigger('click')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('run')?.[0]?.[0]).toMatchObject({
      validators: ['column_exists', 'natural_key_uniqueness', 'non_empty_result'],
    })
  })
})
