# Shape Shifter Project Editor — User Guide

---

# Table of Contents

1. Introduction
2. Quick Start
3. Typical Workflow
4. Projects and Workspace
5. Working with Entities
6. Entity Types
7. Validation
8. Reconciliation
9. Execute and Export
10. Dispatch
11. Advanced Features
12. YAML Editing
13. Automation and CLI
14. Troubleshooting
15. FAQ
16. Additional Documentation

---

# 1. Introduction

## What Is Shape Shifter?

Shape Shifter is a configuration-driven data transformation system used to restructure, validate, reconcile, and export data into formats expected by downstream systems such as SEAD.

It helps bridge the gap between:

- how source data is originally organized
- how target systems expect that data to look

Typical source data includes:

- spreadsheets
- CSV files
- SQL databases
- exported reports
- manually curated lookup tables

Typical users include:

- researchers
- data managers
- integrators
- ETL and migration specialists
- SEAD project contributors

---

## What Problems Does It Solve?

Shape Shifter helps when:

- source data uses inconsistent naming
- identifiers differ between systems
- relationships between tables are unclear
- data must be normalized before delivery
- controlled vocabularies or authority records are required
- exports must follow strict target-system rules

---

## What You Can Do with Shape Shifter

With Shape Shifter you can:

- load data from files or databases
- define transformation pipelines
- create relationships between entities
- preview transformed data
- validate structure and contents
- reconcile values against authority systems
- export normalized datasets
- dispatch processed data to downstream systems

---

## Before You Start Editing

There are a few important things to understand early:

- Shape Shifter automatically manages `system_id`
- Validation is incremental and should be run often
- Projects support backups and restore operations
- Multiple users can edit the same project
- Save conflicts may occur during concurrent editing
- Previewing entities before execution is strongly recommended

---

# 2. Quick Start

This section walks through the simplest successful workflow.

## Create Your First Project

1. Open the **Projects** page.
2. Click **New Project**.
3. Enter a project name.
4. Open the new project.

---

## Upload a Source File

1. Open the **Files** tab.
2. Upload a `.csv` or `.xlsx` file.
3. Confirm the file appears in the project.

---

## Create an Entity

1. Open the **Entities** tab.
2. Click **Add Entity**.
3. Choose an entity type.
4. Select the uploaded source file.
5. Configure identity fields.
6. Save the entity.

---

## Preview the Data

1. Open the entity editor.
2. Switch to **Split View** or **Preview Only**.
3. Confirm columns and row counts look correct.

---

## Run Validation

1. Open the **Validate** tab.
2. Run **YAML Validation**.
3. Run **Sample Data Validation**.
4. Review warnings and errors.

---

## Export the Result

1. Click **Execute**.
2. Choose an output format.
3. Select a destination.
4. Run the workflow.

You now have your first normalized export.

---

# 3. Typical Workflow

Most projects follow the same general lifecycle.

```text
Load Data
   ↓
Create Entities
   ↓
Preview & Validate
   ↓
Reconcile Values
   ↓
Execute Export
   ↓
Dispatch to Target System
```

---

## Step 1 — Load Data

Bring data into the project using:

- uploaded files
- shared data sources
- SQL queries
- inline fixed values

---

## Step 2 — Create Entities

Entities define:

- data sources
- transformations
- relationships
- identifiers
- validation behavior

---

## Step 3 — Preview and Validate

Use previews and validation continuously while editing.

Recommended workflow:

1. Preview entity output
2. Run YAML validation
3. Run sample validation
4. Run complete validation before export

---

## Step 4 — Reconcile Values

If the project uses controlled vocabularies or authority systems:

1. Configure reconciliation
2. Run auto-reconcile
3. Review uncertain matches
4. Save accepted mappings

---

## Step 5 — Execute Export

Run the normalization pipeline and generate:

- Excel exports
- CSV folders
- ZIP archives
- database output

---

## Step 6 — Dispatch

Dispatch sends already-processed data to downstream systems using ingester configuration.

---

# 4. Projects and Workspace

## Projects Page

The **Projects** page is the main entry point.

From here you can:

- create projects
- search projects
- open projects
- duplicate projects
- delete projects
- run quick validation

---

## Project Workspace

A project contains:

- a header toolbar
- validation status
- session status
- tabbed workspace tools

---

## Workspace Tabs

