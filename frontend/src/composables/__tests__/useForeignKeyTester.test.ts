import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useForeignKeyTester } from '../useForeignKeyTester'

const apiMocks = vi.hoisted(() => ({
  post: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  apiClient: {
    post: apiMocks.post,
  },
}))

describe('useForeignKeyTester', () => {
  beforeEach(() => {
    apiMocks.post.mockReset()
  })

  it('sends the current foreign key definition with the test request', async () => {
    const foreignKey = {
      entity: 'site',
      local_keys: ['site_id'],
      remote_keys: ['id'],
      how: 'left' as const,
      constraints: { cardinality: 'many_to_one' as const },
    }
    const result = {
      entity_name: 'sample',
      remote_entity: 'site',
      local_keys: ['site_id'],
      remote_keys: ['id'],
      join_type: 'left',
      statistics: {
        total_rows: 1,
        matched_rows: 1,
        unmatched_rows: 0,
        match_percentage: 100,
        null_key_rows: 0,
        duplicate_matches: 0,
      },
      cardinality: {
        expected: 'many_to_one',
        actual: 'one_to_one',
        matches: false,
        explanation: 'Join produced 1 rows from 1 input rows',
      },
      unmatched_sample: [],
      execution_time_ms: 1,
      success: false,
      warnings: [],
      recommendations: [],
    }
    apiMocks.post.mockResolvedValue({ data: result })
    const { testForeignKey } = useForeignKeyTester()

    await testForeignKey('demo project', 'sample', 1, foreignKey, 50)

    expect(apiMocks.post).toHaveBeenCalledWith(
      '/projects/demo%20project/entities/sample/foreign-keys/1/test',
      foreignKey,
      { params: { sample_size: 50 } }
    )
  })
})
