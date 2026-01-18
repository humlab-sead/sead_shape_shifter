import { test, expect } from '@playwright/test'

/**
 * Smoke Test: Application Basics
 * 
 * Quick tests to ensure the application loads and basic navigation works
 */

test.describe('Application Smoke Tests', () => {
  test('should load homepage', async ({ page }) => {
    await page.goto('/')
    
    // Should load without errors
    await expect(page).not.toHaveTitle(/404|error/i)
    
    // Should show main app container
    await expect(page.locator('#app, [data-app], main').first()).toBeVisible()
  })

  test('should have navigation menu', async ({ page }) => {
    await page.goto('/')
    
    // Should show navigation (sidebar or header)
    await expect(
      page.locator('nav, [data-test="navigation"], .v-navigation-drawer').first()
    ).toBeVisible({ timeout: 5000 })
  })

  test('should navigate to Projects page', async ({ page }) => {
    await page.goto('/')
    
    // Click Projects navigation link
    await page.click('text=Projects')
    
    // Should navigate to projects route
    await expect(page).toHaveURL(/\/projects/)
  })

  test('should not have console errors on load', async ({ page }) => {
    const consoleErrors: string[] = []
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })
    
    await page.goto('/')
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle')
    
    // Should not have critical errors (some warnings are OK)
    const criticalErrors = consoleErrors.filter(err => 
      !err.includes('DevTools') && // Ignore DevTools warnings
      !err.includes('favicon') && // Ignore favicon 404s during dev
      !err.includes('Extension') // Ignore extension warnings
    )
    
    if (criticalErrors.length > 0) {
      console.log('Console errors found:', criticalErrors)
    }
    
    expect(criticalErrors.length).toBe(0)
  })

  test('should handle 404 gracefully', async ({ page }) => {
    await page.goto('/this-route-does-not-exist-12345')
    
    // Should show 404 message or redirect to home
    const has404 = await page.locator('text=/404|not found/i').count() > 0
    const isHome = page.url().endsWith('/') || page.url().includes('/projects')
    
    expect(has404 || isHome).toBe(true)
  })
})
