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
4. Select a registered **Data Provider** and one of its **Provider Schemas**.
5. Click **Create**, then open the new project.

The provider and schema must be a registered pair. If the provider list cannot be loaded or contains no entries, the dialog disables project creation until the registry is available.

### Assign a Pair to an Existing Project

An existing project without a provider pair can receive its first assignment in the **Metadata** tab. Select a registered provider and one of its schemas, then save. After the assignment succeeds, both values are shown as read-only. Application saves and raw YAML edits cannot change or remove the pair; direct file changes require repository review.

Projects already checked into the repository may remain unbound until the planned Phase 4 migration. Run **YAML Validation** to see missing, partial, blank, or unregistered provider values reported under project metadata.

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

| Tab            | Purpose                                    |
|----------------|--------------------------------------------|
| Entities       | Create and manage entities                 |
| Dependencies   | Visualize entity dependency graph          |
| Reconciliation | Configure and run reconciliation           |
| Validation     | Run validation workflows                   |
| Dispatch       | Run the ingester to deliver processed data |
| Data Sources   | Connect shared database sources            |
| Metadata       | Edit project metadata                      |
| Files          | Upload local files                         |
| YAML           | Edit raw project YAML directly             |

---

## Global Navigation

The sidebar provides access to top-level pages:

| Page            | Purpose                                               |
|-----------------|-------------------------------------------------------|
| Projects        | Create and open projects                              |
| Data Sources    | Manage shared database connections                    |
| Schema Explorer | Browse database table and column structure            |
| Query Tester    | Run SQL queries against connected data sources        |
| Data Ingestion  | Run registered ingesters to load data into a database |
| Settings        | Application preferences                               |
| What's New      | Recent release notes                                  |

## Header Actions

| Button       | Purpose                                           |
|--------------|---------------------------------------------------|
| Execute      | Run the normalization workflow and produce output |
| Backups      | View and restore earlier project versions         |
| Refresh      | Reload project state from disk                    |
| Save Changes | Save current edits                                |

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

| Mode         | Purpose                   |
|--------------|---------------------------|
| Form Only    | Focused editing           |
| Split View   | Edit and preview together |
| Preview Only | Inspect transformed data  |

Shortcut:

- `Ctrl+Shift+P` toggles split view

---

## Entity Editor Tabs

| Tab           | Purpose                      |
|---------------|------------------------------|
| Basic         | Core settings                |
| Foreign Keys  | Relationship configuration   |
| Filters       | Row filtering                |
| Unnest        | Wide-to-long transformations |
| Append        | Concatenate data             |
| Replace       | Value replacement rules      |
| Extra Columns | Add derived fields           |
| YAML          | Raw configuration editing    |

---

## Reshape Data with Unnest

Use the **Unnest** tab to turn wide data (one column per measurement) into long data (one row per measurement). It reshapes the table with a melt operation.

The tab has two column lists that behave differently:

| Setting             | What happens to these columns                                                                 |
|---------------------|-----------------------------------------------------------------------------------------------|
| **ID Variables**    | Retained and repeated. The values are copied onto every generated row, so each row keeps its identifier. |
| **Value Variables** | Reshaped and removed. Their names become rows in the variable-name column, their values become rows in the value-name column, and the original columns no longer appear in the output. |

Value-variable columns are consumed by the reshape. Do not add them to **ID Variables** to keep them; listing a column there stops it being melted and changes the result.

If you leave **Value Variables** empty, every column that is not an ID variable is melted.

**Example.** With `site_id` as an ID variable and `KoordX`, `KoordY`, and `KoordZ` as value variables, one row becomes three:

```
| site_id | coordinate_type | coordinate_value |
|---------|-----------------|------------------|
| 1       | KoordX          | 100              |
| 1       | KoordY          | 200              |
| 1       | KoordZ          | 50               |
```

To keep an original value beside the melted result, add a copy of the column first (for example an alias under **Extra Columns**) and list the copy under **ID Variables**. The copy is retained and repeated on each row; the original is still melted.

For the full `unnest` field reference, see [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md).

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

| Type     | Purpose                            |
|----------|------------------------------------|
| entity   | Derived entity from another entity |
| sql      | Query-based entity                 |
| fixed    | Inline static values               |
| merged   | Combined multi-source entity       |
| csv      | CSV or TSV file import             |
| xlsx     | Excel import via Pandas            |
| openpyxl | Excel import with range support    |

---

## Fixed Entities

Use `fixed` entities for:

- lookup tables
- small controlled vocabularies
- manually curated lists
- frozen cached values

The fixed editor supports spreadsheet-style pasting.

### Fixed Row Order and Business Keys

