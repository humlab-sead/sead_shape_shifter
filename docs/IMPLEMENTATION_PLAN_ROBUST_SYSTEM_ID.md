# Implementation Plan: Robust system_id Handling for Fixed Value Entities

## Executive Summary

This document outlines the implementation plan for making `system_id` a stable, client-maintained identifier for fixed value entities. This change addresses FK relationship brittleness caused by server-generated sequential IDs that break when rows are added, removed, or reordered.

## Problem Statement

### Current Behavior (Brittle)
1. **YAML Storage**: Fixed entities store concrete `system_id` values in the 2D `values` array (e.g., `[1, null, ...]`)
2. **Frontend Display**: FixedValuesGrid displays `rowIndex + 1` instead of actual YAML values
3. **Disconnect**: User sees sequential 1-N display, but YAML may have different values
4. **Risk**: If rows are deleted from YAML manually, server-side `add_system_id()` regenerates sequential IDs, breaking FK relationships
5. **No Stability**: Adding/removing rows can change system_id values for other rows

### Required Behavior (Robust)
1. **Client-Maintained**: `system_id` is a concrete value stored and maintained by the client
2. **Stable Identity**: Survives add, remove, and reorder operations
3. **Auto-Increment**: New rows get `max(existing system_id) + 1`, starting at 1
4. **Unique**: Each `system_id` value is unique within the entity
5. **No Renumbering**: Deleting row 2 doesn't change rows 1, 3, 4, etc.
6. **Server As-Is**: Server accepts `system_id` values as provided, only adds if missing
7. **FK Safe**: FK relationships remain valid across edit operations

## Current Implementation Analysis

### Core Layer (`src/`)

**File**: `src/loaders/fixed_loader.py`
```python
async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame:
    data = pd.DataFrame(table_cfg.safe_values, columns=table_cfg.columns)
    
    # Current: Only adds if missing
    if table_cfg.system_id and table_cfg.system_id not in data.columns:
        data = add_system_id(data, table_cfg.system_id)
    
    return data
```

**Issue**: If `system_id` is in columns but values are missing/None, it's not validated.

**File**: `src/transforms/utility.py`
```python
def add_system_id(target: pd.DataFrame, id_name: str = "system_id") -> pd.DataFrame:
    """Add an auto-incrementing system_id column starting at 1."""
    target = target.reset_index(drop=True).copy()
    target[id_name] = range(1, len(target) + 1)  # Always regenerates!
    cols: list[str] = [id_name] + [col for col in target.columns if col != id_name]
    target = target[cols]
    return target
```

**Issue**: Always overwrites with sequential values, breaking stability.

### Backend Layer (`backend/app/`)

**File**: `backend/app/models/entity.py`
- `Entity.values: list[list[Any]] | None` - stores 2D array with system_id as first element per row
- No validation for `system_id` uniqueness or presence in fixed entities

### Frontend Layer (`frontend/src/`)

**File**: `frontend/src/components/entities/FixedValuesGrid.vue`

```typescript
// Current: Displays rowIndex + 1, ignoring actual values
const rowData = computed(() => {
  return props.modelValue.map((row, rowIndex) => {
    const rowObj: any = { id: rowIndex }
    row.forEach((value, colIndex) => {
      const columnName = props.columns[colIndex]
      if (columnName === 'system_id') {
        rowObj[`col_${colIndex}`] = rowIndex + 1  // ⚠️ Ignores actual value!
      } else {
        rowObj[`col_${colIndex}`] = value
      }
    })
    return rowObj
  })
})

function addRow() {
  let rowCount = 0
  gridApi.value.forEachNode(() => rowCount++)
  
  const newRow: any = { id: Date.now() }
  for (let i = 0; i < props.columns.length; i++) {
    const columnName = props.columns[i]
    if (columnName === 'system_id') {
      newRow[`col_${i}`] = parseInt(String(rowCount + 1), 10)  // ⚠️ Uses row count
    } else {
      newRow[`col_${i}`] = null
    }
  }
}
```

**Issues**:
1. Displays `rowIndex + 1` instead of actual `system_id` value from YAML
2. New rows use `rowCount + 1` instead of `max(system_id) + 1`
3. Doesn't preserve actual values when rendering
4. No validation for uniqueness

## Implementation Plan

### Phase 1: Core Layer Changes (Week 1)

#### 1.1 Update `add_system_id` to preserve existing values

**File**: `src/transforms/utility.py`

```python
def add_system_id(target: pd.DataFrame, id_name: str = "system_id") -> pd.DataFrame:
    """Add or fill system_id column with auto-incrementing values.
    
    Behavior:
    - If column missing: Add with sequential values starting at 1
    - If column exists with values: Preserve existing values, fill nulls with max+1
    - If column exists but all nulls: Fill with sequential values starting at 1
    
    Args:
        target: DataFrame to add/fill system_id
        id_name: Column name for the system ID (default: "system_id")
    
    Returns:
        DataFrame with system_id column added/filled
    """
    target = target.reset_index(drop=True).copy()
    
    if id_name not in target.columns:
        # Column missing: Add with sequential values
        target[id_name] = range(1, len(target) + 1)
    else:
        # Column exists: Preserve non-null values, fill nulls
        if target[id_name].notna().any():
            # Has some values - preserve them, fill nulls with max+1
            max_id = target[id_name].max()
            null_count = target[id_name].isna().sum()
            if null_count > 0:
                # Fill nulls with sequential values starting at max+1
                null_indices = target[id_name].isna()
                target.loc[null_indices, id_name] = range(
                    int(max_id) + 1, 
                    int(max_id) + 1 + null_count
                )
        else:
            # All nulls: Fill with sequential values starting at 1
            target[id_name] = range(1, len(target) + 1)
    
    # Ensure integer type
    target[id_name] = target[id_name].astype(int)
    
    # Put id_name as the first column
    cols: list[str] = [id_name] + [col for col in target.columns if col != id_name]
    target = target[cols]
    
    return target
```

