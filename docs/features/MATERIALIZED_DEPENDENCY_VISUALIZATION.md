# Materialized Entity Dependency Visualization

## Overview

When an entity is materialized (frozen to fixed values), the dependency graph now shows the **historical dependencies** that existed when the entity was frozen. This provides valuable context about the data sources used to create the materialized state.

## Backend Implementation

### Source Extraction

The `MaterializedFixedSourceNodeExtractor` class extracts source nodes and edges from the `materialized.source_state` configuration:

- For SQL entities: shows database and table dependencies
- For CSV entities: shows file dependencies  
- For Excel entities: shows file → sheet → entity chains
- **All edges are marked with `frozen=True`** to distinguish them from active dependencies

### Edge Marking

Frozen edges include:
- `frozen: true` flag in edge data
- Modified label: `"<original_label> (frozen)"` for visual distinction
- Same source node types as active entities (database, table, file, sheet)

## Frontend Visualization

### Visual Styling

Frozen edges are styled with:
- **Dashed line** (`line-style: 'dashed'`)
- **Green color** (`#4CAF50`) matching materialized node borders
- **60% opacity** for subtle appearance
- **Custom dash pattern** (8px line, 4px gap)

### User Benefits

1. **Historical Context**: See what data sources were used when entity was frozen
2. **Dependency Tracking**: Understand the lineage of materialized data
3. **Visual Distinction**: Clear separation between active and frozen dependencies
4. **Audit Trail**: Know what was included when the snapshot was taken

## Example

```yaml
entities:
  users:
    type: fixed
    columns: [id, name, email]
    values: @file:materialized/users.parquet
    materialized:
      enabled: true
      source_state:
        type: sql
        data_source: production_db
        query: "SELECT id, name, email FROM users WHERE active = true"
      materialized_at: "2024-01-15T10:30:00"
```

**Dependency Graph Display:**
- **Nodes**: `production_db` (database) → `users` (table) → `users` (entity)
- **Edges**: Dashed green lines with labels like "contains (frozen)" and "used_in (frozen)"
- **Visual**: Clearly distinguishable from active database queries

## Technical Details

### Backend Classes

- `MaterializedFixedSourceNodeExtractor` - Extracts frozen dependencies
- `SqlSourceNodeExtractor` - Reused for SQL source state  
- `CsvFileSourceNodeExtractor` - Reused for CSV source state
- `ExcelFileSourceNodeExtractor` - Reused for Excel source state

### Frontend Updates

- `DependencyEdge` type: Added `frozen?: boolean` field
- `cytoscapeStyles.ts`: Added `.frozen-edge` CSS class
- `graphAdapter.ts`: Maps frozen flag to CSS class

### Testing

Comprehensive tests in `backend/tests/test_dependency_service_validation.py`:
- SQL materialized entity frozen dependencies
- CSV materialized entity frozen file links
- Excel materialized entity frozen sheet chains
- Non-materialized entities have no frozen edges

## Design Rationale

### Why Show Frozen Dependencies?

1. **Transparency**: Users need to know what data sources were used
2. **Debugging**: Helps diagnose issues with materialized data
3. **Auditing**: Provides lineage information for compliance
4. **Decision Making**: Informs whether to rematerialize based on source changes

### Why Visual Distinction?

1. **Clarity**: Prevents confusion with active dependencies
2. **Status Indication**: Green color signals "stable/cached" state
3. **Non-intrusive**: Dashed lines + lower opacity keep graph readable
4. **Consistency**: Matches materialized node styling (double border, green)

## Future Enhancements

Potential improvements:
- Tooltip showing materialization timestamp on hover
- Badge indicating source data staleness
- Diff view comparing frozen vs. current source state
- Click to rematerialize from graph
