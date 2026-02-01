# Shape Shifter Project Editor - User Guide

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Working with Projects](#3-working-with-configurations)
4. [Managing Entities](#4-managing-entities)
5. [Validation](#5-validation)
6. [Auto-Fix Features](#6-auto-fix-features)
7. [Execute Workflow](#7-execute-workflow)
8. [Quick Wins & Performance Features](#8-quick-wins--performance-features)
9. [Tips & Best Practices](#9-tips--best-practices)
10. [Troubleshooting](#10-troubleshooting)
11. [FAQ](#11-faq)

---

## 1. Introduction

### What is Shape Shifter?

Shape Shifter is a declarative data transformation framework that uses YAML configurations to harmonize diverse data sources into target schemas. The Project Editor provides a visual interface for creating and managing these transformation configurations.

### Who Should Use This Guide?

This guide is for:
- **Domain Data Managers** - Managing entitys
- **Data Engineers** - Creating complex transformations
- **Developers** - Integrating transformations into workflows

### Key Features

- **Visual Project Editor** - Monaco Editor for YAML editing
- **Entity Tree Navigation** - Browse entities and dependencies
- **Real-Time Validation** - Immediate feedback on errors
- **Auto-Fix Capabilities** - Intelligent error resolution
- **Data Preview** - See transformation results
- **Performance Optimizations** - Fast, responsive interface
- **Three-Tier Identity System** - Clear separation of local, source, and target identities

### What's New: Three-Tier Identity System

**Important Update:** Shape Shifter now uses a three-tier identity system for clearer entity identification:

1. **System ID** (`system_id`) - Auto-managed local identity
   - Always uses column name `system_id`
   - Auto-incremented (1, 2, 3...)
   - Scoped to your project only
   - Read-only, cannot be changed

2. **Business Keys** (`keys`) - Source domain identifiers
   - Natural keys from your source data
   - Used for deduplication and reconciliation
   - Multi-column support for composite keys
   - Example: `[site_code, year]` or `[sample_name]`

3. **Public ID** (`public_id`) - Target system primary key
   - Defines the column name for target database PK
   - Used to name foreign key columns in child entities
   - Must end with `_id` suffix
   - Required field with validation
   - Example: `site_id`, `sample_type_id`

**Migration Note:** Legacy configurations using `surrogate_id` are automatically migrated to `public_id`. No manual changes required.

---

## 2. Getting Started

### System Requirements

**Browser:**
- Chrome 120+ (recommended)
- Firefox 115+
- Safari 16+
- Edge 120+

**Hardware:**
- Modern CPU (dual-core minimum)
- 4GB RAM minimum
- 1280x720 display minimum (1920x1080 recommended)

### Launching the Editor

1. Start the backend server:
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload
   ```

2. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open your browser to `http://localhost:5173`

### Interface Overview

```
┌──────────────────────────────────────────────────────────┐
│  Project Editor                      [Save] [Validate]│
├─────────────┬────────────────────────┬────────────────────┤
│             │                        │                    │
│  Entity     │   Monaco Editor        │  Validation        │
│  Tree       │   (YAML)               │  Panel             │
│             │                        │                    │
│  • entity_1 │  entities:             │  ✓ No errors       │
│  • entity_2 │    entity_1:           │                    │
│    - entity_3│      type: entity       │  📋 Properties     │
│             │      columns: [...]    │                    │
│             │                        │                    │
└─────────────┴────────────────────────┴────────────────────┘
```

**Three Main Panels:**

1. **Left: Entity Tree** - Navigate entities and dependencies
2. **Center: Monaco Editor** - Edit YAML configuration
3. **Right: Validation/Properties** - View errors and entity details

### First Steps

1. **Open a Project**
   - Click "Open Project" in the toolbar
   - Select from available configurations
   - Project loads into editor

2. **Explore the Entity Tree**
   - Left panel shows all entities
   - Click entity to jump to its definition
   - Expand/collapse dependency trees

3. **Run Validation**
   - Click "Validate All" button
   - Review results in right panel
   - Fix any errors found

---

## 3. Working with Projects

### Opening Projects

**Method 1: Project Selector**
1. Click dropdown in toolbar
2. Select configuration name
3. Project loads automatically

**Method 2: Recent Files**
1. Recently opened configs appear at top
2. Click to reopen instantly
3. Access last 5 configurations quickly

### Creating New Projects

1. Click "New Project"
2. Enter configuration name
3. Choose template (optional):
   - Empty configuration
   - Basic entity setup
   - From existing config
4. Click "Create"
5. Editor opens with template

### Editing YAML

The Monaco Editor provides:

**Syntax Highlighting:**
- Keywords in blue
- Strings in green
- Numbers in orange
- Comments in gray

**Auto-Completion:**
- Start typing entity name
- Press `Ctrl+Space` for suggestions
- Select from dropdown
- Press `Tab` to insert

**Validation:**
- Red underlines for syntax errors
- Yellow underlines for warnings
- Hover for error details
- Click to see fix suggestions

**Keyboard Shortcuts:**
- `Ctrl/Cmd + S` - Save configuration
- `Ctrl/Cmd + F` - Find in file
- `Ctrl/Cmd + H` - Find and replace
- `Ctrl/Cmd + Z` - Undo
- `Ctrl/Cmd + Shift + Z` - Redo
- `Ctrl/Cmd + /` - Toggle comment
- `Ctrl/Cmd + D` - Duplicate line
- `Alt + Up/Down` - Move line up/down

### Saving Projects

**Manual Save:**
1. Make your changes
2. Click "Save" button
3. Success message confirms save
4. Backup created automatically

**Auto-Save:**
- Saves after 30 seconds of inactivity
- Indicated by "Auto-saved" message
- Can be disabled in settings

**Save Indicators:**
- Asterisk (*) in title = unsaved changes
- "Saved" badge = all changes saved
- Timestamp shows last save time

### Project Backups

Every save creates a timestamped backup:

**Location:** `/backups/`  
**Format:** `project_name.backup.YYYYMMDD_HHMMSS.yml`  
**Example:** `arbodat.backup.20251214_143022.yml`

**To Restore from Backup:**
1. Navigate to `/backups/` directory
2. Find desired backup by timestamp
3. Copy to main config directory
4. Rename to remove `.backup` suffix
5. Reload in editor

---

## 4. Managing Entities

### Entity Tree Navigation

The left panel shows your configuration's entity structure:

**Root Entities** (no dependencies):
```
• sample_type
• species
```

**Dependent Entities** (indented under parent):
```
• sample
  - sample_measurement
  - sample_analysis
```

**Navigation:**
- Click entity → jump to definition
- Double-click → expand/collapse
- Right-click → context menu (future)

### Entity Types

**Entity (Derived):**
```yaml
entity_name:
  type: entity
  source: null  # Root entity or name of another entity
  columns: [col1, col2, col3]
```

**SQL Entity:**
```yaml
entity_name:
  type: sql
  data_source: database_name
  query: "SELECT * FROM table"
```

**Fixed Entity:**
```yaml
entity_name:
  type: fixed
  values:
    - [val1, val2]
    - [val3, val4]
```

**CSV Entity:**
```yaml
entity_name:
  type: csv
  columns: [col1, col2]
  options:
    filename: projects/my-file.csv
    sep: ","           # optional, defaults to comma
    encoding: utf-8     # optional
```

**Excel Entity (Pandas):**
```yaml
entity_name:
  type: xlsx
  columns: [col1, col2]
  options:
    filename: projects/my-file.xlsx
    sheet_name: Sheet1   # optional; defaults to first sheet
```

**Excel Entity (OpenPyXL):**
```yaml
entity_name:
  type: openpyxl
  columns: [col1, col2]
  options:
    filename: projects/my-file.xlsx
    sheet_name: Sheet1
    range: A1:D50        # optional
```

### Adding Entities

**Method 1: Direct YAML Editing**
1. Position cursor in `entities:` section
2. Type new entity name
3. Add required fields
4. Save configuration

**Method 2: Properties Panel (Future)**
1. Click "Add Entity" button
2. Fill in entity details
3. Click "Create"
4. Entity added to YAML

### Editing Entity Properties

#### Form Editor vs. YAML Editor

Shape Shifter provides **two ways to edit entities**, similar to VS Code's settings editor:

1. **Form Editor** (Default) - Visual form with input fields
2. **YAML Editor** - Raw YAML code with syntax highlighting

**Switching Between Editors:**
- Click the **Form** tab for visual editing
- Click the **YAML** tab for code editing
- Changes sync automatically when switching tabs

#### Using the Form Editor

The form editor provides a structured interface for editing entity properties:

**Identity Configuration (Three-Tier System):**

Shape Shifter uses a three-tier identity system to manage entity identification:

1. **System ID Column** (Auto-managed)
   - **Field**: System ID
   - **Description**: Local project-scoped identity, auto-incremented (1, 2, 3...)
   - **Default**: `system_id` (read-only, cannot be changed)
   - **Purpose**: Internal tracking within the transformation pipeline
   - **Scope**: Local to this project only

2. **Business Keys** (Source Identifiers)
   - **Field**: Business Keys
   - **Description**: Natural/domain keys from source data for deduplication and reconciliation
   - **Format**: Multi-select list of column names
   - **Example**: `[site_code, year]` or `[sample_name]`
   - **Purpose**: Identify unique records in source data, detect duplicates
   - **Scope**: Source system domain

3. **Public ID** (Target System Identity)
   - **Field**: Public ID Column
   - **Description**: Target system primary key name that defines FK column naming in child entities
   - **Format**: Single column name ending in `_id`
   - **Example**: `site_id`, `sample_type_id`
   - **Required**: Yes (validation enforces `_id` suffix)
   - **Purpose**: Maps to remote system, determines foreign key column names
   - **Scope**: Target database or external system

**Column Selection:**
- **Field**: Columns
- **Description**: Columns to extract from source
- **Format**: Comma-separated list
- **Example**: `col1, col2, col3`

**Dependencies:**
- **Field**: Source Entity
- **Description**: Parent entity this depends on
- **Format**: Entity name from configuration

- **Field**: Additional Dependencies
- **Description**: Other entities required for processing
- **Format**: Comma-separated list of entity names

#### Using the YAML Editor

The YAML editor provides direct access to the entity's YAML definition:

**Features:**
- **Monaco Editor** - Same editor as VS Code
- **Syntax Highlighting** - YAML syntax coloring
- **Real-Time Validation** - Immediate syntax error detection
- **Error Display** - Clear error messages with line numbers

**Example YAML:**
```yaml
entity_name:
  system_id: system_id  # Auto-managed local identity (default, cannot change)
  keys: [key1, key2]  # Business keys from source data for deduplication
  public_id: entity_name_id  # Target system PK (defines FK column names in children)
  columns: [col1, col2, col3]  # Columns to extract
  source: parent_entity  # Depends on parent_entity
  depends_on: [other_entity]  # Additional dependencies
```

**Legacy Format (Backward Compatible):**
```yaml
entity_name:
  surrogate_id: entity_name_id  # Automatically migrated to public_id
  keys: [key1, key2]
  # ... rest of config
```

**When to Use YAML Editor:**
- Complex nested configurations
- Copying/pasting entire entity definitions
- Bulk editing multiple fields
- Advanced users comfortable with YAML syntax

**When to Use Form Editor:**
- Learning the configuration structure
- Editing specific fields
- Preventing syntax errors
- Guided field-by-field editing

**YAML Validation:**
- Invalid YAML shows **red error banner**
- Error message includes line number and description
- Cannot switch back to Form until YAML is valid
- Validation happens automatically as you type

**Auto-Synchronization:**
- **Form → YAML**: Switching to YAML tab converts form data to YAML
- **YAML → Form**: Switching from YAML tab (with valid YAML) updates form fields
- Changes are **not saved** until you click Save/OK button

### Foreign Key Relationships

Define relationships between entities:

```yaml
entity_name:
  foreign_keys:
    - entity: remote_entity
      local_keys: [local_col]
      remote_keys: [remote_col]
      how: inner  # inner, left, outer, cross
      constraints:
        cardinality: many_to_one
        require_unique_left: true
        allow_null_keys: false
```

**Cardinality Options:**
- `one_to_one` - Each left row matches exactly one right row
- `many_to_one` - Multiple left rows match one right row
- `one_to_many` - One left row matches multiple right rows

**Join Types:**
- `inner` - Keep only matching rows
- `left` - Keep all left rows, match or not
- `outer` - Keep all rows from both sides
- `cross` - Cartesian product

### Unnesting (Melt Operations)

Transform wide data to long format:

```yaml
entity_name:
  unnest:
    id_vars: [id, name]
    value_vars: [col1, col2, col3]
    var_name: attribute
    value_name: measurement
```

**Before (Wide):**
```
id | name  | col1 | col2 | col3
1  | Item1 | 10   | 20   | 30
```

**After (Long):**
```
id | name  | attribute | measurement
1  | Item1 | col1      | 10
1  | Item1 | col2      | 20
1  | Item1 | col3      | 30
```

### Deleting Entities

**Manual Deletion:**
1. Select entity definition in YAML
2. Delete all lines for that entity
3. Save configuration
4. Validation will check for orphaned references

**Important:** Check dependent entities before deleting!

### Reordering Entities

The system automatically orders entities by dependencies. Manual YAML order doesn't affect processing order.

**Processing Order:**
1. Root entities (no dependencies)
2. First-level dependents
3. Second-level dependents
4. And so on...

---

## 5. Validation

### Validation Types

**Structural Validation:**
- YAML syntax correctness
- Entity definitions complete
- References resolve correctly
- No circular dependencies

**Data Validation:**
- Columns exist in data sources
- Foreign key relationships valid
- Data types compatible
- Constraint satisfaction

**Comprehensive (All):**
- Runs both structural and data validation
- Recommended before processing

### Running Validation

**Validate All:**
1. Click "Validate All" button
2. Comprehensive check runs
3. Results appear in right panel
4. Issues grouped by severity

**Validate Entity:**
1. Select entity in tree
2. Click "Validate Entity"
3. Focused validation on selected entity
4. Faster for iterative editing

**Validate Structural:**
1. Click "Structural" tab
2. Click "Validate" button
3. Quick syntax and structure check
4. No data source access needed

**Validate Data:**
1. Click "Data" tab
2. Click "Validate" button
3. Checks against actual data
4. Requires data source access

### Understanding Validation Results

**Severity Levels:**

🔴 **Error** - Must fix before processing
- Structural errors
- Missing required fields
- Invalid references
- Constraint violations

⚠️ **Warning** - Should review
- Performance concerns
- Potential issues
- Best practice violations

ℹ️ **Info** - Optional improvements
- Suggestions
- Optimization tips
- Documentation reminders

**Result Details:**

Each issue shows:
- **Message** - What's wrong
- **Entity** - Which entity has the issue
- **Location** - Line number in YAML
- **Fix Available** - Auto-fix available?
- **Suggestion** - How to resolve

### Validation Filtering

**Filter by Severity:**
- Click severity badge to filter
- Show only errors, warnings, or info
- Multiple selections allowed

**Filter by Entity:**
- Select entity in tree
- Shows issues for that entity only
- Click "All" to clear filter

**Search Issues:**
- Type in search box
- Filters by message text
- Real-time filtering

### Validation Cache

Results are cached for 5 minutes:

**Cache Hit (instant):**
- Same configuration
- Same validation type
- Within 5-minute window
- No changes made

**Cache Miss (calls API):**
- Different configuration
- First validation
- Cache expired (>5 min)
- Project changed

**Benefits:**
- 97% faster repeat validations
- Reduced server load
- Better offline resilience

---

## 6. Auto-Fix Features

### What is Auto-Fix?

Auto-fix analyzes validation errors and provides:
- **Automated solutions** for fixable issues
- **Guided recommendations** for complex problems
- **Safe application** with automatic backups
- **Preview capabilities** before applying changes

### Accessing Auto-Fix

**Step 1: Run Validation**
1. Click "Validate All" or "Validate Entity"
2. Review validation results
3. Look for issues with fix suggestions

**Step 2: Identify Fixable Issues**
- Green "Auto-Fix Available" badge
- Green "Apply Fix" button
- Click issue for details

**Step 3: Preview Fix**
1. Click "Preview Fix" button
2. Review before/after comparison
3. Check changes are correct
4. Verify no unintended side effects

**Step 4: Apply Fix**
1. Click "Apply Fix" button
2. Automatic backup created
3. Fix applied to configuration
4. Editor updates with corrected YAML
5. Success message confirms

### Common Fixable Issues

#### Missing Columns

**Problem:** Project references non-existent columns

**Example Error:**
```
Column 'old_column' not found in data
Entity: sample_entity
```

**Auto-Fix Action:**
- Removes the missing column from config
- Updates `columns` list
- Preserves all other settings

**Before:**
```yaml
entity_name:
  columns: [id, name, old_column, value]
```

**After:**
```yaml
entity_name:
  columns: [id, name, value]
```

#### Invalid Foreign Key References

**Problem:** Foreign key references non-existent entity

**Example Error:**
```
Referenced entity 'old_entity' not found
Entity: sample_entity
Field: foreign_keys
```

**Auto-Fix Recommendation:**
- Provides guidance on fixing reference
- Suggests checking entity names
- May require manual intervention

#### Duplicate Business Keys

**Problem:** Data has duplicate values for business keys (natural identifiers)

**Example Error:**
```
Found 5 duplicate business keys
Entity: sample_entity
Keys: name, code
```

**Auto-Fix:**
- Not automatically fixable (data quality issue)
- Manual review required
- Options:
  1. Add more columns to keys for uniqueness
  2. Clean source data to remove duplicates
  3. Use system_id as temporary identifier
  4. Investigate root cause in source system

**Best Practice:**
- Business keys should uniquely identify records in source data
- Used for deduplication and reconciliation
- Consider composite keys if single column insufficient

**Auto-Fix Recommendation:**
- Guidance on resolving duplicates
- Suggests reviewing data or key definition
- Requires manual data cleaning

### Fix Types Explained

**Automatic Fixes (Green Badge):**

✅ **Remove Column** - Safely removes non-existent column
✅ **Update Reference** - Updates entity references (coming soon)
✅ **Add Column** - Adds missing required column (coming soon)

**Manual Fixes (Yellow Badge):**

⚠️ **Unresolved Reference** - Check entity names
⚠️ **Duplicate Keys** - Review data or change keys
⚠️ **Type Mismatch** - Verify data types

**Complex Issues (Red Badge):**

🔴 **Circular Dependencies** - Restructure relationships
🔴 **Data Quality** - Clean source data
🔴 **Schema Conflicts** - Resolve structural issues

### Safety Features

#### Automatic Backups

Every fix application creates a backup:

**Format:** `config.backup.YYYYMMDD_HHMMSS.yml`  
**Location:** `/backups/` directory  
**Example:** `my_config.backup.20251214_143022.yml`

#### Preview Before Apply

Preview shows:
- **Exact changes** to your configuration
- **Reason** for the fix
- **Impact** on data processing
- **Warnings** about potential side effects

#### Validation After Fix

After applying:
1. Project automatically revalidated
2. New results show if issue resolved
3. Remaining issues displayed
4. Additional fixes can be applied

### Best Practices

**✅ Do:**
- Validate regularly after edits
- Review fix previews carefully
- Test after applying fixes
- Keep backups for one processing cycle
- Document significant changes

**❌ Don't:**
- Apply fixes without previewing
- Skip revalidation after fixes
- Delete backups immediately
- Apply multiple fixes without testing
- Ignore fix recommendations

### Keyboard Shortcuts

- `Ctrl/Cmd + V` - Validate configuration
- `Ctrl/Cmd + P` - Preview selected fix
- `Ctrl/Cmd + A` - Apply selected fix
- `Escape` - Close preview/fix dialog

---

## 7. Quick Wins & Performance Features

### Feature Overview

| Feature | Benefit | Impact |
|---------|---------|--------|
| Validation Caching | 97% faster repeat validations | Instant results |
| Contextual Tooltips | Learn features in-context | Reduced learning curve |
| Loading Skeleton | Clear loading feedback | Better perceived performance |
| Success Animations | Clear action confirmation | Professional polish |
| Debounced Validation | Smooth typing | No lag while editing |

### 1. Validation Result Caching

**What It Does:**
Caches validation results for 5 minutes, making repeat validations nearly instant.

**How It Works:**

First validation:
```
Click "Validate" → API call (200ms) → Cache result (5 min)
```

Subsequent validations:
```
Click "Validate" → Return cached (5ms) → 40x faster!
```

**Cache Behavior:**

✅ **Cache Used When:**
- Same configuration
- Same validation type
- Within 5-minute window
- No modifications made

❌ **Cache Cleared When:**
- 5 minutes elapsed
- Project modified
- Page refreshed
- Different config opened

**Benefits:**
- 70% reduction in API calls
- Faster iterative workflow
- Reduced server load
- Better offline resilience

### 2. Contextual Tooltips

**What It Does:**
Shows helpful information when hovering over buttons and controls.

**Available Tooltips:**

**Validation Panel:**
- "Validate All" → "Validate entire configuration against all rules"
- "Structural" tab → "Check configuration file structure and syntax"
- "Data" tab → "Validate against actual data sources"
- "Validate Entity" → "Validate only selected entity"

**Fix Buttons:**
- "Apply Fix" → "Preview and apply automated fix with backup"
- "Preview Fix" → "See changes before applying"

**How to Use:**
1. Hover over any button
2. Wait 500ms for tooltip
3. Read contextual help
4. Move away to dismiss

**Benefits:**
- Reduced learning curve
- Contextual help without leaving page
- No documentation lookup needed
- Consistent behavior

### 3. Loading Skeleton Animation

**What It Does:**
Shows animated placeholder while validation runs.

**Visual Design:**
- Realistic content layout
- Pulsing animation
- Professional appearance
- Smooth transition to results

**When It Appears:**
- Validation taking > 100ms
- Backend processing
- Network latency
- Data source access

**Benefits:**
- Better perceived performance
- Clear loading state
- Reduced user anxiety
- Professional polish

### 4. Success Animations

**What It Does:**
Smoothly animates success messages for clear feedback.

**Animation Details:**
- Scale from 80% to 100%
- 300ms duration
- Smooth easing curve
- GPU-accelerated

**When You'll See It:**
- Project saved
- Auto-fix applied
- Entity created
- Settings updated

**Visual Design:**
- Green color for success
- White text for contrast
- Stays visible 3 seconds
- Smooth fade-out

**Benefits:**
- Clear action confirmation
- Professional appearance
- Non-intrusive notifications
- Smooth user experience

### 5. Debounced Validation

**What It Does:**
Delays automatic validation while typing to avoid interrupting workflow.

**How It Works:**

Without debouncing:
```
Type "e" → Validate
Type "n" → Validate
Type "t" → Validate
...
= 6 validations, choppy typing
```

With debouncing:
```
Type "entity"
Wait 500ms
→ Single validation
= Smooth typing!
```

**Settings:**
- **Delay:** 500ms after last keystroke
- **Applies to:** YAML editor changes
- **Bypassed for:** Manual validation clicks

**Benefits:**
- Smoother typing experience
- Fewer unnecessary validations
- Reduced API load
- Better performance

### Performance Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Repeat Validation | 200ms | 5ms | 97% faster |
| Typing Lag | Frequent | None | Eliminated |
| API Calls (editing) | Many | Few | 70% less |
| Perceived Speed | Slow | Fast | Much better |

**Memory Overhead:** < 100KB total

---

## 7. Execute Workflow

### Overview

The Execute feature runs the complete Shape Shifter normalization pipeline on your project and exports the results to your chosen format. This is the final step after validation and testing.

**Workflow Steps:**
1. Optional validation
2. Load and normalize all entities
3. Apply optional transformations
4. Export to selected format

### Opening Execute Dialog

**From Project Detail View:**
1. Open your project
2. Click "Execute" button in toolbar (green play icon)
3. Execute dialog opens

### Selecting Output Format

**Available Dispatchers:**

**File Formats:**
- **Excel Workbook (xlsx)** - Single Excel file with sheets per entity
- **CSV (csv)** - Single CSV file (combined data)
- **CSV in ZIP (csv_zip)** - Folder of CSV files compressed as ZIP

**Database Formats:**
- **PostgreSQL** - Export to PostgreSQL database
- **SQLite** - Export to SQLite database file

**Folder Formats:**
- **CSV Folder** - Directory of separate CSV files per entity

**How to Select:**
1. Click "Output Format" dropdown
2. Review available dispatchers
3. Select desired format
4. Form updates for selected type

### Configuring File Output

**For File Dispatchers (Excel, CSV):**

1. Select file dispatcher
2. Enter output path (optional)
   - Default: `./output/{project_name}.{extension}`
   - Custom: `./custom/path/output.xlsx`
3. Path must match file extension
4. File will be created/overwritten

**Example Paths:**
```
./output/my_project.xlsx       ✅ Valid
./data/export.csv              ✅ Valid
./output/wrong.txt             ❌ Wrong extension
```

### Configuring Folder Output

**For Folder Dispatchers:**

1. Select folder dispatcher
2. Enter folder path (optional)
   - Default: `./output/{project_name}/`
   - Custom: `./custom/output/`
3. Folder will be created if needed
4. Each entity becomes separate file

**Output Structure:**
```
output/my_project/
  ├── entity_1.csv
  ├── entity_2.csv
  └── entity_3.csv
```

### Configuring Database Output

**For Database Dispatchers:**

1. Select database dispatcher
2. Choose target data source from dropdown
3. Data source must be pre-configured
4. Entities written as database tables

**Requirements:**
- Data source configured in Data Sources
- Database must exist
- Write permissions required
- Connection tested

### Execution Options

**Run Validation Before Execution:**
- **Default:** Enabled
- **Purpose:** Ensure configuration valid
- **Behavior:** Stops execution if validation fails
- **Tip:** Disable to force execution of invalid config (not recommended)

**Apply Translations:**
- **Default:** Disabled
- **Purpose:** Translate column names using configured mappings
- **Use When:** Target schema differs from source
- **Example:** `sample_id` → `sampleId`

**Drop Foreign Key Columns:**
- **Default:** Disabled
- **Purpose:** Remove foreign key columns from output
- **Use When:** Want only natural keys
- **Effect:** Cleaner output, fewer columns

### Running Execution

**Steps:**
1. Configure all settings
2. Click "Execute" button
3. Progress indicator appears
4. Wait for completion (may take minutes)
5. Success or error message displayed

**What Happens:**
1. Validation runs (if enabled)
2. Entities processed in dependency order
3. Transformations applied
4. Data exported to target
5. Result confirmation shown

### Download Results

**For File Outputs:**

1. Execution completes successfully
2. Success message shows entity count
3. "Download result file" button appears
4. Click to download file
5. File downloads to browser's download folder

**Download Features:**
- Works for all file dispatchers
- Direct browser download
- Original filename preserved
- Can download multiple times
- Link remains until dialog closed

**Not Available For:**
- Database outputs (data already in database)
- Folder outputs (access folder directly)

### Understanding Results

**Success Message Shows:**
- ✅ Success indicator
- Number of entities processed
- Output location/path
- Download button (if applicable)
- Execution time (implied)

**Example Success:**
```
Successfully executed workflow
Processed 12 entities to ./output/my_project.xlsx
[Download result file]
```

### Handling Errors

**Validation Errors:**
- Execution stops before processing
- Validation errors displayed
- Fix errors and retry
- Or disable "Run validation" (risky)

**Execution Errors:**
- Error message shown
- Details included when available
- Check logs for full trace
- Common causes:
  - Data source unavailable
  - Disk space full
  - Write permission denied
  - Invalid SQL in entity

**Error Recovery:**
1. Read error message
2. Fix underlying issue
3. Close and reopen dialog
4. Configure again
5. Retry execution

### Best Practices

**Before Execution:**
- ✅ Run full validation
- ✅ Fix all errors
- ✅ Preview entity data to verify transformations
- ✅ Verify data sources connected
- ✅ Check disk space available
- ✅ Backup existing output files

**Choosing Format:**
- **Excel** - Best for sharing, manual review
- **CSV** - Simple, universal compatibility
- **CSV in ZIP** - Many entities, organized
- **Database** - Integration, queries, large data
- **Folder** - Programmatic access, scripting

**Performance Tips:**
- Large datasets take longer
- Database output fastest for large data
- File outputs easier for small datasets
- Use entity preview to validate transformations before full execution

**Troubleshooting:**
- Check backend logs if execution fails
- Verify output path writable
- Test data source connections
- Review entity SQL for errors
- Try with validation disabled to see specific error

---

## 8. Quick Wins & Performance Features

### Workflow Tips

**1. Start with Validation**
- Always validate before processing
- Fix errors top-down (by severity)
- Revalidate after each fix

**2. Use Entity Tree for Navigation**
- Click entities to jump to definitions
- Understand dependency relationships
- Check impact before deleting

**3. Leverage Auto-Fix**
- Preview all fixes before applying
- Apply automatic fixes confidently
- Document manual fixes needed

**4. Take Advantage of Caching**
- Validate frequently without worry
- Iterate quickly on changes
- Trust automatic cache invalidation

**5. Learn Keyboard Shortcuts**
- Speed up common operations
- Reduce mouse usage
- More efficient editing

### Project Best Practices

**Entity Design:**
- ✅ Use descriptive entity names
- ✅ Define business keys carefully (for source data deduplication)
- ✅ Set public_id to match target system naming (defines FK columns)
- ✅ Keep system_id as default (`system_id`) for internal tracking
- ✅ Document complex relationships
- ✅ Keep entity scope focused

**Identity Fields:**
- ✅ **System ID**: Always use default `system_id` (auto-managed)
- ✅ **Business Keys**: Choose columns that uniquely identify source records
- ✅ **Public ID**: Must end with `_id`, matches target system PK name
- ✅ **FK Naming**: Child entities use parent's public_id as FK column name
- ✅ Test for duplicate business keys before processing

**Foreign Keys:**
- ✅ Always specify constraints
- ✅ Use appropriate cardinality
- ✅ Test join results
- ✅ Handle null keys explicitly
- ✅ Ensure FK column names match parent's public_id

**Column Selection:**
- ✅ Include only needed columns
- ✅ Use consistent naming
- ✅ Document column purposes
- ✅ Verify column availability

**Dependencies:**
- ✅ Keep dependency chains short
- ✅ Avoid circular dependencies
- ✅ Document complex dependencies
- ✅ Test processing order

### Validation Best Practices

**Regular Validation:**
- Validate after editing
- Validate before processing
- Validate when data changes
- Validate after applying fixes

**Fix Strategy:**
- Apply automatic fixes first
- Preview manual fixes carefully
- Test after each batch
- Document changes made

**Error Resolution:**
- Start with errors (red)
- Then warnings (yellow)
- Finally info items (blue)
- Don't ignore warnings

### Performance Best Practices

**Editor Usage:**
- Let debouncing work (don't wait)
- Use keyboard shortcuts
- Collapse unused entity trees
- Close unused tabs

**Validation:**
- Use entity-level validation when possible
- Leverage caching
- Don't spam validate button
- Clear old cache if needed

### Collaboration Best Practices

**Version Control:**
- Commit configurations regularly
- Write meaningful commit messages
- Review changes before committing
- Tag stable versions

**Documentation:**
- Document complex transformations
- Explain business logic
- Note known issues
- Keep README updated

**Communication:**
- Share configuration changes with team
- Document breaking changes
- Review each other's configurations
- Establish naming conventions

---

## 10. Troubleshooting

### Common Issues

#### Editor Won't Load Project

**Symptoms:** Blank editor or error message

**Solutions:**
1. Check file exists in config directory
2. Verify YAML syntax is valid
3. Check file permissions (read access)
4. Review browser console for errors
5. Try refreshing page

#### Validation Fails Immediately

**Symptoms:** Error message without results

**Solutions:**
1. Check backend server is running
2. Verify network connectivity
3. Check CORS configuration
4. Review backend logs
5. Try different browser

#### Auto-Fix Not Available

**Symptoms:** No "Apply Fix" button on errors

**Solutions:**
1. Not all errors are auto-fixable
2. Check issue type (only some types)
3. Verify backend supports auto-fix
4. Update to latest version
5. Contact support if expected

#### Changes Not Saving

**Symptoms:** Save fails or reverts

**Solutions:**
1. Check file write permissions
2. Verify disk space available
3. Check backup directory exists
4. Review backend logs for errors
5. Try saving to different location

#### Validation Cache Not Working

**Symptoms:** Every validation makes network request

**Solutions:**
1. Check browser cache not disabled
2. Verify < 5 minutes since last validation
3. Ensure config hasn't been modified
4. Try refreshing page
5. Check browser console for errors

### Performance Issues

#### Slow Editor Response

**Causes:**
- Large project files (> 10MB)
- Too many entities (> 100)
- Complex dependency trees
- Low system resources

**Solutions:**
1. Split large configs into modules
2. Reduce number of entities
3. Close other applications
4. Increase system RAM
5. Use faster computer

#### Validation Takes Too Long

**Causes:**
- Large data sources
- Complex validation rules
- Slow network
- Server under load

**Solutions:**
1. Use entity-level validation
2. Optimize data source queries
3. Check network latency
4. Scale backend resources
5. Enable caching

#### UI Freezes or Stutters

**Causes:**
- Browser resource limits
- Too many browser tabs
- Graphics driver issues
- JavaScript errors

**Solutions:**
1. Close unused tabs
2. Update browser
3. Update graphics drivers
4. Check console for errors
5. Try different browser

### Error Messages

#### "Project not found"

**Cause:** Config file doesn't exist or not in config directory

**Fix:** Check file path and location, verify file name

#### "Invalid YAML syntax"

**Cause:** Syntax error in YAML

**Fix:** Check indentation, quotes, brackets; use YAML validator

#### "Circular dependency detected"

**Cause:** Entity dependency loop

**Fix:** Review dependency graph, break circular reference

#### "Column 'X' not found"

**Cause:** Config references non-existent column

**Fix:** Remove column or add to data source; use auto-fix

#### "Entity 'X' not defined"

**Cause:** Reference to undefined entity

**Fix:** Define missing entity or fix reference

### Getting Help

**In-App Help:**
1. Hover tooltips on buttons
2. Click error for details
3. Check validation messages
4. Review auto-fix suggestions

**Documentation:**
1. This user guide
2. Project reference
3. API documentation
4. Developer guide

**Support:**
1. Check GitHub issues
2. Contact administrator
3. Submit bug report
4. Request feature

---

## 11. FAQ

### General Questions

**Q: What browsers are supported?**  
A: Chrome 120+, Firefox 115+, Safari 16+, Edge 120+. Chrome recommended.

**Q: Can I use offline?**  
A: Editor works offline for loaded configs. Validation requires backend connection.

**Q: Where are configurations stored?**  
A: In the configured directory, typically `projects/` or similar.

**Q: Are my changes auto-saved?**  
A: Yes, after 30 seconds of inactivity. Manual save recommended for important changes.

**Q: Can multiple users edit simultaneously?**  
A: Not currently. Last save wins. Future version will add collaboration features.

### Validation Questions

**Q: How long does validation take?**  
A: Typically 100-500ms. Data validation takes longer with large datasets.

**Q: What's the difference between structural and data validation?**  
A: Structural checks YAML syntax and references. Data checks against actual data sources.

**Q: Why validate if I'm not changing anything?**  
A: Data sources may change, or new validation rules may be added.

**Q: Can I skip validation?**  
A: Not recommended. Validation catches errors before processing fails.

### Auto-Fix Questions

**Q: Are auto-fixes safe?**  
A: Yes! Every fix creates an automatic backup.

**Q: Can I undo a fix?**  
A: Yes, restore from the automatic backup in `/backups/`.

**Q: Will fixes modify my data?**  
A: No, fixes only modify configuration, never source data.

**Q: Can I apply multiple fixes at once?**  
A: Not currently. Batch fix application planned for future release.

**Q: What if I disagree with a fix?**  
A: Skip it and fix manually in YAML editor.

### Performance Questions

**Q: Why is caching important?**  
A: Makes repeat validations 97% faster (from 200ms to 5ms).

**Q: How long are results cached?**  
A: 5 minutes. Clears automatically when configuration changes.

**Q: Can I disable caching?**  
A: Not recommended. Caching is automatic and transparent.

**Q: Why does typing feel slow sometimes?**  
A: Shouldn't with debouncing (500ms delay). Check system resources.

### Feature Questions

**Q: Can I customize keyboard shortcuts?**  
A: Not currently. Standard shortcuts follow VS Code conventions.

**Q: Can I change the editor theme?**  
A: Future feature. Currently uses VS Code Light theme.

**Q: Can I export configurations?**  
A: Yes, they're YAML files you can copy from config directory.

**Q: Can I import from other formats?**  
A: Not currently. YAML only.

**Q: Is there an API for automation?**  
A: Yes, backend REST API documented in API guide.

### Troubleshooting Questions

**Q: Why won't my configuration save?**  
A: Check file permissions, disk space, and backup directory exists.

**Q: Why do I see outdated validation results?**  
A: Cache may be stale. Edit config to invalidate cache, or wait 5 minutes.

**Q: Why is the editor slow?**  
A: Large configs (>10MB) or many entities (>100) can slow performance.

**Q: Why doesn't auto-fix work?**  
A: Not all errors are fixable. Check if fix badge appears on error.

**Q: Where are backups stored?**  
A: In `/backups/` directory with timestamp in filename.

---

## Related Documentation

- [UI Requirements](UI_REQUIREMENTS.md) - Feature specifications
- [UI Architecture](UI_ARCHITECTURE.md) - Technical architecture
- [Project Guide](CONFIGURATION_GUIDE.md) - YAML syntax guide
- [Developer Guide](DEVELOPER_GUIDE.md) - Development information
- [Testing Guide](TESTING_GUIDE.md) - Testing procedures

---

**Document Version**: 1.0  
**Last Updated**: December 14, 2025  
**For**: Shape Shifter Project Editor v0.1.0