**Benefits**:
- Preserves existing `system_id` values (no regeneration)
- Fills missing values intelligently (max+1)
- Maintains backward compatibility for entities without system_id column

#### 1.2 Add validation for fixed entity system_id

**File**: `src/specifications/entity.py` (create new specification)

```python
from typing import Any
import pandas as pd
from src.specifications.base import ProjectSpecification

class FixedEntitySystemIdSpecification(ProjectSpecification):
    """Validate system_id for fixed entities."""
    
    def is_satisfied_by(self, entity_name: str | None = None) -> bool:
        """Check if fixed entity has valid system_id values."""
        if entity_name is None:
            return all(
                self._validate_entity(name, config)
                for name, config in self.entities_cfg.items()
                if config.get("type") == "fixed"
            )
        
        entity_config = self.entities_cfg.get(entity_name, {})
        return self._validate_entity(entity_name, entity_config)
    
    def _validate_entity(self, entity_name: str, entity_config: dict[str, Any]) -> bool:
        """Validate single entity."""
        if entity_config.get("type") != "fixed":
            return True  # Only validate fixed entities
        
        columns = entity_config.get("columns", [])
        values = entity_config.get("values", [])
        
        # system_id must be in columns
        if "system_id" not in columns:
            self.report.append(
                f"Fixed entity '{entity_name}' must include 'system_id' in columns"
            )
            return False
        
        # system_id must be first column
        if columns[0] != "system_id":
            self.report.append(
                f"Fixed entity '{entity_name}': 'system_id' must be the first column"
            )
            return False
        
        # Validate system_id values
        if not values:
            return True  # Empty entity is valid
        
        system_id_index = 0  # We know it's first column
        system_ids = [row[system_id_index] for row in values if len(row) > system_id_index]
        
        # All system_id values must be integers >= 1
        for i, sid in enumerate(system_ids):
            if sid is None:
                self.report.append(
                    f"Fixed entity '{entity_name}', row {i}: system_id cannot be null"
                )
                return False
            if not isinstance(sid, int) or sid < 1:
                self.report.append(
                    f"Fixed entity '{entity_name}', row {i}: system_id must be integer >= 1, got {sid}"
                )
                return False
        
        # system_id values must be unique
        if len(system_ids) != len(set(system_ids)):
            duplicates = [sid for sid in system_ids if system_ids.count(sid) > 1]
            self.report.append(
                f"Fixed entity '{entity_name}': Duplicate system_id values: {set(duplicates)}"
            )
            return False
        
        return True
    
    def get_report(self) -> str:
        """Get validation report."""
        return "\n".join(self.report) if self.report else "All fixed entities have valid system_id values"
```

**Integration**: Add to `CompositeProjectSpecification` in `src/specifications/project.py`

```python
class CompositeProjectSpecification(ProjectSpecification):
    def __init__(self, project: dict[str, Any]):
        super().__init__(project)
        self.specifications: list[ProjectSpecification] = [
            # ... existing specs ...
            FixedEntitySystemIdSpecification(project),
        ]
```

#### 1.3 Update FixedLoader validation

**File**: `src/loaders/fixed_loader.py`

```python
async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame:
    """Create a fixed data entity based on configuration."""
    
    self.validate(entity_name, table_cfg)
    
    values: list[list[Any]] = table_cfg.safe_values
    columns: list[str] = table_cfg.columns
    
    if len(columns) == 0 and len(values) == 0:
        logger.warning(f"Fixed data entity '{entity_name}' has no columns or values defined")
        return pd.DataFrame()
    
    data = pd.DataFrame(table_cfg.safe_values, columns=table_cfg.columns)
    
    # Validate system_id presence and values
    if table_cfg.system_id:
        if table_cfg.system_id not in data.columns:
            raise ValueError(
                f"Fixed entity '{entity_name}': system_id column '{table_cfg.system_id}' "
                f"must be present in columns list"
            )
        
        # Validate all system_id values are present (no nulls)
        if data[table_cfg.system_id].isna().any():
            null_count = data[table_cfg.system_id].isna().sum()
            raise ValueError(
                f"Fixed entity '{entity_name}': {null_count} rows have missing system_id values. "
                f"For fixed entities, system_id must be explicitly provided for all rows."
            )
        
        # Validate uniqueness
        duplicates = data[table_cfg.system_id].duplicated()
        if duplicates.any():
            dup_values = data.loc[duplicates, table_cfg.system_id].unique()
            raise ValueError(
                f"Fixed entity '{entity_name}': Duplicate system_id values found: {dup_values.tolist()}"
            )
    
    return data
```

### Phase 2: Backend API Changes (Week 2)

#### 2.1 Add validation endpoint

**File**: `backend/app/services/validation_service.py`

Add new validation method:

