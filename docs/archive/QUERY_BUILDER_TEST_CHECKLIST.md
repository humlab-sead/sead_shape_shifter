# Visual Query Builder - Integration Test Checklist

**Test Date**: 2025-12-13  
**Backend**: http://localhost:8000  
**Frontend**: http://localhost:5173  
**Test Page**: http://localhost:5173/query-tester

## Test Environment Setup
- [x] Backend server running (port 8000)
- [x] Frontend dev server running (port 5173)
- [x] Query Tester page accessible
- [ ] Data sources configured in backend
- [ ] Test database with sample data available

---

## Phase 1: Visual Builder Basic Flow

### 1.1 UI Loading
- [ ] Query Tester page loads without errors
- [ ] Two tabs visible: "SQL Editor" and "Visual Builder"
- [ ] Tab icons display correctly (mdi-code-tags, mdi-database-cog)

### 1.2 Data Source Selection
- [ ] Visual Builder tab accessible
- [ ] Data source dropdown displays available sources
- [ ] Selecting data source triggers table loading
- [ ] Loading indicator appears while fetching tables

### 1.3 Table Selection
- [ ] Table dropdown populates after data source selection
- [ ] Tables display with schema information (if applicable)
- [ ] Selecting table triggers column loading
- [ ] Loading indicator appears while fetching schema

### 1.4 Column Selection
- [ ] Column selector displays all table columns
- [ ] "Select All" toggle works correctly
- [ ] Individual column selection works
- [ ] Selected columns display as chips
- [ ] SQL preview updates: `SELECT column1, column2 FROM table`
- [ ] Selecting all columns shows `SELECT *`

---

## Phase 2: WHERE Conditions

### 2.1 Add Condition
- [ ] "Add Condition" button enabled after table selection
- [ ] Clicking button adds new condition card
- [ ] Condition card has column selector, operator, value input, delete button

### 2.2 Operators Testing

#### Equals (=)
- [ ] Operator selection works
- [ ] Value input visible
- [ ] SQL generates: `WHERE column = 'value'`
- [ ] Numeric values not quoted: `WHERE id = 123`

#### Not Equals (!=)
- [ ] Generates: `WHERE column != 'value'`

#### Comparison (<, <=, >, >=)
- [ ] Less than: `WHERE column < 'value'`
- [ ] Less or equal: `WHERE column <= 'value'`
- [ ] Greater than: `WHERE column > 'value'`
- [ ] Greater or equal: `WHERE column >= 'value'`

#### IS NULL
- [ ] Value input hidden for IS NULL
- [ ] SQL generates: `WHERE column IS NULL`

#### IS NOT NULL
- [ ] Value input hidden for IS NOT NULL
- [ ] SQL generates: `WHERE column IS NOT NULL`

#### LIKE
- [ ] Accepts pattern with wildcards
- [ ] SQL generates: `WHERE column LIKE '%pattern%'`

#### NOT LIKE
- [ ] SQL generates: `WHERE column NOT LIKE '%pattern%'`

#### IN
- [ ] Accepts comma-separated values
- [ ] SQL generates: `WHERE column IN ('val1', 'val2', 'val3')`

#### NOT IN
- [ ] SQL generates: `WHERE column NOT IN ('val1', 'val2')`

#### BETWEEN
- [ ] Accepts "value1 AND value2" format
- [ ] SQL generates: `WHERE column BETWEEN 'value1' AND 'value2'`

### 2.3 Multiple Conditions
- [ ] Adding 2nd condition shows AND/OR radio buttons
- [ ] Default logic is AND
- [ ] Toggle to OR updates SQL correctly
- [ ] SQL with AND: `WHERE cond1 AND cond2`
- [ ] SQL with OR: `WHERE cond1 OR cond2`
- [ ] 3+ conditions join correctly

### 2.4 Condition Management
- [ ] Delete button removes condition
- [ ] Deleting last condition hides AND/OR toggle
- [ ] Condition panel can be collapsed/expanded

---

## Phase 3: ORDER BY

### 3.1 Basic ORDER BY
- [ ] ORDER BY panel expands
- [ ] "Add ORDER BY" button works
- [ ] Column selector populates
- [ ] Direction dropdown shows ASC/DESC
- [ ] SQL generates: `ORDER BY column ASC`

