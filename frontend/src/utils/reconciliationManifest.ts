import type {
  ReconciliationCompatibility,
  ReconciliationManifest,
  ReconciliationManifestResult,
} from '@/types/reconciliation'

interface ManifestType {
  id: string
  name?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonblankString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function errorResult(error: string): ReconciliationManifestResult {
  return { status: 'error', error }
}

export function parseReconciliationManifest(value: unknown): ReconciliationManifestResult {
  if (!isRecord(value) || !Array.isArray(value.defaultTypes)) {
    return errorResult('The reconciliation manifest is missing a valid defaultTypes list.')
  }

  const defaultTypes: ManifestType[] = []
  const defaultTypeIds = new Set<string>()
  for (const entry of value.defaultTypes) {
    if (
      !isRecord(entry) ||
      !isNonblankString(entry.id) ||
      (entry.name !== undefined && typeof entry.name !== 'string') ||
      defaultTypeIds.has(entry.id)
    ) {
      return errorResult('The reconciliation manifest contains an invalid or duplicate default type.')
    }

    defaultTypeIds.add(entry.id)
    defaultTypes.push({ id: entry.id, ...(typeof entry.name === 'string' ? { name: entry.name } : {}) })
  }

  const reconciliation = value.reconciliation
  if (!isRecord(reconciliation) || !Array.isArray(reconciliation.supportedTypes)) {
    return errorResult('The reconciliation manifest is missing a valid reconciliation.supportedTypes list.')
  }

  const supportedTypeIds = new Set<string>()
  const supportedTypes = []
  for (const id of reconciliation.supportedTypes) {
    if (!isNonblankString(id) || supportedTypeIds.has(id)) {
      return errorResult('The reconciliation manifest contains an invalid or duplicate supported type.')
    }

    const matchingType = defaultTypes.find((type) => type.id === id)
    if (!matchingType) {
      return errorResult(`Supported type '${id}' does not resolve to exactly one default type.`)
    }

    supportedTypeIds.add(id)
    supportedTypes.push({ id, name: matchingType.name?.trim() || id })
  }

  const extend = value.extend
  if (!isRecord(extend) || !Array.isArray(extend.property_settings)) {
    return errorResult('The reconciliation manifest is missing a valid extend.property_settings list.')
  }

  const propertiesByType: Record<string, string[]> = Object.fromEntries([...supportedTypeIds].map((id) => [id, []]))
  for (const entry of extend.property_settings) {
    if (
      !isRecord(entry) ||
      !isNonblankString(entry.name) ||
      !Array.isArray(entry.entity_types) ||
      !entry.entity_types.every(isNonblankString)
    ) {
      return errorResult('The reconciliation manifest contains an invalid property setting.')
    }

    for (const id of entry.entity_types) {
      if (!supportedTypeIds.has(id)) continue

      const typeProperties = propertiesByType[id]
      if (!typeProperties) {
        return errorResult(`Supported type '${id}' has no property index.`)
      }

      if (!typeProperties.includes(entry.name)) typeProperties.push(entry.name)
    }
  }

  const manifest: ReconciliationManifest = { supportedTypes, propertiesByType }
  return { status: 'valid', manifest }
}

export function getReconciliationCompatibility(
  result: ReconciliationManifestResult | null | undefined,
  serviceType: string | null | undefined,
  propertyMappings: Record<string, string>
): ReconciliationCompatibility {
  if (!serviceType) {
    return { status: 'disabled', canMatch: false, message: 'No remote service type is configured.' }
  }

  if (!result || result.status === 'error') {
    return {
      status: 'unknown',
      canMatch: false,
      message: result?.status === 'error' ? result.error : 'Reconciliation service metadata has not been checked.',
    }
  }

  const type = result.manifest.supportedTypes.find((supportedType) => supportedType.id === serviceType)
  if (!type) {
    return {
      status: 'unsupported',
      canMatch: false,
      message: `Remote type '${serviceType}' is not supported for reconciliation.`,
    }
  }

  const servedProperties = result.manifest.propertiesByType[serviceType]
  if (!Array.isArray(servedProperties)) {
    return {
      status: 'unknown',
      canMatch: false,
      message: `Properties for remote type '${serviceType}' cannot be verified.`,
    }
  }

  const unsupportedProperties = Object.keys(propertyMappings).filter((property) => !servedProperties.includes(property))
  if (unsupportedProperties.length > 0) {
    return {
      status: 'unsupported',
      canMatch: false,
      message:
        `Property mapping${unsupportedProperties.length === 1 ? '' : 's'} ` +
        `${unsupportedProperties.map((property) => `'${property}'`).join(', ')} ` +
        `not declared for remote type '${serviceType}'.`,
    }
  }

  return { status: 'supported', canMatch: true, message: null }
}
