import { configureMonacoYaml } from 'monaco-yaml'
import type monaco from 'monaco-editor'
import projectSchema from '@/schemas/projectSchema.json'
import entitySchema from '@/schemas/entitySchema.json'
import targetModelSchema from '@/schemas/targetModelSchema.json'
import reconciliationSchema from '@/schemas/reconciliationSchema.json'
import type { ValidationContext } from '@/utils/projectYamlValidator'

export interface YamlIntelligenceOptions {
  mode: 'project' | 'entity' | 'target-model' | 'reconciliation'
  context?: ValidationContext
}

let yamlConfigured = false

const yamlSchemas = [
  { mode: 'project', schema: projectSchema },
  { mode: 'entity', schema: entitySchema },
  { mode: 'target-model', schema: targetModelSchema },
  { mode: 'reconciliation', schema: reconciliationSchema },
] as const

/**
 * Setup YAML intelligence features for Monaco editor
 * @param monacoInstance - Monaco editor instance
 * @param options - Configuration options
 */
export function setupYamlIntelligence(monacoInstance: typeof monaco, _options: YamlIntelligenceOptions) {
  if (yamlConfigured) {
    return
  }

  try {
    configureMonacoYaml(monacoInstance, {
      enableSchemaRequest: false,
      hover: false, // Disable hover - causes "doHover" errors
      completion: true,
      validate: false, // Disable - we use custom validation
      format: true,
      schemas: yamlSchemas.map(({ mode, schema }) => ({
        uri: `http://shapeshifter/${mode}-schema.json`,
        fileMatch: [`inmemory://shapeshifter/${mode}-*.yml`, `inmemory://shapeshifter/${mode}-*.yaml`],
        schema: schema as any,
      })),
    })

    yamlConfigured = true
  } catch (error) {
    console.warn('Failed to configure Monaco YAML:', error)
    // Continue without YAML language services - basic editing will still work
  }
}