### 3.2 Multiple ORDER BY
- [ ] Add 2nd ORDER BY column
- [ ] SQL generates: `ORDER BY col1 ASC, col2 DESC`
- [ ] Delete button removes ORDER BY entry

### 3.3 ORDER BY Panel
- [ ] Panel can collapse/expanded
- [ ] Chip shows count when collapsed

---

## Phase 4: LIMIT

### 4.1 LIMIT Input
- [ ] LIMIT field accepts numeric input
- [ ] Default value is 100
- [ ] SQL updates: `LIMIT 50`

### 4.2 LIMIT Validation
- [ ] Minimum value enforced (1)
- [ ] Maximum value enforced (10,000)
- [ ] Invalid values rejected
- [ ] Hint text shows: "Maximum 10,000 rows"

---

## Phase 5: SQL Generation & Transfer

### 5.1 SQL Preview
- [ ] Generated SQL card visible
- [ ] SQL syntax highlighted (monospace font)
- [ ] SQL updates in real-time as selections change
- [ ] "SQL Generated" chip appears when SQL exists

### 5.2 Generate SQL Button
- [ ] Button disabled when no columns selected
- [ ] Button enabled when valid selection exists
- [ ] Clicking generates/updates SQL

### 5.3 Use This Query
- [ ] "Use This Query" button visible
- [ ] Button disabled when no SQL generated
- [ ] Clicking switches to SQL Editor tab
- [ ] Generated SQL loaded into editor textarea
- [ ] Data source pre-selected in editor
- [ ] Success snackbar appears
- [ ] Snackbar message: "SQL query loaded into editor..."
- [ ] Page scrolls to top

### 5.4 Clear Button
- [ ] Clear button resets all selections
- [ ] Data source cleared
- [ ] Table cleared
- [ ] Columns cleared
- [ ] Conditions cleared
- [ ] ORDER BY cleared
- [ ] LIMIT reset to 100
- [ ] SQL preview cleared

---

## Phase 6: SQL Execution

### 6.1 Execute from Editor
- [ ] Execute Query button enabled
- [ ] Button shows loading state during execution
- [ ] Query executes successfully
- [ ] Results appear below editor

### 6.2 Keyboard Shortcut
- [ ] Ctrl+Enter (Linux/Windows) executes query
- [ ] Cmd+Enter (Mac) executes query
- [ ] Hint text visible below textarea

### 6.3 Execution Statistics
- [ ] Execution time displayed (ms)
- [ ] Row count shown
- [ ] Truncation warning if 10K rows limit hit

### 6.4 Validation
- [ ] Validate button works
- [ ] Validation errors display in red alert
- [ ] Validation warnings display in orange alert
- [ ] Statement type chip shows SELECT
- [ ] Table names extracted and displayed

### 6.5 Explain Query
- [ ] Explain button works
- [ ] Query plan displays in expansion panel
- [ ] Plan shows estimated cost/rows
- [ ] Plan text formatted (monospace)

---

## Phase 7: Results Display

### 7.1 Results Table
- [ ] Data table displays with all columns
- [ ] Column headers visible and clear
- [ ] Rows display correctly
- [ ] Fixed header (scrollable body)
- [ ] 500px height enforced

### 7.2 Pagination
- [ ] Pagination controls visible
- [ ] Items per page selector: 10/25/50/100
- [ ] Default is 25 items per page
- [ ] Page navigation works (prev/next)
- [ ] "Showing X-Y of Z" text accurate
- [ ] Total pages calculated correctly

### 7.3 Cell Formatting
- [ ] NULL values: red text, italic, opacity 0.7
- [ ] Numbers: right-aligned, primary color
- [ ] Booleans: secondary color, bold
- [ ] Strings: default formatting
- [ ] Objects: JSON.stringify display

### 7.4 Statistics Bar
- [ ] Row count chip displayed
- [ ] Column count chip displayed
- [ ] Execution time chip displayed
- [ ] Truncation warning chip (if applicable)

