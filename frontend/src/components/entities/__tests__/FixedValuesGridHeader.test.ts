import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import FixedValuesGridHeader from '../FixedValuesGridHeader.vue'

describe('FixedValuesGridHeader', () => {
  it('updates the column type when the selector changes', async () => {
    const onTypeChange = vi.fn()
    const wrapper = mount(FixedValuesGridHeader, {
      props: {
        params: {
          columnName: 'rank',
          enableSorting: true,
          progressSort: vi.fn(),
          getSelectorValue: () => 'auto',
          getSourceLabel: () => 'Inferred: string',
          getOptions: () => [
            { value: 'auto', label: 'Auto (string)' },
            { value: 'int', label: 'Integer' },
          ],
          onTypeChange,
        },
      },
    })

    await wrapper.get('select').setValue('int')

    expect(onTypeChange).toHaveBeenCalledWith('rank', 'int')
  })

  it('shows an explicit inferred label for the default selector state', () => {
    const wrapper = mount(FixedValuesGridHeader, {
      props: {
        params: {
          columnName: 'method_id',
          enableSorting: true,
          progressSort: vi.fn(),
          getSelectorValue: () => 'auto',
          getSourceLabel: () => 'Inferred: int',
          getOptions: () => [
            { value: 'auto', label: 'Auto (int)' },
            { value: 'int', label: 'Integer' },
          ],
          onTypeChange: vi.fn(),
        },
      },
    })

    expect(wrapper.html()).toContain('Auto (int)')
    expect(wrapper.get('select').attributes('title')).toBe('Inferred: int')
  })

  it('uses the name button to preserve sortable header behavior', async () => {
    const progressSort = vi.fn()
    const wrapper = mount(FixedValuesGridHeader, {
      props: {
        params: {
          columnName: 'method_id',
          enableSorting: true,
          progressSort,
          getSelectorValue: () => 'auto',
          getSourceLabel: () => 'Inferred: int',
          getOptions: () => [
            { value: 'auto', label: 'Auto (int)' },
            { value: 'int', label: 'Integer' },
          ],
          onTypeChange: vi.fn(),
        },
      },
    })

    await wrapper.get('button').trigger('click')

    expect(progressSort).toHaveBeenCalledWith(false)
  })
})