```python
def _validate_fixed_entity_system_ids(
    self, entity_name: str, entity_config: dict[str, Any]
) -> list[ValidationError]:
    """Validate system_id for fixed entities."""
    errors = []
    
    if entity_config.get("type") != "fixed":
        return errors
    
    columns = entity_config.get("columns", [])
    values = entity_config.get("values", [])
    
    # Validate system_id in columns
    if "system_id" not in columns:
        errors.append(
            ValidationError(
                entity=entity_name,
                field="columns",
                severity="error",
                category="identity",
                message="Fixed entity must include 'system_id' in columns",
                code="SYSTEM_ID_MISSING",
            )
        )
        return errors
    
    # Validate system_id is first column
    if columns[0] != "system_id":
        errors.append(
            ValidationError(
                entity=entity_name,
                field="columns",
                severity="warning",
                category="identity",
                message="system_id should be the first column for consistency",
                code="SYSTEM_ID_NOT_FIRST",
                suggestion="Move 'system_id' to the first position in columns list",
            )
        )
    
    # Validate system_id values
    if values:
        system_id_index = columns.index("system_id")
        system_ids = [
            row[system_id_index] for row in values 
            if len(row) > system_id_index
        ]
        
        # Check for nulls
        null_indices = [i for i, sid in enumerate(system_ids) if sid is None]
        if null_indices:
            errors.append(
                ValidationError(
                    entity=entity_name,
                    field="values",
                    severity="error",
                    category="identity",
                    message=f"system_id cannot be null (found {len(null_indices)} null values)",
                    code="SYSTEM_ID_NULL",
                    suggestion="Provide explicit integer system_id values for all rows",
                )
            )
        
        # Check for duplicates
        seen = set()
        duplicates = []
        for sid in system_ids:
            if sid is not None:
                if sid in seen:
                    duplicates.append(sid)
                seen.add(sid)
        
        if duplicates:
            errors.append(
                ValidationError(
                    entity=entity_name,
                    field="values",
                    severity="error",
                    category="identity",
                    message=f"Duplicate system_id values: {duplicates}",
                    code="SYSTEM_ID_DUPLICATE",
                    suggestion="Ensure each row has a unique system_id value",
                )
            )
        
        # Check for invalid values (< 1)
        invalid = [sid for sid in system_ids if sid is not None and (not isinstance(sid, int) or sid < 1)]
        if invalid:
            errors.append(
                ValidationError(
                    entity=entity_name,
                    field="values",
                    severity="error",
                    category="identity",
                    message=f"system_id must be integer >= 1, found invalid values: {invalid}",
                    code="SYSTEM_ID_INVALID",
                )
            )
    
    return errors
```

Integrate into `validate_entity()`:

```python
async def validate_entity(
    self, project_name: str, entity_name: str
) -> list[ValidationError]:
    """Validate single entity."""
    # ... existing validation ...
    
    # Add system_id validation for fixed entities
    errors.extend(self._validate_fixed_entity_system_ids(entity_name, entity_config))
    
    return errors
```

#### 2.2 Add auto-fix suggestion

**File**: `backend/app/services/auto_fix_service.py`

```python
def _generate_system_id_fixes(
    self, entity_name: str, entity_config: dict[str, Any], errors: list[ValidationError]
) -> list[AutoFixSuggestion]:
    """Generate auto-fix suggestions for system_id issues."""
    suggestions = []
    
    if entity_config.get("type") != "fixed":
        return suggestions
    
    # Check for missing system_id column
    system_id_missing = any(
        e.code == "SYSTEM_ID_MISSING" and e.entity == entity_name 
        for e in errors
    )
    
    if system_id_missing:
        columns = entity_config.get("columns", [])
        values = entity_config.get("values", [])
        
        # Suggest adding system_id as first column
        new_columns = ["system_id"] + columns
        new_values = [
            [i + 1] + row for i, row in enumerate(values)
        ]
        
        suggestions.append(
            AutoFixSuggestion(
                type="add_system_id_column",
                title="Add system_id column",
                description=f"Add 'system_id' as first column with values 1 to {len(values)}",
                before={"columns": columns, "values": values},
                after={"columns": new_columns, "values": new_values},
                confidence="high",
            )
        )
    
    # Check for null system_id values
    system_id_null = any(
        e.code == "SYSTEM_ID_NULL" and e.entity == entity_name 
        for e in errors
    )
    
    if system_id_null:
        columns = entity_config.get("columns", [])
        values = entity_config.get("values", [])
        system_id_index = columns.index("system_id")
        
        # Fill nulls with max+1
        existing_ids = {
            row[system_id_index] for row in values 
            if len(row) > system_id_index and row[system_id_index] is not None
        }
        next_id = max(existing_ids) + 1 if existing_ids else 1
        
        new_values = []
        for row in values:
            new_row = list(row)
            if len(new_row) > system_id_index and new_row[system_id_index] is None:
                new_row[system_id_index] = next_id
                next_id += 1
            new_values.append(new_row)
        
        suggestions.append(
            AutoFixSuggestion(
                type="fill_system_id_nulls",
                title="Fill missing system_id values",
                description="Assign unique system_id values to rows with null system_id",
                before={"values": values},
                after={"values": new_values},
                confidence="high",
            )
        )
    
    return suggestions
```

### Phase 3: Frontend Changes (Week 3)

#### 3.1 Update FixedValuesGrid to use actual values

**File**: `frontend/src/components/entities/FixedValuesGrid.vue`

