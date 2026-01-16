import * as YAML from 'yaml'
import type monaco from 'monaco-editor'

/**
 * External context for validation when editing isolated YAML (e.g., single entity)
 */
export interface ValidationContext {
  entityNames: string[]
  dataSourceNames: string[]
  currentEntityName?: string // Exclude from self-references in depends_on/foreign_keys
}

/**
 * Internal document index built from parsing
 */
interface DocIndex {
  entityNames: string[]
  dataSourceNames: string[]
  entities: Record<string, any>
}

/**
 * Validate project YAML with optional external context
 * @param text - YAML text to validate
 * @param model - Monaco editor model
 * @param context - Optional external context (for single-entity mode)
 * @returns Array of Monaco markers (errors/warnings)
 */
export function validateProjectYaml(
  text: string,
  model: monaco.editor.ITextModel,
  context?: ValidationContext
): monaco.editor.IMarkerData[] {
  const markers: monaco.editor.IMarkerData[] = []

  try {
    const doc = YAML.parseDocument(text)
    const data = doc.toJSON()

    if (!data || typeof data !== 'object') {
      return markers
    }

    // Use provided context OR build from document
    const index = context ? buildIndexFromContext(context) : buildIndex(data)

    // Validate entity references
    markers.push(...validateEntityReferences(data, index, doc, context?.currentEntityName))

    // Validate task list references (only in full project mode)
    if (!context) {
      markers.push(...validateTaskListReferences(data, index, doc))
    }

    // Validate @value expressions
    markers.push(...validateValueExpressions(data, index, doc))
  } catch (error) {
    // YAML parse errors are handled by monaco-yaml
    console.debug('YAML validation error:', error)
  }

  return markers
}

/**
 * Build index from external context (single-entity mode)
 */
function buildIndexFromContext(context: ValidationContext): DocIndex {
  return {
    entityNames: context.entityNames,
    dataSourceNames: context.dataSourceNames,
    entities: {}
  }
}

/**
 * Build index from parsed document (full project mode)
 */
function buildIndex(data: any): DocIndex {
  return {
    entityNames: Object.keys(data.entities || {}),
    dataSourceNames: Object.keys(data.options?.data_sources || {}),
    entities: data.entities || {}
  }
}

/**
 * Validate entity references in depends_on and foreign_keys
 */
function validateEntityReferences(
  data: any,
  index: DocIndex,
  doc: YAML.Document,
  currentEntityName?: string
): monaco.editor.IMarkerData[] {
  const markers: monaco.editor.IMarkerData[] = []

  // In single-entity mode, data IS the entity
  // In full-project mode, iterate through entities
  const entitiesToCheck = index.entities && Object.keys(index.entities).length > 0 
    ? Object.entries(index.entities)
    : [[currentEntityName || 'entity', data]]

  for (const [entityName, entity] of entitiesToCheck) {
    if (!entity || typeof entity !== 'object') continue

    // Check depends_on references
    if (Array.isArray(entity.depends_on)) {
      for (const dep of entity.depends_on) {
        if (typeof dep === 'string' && !index.entityNames.includes(dep)) {
          markers.push(
            createMarker(
              findNodePosition(doc, ['entities', entityName, 'depends_on']),
              `Unknown entity '${dep}' in depends_on`,
              'Error'
            )
          )
        }
      }
    }

    // Check foreign_keys.entity references
    if (Array.isArray(entity.foreign_keys)) {
      for (const fk of entity.foreign_keys) {
        if (fk?.entity && typeof fk.entity === 'string' && !index.entityNames.includes(fk.entity)) {
          markers.push(
            createMarker(
              findNodePosition(doc, ['entities', entityName, 'foreign_keys']),
              `Unknown entity '${fk.entity}' in foreign_keys`,
              'Error'
            )
          )
        }
      }
    }

    // Check filters.exists_in.entity references
    if (entity.filters?.exists_in?.entity) {
      const filterEntity = entity.filters.exists_in.entity
      if (typeof filterEntity === 'string' && !index.entityNames.includes(filterEntity)) {
        markers.push(
          createMarker(
            findNodePosition(doc, ['entities', entityName, 'filters', 'exists_in']),
            `Unknown entity '${filterEntity}' in filters.exists_in`,
            'Error'
          )
        )
      }
    }

    // Check append entity references
    if (Array.isArray(entity.append)) {
      for (const appendEntity of entity.append) {
        if (typeof appendEntity === 'string' && !index.entityNames.includes(appendEntity)) {
          markers.push(
            createMarker(
              findNodePosition(doc, ['entities', entityName, 'append']),
              `Unknown entity '${appendEntity}' in append`,
              'Error'
            )
          )
        }
      }
    }
  }

  return markers
}

