---
marp: true
theme: default
paginate: true
backgroundColor: #fff
backgroundImage: url('https://marp.app/assets/hero-background.svg')
header: 'Shape Shifter - System Overview'
footer: 'SEAD Development Team | March 2026'
---

<!--
This presentation uses Marp.

Suggested export commands:
  marp docs/PRESENTATION.md --html
  marp docs/PRESENTATION.md --pdf
  marp docs/PRESENTATION.md --pptx

Suggested visuals to add later:
  - Graph tab screenshot
  - Validation tab screenshot
  - Reconciliation workflow screenshot
  - Dispatch tab screenshot
-->

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter
## Current System Overview

Declarative data reconciliation for SEAD workflows

**SEAD Development Team**
March 2026

---

## Agenda

1. The data integration problem
2. What Shape Shifter is today
3. How the current workflow is organized
4. Core concepts: entities, identity, dependencies
5. Validation, reconciliation, execution, and dispatch
6. Architecture and extensibility
7. Current value for SEAD and data providers

---

# Part 1
# The Problem

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## The Real Integration Problem

Source data usually contains the right information in the wrong shape.

Common issues:

- Different file and database formats across providers
- Different naming conventions for the same concepts
- Local business keys instead of SEAD identifiers
- Wide spreadsheets that need normalization
- Implicit relationships that must become explicit foreign keys
- Repeated manual transformation work for every delivery

---

## What "Impedance Mismatch" Means Here

**Provider reality**

```text
sample_name | taxon_name | site_code | depth_cm
```

**SEAD-ready reality**

```text
sample_id | taxon_id | site_id | depth_cm
```

The gap is not just column renaming.

It includes:

- restructuring
- identity assignment
- reconciliation to authorities
- dependency management
- validation before ingest

---

## The Cost of Manual Work

For providers and project teams:

- slow onboarding of new datasets
- hidden logic in scripts and spreadsheets
- difficult QA and reproducibility
- repeated lookup work for controlled vocabularies
- hard-to-explain provenance when something goes wrong

For SEAD:

- inconsistent submission quality
- more manual review
- slower time from delivery to usable data

---

# Part 2
# What Shape Shifter Is Now

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Shape Shifter in One Sentence

Shape Shifter is foremost a workflow engine for transforming data from a source model to a target model, driven by reusable configuration and supported by an interactive editor backed by a Python engine.

---

## Current Product Surface

Shape Shifter currently includes:

- A reusable workflow engine for model-to-model data transformation
- A Vue 3 web editor for project work
- A FastAPI backend for project services and validation
- A Python transformation core for normalization and export
- YAML-based project definitions as the source of truth
- Project sessions, version checks, and backups
- Graph, validation, reconciliation, dispatch, files, metadata, and raw YAML workflows

---

## End-to-End Workflow

```text
Define project
  -> connect sources and files
  -> configure entities and relationships
  -> preview and validate
  -> reconcile identities
  -> execute normalization
  -> dispatch or export results
```

This is no longer just a YAML editor.

It is a full project workspace for transformation lifecycle management.

---

## Current Project Workspace

The project detail view is organized around tabs:

- **Entities**: create, edit, duplicate, preview entities
- **Graph**: dependency visualization and graph-based editing workflows
- **Reconcile**: identity matching and review workflows
- **Validate**: structural and data validation with issue review
- **Dispatch**: send processed data to configured targets
- **Data Sources**: connect shared/global sources to the project
- **Metadata**: maintain project metadata and defaults
- **Files**: upload project-local CSV and Excel files
- **YAML**: power-user editing of the full project file

---

# Part 3
# Core Concepts

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Core Concept: Project

A Shape Shifter project is a YAML file that describes:

- metadata
- entities
- relationships
- source connections
- transformations
- reconciliation rules
- execution and dispatch configuration

The file is both:

- a transformation specification
- a durable record of how the data was prepared

---

## Core Concept: Entity

An entity is a logical dataset in the pipeline.

Supported entity types in the current system:

- `entity` for derived data from another entity
- `sql` for query-based extraction from a data source
- `fixed` for static values
- `csv` for delimited files
- `xlsx` for Excel via pandas
- `openpyxl` for Excel workflows with sheet/range support

