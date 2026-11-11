/**
 * Small helpers for offering read-only result sets as a CSV download.
 *
 * The tables these helpers export are already complete in the browser, so the
 * CSV is built client-side rather than fetched from the backend.
 */

/** Quote one cell when it contains a delimiter, a quote, or a line break. */
export function formatCsvCell(value: unknown): string {
  if (value === null || value === undefined) {
    return ''
  }

  const text = typeof value === 'object' ? (JSON.stringify(value) ?? String(value)) : String(value)
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

/**
 * Build CSV text from one header row and zero or more value rows.
 *
 * Rows may be shorter than the header; missing cells become empty, so a partly
 * populated composite key still lines up under its columns.
 */
export function toCsv(headers: readonly string[], rows: readonly (readonly unknown[])[]): string {
  const lines: string[] = [headers.map(formatCsvCell).join(',')]
  for (const row of rows) {
    const cells: string[] = headers.map((_, index) => formatCsvCell(row[index]))
    lines.push(cells.join(','))
  }
  return lines.join('\r\n')
}

/** Save CSV text as a download under the given file name. */
export function downloadCsv(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = filename
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
