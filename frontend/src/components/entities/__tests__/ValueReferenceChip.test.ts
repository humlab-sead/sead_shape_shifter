import { defineComponent, h, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { VCombobox } from 'vuetify/components'
import type { EntityResponse } from '@/api/entities'
import ValueReferenceChip from '../ValueReferenceChip.vue'

const vuetify = createVuetify({ components, directives })

function makeEntity(name: string, entity_data: Record<string, unknown>): EntityResponse {
  return { name, entity_data, etag: `${name}-etag` }
}

const MenuStub = defineComponent({
  props: { modelValue: Boolean },
  emits: ['update:modelValue'],
  setup(props, { emit, slots }) {
    return () =>
      h('div', [
        slots.activator?.({ props: { onClick: () => emit('update:modelValue', true) } }),
        props.modelValue ? h('div', slots.default?.()) : null,
      ])
  },
})

function mountReferenceCombobox(value: string, cachedEntities: EntityResponse[] | null) {
  const model = ref([value])
  const entities = ref(cachedEntities)
  const updates: unknown[] = []

  const Harness = defineComponent({
    setup() {
      return () =>
        h(
          VCombobox,
          {
            modelValue: model.value,
            items: model.value,
            multiple: true,
            chips: true,
            closableChips: true,
            'onUpdate:modelValue': (nextValue: unknown) => {
              updates.push(nextValue)
              model.value = nextValue as string[]
            },
          },
          {
            chip: ({ item, props: chipProps }: { item: { raw: unknown }; props: Record<string, unknown> }) =>
              h(ValueReferenceChip, {
                value: String(item.raw),
                chipProps,
                entities: entities.value,
              }),
          }
        )
    },
  })

  const wrapper = mount(Harness, {
    attachTo: document.body,
    global: { plugins: [vuetify], stubs: { VMenu: MenuStub } },
  })
  return { wrapper, model, entities, updates }
}

function previewText(): string {
  return document.body.textContent ?? ''
}

describe('ValueReferenceChip', () => {
  it('shows ordered cached columns only after Preview and leaves the combobox value unchanged', async () => {
    const value = '@value: entities.sample.columns'
    const { wrapper, model, updates } = mountReferenceCombobox(value, [
      makeEntity('site', { keys: ['site_id', 'site_id'], columns: ['name', '@value: entities.site.keys'] }),
      makeEntity('sample', {
        keys: '@value: entities.site.columns',
        columns: ['sample_id', '@value: entities.sample.keys'],
      }),
    ])

    expect(previewText()).not.toContain('Based on cached configuration')
    expect(model.value).toEqual([value])
    expect(updates).toEqual([])

    await wrapper.get('button[aria-label="Preview value reference"]').trigger('click')
    await flushPromises()

    expect(previewText()).toContain('Based on cached configuration')
    expect(
      Array.from(document.querySelectorAll('[data-testid="value-reference-preview-column"]')).map((node) =>
        node.textContent?.trim()
      )
    ).toEqual(['sample_id', 'name', 'site_id', 'site_id'])
    expect(previewText()).toContain(value)
    expect(model.value).toEqual([value])
    expect(updates).toEqual([])

    const closeButton = wrapper.find('.v-chip__close')
    expect(closeButton.exists()).toBe(true)
    await closeButton.trigger('click')
    await flushPromises()
    expect(model.value).toEqual([])
    wrapper.unmount()
  })

  it.each(['enter', 'space'])('opens the read-only preview with the %s key', async (key) => {
    const { wrapper } = mountReferenceCombobox('@value: entities.site.keys', [
      makeEntity('site', { keys: ['site_id'] }),
    ])

    await wrapper.get('button[aria-label="Preview value reference"]').trigger(`keydown.${key}`)
    await flushPromises()

    expect(previewText()).toContain('Based on cached configuration')
    expect(previewText()).toContain('site_id')
    wrapper.unmount()
  })

  it('shows an explicit empty result for a supported empty reference', async () => {
    const { wrapper } = mountReferenceCombobox('@value: entities.site.keys', [makeEntity('site', { keys: [] })])

    await wrapper.get('button[aria-label="Preview value reference"]').trigger('click')
    await flushPromises()

    expect(document.querySelector('[data-testid="value-reference-preview-empty"]')?.textContent).toContain(
      'This reference contains no columns.'
    )
    expect(document.querySelector('[data-testid="value-reference-preview-unavailable"]')).toBeNull()
    wrapper.unmount()
  })

  it.each([
    ['missing cache', '@value: entities.site.keys', null],
    ['missing path', '@value: entities.site.columns', [makeEntity('site', { keys: ['site_id'] })]],
    ['cycle', '@value: entities.site.keys', [makeEntity('site', { keys: '@value: entities.site.keys' })]],
    ['unsupported nested value', '@value: entities.site.keys', [makeEntity('site', { keys: ['site_id', ['nested']] })]],
    ['legacy expression', "@value: entities.site.keys + ['other']", [makeEntity('site', { keys: ['site_id'] })]],
  ])('shows no partial columns for %s', async (_caseName, value, cachedEntities) => {
    const { wrapper, model, updates } = mountReferenceCombobox(value, cachedEntities)

    await wrapper.get('button[aria-label="Preview value reference"]').trigger('click')
    await flushPromises()

    expect(document.querySelector('[data-testid="value-reference-preview-unavailable"]')?.textContent).toContain(
      'Preview unavailable'
    )
    expect(document.querySelectorAll('[data-testid="value-reference-preview-column"]')).toHaveLength(0)
    expect(previewText()).toContain(value)
    expect(model.value).toEqual([value])
    expect(updates).toEqual([])
    wrapper.unmount()
  })

  it('closes an open preview when the cache changes', async () => {
    const { wrapper, entities } = mountReferenceCombobox('@value: entities.site.keys', [
      makeEntity('site', { keys: ['site_id'] }),
    ])

    await wrapper.get('button[aria-label="Preview value reference"]').trigger('click')
    await flushPromises()
    expect(previewText()).toContain('site_id')

    entities.value = null
    await flushPromises()

    expect(previewText()).not.toContain('Based on cached configuration')
    expect(document.querySelector('[data-testid="value-reference-preview-column"]')).toBeNull()
    wrapper.unmount()
  })
})
