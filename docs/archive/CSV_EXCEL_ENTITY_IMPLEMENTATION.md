# CSV and Excel Entity Type Implementation

## Overview

This document describes the implementation of CSV and Excel file type support in the Shape Shifter entity editor, enabling users to directly specify file sources for entities without creating separate data sources.

**Date**: January 2025  
**Status**: ✅ Implementation Complete - Ready for Testing

## Motivation

Previously, loading data from CSV or Excel files required:
1. Creating a data source configuration
2. Referencing that data source in the entity

This was cumbersome for simple file loading scenarios. The new implementation allows direct specification of file sources in the entity editor.

## Implementation Summary

### Entity Types Added

Three new entity types were added to complement existing types (entity, sql, fixed):

- **`csv`** - CSV files with configurable delimiter and encoding
- **`xlsx`** - Excel files using Pandas loader (supports sheet_name, range)
- **`openpyxl`** - Excel files using OpenPyXL loader (supports sheet_name, range)

### Key Changes

#### 1. TypeScript Type Definitions (`frontend/src/types/entity.ts`)

**EntityType enum extended:**
```typescript
export type EntityType = 'entity' | 'sql' | 'fixed' | 'csv' | 'xlsx' | 'openpyxl'
```

**New EntityFileOptions interface:**
```typescript
export interface EntityFileOptions {
  filename: string
  sep?: string          // CSV delimiter
  encoding?: string     // File encoding
  sheet_name?: string   // Excel sheet name
  range?: string        // Excel range (e.g., "A1:D10")
}
```

**Entity interface updated:**
```typescript
export interface Entity {
  // ... existing fields
  options?: EntityFileOptions | null
}
```

#### 2. Entity Form Dialog (`frontend/src/components/entities/EntityFormDialog.vue`)

**UI Components Added:**

1. **Entity Type Selector** - Extended with CSV and Excel options:
   - CSV (Text file with delimiter)
   - Excel - Pandas (*.xlsx with pandas)
   - Excel - OpenPyXL (*.xlsx with openpyxl)

2. **File Options Section** - Conditional UI based on entity type:
   - **Filename** (autocomplete) - Required for file types
   - **Delimiter** (select) - CSV only, defaults to comma
   - **Sheet Name** (text) - Excel only, optional
   - **Range** (text) - Excel with OpenPyXL only, optional (e.g., "A1:D10")

**State Management:**

- `FormData` interface extended with `options` object
- `availableProjectFiles` ref for file listing
- `filesLoading` ref for loading state
- `delimiterOptions` constant for CSV delimiter choices

**Computed Properties:**

- `isFileType` - Detects if current type is csv, xlsx, or openpyxl
- `isExcelType` - Detects if current type is xlsx or openpyxl  
- `getFileExtensionHint` - Shows expected file extension based on type

**Functions Added:**

- `fetchProjectFiles()` - Loads available files from API endpoint
- `getFileExtensions()` - Returns expected extensions for filtering

**Watchers:**

- Type change watcher clears options and fetches appropriate files
- Form data watcher syncs options to YAML editor

**Serialization/Deserialization:**

- `formDataToYaml()` - Serializes options for CSV/Excel types
- `yamlToFormData()` - Parses options from YAML
- `handleSubmit()` - Includes options in API payload for file types

**Validation:**

- Filename field has required validation when file type selected
- Delimiter required for CSV type

#### 3. Backend Integration

**No backend changes required** - The backend already fully supports file options through existing loaders:

- `src/loaders/file_loaders.py` - `CsvLoader` accepts filename, sep, encoding
- `src/loaders/excel_loaders.py` - `PandasLoader` and `OpenPyxlLoader` accept filename, sheet_name, range

**API Endpoint Used:**

- `GET /api/v1/data-sources/files` - Lists available project files

## Architecture Pattern

### SQL vs File Type Patterns

**SQL Type (data source approach - unchanged):**
```yaml
entities:
  my_table:
    type: sql
    data_source: postgres_db  # Reusable connection
    query: "SELECT * FROM table"
    keys: [id]
```

