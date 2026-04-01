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

export function coercePastedValue(columnName: string, value: string): any {
  if (columnName === 'system_id') {
    const parsed = parseInt(value, 10)
    return isNaN(parsed) ? null : parsed
  }

  return value === '' ? null : value
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
}: ApplyClipboardMatrixOptions): any[][] {
  const result = rows.map((row) => [...row])
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

      targetRow[targetColIndex] = coercePastedValue(columnName, sourceRow[columnOffset] ?? '')
    }
  }

  return result
}