```typescript
// Convert 2D array to row objects for ag-grid
// Use actual system_id values from data, not rowIndex
const rowData = computed(() => {
  if (!props.modelValue || props.modelValue.length === 0) {
    return []
  }

  return props.modelValue.map((row, rowIndex) => {
    const rowObj: any = { id: rowIndex }
    row.forEach((value, colIndex) => {
      // Use actual value for all columns including system_id
      rowObj[`col_${colIndex}`] = value
    })
    return rowObj
  })
})

// Helper: Get maximum system_id from current data
function getMaxSystemId(): number {
  if (!gridApi.value || !props.columns) return 0
  
  const systemIdIndex = props.columns.findIndex(col => col === 'system_id')
  if (systemIdIndex === -1) return 0
  
  let maxId = 0
  gridApi.value.forEachNode((node) => {
    const systemId = node.data[`col_${systemIdIndex}`]
    if (typeof systemId === 'number' && systemId > maxId) {
      maxId = systemId
    }
  })
  
  return maxId
}

function addRow() {
  if (!gridApi.value) return

  // Calculate next system_id as max(existing) + 1
  const nextSystemId = getMaxSystemId() + 1

  // Create a new row with null values for all columns
  const newRow: any = { id: Date.now() }
  for (let i = 0; i < props.columns.length; i++) {
    const columnName = props.columns[i]
    if (columnName === 'system_id') {
      // Use next sequential system_id (max + 1)
      newRow[`col_${i}`] = nextSystemId
    } else {
      newRow[`col_${i}`] = null
    }
  }

  gridApi.value.applyTransaction({ add: [newRow] })

  // Update model
  const allRows = getAllRows()
  emit('update:modelValue', allRows)
}

function deleteSelectedRows() {
  if (!gridApi.value) return

  const selectedRows = gridApi.value.getSelectedRows()
  if (selectedRows.length === 0) return

  // Just remove selected rows - don't renumber system_id
  gridApi.value.applyTransaction({ remove: selectedRows })

  // Update model - system_id values remain unchanged
  const allRows = getAllRows()
  emit('update:modelValue', allRows)

  hasSelection.value = false
}

// Prevent system_id editing
const columnDefs = computed<ColDef[]>(() => {
  if (!props.columns || props.columns.length === 0) {
    return []
  }

  return [
    {
      headerName: '',
      checkboxSelection: true,
      headerCheckboxSelection: true,
      width: 50,
      minWidth: 50,
      maxWidth: 50,
      flex: 0,
      editable: false,
      sortable: false,
      filter: false,
      resizable: false,
    },
    ...props.columns.map((col, index) => {
      const isSystemId = col === 'system_id'
      const isPublicId = col === props.publicId
      
      return {
        field: `col_${index}`,
        headerName: col,
        // system_id is read-only, others are editable
        editable: !isSystemId,  // ✅ Already prevents editing
        sortable: true,
        filter: true,
        resizable: true,
        minWidth: 100,
        flex: 1,
        // Ensure system_id is always an integer
        valueParser: isSystemId ? (params: any) => {
          const val = params.newValue
          return val !== null && val !== undefined ? parseInt(String(val), 10) : val
        } : undefined,
        // Apply special styling
        cellClass: isSystemId ? 'system-id-column' : (isPublicId ? 'public-id-column' : ''),
        headerClass: isSystemId ? 'system-id-header' : (isPublicId ? 'public-id-header' : ''),
      }
    }),
  ]
})
```

#### 3.2 Update EntityFormDialog validation

**File**: `frontend/src/components/entities/EntityFormDialog.vue`

Add validation for fixed entity system_id:

```typescript
const validateFixedEntity = computed(() => {
  if (formData.value.type !== 'fixed') return null
  
  const errors: string[] = []
  
  // Validate system_id in columns
  if (!formData.value.columns.includes('system_id')) {
    errors.push("Fixed entity must include 'system_id' in columns")
  }
  
  // Validate system_id is first column
  if (formData.value.columns[0] !== 'system_id') {
    errors.push("'system_id' should be the first column")
  }
  
  // Validate system_id values in data
  if (formData.value.values && formData.value.values.length > 0) {
    const systemIdIndex = formData.value.columns.indexOf('system_id')
    if (systemIdIndex !== -1) {
      const systemIds = formData.value.values.map((row: any[]) => row[systemIdIndex])
      
      // Check for nulls
      const nullCount = systemIds.filter((id: any) => id === null || id === undefined).length
      if (nullCount > 0) {
        errors.push(`${nullCount} rows have missing system_id values`)
      }
      
      // Check for duplicates
      const seen = new Set()
      const duplicates = new Set()
      systemIds.forEach((id: any) => {
        if (id !== null && id !== undefined) {
          if (seen.has(id)) {
            duplicates.add(id)
          }
          seen.add(id)
        }
      })
      if (duplicates.size > 0) {
        errors.push(`Duplicate system_id values: ${Array.from(duplicates).join(', ')}`)
      }
    }
  }
  
  return errors.length > 0 ? errors : null
})

// Show validation errors in UI
const fixedEntityErrors = computed(() => validateFixedEntity.value)
```

### Phase 4: Documentation Updates (Week 4)

#### 4.1 Update CONFIGURATION_GUIDE.md

Add section on system_id for fixed entities:

```markdown
### Fixed Entity Identity Rules

Fixed value entities must follow strict identity rules to ensure FK relationship stability:

1. **system_id Column**
   - Must be present in `columns` list
   - Should be the first column
   - Contains unique integer values >= 1
   - Values are client-maintained and stable

2. **Adding Rows**
   - New `system_id` = `max(existing system_id) + 1`
   - First row starts at 1

3. **Removing Rows**
   - Other rows keep their `system_id` values
   - No renumbering occurs

4. **Reordering Rows**
   - `system_id` values don't change
   - Display order doesn't affect identity

**Example**:
```yaml
contact_type:
  type: fixed
  public_id: contact_type_id
  keys: [arbodat_code]
  columns: [system_id, contact_type_id, contact_type, description, arbodat_code]
  values:
    - [1, null, Archaeologist, Description, ArchBear]
    - [2, null, Botanist, Description, BotBear]
    - [3, null, Author, Description, Aut]
