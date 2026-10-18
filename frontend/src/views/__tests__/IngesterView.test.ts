import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, reactive, toRefs } from 'vue'
import { mount } from '@vue/test-utils'

import IngesterView from '../IngesterView.vue'
import IngesterList from '@/components/ingester/IngesterList.vue'
import type { IngesterMetadata } from '@/types/ingester'

vi.mock('pinia', async () => {
  const actual = await vi.importActual<typeof import('pinia')>('pinia')

  return {
    ...actual,
    storeToRefs: (store: object) => toRefs(store),
  }
})

const ingesterStore = reactive({
  ingesters: [] as IngesterMetadata[],
  selectedIngester: null as IngesterMetadata | null,
  loading: false,
  fetchIngesters: vi.fn(async () => {}),
  selectIngester: vi.fn((key: string) => {
    ingesterStore.selectedIngester = ingesterStore.ingesters.find((ingester) => ingester.key === key) ?? null
  }),
})

vi.mock('@/stores/ingester', () => ({
  useIngesterStore: () => ingesterStore,
}))

const changeRequest: IngesterMetadata = {
  key: 'sead_change_request',
  name: 'SEAD Change Request',
  description: 'Uses a saved project',
  version: '1.0.0',
  supported_formats: ['xlsx'],
}

const ordinaryIngester: IngesterMetadata = {
  key: 'ordinary',
  name: 'Ordinary Ingester',
  description: 'Project-independent',
  version: '1.0.0',
  supported_formats: ['xlsx'],
}

const slotStub = {
  template: '<div><slot /><slot name="prepend" /><slot name="append" /></div>',
}

const stubs = {
  VContainer: slotStub,
  VRow: slotStub,
  VCol: slotStub,
  VOverlay: slotStub,
  VProgressCircular: true,
  VCard: slotStub,
  VCardTitle: slotStub,
  VCardText: slotStub,
  VList: slotStub,
  VListItem: {
    name: 'VListItem',
    template: '<div class="v-list-item"><slot /><slot name="prepend" /><slot name="append" /></div>',
  },
  VListItemTitle: slotStub,
  VListItemSubtitle: slotStub,
  VAlert: slotStub,
  VChip: slotStub,
  VIcon: true,
  IngesterForm: {
    name: 'IngesterForm',
    props: ['excludedIngesterKeys'],
    template: '<div data-test="ingester-form" />',
  },
  IngesterList: {
    name: 'IngesterList',
    props: ['excludedIngesterKeys'],
    template: '<div data-test="ingester-list" />',
  },
}

describe('IngesterView', () => {
  beforeEach(() => {
    ingesterStore.ingesters = [changeRequest, ordinaryIngester]
    ingesterStore.selectedIngester = changeRequest
    ingesterStore.loading = false
    ingesterStore.fetchIngesters.mockClear()
    ingesterStore.selectIngester.mockClear()
  })

  it('replaces a Change Request selection retained from Project Dispatch', async () => {
    const wrapper = mount(IngesterView, { global: { stubs } })
    await nextTick()

    expect(ingesterStore.selectedIngester).toEqual(ordinaryIngester)
    expect(wrapper.find('[data-test="ingester-form"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="ingester-list"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Open that project and use its Dispatch tab')
  })

  it('clears a stale Change Request selection when no other ingester is registered', async () => {
    ingesterStore.ingesters = [changeRequest]

    const wrapper = mount(IngesterView, { global: { stubs } })
    await nextTick()

    expect(ingesterStore.selectedIngester).toBeNull()
    expect(wrapper.find('[data-test="ingester-form"]').exists()).toBe(false)
  })
})

describe('IngesterList exclusions', () => {
  beforeEach(() => {
    ingesterStore.ingesters = [changeRequest, ordinaryIngester]
    ingesterStore.selectedIngester = ordinaryIngester
  })

  it('shows only permitted entries and reports when the permitted list is empty', async () => {
    const wrapper = mount(IngesterList, {
      props: { excludedIngesterKeys: ['sead_change_request'] },
      global: { stubs },
    })

    expect(wrapper.text()).toContain('Ordinary Ingester')
    expect(wrapper.text()).not.toContain('SEAD Change Request')
    expect(wrapper.findAllComponents({ name: 'VListItem' })).toHaveLength(1)

    ingesterStore.ingesters = [changeRequest]
    await nextTick()

    expect(wrapper.findAllComponents({ name: 'VListItem' })).toHaveLength(0)
    expect(wrapper.text()).toContain('No ingesters available')
  })
})
