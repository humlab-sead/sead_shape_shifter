# User Guide: Auto-Fix Features

## Overview

The Shape Shifter Configuration Editor includes intelligent auto-fix capabilities that can automatically resolve common configuration issues. This guide explains how to use these features effectively.

## What is Auto-Fix?

Auto-fix analyzes validation errors in your configuration and provides:
- **Automated solutions** for fixable issues
- **Guided recommendations** for complex problems
- **Safe application** with automatic backups
- **Preview capabilities** before applying changes

## Accessing Auto-Fix

### 1. Validate Your Configuration

First, run validation to identify issues:

1. Open your configuration in the editor
2. Click **"Validate All"** or **"Validate Entity"**
3. Review the validation results in the Validation Panel

### 2. View Fix Suggestions

When validation finds fixable issues:

1. Look for the **"Auto-Fix Available"** badge on error items
2. Errors with suggested fixes show a green **"Apply Fix"** button
3. Click on an error to see detailed fix information

### 3. Preview Fixes

Before applying any fix:

1. Click **"Preview Fix"** to see what will change
2. Review the changes in the preview dialog
3. Check the **"Before"** and **"After"** states
4. Verify the fix addresses the issue correctly

### 4. Apply Fixes

To apply a suggested fix:

1. Click **"Apply Fix"** on the error item
2. System automatically creates a backup
3. Fix is applied to your configuration
4. Editor updates with the corrected YAML
5. Success message confirms the change

## Common Fixable Issues

### Missing Columns

**Problem:** Configuration references columns that don't exist in your data

**Example Error:**
```
Column 'missing_column' not found in data
Entity: sample_entity
```

**Auto-Fix Action:**
- Removes the non-existent column from the configuration
- Updates the `columns` list
- Preserves all other settings

**When to Use:**
- Column was removed from data source
- Typo in column name (manual fix needed first)
- Configuration is outdated

### Invalid References

**Problem:** Configuration references entities that don't exist

**Example Error:**
```
Referenced entity 'old_entity' not found
Entity: sample_entity
Field: foreign_keys
```

**Auto-Fix Recommendation:**
- Provides guidance on fixing the reference
- Suggests checking entity names
- May require manual intervention

**When to Use:**
- Entity was renamed
- Entity was removed from configuration
- Reference path is incorrect

### Duplicate Natural Keys

**Problem:** Data contains duplicate values for natural key columns

**Example Error:**
```
Found 5 duplicate natural keys
Entity: sample_entity
Keys: name, code
```

**Auto-Fix Recommendation:**
- Provides guidance on resolving duplicates
- Suggests reviewing data or key definition
- Requires manual data cleaning

**When to Use:**
- Data quality issues need attention
- Key definition may need adjustment
- Business rules need clarification

## Fix Types Explained

### Automatic Fixes (Green Badge)

These fixes can be safely applied automatically:

- ✅ **Remove Column** - Removes non-existent column from config
- ✅ **Update Reference** - Updates simple entity references (coming soon)
- ✅ **Add Column** - Adds missing required columns (coming soon)

### Manual Fixes (Yellow Badge)

These issues require your judgment:

- ⚠️ **Unresolved Reference** - Check entity names and structure
- ⚠️ **Duplicate Keys** - Review data or change key definition
- ⚠️ **Type Mismatch** - Verify data types match expectations

### Complex Issues (Red Badge)

These need careful manual review:

- 🔴 **Circular Dependencies** - Restructure entity relationships
- 🔴 **Data Quality** - Clean source data before import
- 🔴 **Schema Conflicts** - Resolve structural inconsistencies

## Safety Features

### Automatic Backups

Every time you apply a fix:

1. **Backup Created** - Original saved to `/backups/` directory
2. **Timestamp Added** - Format: `config.backup.YYYYMMDD_HHMMSS.yml`
3. **Rollback Available** - Restore from backup if needed

**Example Backup:**
```
/backups/my_config.backup.20251214_143022.yml
```

### Preview Before Apply

Always preview fixes to understand:
- **What will change** - Exact modifications to your config
- **Why it's changing** - Reason for the fix
- **Impact** - How it affects your data processing
- **Warnings** - Any potential side effects

### Validation After Fix

After applying a fix:

1. Configuration is automatically revalidated
2. New validation results show if issue is resolved
3. Any remaining issues are displayed
4. You can apply additional fixes if needed

## Best Practices

### 1. Validate Regularly

Run validation:
- ✅ After editing configuration
- ✅ Before processing data
- ✅ When data sources change
- ✅ After applying fixes

### 2. Review Suggestions Carefully

Before applying any fix:
- ✅ Read the error message completely
- ✅ Understand why the issue occurred
- ✅ Preview the exact changes
- ✅ Consider downstream impacts