```

**Adding a row**:
```yaml
  values:
    - [1, null, Archaeologist, Description, ArchBear]
    - [2, null, Botanist, Description, BotBear]
    - [3, null, Author, Description, Aut]
    - [4, null, NewType, Description, NewCode]  # max(1,2,3) + 1 = 4
```

**Removing row 2**:
```yaml
  values:
    - [1, null, Archaeologist, Description, ArchBear]
    # Row 2 deleted - other system_ids remain unchanged
    - [3, null, Author, Description, Aut]
    - [4, null, NewType, Description, NewCode]
```
```

#### 4.2 Update USER_GUIDE.md

Add section on editing fixed entities:

```markdown
## Editing Fixed Value Entities

### system_id Column

The `system_id` column is a **stable identifier** for each row in a fixed entity. It has special behavior:

- **Read-only**: Cannot be edited in the UI
- **Auto-assigned**: New rows automatically get the next available number
- **Stable**: Survives add, remove, and reorder operations
- **Unique**: Each row has a different system_id

### Adding Rows

1. Click "Add Row" button
2. New row appears with `system_id` = highest existing + 1
3. Fill in other column values
4. system_id is automatically assigned and cannot be changed

### Removing Rows

1. Select rows to delete (checkbox)
2. Click "Delete Selected"
3. Other rows keep their original system_id values
4. No renumbering occurs

**Example**:
- Original: rows with system_id [1, 2, 3, 4, 5]
- Delete row 2 and 4
- Result: rows with system_id [1, 3, 5]
- Note: system_id values don't change for remaining rows

### Why is system_id Important?

system_id is used as the **target for foreign key relationships**. If system_id values changed when rows were deleted or reordered, it would break relationships with other entities.

**Example**:
- Entity A has row with system_id = 3
- Entity B has row with foreign key pointing to system_id = 3
- If you delete Entity A row 2, Entity A row 3 keeps system_id = 3
- Entity B's foreign key still works correctly
```

### Phase 5: Migration Plan (Week 4-5)

#### 5.1 Existing Project Migration

For existing projects with fixed entities that may not have explicit system_id values:

**Migration Script**: `scripts/migrate_fixed_entity_system_ids.py`

```python
"""
Migrate existing fixed entities to have explicit system_id values.

This script:
1. Scans all projects for fixed entities
2. Checks if system_id is in columns and values
3. If missing: adds system_id as first column with sequential values
4. If present but has nulls: fills nulls with max+1
5. Creates backup before modifying
6. Validates after modification
"""

import argparse
import shutil
from pathlib import Path
import yaml
from loguru import logger

def migrate_project(project_path: Path, dry_run: bool = True) -> dict:
    """Migrate single project."""
    results = {
        "project": project_path.name,
        "entities_fixed": [],
        "entities_skipped": [],
        "errors": [],
    }
    
    # Load project
    with open(project_path, 'r') as f:
        project = yaml.safe_load(f)
    
    entities = project.get("entities", {})
    modified = False
    
    for entity_name, entity_config in entities.items():
        if entity_config.get("type") != "fixed":
            continue
        
        columns = entity_config.get("columns", [])
        values = entity_config.get("values", [])
        
        # Check if system_id already present and valid
        if "system_id" in columns and values:
            system_id_index = columns.index("system_id")
            system_ids = [row[system_id_index] for row in values if len(row) > system_id_index]
            
            # Check if all have values
            if all(sid is not None for sid in system_ids):
                results["entities_skipped"].append(entity_name)
                continue
        
        # Need to add or fix system_id
        logger.info(f"Migrating entity '{entity_name}' in project '{project_path.name}'")
        
        if "system_id" not in columns:
            # Add system_id as first column
            new_columns = ["system_id"] + columns
            new_values = [[i + 1] + row for i, row in enumerate(values)]
            
            entity_config["columns"] = new_columns
            entity_config["values"] = new_values
            modified = True
            results["entities_fixed"].append(entity_name)
        else:
            # Fill nulls
            system_id_index = columns.index("system_id")
            existing_ids = {row[system_id_index] for row in values if len(row) > system_id_index and row[system_id_index] is not None}
            next_id = max(existing_ids) + 1 if existing_ids else 1
            
            new_values = []
            for row in values:
                new_row = list(row)
                if len(new_row) > system_id_index and new_row[system_id_index] is None:
                    new_row[system_id_index] = next_id
                    next_id += 1
                new_values.append(new_row)
            
            entity_config["values"] = new_values
            modified = True
            results["entities_fixed"].append(entity_name)
    
    # Save if modified
    if modified and not dry_run:
        # Backup original
        backup_path = project_path.with_suffix('.yml.backup')
        shutil.copy2(project_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        
        # Save modified
        with open(project_path, 'w') as f:
            yaml.dump(project, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved modified project: {project_path}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Migrate fixed entity system_ids")
    parser.add_argument("--projects-dir", type=Path, default=Path("data/projects"),
                       help="Projects directory")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without modifying files")
    
    args = parser.parse_args()
    
    # Find all project files
    project_files = list(args.projects_dir.glob("*/shapeshifter.yml"))
    logger.info(f"Found {len(project_files)} projects")
    
    all_results = []
    for project_file in project_files:
        try:
            results = migrate_project(project_file, dry_run=args.dry_run)
            all_results.append(results)
        except Exception as e:
            logger.error(f"Error migrating {project_file}: {e}")
    
    # Print summary
    print("\n" + "="*80)
    print("MIGRATION SUMMARY")
    print("="*80)
    
    total_fixed = sum(len(r["entities_fixed"]) for r in all_results)
    total_skipped = sum(len(r["entities_skipped"]) for r in all_results)
    
    print(f"Projects processed: {len(all_results)}")
    print(f"Entities fixed: {total_fixed}")
    print(f"Entities skipped (already valid): {total_skipped}")
    
    if args.dry_run:
        print("\n⚠️  DRY RUN - No files were modified")
        print("Run without --dry-run to apply changes")
    else:
        print("\n✅ Migration complete")
        print("Backups created with .backup extension")

if __name__ == "__main__":
    main()
```

