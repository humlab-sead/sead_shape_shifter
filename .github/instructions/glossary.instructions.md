---
description: "Maintain docs/GLOSSARY.md: key Shape Shifter terms for import, transformation, and implementation."
applyTo: "docs/GLOSSARY.md"
---------------------------

# AI Agent Instructions for `GLOSSARY.md`

Maintain a concise glossary for **Shape Shifter**, a general ETL/model-transformation system.

Do not frame Shape Shifter as SEAD-specific. Use **target model**, **target schema**, **target ERD**, or **downstream system**. SEAD may appear only as an example.

## Structure

Use exactly:

```markdown id="55zscc"
# Glossary

## 1. Data Import and Target Domain
## 2. Shape Shifter Transformation Concepts
## 3. Implementation and Architecture Concepts
```

## Scope

**1. Data Import and Target Domain**
Plain-language terms for stakeholders and curators: source data, source model, target model, target schema, import, ETL, mapping, validation, provenance, identifier, record.

**2. Shape Shifter Transformation Concepts**
Project-specific transformation terms: shape shifting, pipeline, import specification, mapping specification, entity/attribute/value mapping, transformation rule, resolver, identity resolution, foreign key resolution, staging, dry run, import report, error report.

**3. Implementation and Architecture Concepts**
Developer terms only when project-relevant: adapter, parser, transformer, loader, repository, service, configuration, schema, CLI, API, transaction, idempotency, logging, test fixture, integration test.

## Entry Format

Use this format:

```markdown id="0bgn5u"
### Term

**Definition:** Short explanation in Shape Shifter context.

**Context:** Optional. Add only when it clarifies project-specific usage.
```

## Rules

* Keep entries concise.
* Prefer Shape Shifter meaning over textbook meaning.
* Use `Context` only when it adds useful clarification.
* Merge synonyms under one preferred term.
* Mark unclear definitions as provisional.
* Do not list every class, function, or file.
* Include only terms useful to users or maintainers.
