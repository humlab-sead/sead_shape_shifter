import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/api/client'
import { useDataValidation } from '../useDataValidation'

vi.mock('@/api/client', () => ({
  apiClient: { post: vi.fn() },
}))

const post = () => vi.mocked(apiClient.post)

describe('useDataValidation', () => {
  beforeEach(() => {
    post().mockReset()
    post().mockResolvedValue({ data: { is_valid: true, errors: [], warnings: [] } })
  })

  it('sends the selected data checks so unchecking one is honoured', async () => {
    const validation = useDataValidation()

    await validation.validateData('project-a', ['orders'], 'complete', ['column_exists', 'natural_key_uniqueness'])

    expect(post()).toHaveBeenCalledWith('/projects/project-a/validate/data', null, {
      params: {
        validation_mode: 'complete',
        entity_names: 'orders',
        validators: 'column_exists,natural_key_uniqueness',
      },
    })
  })

  it('omits the parameter when the caller does not choose checks', async () => {
    const validation = useDataValidation()

    await validation.validateData('project-a', undefined, 'complete')

    expect(post()).toHaveBeenCalledWith('/projects/project-a/validate/data', null, {
      params: { validation_mode: 'complete' },
    })
  })

  it('sends an empty value when no check is selected', async () => {
    const validation = useDataValidation()

    await validation.validateData('project-a', undefined, 'complete', [])

    expect(post()).toHaveBeenCalledWith('/projects/project-a/validate/data', null, {
      params: { validation_mode: 'complete', validators: '' },
    })
  })
})