## Testing Plan

### Unit Tests

#### Core Tests (`tests/transforms/test_utility.py`)

```python
class TestAddSystemIdRobust:
    """Test add_system_id with preservation behavior."""
    
    def test_add_system_id_preserves_existing_values(self):
        """Test that existing system_id values are preserved."""
        df = pd.DataFrame({
            "name": ["A", "B", "C"],
            "system_id": [10, 20, 30]
        })
        
        result = add_system_id(df, "system_id")
        
        assert result["system_id"].tolist() == [10, 20, 30]
    
    def test_add_system_id_fills_nulls_with_max_plus_one(self):
        """Test that null system_id values are filled with max+1."""
        df = pd.DataFrame({
            "name": ["A", "B", "C", "D"],
            "system_id": [1, None, 3, None]
        })
        
        result = add_system_id(df, "system_id")
        
        # Nulls should be filled with 4, 5
        assert result["system_id"].tolist() == [1, 4, 3, 5]
    
    def test_add_system_id_all_nulls_generates_sequential(self):
        """Test that all-null system_id generates 1, 2, 3..."""
        df = pd.DataFrame({
            "name": ["A", "B", "C"],
            "system_id": [None, None, None]
        })
        
        result = add_system_id(df, "system_id")
        
        assert result["system_id"].tolist() == [1, 2, 3]
    
    def test_add_system_id_missing_column_generates_sequential(self):
        """Test that missing system_id column generates 1, 2, 3..."""
        df = pd.DataFrame({"name": ["A", "B", "C"]})
        
        result = add_system_id(df, "system_id")
        
        assert result["system_id"].tolist() == [1, 2, 3]
        assert result.columns[0] == "system_id"
```

#### Backend Tests (`backend/tests/services/test_validation_service.py`)

```python
class TestFixedEntitySystemIdValidation:
    """Test system_id validation for fixed entities."""
    
    @pytest.mark.asyncio
    async def test_validates_system_id_presence(self):
        """Test that missing system_id is detected."""
        entity_config = {
            "type": "fixed",
            "columns": ["name", "value"],
            "values": [["A", 1], ["B", 2]],
        }
        
        errors = await validation_service.validate_entity("test_project", "test_entity")
        
        assert any(e.code == "SYSTEM_ID_MISSING" for e in errors)
    
    @pytest.mark.asyncio
    async def test_validates_system_id_uniqueness(self):
        """Test that duplicate system_id values are detected."""
        entity_config = {
            "type": "fixed",
            "columns": ["system_id", "name"],
            "values": [[1, "A"], [1, "B"], [2, "C"]],
        }
        
        errors = await validation_service.validate_entity("test_project", "test_entity")
        
        assert any(e.code == "SYSTEM_ID_DUPLICATE" for e in errors)
    
    @pytest.mark.asyncio
    async def test_validates_system_id_not_null(self):
        """Test that null system_id values are detected."""
        entity_config = {
            "type": "fixed",
            "columns": ["system_id", "name"],
            "values": [[1, "A"], [None, "B"], [3, "C"]],
        }
        
        errors = await validation_service.validate_entity("test_project", "test_entity")
        
        assert any(e.code == "SYSTEM_ID_NULL" for e in errors)
```

#### Frontend Tests (`frontend/tests/unit/components/FixedValuesGrid.spec.ts`)

```typescript
describe('FixedValuesGrid', () => {
  it('displays actual system_id values from data', () => {
    const wrapper = mount(FixedValuesGrid, {
      props: {
        modelValue: [
          [5, null, 'Item A'],
          [10, null, 'Item B'],
          [15, null, 'Item C'],
        ],
        columns: ['system_id', 'public_id', 'name'],
      },
    })
    
    // Should display 5, 10, 15 (not 1, 2, 3)
    const rows = wrapper.findAll('.ag-row')
    expect(rows[0].text()).toContain('5')
    expect(rows[1].text()).toContain('10')
    expect(rows[2].text()).toContain('15')
  })
  
  it('assigns next system_id when adding row', async () => {
    const wrapper = mount(FixedValuesGrid, {
      props: {
        modelValue: [
          [1, null, 'Item A'],
          [5, null, 'Item B'],
          [8, null, 'Item C'],
        ],
        columns: ['system_id', 'public_id', 'name'],
      },
    })
    
    await wrapper.find('[data-test="add-row"]').trigger('click')
    
    // New row should have system_id = 9 (max(1,5,8) + 1)
    const emitted = wrapper.emitted('update:modelValue')
    const newData = emitted[0][0]
    expect(newData[3][0]).toBe(9)
  })
  
  it('preserves system_id when deleting row', async () => {
    const wrapper = mount(FixedValuesGrid, {
      props: {
        modelValue: [
          [1, null, 'Item A'],
          [2, null, 'Item B'],
          [3, null, 'Item C'],
        ],
        columns: ['system_id', 'public_id', 'name'],
      },
    })
    
    // Select and delete row 2
    await wrapper.find('[data-test="checkbox-1"]').trigger('click')
    await wrapper.find('[data-test="delete-selected"]').trigger('click')
    
    // Remaining rows should have system_id [1, 3] (not renumbered)
    const emitted = wrapper.emitted('update:modelValue')
    const newData = emitted[0][0]
    expect(newData.length).toBe(2)
    expect(newData[0][0]).toBe(1)
    expect(newData[1][0]).toBe(3)  // Not renumbered to 2!
  })
  
  it('prevents editing system_id column', () => {
    const wrapper = mount(FixedValuesGrid, {
      props: {
        modelValue: [[1, null, 'Item A']],
        columns: ['system_id', 'public_id', 'name'],
      },
    })
    
    const systemIdColumn = wrapper.find('[col-id="col_0"]')
    expect(systemIdColumn.classes()).toContain('system-id-column')
    expect(systemIdColumn.attributes('editable')).toBe('false')
  })
})
```

