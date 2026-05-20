export type FixedGridColumnTypeName = 'int' | 'string' | 'float' | 'bool' | 'date'
export type GridColumnType = 'number' | 'float' | 'string' | 'preserve'
export interface GridValidationIssue {
  rowIndex: number
  columnName: string
  message: string
}
export interface CoercedGridValue {
  value: any
  error: string | null
}
export interface ApplyClipboardMatrixResult {
  rows: any[][]
  issues: GridValidationIssue[]
  errors: string[]
}
export interface CoerceGridRowsResult {
  rows: any[][]
  issues: GridValidationIssue[]
  errors: string[]
}
const ALL_FIXED_GRID_COLUMN_TYPES: FixedGridColumnTypeName[] = ['int', 'string', 'float', 'bool', 'date']

function isFixedGridColumnTypeName(value: string): value is FixedGridColumnTypeName {
  return ALL_FIXED_GRID_COLUMN_TYPES.includes(value as FixedGridColumnTypeName)
}
export function normalizeGridColumnTypes(columnTypes?: Record<string, unknown> | null): Record<string, FixedGridColumnTypeName> {
  if (!columnTypes) {
    return {}
  }

  return Object.fromEntries(
    Object.entries(columnTypes)
      .map(([columnName, typeName]) => [columnName, String(typeName).trim().toLowerCase()] as const)
      .filter((entry): entry is [string, FixedGridColumnTypeName] => isFixedGridColumnTypeName(entry[1]))
  )
}
function getIntegerValidationMessage(columnName: string, explicitType: FixedGridColumnTypeName | undefined): string {
  if (explicitType === 'int' && !columnName.endsWith('_id')) {
    return 'Expected integer value'
  }

  return 'Expected integer ID'
}
function getFloatValidationMessage(): string {
  return 'Expected float value'
}
export function formatValidationIssue(issue: GridValidationIssue): string {
  return `Row ${issue.rowIndex + 1}, column ${issue.columnName}: ${issue.message}`
}

