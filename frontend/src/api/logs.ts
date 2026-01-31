/**
 * API client for application logs
 */

import { apiClient } from './client'

export interface LogResponse {
  lines: string[]
  total: number
}

export interface LogDownloadResponse {
  content: string
  filename: string
}

export type LogType = 'app' | 'error'
export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'

export const logsApi = {
  /**
   * Fetch application logs
   */
  getLogs: async (
    logType: LogType,
    lines: number = 500,
    level?: LogLevel
  ): Promise<LogResponse> => {
    const params = new URLSearchParams({ lines: lines.toString() })
    if (level) {
      params.append('level', level)
    }

    const response = await apiClient.get<LogResponse>(
      `/logs/${logType}?${params.toString()}`
    )
    return response.data
  },

  /**
   * Download log file
   */
  downloadLogs: async (logType: LogType): Promise<LogDownloadResponse> => {
    const response = await apiClient.get<LogDownloadResponse>(
      `/logs/${logType}/download`
    )
    return response.data
  },
}
