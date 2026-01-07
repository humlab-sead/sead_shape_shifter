# Shape Shifter Configuration Editor - User Guide

Complete guide for using the Shape Shifter Configuration Editor web interface.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Managing Configurations](#managing-configurations)
3. [Working with Entities](#working-with-entities)
4. [Visualizing Dependencies](#visualizing-dependencies)
5. [Validation](#validation)
6. [Keyboard Shortcuts](#keyboard-shortcuts)
7. [Tips & Tricks](#tips--tricks)

## Getting Started

### Accessing the Editor

1. Open your web browser
2. Navigate to http://localhost:5173 (or your deployment URL)
3. You'll see the home page with navigation options

### Interface Overview

The editor consists of:

- **Sidebar**: Quick navigation to all features
- **App Bar**: Current configuration and quick actions
- **Breadcrumbs**: Shows your current location
- **Main Content**: The active view

## Managing Configurations

### Viewing Configurations

1. Click **Configurations** in the sidebar
2. See all configurations in a grid layout
3. Each card shows:
   - Configuration name
   - Number of entities
   - Last modified date
   - Validation status

### Creating a Configuration

1. Go to Configurations page
2. Click **New Configuration** button
3. Enter a configuration name:
   - Use letters, numbers, hyphens, and underscores
   - 3-50 characters
   - Must be unique
4. Click **Create**

### Editing a Configuration

1. Click on a configuration card
2. You'll see three tabs:
   - **Entities**: Manage entities
   - **Validation**: View validation results
   - **Settings**: Backup management

### Deleting a Configuration

1. Click the delete icon on a configuration card
2. Confirm deletion in the dialog
3. ⚠️ This action cannot be undone

### Searching Configurations

Use the search bar at the top to filter by name.

### Sorting Configurations

Use the sort dropdown to order by:
- Name (A-Z or Z-A)
- Entity count
- Last modified date

## Working with Entities

### What are Entities?

Entities represent tables or data sources in your configuration. Each entity defines:
- How data is loaded
- Which columns to include
- Relationships to other entities
- Transformations to apply

### Creating an Entity

1. Open a configuration
2. Click **Add Entity** button
3. Fill in the **Basic** tab:
   - **Name**: Lowercase snake_case (e.g., `sample_type`)
   - **Type**: Choose data source type
     - **Data**: Load from CSV
     - **SQL**: Execute SQL query
     - **Fixed**: Use fixed values
   - **Keys**: Natural key columns
   - **Surrogate ID**: Optional generated ID
   - **Columns**: Columns to extract
   - **Source**: Optional parent entity

4. For SQL type, also provide:
   - **Data Source**: Database connection name
   - **Query**: SQL SELECT statement

5. Click **Create**

### Editing an Entity

1. Click the edit icon next to an entity
2. Modify fields in the **Basic** tab
3. Switch to **Foreign Keys** tab for relationships
4. Switch to **Advanced** tab for filters/transformations
5. Click **Save**

### Configuring Foreign Keys

Foreign keys define relationships between entities:

1. Edit an entity
2. Go to **Foreign Keys** tab
3. Click **Add**
4. Configure:
   - **Entity**: Target entity name
   - **Local Keys**: Columns in this entity
   - **Remote Keys**: Columns in target entity
   - **Join Type**: inner, left, right, outer, or cross
   - **Constraints**: Cardinality and uniqueness rules

### Advanced Entity Configuration

The **Advanced** tab provides:

#### Filters
- **Exists In**: Keep only rows that exist in another entity
- Add multiple filters to combine conditions

#### Unnest
- Transform wide data to long format
- **ID Variables**: Columns to keep
- **Value Variables**: Columns to unpivot
- **Variable Name**: Name for new category column
- **Value Name**: Name for new value column

#### Append
- Add additional rows to entity
- **Fixed**: Provide JSON array of values
- **SQL**: Execute query to fetch rows

### Deleting an Entity

1. Click the delete icon next to an entity
2. Confirm deletion
3. ⚠️ Check dependencies first!

### Searching Entities

Use the search bar in the entity list to filter by name.

### Filtering by Type

Use the type dropdown to show only data, SQL, or fixed entities.

## Visualizing Dependencies

### Opening the Graph

1. Click **Dependency Graph** in sidebar
2. Select a configuration from dropdown
3. View the entity dependency graph

### Understanding the Graph

- **Nodes**: Represent entities
- **Edges**: Show dependencies (arrows point from dependent to dependency)
- **Blue nodes**: Normal entities
- **Red nodes**: Entities in circular dependency
- **Red edges**: Part of circular dependency

### Interacting with the Graph

- **Click node**: View entity details in side panel
- **View dependencies**: See what this entity depends on
- **View dependents**: See what depends on this entity
- **Edit entity**: Click "Edit Entity" button in panel

### Graph Controls

- **Show Labels**: Toggle entity names
- **Highlight Cycles**: Emphasize circular dependencies
- **Statistics**: View node and edge counts

## Validation

### Running Validation

1. Open a configuration
2. Go to **Validation** tab
3. Click **Validate Now**
4. Wait for validation to complete

### Understanding Results

#### Success ✓
- Green indicator
- "Validation Passed"
- Configuration is ready to use

#### Warnings ⚠
- Yellow indicator
- Shows warning count
- Review warnings in tabs below

#### Errors ✗
- Red indicator
- Shows error count
- Must fix before using configuration

### Viewing Messages

Switch between tabs:
- **All Issues**: Combined errors and warnings
- **Errors**: Critical issues only
- **Warnings**: Non-critical issues only

Each message shows:
- Severity icon
- Error/warning message
- Entity name (if applicable)
- Field name (if applicable)
- Error code
- Suggestion (hover lightbulb icon)

### Common Validation Issues

**Circular Dependencies**
- Entities depend on each other in a loop
- Fix: Break the cycle by removing a dependency

**Missing Entity**
- Referenced entity doesn't exist
- Fix: Create the entity or remove reference

**Invalid Keys**
- Key columns not found in entity
- Fix: Check column names or data source

**Type Mismatch**
- Data type incompatibility
- Fix: Ensure consistent data types

## Keyboard Shortcuts

### Global

- `Ctrl+K` - Open command palette
- `Ctrl+H` - Go to home
- `Ctrl+G` - Go to dependency graph
- `Ctrl+Shift+C` - Go to configurations
- `Esc` - Close open dialog

### Command Palette

Press `Ctrl+K` to open, then:
- Type to search commands
- Use arrow keys to navigate
- Press Enter to execute
- Press Esc to close

## Tips & Tricks

### Efficient Workflow

1. **Create configuration structure first**
   - Plan entity hierarchy
   - Start with root entities (no dependencies)
   - Add dependent entities progressively

2. **Validate early and often**
   - Run validation after adding entities
   - Fix issues before they compound

3. **Use the dependency graph**
   - Visualize before building complex relationships
   - Identify circular dependencies early

4. **Leverage keyboard shortcuts**
   - `Ctrl+K` for quick navigation
   - `Esc` to close dialogs quickly

### Best Practices

**Naming Conventions**
- Use snake_case for entity names
- Keep names descriptive but concise
- Use consistent prefixes for related entities

**Entity Organization**
- Group related entities by source/destination
- Use clear source relationships
- Document complex transformations

**Foreign Keys**
- Prefer inner joins for required relationships
- Use left joins for optional relationships
- Add constraints to enforce data quality

**Validation**
- Fix errors before warnings
- Read suggestions carefully
- Test with sample data

### Backup & Recovery

**Automatic Backups**
- Configurations are backed up automatically
- Access via configuration detail page
- Click "Backups" button

**Restoring**
1. Click "Backups" in configuration detail
2. See list of available backups with timestamps
3. Click "Restore" on desired backup
4. Confirm restoration
5. Current version is backed up before restoring

**Manual Backup**
- Download YAML file directly (coming soon)
- Keep local copies of important configurations

### Troubleshooting

**Cannot Create Entity**
- Check name is valid snake_case
- Ensure name is unique
- Verify required fields are filled

**Validation Fails**
- Read error messages carefully
- Check entity exists before referencing
- Verify data source connections

**Graph Not Showing**
- Ensure configuration has entities
- Check browser console for errors
- Refresh page and try again

**Slow Performance**
- Limit large entity lists with filters
- Close unused browser tabs
- Clear browser cache if needed

## Getting Help

### In-App Help

Press `Ctrl+K` and search for "help" or click the help icon in the sidebar.

### Documentation

- [Developer Guide](./DEVELOPER_GUIDE.md)
- [API Documentation](../../backend/README.md)
- [Shape Shifter Main Docs](../../docs/)

### Support

For issues or questions:
1. Check this user guide
2. Review validation messages
3. Consult Shape Shifter documentation
4. Contact your system administrator

## Next Steps

Now that you understand the basics:

1. Create your first configuration
2. Add some entities
3. Define relationships
4. Run validation
5. Visualize dependencies
6. Export to YAML (via backend)

Happy configuring! 🎉