The fixed grid shows the schema Shape Shifter uses for the stored rows:

- Managed identity fields lead the grid: `system_id`, then the entity's `public_id` when it has one.
- Produced data fields follow in their configured order.
- Business keys label fields that already exist in the grid. Adding a key does not add a grid column, and a key that no produced field matches is reported by validation.

If a fixed entity stores its values in a separate file (an `@load:` directive), the editor loads those rows into the same displayed order. When the values file columns cannot be matched to the displayed schema, the editor shows an error and disables saving instead of writing rows into the wrong fields.

### Edit a Fixed Entity

Use this workflow when you need to maintain a lookup table directly in the project:

1. Open the entity in the editor.
2. Paste or type values into the fixed grid.
3. Review any validation messages shown in the grid.
4. Save the project.
5. Run validation before executing the full workflow.

### Partial Saves and Mapping Retry

Saving a fixed entity updates the mapping sidecar when the saved rows change a linked ID or row key. The mapping sidecar is a separate file, so the rows can be saved while the mapping update does not happen. When that occurs, the editor reports a partial save instead of a full success:

- The editor shows **Rows saved; mapping changes pending** and a **Retry mapping** button.
- **Save & Close** keeps the dialog open while changes are pending.
- The pending result is retained until the retry succeeds or you close and reopen the editor.

Use these steps to recover:

1. Click **Retry mapping**. Shape Shifter applies only the recorded mapping changes; it does not resend the rows.
2. If the retry succeeds, the pending notice is replaced by the usual save confirmation.
3. If the retry reports a conflict, the editor lists the changed keys under the notice. Review the current rows and mapping links for those keys, adjust them, and retry, or reload the entity.

A retry does not change rows or links at unaffected keys, so edits you made elsewhere while the mapping was pending are preserved.

### What Happens to `_id` Columns

Fixed entities treat columns ending in `_id` as integers by default.

This matters in two common situations:

- If you paste a quoted integer such as `"53"`, the editor normalizes it to `53` when it can do so safely.
- If a project is loaded with coercible fixed-entity values, the project page shows a **Load-Time Normalizations Detected** warning banner.

When that banner appears, Shape Shifter has normalized values in memory only. Save the project if you want those normalized values written back to YAML.

### When to Use `column_types`

Most fixed entities work without extra type configuration. Add `column_types` in YAML only when a fixed column should be treated as something other than the default:

- `_id` columns default to `int`
- other fixed columns default to `string`
- declare `column_types` when a column should be `int`, `float`, `bool`, or `date`

Use the configuration reference for the exact YAML format and allowed values: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md).

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

# 8. Reconciliation and Mapping

## What Is Reconciliation?

Reconciliation links local source values to authoritative target-system records.

Examples:

- taxon names
- site names
- method names
- vocabulary terms

---

## How Mappings Are Stored

Reconciled ID links and manual overrides are persisted in a **mapping sidecar file** (`<project>-mapping.yml`) stored alongside `shapeshifter.yml`. This file is the single source of truth for all entity ID mappings.

Shape Shifter blocks renaming an entity that has a mapping entry, including an entry with no links. Ask a project maintainer to move or remove that entry before renaming the entity.

Legacy `options.mappings` in `shapeshifter.yml` is no longer used for new projects.

The mapping sidecar stores per-entity links with full provenance:

- **source**: who or what created the link (`manual`, `reconciliation`, `import`)
- **committed_at**: when the link was finalized (null = draft, not yet applied)
- **confidence**: match confidence (0.0–1.0)
- **created_by / reviewed_by**: audit trail

## Mapping Precedence

During normalization, mappings are applied in this order (first match wins):

1. **Manual overrides** (`source: "manual"`, committed) — highest priority
2. **Reconciliation exports** (`source: "reconciliation"`, committed)
3. **Imported links** (`source: "import"`, committed)
4. **Draft links** (`committed_at: null`) — skipped, not applied

## Reconciliation Workflow

1. Configure reconciliation specs in the **Reconciliation** tab
2. Select entity and field
3. Run auto-reconcile
4. Review matches in the review grid
5. Accept or adjust mappings
6. **Export** accepted links to the mapping sidecar
7. Links in the sidecar are applied during normalization

## Materialized Entity Edits

When editing a materialized entity and assigning `public_id` values:

- Saving fixed rows updates links for ID or row-key changes and adds a missing link for a saved non-blank ID. Links at unaffected keys keep their source and details, even when a saved `public_id` is blank or older.
- During normalization, committed manual links take precedence over reconciliation and imported links.

