import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'

import ForeignKeyEditor from '../ForeignKeyEditor.vue'

const directiveMocks = vi.hoisted(() => ({
  getValidDirectives: vi.fn(async () => ['@value:available']),
  validateDirective: vi.fn(async () => ({ is_valid: true, path: '@value:available', error: null, suggestions: [] })),
}))

vi.mock('@/composables/useDirectiveValidation', () => ({
  useDirectiveValidation: () => ({
    getValidDirectives: directiveMocks.getValidDirectives,
    validateDirective: directiveMocks.validateDirective,
    isDirective: (value: unknown) => typeof value === 'string' && value.startsWith('@value:'),
  }),
}))

const ForeignKeyTesterStub = {
  name: 'ForeignKeyTester',
  props: ['disabled', 'foreignKey'],
  template:
    '<div data-testid="foreign-key-tester" :data-disabled="String(disabled)" :data-entity="foreignKey.entity" />',
}

const ComboboxStub = {
  name: 'VCombobox',
  props: ['label', 'items', 'modelValue'],
  emits: ['focus', 'update:modelValue'],
  template: '<div class="v-combobox-stub" />',
}

const ControlStub = {
  inheritAttrs: false,
  props: ['modelValue'],
  template: '<div><slot /></div>',
}

describe('ForeignKeyEditor', () => {
  beforeEach(() => {
    directiveMocks.getValidDirectives.mockClear()
    directiveMocks.validateDirective.mockClear()
  })

  it('allows testing an existing entity foreign key draft without saving', async () => {
    const wrapper = shallowMount(ForeignKeyEditor, {
      props: {
        modelValue: [
          {
            entity: 'site',
            local_keys: ['site_id'],
            remote_keys: ['site_id'],
            how: 'inner',
          },
        ],
        projectName: 'demo',
        entityName: 'sample',
        isEntitySaved: true,
        hasUnsavedChanges: true,
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: {
          ForeignKeyTester: ForeignKeyTesterStub,
          VAutocomplete: ControlStub,
          VSelect: ControlStub,
          VCombobox: ControlStub,
        },
      },
    })

    const tester = wrapper.find('[data-testid="foreign-key-tester"]')
    expect(tester.attributes('data-disabled')).toBe('false')
    expect(tester.attributes('data-entity')).toBe('site')
    expect(wrapper.text()).toContain('Tests this foreign key against saved entity data without saving your changes.')

    await wrapper.setProps({ hasUnsavedChanges: false })

    expect(tester.attributes('data-disabled')).toBe('false')
  })

  it('shows the positional key pairs and warns when matching keys are reordered', () => {
    const wrapper = shallowMount(ForeignKeyEditor, {
      props: {
        modelValue: [
          {
            entity: 'site',
            local_keys: ['Fustel', 'EVNr'],
            remote_keys: ['EVNr', 'Fustel'],
            how: 'inner',
          },
        ],
        projectName: 'demo',
        entityName: 'sample',
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: { VAutocomplete: ControlStub, VSelect: ControlStub, VCombobox: ControlStub },
      },
    })

    const rows = wrapper.findAll('[data-testid="fk-key-pair-preview"] tbody tr')
    expect(rows.map((row) => row.findAll('td').map((cell) => cell.text()))).toEqual([
      ['1', 'Fustel', 'EVNr'],
      ['2', 'EVNr', 'Fustel'],
    ])
    expect(wrapper.get('[data-testid="fk-key-order-warning"]').text()).toContain(
      'Local and remote keys contain the same names in a different order.'
    )
    expect(wrapper.find('[data-testid="fk-key-count-warning"]').exists()).toBe(false)
  })

  it('shows a warning and an empty pair slot when key counts differ', () => {
    const wrapper = shallowMount(ForeignKeyEditor, {
      props: {
        modelValue: [
          {
            entity: 'location',
            local_keys: ['location_type', 'location_name'],
            remote_keys: ['location_type'],
            how: 'inner',
          },
        ],
        projectName: 'demo',
        entityName: 'sample',
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: { VAutocomplete: ControlStub, VSelect: ControlStub, VCombobox: ControlStub },
      },
    })

    const rows = wrapper.findAll('[data-testid="fk-key-pair-preview"] tbody tr')
    expect(rows.map((row) => row.findAll('td').map((cell) => cell.text()))).toEqual([
      ['1', 'location_type', 'location_type'],
      ['2', 'location_name', ''],
    ])
    expect(wrapper.get('[data-testid="fk-key-count-warning"]').text()).toContain('Local and remote key counts differ.')
    expect(wrapper.find('[data-testid="fk-key-order-warning"]').exists()).toBe(false)
  })

  it('maps candidates to the matching foreign key and keeps free-text entry', async () => {
    const wrapper = shallowMount(ForeignKeyEditor, {
      props: {
        modelValue: [
          {
            entity: 'site',
            local_keys: ['site_name'],
            remote_keys: ['name'],
            how: 'inner',
            extra_columns: { site_code: 'code' },
          },
          {
            entity: 'taxon',
            local_keys: ['taxon_name'],
            remote_keys: ['name'],
            how: 'inner',
          },
        ],
        columnCandidates: [
          {
            index: 0,
            entity: 'site',
            local_keys_before_unnest: ['site_name', 'shared'],
            local_keys_after_unnest: ['measurement_type', 'shared'],
            remote_keys: ['site_id', 'system_id'],
            extra_column_sources: ['site_code', 'system_id'],
          },
          {
            index: 1,
            entity: 'taxon',
            local_keys_before_unnest: ['taxon_name'],
            local_keys_after_unnest: [],
            remote_keys: ['taxon_id'],
            extra_column_sources: ['taxon_label'],
          },
        ],
        projectName: 'demo',
        entityName: 'sample',
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: {
          ForeignKeyTester: ForeignKeyTesterStub,
          VAutocomplete: ControlStub,
          VSelect: ControlStub,
          VCombobox: ComboboxStub,
        },
      },
    })

    const comboboxes = wrapper.findAllComponents(ComboboxStub)
    const localInputs = comboboxes.filter((input) => input.props('label') === 'Local Keys')
    const remoteInputs = comboboxes.filter((input) => input.props('label') === 'Remote Keys')
    const extraSourceInput = comboboxes.find((input) => input.props('label') === 'Remote Column')

    expect(localInputs.map((input) => input.props('items'))).toEqual([
      ['site_name', 'shared', 'measurement_type'],
      ['taxon_name'],
    ])
    expect(remoteInputs.map((input) => input.props('items'))).toEqual([['site_id', 'system_id'], ['taxon_id']])
    expect(extraSourceInput?.props('items')).toEqual(['site_code', 'system_id'])

    localInputs[0]!.vm.$emit('update:modelValue', ['entered_column_not_in_candidates'])
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toEqual([
      expect.objectContaining({ local_keys: ['entered_column_not_in_candidates'] }),
      expect.objectContaining({ entity: 'taxon' }),
    ])
  })

  it('clears mismatched candidates when the target changes and reflects the updated response', async () => {
    const wrapper = shallowMount(ForeignKeyEditor, {
      props: {
        modelValue: [{ entity: 'site', local_keys: [], remote_keys: [], how: 'inner' }],
        columnCandidates: [
          {
            index: 0,
            entity: 'site',
            local_keys_before_unnest: ['site_name'],
            local_keys_after_unnest: [],
            remote_keys: ['site_id'],
            extra_column_sources: [],
          },
        ],
        projectName: 'demo',
        entityName: 'sample',
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: { VCombobox: ComboboxStub },
      },
    })

    await wrapper.setProps({
      modelValue: [{ entity: 'location', local_keys: [], remote_keys: [], how: 'inner' }],
    })

    const getComboboxItems = (label: string) =>
      wrapper
        .findAllComponents(ComboboxStub)
        .find((input) => input.props('label') === label)
        ?.props('items')

    expect(getComboboxItems('Local Keys')).toEqual([])
    expect(getComboboxItems('Remote Keys')).toEqual([])

    await wrapper.setProps({
      columnCandidates: [
        {
          index: 0,
          entity: 'location',
          local_keys_before_unnest: ['location_name'],
          local_keys_after_unnest: [],
          remote_keys: ['location_id'],
          extra_column_sources: [],
        },
      ],
    })

    expect(getComboboxItems('Local Keys')).toEqual(['location_name'])
    expect(getComboboxItems('Remote Keys')).toEqual(['location_id'])
  })

  it('retains directive suggestions and validation for local and remote keys', async () => {
    const wrapper = shallowMount(ForeignKeyEditor, {
      props: {
        modelValue: [{ entity: 'site', local_keys: [], remote_keys: [], how: 'inner' }],
        entityColumns: ['@value:entity_column'],
        columnCandidates: [
          {
            index: 0,
            entity: 'site',
            local_keys_before_unnest: ['site_name'],
            local_keys_after_unnest: [],
            remote_keys: ['site_id'],
            extra_column_sources: ['site_code'],
          },
        ],
        projectName: 'demo',
        entityName: 'sample',
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: { VCombobox: ComboboxStub },
      },
    })

    const getCombobox = (label: string) =>
      wrapper.findAllComponents(ComboboxStub).find((input) => input.props('label') === label)!
    const localInput = getCombobox('Local Keys')
    const remoteInput = getCombobox('Remote Keys')

    localInput.vm.$emit('focus')
    await flushPromises()

    expect(directiveMocks.getValidDirectives).toHaveBeenCalledWith('demo')
    expect(localInput.props('items')).toEqual(['site_name', '@value:available', '@value:entity_column'])
    expect(remoteInput.props('items')).toEqual(['site_id', '@value:available'])

    localInput.vm.$emit('update:modelValue', ['@value:local'])
    remoteInput.vm.$emit('update:modelValue', ['@value:remote'])
    await flushPromises()

    expect(directiveMocks.validateDirective).toHaveBeenCalledWith('demo', '@value:local', {
      localEntity: 'sample',
      remoteEntity: 'site',
      isLocalKeys: true,
    })
    expect(directiveMocks.validateDirective).toHaveBeenCalledWith('demo', '@value:remote', {
      localEntity: 'sample',
      remoteEntity: 'site',
      isLocalKeys: false,
    })
  })
})
