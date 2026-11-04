import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { defineComponent, h, onMounted, reactive, type PropType } from 'vue'

import SpecificationEditor from '../SpecificationEditor.vue'

const manifest = {
  defaultTypes: [
    { id: 'site', name: 'Site' },
    { id: 'feature_type', name: 'Feature type' },
    { id: 'taxon', name: 'Taxon' },
  ],
  reconciliation: { supportedTypes: ['site', 'feature_type'] },
  extend: {
    property_settings: [
      { name: 'place_name', entity_types: ['site'] },
      { name: 'latitude', entity_types: ['site_archive'] },
    ],
  },
}

const reconciliationStore = reactive({
  specifications: [],
  getAvailableFields: vi.fn(async () => ['site_code', 'site_name']),
  getServiceManifest: vi.fn(async () => manifest),
  createSpecification: vi.fn(async () => {}),
  updateSpecification: vi.fn(async () => {}),
})

const projectStore = reactive({
  selectedProject: { entities: { site: {} } },
})

const notificationMocks = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
}))

vi.mock('@/stores/reconciliation', () => ({
  useReconciliationStore: () => reconciliationStore,
}))

vi.mock('@/stores/project', () => ({
  useProjectStore: () => projectStore,
}))

vi.mock('@/composables/useNotification', () => ({
  useNotification: () => ({
    success: notificationMocks.success,
    error: notificationMocks.error,
  }),
}))

const VAutocompleteStub = defineComponent({
  name: 'VAutocomplete',
  props: {
    items: { type: Array as PropType<unknown[]>, default: () => [] },
    modelValue: { default: undefined },
    label: { type: String, default: '' },
    itemTitle: { type: String, default: '' },
    itemValue: { type: String, default: '' },
    disabled: { type: Boolean, default: false },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    function optionTitle(option: unknown): string {
      if (typeof option === 'string') return option
      if (typeof option !== 'object' || option === null) return String(option)
      const item = option as Record<string, unknown>
      const title = item[props.itemTitle] ?? item.name ?? item.id
      return typeof title === 'string' ? title : String(title)
    }

    function optionValue(option: unknown): string {
      if (typeof option !== 'object' || option === null) return String(option)
      const item = option as Record<string, unknown>
      return String(item[props.itemValue] ?? item.id ?? item.value)
    }

    function optionDisabled(option: unknown): boolean {
      return typeof option === 'object' && option !== null && 'disabled' in option && option.disabled === true
    }

    function select(option: unknown) {
      if (!props.disabled) emit('update:modelValue', optionValue(option))
    }

    return { optionTitle, optionValue, optionDisabled, select }
  },
  template: `
    <div class="autocomplete-stub" :data-label="label">
      <button
        v-for="(item, index) in items"
        :key="index"
        type="button"
        :data-option-value="optionValue(item)"
        :disabled="disabled || optionDisabled(item)"
        @click="select(item)"
      >
        {{ optionTitle(item) }}
      </button>
      <input :value="modelValue ?? ''" @input="$emit('update:modelValue', $event.target.value)" />
    </div>
  `,
})

const VFormStub = defineComponent({
  name: 'VForm',
  props: { modelValue: { type: Boolean, default: false } },
  emits: ['update:modelValue'],
  setup(_, { emit, expose, slots }) {
    onMounted(() => emit('update:modelValue', true))
    expose({ validate: () => true, resetValidation: () => {} })
    return () => h('form', slots.default?.())
  },
})

const YamlEditorStub = defineComponent({
  name: 'YamlEditor',
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue', 'change'],
  template: `
    <textarea
      data-testid="yaml-editor"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value); $emit('change', $event.target.value)"
    />
  `,
})

const vuetify = createVuetify({ components, directives })

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverMock)

function createSpecification(serviceType: string, propertyMappings: Record<string, string>) {
  return {
    entity_name: 'site',
    target_field: 'site_code',
    source: null,
    property_mappings: propertyMappings,
    remote: { service_type: serviceType, columns: [] },
    auto_accept_threshold: 0.95,
    review_threshold: 0.7,
    mapping_count: 0,
    property_mapping_count: Object.keys(propertyMappings).length,
  }
}