| Tab | Purpose |
|---|---|
| Entities | Create and manage entities |
| Dependencies | Visualize entity dependency graph |
| Reconciliation | Configure and run reconciliation |
| Validation | Run validation workflows |
| Dispatch | Run the ingester to deliver processed data |
| Data Sources | Connect shared database sources |
| Metadata | Edit project metadata |
| Files | Upload local files |
| YAML | Edit raw project YAML directly |

---

## Global Navigation

The sidebar provides access to top-level pages:

| Page | Purpose |
|---|---|
| Projects | Create and open projects |
| Data Sources | Manage shared database connections |
| Schema Explorer | Browse database table and column structure |
| Query Tester | Run SQL queries against connected data sources |
| Data Ingestion | Run registered ingesters to load data into a database |
| Settings | Application preferences |
| What's New | Recent release notes |

## Header Actions

| Button | Purpose |
|---|---|
| Execute | Run the normalization workflow and produce output |
| Backups | View and restore earlier project versions |
| Refresh | Reload project state from disk |
| Save Changes | Save current edits |

---

## Concurrent Editing

Projects support multiple editing sessions.

If another user changes the project while you are editing:

- save may fail
- refresh may be required
- your changes may need to be reapplied

Always save regularly.

---

# 5. Working with Entities

## What Is an Entity?

An entity is the core transformation object in Shape Shifter.

Entities:

- load data
- transform rows
- define relationships
- expose normalized columns
- participate in validation and export

Conceptually, entities are similar to:

- database tables
- SQL views
- ETL pipeline stages

---

## Common Entity Workflow

Typical editing process:

1. Create entity
2. Configure source
3. Define keys and IDs
4. Preview results
5. Add relationships
6. Validate output
7. Execute export

---

## Entity Editor Modes

| Mode | Purpose |
|---|---|
| Form Only | Focused editing |
| Split View | Edit and preview together |
| Preview Only | Inspect transformed data |

Shortcut:

- `Ctrl+Shift+P` toggles split view

---

## Entity Editor Tabs

| Tab | Purpose |
|---|---|
| Basic | Core settings |
| Foreign Keys | Relationship configuration |
| Filters | Row filtering |
| Unnest | Wide-to-long transformations |
| Append | Concatenate data |
| Replace | Value replacement rules |
| Extra Columns | Add derived fields |
| YAML | Raw configuration editing |

---

## Preview While Editing

Preview helps verify:

- row counts
- column names
- inferred data types
- transformation logic
- filter behavior
- dependency joins

Preview early and often.

---

## Identity Fields

Shape Shifter uses a three-level identity model.

### System ID

- always named `system_id`
- managed automatically
- used internally for relationships
- read-only in the editor

---

### Public ID

- target-facing identifier
- must end with `_id`
- used in exports and reconciliation

---

### Business Keys

- natural keys from source data
- used for matching and deduplication
- may be compound keys

---

## Working with Source Data

Depending on entity type, entities can load data from:

- another entity
- SQL queries
- CSV files
- Excel files
- inline fixed values

---

## Common Editing Patterns

### Create from Scratch

1. Add entity
2. Choose type
3. Configure source
4. Define IDs and keys
5. Add transformations
6. Save

---

### Create from Database Source

1. Open **Data Sources**
2. Connect shared source
3. Use **Create Entity from Table**
4. Review generated configuration

---

### Edit YAML Directly

1. Open entity editor
2. Switch to **YAML**
3. Edit configuration
4. Save

---

# 6. Entity Types

## Overview

Different entity types support different workflows.

| Type | Purpose |
|---|---|
| entity | Derived entity from another entity |
| sql | Query-based entity |
| fixed | Inline static values |
| merged | Combined multi-source entity |
| csv | CSV or TSV file import |
| xlsx | Excel import via Pandas |
| openpyxl | Excel import with range support |

---

## Fixed Entities

Use `fixed` entities for:

- lookup tables
- small controlled vocabularies
- manually curated lists
- frozen cached values

The fixed editor supports spreadsheet-style pasting.

---

## Merged Entities

### When to Use Merged Entities

Use `type: merged` when:

- multiple sources represent one logical parent
- branch sources differ structurally
- unified exports are needed
- sparse branch lineage must be preserved

---

### What Merged Entities Produce

Merged entities create:

- discriminator columns
- sparse lineage foreign keys
- unified parent outputs
- new local `system_id` values

---

### Recommended Workflow

1. Validate each branch source independently
2. Create merged parent
3. Add branches
4. Preview merged output
5. Run validation

---

### Debugging Merged Entities

If merged previews look incorrect:

- switch preview to **Branch Source**
- inspect branch-specific rows
- verify branch keys
- check source entities independently

