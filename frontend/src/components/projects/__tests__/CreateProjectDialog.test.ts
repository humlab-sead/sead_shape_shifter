import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { defineComponent, h, onMounted, useAttrs } from 'vue'
import CreateProjectDialog from '../CreateProjectDialog.vue'

const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  listProviders: vi.fn(),
}))

vi.mock('@/composables', () => ({
  useProjects: () => ({ create: mocks.create, projects: { value: [] } }),
}))

vi.mock('@/api/data-providers', () => ({
  dataProvidersApi: { list: mocks.listProviders },
}))

const VFormStub = defineComponent({
  props: ['modelValue'],
  emits: ['update:modelValue'],
  setup(_, { emit, expose, slots }) {
    expose({ validate: async () => ({ valid: true }), reset: () => undefined, resetValidation: () => undefined })
    onMounted(() => emit('update:modelValue', true))
    return () => h('form', slots.default?.())
  },
})

const VTextFieldStub = defineComponent({
  props: ['modelValue', 'label'],
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () =>
      h('label', [
        props.label,
        h('input', {
          value: props.modelValue,
          onInput: (event: Event) => emit('update:modelValue', (event.target as HTMLInputElement).value),
        }),
      ])
  },
})

const VSelectStub = defineComponent({
  props: ['modelValue', 'items', 'label', 'disabled'],
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () =>
      h('label', [
        props.label,
        h(
          'select',
          {
            value: props.modelValue ?? '',
            disabled: props.disabled,
            onChange: (event: Event) => emit('update:modelValue', (event.target as HTMLSelectElement).value),
          },
          [
            h('option', { value: '' }, ''),
            ...(props.items ?? []).map((item: { title: string; value: string }) =>
              h('option', { value: item.value }, item.title)
            ),
          ]
        ),
      ])
  },
})

const VBtnStub = defineComponent({
  props: ['disabled', 'loading'],
  setup(props, { slots }) {
    const attrs = useAttrs()
    return () => h('button', { disabled: props.disabled, onClick: attrs.onClick }, slots.default?.())
  },
})

const VAlertStub = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

const globalStubs = {
  VForm: VFormStub,
  VTextField: VTextFieldStub,
  VSelect: VSelectStub,
  VBtn: VBtnStub,
  VAlert: VAlertStub,
}

const providers = [
  {
    code: 'provider-a',
    name: 'Provider A',
    schemas: [
      { provider_schema: 'schema-one', scope_name: 'provider-a/one' },
      { provider_schema: 'schema-two', scope_name: 'provider-a/two' },
    ],
  },
  {
    code: 'provider-b',
    name: 'Provider B',
    schemas: [{ provider_schema: 'schema-three', scope_name: 'provider-b/three' }],
  },
]

function selectForLabel(wrapper: ReturnType<typeof shallowMount>, label: string) {
  const field = wrapper.findAll('label').find((item) => item.text().startsWith(label))
  if (!field) throw new Error(`Missing field: ${label}`)
  return field.get('select')
}

describe('CreateProjectDialog', () => {
  beforeEach(() => {
    mocks.create.mockReset().mockResolvedValue(undefined)
    mocks.listProviders.mockReset().mockResolvedValue(providers)
  })

  it('sends the selected registered provider-schema pair', async () => {
    const wrapper = shallowMount(CreateProjectDialog, {
      props: { modelValue: false },
      global: { renderStubDefaultSlot: true, stubs: globalStubs },
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()

    await wrapper.get('input').setValue('new-project')
    await selectForLabel(wrapper, 'Data Provider').setValue('provider-a')
    await selectForLabel(wrapper, 'Provider Schema').setValue('schema-two')
    const createButton = wrapper.findAll('button').find((button) => button.text() === 'Create')
    await createButton?.trigger('click')
    await flushPromises()

    expect(mocks.create).toHaveBeenCalledWith({
      name: 'new-project',
      data_provider_code: 'provider-a',
      provider_schema: 'schema-two',
      entities: {},
    })
    expect(wrapper.emitted('created')).toEqual([['new-project']])
  })

  it('clears the schema when the provider changes', async () => {
    const wrapper = shallowMount(CreateProjectDialog, {
      props: { modelValue: false },
      global: { renderStubDefaultSlot: true, stubs: globalStubs },
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()

    await selectForLabel(wrapper, 'Data Provider').setValue('provider-a')
    await selectForLabel(wrapper, 'Provider Schema').setValue('schema-two')
    await selectForLabel(wrapper, 'Data Provider').setValue('provider-b')

    expect((selectForLabel(wrapper, 'Provider Schema').element as HTMLSelectElement).value).toBe('')
    expect(
      selectForLabel(wrapper, 'Provider Schema')
        .findAll('option')
        .map((option) => option.element.value)
    ).toEqual(['', 'schema-three'])
  })

  it('disables creation when the provider list cannot be loaded', async () => {
    mocks.listProviders.mockRejectedValueOnce(new Error('registry unavailable'))
    const wrapper = shallowMount(CreateProjectDialog, {
      props: { modelValue: false },
      global: { renderStubDefaultSlot: true, stubs: globalStubs },
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()

    const createButton = wrapper.findAll('button').find((button) => button.text() === 'Create')
    expect(createButton?.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Could not load registered data providers')
  })
})