### 7.5 Export to CSV
- [ ] Export button visible when results exist
- [ ] Clicking triggers file download
- [ ] Filename includes timestamp
- [ ] CSV contains all rows (not just visible page)
- [ ] CSV headers included
- [ ] Special characters escaped (quotes, commas)
- [ ] File opens correctly in spreadsheet app

---

## Phase 8: Error Handling

### 8.1 Destructive Query Prevention
- [ ] Generate valid SELECT query
- [ ] Switch to SQL Editor
- [ ] Change SELECT to DELETE
- [ ] Execute query
- [ ] Error message: "Destructive SQL operation 'DELETE' is not allowed"
- [ ] Test with: INSERT, UPDATE, DROP, CREATE, ALTER, TRUNCATE

### 8.2 Syntax Errors
- [ ] Enter invalid SQL (e.g., missing FROM)
- [ ] Validation shows syntax error
- [ ] Error message is clear and helpful
- [ ] No server crash

### 8.3 Connection Errors
- [ ] Select non-existent data source
- [ ] Error message displays
- [ ] 404 error handled gracefully

### 8.4 Query Timeout
- [ ] Long-running query (>30s) times out
- [ ] Timeout error message displayed
- [ ] User can cancel/retry

### 8.5 Empty Results
- [ ] Query returns 0 rows
- [ ] "Query returned no results" alert shows
- [ ] No table errors
- [ ] Stats show 0 rows

---

## Phase 9: Complex Query End-to-End

### 9.1 Build Complex Query
- [ ] Select data source
- [ ] Select table with 10+ columns
- [ ] Select 5-7 specific columns
- [ ] Add 3 WHERE conditions
- [ ] Set logic to OR
- [ ] Add 2 ORDER BY columns (ASC + DESC)
- [ ] Set LIMIT to 500
- [ ] Verify SQL is syntactically correct
- [ ] Verify all clauses present

### 9.2 Execute Complex Query
- [ ] Transfer to SQL Editor
- [ ] Execute query
- [ ] Results display correctly
- [ ] Pagination works with 500 rows
- [ ] Export works for full result set

---

## Phase 10: Edge Cases

### 10.1 Special Characters
- [ ] Column names with spaces/special chars
- [ ] Table names with schema prefix
- [ ] Values with quotes, commas, newlines
- [ ] SQL escaping works correctly

### 10.2 Large Results
- [ ] Query with 10,000 rows (limit)
- [ ] Truncation warning displays
- [ ] Pagination handles max rows
- [ ] Export includes all 10K rows

### 10.3 Empty States
- [ ] No data sources configured
- [ ] Table with no columns (edge case)
- [ ] Empty table (0 rows)
- [ ] Appropriate messages display

### 10.4 Browser Compatibility
- [ ] Works in Chrome/Chromium
- [ ] Works in Firefox
- [ ] Works in Safari
- [ ] Works in Edge

---

## Phase 11: UI/UX Testing

### 11.1 Responsiveness
- [ ] Works on full-width display
- [ ] Works on half-width split screen
- [ ] Mobile view (if applicable)
- [ ] Components don't overflow

### 11.2 Visual Feedback
- [ ] Loading indicators appear during async ops
- [ ] Disabled states clear (grayed out)
- [ ] Success states highlighted (green)
- [ ] Error states highlighted (red)
- [ ] Hover effects on buttons/cards

### 11.3 Navigation
- [ ] Tab switching smooth
- [ ] State preserved when switching tabs
- [ ] Back button works (browser)
- [ ] Page refresh preserves data sources

### 11.4 Help Section
- [ ] Help expansion panel works
- [ ] Keyboard shortcuts documented
- [ ] Security/limits explained
- [ ] Example queries clickable
- [ ] Example loads into editor correctly

---

## Test Results Summary

### Passed Tests: 0 / TBD
### Failed Tests: 0
### Blocked Tests: 0
### Not Tested: TBD

---

## Issues Found

| # | Severity | Component | Description | Status |
|---|----------|-----------|-------------|--------|
| 1 |          |           |             |        |

---

## Notes
- Test environment: Development (localhost)
- Browser: VS Code Simple Browser
- OS: Linux
- Database: [To be specified]

---

## Sign-off
- [ ] All critical tests passed
- [ ] No blocking issues found
- [ ] Ready for production deployment
