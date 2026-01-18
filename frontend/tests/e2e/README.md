# Playwright E2E Tests

End-to-end tests for the Shape Shifter frontend application using Playwright.

## Overview

These tests verify critical user workflows and ensure the application works correctly from a user's perspective.

## Test Structure

```
tests/e2e/
├── fixtures/           # Test data and helper functions
│   └── projects.ts    # Sample project configurations
├── 00-smoke.spec.ts   # Basic application loading tests
├── 01-project-management.spec.ts  # Project CRUD operations
├── 02-validation-workflow.spec.ts # Validation and auto-fix
└── 03-entity-management.spec.ts   # Entity CRUD and preview
```

## Running Tests

### All tests (headless)
```bash
pnpm test:e2e
```

### Interactive UI mode (recommended for development)
```bash
pnpm test:e2e:ui
```

### Headed mode (see browser)
```bash
pnpm test:e2e:headed
```

### Debug mode
```bash
pnpm test:e2e:debug
```

### Specific test file
```bash
pnpm test:e2e tests/e2e/01-project-management.spec.ts
```

### Generate new tests interactively
```bash
pnpm test:e2e:codegen
```

## Test Reports

After running tests, view the HTML report:
```bash
npx playwright show-report
```

## Writing Tests

### Test Fixtures

Use test fixtures from `fixtures/projects.ts` for consistent test data:

```typescript
import { testProjects } from './fixtures/projects'

test('example with fixture', async ({ page }) => {
  // Use predefined project data
  const project = testProjects.minimal
  // ... test logic
})
```

### Selectors Best Practices

1. **Prefer data-test attributes** (add these to components as needed):
   ```typescript
   await page.click('[data-test="validate-button"]')
   ```

2. **Use accessible roles**:
   ```typescript
   await page.click('button:has-text("Validate")')
   ```

3. **Avoid brittle selectors** (CSS classes, deep nesting):
   ```typescript
   // ❌ Bad
   await page.click('.v-btn.primary > span')
   
   // ✅ Good
   await page.click('[data-test="validate-button"]')
   await page.click('button:has-text("Validate")')
   ```

### Waiting Strategies

```typescript
// Wait for navigation
await page.waitForLoadState('networkidle')

// Wait for element
await expect(page.locator('[data-test="results"]')).toBeVisible()

// Wait for API response
await page.waitForResponse(resp => resp.url().includes('/api/validate'))
```

## Test Categories

### Smoke Tests (00-smoke.spec.ts)
- Application loads
- No console errors
- Basic navigation works

### Critical Workflows
- **Project Management**: CRUD operations
- **Validation**: Run validation, view errors, auto-fix
- **Entity Management**: Create, edit, preview entities
- **Reconciliation**: Configure and run reconciliation (TODO)
- **Dispatch**: Configure and execute dispatch (TODO)

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Main branch commits

### GitHub Actions Configuration

```yaml
- name: Install dependencies
  run: pnpm install

- name: Install Playwright browsers
  run: npx playwright install --with-deps chromium

- name: Run E2E tests
  run: pnpm test:e2e

- name: Upload test report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Debugging Tips

### 1. Use UI Mode
```bash
pnpm test:e2e:ui
```
- Time travel debugger
- Step through tests
- Inspect DOM at each step

### 2. Use Debug Mode
```bash
pnpm test:e2e:debug
```
- Runs headed with debugger
- Pauses on failures

### 3. Screenshots and Videos
Automatically captured on failure:
- Screenshots: `test-results/*/test-failed-*.png`
- Videos: `test-results/*/video.webm`

### 4. Playwright Inspector
```bash
PWDEBUG=1 pnpm test:e2e
```

### 5. Console Logs
```typescript
test('debug example', async ({ page }) => {
  page.on('console', msg => console.log('BROWSER:', msg.text()))
  // ... test
})
```

## Adding New Tests

1. Create a new spec file: `tests/e2e/04-my-feature.spec.ts`
2. Use the test template:

```typescript
import { test, expect } from '@playwright/test'

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    // Setup
  })

  test('should do something', async ({ page }) => {
    // Test logic
  })
})
```

3. Add data-test attributes to components as needed
4. Run tests: `pnpm test:e2e tests/e2e/04-my-feature.spec.ts`

## Common Patterns

### Navigate to a project
```typescript
await page.goto('/')
await page.click('text=Projects')
await page.click('[data-test="project-item"]')
```

### Fill and submit form
```typescript
await page.fill('[name="entity-name"]', 'my_entity')
await page.selectOption('[name="type"]', 'sql')
await page.click('button:has-text("Save")')
```

### Wait for validation
```typescript
await page.click('button:has-text("Validate")')
await expect(page.locator('[data-test="validation-results"]')).toBeVisible({ timeout: 10000 })
```

### Check for success/error
```typescript
const hasError = await page.locator('.v-alert--type-error').count() > 0
if (hasError) {
  // Handle error case
} else {
  // Handle success case
}
```

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Selectors Guide](https://playwright.dev/docs/selectors)
- [Debugging Guide](https://playwright.dev/docs/debug)
