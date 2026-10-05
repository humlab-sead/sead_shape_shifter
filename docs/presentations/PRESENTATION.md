---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
header: 'Shape Shifter | System overview'
footer: 'SEAD Project Team | October 2026'
style: |
  section {
    font-family: Aptos, "Segoe UI", sans-serif;
    font-size: 25px;
    color: #263747;
  }
  h1, h2 {
    color: #173b57;
  }
  h2 {
    border-bottom: 3px solid #2b8a8f;
    padding-bottom: 0.15em;
  }
  strong {
    color: #1f6d73;
  }
  table {
    font-size: 0.78em;
  }
  footer {
    color: #667085;
    font-size: 14px;
  }
---

<!--
This presentation uses Marp.

Export commands:
  marp docs/presentations/PRESENTATION.md --html
  marp docs/presentations/PRESENTATION.md --pdf
  marp docs/presentations/PRESENTATION.md --pptx
-->

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter

## System overview

Reusable, reviewable data transformation for structured research data

**SEAD Project Team · October 2026**

---

## The integration problem

Research data arrives in different shapes:

- Spreadsheets, files, and databases use different layouts.
- The same concept may have different names in each source.
- Local identifiers do not match target-system identifiers.
- Relationships and required target fields may be implicit.
- One-off scripts make decisions difficult to review and repeat.

Shape Shifter makes those transformation steps explicit and reusable.

---

## What Shape Shifter does

Shape Shifter turns source data into structured output that follows a target model.

It brings together:

- A Python engine that processes configured data entities.
- A browser-based project editor for configuration and review.
- Previews and validation to find problems during preparation.
- Reconciliation tools for linking local values to authoritative records.
- Export and ingester workflows for delivering processed data.

It is used for SEAD workflows and can support other structured-data targets.

---

## A project is a reusable transformation definition

A project records:

- Which files and data sources to read.
- How to shape entities and connect their relationships.
- How to handle local keys and target identifiers.
- Which target model and validation rules apply.
- How to produce or deliver the result.

Most users work through the editor. The project definition is stored as YAML and can also be edited directly.

---

## A typical project workflow

**Connect sources** → **Model entities** → **Preview and validate** → **Review identity mappings** → **Execute** → **Export or dispatch**

The workflow is iterative. Users can preview and validate while they configure a project, then run complete checks before producing a delivery.

---

## Bring source data into a project

Common inputs include:

- CSV and Excel files uploaded to a project.
- PostgreSQL, SQLite, and MS Access data sources.
- Fixed values and project-managed lookup data.
- Results from other entities in the same project.

Entities describe logical tables in the transformation. They define source data, output columns, keys, relationships, and transformations.

---

## Shape data through ordered steps

The core processes entities in this order:

**Extract → Filter → Link → Unnest → Translate → Store**

- Extract rows from a file, database, or earlier project result.
- Filter rows and link related entities.
- Unnest repeated values and reshape rows.
- Translate column names and values for the target.
- Store the processed entity for output.

Dependencies determine when each entity can be processed.

---

## Keep local and target identity clear

| Identity | Use |
|---|---|
| **system_id** | Local row ID used for foreign-key relationships during processing |
| **keys** | Business values used to match and deduplicate records |
| **public_id** | Target-facing ID column used in exported data |

Internal foreign keys use the parent entity's local system_id. External target IDs are handled separately through public_id and reviewed mappings.

---

## Describe what the target expects

A project can reference a target model specification that describes:

- Required entities and columns.
- Required foreign-key relationships.
- Naming conventions and data constraints.
- Identity handling for target entities.

Conformance validation compares the project with that specification before execution or dispatch. A target model can be shared across projects or tailored to a specific destination.

---

## Validate as you prepare data

Shape Shifter checks different parts of a project:

- **Configuration checks** find invalid structure and references.
- **Data checks** inspect processed rows, required columns, keys, and relationships.
- **Conformance checks** compare the result with the selected target model.

Sample validation supports quick iteration. Complete validation checks the full workflow output. Results are grouped so users can review issues by entity and severity.

---

## Review identity matches and mappings

Reconciliation helps connect local values, such as site or taxon names, to authoritative records.

1. Generate or search for candidate matches.
2. Review uncertain candidates and adjust choices.
3. Commit accepted links to the project mapping catalog.
4. Apply committed mappings during normalization.

The mapping catalog is stored alongside the YAML project and records the source and review status of links. Draft links do not affect normalization until committed.

---

## Execute, export, and dispatch

**Execute** runs the normalization workflow and produces processed output. Supported output workflows include CSV, Excel, and database destinations.

**Dispatch** sends processed output through a configured ingester. The SEAD Clearinghouse ingester supports validation and loading into its staging and public data structures.

Execution and delivery are separate steps, so teams can inspect output before submitting it.

---

## The Project Editor supports the workflow

The project workspace includes:

- **Entities** — configure and preview project data.
- **Dependencies** — inspect relationships and processing order.
- **Reconciliation** — configure matching and review mappings.
- **Validation** — run checks and review issues.
- **Dispatch** — send processed data through a configured ingester.
- **Data Sources, Metadata, Files, and YAML** — manage project inputs and configuration.

The editor combines guided forms with direct YAML editing for advanced work.

---

## How the system fits together

- **Project Editor (Vue 3):** edit, preview, validate, and dispatch.
- **FastAPI backend:** project services, sessions, authorization, and project-to-core mapping.
- **Python transformation core:** ordered processing, data loaders, validators, and output dispatchers.
- **Integrations:** files and databases, authority services, output files, and ingesters.

The editor calls the backend through a REST API. The backend maps project configuration for the Python core.

---

## Access is scoped to users and resources

- Authenticated users receive permissions for projects and shared data sources.
- Project access and shared-source access are managed separately.
- Application-level roles control operations such as running ingesters.
- Authorization changes are recorded for review.

This lets teams share project work while keeping access to source data and delivery operations controlled.

---

## Extend the system through registered components

Shape Shifter uses registries for components such as:

- Data loaders for new source types.
- Validators for additional project and data checks.
- Transformations and output dispatchers.
- Ingesters for downstream delivery workflows.

New integrations can be added while the project workflow and core processing order remain consistent.

---

## What this changes for teams

- Providers can describe a transformation once and reuse it for later deliveries.
- Data managers can review mappings and validation results before delivery.
- Integrators can see how entities relate and how IDs are assigned.
- SEAD teams receive more consistent, inspectable submissions.
- Project configuration keeps transformation choices available for handover and future work.

---

## Suggested demonstration

1. Open a project and review its entity dependencies.
2. Preview an entity and show a transformation.
3. Run validation and inspect a reported issue.
4. Review a reconciliation match and its committed mapping.
5. Run complete validation, then execute and inspect the output.
6. Show the dispatch workflow and the project YAML.

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter

## From source data to reviewed, reusable data deliveries

Questions?
