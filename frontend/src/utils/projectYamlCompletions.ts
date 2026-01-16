import type monaco from 'monaco-editor'
import * as YAML from 'yaml'
import type { ValidationContext } from './projectYamlValidator'

/**
 * Register YAML completion provider with optional context support
 * @param monacoInstance - Monaco editor instance
 * @param contextProvider - Optional callback to get validation context
 */
export function registerProjectCompletions(
  monacoInstance: typeof monaco,
  contextProvider?: () => ValidationContext | undefined
) {
  monacoInstance.languages.registerCompletionItemProvider('yaml', {
    provideCompletionItems: (model, position) => {
      const textUntilPosition = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column
      })

      const suggestions: monaco.languages.CompletionItem[] = []

      // Get context from external source OR parse document
      let index: { entityNames: string[]; dataSourceNames: string[] }

      if (contextProvider) {
        const context = contextProvider()
        if (context) {
          index = {
            entityNames: context.entityNames,
            dataSourceNames: context.dataSourceNames
          }
        } else {
          index = { entityNames: [], dataSourceNames: [] }
        }
      } else {
        const fullText = model.getValue()
        index = extractEntityNames(fullText)
      }

      // Detect context and provide suggestions
      const line = textUntilPosition.toLowerCase().trim()

      // Suggest entity names in depends_on arrays
      if (line.includes('depends_on:') || line.match(/depends_on:\s*$/)) {
        suggestions.push(...createEntitySuggestions(index.entityNames, monacoInstance))
      }
      // Suggest data source names
      else if (line.match(/data_source:\s*$/)) {
        suggestions.push(...createDataSourceSuggestions(index.dataSourceNames, monacoInstance))
      }
      // Suggest entity names in foreign_keys.entity
      else if (line.match(/entity:\s*$/)) {
        suggestions.push(...createEntitySuggestions(index.entityNames, monacoInstance))
      }
      // Suggest entity names in filters.exists_in.entity
      else if (line.includes('exists_in') && line.match(/entity:\s*$/)) {
        suggestions.push(...createEntitySuggestions(index.entityNames, monacoInstance))
      }
      // Suggest entity names in append arrays
      else if (line.includes('append:') || line.match(/append:\s*$/)) {
        suggestions.push(...createEntitySuggestions(index.entityNames, monacoInstance))
      }
      // Suggest join types
      else if (line.match(/how:\s*$/)) {
        suggestions.push(...createJoinTypeSuggestions(monacoInstance))
      }
      // Suggest cardinality values
      else if (line.match(/cardinality:\s*$/)) {
        suggestions.push(...createCardinalitySuggestions(monacoInstance))
      }
      // Suggest entity types
      else if (line.match(/type:\s*$/) && !line.includes('metadata')) {
        suggestions.push(...createEntityTypeSuggestions(monacoInstance))
      }

      return { suggestions }
    }
  })
}

/**
 * Extract entity and data source names from YAML text
 */
function extractEntityNames(text: string): { entityNames: string[]; dataSourceNames: string[] } {
  try {
    const data = YAML.parse(text)
    return {
      entityNames: Object.keys(data?.entities || {}),
      dataSourceNames: Object.keys(data?.options?.data_sources || {})
    }
  } catch {
    return { entityNames: [], dataSourceNames: [] }
  }
}

/**
 * Create entity name completion suggestions
 */
function createEntitySuggestions(
  entityNames: string[],
  monaco: typeof monaco
): monaco.languages.CompletionItem[] {
  return entityNames.map((name) => ({
    label: name,
    kind: monaco.languages.CompletionItemKind.Reference,
    insertText: name,
    documentation: `Entity: ${name}`,
    sortText: `0_${name}` // Prioritize entity suggestions
  }))
}

/**
 * Create data source name completion suggestions
 */
function createDataSourceSuggestions(
  dsNames: string[],
  monaco: typeof monaco
): monaco.languages.CompletionItem[] {
  return dsNames.map((name) => ({
    label: name,
    kind: monaco.languages.CompletionItemKind.Reference,
    insertText: name,
    documentation: `Data source: ${name}`,
    sortText: `0_${name}` // Prioritize data source suggestions
  }))
}

/**
 * Create join type completion suggestions
 */
function createJoinTypeSuggestions(monaco: typeof monaco): monaco.languages.CompletionItem[] {
  return [
    {
      label: 'left',
      kind: monaco.languages.CompletionItemKind.Enum,
      insertText: 'left',
      documentation: 'Left join: keep all records from local entity',
      sortText: '0_left'
    },
    {
      label: 'inner',
      kind: monaco.languages.CompletionItemKind.Enum,
      insertText: 'inner',
      documentation: 'Inner join: keep only matching records',
      sortText: '0_inner'
    },
    {
      label: 'outer',
      kind: monaco.languages.CompletionItemKind.Enum,
      insertText: 'outer',
      documentation: 'Outer join: keep all records from both entities',
      sortText: '0_outer'
    }
  ]
}

/**
 * Create cardinality completion suggestions
 */
function createCardinalitySuggestions(monaco: typeof monaco): monaco.languages.CompletionItem[] {
  return [
    {
      label: 'many-to-one',
      kind: monaco.languages.CompletionItemKind.Enum,
      insertText: 'many-to-one',
      documentation: 'Many local records map to one remote record',
      sortText: '0_many-to-one'
    },
    {
      label: 'one-to-many',
      kind: monaco.languages.CompletionItemKind.Enum,
      insertText: 'one-to-many',
      documentation: 'One local record maps to many remote records',
      sortText: '0_one-to-many'
    },
    {
      label: 'one-to-one',
      kind: monaco.languages.CompletionItemKind.Enum,
      insertText: 'one-to-one',
      documentation: 'One local record maps to one remote record',
      sortText: '0_one-to-one'
    },
    {
      label: 'many-to-many',
      kind: monaco.languages.CompletionItemKind.Enum,
      insertText: 'many-to-many',
      documentation: 'Many-to-many relationship',
      sortText: '0_many-to-many'
    }
  ]
}

/**
 * Create entity type completion suggestions
 */
function createEntityTypeSuggestions(monaco: typeof monaco): monaco.languages.CompletionItem[] {
  return [
    {
      label: 'sql',
      kind: monaco.languages.CompletionItemKind.Enum,
      insertText: 'sql',
      documentation: 'SQL query entity: load data by executing SQL query',
      sortText: '0_sql'
    },
    {
      label: 'fixed',
      kind: monaco.languages.CompletionItemKind.Enum,
      insertText: 'fixed',
      documentation: 'Fixed values entity: hardcoded data defined in values array',
      sortText: '0_fixed'
    }
  ]
}
