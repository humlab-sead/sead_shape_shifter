import { flushPromises, shallowMount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProjectFileUploadCard from '../ProjectFileUploadCard.vue'

const mocks = vi.hoisted(() => ({
  listFiles: vi.fn(),
  getFileCapabilities: vi.fn(),
}))

vi.mock('@/api/projects', () => ({
  projectsApi: {
    listFiles: mocks.listFiles,
    getFileCapabilities: mocks.getFileCapabilities,
  },
}))

const VBtnStub = defineComponent({
  setup(_, { attrs, slots }) {
    return () => h('button', attrs, slots.default?.())
  },
})

const VListItemStub = defineComponent({
  props: ['title', 'subtitle'],
  setup(props, { slots }) {
    return () => h('li', [h('span', props.title), h('span', props.subtitle), slots.append?.()])
  },
})

const VChipStub = defineComponent({
  setup(_, { slots }) {
    return () => h('span', slots.default?.())
  },
})

const VAlertStub = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

const SlotStub = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

const globalStubs = {
  VBtn: VBtnStub,
  VListItem: VListItemStub,
  VChip: VChipStub,
  VAlert: VAlertStub,
  VCard: SlotStub,
  VCardTitle: SlotStub,
  VCardText: SlotStub,
  VList: SlotStub,
  VListSubheader: SlotStub,
  VIcon: SlotStub,
  VSpacer: SlotStub,
}

describe('ProjectFileUploadCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.listFiles.mockResolvedValue([
      { name: 'local.csv', path: 'local.csv', location: 'local', size_bytes: 10 },
      { name: 'shared.csv', path: 'shared.csv', location: 'global', size_bytes: 20 },
    ])
  })

  it('shows share actions only for local files and keeps shared files read-only', async () => {
    mocks.getFileCapabilities.mockResolvedValue({ can_share_with_all_projects: true })

    const wrapper = shallowMount(ProjectFileUploadCard, {
      props: { projectName: 'sample' },
      global: { stubs: globalStubs },
    })
    await flushPromises()

    expect(wrapper.find('[aria-label="Share local.csv with all projects"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Delete local.csv"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Share shared.csv with all projects"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="Delete shared.csv"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Read-only shared file')
  })

  it('hides share actions when the user lacks shared-source permission', async () => {
    mocks.getFileCapabilities.mockResolvedValue({ can_share_with_all_projects: false })

    const wrapper = shallowMount(ProjectFileUploadCard, {
      props: { projectName: 'sample' },
      global: { stubs: globalStubs },
    })
    await flushPromises()

    expect(wrapper.find('[aria-label="Share local.csv with all projects"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label="Delete local.csv"]').exists()).toBe(true)
  })
})
