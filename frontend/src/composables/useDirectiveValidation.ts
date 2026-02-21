/**
 * Composable for validating @value directives.
 */
import { ref } from 'vue'
import { apiClient } from '@/api/client'

export interface DirectiveValidationResult {
  is_valid: boolean
  path: string
  error: string | null
  suggestions: string[]
}

export function useDirectiveValidation() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Validate a @value directive against project structure.
   */
  async function validateDirective(
    projectName: string,
    directive: string,
    options?: {
      localEntity?: string
      remoteEntity?: string
      isLocalKeys?: boolean
    }
  ): Promise<DirectiveValidationResult | null> {
    if (!directive.startsWith('@value:')) {
      return {
        is_valid: false,
        path: directive,
        error: "Directive must start with '@value:'",
        suggestions: [],
      }
    }

    loading.value = true
    error.value = null

    try {
      const response = await apiClient.post<DirectiveValidationResult>(
        `/projects/${projectName}/validate-directive`,
        {
          directive,
          local_entity: options?.localEntity,
          remote_entity: options?.remoteEntity,
          is_local_keys: options?.isLocalKeys,
        }
      )
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to validate directive'
      console.error('Error validating directive:', e)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get all valid @value directive paths in the project.
   */
  async function getValidDirectives(projectName: string): Promise<string[]> {
    loading.value = true
    error.value = null

    try {
      const response = await apiClient.get<string[]>(`/projects/${projectName}/valid-directives`)
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to fetch valid directives'
      console.error('Error fetching valid directives:', e)
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Check if a value is a @value directive.
   */
  function isDirective(value: string | any): boolean {
    return typeof value === 'string' && value.startsWith('@value:')
  }

  /**
   * Extract directive path from full directive string.
   */
  function extractPath(directive: string): string {
    return directive.startsWith('@value:') ? directive.substring(7) : directive
  }

  return {
    loading,
    error,
    validateDirective,
    getValidDirectives,
    isDirective,
    extractPath,
  }
}
