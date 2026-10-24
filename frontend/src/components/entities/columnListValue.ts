export function normalizeColumnListChips(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'string') return item.trim()
        if (typeof item === 'object' && item !== null && 'value' in item) {
          const chipValue = (item as { value?: unknown }).value
          return typeof chipValue === 'string' ? chipValue.trim() : String(chipValue ?? '').trim()
        }
        return String(item ?? '').trim()
      })
      .filter((item) => item.length > 0)
  }

  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length > 0 ? [trimmed] : []
  }

  return []
}

export function cloneColumnListValue(value: unknown): unknown {
  return Array.isArray(value) ? [...value] : value
}

export function serializeColumnListValue(
  chips: string[],
  originalValue: unknown,
  originalChips = normalizeColumnListChips(originalValue)
): string | string[] {
  const currentChips = normalizeColumnListChips(chips)
  const hasOriginalColumnList = typeof originalValue === 'string' || Array.isArray(originalValue)

  if (hasOriginalColumnList && areEqual(currentChips, originalChips)) {
    return cloneColumnListValue(originalValue) as string | string[]
  }

  if (currentChips.length === 1) {
    const onlyChip = currentChips[0]!
    const trimmedChip = onlyChip.trim()
    if (trimmedChip.startsWith('@value:') && !trimmedChip.includes('+')) {
      return trimmedChip
    }
  }

  return chips
}

function areEqual(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index])
}
