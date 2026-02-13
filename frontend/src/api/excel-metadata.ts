import type { ExcelMetadata } from '@/types'
import { apiRequest } from './client'

export const excelMetadataApi = {
  fetch: async (file: string, sheetName?: string, range?: string): Promise<ExcelMetadata> => {
    return apiRequest<ExcelMetadata>({
      method: 'GET',
      url: '/data-sources/excel/metadata',
      params: {
        file,
        sheet_name: sheetName,
        range: range,
      },
    })
  },
}