Entities can also define:

- keys
- public IDs
- foreign keys
- filters
- unnest operations
- append rules
- extra columns
- value replacements

---

## Core Concept: Three-Tier Identity

Shape Shifter uses three identity layers:

1. **system_id**
   The local sequential identifier used internally for relationships.

2. **keys**
   Business keys used for matching, deduplication, and joins.

3. **public_id**
   The target-facing identifier column name used in exports and mappings.

Critical rule:

All internal foreign key relationships use local `system_id` values, not external SEAD IDs.

---

## Core Concept: Dependency-Aware Processing

Entities are processed in dependency order.

Dependencies come from:

- explicit `depends_on`
- foreign key references
- entity source relationships

Current behavior includes:

- topological sorting
- cycle detection
- graph visualization of dependencies
- warning surfaces for circular dependencies

---

# Part 4
# Editing and Visualization

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Entity Editing Today

The entity workflow supports both guided editing and power-user control.

Current editing modes:

- form-based editing for common configuration tasks
- YAML editing for advanced control
- split view for editing and preview side by side
- preview-first inspection when testing changes

Entity editing is no longer limited to raw configuration management.

It is supported by validation, preview, and graph navigation.

---

## Graph Tab: Current Capabilities

The graph view is now a real working surface, not just a diagram.

Implemented capabilities include:

- Cytoscape-based dependency graph
- hierarchical, force, and saved custom layouts
- color by entity type or task status
- show or hide labels and edge categories
- optional source and source-entity visibility
- cycle warnings and dependency statistics
- PNG export

---

## Graph Tab: User Interactions

Users can work directly from the graph:

- click nodes to open a quick drawer
- double-click to open full entity editing
- Ctrl/Cmd + double-click to jump to entity YAML editing
- right-click for context actions
- create task-list placeholder nodes
- duplicate or delete entities from graph context
- inspect task completion directly on nodes

This makes the graph a coordination tool for both configuration and workflow tracking.

---

## Data Sources, Files, and Schema Exploration

Current source-side capabilities include:

- project-local file upload for CSV and Excel assets
- shared/global data source configuration
- PostgreSQL, SQLite, and MS Access connectivity
- schema inspection and table discovery
- query testing against configured sources

This means Shape Shifter supports both file-centric and database-centric onboarding workflows.

---

# Part 5
# Quality and Confidence

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Validation Is a First-Class Workflow

Validation is a dedicated workspace, not an afterthought.

Current validation surface includes:

- structural validation of project configuration
- data validation against actual loaded data
- grouped issue reporting by severity and entity
- project-level and entity-level review
- issue preview before applying fixes

The goal is to catch problems before they reach SEAD ingestion.

---

## Current Validation Modes

Two practical validation modes are available:

- **sample mode** for fast checks using preview-sized data
- **complete mode** for more comprehensive validation of the full workflow output

This supports two different needs:

- quick iteration while editing
- higher confidence before execution or dispatch

---

## Validation Review and Auto-Fix Support

Current workflow support includes:

- review issues by category and severity
- inspect entity context before changing configuration
- preview proposed fixes before applying them
- apply fix sets with backup support

Important framing:

Shape Shifter can propose and apply some fixes, but it is still a review-driven workflow rather than blind automation.

---

## Preview Before Commitment

Entity preview is a core confidence tool.

Current preview capabilities include:

- row preview inside entity editing workflows
- cached preview results for faster iteration
- dependency-aware preview refresh
- statistics and table inspection during editing

The current backend uses a 3-tier cache strategy:

- TTL
- project version
- entity hash

---

# Part 6
# Reconciliation and Identity Matching

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Reconciliation Is the SEAD Bridge

Reconciliation is where local values are linked to authoritative external identities.

Typical examples:

- site names to SEAD site records
- taxa to taxon identifiers
- methods or vocabularies to controlled records

This is one of the most important differences between simple transformation and real SEAD integration.

---

## Current Reconciliation Workflow

Shape Shifter currently supports:

