import type { EntityResponse } from '@/api/entities'

interface ValueReferencePath {
  entityName: string
  propertyName: 'keys' | 'columns'
}

const VALUE_REFERENCE_PATTERN = /^@value:\s*entities\.([^.]+)\.(keys|columns)$/

function parseValueReference(value: string): ValueReferencePath | null {
  const match = VALUE_REFERENCE_PATTERN.exec(value.trim())
  if (!match) {
    return null
  }

  const propertyName = match[2]
  if (propertyName !== 'keys' && propertyName !== 'columns') {
    return null
  }

  return { entityName: match[1]!, propertyName }
}

function containsDirectiveText(value: string): boolean {
  return value.trim().startsWith('@') || value.includes('@value:')
}

/**
 * Expands a complete supported `@value` reference from completed cached entities.
 * Returns null if any referenced value is unavailable or unsupported.
 */
export function expandValueReference(reference: string, entities: EntityResponse[] | null): string[] | null {
  if (!entities) {
    return null
  }
  const cachedEntities = entities

  function expandReference(value: string, referenceStack: Set<string>): string[] | null {
    const path = parseValueReference(value)
    if (!path) {
      return null
    }

    const pathKey = `${path.entityName}.${path.propertyName}`
    if (referenceStack.has(pathKey)) {
      return null
    }

    const entity = cachedEntities.find((candidate) => candidate.name === path.entityName)
    if (!entity || !Object.prototype.hasOwnProperty.call(entity.entity_data, path.propertyName)) {
      return null
    }

    const nextReferenceStack = new Set(referenceStack)
    nextReferenceStack.add(pathKey)
    const referencedValue = entity.entity_data[path.propertyName]

    if (typeof referencedValue === 'string') {
      return expandReference(referencedValue, nextReferenceStack)
    }

    if (!Array.isArray(referencedValue)) {
      return null
    }

    const columns: string[] = []
    for (const item of referencedValue) {
      if (typeof item !== 'string') {
        return null
      }

      if (containsDirectiveText(item)) {
        const expandedItem = expandReference(item, nextReferenceStack)
        if (!expandedItem) {
          return null
        }
        columns.push(...expandedItem)
      } else {
        columns.push(item)
      }
    }

    return columns
  }

  return expandReference(reference, new Set())
}
