# Testing Appendix - Shape Shifter

## Useful Keyboard Shortcuts

### Application Shortcuts

- `Ctrl/Cmd + S` - Save project
- `Ctrl/Cmd + K` - Open command palette
- `Ctrl/Cmd + Shift + L` - Toggle log viewer overlay
- `Ctrl/Cmd + H` - Go to home
- `Ctrl/Cmd + Shift + C` - Go to projects
- `Ctrl/Cmd + /` - Toggle comments in YAML editor
- `Esc` - Close dialogs/overlays

### DevTools Shortcuts

- `F12` - Open/close DevTools
- `Ctrl/Cmd + Shift + C` - Element picker
- `Ctrl/Cmd + Shift + M` - Responsive design mode
- `Ctrl/Cmd + Shift + P` - Command menu in DevTools

---

## Common Issues and Solutions

### Application Won't Load

**Symptoms:**
- Blank page
- Infinite loading spinner
- Console errors

**Solutions:**
- Check backend is running (http://localhost:8012/api/v1/health)
- Clear browser cache and hard reload (Ctrl+Shift+R)
- Check console for JavaScript errors
- Verify network connectivity to backend

### YAML Editor Not Highlighting Syntax

**Symptoms:**
- Plain text display
- No color coding
- No autocomplete

**Solutions:**
- Refresh page (F5)
- Check console for Monaco Editor errors
- Clear browser cache
- Verify JavaScript is enabled

### Validation Not Running

**Symptoms:**
- "Validate All" button doesn't respond
- No validation results appear
- Loading state persists indefinitely

**Solutions:**
- Check Network tab for API errors
- Verify backend connection (health endpoint)
- Clear validation cache
- Check for YAML syntax errors preventing validation

### Entity Editor Won't Open

**Symptoms:**
- Dialog doesn't appear
- Click has no effect
- Console errors

**Solutions:**
- Check console for errors
- Verify entity exists in project configuration
- Refresh page and retry
- Check browser console for React/Vue errors

### Save Not Working

**Symptoms:**
- Save button disabled
- Save fails silently
- Changes not persisted

**Solutions:**
- Check for validation errors (red indicators)
- Verify backend has write permissions
- Check Network tab for failed POST requests
- Ensure YAML is valid (check syntax)

### Preview Fails to Load

**Symptoms:**
- Empty preview area
- Error message in preview
- Loading spinner never completes

**Solutions:**
- Check entity configuration (data source, query)
- Verify database connection
- Check SQL syntax (for SQL entities)
- Review console for errors

### Execute Workflow Fails

**Symptoms:**
- Execution error
- Output file not created
- Partial results

**Solutions:**
- Run validation first
- Check dispatcher configuration
- Verify output path permissions
- Review execution logs
- Check data source connectivity

---

## Test Data Locations

### Project Files

- **Projects Directory**: `/home/roger/source/sead_shape_shifter/projects/`
- **Test Database**: `/home/roger/source/sead_shape_shifter/projects/test_query_tester.db`
- **Backups**: `/home/roger/source/sead_shape_shifter/backups/`

### Sample Projects

- `arbodat-test` - Small test project with basic entities
- `dendro_example` - Complex dendrochronology data project
- `ceramics_test` - Test project with multiple data sources

### Test Databases

- `test_query_tester.db` - SQLite database for testing SQL queries
- Various PostgreSQL test databases on `humlab-sead` server

---

## Browser DevTools Tips

### Network Tab

**Useful Filters:**
- `XHR` - Filter API requests only
- `status-code:404` - Find 404 errors
- `larger-than:100k` - Find large responses

**Throttling:**
- Fast 3G - Test on slower connections
- Offline - Test offline behavior

**Preserve Log:**
- Enable to keep requests across page navigations

### Console Tab

**Filtering:**
- `Errors` - Show only errors
- `Warnings` - Show only warnings
- `Verbose` - Show all log levels

**Useful Commands:**
```javascript
// Clear console
clear()

// Monitor function calls
monitor(functionName)

// Get all localStorage
console.table(localStorage)

// Performance timing
performance.getEntriesByType('navigation')
```

### Performance Tab

**Recording:**
1. Start recording
2. Perform actions
3. Stop recording
4. Analyze timeline

**Look for:**
- Long tasks (> 50ms)
- Layout thrashing
- Memory leaks
- Render-blocking resources

### Application Tab

**Local Storage:**
- View stored project settings
- Clear cache manually

**Session Storage:**
- View temporary session data

**Cookies:**
- Check authentication tokens

---

## Testing Tools

### Browser Extensions

**Chrome/Edge:**
- React DevTools - Inspect React components
- Vue.js DevTools - Inspect Vue components
- Redux DevTools - Debug state management
- axe DevTools - Accessibility testing
- WAVE - Accessibility evaluation

**Firefox:**
- Firefox Developer Tools - Built-in comprehensive tools
- Vue.js DevTools - Vue component inspection
- Accessibility Inspector - Built-in a11y tools

### Online Tools

- [Can I Use](https://caniuse.com/) - Browser compatibility
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) - Color contrast
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Performance audits
- [PageSpeed Insights](https://pagespeed.web.dev/) - Performance analysis

---

## Environment Setup

### Backend Server

```bash
# Start backend
cd /home/roger/source/sead_shape_shifter
make backend-run
# or
make br

# Backend runs at: http://localhost:8012
# Health check: http://localhost:8012/api/v1/health
```

### Frontend Server

```bash
# Start frontend dev server
cd /home/roger/source/sead_shape_shifter
make frontend-run
# or
make fr

# Frontend runs at: http://localhost:5173
```

### Database Connections

**PostgreSQL (SEAD):**
- Host: humlab-sead.srv.its.umu.se
- Port: 5432
- Database: sead_staging / sead_production
- User: sead_read / sead_write

**SQLite (Local):**
- Path: `projects/test_query_tester.db`

---

## Related Documentation

- [Testing Guide](../TESTING_GUIDE.md) - Main functional testing procedures
- [Non-Functional Testing Guide](NON_FUNCTIONAL_TESTING_GUIDE.md) - Performance, browser compatibility
- [Accessibility Testing Guide](ACCESSIBILITY_TESTING_GUIDE.md) - WCAG compliance testing
- [Error Scenario Testing](ERROR_SCENARIO_TESTING.md) - Error handling verification
- [Test Results Template](TEST_RESULTS_TEMPLATE.md) - Test documentation format

---

## Contact

For questions or issues with testing:
- File GitHub issue: https://github.com/humlab-sead/sead_shape_shifter/issues
- Tag with `testing` or `documentation` label
- Include environment details and steps to reproduce
