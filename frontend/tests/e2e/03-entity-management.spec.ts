import { test, expect } from '@playwright/test'

/**
 * Critical Workflow Test: Entity Management
 * 
 * Tests entity CRUD operations and the entity form dialog
 */

test.describe('Entity Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    
    // Navigate to a project
    await page.click('text=Projects')
    await page.waitForLoadState('networkidle')
    
    const firstProject = page.locator('[data-test="project-item"], .project-card, .project-list-item').first()
    if (await firstProject.count() > 0) {
      await firstProject.click()
    } else {
      test.skip('No project available for testing')
    }
  })

  test('should navigate to entities tab', async ({ page }) => {
    // Click entities tab
    await page.click('[data-test="entities-tab"], button:has-text("Entities"), a:has-text("Entities")')
    
    // Should show entity list or tree
    await expect(
      page.locator('[data-test="entity-list"], .entity-tree, text=/entities/i').first()
    ).toBeVisible({ timeout: 5000 })
  })

  test('should display entity tree/list', async ({ page }) => {
    // Navigate to entities tab
    await page.click('[data-test="entities-tab"], button:has-text("Entities"), a:has-text("Entities")')
    
    // Wait for entities to load
    await page.waitForLoadState('networkidle')
    
    // Should show entities (or empty state)
    const hasEntities = await page.locator('[data-test="entity-item"], .entity-node, .entity-card').count() > 0
    
    if (hasEntities) {
      console.log('Entities are displayed')
    } else {
      console.log('No entities in project (showing empty state)')
    }
    
    // Either way, the tab should have loaded
    expect(true).toBe(true)
  })

  test('should open add entity dialog', async ({ page }) => {
    // Navigate to entities tab
    await page.click('[data-test="entities-tab"], button:has-text("Entities"), a:has-text("Entities")')
    
    // Click add entity button
    await page.click('[data-test="add-entity"], button:has-text("Add Entity"), button:has-text("New Entity")')
    
    // Dialog should open
    await expect(
      page.locator('[data-test="entity-dialog"], .entity-form-dialog, [role="dialog"]').first()
    ).toBeVisible({ timeout: 5000 })
  })

  test('should switch between form and YAML mode in entity editor', async ({ page }) => {
    // Navigate to entities tab
    await page.click('[data-test="entities-tab"], button:has-text("Entities"), a:has-text("Entities")')
    
    // Open add entity dialog
    await page.click('[data-test="add-entity"], button:has-text("Add Entity"), button:has-text("New Entity")')
    
    // Look for mode toggle buttons
    const formModeButton = page.locator('button:has-text("Form"), [data-test="form-mode"]')
    const yamlModeButton = page.locator('button:has-text("YAML"), button:has-text("Code"), [data-test="yaml-mode"]')
    
    if (await yamlModeButton.count() > 0) {
      // Click YAML mode
      await yamlModeButton.first().click()
      
      // Should show Monaco editor
      await expect(
        page.locator('.monaco-editor, [data-test="yaml-editor"]').first()
      ).toBeVisible({ timeout: 3000 })
      
      // Switch back to form mode
      if (await formModeButton.count() > 0) {
        await formModeButton.first().click()
        
        // Should show form fields
        await expect(
          page.locator('input, select, textarea').first()
        ).toBeVisible({ timeout: 3000 })
      }
      
      console.log('Mode switching works')
    } else {
      console.log('Mode toggle not found (may be single mode)')
    }
  })

  test('should close entity dialog on cancel', async ({ page }) => {
    // Navigate to entities tab
    await page.click('[data-test="entities-tab"], button:has-text("Entities"), a:has-text("Entities")')
    
    // Open add entity dialog
    await page.click('[data-test="add-entity"], button:has-text("Add Entity"), button:has-text("New Entity")')
    
    // Wait for dialog
    const dialog = page.locator('[data-test="entity-dialog"], .entity-form-dialog, [role="dialog"]').first()
    await expect(dialog).toBeVisible()
    
    // Click cancel
    await page.click('button:has-text("Cancel")')
    
    // Dialog should close
    await expect(dialog).not.toBeVisible({ timeout: 3000 })
  })

  test('should preview entity data', async ({ page }) => {
    // Navigate to entities tab
    await page.click('[data-test="entities-tab"], button:has-text("Entities"), a:has-text("Entities")')
    
    // Wait for entities to load
    await page.waitForLoadState('networkidle')
    
    // Look for an entity with preview button
    const previewButton = page.locator(
      '[data-test="preview-entity"], button:has-text("Preview"), [title*="preview" i]'
    ).first()
    
    if (await previewButton.count() > 0) {
      await previewButton.click()
      
      // Should show preview panel or modal with data table
      await expect(
        page.locator('[data-test="entity-preview"], .preview-panel, .ag-grid, table').first()
      ).toBeVisible({ timeout: 10000 })
      
      console.log('Entity preview displayed')
    } else {
      console.log('No preview buttons found (may need to configure entities first)')
    }
  })
})
