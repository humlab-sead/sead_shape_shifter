# Fixed Values Grid Installation

The Entity Form now includes an editable grid for managing fixed entity values using **Ag-Grid Community Edition** (MIT Licensed).

## Installation

Install the required dependencies:

```bash
pnpm install
```

This will install:
- `ag-grid-community` ^32.3.3
- `ag-grid-vue3` ^32.3.3

## Features

### Current Features
- ✅ Editable grid for fixed entity values
- ✅ Row selection with checkbox
- ✅ Add/Delete rows
- ✅ Sortable and filterable columns
- ✅ Resizable columns
- ✅ Column headers from entity Keys + Columns
- ✅ Full integration with entity CRUD operations
- ✅ YAML export/import support

### Future Customization Options (Ag-Grid supports)
- Type-aware cell editors (number, date, boolean, etc.)
- Dropdown/autocomplete cell editors with picklists
- Cell validation and custom validators
- Custom cell renderers (colors, badges, icons)
- Conditional formatting
- Copy/paste support
- Undo/redo
- Excel export
- And much more...

## Usage

The grid automatically appears in the **Basic** tab when:
- Entity Type is set to "fixed"
- Keys and Columns are defined

The grid columns are automatically generated from the combined Keys + Columns fields.

## Component Location

`frontend/src/components/entities/FixedValuesGrid.vue`

## Documentation

- [Ag-Grid Documentation](https://www.ag-grid.com/vue-data-grid/)
- [Vue 3 Integration Guide](https://www.ag-grid.com/vue-data-grid/getting-started/)