**Benefits**: Connection reusability, credential security, DBMS abstraction

**File Types (inline options - new):**
```yaml
entities:
  my_csv:
    type: csv
    options:
      filename: data.csv
      sep: ','
      encoding: utf-8
    keys: [id]
  
  my_excel:
    type: xlsx
    options:
      filename: data.xlsx
      sheet_name: Sheet1
      range: A1:D100
    keys: [id]
```

**Benefits**: Simplicity, no extra configuration, direct specification

## File Type Details

### CSV Type

**Required Options:**
- `filename` - Path to CSV file (relative to project directory)
- `sep` - Delimiter character (default: `,`)

**Optional Options:**
- `encoding` - File encoding (default: `utf-8`)

**Example:**
```yaml
my_data:
  type: csv
  options:
    filename: input/data.csv
    sep: ';'
    encoding: utf-8
  keys: [id]
  columns: [name, value]
```

**UI Fields:**
- Filename (autocomplete with .csv files)
- Delimiter (dropdown: comma, semicolon, tab, pipe, space)

### Excel - Pandas Type (xlsx)

**Required Options:**
- `filename` - Path to Excel file

**Optional Options:**
- `sheet_name` - Sheet name or index (default: first sheet)

**Example:**
```yaml
my_excel:
  type: xlsx
  options:
    filename: input/data.xlsx
    sheet_name: Sheet1
  keys: [id]
  columns: [name, value]
```

**UI Fields:**
- Filename (autocomplete with .xlsx files)
- Sheet Name (text field, optional)

### Excel - OpenPyXL Type (openpyxl)

**Required Options:**
- `filename` - Path to Excel file

**Optional Options:**
- `sheet_name` - Sheet name or index (default: first sheet)
- `range` - Cell range (e.g., "A1:D10") for partial sheet loading

**Example:**
```yaml
my_excel_range:
  type: openpyxl
  options:
    filename: input/data.xlsx
    sheet_name: Sheet1
    range: A1:D100
  keys: [id]
  columns: [name, value]
```

**UI Fields:**
- Filename (autocomplete with .xlsx files)
- Sheet Name (text field, optional)
- Range (text field, optional, format: "A1:D10")

## User Workflow

### Creating a CSV Entity

1. Click "Create Entity" button
2. Enter entity name
3. Select "CSV" from type dropdown
4. **File Options section appears**
5. Select CSV file from filename dropdown (autocomplete)
6. Choose delimiter (default: comma)
7. Define keys and columns as usual
8. Click "Create Entity"

### Creating an Excel Entity

1. Click "Create Entity" button
2. Enter entity name
3. Select "Excel - Pandas" or "Excel - OpenPyXL" from type dropdown
4. **File Options section appears**
5. Select Excel file from filename dropdown (autocomplete)
6. (Optional) Enter sheet name
7. (Optional for OpenPyXL) Enter cell range
8. Define keys and columns as usual
9. Click "Create Entity"

### Editing File Entities

When editing an entity with file type:
1. File options section automatically displays
2. Current options are pre-populated
3. Modify filename, delimiter, sheet_name, or range as needed
4. Changes are reflected in YAML editor in real-time

## Testing Checklist

### Unit Testing

- [ ] Verify EntityType enum includes csv, xlsx, openpyxl
- [ ] Verify EntityFileOptions interface structure
- [ ] Test isFileType computed property detection
- [ ] Test isExcelType computed property detection
- [ ] Test formDataToYaml serialization for file types
- [ ] Test yamlToFormData parsing for file types
- [ ] Test handleSubmit includes options in payload

### Integration Testing

- [ ] Test GET /api/v1/data-sources/files endpoint
- [ ] Verify files are listed correctly in autocomplete
- [ ] Test file filtering by extension based on type
- [ ] Verify form validation (required filename)
- [ ] Test entity creation with CSV type
- [ ] Test entity creation with Excel types
- [ ] Test entity update with file options
- [ ] Verify YAML editor sync with form changes

### End-to-End Testing

