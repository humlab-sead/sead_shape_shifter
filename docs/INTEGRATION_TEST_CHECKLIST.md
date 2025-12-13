# Integration Test Checklist - Query Builder Feature

**Date**: December 13, 2025  
**Feature**: Visual Query Builder with Backend Integration  
**Test Environment**: 
- Backend: http://localhost:8000
- Frontend: http://localhost:5173

---

## Prerequisites

### 1. Server Status
- [ ] Backend running on port 8000
  ```bash
  curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
  # Should return: {"status": "healthy", "version": "0.1.0"}
  ```

- [ ] Frontend running on port 5173
  ```bash
  timeout 3 curl -s http://localhost:5173 > /dev/null && echo "✓ OK" || echo "✗ Failed"
  ```

- [ ] Test database exists
  ```bash
  ls -lh input/test_query_tester.db
  # Should show SQLite database file
  ```

---

## Backend API Tests

### 2. Data Source API
- [ ] List data sources
  ```bash
  curl -s http://localhost:8000/api/v1/data-sources | python3 -m json.tool
  # Expected: Array with "test_sqlite" data source
  ```

- [ ] Get specific data source
  ```bash
  curl -s http://localhost:8000/api/v1/data-sources/test_sqlite | python3 -m json.tool
  # Expected: Data source details with driver="sqlite"
  ```

### 3. Schema Introspection API
- [ ] List tables
  ```bash
  curl -s http://localhost:8000/api/v1/data-sources/test_sqlite/tables | python3 -m json.tool
  # Expected: Array with 3 tables: orders, products, users
  ```

- [ ] Get table schema
  ```bash
  curl -s "http://localhost:8000/api/v1/data-sources/test_sqlite/tables/users/schema" | python3 -m json.tool
  # Expected: Table schema with 6 columns, primary_keys=["user_id"]
  ```

- [ ] Preview table data
  ```bash
  curl -s "http://localhost:8000/api/v1/data-sources/test_sqlite/tables/users/preview?limit=3" | python3 -m json.tool
  # Expected: 3 rows of user data with all 6 columns
  ```

### 4. Error Handling
- [ ] Non-existent data source
  ```bash
  curl -s http://localhost:8000/api/v1/data-sources/invalid_source | python3 -m json.tool
  # Expected: 404 error with clear message
  ```

- [ ] Non-existent table
  ```bash
  curl -s "http://localhost:8000/api/v1/data-sources/test_sqlite/tables/invalid_table/schema" | python3 -m json.tool
  # Expected: Error message (table not found)
  ```

---

## Frontend Integration Tests

### 5. Application Loading
- [ ] Open frontend in browser: http://localhost:5173
- [ ] Page loads without errors (check browser console for errors)
- [ ] Navigation menu visible
- [ ] No JavaScript errors in console

### 6. Navigate to Query Tester
- [ ] Click "Query Tester" in navigation menu OR
- [ ] Navigate directly to: http://localhost:5173/#/query-tester
- [ ] Page displays with two tabs: "SQL Editor" and "Visual Builder"
- [ ] Default tab is "SQL Editor"

---

## Visual Query Builder Tests

### 7. Basic UI Elements
- [ ] Click "Visual Builder" tab
- [ ] Query Builder component loads
- [ ] See these elements:
  - Data Source selector (dropdown)
  - Table selector (dropdown, disabled initially)
  - Column selector (multi-select, disabled initially)
  - Conditions section (collapsed)
  - Order By section (collapsed)
  - LIMIT field (default: 100)
  - "Generate SQL" button (disabled initially)
  - "Use This Query" button (disabled initially)
  - "Clear" button

### 8. Data Source Selection
- [ ] Click Data Source dropdown
- [ ] **Expected**: "test_sqlite" appears in list
- [ ] Select "test_sqlite"
- [ ] **Expected**: 
  - Table selector becomes enabled
  - Loading indicator appears briefly
  - No errors in console

### 9. Table Selection
- [ ] Click Table dropdown
- [ ] **Expected**: See 3 tables:
  - orders
  - products
  - users
- [ ] Select "users" table
- [ ] **Expected**:
  - Column selector becomes enabled
  - Loading indicator appears briefly
  - Columns load automatically
  - No errors in console

