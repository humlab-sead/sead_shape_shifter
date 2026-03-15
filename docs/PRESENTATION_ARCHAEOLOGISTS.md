---
marp: true
theme: default
paginate: true
backgroundColor: #fff
backgroundImage: url('https://marp.app/assets/hero-background.svg')
header: 'Shape Shifter - Archaeologist Overview'
footer: 'SEAD Development Team | March 2026'
---

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter
## Short Overview for Archaeologists

From local research data to SEAD-ready structure

**SEAD Development Team**
March 2026

---

## What This Talk Covers

1. Why data preparation is difficult
2. What Shape Shifter does
3. What the workflow looks like
4. How validation and reconciliation help
5. Why this matters in practice

---

## The Usual Problem

Archaeological data often starts life in:

- spreadsheets
- local databases
- project-specific exports
- naming conventions that make sense locally

But SEAD needs:

- clear structure
- explicit relationships
- stable identifiers
- reproducible transformation steps

---

## Why This Takes So Much Time

The work is never just “import the file”.

Usually it means:

- renaming fields
- splitting one table into several entities
- linking records correctly
- checking what values should match SEAD authorities
- repeating the same cleanup for every dataset

---

## What Shape Shifter Is

Shape Shifter is foremost a **workflow engine** for transforming data from a source model to a target model.
The workflow os driven by reusable configuration and supported by an interactive editor.

In practical terms, it aids in:

- describing a transformation once
- validating it
- previewing the result
- reusing the configuration later on

---

## The Main Idea

You create a reusable project that describes:

- where the data comes from
- how it should be reshaped
- how records relate to each other
- how local values should connect to SEAD identities
- how the final result should be exported or dispatched

---

## Typical Workflow

```text
Open or create a project
  -> connect files or data sources
  -> define entities
    -> define properties
    -> define transformations
    -> define relationships
  -> preview and validate
  -> reconcile important identities
  -> execute the workflow and export or dispatch the result
```

---

## What Users See

The current workspace includes tabs for:

| Tab          | Description                  |
|--------------|------------------------------|
| Entities     | List entities in the project |
| Graph        | View the entity graph        |
| Reconcile    | Reconcile data to SEAD       |
| Validate     | Validate project             |
| Dispatch     | Dispatch data                |
| Data Sources | Link project to data source  |
| Files        | List and add new data files  |
| YAML         | Project YAML editor          |

---

## Why the Graph Matters

The graph view shows how entities depend on one another.

It helps to:

- see the overall structure of a project
- understand processing order
- open entities directly from the graph
- track work by entity type or task status
- show from where entities get their data

---

## Why Validation Matters

Validation checks whether the configuration and the data make sense.

Current validation helps detect:

- broken references
- missing columns, missing data
- relationship problems
- structural mistakes

That reduces trial-and-error and catches problems earlier.

---

## Why Reconciliation Matters

Some data may already exist in SEAD. We must ensure uniqueness.

For example:

- a site may already exist in SEAD - we need to find the site identity
- a taxon probably exist in SEAD - we need to find the taxon ID
- the same reconciliation is need for other data

Shape Shifter supports reconciliation workflows using an OpenRefine compatible API.
Shape Shifter talks to SEAD Authoritative Service
---

## What This Means in Practice

Without a managed workflow:

- transformation knowledge is not persisted
- repeat deliveries require repeated effort
- QA is harder
- identity resolutions are difficult to trace

With Shape Shifter:

- the workflow becomes explicit (YAML)
- the same configuration can be reused
- review happens before ingest
- transformation choices remain visible over time

---

## What Shape Shifter Is Not

It is not just:

- a spreadsheet importer
- a YAML editor
- a one-off conversion script

It is a  workflow for turning provider's data into SEAD compliant data.

---

## Why This Matters for Archaeologists

The benefit is that it becomes easier to:

- prepare datasets consistently
- explain how the data was transformed
- hand work over between people
- revisit a dataset later without starting from scratch
- connect local research data to a larger shared system

---

## Suggested Live Demo

For this audience, the clearest demo path is:

1. Open a real project
2. Show the graph and one entity
3. Preview a transformation
4. Show validation feedback
5. Show a reconciliation example
6. Execute or export the result

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter
## A reusable workflow for preparing archaeological data for SEAD

Questions?