- OpenRefine-compatible reconciliation services
- reconciliation specs in project configuration
- automatic matching with confidence thresholds
- review queues for uncertain matches
- manual acceptance and mapping persistence

Typical threshold pattern:

- high confidence: auto-accept
- medium confidence: review
- low confidence: manual follow-up

---

## Why Reconciliation Matters Operationally

Without reconciliation:

- identity lookups are manual
- ambiguity handling is inconsistent
- mappings live in side spreadsheets or personal notes

With reconciliation in Shape Shifter:

- matching rules become explicit
- review becomes structured
- accepted mappings are retained with the project workflow

This reduces both time cost and institutional memory risk.

---

# Part 7
# Execution and Dispatch

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Execution vs Dispatch

The current system separates two related concepts.

**Execute**

- runs the normalization workflow
- produces validated, processed outputs
- supports export-oriented workflows

**Dispatch**

- sends processed data to a downstream target
- uses ingester configuration defined in the project
- supports target-specific operational policies

This distinction helps keep transformation and delivery concerns clear.

---

## Current Output and Dispatch Surface

Implemented output and dispatch capabilities include:

- file-based export workflows
- database-oriented output workflows
- dispatcher-based execution in the core
- ingester-based dispatch in the application layer
- SEAD Clearinghouse-oriented integration patterns

The system is explicitly designed to be extensible here rather than hard-coded to one target.

---

## Dispatch and Ingester Architecture

Current design uses a plugin-style ingester model.

This means:

- dispatch logic can be added without rewriting the whole application
- project configuration can select target-specific behavior
- SEAD-specific integration can evolve independently of general transformation logic

This is important for long-term maintainability and for adding future downstream targets.

---

# Part 8
# Architecture and Extensibility

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Current Architecture

```text
Browser UI
  -> Vue 3 + Pinia + Monaco + Cytoscape
  -> FastAPI backend
  -> Python transformation core
  -> files, databases, reconciliation services, target systems
```

Three major layers:

- **Frontend** for editing, graphing, validation review, and workflow control
- **Backend** for project services, mappers, preview, validation, and orchestration
- **Core** for transformation pipeline execution

---

## Current Pipeline

The transformation core follows the current pipeline:

1. Extract
2. Filter
3. Link
4. Unnest
5. Translate
6. Store

This sequencing matters because relationships, reshaping, and naming all depend on upstream phases being resolved correctly.

---

## Why the Layering Matters

Current architecture deliberately separates:

- API models used for editing and transport
- mapper logic used for resolution and translation
- core models used for execution

This separation gives the system:

- cleaner testing
- clearer boundaries
- safer environment-variable handling
- reuse of the core outside the UI

---

## Extensibility Points Already in Use

The system already uses registry and plugin patterns for:

- data loaders
- validators
- filters
- dispatchers
- ingesters

This means Shape Shifter is not just a fixed application.

It is a platform with extension points that are already part of the running architecture.

---

# Part 9
# Operational Value

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## What This Changes for Teams

Shape Shifter moves work from ad hoc transformation toward **managed** transformation.

Benefits for data providers and project teams:

- repeatable workflows instead of one-off scripts
- clearer review surfaces before ingest
- documented reconciliation and mapping decisions
- lower onboarding cost for new datasets
- easier handover across people and projects

---

## What This Changes for SEAD

Benefits for SEAD operations:

- more consistent incoming structure
- earlier detection of quality problems
- explicit relationship and identity handling
- better provenance of transformation decisions
- a clearer bridge between provider data and SEAD-ready outputs

---

## The Current Strategic Position

Shape Shifter is already more than a transformation script runner.

It is now:

- a project workspace
- a validation surface
- a reconciliation workflow
- a graph-based dependency explorer
- a dispatch platform

That makes it a strong foundation for operational SEAD data onboarding.

---

## Suggested Demo Flow

For a live walkthrough, the current best path is:

1. Open a real project
2. Show the Graph tab and dependency overview
3. Open an entity from the graph
4. Preview and validate a change
5. Show reconciliation configuration and review state
6. Show Execute and Dispatch entry points
7. End in the YAML tab to demonstrate transparency

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter
## From manual wrangling to managed data transformation

Questions?
