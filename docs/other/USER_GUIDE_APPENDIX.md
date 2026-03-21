# Shape Shifter Project Editor - Appendix

## Table of Contents

1. [System Requirements](#system-requirements)
5. [Keyboard Shortcuts](#keyboard-shortcuts)
6. [Tips & Best Practices](#tips--best-practices)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## System Requirements

### Browser Support

**Recommended:**
- Chrome 120+ (best performance)
- Edge 120+

**Supported:**
- Firefox 115+
- Safari 16+

**Not Supported:**
- Internet Explorer (any version)
- Browsers older than 2 years

## Keyboard Shortcuts

### Global Shortcuts

| Shortcut       | Action                 |
|----------------|------------------------|
| `Ctrl/Cmd + S` | Save project           |
| `Ctrl/Cmd + V` | Validate configuration |
| `Ctrl/Cmd + E` | Execute workflow       |
| `Ctrl/Cmd + O` | Open project           |
| `Ctrl/Cmd + N` | New project            |
| `Escape`       | Close dialog           |

### Editor Shortcuts

| Shortcut               | Action            |
|------------------------|-------------------|
| `Ctrl/Cmd + F`         | Find in file      |
| `Ctrl/Cmd + H`         | Find and replace  |
| `Ctrl/Cmd + Z`         | Undo              |
| `Ctrl/Cmd + Shift + Z` | Redo              |
| `Ctrl/Cmd + /`         | Toggle comment    |
| `Ctrl/Cmd + D`         | Duplicate line    |
| `Alt + Up/Down`        | Move line up/down |
| `Ctrl/Cmd + Space`     | Auto-complete     |

### Validation Panel Shortcuts

| Shortcut        | Action             |
|-----------------|--------------------|
| `Ctrl/Cmd + P`  | Preview fix        |
| `Ctrl/Cmd + A`  | Apply fix          |
| `/`             | Focus search box   |
| `Arrow Up/Down` | Navigate issues    |
| `Enter`         | Show issue details |

---

## Tips & Best Practices

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

## Troubleshooting

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
1. Check backend server is running (`curl http://localhost:8012/api/v1/health`)
2. Verify network connectivity
3. Check CORS configuration
4. Review backend logs
5. Try different browser

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

**Fix:** Remove column or add to data source

#### "Entity 'X' not defined"

**Cause:** Reference to undefined entity

**Fix:** Define missing entity or fix reference

### Getting Help

**In-App Help:**
1. Hover tooltips on buttons
2. Click error for details
3. Check validation messages

**Documentation:**
1. User Guide (main workflow)
2. This Appendix (technical reference)
3. Configuration Guide (YAML reference)
4. Developer Guide (advanced usage)

**Support:**
1. Check GitHub issues
2. Contact administrator
3. Submit bug report
4. Request feature

---

## FAQ

### General Questions

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

**Q: What's the difference between Sample and Complete data validation?**  
A: **Sample (Fast)**: Validates using preview data (first 1000 rows) for quick feedback. **Complete (Comprehensive)**: Runs full normalization pipeline and validates all data - slower but thorough.

**Q: Why validate if I'm not changing anything?**  
A: Data sources may change, or new validation rules may be added.

**Q: Can I skip validation?**  
A: Not recommended. Validation catches errors before processing fails.

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

**Q: Where are backups stored?**  
A: In `/backups/` directory with timestamp in filename.

---

## Related Documentation

- [User Guide](USER_GUIDE.md) - Main workflow documentation
- [Configuration Guide](CONFIGURATION_GUIDE.md) - Complete YAML reference
- [Architecture](ARCHITECTURE.md) - Technical architecture
- [Developer Guide](DEVELOPER_GUIDE.md) - Development information
- [Testing Guide](TESTING_GUIDE.md) - Testing procedures

---

**Document Version**: 1.0  
**Last Updated**: January 29, 2026  
**For**: Shape Shifter Project Editor v0.1.0
