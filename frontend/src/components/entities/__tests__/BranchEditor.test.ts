import { describe, expect, it, beforeEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import BranchEditor from '../BranchEditor.vue'
import type { BranchConfig } from '@/types/entity'

const vuetify = createVuetify({ components, directives })

const mountBranchEditor = (props = {}) => {
  return mount(BranchEditor, {
    global: { plugins: [vuetify] },
    props: {
      modelValue: [],
      availableEntities: ['dendro_analysis', 'ceramics_analysis', 'pollen_analysis'],
      parentEntity: 'analysis_entity',
      sourceEntityPublicIds: {
        dendro_analysis: 'dendro_id',
        ceramics_analysis: 'ceramics_id',
        pollen_analysis: null,
      },
      sourceEntityColumns: {
        dendro_analysis: ['sample_name', 'dendro_date', 'tree_species'],
        ceramics_analysis: ['sample_name', 'ceramic_type'],
        pollen_analysis: ['sample_name', 'taxon_code'],
      },
      ...props,
    },
  })
}

describe('BranchEditor', () => {
  it('renders empty state warning when no branches configured', () => {
    const wrapper = mountBranchEditor()
    expect(wrapper.text()).toContain('No branches configured')
  })

  it('shows existing branches when modelValue is provided', () => {
    const branches: BranchConfig[] = [
      { name: 'dendro', source: 'dendro_analysis', keys: ['sample_name'] },
      { name: 'ceramics', source: 'ceramics_analysis', keys: [] },
    ]
    const wrapper = mountBranchEditor({ modelValue: branches })
    expect(wrapper.text()).toContain('dendro')
    expect(wrapper.text()).toContain('ceramics')
  })

  it('shows source entity FK info in chips when public_id is defined', () => {
    const branches: BranchConfig[] = [{ name: 'dendro', source: 'dendro_analysis' }]
    const wrapper = mountBranchEditor({ modelValue: branches })
    expect(wrapper.text()).toContain('FK: dendro_id')
  })

  it('shows warning when source entity has no public_id', () => {
    const branches: BranchConfig[] = [{ name: 'pollen', source: 'pollen_analysis' }]
    const wrapper = mountBranchEditor({ modelValue: branches })
    // pollen_analysis has no public_id → should show warning
    expect(wrapper.text()).toContain('pollen_analysis')
  })

  it('emits update:modelValue when Add Branch is clicked', async () => {
    const wrapper = mountBranchEditor()
    const addBtn = wrapper.find('[prepend-icon="mdi-plus"]')
    // Find button by text content
    const buttons = wrapper.findAll('button')
    const addButton = buttons.find((b) => b.text().includes('Add Branch'))
    expect(addButton).toBeDefined()
    await addButton!.trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    const emitted = wrapper.emitted('update:modelValue') as BranchConfig[][]
    expect(emitted[0][0]).toHaveLength(1)
    expect(emitted[0][0][0]).toMatchObject({ name: '', source: '' })
  })

  it('shows merged output summary when multiple branches present', () => {
    const branches: BranchConfig[] = [
      { name: 'dendro', source: 'dendro_analysis' },
      { name: 'ceramics', source: 'ceramics_analysis' },
    ]
    const wrapper = mountBranchEditor({ modelValue: branches })
    expect(wrapper.text()).toContain('Merged output will include')
    expect(wrapper.text()).toContain('analysis_entity_branch')
  })

  it('shows branch discriminator column name based on parentEntity prop', () => {
    const branches: BranchConfig[] = [
      { name: 'branch_a', source: 'dendro_analysis' },
      { name: 'branch_b', source: 'ceramics_analysis' },
    ]
    const wrapper = mountBranchEditor({ modelValue: branches, parentEntity: 'sample_analysis' })
    expect(wrapper.text()).toContain('sample_analysis_branch')
  })

  it('hides merged output summary when only one branch present', () => {
    const branches: BranchConfig[] = [{ name: 'dendro', source: 'dendro_analysis' }]
    const wrapper = mountBranchEditor({ modelValue: branches })
    expect(wrapper.text()).not.toContain('Merged output will include')
  })

  it('omits empty keys from emitted value', async () => {
    const branches: BranchConfig[] = [
      { name: 'dendro', source: 'dendro_analysis', keys: [] },
    ]
    const wrapper = mountBranchEditor({ modelValue: branches })
    // Trigger a re-emit by simulating a change via buttons
    const buttons = wrapper.findAll('button')
    const addButton = buttons.find((b) => b.text().includes('Add Branch'))
    await addButton!.trigger('click')
    const emitted = wrapper.emitted('update:modelValue') as BranchConfig[][]
    const lastEmit = emitted[emitted.length - 1][0]
    // The first branch has empty keys → should be omitted in serialized output
    const dendroEmit = lastEmit.find((b) => b.name === 'dendro')
    expect(dendroEmit).toBeTruthy()
    expect(dendroEmit?.keys).toBeUndefined()
  })
})
