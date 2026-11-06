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
  const item = wrapper.findAll('tbody > tr.v-data-table__tr')[index]
  if (!item) {
    throw new Error(`expected a validation message row at index ${index}`)
  }
  return item
}

function expandButtonAt(wrapper: MessageListWrapper, index: number) {
  return itemAt(wrapper, index).find('.validation-message-expand')
}

describe('ValidationMessageList', () => {
  it('renders every message in a collapsed row by default', () => {
    const wrapper = mountList()

    expect(wrapper.findAll('tbody > tr.v-data-table__tr')).toHaveLength(2)
    expect(wrapper.text()).toContain(longMessage)
    expect(wrapper.text()).toContain('Short warning')
    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('.validation-message-details-row').exists()).toBe(false)
  })

  it('uses table headers without a pagination footer', () => {
    const wrapper = mountList()
    const headerText = wrapper.find('thead').text()

    expect(headerText).toContain('Severity')
    expect(headerText).toContain('Message')
    expect(headerText).toContain('Location')
    expect(headerText).toContain('Category')
    expect(wrapper.find('.v-data-table-footer').exists()).toBe(false)
  })

  it('marks informational messages with their severity', () => {
    const wrapper = mountList([{ severity: 'info', message: 'Awaiting reconciliation' }])

    expect(itemAt(wrapper, 0).find('[data-severity]').attributes('data-severity')).toBe('info')
    expect(itemAt(wrapper, 0).text()).toContain('Info')
    expect(wrapper.text()).toContain('Awaiting reconciliation')
  })

  it('expands a row on click and shows the suggestion inline', async () => {
    const wrapper = mountList()

    await itemAt(wrapper, 0).trigger('click')

    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.validation-message-details-row').exists()).toBe(true)
    expect(wrapper.text()).toContain('Suggestion:')
    expect(wrapper.text()).toContain('Point the branch at an existing source')
  })

  it('collapses an expanded row on a second click', async () => {
    const wrapper = mountList()

    await itemAt(wrapper, 0).trigger('click')
    await itemAt(wrapper, 0).trigger('click')

    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('.validation-message-details-row').exists()).toBe(false)
  })

  it('expands rows independently', async () => {
    const wrapper = mountList()

    await itemAt(wrapper, 1).trigger('click')

    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('false')
    expect(expandButtonAt(wrapper, 1).attributes('aria-expanded')).toBe('true')
  })

  it('emits open-entity without toggling the row when the entity link is clicked', async () => {
    const wrapper = mountList()

    await wrapper.find('.validation-entity-link').trigger('click')

    expect(wrapper.emitted('open-entity')?.[0]).toEqual(['analysis_entity'])
    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('false')
  })

  it('shows the troubleshooter only for candidates and keeps a candidate row expanded', async () => {
    const candidate: ValidationError = {
      severity: 'warning',
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
    const wrapper = mountList([candidate])

    await itemAt(wrapper, 0).trigger('click')
    const action = wrapper.find('.link-troubleshooter-action')
    expect(action.text()).toContain('Troubleshoot link')
    await action.trigger('click')

    expect(wrapper.emitted('troubleshoot')?.[0]).toEqual([candidate])
    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('true')

    const nonCandidate = mountList([messages[0]!])
    await itemAt(nonCandidate, 0).trigger('click')
    expect(nonCandidate.find('.link-troubleshooter-action').exists()).toBe(false)
  })

  it('offers the troubleshooter for an integrity candidate and emits the original message', async () => {
    const candidate: ValidationError = {
      severity: 'warning',
      entity: 'orders',
      message: "2 foreign key value(s) not found in 'customers'",
      code: 'FK_DATA_INTEGRITY',
      metadata: { fk_index: 0, fk_signature: 'saved-signature', orphan_count: 2 },
    }
    const wrapper = mountList([candidate])

    await itemAt(wrapper, 0).trigger('click')
    const action = wrapper.find('.link-troubleshooter-action')
    expect(action.text()).toContain('Troubleshoot link')
    await action.trigger('click')

    expect(wrapper.emitted('troubleshoot')?.[0]).toEqual([candidate])
    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.integrity-troubleshoot-refusal').exists()).toBe(false)
  })

  it('explains a locally unusable integrity warning instead of offering the action', async () => {
    const malformed: ValidationError = {
      severity: 'warning',
      entity: 'orders',
      message: "2 foreign key value(s) not found in 'customers'",
      code: 'FK_DATA_INTEGRITY',
      metadata: { orphan_count: 2 },
    }
    const wrapper = mountList([malformed])

    await itemAt(wrapper, 0).trigger('click')

    expect(wrapper.find('.link-troubleshooter-action').exists()).toBe(false)
    expect(wrapper.find('.integrity-troubleshoot-refusal').text()).toContain('does not record which saved link')
    expect(wrapper.emitted('troubleshoot')).toBeUndefined()
  })

  it('does not show an integrity refusal for unrelated warnings', async () => {
    const wrapper = mountList([messages[0]!])

    await itemAt(wrapper, 0).trigger('click')

    expect(wrapper.find('.link-troubleshooter-action').exists()).toBe(false)
    expect(wrapper.find('.integrity-troubleshoot-refusal').exists()).toBe(false)
  })

  it('collapses expanded rows when the message list changes', async () => {
    const wrapper = mountList()

    await itemAt(wrapper, 0).trigger('click')
    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('true')

    await wrapper.setProps({ messages: [{ severity: 'error', message: 'Replacement message' }] })

    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('.validation-message-details-row').exists()).toBe(false)
  })

  it('offers the troubleshooter action for an integrity candidate', async () => {
    const candidate: ValidationError = {
      severity: 'warning',
      entity: 'orders',
      message: "2 foreign key value(s) not found in 'customers'",
      code: 'FK_DATA_INTEGRITY',
      metadata: { fk_index: 1, fk_signature: 'saved-signature', orphan_count: 2, join_type: 'right' },
    }
    const wrapper = mountList([candidate])

    await itemAt(wrapper, 0).trigger('click')
    const action = wrapper.find('.link-troubleshooter-action')
    expect(action.text()).toContain('Troubleshoot link')
    await action.trigger('click')

    expect(wrapper.emitted('troubleshoot')?.[0]).toEqual([candidate])
    expect(wrapper.find('.integrity-troubleshoot-refusal').exists()).toBe(false)
    expect(expandButtonAt(wrapper, 0).attributes('aria-expanded')).toBe('true')
  })

  it('explains an integrity warning that has no usable saved-link identity', async () => {
    const malformed: ValidationError = {
      severity: 'warning',
      entity: 'orders',
      message: "2 foreign key value(s) not found in 'customers'",
      code: 'FK_DATA_INTEGRITY',
      metadata: { orphan_count: 2 },
    }
    const wrapper = mountList([malformed])

    await itemAt(wrapper, 0).trigger('click')

    expect(wrapper.find('.link-troubleshooter-action').exists()).toBe(false)
    const refusal = wrapper.find('.integrity-troubleshoot-refusal')
    expect(refusal.exists()).toBe(true)
    expect(refusal.text()).toContain('does not record which saved link')
  })

  it('leaves unrelated warnings without an action or a refusal', async () => {
    const wrapper = mountList(messages)

    await itemAt(wrapper, 0).trigger('click')

    expect(wrapper.find('.link-troubleshooter-action').exists()).toBe(false)
    expect(wrapper.find('.integrity-troubleshoot-refusal').exists()).toBe(false)
  })
})