**CSV Entity:**
1. [ ] Create project
2. [ ] Upload CSV file to project
3. [ ] Create entity with type: csv
4. [ ] Specify filename and delimiter
5. [ ] Verify entity appears in entity list
6. [ ] Preview entity data
7. [ ] Verify data loads correctly

**Excel Entity (Pandas):**
1. [ ] Upload Excel file with multiple sheets
2. [ ] Create entity with type: xlsx
3. [ ] Specify filename and sheet_name
4. [ ] Preview entity data
5. [ ] Verify correct sheet data loads

**Excel Entity (OpenPyXL):**
1. [ ] Create entity with type: openpyxl
2. [ ] Specify filename, sheet_name, and range
3. [ ] Preview entity data
4. [ ] Verify only specified range loads

**Edit Workflow:**
1. [ ] Edit existing file entity
2. [ ] Change filename
3. [ ] Modify delimiter/sheet_name
4. [ ] Save changes
5. [ ] Verify changes persist

**YAML Editor Sync:**
1. [ ] Create file entity in form view
2. [ ] Switch to YAML view
3. [ ] Verify options serialized correctly
4. [ ] Edit YAML directly (add/modify options)
5. [ ] Switch to form view
6. [ ] Verify form reflects YAML changes

## File Organization

### Modified Files

1. `frontend/src/types/entity.ts` - Type definitions
2. `frontend/src/components/entities/EntityFormDialog.vue` - Main entity editor

### Backend Files (No Changes Required)

- `src/loaders/file_loaders.py` - CsvLoader implementation
- `src/loaders/excel_loaders.py` - PandasLoader, OpenPyxlLoader implementations
- `backend/app/api/v1/endpoints/data_sources.py` - File listing endpoint

## Configuration Changes

No configuration changes required - uses existing `PROJECTS_DIR` setting for file storage.

## Known Limitations

1. **File Upload**: Users must upload files to project directory before referencing them
2. **File Validation**: File existence not validated until preview/execution
3. **Large Files**: No file size limits enforced (delegated to backend loaders)
4. **Excel Formulas**: Formula evaluation depends on loader (Pandas vs OpenPyXL)

## Future Enhancements

1. **File Upload UI**: Direct file upload from entity editor
2. **File Preview**: Preview file contents before entity creation
3. **Column Detection**: Auto-detect columns from file headers
4. **Encoding Detection**: Auto-detect CSV encoding
5. **Sheet Selection**: Dropdown for Excel sheet selection
6. **Range Picker**: Visual Excel range selector

## Migration Guide

### Existing File-Based Entities

Entities using data sources for file loading can be migrated to direct file specification:

**Before (data source approach):**
```yaml
data_sources:
  csv_files:
    driver: csv
    config:
      base_path: input/

entities:
  my_data:
    type: entity
    source: csv_files
    query: data.csv
    keys: [id]
```

**After (direct file approach):**
```yaml
entities:
  my_data:
    type: csv
    options:
      filename: input/data.csv
      sep: ','
      encoding: utf-8
    keys: [id]
```

**Benefits:**
- Simpler configuration
- No data source management
- Direct file reference

**When to Keep Data Source Approach:**
- Multiple entities sharing same connection
- Dynamic base path configuration
- Environment-specific paths

## Documentation Updates

### Files to Update

1. ✅ This implementation document
2. [ ] `docs/CONFIGURATION_GUIDE.md` - Add file type entity examples
3. [ ] `docs/USER_GUIDE.md` - Add user workflow documentation
4. [ ] `README.md` - Update feature list

### Code Comments

- EntityFormDialog.vue has inline comments for file handling logic
- TypeScript interfaces documented with JSDoc comments

## Conclusion

The CSV and Excel entity type implementation provides a streamlined workflow for file-based entities, reducing configuration complexity while maintaining full backend compatibility. The implementation is complete and ready for testing.

**Next Steps:**
1. Run integration tests
2. Perform end-to-end testing with real CSV/Excel files
3. Update user-facing documentation
4. Consider future enhancements based on user feedback
