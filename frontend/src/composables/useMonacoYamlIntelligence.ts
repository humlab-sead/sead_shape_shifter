import { configureMonacoYaml } from 'monaco-yaml'
import type monaco from 'monaco-editor'
import projectSchema from '@/schemas/projectSchema.json'
import entitySchema from '@/schemas/entitySchema.json'
import type { ValidationContext } from '@/utils/projectYamlValidator'

export interface YamlIntelligenceOptions {
  mode: 'project' | 'entity'
  context?: ValidationContext
}

/**
 * Setup YAML intelligence features for Monaco editor
 * @param monacoInstance - Monaco editor instance
 * @param options - Configuration options
 */
export function setupYamlIntelligence(
  monacoInstance: typeof monaco,
  options: YamlIntelligenceOptions
) {
  const schema = options.mode === 'project' ? projectSchema : entitySchema

  configureMonacoYaml(monacoInstance, {
    enableSchemaRequest: false,
    hover: true,
    completion: true,
    validate: true,
    format: true,
    schemas: [
      {
        uri: `http://shapeshifter/${options.mode}-schema.json`,
        fileMatch: ['*.yml', '*.yaml'],
        schema: schema as any
      }
    ]
  })
}