---

# 7. Validation

## Why Validation Matters

Validation catches:

- broken references
- invalid structure
- missing columns
- duplicate keys
- empty outputs
- target-model violations

---

## Validation Workflow

Recommended sequence:

1. YAML Validation
2. Sample Data Validation
3. Complete Data Validation
4. Conformance Validation

---

## Validation Types

### YAML Validation

Checks:

- configuration structure
- entity references
- consistency rules

---

### Data Validation

Checks actual processed data.

Available validators:

- Column Exists
- Natural Key Uniqueness
- Non-Empty Result

---

### Conformance Validation

Checks whether the project satisfies a target model.

Examples:

- required entities
- required columns
- required foreign keys
- naming conventions

---

## Reading Validation Results

Results are grouped by:

- severity
- entity
- category
- issue type

Categories include:

- structural
- data
- performance
- conformance

---

## Recommended Best Practice

- validate after structural edits
- use sample validation during iteration
- always run complete validation before execution

---

# 8. Reconciliation

## What Is Reconciliation?

Reconciliation links local source values to authoritative target-system records.

Examples:

- taxon names
- site names
- method names
- vocabulary terms

---

## Reconciliation Workflow

1. Configure reconciliation specs
2. Select entity and field
3. Run auto-reconcile
4. Review matches
5. Approve or adjust mappings
6. Save reconciliation results

---

## Reconcile Tab Areas

| Area | Purpose |
|---|---|
| Configuration | Define reconciliation specs |
| YAML | Edit raw reconciliation config |
| Reconcile & Review | Interactive review grid |

---

# 9. Execute and Export

## What Execute Does

Execute runs the normalization workflow and produces output.

---

## Common Output Types

| Type | Dispatcher |
|---|---|
| CSV Folder | csv |
| ZIP CSV | zipcsv |
| Excel | xlsx |
| Excel (advanced) | openpyxl |
| Database | db |

---

## Recommended Execution Workflow

1. Save changes
2. Run complete validation
3. Execute export
4. Review output
5. Dispatch if needed

---

## Execution Options

| Option | Purpose |
|---|---|
| Run validation first | Validate before processing |
| Apply translations | Apply mapping rules |
| Drop FK columns | Remove FK columns from output |

---

## After Execution

The dialog reports:

- success or failure
- processed entity count
- destination path
- downloadable result files

---

# 10. Dispatch and Data Ingestion

## Execute vs. Dispatch vs. Ingestion

These three actions are distinct:

| Action | Where | Purpose |
|---|---|---|
| **Execute** | Header button | Runs the normalization pipeline and produces output files (CSV, Excel, ZIP, or database) |
| **Dispatch** | Project → Dispatch tab | Runs a configured ingester directly from the project workspace to deliver processed data to a target system |
| **Data Ingestion** | Top-level page | Runs any registered ingester independently of a project |

## Dispatch Tab (in Project Workspace)

The Dispatch tab lets you configure and run an ingester from within your project.

Workflow:
1. Open a project and go to the **Dispatch** tab.
2. Select a registered ingester from the list.
3. Fill in the ingester configuration (data source, submission name, options).
4. Run the ingester.
5. Review the result summary.

Dispatch requires that Execute has already produced output, or that a suitable output path is configured.

## Data Ingestion Page

The top-level **Data Ingestion** page provides the same ingester capability without being tied to a specific project.

Use it for:
- one-off ingestion runs
- batch imports
- testing ingester configuration before using it in a project

Workflow:
1. Open **Data Ingestion** from the sidebar.
2. Select an ingester from the list.
3. Enter connection and configuration details.
4. Run the ingester.

---

# 11. Advanced Features

## Dependencies Graph

The Dependencies tab shows the full entity dependency graph for the project.

Features:
- visualize data flow between entities
- detect circular dependencies (shown as alerts)
- navigate directly to any entity by clicking a node
- filter by task completion status
- switch layout algorithms
- inspect entity YAML or notes in a side drawer

Useful for:
- understanding a complex project before editing
- locating circular dependency errors
- tracking task progress across entities

---

## Schema Explorer

The **Schema Explorer** page lets you browse the table and column structure of connected data sources.

Use it to:
- confirm column names before configuring an entity
- explore available tables in a connected database
- understand source data structure before writing SQL

Requires at least one data source to be connected.

---

## Query Tester

The **Query Tester** page lets you run SQL queries against connected data sources.