### 3. Test After Fixes

After applying fixes:
- ✅ Revalidate to confirm fix worked
- ✅ Test with sample data if possible
- ✅ Review generated output
- ✅ Keep backups for at least one cycle

### 4. Document Changes

Keep track of fixes:
- ✅ Note what was fixed and why
- ✅ Document any manual adjustments needed
- ✅ Update your configuration documentation
- ✅ Inform team members of changes

## Troubleshooting

### Fix Doesn't Resolve Issue

If applying a fix doesn't resolve the error:

1. **Check validation results** - New errors may have appeared
2. **Review recent changes** - May have introduced new issues
3. **Verify data source** - Data may have changed
4. **Check dependencies** - Related entities may have issues

### Fix Creates New Problems

If a fix causes new validation errors:

1. **Use backup to restore** - Revert to previous version
2. **Review fix preview** - Check if warnings were missed
3. **Contact support** - May be a bug in auto-fix logic
4. **Try manual fix** - Some issues need human judgment

### Can't Apply Fix

If the "Apply Fix" button doesn't work:

1. **Check permissions** - Ensure write access to config file
2. **Verify file isn't locked** - Close other editors
3. **Check disk space** - Ensure room for backups
4. **Review console** - Check for error messages

### Backup Not Created

If backup creation fails:

1. **Check backup directory** - May need to create `/backups/`
2. **Verify permissions** - Need write access to backups folder
3. **Check disk space** - Ensure room for backup files
4. **Review settings** - Backup location may be configured

## Keyboard Shortcuts

Speed up your workflow:

- `Ctrl/Cmd + V` - Validate configuration
- `Ctrl/Cmd + P` - Preview selected fix
- `Ctrl/Cmd + A` - Apply selected fix
- `Ctrl/Cmd + Z` - Undo last change (editor)
- `Escape` - Close preview/fix dialog

## Advanced Features

### Batch Fixes (Coming Soon)

Apply multiple fixes at once:

1. Select multiple errors with fixes
2. Click "Apply All Fixes"
3. Preview all changes together
4. Apply in single operation with one backup

### Custom Fix Rules (Future)

Define your own fix patterns:

1. Create custom fix rules
2. Apply to specific error types
3. Share rules with team
4. Version control fix rules

### Fix History (Future)

Track all applied fixes:

1. View history of fixes
2. See who applied what when
3. Rollback to specific point
4. Audit fix applications

## Getting Help

If you need assistance:

1. **Hover tooltips** - Information on each button
2. **Error details** - Click error for more info
3. **Documentation** - This guide and others
4. **Support** - Contact your administrator

## Example Workflows

### Workflow 1: Clean Up After Data Source Change

1. Open configuration
2. Click "Validate All"
3. Review errors for missing columns
4. Preview each fix
5. Apply fixes one by one
6. Revalidate to confirm
7. Test with sample data

### Workflow 2: Fix Multiple Issues

1. Run validation
2. Sort errors by severity
3. Apply automatic fixes first
4. Preview manual fixes
5. Apply manual fixes with care
6. Revalidate after each batch
7. Document changes made

### Workflow 3: Rollback After Bad Fix

1. Notice unexpected behavior
2. Stop data processing
3. Locate backup in `/backups/`
4. Restore from backup file
5. Review what went wrong
6. Apply correct fix
7. Test thoroughly

## FAQ

**Q: Are auto-fixes safe?**  
A: Yes! Every fix creates an automatic backup, and you can preview changes before applying.

**Q: Can I undo a fix?**  
A: Yes, restore from the automatic backup created before the fix.

**Q: Will fixes modify my data?**  
A: No, fixes only modify your configuration file, never your source data.

**Q: Can I apply multiple fixes at once?**  
A: Currently no, but batch fix application is planned for a future release.

**Q: What if I disagree with a fix suggestion?**  
A: You can skip any suggestion and fix the issue manually in the YAML editor.

**Q: How long are backups kept?**  
A: Backups are kept indefinitely. You may want to clean old backups periodically.

**Q: Can I disable auto-fix?**  
A: Yes, you can choose to never use auto-fix and fix all issues manually.

**Q: Does auto-fix work offline?**  
A: Yes, auto-fix is processed locally and doesn't require internet connectivity.

## Related Documentation

- [Validation Guide](VALIDATION_GUIDE.md) - Understanding validation results
- [Configuration Reference](CONFIGURATION_REFERENCE.md) - Config file syntax
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Quick Start Guide](QUICKSTART.md) - Getting started quickly

---

**Version:** 1.0  
**Last Updated:** December 14, 2025  
**For:** Shape Shifter Configuration Editor v0.1.0
