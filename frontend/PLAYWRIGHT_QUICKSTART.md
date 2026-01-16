# Playwright E2E Testing - Quick Start Guide

## What We've Set Up

✅ **Playwright installed** with Chromium, Firefox, and WebKit browsers
✅ **Configuration file** (`playwright.config.ts`)
✅ **Test fixtures** for reusable test data
✅ **Initial test suites** covering critical workflows
✅ **npm scripts** for easy test execution

## Test Files Created

```
tests/e2e/
├── fixtures/
│   └── projects.ts          # Sample project configurations
├── 00-smoke.spec.ts         # Basic app loading tests
├── 01-project-management.spec.ts  # Project CRUD
├── 02-validation-workflow.spec.ts # Validation & auto-fix
├── 03-entity-management.spec.ts   # Entity CRUD & preview
└── README.md                # Detailed documentation
```

## Quick Start

### 1. Run Your First Test

```bash
# Make sure the dev server is running in another terminal
pnpm run dev

# Then in a new terminal, run tests in UI mode (recommended for learning)
pnpm run test:e2e:ui
```

The UI mode will open and show you:
- All available tests
- Time travel debugger
- DOM snapshots at each step
- Network activity
- Console logs

### 2. Run Tests Headless (CI mode)

```bash
pnpm run test:e2e
```

This runs all tests in the background and shows results in terminal.

### 3. Generate New Tests Interactively

```bash
# This opens a browser where you can interact with your app
# Playwright records your actions and generates test code!
pnpm run test:e2e:codegen
```

Click around your app, and Playwright will generate the test code for you.

### 4. Debug Failing Tests

```bash
pnpm run test:e2e:debug
```

This opens the Playwright Inspector where you can:
- Step through each action
- See the browser state
- Modify selectors on the fly

## What Each Test Suite Does

### 00-smoke.spec.ts (Foundation)
- ✅ App loads without errors
- ✅ Navigation menu exists
- ✅ No critical console errors
- ✅ 404 handling works

**Run time:** ~10 seconds

### 01-project-management.spec.ts (Projects)
- ✅ Display projects page
- ✅ Create new project
- ✅ Open existing project

**Run time:** ~15 seconds

### 02-validation-workflow.spec.ts (Validation)
- ✅ Navigate to validation tab
- ✅ Run validation
- ✅ Display validation errors
- ✅ Show auto-fix suggestions
- ✅ Re-validation updates results

**Run time:** ~30 seconds

### 03-entity-management.spec.ts (Entities)
- ✅ Navigate to entities tab
- ✅ Display entity tree
- ✅ Open add entity dialog
- ✅ Switch between Form/YAML modes
- ✅ Close dialog on cancel
- ✅ Preview entity data

**Run time:** ~25 seconds

**Total test suite:** ~80 seconds

## Next Steps

### Phase 1: Add data-test Attributes (Recommended)

For more reliable tests, add `data-test` attributes to your Vue components:

```vue
<!-- EntityFormDialog.vue -->
<v-dialog data-test="entity-dialog">
  <v-btn data-test="save-entity">Save</v-btn>
  <v-btn data-test="cancel">Cancel</v-btn>
</v-dialog>
```

Then update tests to use these:
```typescript
await page.click('[data-test="save-entity"]')
```

### Phase 2: Add More Workflows

Create tests for:
- Reconciliation workflow (`04-reconciliation.spec.ts`)
- Dispatch workflow (`05-dispatch.spec.ts`)
- Dependency graph interactions (`06-graph.spec.ts`)
- YAML editor features (`07-yaml-editor.spec.ts`)

### Phase 3: CI Integration

Add to `.github/workflows/test.yml`:

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: pnpm/action-setup@v2
      
      - name: Install dependencies
        run: pnpm install
      
      - name: Install Playwright
        run: npx playwright install --with-deps chromium
      
      - name: Run E2E tests
        run: pnpm run test:e2e
      
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

## Tips for Writing Tests

### 1. Use Test Fixtures
```typescript
import { testProjects } from './fixtures/projects'

test('my test', async ({ page }) => {
  const project = testProjects.withForeignKeys
  // Use predefined data
})
```

### 2. Wait for Network Idle
```typescript
await page.waitForLoadState('networkidle')
```

### 3. Use Soft Assertions for Multiple Checks
```typescript
await expect.soft(page.locator('.error')).toBeVisible()
await expect.soft(page.locator('.warning')).toHaveCount(2)
// Both assertions run even if first fails
```

### 4. Group Related Tests
```typescript
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Common setup
  })
  
  test('scenario 1', async ({ page }) => {})
  test('scenario 2', async ({ page }) => {})
})
```

### 5. Skip Tests Conditionally
```typescript
test('conditional test', async ({ page }) => {
  const hasData = await page.locator('[data-test="item"]').count() > 0
  if (!hasData) {
    test.skip('No data available')
  }
  // ... rest of test
})
```

## Common Commands

```bash
# Run all tests
pnpm test:e2e

# Run specific file
pnpm test:e2e tests/e2e/01-project-management.spec.ts

# Run tests matching pattern
pnpm test:e2e --grep "validation"

# Run in specific browser
pnpm test:e2e --project=firefox

# Update snapshots
pnpm test:e2e --update-snapshots

# Show test report
npx playwright show-report

# Clear test cache
rm -rf test-results playwright-report
```

## Learning Resources

- **Playwright Docs:** https://playwright.dev
- **Selectors Guide:** https://playwright.dev/docs/selectors
- **Best Practices:** https://playwright.dev/docs/best-practices
- **API Reference:** https://playwright.dev/docs/api/class-test

## Troubleshooting

### Tests fail with "Navigation timeout"
- Increase timeout in `playwright.config.ts`
- Or add explicit waits: `await page.waitForLoadState('networkidle')`

### Can't find element
- Use `pnpm test:e2e:codegen` to record the correct selector
- Use `page.locator('[data-test="element"]').first()` if multiple matches

### Tests pass locally but fail in CI
- Add `--with-deps` when installing browsers in CI
- Use `process.env.CI` to adjust timeouts/behavior

## Success Criteria

You'll know Playwright is working when:
- ✅ `pnpm test:e2e` runs all tests successfully
- ✅ `pnpm test:e2e:ui` opens interactive UI
- ✅ Tests catch real bugs in your workflows
- ✅ You can record new tests with `codegen`

## Getting Help

If you encounter issues:
1. Check the test output for specific errors
2. Run with `--debug` flag: `pnpm test:e2e:debug`
3. View the HTML report: `npx playwright show-report`
4. Check the detailed README: `tests/e2e/README.md`

---

**Happy Testing! 🎭**

You've now got a solid foundation for E2E testing with Playwright. Start with the smoke tests, then gradually add more coverage for your critical workflows.