export function summarizeValidationIssues(issues: GridValidationIssue[]): string[] {
  const issuesByColumn = new Map<string, GridValidationIssue[]>()

  for (const issue of issues) {
    const columnIssues = issuesByColumn.get(issue.columnName) || []
    columnIssues.push(issue)
    issuesByColumn.set(issue.columnName, columnIssues)
  }

  return Array.from(issuesByColumn.entries()).map(([columnName, columnIssues]) => {
    const rowNumbers = Array.from(new Set(columnIssues.map((issue) => issue.rowIndex + 1))).sort((left, right) => left - right)
    const valueLabel = columnIssues.length === 1 ? 'value' : 'values'
    const rowLabel = rowNumbers.length === 1 ? 'row' : 'rows'

    return `Column ${columnName}: ${columnIssues.length} invalid ${valueLabel} (${rowLabel} ${rowNumbers.join(', ')})`
  })
}
export function inferColumnType(columnName: string, columnTypes?: Record<string, unknown> | null): GridColumnType {
  const normalizedColumnTypes = normalizeGridColumnTypes(columnTypes)
  const explicitType = normalizedColumnTypes[columnName]

  if (explicitType === 'int') {
    return 'number'
  }

  if (explicitType === 'float') {
    return 'float'
  }

  if (explicitType === 'string') {
    return 'string'
  }

  if (explicitType) {
    return 'preserve'
  }

  if (columnName.endsWith('_id')) {
    return 'number'
  }

  return 'string'
}
export function parseStrictInteger(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null
  }

  const text = String(value).trim()
  if (text === '') {
    return null
  }

  if (!/^-?\d+$/.test(text)) {
    return null
  }

  return Number(text)
}
export function parseStrictFloat(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null
  }

  const text = String(value).trim()
  if (text === '') {
    return null
  }

  if (!/^-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(text)) {
    return null
  }

  const parsed = Number(text)
  return Number.isFinite(parsed) ? parsed : null
}
export function coerceGridValue(
  columnName: string,
  value: unknown,
  fallbackValue: any = null,
  columnTypes?: Record<string, unknown> | null,
): CoercedGridValue {
  const normalizedColumnTypes = normalizeGridColumnTypes(columnTypes)
  const explicitType = normalizedColumnTypes[columnName]
  const inferredType = inferColumnType(columnName, normalizedColumnTypes)

  if (inferredType === 'number') {
    const parsed = parseStrictInteger(value)
    const text = value === null || value === undefined ? '' : String(value).trim()

    if (parsed === null && text !== '') {
      return {
        value: fallbackValue,
        error: getIntegerValidationMessage(columnName, explicitType),
      }
    }

    return {
      value: parsed,
      error: null,
    }
  }

  if (inferredType === 'float') {
    const parsed = parseStrictFloat(value)
    const text = value === null || value === undefined ? '' : String(value).trim()

    if (parsed === null && text !== '') {
      return {
        value: fallbackValue,
        error: getFloatValidationMessage(),
      }
    }

    return {
      value: parsed,
      error: null,
    }
  }

  if (inferredType === 'preserve') {
    if (value === null || value === undefined || value === '') {
      return {
        value: null,
        error: null,
      }
    }

    return {
      value,
      error: null,
    }
  }

  if (value === null || value === undefined || value === '') {
    return {
      value: null,
      error: null,
    }
  }

  return {
    value: String(value),
    error: null,
  }
}
export function parseClipboardTable(text: string): string[][] {
  const rows = text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n')
    .map((line) => line.split('\t'))

  while (rows.length > 0 && rows[rows.length - 1]!.every((cell) => cell === '')) {
    rows.pop()
  }

  return rows
}
export function buildGridRowData(rows: any[][], systemIdColumnIndex: number): Array<Record<string, any>> {
  return rows.map((row, rowIndex) => {
    const stableSystemId = systemIdColumnIndex >= 0 ? row[systemIdColumnIndex] : undefined
    const rowObj: Record<string, any> = {
      id: stableSystemId !== null && stableSystemId !== undefined ? stableSystemId : `row-${rowIndex}`,
    }

    row.forEach((value, colIndex) => {
      rowObj[`col_${colIndex}`] = value
    })

    return rowObj
  })
}
export function coerceGridRows(
  columns: string[],
  rows: any[][],
  columnTypes?: Record<string, unknown> | null,
): CoerceGridRowsResult {
  const issues: GridValidationIssue[] = []
  const coercedRows = rows.map((row, rowIndex) => row.map((value, columnIndex) => {
    const columnName = columns[columnIndex]
    if (!columnName) {
      return value
    }

    const result = coerceGridValue(columnName, value, value, columnTypes)
    if (result.error) {
      issues.push({ rowIndex, columnName, message: result.error })
    }

    return result.value
  }))

  return { rows: coercedRows, issues, errors: issues.map(formatValidationIssue) }
}
interface ApplyClipboardMatrixOptions {
  rows: any[][]
  columns: string[]
  columnTypes?: Record<string, unknown> | null
  startRowIndex: number
  startColIndex: number
  matrix: string[][]
  createEmptyRow: () => any[]
}
export function applyClipboardMatrix({
  rows,
  columns,
  columnTypes,
  startRowIndex,
  startColIndex,
  matrix,
  createEmptyRow,
}: ApplyClipboardMatrixOptions): ApplyClipboardMatrixResult {
  const result = rows.map((row) => [...row])
  const issues: GridValidationIssue[] = []
  const requiredRowCount = startRowIndex + matrix.length

  while (result.length < requiredRowCount) {
    result.push(createEmptyRow())
  }

  for (let rowOffset = 0; rowOffset < matrix.length; rowOffset += 1) {
    const targetRowIndex = startRowIndex + rowOffset
    const sourceRow = matrix[rowOffset]
    const targetRow = result[targetRowIndex]

    if (!sourceRow || !targetRow) {
      continue
    }

    for (let columnOffset = 0; columnOffset < sourceRow.length; columnOffset += 1) {
      const targetColIndex = startColIndex + columnOffset
      if (targetColIndex >= columns.length) {
        break
      }

      const columnName = columns[targetColIndex]
      if (!columnName) {
        continue
      }

      if (columnName === 'system_id') {
        continue
      }

      const { value, error } = coerceGridValue(columnName, sourceRow[columnOffset] ?? '', targetRow[targetColIndex], columnTypes)

      if (error) {
        issues.push({ rowIndex: targetRowIndex, columnName, message: error })
      }

      targetRow[targetColIndex] = value
    }
  }

  return { rows: result, issues, errors: issues.map(formatValidationIssue) }
}
