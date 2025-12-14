/**
 * Base API client configuration
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_V1_PREFIX = '/api/v1'

/**
 * Create configured axios instance
 */
export const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: `${API_BASE_URL}${API_V1_PREFIX}`,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  // Request interceptor for logging
  client.interceptors.request.use(
    (config) => {
      console.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
      return config
    },
    (error) => {
      console.error('API Request Error:', error)
      return Promise.reject(error)
    }
  )

  // Response interceptor for error handling
  client.interceptors.response.use(
    (response) => {
      console.debug(`API Response: ${response.status} ${response.config.url}`)
      return response
    },
    (error) => {
      if (error.response) {
        // Server responded with error status
        console.error('API Error Response:', {
          status: error.response.status,
          data: error.response.data,
          url: error.config?.url,
        })
      } else if (error.request) {
        // Request made but no response
        console.error('API No Response:', error.request)
      } else {
        // Error setting up request
        console.error('API Request Setup Error:', error.message)
      }
      return Promise.reject(error)
    }
  )

  return client
}

// Singleton instance
export const apiClient = createApiClient()

/**
 * Generic API request wrapper with type safety
 */
export const apiRequest = async <T>(
  config: AxiosRequestConfig
): Promise<T> => {
  const response: AxiosResponse<T> = await apiClient.request(config)
  return response.data
}
