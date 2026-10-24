import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import type { ColumnReferenceResolveResponse } from '@/api/entities'
import ColumnReferenceCombobox from '../ColumnReferenceCombobox.vue'

const apiMocks = vi.hoisted(() => ({
  complete: vi.fn(),
  resolve: vi.fn(),
}))

vi.mock('@/api/entities', () => ({
  entitiesApi: {
    completeColumnReferences: apiMocks.complete,
    resolveColumnReference: apiMocks.resolve,
  },
}))

const ComboboxStub = {
  name: 'VCombobox',
  props: ['modelValue', 'items', 'search', 'disabled'],
  emits: ['update:modelValue', 'update:search'],
  template: `
    <div>
      <input
        aria-label="Search"
        :value="search"
        @input="$emit('update:search', $event.target.value)"
        @blur="$emit('update:modelValue', [...modelValue, search])"
        @keydown.enter.prevent="$emit('update:modelValue', [...modelValue, items.find((item) => item.startsWith(search)) || search]); $emit('update:search', '')"
      />
      <button
        v-for="item in items"
        :key="item"
        type="button"
        @click="$emit('update:modelValue', [...modelValue, item]); $emit('update:search', '')"
      >
        {{ item }}
      </button>
      <slot
        v-for="(item, index) in modelValue"
        name="chip"
        :key="index"
        :item="{ value: item, title: item }"
        :index="index"
        :props="{ text: item }"
      />
      <slot name="message" />
    </div>
  `,
}

const stubs = {
  VCombobox: ComboboxStub,
  VChip: {
    inheritAttrs: false,
    template: '<span v-bind="$attrs"><slot /><slot name="append" /></span>',
  },
  VBtn: {
    inheritAttrs: false,
    emits: ['click'],
    template:
      '<button v-bind="$attrs" type="button" @click="$emit(\'click\', $event)" @keydown.enter="$emit(\'click\', $event)" @keydown.space="$emit(\'click\', $event)"><slot /></button>',
  },
  VCard: { template: '<section><slot /></section>' },
  VAlert: { template: '<div><slot /></div>' },
  VProgressLinear: { template: '<div />' },
}

const baseProps = {
  modelValue: [] as string[],
  items: ['ordinary_column'],
  projectName: 'demo',
  entityName: 'sample',
  entityDraft: { columns: ['sample_name'] },
  editedFieldPath: 'entities.sample.keys',
}

function mountPicker(props: typeof baseProps & { modelValue?: string[] }) {
  const Parent = defineComponent({
    setup() {
      const modelValue = ref(props.modelValue ?? [])
      return () =>
        h(ColumnReferenceCombobox, {
          ...props,
          modelValue: modelValue.value,
          'onUpdate:modelValue': (value: string[]) => {
            modelValue.value = value
          },
        })
    },
  })
  return mount(Parent, { global: { stubs } }).findComponent(ColumnReferenceCombobox)
}