Use **Sync from materialized entity** in Mapping Sidecar Management to seed or repair links from all saved rows. A request without options adds links only where no link exists and keeps every existing link. To rebuild manual links and remove stale manual entries, explicitly set `replace_manual_links` to `true`. A rebuilt link can replace another source at the same key because the sidecar stores one link per key.

## Mapping Sidecar Management

The sidecar file supports full CRUD via API endpoints:

| Action                        | Endpoint                                                       |
|-------------------------------|----------------------------------------------------------------|
| List links for entity         | `GET /projects/{project}/mapping/{entity}`                     |
| Get single link               | `GET /projects/{project}/mapping/{entity}/{key}`               |
| Create/update link            | `PUT /projects/{project}/mapping/{entity}/{key}`               |
| Sync from materialized entity | `PATCH /projects/{project}/mapping/from-materialized/{entity}` |
| Retry pending fixed-entity mapping | `PATCH /projects/{project}/mapping/retry-fixed-entity/{entity}` |
| Commit draft links            | `POST /projects/{project}/mapping/commit`                      |
| Delete link                   | `DELETE /projects/{project}/mapping/{entity}/{key}`            |
| Export to CSV                 | `GET /projects/{project}/mapping/export?format=csv`            |
| Import from CSV               | `POST /projects/{project}/mapping/import`                      |

## Reconcile Tab Areas

| Area               | Purpose                        |
|--------------------|--------------------------------|
| Configuration      | Define reconciliation specs    |
| YAML               | Edit raw reconciliation config |
| Reconcile & Review | Interactive review grid        |

---

# 9. Execute and Export

## What Execute Does

Execute runs the normalization workflow and produces output.

---

## Common Output Types

| Type             | Dispatcher |
|------------------|------------|
| CSV Folder       | csv        |
| ZIP CSV          | zipcsv     |
| Excel            | xlsx       |
| Excel (advanced) | openpyxl   |
| Database         | db         |

---

## Recommended Execution Workflow

1. Save changes
2. Run complete validation
3. Execute export
4. Review output
5. Dispatch if needed

---

## Execution Options

| Option               | Purpose                       |
|----------------------|-------------------------------|
| Run validation first | Validate before processing    |
| Apply translations   | Apply mapping rules           |
| Drop FK columns      | Remove FK columns from output |

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

| Action             | Where                  | Purpose                                                                                                     |
|--------------------|------------------------|-------------------------------------------------------------------------------------------------------------|
| **Execute**        | Header button          | Runs the normalization pipeline and produces output files (CSV, Excel, ZIP, or database)                    |
| **Dispatch**       | Project → Dispatch tab | Runs a configured ingester directly from the project workspace to deliver processed data to a target system |
| **Data Ingestion** | Top-level page         | Runs any registered ingester independently of a project                                                     |

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

Use [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for field names, entity types,
identity rules, relationships, directives, and valid YAML examples. This guide
only covers when and why to switch from form editing to YAML.

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

## Change Request Stops Because a Link Is Missing

A change request stops before it writes any output when a submitted row has no usable link to a related record. A typical example is a new location row with no location type.

Shape Shifter links a row to a related record in two steps. It looks the related record up among the rows in your submission, and it writes the target system's ID for that record into the link column. The link fails when either step has nothing to work with.

The message wording is technical. Use it to identify the cause and who can resolve it:

| If the message mentions | The cause is | Resolved by |
|------------------------|--------------|-------------|
| a missing link column, or a missing link | The project does not connect the two entities, so the link column is never produced | The project owner |
| a missing value | A cell in the source data is empty | The data provider |
| a value that is unresolved, or that could not be found | The value does not match any row in the related data | The data provider |
| a related entity that could not be found | The related data was not part of this submission | The project owner or the data provider |

To resolve it:

1. Read the entity, column, and related entity names in the message. They name the link that failed.
2. Check that the related rows are present in the submission.
3. Check that the link values are filled in and spelled the same way as the related rows.
4. If the link column is missing from the submission entirely, ask the project owner to connect the two entities.
5. Re-run validation after fixing the source data. Correcting values does not need a project change.

Some submissions do not need link values at all. When every row matches a record that already exists in the target system, Shape Shifter inserts nothing and does not require the link. This is why the same project can report a link error for one submission and accept another.

For the rule that decides when a link is required, see [TARGET_MODEL_GUIDE.md](TARGET_MODEL_GUIDE.md).

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

After pasting:

1. Check the grid for validation problems.
2. Review `_id` columns carefully, because they are treated as integers by default.
3. Save the project if you want normalized values to be persisted back to YAML.

If the project shows **Load-Time Normalizations Detected**, Shape Shifter has already normalized coercible fixed values in memory while loading the project.

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
