# Shape Shifter Configuration Editor - User Guide

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Working with Configurations](#3-working-with-configurations)
4. [Managing Entities](#4-managing-entities)
5. [Validation](#5-validation)
6. [Auto-Fix Features](#6-auto-fix-features)
7. [Quick Wins & Performance Features](#7-quick-wins--performance-features)
8. [Tips & Best Practices](#8-tips--best-practices)
9. [Troubleshooting](#9-troubleshooting)
10. [FAQ](#10-faq)

---

## 1. Introduction

### What is Shape Shifter?

Shape Shifter is a declarative data transformation framework that uses YAML configurations to harmonize diverse data sources into target schemas. The Configuration Editor provides a visual interface for creating and managing these transformation configurations.

### Who Should Use This Guide?

This guide is for:
- **Domain Data Managers** - Managing entity configurations
- **Data Engineers** - Creating complex transformations
- **Developers** - Integrating transformations into workflows

### Key Features

- **Visual Configuration Editor** - Monaco Editor for YAML editing
- **Entity Tree Navigation** - Browse entities and dependencies
- **Real-Time Validation** - Immediate feedback on errors
- **Auto-Fix Capabilities** - Intelligent error resolution
- **Data Preview** - See transformation results
- **Performance Optimizations** - Fast, responsive interface

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
│  Configuration Editor                      [Save] [Validate]│
├─────────────┬────────────────────────┬────────────────────┤
│             │                        │                    │
│  Entity     │   Monaco Editor        │  Validation        │
│  Tree       │   (YAML)               │  Panel             │
│             │                        │                    │
│  • entity_1 │  entities:             │  ✓ No errors       │
│  • entity_2 │    entity_1:           │                    │
│    - entity_3│      type: data       │  📋 Properties     │
│             │      columns: [...]    │                    │
│             │                        │                    │
└─────────────┴────────────────────────┴────────────────────┘
```

**Three Main Panels:**

1. **Left: Entity Tree** - Navigate entities and dependencies
2. **Center: Monaco Editor** - Edit YAML configuration
3. **Right: Validation/Properties** - View errors and entity details

### First Steps

1. **Open a Configuration**
   - Click "Open Configuration" in the toolbar
   - Select from available configurations
   - Configuration loads into editor

2. **Explore the Entity Tree**
   - Left panel shows all entities
   - Click entity to jump to its definition
   - Expand/collapse dependency trees

3. **Run Validation**
   - Click "Validate All" button
   - Review results in right panel
   - Fix any errors found

---

## 3. Working with Configurations

### Opening Configurations

**Method 1: Configuration Selector**
1. Click dropdown in toolbar
2. Select configuration name
3. Configuration loads automatically

**Method 2: Recent Files**
1. Recently opened configs appear at top
2. Click to reopen instantly
3. Access last 5 configurations quickly

### Creating New Configurations

1. Click "New Configuration"
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

### Saving Configurations

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

### Configuration Backups

Every save creates a timestamped backup:

**Location:** `/backups/`  
**Format:** `config_name.backup.YYYYMMDD_HHMMSS.yml`  
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

**Data Entity:**
```yaml
entity_name:
  type: data
  source: null  # Root entity
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

**Natural Keys:**
```yaml
entity_name:
  keys: [key1, key2]  # Unique identifier columns
```

**Surrogate IDs:**
```yaml
entity_name:
  surrogate_id: entity_name_id  # Generated integer ID
```

**Column Selection:**
```yaml
entity_name:
  columns: [col1, col2, col3]  # Columns to extract
```

**Dependencies:**
```yaml
entity_name:
  source: parent_entity  # Depends on parent_entity
  depends_on: [other_entity]  # Additional dependencies
```

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
- Configuration changed

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

**Problem:** Configuration references non-existent columns

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

#### Duplicate Natural Keys

**Problem:** Data has duplicate values for natural keys

**Example Error:**
```
Found 5 duplicate natural keys
Entity: sample_entity
Keys: name, code
```

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
1. Configuration automatically revalidated
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
- Configuration modified
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
- Configuration saved
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

## 8. Tips & Best Practices

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

### Configuration Best Practices

**Entity Design:**
- ✅ Use descriptive entity names
- ✅ Define natural keys carefully
- ✅ Document complex relationships
- ✅ Keep entity scope focused

**Foreign Keys:**
- ✅ Always specify constraints
- ✅ Use appropriate cardinality
- ✅ Test join results
- ✅ Handle null keys explicitly

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

## 9. Troubleshooting

### Common Issues

#### Editor Won't Load Configuration

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
- Large configuration files (> 10MB)
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

#### "Configuration not found"

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
2. Configuration reference
3. API documentation
4. Developer guide

**Support:**
1. Check GitHub issues
2. Contact administrator
3. Submit bug report
4. Request feature

---

## 10. FAQ

### General Questions

**Q: What browsers are supported?**  
A: Chrome 120+, Firefox 115+, Safari 16+, Edge 120+. Chrome recommended.

**Q: Can I use offline?**  
A: Editor works offline for loaded configs. Validation requires backend connection.

**Q: Where are configurations stored?**  
A: In the configured directory, typically `input/` or similar.

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
- [Configuration Guide](CONFIGURATION_GUIDE.md) - YAML syntax guide
- [Developer Guide](DEVELOPER_GUIDE.md) - Development information
- [Testing Guide](TESTING_GUIDE.md) - Testing procedures

---

**Document Version**: 1.0  
**Last Updated**: December 14, 2025  
**For**: Shape Shifter Configuration Editor v0.1.0