Use it to:
- test SQL before adding it to an entity
- explore data quality in source tables
- verify joins and filters

Requires at least one data source to be connected.

---

## Backups

Use backups before:

- large YAML refactors
- bulk operations
- schema restructuring

Access backups via the **Backups** button in the project header. Restoring replaces the current project YAML with the selected version.

---

## Materialized Entities

An entity can be materialized — its output is cached to disk instead of recalculated on every preview or execution.

When to materialize:
- the entity's source data is slow to query
- the source is no longer available but the output is stable
- execution time needs to be reduced

The entity shows a **Materialized** badge when cached output is in use. Use the unmaterialize action to clear the cache and return to live queries.

---

## Foreign Keys

Always declare foreign keys explicitly.

Benefits include:

- clearer documentation
- improved validation
- stronger conformance checking
- future compatibility

---

# 12. YAML Editing

## When to Use YAML Editing

Use raw YAML editing when:

- bulk changes are required
- advanced directives are needed
- form editing is insufficient
- debugging configuration problems

---

## YAML Editor Features

The YAML editor supports:

- syntax-aware editing
- reload from disk
- direct save
- partial validation

---

## Best Practices

- validate frequently
- save before major edits
- use backups before refactors
- preview after structural changes

---

# 13. Automation and CLI

## Why Use the CLI?

The command-line interface is useful for:

- automation
- CI/CD
- batch processing
- scheduled execution
- headless environments

---

## Basic Usage

```bash
python -m src.shapeshift OUTPUT_PATH --project PROJECT_FILE.yml
```

---

## Common Examples

### Export to Excel

```bash
python -m src.shapeshift output.xlsx \
  --project data/projects/my_project.yml \
  --mode xlsx
```

---

### Validate Only

```bash
python -m src.shapeshift output.xlsx \
  --project data/projects/my_project.yml \
  --validate-then-exit
```

---

## Common CLI Options

| Option | Purpose |
|---|---|
| `--project` / `-p` | Project YAML file path |
| `--mode` / `-m` | Output format: `xlsx`, `csv`, `db` (default: `xlsx`) |
| `--default-entity` / `-de` | Override the default entity name |
| `--env-file` / `-e` | Load environment variables from a file |
| `--verbose` / `-v` | Enable detailed logs |
| `--translate` / `-t` | Apply translation rules |
| `--drop-foreign-keys` / `-d` | Remove FK columns from output |
| `--log-file` / `-l` | Write log output to a file |
| `--validate-then-exit` | Validate configuration only, then exit |

---

# 14. Troubleshooting

## Project Will Not Save

Possible causes:

- concurrent editing conflict
- invalid YAML
- failed validation

Try:

1. refresh project
2. rerun validation
3. reopen editor
4. save again

---

## Entity Preview Shows No Data

Check:

- source selection
- uploaded files
- SQL correctness
- filters removing all rows
- missing data sources

---

## Validation Fails

Start with YAML validation first.

Fix structural problems before investigating data validation.

---

## Execute Succeeds but Output Looks Wrong

Review:

- foreign keys
- unnest logic
- replacement rules
- translation settings
- export options

---

## Need to Undo Changes?

Use the **Backups** feature to restore an earlier version.

---

# 15. FAQ

## Should I use Graph or Entities to edit?

Use:

- **Entities** for routine editing
- **Graph** for dependency analysis and navigation

---

## Why is `system_id` read-only?

Because Shape Shifter manages it internally for stable relationships.

---

## What does the Materialized badge mean?

The entity uses cached output instead of recalculating live results.

---

## What does the External badge mean?

The entity loads values from external storage rather than inline YAML.

---

## Can I paste spreadsheet data into a fixed entity?

Yes.

The fixed editor supports rectangular spreadsheet pasting.

---

## Where do I upload source files?

Use the **Files** tab.

---

## Where do shared database connections come from?

They are managed outside the project and connected through **Data Sources**.

---

# 16. Additional Documentation

## User-Oriented References

- USER_GUIDE_APPENDIX.md
- RECONCILIATION_WORKFLOW.md
- TARGET_MODEL_GUIDE.md

---

## Technical References

- CONFIGURATION_GUIDE.md
- DESIGN.md
- DEVELOPMENT.md
- CHANGELOG.md

---

## Release Notes

User-facing release notes are published in:

```text
docs/whats-new/
```

These focus on:

- visible improvements
- workflow changes
- upgrade notes
- new features

---

**Audience**: End Users, Data Managers, Integrators
**Focus**: Workflow-Oriented User Documentation

