import { test, expect } from '@playwright/test'

/**
 * Critical Workflow Test: Project Management
 * 
 * Tests the core project CRUD operations
 */

test.describe('Project Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should display projects page', async ({ page }) => {
    // Navigate to projects
    await page.click('text=Projects')
    
    // Should show projects list
    await expect(page.locator('h1, h2, h3').filter({ hasText: /projects/i })).toBeVisible()
  })

  test('should create new project', async ({ page }) => {
    // Navigate to projects
    await page.click('text=Projects')
    
    // Click new project button
    await page.click('button:has-text("New")')
    
    // Fill in project name
    const projectName = `test-project-${Date.now()}`
    await page.fill('input[name="name"], input[placeholder*="name" i]', projectName)
    
    // Submit form
    await page.click('button:has-text("Create")')
    
    // Should see success message or redirect to project
    await expect(
      page.locator(`text=${projectName}`).first()
    ).toBeVisible({ timeout: 10000 })
  })

  test('should open existing project', async ({ page }) => {
    // Navigate to projects
    await page.click('text=Projects')
    
    // Wait for project list to load
    await page.waitForLoadState('networkidle')
    
    // Click on first project (if any exist)
    const firstProject = page.locator('[data-test="project-item"], .project-card, .project-list-item').first()
    
    if (await firstProject.count() > 0) {
      const projectName = await firstProject.textContent()
      await firstProject.click()
      
      // Should navigate to project detail page
      await expect(page).toHaveURL(/\/projects\/[^\/]+/)
      
      // Should show project name in header
      await expect(page.locator('h1, h2').filter({ hasText: projectName || '' })).toBeVisible()
    } else {
      test.skip('No projects available to test')
    }
  })
})