async function mountEditor(specification = createSpecification('site', {})) {
  return mount(SpecificationEditor, {
    global: {
      plugins: [vuetify],
      stubs: {
        VAutocomplete: VAutocompleteStub,
        VDialog: {
          props: ['modelValue'],
          template: '<div v-if="modelValue"><slot /></div>',
        },
        VForm: VFormStub,
        YamlEditor: YamlEditorStub,
      },
    },
    props: {
      modelValue: true,
      projectName: 'test_project',
      specification,
      isNew: false,
    },
  })
}

describe('SpecificationEditor', () => {
  beforeEach(() => {
    reconciliationStore.getAvailableFields = vi.fn(async () => ['site_code', 'site_name'])
    reconciliationStore.getServiceManifest = vi.fn(async () => manifest)
    reconciliationStore.updateSpecification = vi.fn(async () => {})
    reconciliationStore.createSpecification = vi.fn(async () => {})
    projectStore.selectedProject = { entities: { site: {} } }
    notificationMocks.success.mockReset()
    notificationMocks.error.mockReset()
  })

  it('offers only supported types and preserves saved mappings after type changes', async () => {
    const wrapper = await mountEditor(createSpecification('site', { old_property: 'site_name' }))
    await flushPromises()

    const remoteType = wrapper.get('[data-label="Remote Type *"]')
    expect(remoteType.text()).toContain('Site')
    expect(remoteType.text()).toContain('Feature type')
    expect(remoteType.text()).not.toContain('Taxon')
    expect(wrapper.find('[data-label="Source column for place_name"]').exists()).toBe(true)
    expect(wrapper.find('[data-label="Source column for old_property"]').exists()).toBe(true)
    expect(wrapper.find('[data-label="Source column for latitude"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Unsupported')
    expect((wrapper.get('[data-label="Source column for old_property"] input').element as HTMLInputElement).value).toBe(
      'site_name'
    )

    await remoteType.get('[data-option-value="feature_type"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-label="Source column for old_property"]').exists()).toBe(true)
    expect((wrapper.get('[data-label="Source column for old_property"] input').element as HTMLInputElement).value).toBe(
      'site_name'
    )
    await wrapper.get('[data-testid="remove-property-mapping-old_property"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-label="Source column for old_property"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('No properties are declared for this remote type.')
  })

  it('shows manifest failures and preserves saved type and mapping values', async () => {
    reconciliationStore.getServiceManifest = vi.fn().mockRejectedValue(new Error('Manifest unavailable'))
    const wrapper = await mountEditor(createSpecification('taxon', { family: 'site_name' }))
    await flushPromises()

    expect(wrapper.get('[data-testid="manifest-error"]').text()).toContain('Manifest unavailable')
    expect(wrapper.get('[data-label="Remote Type *"]').text()).toContain('taxon (cannot be verified)')
    expect(wrapper.get('[data-label="Remote Type *"] [data-option-value="taxon"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Cannot verify')
    expect((wrapper.get('[data-label="Source column for family"] input').element as HTMLInputElement).value).toBe(
      'site_name'
    )
  })

  it('round-trips empty mappings and applies explicit YAML removals', async () => {
    const wrapper = await mountEditor(createSpecification('site', { place_name: 'site_name', old_property: '' }))
    await flushPromises()
    const yamlTab = wrapper.findAll('button').find((button) => button.text().trim() === 'YAML')
    expect(yamlTab).toBeDefined()
    await yamlTab!.trigger('click')
    await flushPromises()

    const editor = wrapper.get('[data-testid="yaml-editor"]')
    expect((editor.element as HTMLTextAreaElement).value).toContain("old_property: ''")

    await editor.setValue(
      "remote:\n  service_type: site\nproperty_mappings:\n  place_name: site_name\n  empty_property: ''\nauto_accept_threshold: 0.95\nreview_threshold: 0.7\n"
    )
    await flushPromises()

    const formTab = wrapper.findAll('button').find((button) => button.text().trim() === 'Form')
    expect(formTab).toBeDefined()
    await formTab!.trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-label="Source column for old_property"]').exists()).toBe(false)
    expect(wrapper.find('[data-label="Source column for empty_property"]').exists()).toBe(true)
    const saveButton = wrapper.findAll('button').find((button) => button.text().trim() === 'Save')
    expect(saveButton).toBeDefined()
    await saveButton!.trigger('click')
    await flushPromises()

    expect(reconciliationStore.updateSpecification).toHaveBeenCalledWith(
      'test_project',
      'site',
      'site_code',
      expect.objectContaining({ property_mappings: { place_name: 'site_name', empty_property: '' } })
    )
  })
})