### 10. Column Selection
- [ ] Click Column selector
- [ ] **Expected**: See 6 columns:
  - user_id
  - username
  - email
  - age
  - created_at
  - is_active
- [ ] Click "Select All" at top of dropdown
- [ ] **Expected**: All 6 columns selected
- [ ] **Expected**: SQL preview appears showing:
  ```sql
  SELECT *
  FROM "users"
  LIMIT 100
  ```
- [ ] Unselect some columns (e.g., keep only username, email, age)
- [ ] **Expected**: SQL updates to show selected columns:
  ```sql
  SELECT "username", "email", "age"
  FROM "users"
  LIMIT 100
  ```

### 11. WHERE Conditions
- [ ] Expand "WHERE Conditions" section
- [ ] Click "Add Condition" button
- [ ] **Expected**: New condition row appears with:
  - Column dropdown (populated with available columns)
  - Operator dropdown (=, !=, <, >, <=, >=, etc.)
  - Value text field
  - Delete button
- [ ] Set condition: `age > 30`
  - Column: age
  - Operator: >
  - Value: 30
- [ ] **Expected**: SQL updates automatically:
  ```sql
  SELECT "username", "email", "age"
  FROM "users"
  WHERE "age" > 30
  LIMIT 100
  ```
- [ ] Add second condition: `is_active = 1`
- [ ] **Expected**: SQL shows both conditions:
  ```sql
  SELECT "username", "email", "age"
  FROM "users"
  WHERE "age" > 30
    AND "is_active" = 1
  LIMIT 100
  ```
- [ ] Change AND/OR toggle to "OR"
- [ ] **Expected**: SQL changes to use OR
- [ ] Test different operators:
  - [ ] LIKE (e.g., `username LIKE '%alice%'`)
  - [ ] IN (e.g., `age IN (25, 30, 35)`)
  - [ ] IS NULL
  - [ ] IS NOT NULL

### 12. ORDER BY
- [ ] Expand "ORDER BY" section
- [ ] Click "Add ORDER BY" button
- [ ] **Expected**: New order by row appears
- [ ] Set: Column=username, Direction=ASC
- [ ] **Expected**: SQL includes ORDER BY clause:
  ```sql
  SELECT "username", "email", "age"
  FROM "users"
  WHERE "age" > 30
    AND "is_active" = 1
  ORDER BY "username" ASC
  LIMIT 100
  ```
- [ ] Add second order: age DESC
- [ ] **Expected**: SQL shows both:
  ```sql
  ORDER BY "username" ASC, "age" DESC
  ```

### 13. LIMIT
- [ ] Change LIMIT value to 5
- [ ] **Expected**: SQL updates to `LIMIT 5`
- [ ] Try clearing LIMIT field
- [ ] **Expected**: SQL removes LIMIT clause
- [ ] Set it back to 100

### 14. Generate and Use Query
- [ ] Click "Generate SQL" button
- [ ] **Expected**: 
  - SQL preview shows generated query
  - "Use This Query" button becomes enabled
  - Success chip appears ("SQL Generated")
