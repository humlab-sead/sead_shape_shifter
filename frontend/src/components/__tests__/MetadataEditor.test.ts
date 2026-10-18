import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, h, onMounted, useAttrs } from 'vue'
import { useProjectStore } from '@/stores/project'
import MetadataEditor from '../MetadataEditor.vue'

const mocks = vi.hoisted(() => ({
  updateMetadata: vi.fn(),
  listProviders: vi.fn(),
  listTargetModels: vi.fn(),
}))

vi.mock('@/api', () => ({
  api: { projects: { updateMetadata: mocks.updateMetadata } },
}))

vi.mock('@/api/projects', () => ({
  projectsApi: { listTargetModels: mocks.listTargetModels },
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
  props: ['modelValue', 'label', 'readonly'],
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () =>
      h('label', [
        props.label,
        h('input', {
          value: props.modelValue ?? '',
          readonly: props.readonly,
          onInput: (event: Event) => emit('update:modelValue', (event.target as HTMLInputElement).value),
        }),
      ])
  },
})

const VTextareaStub = VTextFieldStub

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
            onChange: (event: Event) => emit('update:modelValue', (event.target as HTMLSelectElement).value || null),
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

const globalStubs = {
  VForm: VFormStub,
  VTextField: VTextFieldStub,
  VTextarea: VTextareaStub,
  VSelect: VSelectStub,
  VBtn: VBtnStub,
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

function createProject(providerCode: string | null, providerSchema: string | null) {
  return {
    metadata: {
      name: 'legacy-project',
      description: null,
      version: '1.0.0',
      entity_count: 0,
      data_provider_code: providerCode,
      provider_schema: providerSchema,
    },
    entities: {},
  }
}

describe('MetadataEditor', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mocks.updateMetadata.mockReset()
    mocks.listProviders.mockReset().mockResolvedValue(providers)
    mocks.listTargetModels.mockReset().mockResolvedValue([])
  })

  it('assigns an unbound project once using the selected registered pair', async () => {
    const store = useProjectStore()
    store.selectedProject = createProject(null, null)
    const assignedProject = createProject('provider-a', 'schema-two')
    mocks.updateMetadata.mockResolvedValue(assignedProject)

    const wrapper = shallowMount(MetadataEditor, {
      props: { projectName: 'legacy-project' },
      global: { renderStubDefaultSlot: true, stubs: globalStubs },
    })
    await flushPromises()

    await selectForLabel(wrapper, 'Data Provider').setValue('provider-a')
    await selectForLabel(wrapper, 'Provider Schema').setValue('schema-two')
    const saveButton = wrapper.findAll('button').find((button) => button.text() === 'Save Metadata')
    await saveButton?.trigger('click')
    await flushPromises()

    expect(mocks.updateMetadata).toHaveBeenCalledWith(
      'legacy-project',
      expect.objectContaining({
        data_provider_code: 'provider-a',
        provider_schema: 'schema-two',
      })
    )
  })

  it('shows an assigned pair as read-only fields', async () => {
    const store = useProjectStore()
    store.selectedProject = createProject('provider-a', 'schema-one')

    const wrapper = shallowMount(MetadataEditor, {
      props: { projectName: 'legacy-project' },
      global: { renderStubDefaultSlot: true, stubs: globalStubs },
    })
    await flushPromises()

    expect(
      wrapper.findAll('select').some((select) => select.element.parentElement?.textContent?.includes('Data Provider'))
    ).toBe(false)
    const providerField = wrapper.findAll('label').find((field) => field.text().startsWith('Data Provider'))
    const schemaField = wrapper.findAll('label').find((field) => field.text().startsWith('Provider Schema'))
    expect(providerField?.get('input').attributes('readonly')).toBeDefined()
    expect(providerField?.get('input').element.value).toBe('Provider A (provider-a)')
    expect(schemaField?.get('input').element.value).toBe('schema-one')
  })

  it('clears the selected schema when an unbound project changes provider', async () => {
    const store = useProjectStore()
    store.selectedProject = createProject(null, null)

    const wrapper = shallowMount(MetadataEditor, {
      props: { projectName: 'legacy-project' },
      global: { renderStubDefaultSlot: true, stubs: globalStubs },
    })
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
})
