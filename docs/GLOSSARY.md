# Glossary

## 1. Data Import and Target Domain

### Source Data

The data read from an external file, table, or service before Shape Shifter transforms it.

### Source Model

The structure and meaning of the source data as it is understood before import.

### Target Model

The structure Shape Shifter prepares data for in the downstream system.

### Target Schema

The field and relationship layout expected by the downstream system.

### Import

The process of bringing source data into Shape Shifter so it can be validated and transformed.

### ETL

Extract, Transform, Load: the general data movement pattern Shape Shifter follows.

### Mapping

The set of rules that connect source fields and records to target fields and records.

### Validation

The checks Shape Shifter runs to confirm data meets required rules before or during transformation.

### Provenance

Information about where a value came from and how it was produced or chosen.

### Identifier

A value used to distinguish one record from another.

### Record

A single item of data, usually one row in a table or one object in a source file.

## 2. Shape Shifter Transformation Concepts

### Shape Shifting

The process of transforming source data into the target model.

### Pipeline

The ordered sequence of steps Shape Shifter runs to transform data.

### Import Specification

The project configuration that describes what data to read and how to process it.

### Mapping Specification

The part of the configuration that describes how source values map to target values.

### Entity/Attribute/Value Mapping

A mapping pattern that links an entity, one of its fields, and the value that should be used in the target model.

### Transformation Rule

A rule that changes, filters, combines, or assigns data during processing.

### Resolver

A component that looks up or derives the correct value when a direct source value is not enough.

### Identity Resolution

The process of deciding which target record a source record should match.

### Foreign Key Resolution

The process of finding the correct parent record for a related child record.

### Staging

An intermediate step where data is prepared before final loading or export.

### Dry Run

A run that shows what would happen without writing final output changes.

### Import Report

A summary of what was imported, transformed, matched, and written.

### Error Report

A summary of problems found during validation or transformation.

## 3. Implementation and Architecture Concepts

### Adapter

A component that converts between Shape Shifter and an external format or service.

### Parser

A component that reads structured input and turns it into internal data structures.

### Transformer

A component that changes data from one shape to another.

### Loader

A component that reads source data for use in the pipeline.

### Repository

A storage layer that reads or writes project or mapping data.

### Service

A component that coordinates application logic for a specific task.

### Configuration

The settings that define how a project or component should behave.

### Schema

The structure and type definition of data fields used by a component or file.

### CLI

The command-line interface used to run Shape Shifter tools.

### API

The programmatic interface exposed by the backend.

### Transaction

A group of related changes that succeed or fail together.

### Idempotency

The property of repeating an operation without creating extra unintended changes.

### Logging

Recording events and diagnostics so runs can be inspected and debugged.

### Test Fixture

A fixed test setup used to run repeatable checks.

### Integration Test

A test that checks multiple parts of the system working together.