describe('ColumnReferenceCombobox', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    apiMocks.complete.mockReset()
    apiMocks.resolve.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('offers progressive reference choices and keeps intermediate paths out of the model', async () => {
    apiMocks.complete.mockImplementation(async (_project: string, _entity: string, request: { prefix: string }) => {
      if (request.prefix === '@value') return { candidates: ['@value: entities.'] }
      if (request.prefix.endsWith('entities.')) return { candidates: ['@value: entities.site.'] }
      return { candidates: ['@value: entities.site.keys'] }
    })
    const wrapper = mountPicker(baseProps)
    const search = wrapper.get('input[aria-label="Search"]')

    await search.setValue('@value')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '@value: entities.')
      ?.trigger('click')
    await flushPromises()

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('@value: entities.')

    await search.setValue('@value: entities.si')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '@value: entities.site.')
      ?.trigger('click')
    await flushPromises()
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()

    await search.setValue('@value: entities.site.k')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await search.trigger('keydown.enter')
    await flushPromises()

    expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toEqual(['@value: entities.site.keys'])
    expect(apiMocks.complete).toHaveBeenCalledWith(
      'demo',
      'sample',
      expect.objectContaining({
        prefix: '@value: entities.site.k',
        edited_field_path: 'entities.sample.keys',
      })
    )
  })

  it('does not store incomplete reference prefixes when focus leaves the combobox', async () => {
    const wrapper = mountPicker(baseProps)
    const search = wrapper.get('input[aria-label="Search"]')

    for (const prefix of ['@value', '@value: entities.', '@value: entities.site']) {
      await search.setValue(prefix)
      await search.trigger('blur')
      await flushPromises()
    }

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(apiMocks.resolve).not.toHaveBeenCalled()
  })

  it('inspects ordered columns on demand without changing saved chips', async () => {
    const directive = '@value: entities.site.keys'
    const response: ColumnReferenceResolveResponse = {
      directive,
      path: 'entities.site.keys',
      status: 'resolved',
      columns: ['first', 'nested_name', 'first'],
    }
    apiMocks.resolve.mockResolvedValue(response)
    const wrapper = mountPicker({ ...baseProps, modelValue: ['literal', directive] })

    await wrapper.get(`button[aria-label="Inspect ${directive}"]`).trigger('click')
    await flushPromises()

    expect(apiMocks.resolve).toHaveBeenCalledWith('demo', 'sample', {
      entity_draft: baseProps.entityDraft,
      directive,
    })
    expect(wrapper.findAll('[data-testid="reference-inspection"] li').map((item) => item.text())).toEqual([
      'first',
      'nested_name',
      'first',
    ])
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(wrapper.emitted('inspect-reference')).toHaveLength(1)
  })

  it('marks overlapping expanded columns and replaces only the inspected duplicate chip', async () => {
    const directive = '@value: entities.site.keys'
    apiMocks.resolve.mockResolvedValue({
      directive,
      path: 'entities.site.keys',
      status: 'resolved',
      columns: ['shared', 'other', 'shared'],
    })
    const wrapper = mountPicker({
      ...baseProps,
      modelValue: ['before', directive, directive, 'after'],
      validationIssues: [
        {
          severity: 'warning',
          entity: 'sample',
          field: 'unnest.value_vars',
          message: 'The ID and Value Variables overlap.',
          code: 'UNNEST_VARIABLE_OVERLAP',
          related_columns: ['shared'],
        },
      ],
    } as typeof baseProps & { modelValue: string[] })

    const inspectButtons = wrapper.findAll(`button[aria-label="Inspect ${directive}"]`)
    await inspectButtons[1]?.trigger('click')
    await flushPromises()

    const expandedRows = wrapper.findAll('[data-testid="reference-inspection"] li')
    expect(expandedRows).toHaveLength(3)
    expect(expandedRows[0]?.text()).toContain('warning')
    expect(expandedRows[0]?.text()).toContain('The ID and Value Variables overlap.')
    expect(expandedRows[1]?.text()).toBe('other')
    expect(expandedRows[2]?.text()).toContain('warning')
    expect(wrapper.text()).toContain('will not follow later source changes')

    await wrapper.get('[data-testid="replace-reference"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toEqual([
      'before',
      directive,
      'shared',
      'other',
      'shared',
      'after',
    ])
    expect(wrapper.emitted('replace-reference')?.[0]?.[0]).toEqual({
      fieldPath: 'entities.sample.keys',
      before: ['before', directive, directive, 'after'],
      after: ['before', directive, 'shared', 'other', 'shared', 'after'],
    })
  })

  it('allows replacing a resolved reference that returns no columns', async () => {
    const directive = '@value: entities.site.columns'
    apiMocks.resolve.mockResolvedValue({ directive, path: 'entities.site.columns', status: 'resolved', columns: [] })
    const wrapper = mountPicker({ ...baseProps, modelValue: ['before', directive, 'after'] })

    await wrapper.get(`button[aria-label="Inspect ${directive}"]`).trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="replace-reference"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toEqual(['before', 'after'])
  })

  it('checks a manually committed path and displays unresolved and request errors separately', async () => {
    apiMocks.resolve
      .mockResolvedValueOnce({
        directive: '@value: entities.site.missing',
        path: 'entities.site.missing',
        status: 'unresolved',
        reason_code: 'missing_path',
        reason: 'The requested path is missing.',
      })
      .mockRejectedValueOnce(new Error('read denied'))
    const wrapper = mountPicker(baseProps)
    const search = wrapper.get('input[aria-label="Search"]')

    await search.setValue('@value: entities.site.missing')
    await search.trigger('keydown.enter')
    await flushPromises()
    expect(wrapper.text()).toContain('The requested path is missing.')
    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toEqual(['@value: entities.site.missing'])

    await wrapper.get('button[aria-label="Inspect @value: entities.site.missing"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('read denied')
  })

  it('shows an empty result and opens inspection with the keyboard', async () => {
    const directive = '@value: entities.site.columns'
    apiMocks.resolve.mockResolvedValue({
      directive,
      path: 'entities.site.columns',
      status: 'resolved',
      columns: [],
    })
    const wrapper = mountPicker({ ...baseProps, modelValue: [directive] })
    const inspectButton = wrapper.get(`button[aria-label="Inspect ${directive}"]`)

    await inspectButton.trigger('keydown.enter')
    await flushPromises()

    expect(apiMocks.resolve).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('This reference returns no columns.')
  })

  it('does not add reference actions for legacy expressions and starts keyboard entry from the button', async () => {
    const wrapper = mountPicker({ ...baseProps, modelValue: ["['literal'] + @value: entities.site.keys"] })

    expect(wrapper.find('[aria-label^="Inspect"]').exists()).toBe(false)
    await wrapper.get('[data-testid="insert-reference"]').trigger('click')
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('@value')
  })
})
