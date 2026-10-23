import { beforeEach, describe, expect, it, vi } from 'vitest'

import type monaco from 'monaco-editor'

const { configureMonacoYamlMock } = vi.hoisted(() => ({
  configureMonacoYamlMock: vi.fn(),
}))
vi.mock('monaco-yaml', () => ({
  configureMonacoYaml: configureMonacoYamlMock,
}))

describe('setupYamlIntelligence', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.resetModules()
  })

  it('registers separate schemas for each YAML editor mode only once', async () => {
    const { setupYamlIntelligence } = await import('../useMonacoYamlIntelligence')
    const monacoInstance = {} as typeof monaco

    setupYamlIntelligence(monacoInstance, { mode: 'reconciliation' })
    setupYamlIntelligence(monacoInstance, { mode: 'project' })

    expect(configureMonacoYamlMock).toHaveBeenCalledTimes(1)
    const options = configureMonacoYamlMock.mock.calls[0]?.[1]
    expect(options?.schemas).toHaveLength(4)
    expect(options?.schemas).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          fileMatch: ['inmemory://shapeshifter/reconciliation-*.yml', 'inmemory://shapeshifter/reconciliation-*.yaml'],
        }),
      ])
    )

    const entitySchema = options?.schemas.find((schema) => schema.uri.endsWith('/entity-schema.json'))?.schema as any
    expect(entitySchema.properties.foreign_key_value_sources.default).toEqual({})
    expect(entitySchema.properties.foreign_key_value_sources.additionalProperties.enum).toEqual([
      'system_id',
      'public_id',
    ])
    expect(entitySchema.properties.foreign_key_value_sources.description).toContain('existing target ID')
    expect(entitySchema.properties.foreign_key_value_sources.description).toContain('without creating a Core link')
    expect(entitySchema.properties.foreign_key_value_sources.description).toContain('Omitted entries use system_id')
  })
})
