import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
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

const getIconButtons = (wrapper: ReturnType<typeof mountBranchEditor>) => {
  return wrapper.findAllComponents({ name: 'VBtn' }).filter((button) => typeof button.props('icon') === 'string')
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
    // Find button by text content
    const buttons = wrapper.findAll('button')
    const addButton = buttons.find((b) => b.text().includes('Add Branch'))
    expect(addButton).toBeDefined()
    await addButton!.trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    const emitted = wrapper.emitted('update:modelValue')! as Array<[BranchConfig[]]>
    expect(emitted.length).toBeGreaterThan(0)
    expect(emitted[0]![0]).toHaveLength(1)
    expect(emitted[0]![0][0]).toMatchObject({ name: '', source: '' })
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
    const emitted = wrapper.emitted('update:modelValue')! as Array<[BranchConfig[]]>
    const lastEmit = emitted[emitted.length - 1]![0]
    // The first branch has empty keys → should be omitted in serialized output
    const dendroEmit = lastEmit.find((b) => b.name === 'dendro')
    expect(dendroEmit).toBeTruthy()
    expect(dendroEmit?.keys).toBeUndefined()
  })

  it('emits updated branches when removing and reordering branches', async () => {
    const branches: BranchConfig[] = [
      { name: 'dendro', source: 'dendro_analysis', keys: ['sample_name'] },
      { name: 'ceramics', source: 'ceramics_analysis', keys: ['sample_name'] },
    ]
    const wrapper = mountBranchEditor({ modelValue: branches })

    const iconButtons = getIconButtons(wrapper)
    const downButtons = iconButtons.filter((button) => button.props('icon') === 'mdi-arrow-down')
    expect(downButtons).toHaveLength(2)

    await downButtons[0]!.trigger('click')

    const emitted = wrapper.emitted('update:modelValue')! as Array<[BranchConfig[]]>
    expect(emitted.at(-1)?.[0].map((branch) => branch.name)).toEqual(['ceramics', 'dendro'])

    const updatedBranches = emitted.at(-1)![0]
    await wrapper.setProps({ modelValue: updatedBranches })
    await nextTick()

    const deleteButtons = getIconButtons(wrapper).filter((button) => button.props('icon') === 'mdi-delete')
    expect(deleteButtons).toHaveLength(2)

    await deleteButtons[0]!.trigger('click')

    const removedEmit = (wrapper.emitted('update:modelValue')! as Array<[BranchConfig[]]>).at(-1)?.[0]
    expect(removedEmit).toHaveLength(1)
    expect(removedEmit?.[0]).toMatchObject({ name: 'dendro', source: 'dendro_analysis', keys: ['sample_name'] })
  })

  it('emits inline edits for branch name, source entity, and keys', async () => {
    const branches: BranchConfig[] = [{ name: 'draft', source: 'dendro_analysis', keys: ['sample_name'] }]
    const wrapper = mountBranchEditor({ modelValue: branches })

    const expansionTitle = wrapper.find('.v-expansion-panel-title')
    expect(expansionTitle.exists()).toBe(true)
    await expansionTitle.trigger('click')
    await nextTick()

    const textField = wrapper.findComponent({ name: 'VTextField' })
    const autocomplete = wrapper.findComponent({ name: 'VAutocomplete' })
    const combobox = wrapper.findComponent({ name: 'VCombobox' })

    expect(textField.exists()).toBe(true)
    expect(autocomplete.exists()).toBe(true)
    expect(combobox.exists()).toBe(true)

    textField.vm.$emit('update:modelValue', 'abundance')
    await nextTick()

    autocomplete.vm.$emit('update:modelValue', 'ceramics_analysis')
    await nextTick()

    combobox.vm.$emit('update:modelValue', ['sample_name', 'ceramic_type'])
    await nextTick()

    const emitted = wrapper.emitted('update:modelValue')! as Array<[BranchConfig[]]>
    const lastEmit = emitted.at(-1)?.[0]

    expect(lastEmit).toHaveLength(1)
    expect(lastEmit?.[0]).toMatchObject({
      name: 'abundance',
      source: 'ceramics_analysis',
      keys: ['sample_name', 'ceramic_type'],
    })
  })
})
