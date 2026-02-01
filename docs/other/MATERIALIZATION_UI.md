# Materialization UI Behavior

## Overview

This document explains the expected behavior of the materialization feature in the entity editor UI.

## Button States

### Correct Behavior (After Fix)

- **Non-materialized entity**: Shows "Materialize" button (blue, database-arrow-down icon)
- **Materialized entity**: Shows "Unmaterialize" button (orange/warning, database-arrow-up icon)

### How It Works

1. When the entity dialog opens in edit mode, it fetches fresh entity data from the API
2. The complete entity object (including `materialized` metadata) is stored in `currentEntity` ref
3. Button visibility is determined by checking `currentEntity.materialized?.enabled`
4. After materialization/unmaterialization, the entity is reloaded and `currentEntity` is updated

### Previous Issue (Fixed)

Previously, the button checked the initial `entity` prop which became stale after the first load. The fix stores the fresh entity data in a dedicated `currentEntity` ref that gets updated after materialization operations.

## YAML Editor Behavior

### Expected Behavior (By Design)

The YAML editor in the entity dialog **intentionally excludes** the `materialized` section.

**Rationale:**
- The `materialized` section is **metadata**, not user-editable configuration
- It contains:
  - `enabled`: Auto-set by materialization action
  - `source_state`: Backup of original config (managed by system)
  - `materialized_at`: Timestamp (auto-generated)
  - `materialized_by`: User tracking (auto-populated)
  - `data_file`: Optional storage reference (managed by system)

- Users should **not manually edit** these fields
- The YAML view shows only what users can configure (type, columns, keys, etc.)
- This prevents accidental corruption of materialization metadata

### Viewing Complete YAML

To see the complete YAML including the `materialized` section:

1. **Option 1 - Project-level YAML tab**: View the entire project configuration in the main YAML editor
2. **Option 2 - Direct file access**: Open `projects/<project_name>.yml` in any text editor
3. **Option 3 - Entity list**: The entity list shows a "Materialized" chip badge for materialized entities

### Example

**What you see in entity editor YAML view:**
```yaml
name: cultural_group
type: fixed
public_id: cultural_group_id
keys: [KultGr]
columns: [system_id, KultGr, Cult_EN]
values:
  - [1, "-99", "-99"]
  - [2, Carolingians, Karolinger]
  # ... more rows
```

**What's actually in the project YAML file:**
```yaml
cultural_group:
  type: fixed
  public_id: cultural_group_id
  keys: [KultGr]
  columns: [system_id, KultGr, Cult_EN]
  materialized:  # ← Hidden from entity editor
    enabled: true
    source_state:
      data_source: arbodat_lookup
      query: select distinct KultGr, Cult_EN from Kulturgruppen;
    materialized_at: "2026-01-30T15:29:02.818590"
  values:
    - [1, "-99", "-99"]
    - [2, Carolingians, Karolinger]
    # ... more rows
```

## UI Indicators for Materialized State

### Entity List (EntityListCard.vue)

Materialized entities show a chip badge:
- **Icon**: `mdi-database-check`
- **Color**: Blue
- **Text**: "Materialized"
- **Tooltip**: "This entity has been materialized (frozen data)"

### Entity Editor (EntityFormDialog.vue)

**Edit mode only:**
- **Materialized entity**: "Unmaterialize" button visible
- **Non-materialized entity**: "Materialize" button visible (only for non-fixed types)
- **Fixed type (non-materialized)**: No button (already static data)

## Workflow

### Materializing an Entity

1. Open entity in edit mode
2. Click "Materialize" button
3. Configure materialization options (storage method, etc.)
4. Confirm materialization
5. Backend converts entity to fixed type with inline/external storage
6. Entity reloads automatically
7. Button changes to "Unmaterialize"
8. Entity list shows "Materialized" badge

### Unmaterializing an Entity

1. Open materialized entity in edit mode
2. Click "Unmaterialize" button
3. Review cascade warning if dependent entities exist
4. Confirm unmaterialization
5. Backend restores entity to original configuration from `source_state`
6. Entity reloads automatically
7. Button changes to "Materialize" (if not fixed type)
8. "Materialized" badge disappears from entity list

## Technical Notes

### State Management

- **Source of Truth**: YAML file on disk
- **Fresh Data**: Always fetched from API when dialog opens
- **currentEntity ref**: Stores complete entity including metadata
- **formData ref**: Stores only user-editable configuration
- **Sync**: After materialization operations, entity is reloaded to update both refs

### Why Not Show Materialized Section in YAML Editor?

1. **Separation of Concerns**: Configuration vs. metadata
2. **User Intent**: Users edit entity structure, system manages materialization state
3. **Error Prevention**: Prevents manual editing of computed/managed fields
4. **Consistency**: Ensures metadata is only modified through controlled operations
5. **Clarity**: Reduces confusion about what fields are user-editable

### Alternative: Read-Only Metadata Section

A future enhancement could add a read-only metadata panel in the entity editor to display (but not edit) the `materialized` section for transparency. This would require:
- Separate read-only panel below the YAML editor
- Clear visual indication that it's read-only
- Collapsible section to avoid clutter

## Troubleshooting

### Button Not Updating After Materialization

**Symptom**: Button still shows "Materialize" after successful materialization

**Cause**: Entity data not reloaded, or `currentEntity` ref not updated

**Solution**: Check that `handleMaterialized()` and `handleUnmaterialized()` functions:
1. Fetch fresh entity from API
2. Update `currentEntity.value = freshEntity`
3. Update `formData.value` and `yamlContent.value`

### Can't See Materialized Section

**Symptom**: YAML editor doesn't show materialized metadata

**Expected Behavior**: This is intentional - use project-level YAML view or direct file access

**Why**: Prevents accidental editing of system-managed metadata