### Integration Tests

#### End-to-End Test (`frontend/tests/e2e/fixed-entity-editing.spec.ts`)

```typescript
test('fixed entity system_id stability', async ({ page }) => {
  // Create fixed entity
  await page.goto('/projects/test-project')
  await page.click('[data-test="add-entity"]')
  await page.fill('[data-test="entity-name"]', 'contact_type')
  await page.selectOption('[data-test="entity-type"]', 'fixed')
  
  // Add system_id and columns
  await page.fill('[data-test="columns"]', 'system_id,contact_type_id,name')
  
  // Add 3 rows
  await page.click('[data-test="add-row"]')  // system_id = 1
  await page.fill('[data-test="row-0-col-2"]', 'Type A')
  
  await page.click('[data-test="add-row"]')  // system_id = 2
  await page.fill('[data-test="row-1-col-2"]', 'Type B')
  
  await page.click('[data-test="add-row"]')  // system_id = 3
  await page.fill('[data-test="row-2-col-2"]', 'Type C')
  
  // Save entity
  await page.click('[data-test="save-entity"]')
  
  // Verify system_id values in UI
  await expect(page.locator('[data-test="row-0-col-0"]')).toHaveText('1')
  await expect(page.locator('[data-test="row-1-col-0"]')).toHaveText('2')
  await expect(page.locator('[data-test="row-2-col-0"]')).toHaveText('3')
  
  // Delete row 2
  await page.click('[data-test="checkbox-1"]')
  await page.click('[data-test="delete-selected"]')
  
  // Verify system_id stability (1, 3 remain)
  await expect(page.locator('[data-test="row-0-col-0"]')).toHaveText('1')
  await expect(page.locator('[data-test="row-1-col-0"]')).toHaveText('3')  // Not renumbered!
  
  // Add new row
  await page.click('[data-test="add-row"]')
  
  // New row should have system_id = 4 (max(1,3) + 1)
  await expect(page.locator('[data-test="row-2-col-0"]')).toHaveText('4')
  
  // Save and reload
  await page.click('[data-test="save-entity"]')
  await page.reload()
  
  // Verify system_id values persisted
  await expect(page.locator('[data-test="row-0-col-0"]')).toHaveText('1')
  await expect(page.locator('[data-test="row-1-col-0"]')).toHaveText('3')
  await expect(page.locator('[data-test="row-2-col-0"]')).toHaveText('4')
})
```

## UI/UX Considerations

### Question: Should system_id and public_id be addable to columns?

**Analysis**:

**Option A: Not Addable (Recommended)**
- ✅ **Prevents confusion**: Users can't accidentally add/remove critical identity columns
- ✅ **Enforces best practices**: system_id and public_id are always present and correctly positioned
- ✅ **Simpler UI**: No need to explain why these columns are "special"
- ✅ **Prevents errors**: Can't create fixed entity without system_id
- ❌ **Less flexible**: Power users can't customize identity column names

**Option B: Addable with Validation**
- ✅ **Flexible**: Advanced users can customize identity columns
- ✅ **Explicit**: User sees and controls all columns
- ❌ **Complex**: Need extensive validation and error messages
- ❌ **Error-prone**: Users can accidentally remove critical columns
- ❌ **Confusing**: "Why do I need to add system_id? What is it?"

**Recommendation**: **Option A - Not Addable**

**Implementation**:
1. `system_id` is always first column (automatically added, read-only)
2. `public_id` (if defined) is always second column (automatically added, editable)
3. UI shows these columns but they're not in the "Add Column" interface
4. Columns editor only shows business keys and domain columns
5. Clear visual distinction (styling, icons) shows identity vs. domain columns

**UI Mock**:
```
┌─────────────────────────────────────────────────────────┐
│ Fixed Values Data                                        │
├─────────────────────────────────────────────────────────┤
│ Identity Columns (Auto-managed)                         │
│ ● system_id (read-only, auto-assigned)                  │
│ ● contact_type_id (public_id, editable)                 │
│                                                          │
│ Business Keys                                            │
│ ● arbodat_code ✕                                        │
│   [+ Add Key]                                           │
│                                                          │
│ Domain Columns                                           │
│ ● contact_type ✕                                        │
│ ● description ✕                                         │
│   [+ Add Column]                                        │
└─────────────────────────────────────────────────────────┘
```

## Rollout Plan

### Week 1: Core Implementation
- ✅ Update `add_system_id()` to preserve existing values
- ✅ Add `FixedEntitySystemIdSpecification`
- ✅ Update `FixedLoader` validation
- ✅ Write core unit tests

