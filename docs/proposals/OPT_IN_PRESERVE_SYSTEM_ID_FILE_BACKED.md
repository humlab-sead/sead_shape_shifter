# Proposal: Opt-in Preservation of system_id for File-Backed Reference Entities

## Problem

Currently, Shape Shifter enforces that only fixed entities may declare a `system_id` column in their configuration. However, some curated reference tables (e.g., `relative_ages` loaded from Excel) require preservation of externally assigned `system_id` values for stable cross-project identity and mapping. The runtime sometimes preserves these IDs if present, but this is not an explicit, validated, or documented feature for file-backed entities. This leads to ambiguity, validation errors, and potential data integrity issues.

## Objective

Introduce an explicit, validated opt-in mechanism to allow file-backed reference entities (e.g., loaded via openpyxl, csv) to preserve externally curated `system_id` values. This will:
- Enable stable identity for reference tables curated outside Shape Shifter
- Prevent accidental acceptance of user-supplied IDs without review
- Maintain strict validation and integrity for all other entity types

## Proposed Solution

### 1. Configuration Model
- Add a new boolean field `preserve_source_system_id` to the entity config model (YAML, Pydantic, API), defaulting to `false`.
- Only allow this field for file-backed entity types (`openpyxl`, `csv`, possibly `sql` with explicit opt-in).
- Document the field in the configuration guide and schema.

### 2. Validation Rules
- Update entity validation (src/specifications/entity.py):
  - If `preserve_source_system_id: true` is set, allow `system_id` in `columns` for file-backed entities.
  - Enforce strict integrity checks: all values must be unique, non-null, and sequentiality is not required but must not conflict with runtime-generated IDs.
  - For all other entities, continue to block user-supplied `system_id`.

### 3. Runtime Behavior
- Update data loading pipeline (src/model.py, add_system_id_column):
  - If `preserve_source_system_id: true`, do not overwrite or reassign `system_id` values from the source file.
  - If false or not set, generate `system_id` as usual.
- Ensure downstream processes (linking, mapping, export) treat these IDs as authoritative for the entity.

### 4. Project Mapping and Round-Trip
- Update backend/app/mappers/project_mapper.py to support round-tripping the new flag between YAML, API, and core models.
- Ensure the flag is preserved in project save/load cycles.

### 5. User Experience and Documentation
- Document the new field and its intended use in CONFIGURATION_GUIDE.md.
- Add warnings in validation output if the field is used without meeting integrity requirements.
- Provide clear error messages if the field is set on unsupported entity types.

### 6. Testing
- Add regression and property-based tests for:
  - Validation: acceptance and rejection of system_id in various scenarios
  - Runtime: correct preservation and usage of source IDs
  - Round-trip: config, API, and YAML consistency

## Out of Scope
- No changes to fixed entity handling (remains as-is)
- No support for user-supplied system_id in non-reference, non-file-backed entities

## Risks and Mitigations
- **Risk:** Users may set the flag without understanding the implications.
  - **Mitigation:** Strict validation, clear documentation, and warnings.
- **Risk:** Data integrity issues if source IDs are not unique or non-null.
  - **Mitigation:** Validation enforces uniqueness and non-null constraints.

## Alternatives Considered
- Continue implicit preservation (status quo): rejected due to ambiguity and lack of validation.
- Allow for all entity types: rejected due to high risk of integrity violations.

## Acceptance Criteria
- File-backed reference entities can opt-in to preserve source `system_id` via config
- Validation and runtime behavior are consistent and robust
- Documentation and tests are updated

---

**Author:** GitHub Copilot
**Date:** 2026-03-26