- [ ] Click "Use This Query" button
- [ ] **Expected**: 
  - Switch to "SQL Editor" tab
  - Generated SQL appears in editor
  - (Note: Query execution may not work yet - that's OK)

### 15. Clear Builder
- [ ] Switch back to "Visual Builder" tab
- [ ] Click "Clear" button
- [ ] **Expected**:
  - All selections reset
  - Data source cleared
  - Table cleared
  - Columns cleared
  - Conditions cleared
  - Order by cleared
  - LIMIT back to 100
  - SQL preview disappears

---

## Edge Cases & Error Handling

### 16. Empty States
- [ ] With no data source selected, confirm:
  - Table selector disabled
  - Column selector disabled
  - "Generate SQL" button disabled
- [ ] With data source but no table:
  - Column selector disabled
  - "Generate SQL" button disabled
- [ ] With data source and table but no columns:
  - "Generate SQL" button disabled

### 17. API Error Simulation
- [ ] Stop the backend server:
  ```bash
  pkill -f "uvicorn backend.app.main:app"
  ```
- [ ] In Query Builder, try selecting a data source
- [ ] **Expected**: 
  - Error message appears (network error or API error)
  - UI handles gracefully (no crash)
  - Check browser console for error logged
- [ ] Restart backend:
  ```bash
  cd /home/roger/source/sead_shape_shifter && \
  CONFIG_FILE=input/query_tester_config.yml \
  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
  ```
- [ ] Refresh page and verify functionality restored

### 18. Browser Console Check
- [ ] Open browser developer tools (F12)
- [ ] Go through Query Builder workflow again
- [ ] **Expected**: 
  - No error messages in console
  - API calls visible in Network tab
  - Successful responses (200 OK)

---

## Different Tables Test

### 19. Test with "products" Table
- [ ] Select "test_sqlite" data source
- [ ] Select "products" table
- [ ] **Expected**: 6 columns appear:
  - product_id, product_name, category, price, stock_quantity, supplier_id
- [ ] Select all columns
- [ ] Add condition: `price > 50`
- [ ] Add order by: `price DESC`
- [ ] **Expected**: Valid SQL generated
- [ ] Verify SQL syntax is correct

### 20. Test with "orders" Table
- [ ] Select "orders" table
- [ ] **Expected**: 5 columns appear:
  - order_id, user_id, order_date, total_amount, status
- [ ] Build a complex query with:
  - 3+ conditions
  - 2+ order by clauses
  - Custom LIMIT
- [ ] Verify SQL is syntactically correct

---

## Performance Tests

### 21. Response Times
- [ ] Measure data source loading time
  - **Expected**: < 1 second
- [ ] Measure table list loading time
  - **Expected**: < 2 seconds
- [ ] Measure schema loading time (columns)
  - **Expected**: < 2 seconds
- [ ] Measure SQL generation time
  - **Expected**: Instant (< 100ms)

### 22. Rapid Changes
- [ ] Rapidly change selections:
  - Switch data sources quickly
  - Switch tables quickly
  - Add/remove columns quickly
- [ ] **Expected**:
  - No UI freezing
  - Debouncing works (not too many API calls)
  - Final state is consistent
  - SQL updates correctly

---

## Success Criteria

### Must Pass
- [x] Backend APIs return correct data
- [x] Frontend loads without errors
- [x] Data sources load from API
- [x] Tables load when data source selected
- [x] Columns load when table selected
- [x] SQL generates correctly
- [x] Generated SQL is valid syntax
- [x] Clear button resets state

### Should Pass
- [ ] Error handling is graceful
- [ ] Loading indicators appear
- [ ] No console errors
- [ ] Performance is acceptable
- [ ] UI is responsive

### Nice to Have
- [ ] Transitions are smooth
- [ ] Help tooltips are helpful
- [ ] Keyboard shortcuts work
- [ ] Mobile-responsive (if applicable)

---

## Notes & Issues Found

**Tester Name**: _________________  
**Date**: _________________  
**Browser**: _________________  

### Issues Found
1. 
2. 
3. 

### Suggestions
1. 
2. 
3. 

### Additional Comments



---

## Quick Test Command

Run this to verify all backend APIs in one go:

```bash
cd /home/roger/source/sead_shape_shifter

echo "=== Quick Backend Test ==="
curl -s http://localhost:8000/api/v1/health | python3 -c "import sys, json; d=json.load(sys.stdin); print('✓ Health:', d['status'])" && \
curl -s http://localhost:8000/api/v1/data-sources | python3 -c "import sys, json; d=json.load(sys.stdin); print('✓ Data sources:', [x['name'] for x in d])" && \
curl -s http://localhost:8000/api/v1/data-sources/test_sqlite/tables | python3 -c "import sys, json; d=json.load(sys.stdin); print('✓ Tables:', [x['name'] for x in d])" && \
curl -s "http://localhost:8000/api/v1/data-sources/test_sqlite/tables/users/schema" | python3 -c "import sys, json; d=json.load(sys.stdin); print('✓ Schema:', len(d['columns']), 'columns')" && \
echo "=== All APIs Working ==="
```

## Test Summary

**Total Tests**: 22 sections  
**Completed**: _____ / 22  
**Passed**: _____ / _____  
**Failed**: _____ / _____  
**Status**: ⬜ Pass / ⬜ Fail / ⬜ Partial

**Overall Assessment**: 
