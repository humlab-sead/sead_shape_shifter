export interface ExtraColumnEditorRow {
  column: string
  source: string | null
}

export interface ExtraColumnAnalysis {
  kind: 'empty' | 'copy' | 'constant' | 'interpolation' | 'formula' | 'escaped-literal'
  references: string[]
}

export interface ExtraColumnDiagnostic {
  severity: 'error' | 'warning' | 'info'
  message: string
}

export interface ExtraColumnSuggestion {
  label: string
  value: string
  category: 'placeholder' | 'column' | 'function'
}

const INTERPOLATION_PATTERN = /(?<!\{)\{([a-zA-Z_][\w]*)\}(?!\})/g
const FORMULA_REFERENCE_PATTERN = /\b([a-zA-Z_][\w]*)\b/g
const DSL_FUNCTIONS = new Set(['concat', 'upper', 'lower', 'trim', 'substr', 'coalesce', 'null', 'true', 'false'])
const FORMULA_SNIPPETS = ['concat()', 'upper()', 'lower()', 'trim()', 'substr()', 'coalesce()'] as const

export function extractInterpolationReferences(expression: string): string[] {
  const matches = Array.from(expression.matchAll(INTERPOLATION_PATTERN))
    .map((match) => match[1])
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
  return Array.from(new Set(matches))
}

export function extractFormulaReferences(expression: string): string[] {
  const formulaBody = expression.startsWith('=') ? expression.slice(1) : expression
  const matches = Array.from(formulaBody.matchAll(FORMULA_REFERENCE_PATTERN))
    .map((match) => match[1])
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
    .filter((token) => !DSL_FUNCTIONS.has(token.toLowerCase()))

  return Array.from(new Set(matches))
}

export function analyzeExtraColumnExpression(
  expression: string | null | undefined,
  availableColumns: string[] = []
): ExtraColumnAnalysis {
  const normalized = expression?.trim() ?? ''
  const available = new Set(availableColumns.map((column) => column.trim()).filter(Boolean))

  if (!normalized) {
    return { kind: 'empty', references: [] }
  }

  if (normalized.startsWith('==')) {
    return { kind: 'escaped-literal', references: [] }
  }

  if (normalized.startsWith('=')) {
    return { kind: 'formula', references: extractFormulaReferences(normalized) }
  }

  const interpolationReferences = extractInterpolationReferences(normalized)
  if (interpolationReferences.length > 0) {
    return { kind: 'interpolation', references: interpolationReferences }
  }

  if (available.has(normalized)) {
    return { kind: 'copy', references: [normalized] }
  }

  return { kind: 'constant', references: [] }
}

export function getExtraColumnDiagnostics(
  rows: ExtraColumnEditorRow[],
  index: number,
  options: {
    reservedNames?: string[]
    availableColumns?: string[]
  } = {}
): ExtraColumnDiagnostic[] {
  const row = rows[index]
  if (!row) return []

  const reservedNames = new Set((options.reservedNames ?? []).map((name) => name.trim()).filter(Boolean))
  const availableColumns = new Set((options.availableColumns ?? []).map((name) => name.trim()).filter(Boolean))
  const diagnostics: ExtraColumnDiagnostic[] = []
  const columnName = row.column.trim()
  const expression = row.source?.trim() ?? ''

  if (!columnName) {
    diagnostics.push({ severity: 'warning', message: 'Enter a derived column name.' })
    return diagnostics
  }

  const duplicateCount = rows.filter((candidate) => candidate.column.trim() === columnName).length
  if (duplicateCount > 1) {
    diagnostics.push({ severity: 'error', message: `Duplicate derived column name '${columnName}'.` })
  }

  if (reservedNames.has(columnName)) {
    diagnostics.push({ severity: 'error', message: `'${columnName}' conflicts with an existing or reserved result column.` })
  }

  const analysis = analyzeExtraColumnExpression(expression, [...availableColumns])

  if (analysis.kind === 'empty') {
    diagnostics.push({ severity: 'info', message: 'Empty expression stores null.' })
    return diagnostics
  }

  if (analysis.kind === 'copy') {
    diagnostics.push({ severity: 'info', message: `Copies existing column '${analysis.references[0]}'.` })
    return diagnostics
  }

  if (analysis.kind === 'escaped-literal') {
    diagnostics.push({ severity: 'info', message: 'Stores a literal value that begins with =.' })
    return diagnostics
  }

  if (analysis.kind === 'constant') {
    diagnostics.push({ severity: 'info', message: 'Stores a constant literal value.' })
    return diagnostics
  }

  if (analysis.references.length > 0) {
    diagnostics.push({
      severity: 'info',
      message:
        analysis.kind === 'formula'
          ? `Formula references: ${analysis.references.join(', ')}`
          : `Interpolates: ${analysis.references.join(', ')}`,
    })

    const unresolved = analysis.references.filter((reference) => !availableColumns.has(reference))
    if (unresolved.length > 0) {
      diagnostics.push({
        severity: 'warning',
        message: `Not currently visible in the editor: ${unresolved.join(', ')}. These may still resolve later via FK or unnest output.`,
      })
    }
  } else if (analysis.kind === 'formula') {
    diagnostics.push({ severity: 'info', message: 'Formula expression.' })
  }

  return diagnostics
}

export function getExtraColumnSuggestions(
  expression: string | null | undefined,
  availableColumns: string[] = []
): ExtraColumnSuggestion[] {
  const normalized = expression?.trim() ?? ''
  const analysis = analyzeExtraColumnExpression(normalized, availableColumns)
  const uniqueColumns = Array.from(new Set(availableColumns.map((column) => column.trim()).filter(Boolean)))

  if (analysis.kind === 'formula') {
    return [
      ...FORMULA_SNIPPETS.map((snippet) => ({
        label: snippet,
        value: snippet,
        category: 'function' as const,
      })),
      ...uniqueColumns.map((column) => ({
        label: column,
        value: column,
        category: 'column' as const,
      })),
    ]
  }

  return uniqueColumns.map((column) => ({
    label: `{${column}}`,
    value: `{${column}}`,
    category: 'placeholder' as const,
  }))
}

export function applySuggestionToExpression(
  expression: string | null | undefined,
  suggestion: ExtraColumnSuggestion,
  availableColumns: string[] = []
): string {
  const normalized = expression?.trim() ?? ''
  const analysis = analyzeExtraColumnExpression(normalized, availableColumns)

  if (!normalized) {
    if (suggestion.category === 'function') {
      return `=${suggestion.value}`
    }
    return suggestion.value
  }

  if (analysis.kind === 'formula') {
    if (suggestion.category === 'function') {
      return `${normalized}${normalized.endsWith('(') ? '' : ' '}${suggestion.value}`
    }
    return `${normalized}${/[\s,(]$/.test(normalized) ? '' : ', '}${suggestion.value}`
  }

  const separator = normalized.endsWith(' ') || normalized.endsWith('/') || normalized.endsWith('-') ? '' : ' '
  return `${normalized}${separator}${suggestion.value}`
}
