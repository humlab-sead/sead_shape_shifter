# Error Scenario Testing - Shape Shifter

## Overview

This guide covers error handling scenarios to ensure the application fails gracefully and provides meaningful feedback to users.

---

## Syntax Errors

### YAML Syntax Error

1. Introduce YAML syntax error (e.g., invalid indentation)
2. Attempt to save
3. Run validation

**Expected Results:**
- [ ] Editor highlights error
- [ ] Hover shows error message
- [ ] Save completes (allows invalid YAML)
- [ ] Validation shows syntax error
- [ ] Error message indicates line number

---

## Missing References

### Reference Non-Existent Entity

1. In foreign key, reference entity that doesn't exist
2. Save entity
3. Run validation

**Expected Results:**
- [ ] Validation error appears
- [ ] Error message: "Entity 'xxx' not found"
- [ ] Location information provided
- [ ] Can fix by updating reference

---

## Circular Dependencies

### Create Circular Dependency

1. Entity A depends on Entity B
2. Entity B depends on Entity A
3. Run validation

**Expected Results:**
- [ ] Validation error about circular dependency
- [ ] Entities involved listed
- [ ] Can fix by removing one dependency

---

## Invalid SQL

### Malformed SQL in Entity

1. Create SQL entity
2. Enter invalid SQL (e.g., missing FROM clause)
3. Save entity
4. Try to preview

**Expected Results:**
- [ ] Preview fails gracefully
- [ ] Error message shows SQL error
- [ ] No app crash
- [ ] Can edit SQL and retry

---

## API Errors

### Backend Unavailable

1. Stop backend server (`Ctrl+C` in backend terminal)
2. Try to load project or validate

**Expected Results:**
- [ ] Error notification appears
- [ ] Error message: "Unable to connect to server"
- [ ] UI remains functional (no crash)
- [ ] Can retry after restarting backend

### API Returns Error

1. Trigger API error (e.g., invalid data source reference)
2. Observe error handling

**Expected Results:**
- [ ] Error notification with details
- [ ] Error logged to console
- [ ] User-friendly error message
- [ ] Can dismiss and continue

---

## Network Errors

### Slow/Failed Network Requests

1. Open DevTools Network tab
2. Throttle to "Slow 3G"
3. Perform actions (load project, validate, preview)

**Expected Results:**
- [ ] Loading indicators appear
- [ ] Requests eventually complete
- [ ] Timeout handled gracefully (if request fails)
- [ ] User notified of issues
- [ ] Can retry failed requests

---

## Best Practices

### Error Testing Checklist

When testing error scenarios:

- [ ] Verify user receives clear, actionable error messages
- [ ] Confirm application doesn't crash or enter invalid state
- [ ] Check error messages are logged to console for debugging
- [ ] Test recovery path (can user retry/fix the issue?)
- [ ] Verify UI remains responsive during errors
- [ ] Ensure error state is properly cleared on retry

### Common Error Patterns

**Network Errors:**
- Use descriptive messages ("Unable to connect to server")
- Provide retry mechanism
- Don't expose stack traces to users

**Validation Errors:**
- Show location of error (line number, entity name)
- Explain what's wrong and how to fix it
- Allow saving invalid YAML for later fixing

**Data Errors:**
- Graceful degradation (show partial data if possible)
- Clear indication of what failed
- Suggest corrective actions

---

## Contact

For error handling issues:
- File GitHub issue: https://github.com/humlab-sead/sead_shape_shifter/issues
- Tag with `error-handling` label
- Include error messages and stack traces
