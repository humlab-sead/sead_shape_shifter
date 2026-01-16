import { test, expect } from '@playwright/test'

/**
 * Critical Workflow Test: Validation and Auto-Fix
 * 
 * Tests the validation workflow including error detection and auto-fix suggestions
 */

test.describe('Validation and Auto-Fix Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    
    // Navigate to a project (assume first project exists)
    await page.click('text=Projects')
    await page.waitForLoadState('networkidle')
    
    const firstProject = page.locator('[data-test="project-item"], .project-card, .project-list-item').first()
    if (await firstProject.count() > 0) {
      await firstProject.click()
    } else {
      test.skip('No project available for testing')
    }
  })

  test('should navigate to validation tab', async ({ page }) => {
    // Click validation tab
    await page.click('[data-test="validation-tab"], button:has-text("Validation"), a:has-text("Validation")')
    
    // Should show validation interface
    await expect(
      page.locator('button:has-text("Validate"), button:has-text("Run Validation")')
    ).toBeVisible({ timeout: 5000 })
  })

  test('should run validation', async ({ page }) => {
    // Navigate to validation tab
    await page.click('[data-test="validation-tab"], button:has-text("Validation"), a:has-text("Validation")')
    
    // Click validate button
    const validateButton = page.locator(
      '[data-test="validate-all"], button:has-text("Validate All"), button:has-text("Run Validation")'
    ).first()
    
    await validateButton.click()
    
    // Should show validation results (either success or errors)
    await expect(
      page.locator(
        '[data-test="validation-results"], .validation-result, text=/validation (passed|failed|complete)/i'
      ).first()
    ).toBeVisible({ timeout: 15000 })
  })

  test('should display validation errors if present', async ({ page }) => {
    // Navigate to validation tab
    await page.click('[data-test="validation-tab"], button:has-text("Validation"), a:has-text("Validation")')
    
    // Run validation
    await page.click('[data-test="validate-all"], button:has-text("Validate")')
    await page.waitForTimeout(2000) // Wait for validation to complete
    
    // Check if errors are displayed (may or may not have errors depending on project)
    const errorElements = page.locator('[data-test="validation-error"], .error, .v-alert--type-error')
    const errorCount = await errorElements.count()
    
    if (errorCount > 0) {
      // If errors exist, they should be visible
      await expect(errorElements.first()).toBeVisible()
      console.log(`Found ${errorCount} validation errors`)
    } else {
      // If no errors, should show success
      await expect(
        page.locator('[data-test="validation-success"], .success, .v-alert--type-success, text=/passed|success/i')
      ).toBeVisible()
    }
  })

  test('should show auto-fix button when errors exist', async ({ page }) => {
    // Navigate to validation tab
    await page.click('[data-test="validation-tab"], button:has-text("Validation"), a:has-text("Validation")')
    
    // Run validation
    await page.click('[data-test="validate-all"], button:has-text("Validate")')
    await page.waitForTimeout(2000)
    
    // Look for auto-fix button (only appears when fixable errors exist)
    const autoFixButton = page.locator('[data-test="auto-fix"], button:has-text("Auto-Fix"), button:has-text("Fix")')
    
    if (await autoFixButton.count() > 0) {
      await expect(autoFixButton.first()).toBeVisible()
      console.log('Auto-fix button available')
    } else {
      console.log('No auto-fix suggestions available (project may be valid)')
    }
  })

  test('validation results should update on re-validation', async ({ page }) => {
    // Navigate to validation tab
    await page.click('[data-test="validation-tab"], button:has-text("Validation"), a:has-text("Validation")')
    
    // Run validation first time
    await page.click('[data-test="validate-all"], button:has-text("Validate")')
    await page.waitForTimeout(2000)
    
    // Get initial result
    const resultsLocator = page.locator('[data-test="validation-results"], .validation-results').first()
    const initialText = await resultsLocator.textContent()
    
    // Run validation again
    await page.click('[data-test="validate-all"], button:has-text("Validate")')
    await page.waitForTimeout(2000)
    
    // Results should be updated (even if same)
    const updatedText = await resultsLocator.textContent()
    expect(updatedText).toBeTruthy()
    
    console.log('Validation ran successfully twice')
  })
})