### Week 2: Backend API
- ✅ Add validation endpoint for system_id
- ✅ Add auto-fix suggestions
- ✅ Write backend tests
- ✅ Update API documentation

### Week 3: Frontend Implementation
- ✅ Update `FixedValuesGrid` to use actual values
- ✅ Implement max+1 for new rows
- ✅ Add validation UI
- ✅ Write frontend tests

### Week 4: Documentation & Migration
- ✅ Update CONFIGURATION_GUIDE.md
- ✅ Update USER_GUIDE.md
- ✅ Create migration script
- ✅ Test migration on sample projects

### Week 5: Testing & Rollout
- ✅ End-to-end testing
- ✅ Migrate existing projects
- ✅ Deploy to staging
- ✅ User acceptance testing
- ✅ Deploy to production

## Success Criteria

1. ✅ **Stability**: system_id values never change for existing rows
2. ✅ **Uniqueness**: No duplicate system_id values in fixed entities
3. ✅ **Auto-increment**: New rows get max(system_id) + 1
4. ✅ **Validation**: Clear error messages for invalid system_id configurations
5. ✅ **FK Integrity**: Foreign keys remain valid after add/remove/reorder
6. ✅ **User Experience**: Intuitive UI with clear identity column distinction
7. ✅ **Migration**: All existing projects successfully migrated
8. ✅ **Documentation**: Complete guides for users and developers

## Risk Mitigation

### Risk 1: Breaking Existing Projects
**Mitigation**:
- Comprehensive migration script with dry-run mode
- Backup creation before modification
- Validation after migration
- Rollback capability

### Risk 2: User Confusion
**Mitigation**:
- Clear documentation with examples
- In-app tooltips and help text
- Visual distinction for identity columns
- Auto-fix suggestions for common errors

### Risk 3: Performance Impact
**Mitigation**:
- system_id validation only on save (not real-time)
- Efficient max() calculation using Set
- Grid maintains performance with read-only column

### Risk 4: Data Loss During Migration
**Mitigation**:
- Automatic backups before migration
- Validation after migration
- Manual review option
- Version control for project files

## Appendix: Example Scenarios

### Scenario 1: Creating New Fixed Entity

**User Actions**:
1. Create entity, type: "fixed"
2. Add columns: click "Add Column" → "contact_type", "description"
3. Click "Add Row" 3 times
4. Fill in values

**System Behavior**:
- system_id automatically added as first column (hidden from Add Column UI)
- First row: system_id = 1
- Second row: system_id = 2
- Third row: system_id = 3

**YAML Output**:
```yaml
contact_type:
  type: fixed
  public_id: contact_type_id
  columns: [system_id, contact_type_id, contact_type, description]
  values:
    - [1, null, "Archaeologist", "Description"]
    - [2, null, "Botanist", "Description"]
    - [3, null, "Author", "Description"]
```

### Scenario 2: Editing Existing Entity - Delete Middle Row

**Initial State**:
```yaml
values:
  - [1, null, "Archaeologist", "Description"]
  - [2, null, "Botanist", "Description"]
  - [3, null, "Author", "Description"]
  - [4, null, "Director", "Description"]
```

**User Actions**:
1. Open entity for editing
2. Select row 2 (Botanist)
3. Click "Delete Selected"
4. Save

**System Behavior**:
- Row 2 removed
- Other rows keep their system_id values
- No renumbering

**YAML Output**:
```yaml
values:
  - [1, null, "Archaeologist", "Description"]
  - [3, null, "Author", "Description"]
  - [4, null, "Director", "Description"]
```

**FK Integrity**:
- Any FK pointing to system_id = 1, 3, or 4 remains valid
- FK pointing to system_id = 2 becomes unmatched (expected)

### Scenario 3: Adding Row After Deletion

**Initial State**:
```yaml
values:
  - [1, null, "Type A", "Desc"]
  - [3, null, "Type B", "Desc"]
  - [4, null, "Type C", "Desc"]
```

**User Actions**:
1. Click "Add Row"
2. Fill in values
3. Save

**System Behavior**:
- Calculate max(1, 3, 4) = 4
- New system_id = 5

**YAML Output**:
```yaml
values:
  - [1, null, "Type A", "Desc"]
  - [3, null, "Type B", "Desc"]
  - [4, null, "Type C", "Desc"]
  - [5, null, "Type D", "Desc"]
```

### Scenario 4: Manual YAML Edit with Missing system_id

**User Actions**:
1. Manually edit YAML file
2. Add row without system_id: `[null, null, "NewType", "Desc"]`
3. Save and reload in UI

**System Behavior**:
- Validation detects null system_id
- Shows error: "Row 4 has missing system_id value"
- Auto-fix suggests: "Fill with value 5"
- User clicks "Apply Fix"
- system_id set to 5

**YAML After Fix**:
```yaml
values:
  - [1, null, "Type A", "Desc"]
  - [3, null, "Type B", "Desc"]
  - [4, null, "Type C", "Desc"]
  - [5, null, "NewType", "Desc"]
```

## Conclusion

This implementation plan provides a comprehensive approach to making `system_id` a stable, client-maintained identifier for fixed value entities. The key principle is **stability**: system_id values never change except when explicitly set by the user or auto-assigned for new rows.

By implementing these changes, we ensure:
- ✅ FK relationships remain valid across edit operations
- ✅ Users have predictable, intuitive editing experience  
- ✅ Data integrity is maintained
- ✅ System is robust against reordering and deletion
- ✅ Clear separation between identity and domain columns
