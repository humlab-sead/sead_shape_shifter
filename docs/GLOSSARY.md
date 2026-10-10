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

### Directives

YAML-level instructions such as `@include:`, `@value:`, and `${ENV_VAR}` that are resolved at the API-to-Core conversion boundary. Core models receive resolved values, not raw directives.

### Three-Tier Identity System

Shape Shifter's identity model: (1) `system_id` for internal references, (2) `keys` for business-key matching and deduplication, (3) `public_id` for target schema column names that hold SEAD IDs after mapping. These Shape Shifter fields are distinct from the SEAD ID, SIMS UUID, and source-key roles described below.

### system_id

A local sequential integer that serves as the primary key for all Shape Shifter entities. Used for all internal foreign-key relationships. Never exposed as a target-system identity.

### Business Keys

Human-meaningful identifiers that uniquely distinguish an entity within a domain, such as a site code or scientific name. Used for matching and deduplication in the keys tier of the three-tier identity system.

### Authoritative Fixed Column Ordering

**Definition:** The one column order Shape Shifter uses for a fixed entity's rows: the managed identity columns first (`system_id`, then `public_id` when the entity defines one), followed by the entity's produced data columns in their declared order. Business keys describe produced fields and add no positions.

**Context:** This is the order exposed as `fixed_schema.full_columns` in entity responses. Stored values, values requests, and the editor grid must match it position for position. A stored file holding the same columns in another order is reordered on read without being written; a values request in another order is rejected. Use this full term rather than the shorter "authoritative order", which is ambiguous.

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

### Foreign Key

A relationship between entities using local `system_id` values. Foreign keys never use external IDs as internal reference values. The child column uses the parent's `public_id` as its column name.

### SEAD Internal ID

**Definition:** The integer or bigint primary key used for relational storage in a SEAD table, such as `site_id`.

**Context:** SIMS does not map its identities to SEAD tables or columns and does not enforce uniqueness in the SEAD database. SEAD consumes SIMS-issued aggregate identity values under the SIMS–SEAD trust contract. This is not Shape Shifter's local `system_id`.

### SIMS Tracked UUID

**Definition:** The stable UUID SIMS assigns to one tracked aggregate identity.

**Context:** SIMS stores the UUID with the entity-scoped aggregate identity value and its scoped source identities. SEAD's use of those values is governed by the trust contract.

### Source Identity Keys

**Definition:** Business, provider, and authority identifiers recorded within a source scope and used to identify or reconcile incoming records.

**Context:** SIMS links source identities to a tracked aggregate identity. Source keys are not SIMS-minted aggregate identity values.

### SIMS Identity Mapping

**Definition:** SIMS's record associating an entity type, its SIMS-issued aggregate identity value, its tracked UUID, and scoped source identities.

**Context:** SIMS uses a generic mechanism configured by entity type and guarantees uniqueness within its own identity store. SIMS does not map identity values to SEAD tables or columns or guarantee uniqueness in SEAD.

## 4. SEAD and Identity Concepts

### SEAD

Strategic Environmental Archaeology Database. The target system for Shape Shifter. A relational database with specific identity, reconciliation, and modeling requirements.

### Shape Shifter

The normalization and transformation engine. Converts source data into SEAD-compatible formats using project YAML configuration, validation, and reconciliation workflows.

### SIMS

Scientific Identity Management Service. The owner of tracked aggregate identities and scoped source-identity associations. Shape Shifter prepares reconciliation inputs; SEAD consumes SIMS-issued aggregate identity values under a trust contract.

### SEAD Authoritative Service

An existing SEAD-facing service that Shape Shifter calls during reconciliation workflows. Provides authority lookups for specific entity types and fields.

### Reconciliation

The process of matching incoming data against existing SEAD records or external authoritative services. Determines whether to create new records, update existing ones, or merge duplicates.

### Authority Keys

Identifiers assigned by an external identity authority, such as a taxonomic naming authority. Used to link local records to official external identities.

### Provider Keys

Identifiers assigned by the data provider or source system. May differ from official SEAD identities and require reconciliation or authority lookup.

### Tracked Entities

Entities with stable, long-term identity that are followed across imports and reconciliations. Contrasted with shared metadata and child values.

### Shared Metadata

Classifiers, categories, or reference data that are shared across multiple entities. Have stable identity and should be reconciled rather than duplicated.

### Child Values

Data objects that do not have independent identity. They exist only as part of a parent entity and are not reconciled or tracked separately.

### Ownership

A parent-child relationship where the child's identity and lifecycle are tied to the parent. Deleting the parent affects the child. Contrasted with association.

### Association

A relationship between independently meaningful entities. The child entity has its own identity and lifecycle, separate from the parent. Contrasted with ownership.

### Conformance Validation

Validation against an active target model specification. Checks whether a project exposes the required entities, columns, foreign-key relationships, and naming rules for the target system.
