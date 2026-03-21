import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { shallowMount } from '@vue/test-utils'
import type { EntityResponse } from '@/api/entities'
import EntityListCard from '../EntityListCard.vue'

const entities = ref<EntityResponse[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const remove = vi.fn()

vi.mock('@/composables', () => ({
  useEntities: () => ({
    entities,
    loading,
    error,
    remove,
  }),
}))

const EntityFormDialogStub = {
  name: 'EntityFormDialog',
  props: ['modelValue', 'entity'],
  template: `<div class="entity-form-dialog-stub" :data-open="String(modelValue)" :data-entity="entity?.name || ''" />`,
}

const DeleteConfirmationDialogStub = {
  name: 'DeleteConfirmationDialog',
  template: '<div class="delete-confirmation-dialog-stub" />',
}

function createEntity(name: string): EntityResponse {
  return {
    name,
    entity_data: { type: 'entity' },
  } as EntityResponse
}

describe('EntityListCard', () => {
  beforeEach(() => {
    entities.value = []
    loading.value = false
    error.value = null
    remove.mockReset()
  })

  it('opens the requested entity immediately when it is already loaded', async () => {
    entities.value = [createEntity('sample_type')]

    const wrapper = shallowMount(EntityListCard, {
      props: {
        projectName: 'demo',
        entityToEdit: 'sample_type',
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: {
          EntityFormDialog: EntityFormDialogStub,
          DeleteConfirmationDialog: DeleteConfirmationDialogStub,
        },
      },
    })

    await nextTick()

    const dialog = wrapper.get('.entity-form-dialog-stub')
    expect(dialog.attributes('data-open')).toBe('true')
    expect(dialog.attributes('data-entity')).toBe('sample_type')
    expect(wrapper.emitted('entity-edit-request-consumed')).toEqual([['sample_type']])
  })

  it('retries the edit request after entities finish loading', async () => {
    const wrapper = shallowMount(EntityListCard, {
      props: {
        projectName: 'demo',
        entityToEdit: 'sample_type',
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: {
          EntityFormDialog: EntityFormDialogStub,
          DeleteConfirmationDialog: DeleteConfirmationDialogStub,
        },
      },
    })

    await nextTick()
    expect(wrapper.emitted('entity-edit-request-consumed')).toBeUndefined()

    entities.value = [createEntity('sample_type')]
    await nextTick()
    await nextTick()

    const dialog = wrapper.get('.entity-form-dialog-stub')
    expect(dialog.attributes('data-open')).toBe('true')
    expect(dialog.attributes('data-entity')).toBe('sample_type')
    expect(wrapper.emitted('entity-edit-request-consumed')).toEqual([['sample_type']])
  })

  it('can consume the same entity edit request more than once after the parent clears it', async () => {
    entities.value = [createEntity('sample_type')]

    const wrapper = shallowMount(EntityListCard, {
      props: {
        projectName: 'demo',
        entityToEdit: 'sample_type',
      },
      global: {
        renderStubDefaultSlot: true,
        stubs: {
          EntityFormDialog: EntityFormDialogStub,
          DeleteConfirmationDialog: DeleteConfirmationDialogStub,
        },
      },
    })

    await nextTick()
    await wrapper.setProps({ entityToEdit: null })
    await wrapper.setProps({ entityToEdit: 'sample_type' })
    await nextTick()

    expect(wrapper.emitted('entity-edit-request-consumed')).toEqual([
      ['sample_type'],
      ['sample_type'],
    ])
  })
})