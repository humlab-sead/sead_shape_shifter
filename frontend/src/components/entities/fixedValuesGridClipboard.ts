export type GridColumnType = 'number' | 'string'

export interface CoercedGridValue {
  value: any
  error: string | null
}

export interface ApplyClipboardMatrixResult {
  rows: any[][]
  errors: string[]
}

export interface CoerceGridRowsResult {
  rows: any[][]
  errors: string[]
}

export function inferColumnType(columnName: string): GridColumnType {
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

export function coerceGridValue(columnName: string, value: unknown, fallbackValue: any = null): CoercedGridValue {
  if (inferColumnType(columnName) === 'number') {
    const parsed = parseStrictInteger(value)
    const text = value === null || value === undefined ? '' : String(value).trim()

    if (parsed === null && text !== '') {
      return {
        value: fallbackValue,
        error: 'Expected integer ID',
      }
    }

    return {
      value: parsed,
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

export function coerceGridRows(columns: string[], rows: any[][]): CoerceGridRowsResult {
  const errors: string[] = []
  const coercedRows = rows.map((row, rowIndex) => row.map((value, columnIndex) => {
    const columnName = columns[columnIndex]
    if (!columnName) {
      return value
    }

    const result = coerceGridValue(columnName, value, value)
    if (result.error) {
      errors.push(`Row ${rowIndex + 1}, column ${columnName}: ${result.error}`)
    }

    return result.value
  }))

  return { rows: coercedRows, errors }
}

interface ApplyClipboardMatrixOptions {
  rows: any[][]
  columns: string[]
  startRowIndex: number
  startColIndex: number
  matrix: string[][]
  createEmptyRow: () => any[]
}

export function applyClipboardMatrix({
  rows,
  columns,
  startRowIndex,
  startColIndex,
  matrix,
  createEmptyRow,
}: ApplyClipboardMatrixOptions): ApplyClipboardMatrixResult {
  const result = rows.map((row) => [...row])
  const errors: string[] = []
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

      const { value, error } = coerceGridValue(columnName, sourceRow[columnOffset] ?? '', targetRow[targetColIndex])

      if (error) {
        errors.push(`Row ${targetRowIndex + 1}, column ${columnName}: ${error}`)
      }

      targetRow[targetColIndex] = value
    }
  }

  return { rows: result, errors }
}
