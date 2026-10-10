import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import ValidationMessageList from '../ValidationMessageList.vue'
import type { ValidationError } from '@/types'

const vuetify = createVuetify({ components, directives })

const longMessage = 'This validation message is intentionally very long so that it overflows the screen width. '.repeat(
  3
)

const messages: ValidationError[] = [
  {
    severity: 'error',
    entity: 'analysis_entity',
    message: longMessage,
    code: 'MERGED_BRANCH_SOURCE_NOT_FOUND',
    suggestion: 'Point the branch at an existing source',
    category: 'structural',
    priority: 'high',
  },
  {
    severity: 'warning',
    message: 'Short warning',
  },
]

function mountList(msgs: ValidationError[] = messages) {
  return mount(ValidationMessageList, {
    global: { plugins: [vuetify] },
    props: { messages: msgs },
  })
}

type MessageListWrapper = ReturnType<typeof mountList>

function itemAt(wrapper: MessageListWrapper, index: number) {
  const item = wrapper.findAll('.validation-message-item')[index]
  if (!item) {
    throw new Error(`expected a validation message row at index ${index}`)
  }
  return item
}

describe('ValidationMessageList', () => {
  it('renders every message in a collapsed row by default', () => {
    const wrapper = mountList()

    expect(wrapper.findAll('.validation-message-item')).toHaveLength(2)
    expect(wrapper.text()).toContain(longMessage)
    expect(wrapper.text()).toContain('Short warning')
    expect(itemAt(wrapper, 0).classes()).not.toContain('validation-message-item--expanded')
  })

  it('expands a row on click and shows the suggestion inline', async () => {
    const wrapper = mountList()

    await itemAt(wrapper, 0).trigger('click')

    expect(itemAt(wrapper, 0).classes()).toContain('validation-message-item--expanded')
    expect(wrapper.text()).toContain('Suggestion:')
    expect(wrapper.text()).toContain('Point the branch at an existing source')
  })

  it('collapses an expanded row on a second click', async () => {
    const wrapper = mountList()

    await itemAt(wrapper, 0).trigger('click')
    await itemAt(wrapper, 0).trigger('click')

    expect(itemAt(wrapper, 0).classes()).not.toContain('validation-message-item--expanded')
    expect(wrapper.text()).not.toContain('Point the branch at an existing source')
  })

  it('expands rows independently', async () => {
    const wrapper = mountList()

    await itemAt(wrapper, 1).trigger('click')

    expect(itemAt(wrapper, 0).classes()).not.toContain('validation-message-item--expanded')
    expect(itemAt(wrapper, 1).classes()).toContain('validation-message-item--expanded')
  })

  it('emits open-entity without toggling the row when the entity chip is clicked', async () => {
    const wrapper = mountList()

    await wrapper.find('.validation-entity-chip').trigger('click')

    expect(wrapper.emitted('open-entity')?.[0]).toEqual(['analysis_entity'])
    expect(itemAt(wrapper, 0).classes()).not.toContain('validation-message-item--expanded')
  })

  it('collapses expanded rows when the message list changes', async () => {
    const wrapper = mountList()

    await itemAt(wrapper, 0).trigger('click')
    expect(itemAt(wrapper, 0).classes()).toContain('validation-message-item--expanded')

    await wrapper.setProps({ messages: [{ severity: 'error', message: 'Replacement message' }] })

    expect(itemAt(wrapper, 0).classes()).not.toContain('validation-message-item--expanded')
  })
})
