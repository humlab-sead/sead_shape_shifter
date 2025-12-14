/**
 * Test Run API Client
 * 
 * API client for configuration test run operations.
 */

import { apiRequest } from './client'
import type { TestRunRequest, TestRunResult, TestProgress } from '../types/testRun'

const BASE_URL = '/test-runs';

export const testRunApi = {
  /**
   * Start a new test run
   */
  async startTestRun(request: TestRunRequest): Promise<TestRunResult> {
    return await apiRequest<TestRunResult>({
      method: 'POST',
      url: BASE_URL,
      data: request,
    })
  },

  /**
   * Get test run result by ID
   */
  async getTestRun(runId: string): Promise<TestRunResult> {
    return await apiRequest<TestRunResult>({
      method: 'GET',
      url: `${BASE_URL}/${runId}`,
    })
  },

  /**
   * Get test run progress by ID
   */
  async getTestRunProgress(runId: string): Promise<TestProgress> {
    return await apiRequest<TestProgress>({
      method: 'GET',
      url: `${BASE_URL}/${runId}/progress`,
    })
  },

  /**
   * Cancel a running test or delete a completed test
   */
  async cancelTestRun(runId: string): Promise<void> {
    await apiRequest({
      method: 'DELETE',
      url: `${BASE_URL}/${runId}`,
    })
  },

  /**
   * Delete a test run result
   */
  async deleteTestRun(runId: string): Promise<void> {
    await apiRequest({
      method: 'DELETE',
      url: `${BASE_URL}/${runId}`,
    })
  },

  /**
   * List all test runs
   */
  async listTestRuns(): Promise<TestRunResult[]> {
    return await apiRequest<TestRunResult[]>({
      method: 'GET',
      url: BASE_URL,
    })
  },
}

export default testRunApi
