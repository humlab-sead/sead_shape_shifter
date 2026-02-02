import { configureMonacoYaml } from 'monaco-yaml'
import type monaco from 'monaco-editor'
import projectSchema from '@/schemas/projectSchema.json'
import entitySchema from '@/schemas/entitySchema.json'
import type { ValidationContext } from '@/utils/projectYamlValidator'

export interface YamlIntelligenceOptions {
  mode: 'project' | 'entity'
  context?: ValidationContext
}

// Track if YAML has been configured globally
let yamlConfigured = false

/**
 * Setup YAML intelligence features for Monaco editor
 * @param monacoInstance - Monaco editor instance
 * @param options - Configuration options
 */
export function setupYamlIntelligence(
  monacoInstance: typeof monaco,
  options: YamlIntelligenceOptions
) {
  // Only configure monaco-yaml once globally to avoid worker conflicts
  if (yamlConfigured) {
    return
  }

  const schema = options.mode === 'project' ? projectSchema : entitySchema

  try {
    configureMonacoYaml(monacoInstance, {
      enableSchemaRequest: false,
      hover: false, // Disable hover - causes "doHover" errors
      completion: true,
      validate: false, // Disable - we use custom validation
      format: true,
      schemas: [
        {
          uri: `http://shapeshifter/${options.mode}-schema.json`,
          fileMatch: ['*.yml', '*.yaml'],
          schema: schema as any
        }
      ]
    })
    
    yamlConfigured = true
  } catch (error) {
    console.warn('Failed to configure Monaco YAML:', error)
    // Continue without YAML language services - basic editing will still work
  }
}