/**
 * Validate task list entity references (full project mode only)
 */
function validateTaskListReferences(
  data: any,
  index: DocIndex,
  doc: YAML.Document
): monaco.editor.IMarkerData[] {
  const markers: monaco.editor.IMarkerData[] = []
  const taskList = data.task_list

  if (!taskList || typeof taskList !== 'object') return markers

  const checkArray = (arrayName: string) => {
    const entities = taskList[arrayName]
    if (!Array.isArray(entities)) return

    for (const entity of entities) {
      if (typeof entity === 'string' && !index.entityNames.includes(entity)) {
        markers.push(
          createMarker(
            findNodePosition(doc, ['task_list', arrayName]),
            `Unknown entity '${entity}' in task_list.${arrayName}`,
            'Warning'
          )
        )
      }
    }
  }

  checkArray('required_entities')
  checkArray('completed')
  checkArray('ignored')

  return markers
}

/**
 * Validate @value expressions for entity references
 */
function validateValueExpressions(
  data: any,
  index: DocIndex,
  doc: YAML.Document
): monaco.editor.IMarkerData[] {
  const markers: monaco.editor.IMarkerData[] = []

  // Simple regex to extract entity references from @value expressions
  const valueExprPattern = /@value:\s*entities\.(\w+)/g
  const text = JSON.stringify(data)

  let match
  while ((match = valueExprPattern.exec(text)) !== null) {
    const entityName = match[1]
    if (!index.entityNames.includes(entityName)) {
      // Note: Position mapping from JSON string is approximate
      // In a production implementation, walk the YAML AST to find exact positions
      markers.push({
        severity: 8 as monaco.MarkerSeverity, // Error
        message: `Unknown entity '${entityName}' in @value expression`,
        startLineNumber: 1,
        startColumn: 1,
        endLineNumber: 1,
        endColumn: 1
      })
    }
  }

  return markers
}

/**
 * Create a Monaco marker from position and message
 */
function createMarker(
  position: { line: number; col: number } | null,
  message: string,
  severity: 'Error' | 'Warning'
): monaco.editor.IMarkerData {
  return {
    severity: severity === 'Error' ? 8 : 4, // Monaco.MarkerSeverity enum values
    message,
    startLineNumber: position?.line || 1,
    startColumn: position?.col || 1,
    endLineNumber: position?.line || 1,
    endColumn: position?.col || 100
  }
}

/**
 * Find the position of a YAML node by path
 * @param doc - Parsed YAML document
 * @param path - Path to the node (e.g., ['entities', 'sample', 'depends_on'])
 * @returns Position object with line and column, or null if not found
 */
function findNodePosition(
  doc: YAML.Document,
  path: string[]
): { line: number; col: number } | null {
  try {
    // Walk the YAML document to find the node
    let node: any = doc.contents

    for (const segment of path) {
      if (!node) break

      if (YAML.isMap(node)) {
        const pair = node.items.find((item: any) => {
          const key = YAML.isScalar(item.key) ? item.key.value : null
          return key === segment
        })
        node = pair?.value
      } else if (YAML.isSeq(node)) {
        const index = parseInt(segment, 10)
        node = !isNaN(index) ? node.items[index] : null
      } else {
        node = null
      }
    }

    if (node?.range) {
      // Convert character offset to line/col
      // This is simplified - real implementation would use doc.lineCounter
      return { line: 1, col: node.range[0] }
    }
  } catch (error) {
    console.debug('Error finding node position:', error)
  }

  return null
}
