export type ForeignKeyKeyInput = string | { value?: string | null } | null | undefined

/**
 * Normalize combobox key selections to unique non-empty strings while preserving order.
 */
export function normalizeForeignKeyKeys(keys: ForeignKeyKeyInput[] | string | null | undefined): string[] {
  if (!Array.isArray(keys)) {
    if (typeof keys === 'string') {
      const trimmed = keys.trim()
      return trimmed.length > 0 ? [trimmed] : []
    }
    return []
  }

  const normalized = keys
    .map((key) => {
      if (typeof key === 'string') return key
      if (typeof key === 'object' && key !== null && 'value' in key && typeof key.value === 'string') return key.value
      return ''
    })
    .map((key) => key.trim())
    .filter((key) => key.length > 0)

  return [...new Set(normalized)]
}