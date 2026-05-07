# Proposal: Target Model Conformance Enhancements

## Status

**Active — backlog.** Core conformance engine (Milestones 1–3) is complete. This proposal tracks the remaining deferred and future work gathered from five now-archived source documents.

## Implementation Checklist

### Validators
- [x] `required_entity` — required entities present in the project
- [x] `public_id` — `public_id` present and matches spec
- [x] `foreign_key` — required FK targets present on project entities
- [x] `required_columns` — required columns present
- [x] `naming_convention` — `public_id` values end with configured suffix
- [x] `induced_requirements` — optional entity present → its required FK targets are induced-required (transitive)
- [x] `source_type_appropriateness` — classifiers should not use `type: entity`
- [ ] `no_orphan_facts` — fact entities must have a required FK path to at least one required lookup
- [ ] `semantic_mismatch` — entity name role disagrees with `public_id` role (Phase 4, high false-positive risk)
- [ ] `schema_aware_append` — appended columns conform to target model column spec

### Data Conformance Validators
- [ ] `nullable` — required-not-null columns must have no null values in produced data
- [ ] `type_compatibility` — column values must be compatible with the declared logical type (integer, string, date, …)
- [ ] `fk_referential_integrity` — FK values must exist in the parent entity's output

See [Target-Model-Aware Data Conformance](#target-model-aware-data-conformance) for design rationale and implementation notes.

### Format Extensions
- [ ] `format_version` field in `model:` block
- [ ] `generated: true` flag on `ColumnSpec` (suppress missing-column warnings for auto-generated columns)
- [ ] `allowed_values` / `type: enum` on `ColumnSpec`
- [x] Richer FK semantics — bridge entity support via `via` attribute in FK spec
- [ ] Advanced FK validation modes — `direct`, `transitive`, explicit path constraints
- [ ] Entity spec inheritance (`extends:`) — defer until 5+ target models exist

### Test Coverage
- [ ] Target model spec parsing — valid, invalid, round-trip
- [ ] `@include:` resolution at mapper boundary (inline dict, file ref, missing file, relative path)
- [ ] Projects without target model — structural validation unaffected, conformance returns empty
- [ ] Missing target model file — graceful 422, not 500
- [x] Backend adapter integration — `TargetModelValidator` code mapping, endpoint response, category tagging
- [ ] Warning vs error severity (Phase 4 checks)

### Infrastructure
- [ ] Rule disabling via `options.validation.disabled_rules`
- [ ] `GlobalConformanceValidator` base type for multi-entity checks
- [ ] `TargetModelService` — extract loading/caching when remote refs become real
- [x] Target model YAML editor tab — raw YAML edit tab for the project's **project-local** target model file alongside the project YAML tab
- [x] Monaco editor schema support for target model YAML files — autocomplete and IntelliSense using `targetModelSchema.json`

### Tooling / Ecosystem
- [x] Target model documentation downloads — Project-aware HTML/Markdown/Excel documentation accessible from UX
- [ ] Target model diff report (version upgrade planning)
- [ ] Remote target model references (SSRF-safe, with caching)
- [ ] Curated target model registry (bundled YAML short-name resolution)

### SEAD spec coverage (`resources/target_models/sead_standard_model.yml`)
- [x] Abundance chain — `abundance`, `abundance_element`, `abundance_element_group`, `abundance_modification`, `modification_type`, `abundance_property`
- [x] Dating — `relative_dating`, `relative_ages`, `geochronology` (abs/radiocarbon), `dating_lab`
- [x] Method/contacts — `method_group`, `citation` (`tbl_biblio`), `contact`, `contact_type`, `dataset_contact`
- [ ] Taxonomy — `taxa_tree_master` present; `taxonomic_order`, `ecocodes` still missing
- [ ] Data-type-specific tables (ceramics, dendrochronology, insects)

---

## Source Documents

This proposal consolidates deferred and future items from:

- `docs/proposals/done/TARGET_SCHEMA_AWARE_VALIDATION.md` — original validation proposal
- `docs/proposals/done/TARGET_SCHEMA_AWARE_VALIDATION_IMPLEMENTATION_SKETCH.md` — implementation sketch and phase plan
- `docs/proposals/done/TARGET_MODEL_SPECIFICATION_FORMAT.md` — format specification proposal
- `docs/proposals/done/SEAD_V2_IMPLEMENTATION_PLAN.md` — phased SEAD rollout plan
- `docs/proposals/done/TARGET_MODEL_CONFORMANCE_REFINEMENT.md` — conformance refinement notes

## What Is Already Implemented

Seven conformance validators are registered and active:

| Key                            | What it checks                                                                            |
|--------------------------------|-------------------------------------------------------------------------------------------|
| `required_entity`              | Required entities present in the project                                                  |
| `public_id`                    | `public_id` present and not unexpected                                                    |
| `foreign_key`                  | Required FK targets present on entities that are in the project (with bridge support)     |
| `required_columns`             | Required columns present                                                                  |
| `naming_convention`            | `public_id` values end with `naming.public_id_suffix`                                    |
| `induced_requirements`         | If optional entity X is present and has a required FK to Y, then Y is required (transitively) |
| `source_type_appropriateness`  | Classifiers (`role: classifier`) must use `type: fixed` or `type: sql`, not `type: entity` |

Backend wiring, frontend Check Conformance button, and Conformance panel in ValidationPanel are all live.

### Induced Requirements — Implementation Notes

`InducedRequirementConformanceValidator` (key: `induced_requirements`) uses breadth-first search (BFS) over the required-FK graph:

- **Seed:** every entity that is present in the project and not globally required
- **Traversal:** follow `required: true` FK edges; report each absent, non-globally-required target as `MISSING_INDUCED_REQUIRED_ENTITY`; continue BFS through absent nodes for transitive closure
- **Guard:** globally-required targets are skipped — the `required_entity` validator covers them independently
- **No execution order needed:** transitivity is handled inside a single validator pass; there is no inter-validator dependency

**Example:** `abundance` (present) → `taxon` (absent, required FK) → `taxon_group` (absent, required FK). Both `taxon` and `taxon_group` are reported in one pass.

Issue code: `MISSING_INDUCED_REQUIRED_ENTITY`

### Bridge Entity Support — Implementation Notes

`ForeignKeyConformanceValidator` (key: `foreign_key`) now supports many-to-many relationships mediated by bridge entities using the `via` attribute.

**Format:**

```yaml
# In target model specification
site:
  role: lookup
  foreign_keys:
    - entity: location        # Ultimate target
      via: site_location      # Bridge entity mediating the relationship
      required: true
```

**Validation Logic:**

When a FK spec includes `via: bridge_entity`, the validator performs two checks:

1. **Bridge presence**: The bridge entity must be present in the source entity's FK targets
2. **Bridge completeness**: The bridge entity should have a FK to the ultimate target entity

**Issue codes:**
- `MISSING_BRIDGE_ENTITY` — Bridge entity not present in source entity's FK targets
- `BRIDGE_MISSING_TARGET_FK` — Bridge entity exists but doesn't have FK to ultimate target

**Example scenario:**

Target model declares: `site → location (via: site_location)`

Project configuration:
```yaml
site:
  foreign_keys:
    - entity: site_location    # ✅ Bridge present
      local_keys: [site_id]
      remote_keys: [site_id]

site_location:
  foreign_keys:
    - entity: location         # ✅ Bridge has FK to ultimate target
      local_keys: [location_id]
      remote_keys: [location_id]
```

**Validation outcome:** ✅ Pass — bridge relationship properly configured

**Rationale:**

Many-to-many relationships are common in relational models. The `via` attribute makes bridge patterns explicit in the target model specification, enabling validators to understand transitive FK relationships without requiring deep graph traversal. This documents intent and prevents false positives when the direct FK relationship doesn't exist.

### Advanced FK Validation Modes — Future Enhancement

The current bridge entity support (`via` attribute) handles the most common many-to-many pattern. Future enhancements could add more flexible FK validation modes to handle complex relationship patterns.

**Proposed FK validation mode attributes:**

```yaml
# Mode 1: Direct FK only (no transitive relationships allowed)
entity_a:
  foreign_keys:
    - entity: entity_b
      direct: true          # Must be a direct FK, fail if only transitive path exists
      required: true

# Mode 2: Bridge-mediated (current implementation)
entity_a:
  foreign_keys:
    - entity: entity_c
      via: bridge_entity    # Must go through specific bridge entity
      required: true

# Mode 3: Transitive FK (any path allowed)
entity_a:
  foreign_keys:
    - entity: entity_d
      transitive: true      # Can be satisfied by any FK chain (BFS/DFS walk)
      required: true
      max_depth: 3          # Optional: limit transitive search depth

# Mode 4: Explicit path constraint
entity_a:
  foreign_keys:
    - entity: entity_e
      path: [intermediary_1, intermediary_2]  # Must follow specific FK chain
      required: true
```

**Validation strategies:**

1. **Direct mode** (`direct: true`)
   - Default if no mode specified
   - Check that target entity appears in source's immediate FK targets
   - Reject transitive paths

2. **Bridge mode** (`via: bridge_name`)
   - Current implementation ✅
   - Validate bridge presence in direct FK targets
   - Validate bridge has FK to ultimate target

3. **Transitive mode** (`transitive: true`)
   - BFS/DFS graph walk through FK graph
   - Accept any valid FK chain from source to target
   - Optional `max_depth` to prevent infinite loops
   - Performance consideration: may require full FK graph construction

4. **Explicit path mode** (`path: [...]`)
   - Validate that each entity in path has FK to next entity
   - Strictest validation: only accept specified route
   - Use case: documenting canonical FK traversal paths

**Implementation considerations:**

- **Mutual exclusivity**: Only one mode per FK spec (enforced by Pydantic validators)
- **Default behavior**: No mode specified = `direct: true` (backward compatible)
- **Performance**: Transitive and path modes require FK graph access (may need `ProcessState` or equivalent)
- **False positive risk**: Transitive mode may be too permissive; use with caution

**Deferred until:**
- Real-world use cases demonstrate need for modes beyond `via`
- FK graph structure is stable and available at validation time
- Performance implications of graph traversal are analyzed

---

## Advanced Semantic Validation (Phase 4)

These items were labeled "Phase 4 — Advanced Semantic Rules" in the implementation sketch. None are implemented.

### Semantic Mismatch Detection

Detect when an entity's name implies a different semantic role than its `public_id` style.

**Motivating example:** An entity named `relative_dating` (implies a fact) using `public_id: relative_age_id` (implies a lookup). The mismatch is detectable without running the pipeline.

**Approach:**
- Classify entity names using heuristics (noun patterns, role keywords)
- Classify `public_id` values using suffix patterns
- Emit `UNEXPECTED_PUBLIC_ID` or a new `SEMANTIC_ROLE_MISMATCH` code when name-role and id-role disagree
- Keep detection conservative: only emit for clear, low-noise cases

**Prerequisite:** Define the heuristic threshold before implementing. Avoid false positives at all cost.

### Global Role-Informed Checks

Check global modeling requirements that depend on understanding the *combination* of entity roles.

**Candidate rule:** `no_orphan_facts` — a fact entity must be linked (directly or transitively) to at least one required lookup entity. A fact with no FK path to any required parent is likely misconfigured.

**Implementation note:** BFS over the required-FK graph is already implemented in `InducedRequirementConformanceValidator`. A `GlobalConformanceValidator` base type and the `no_orphan_facts` rule can reuse that traversal pattern. The FK graph walk no longer needs `ProcessState` as a prerequisite.

### Source-Type Appropriateness

Classifiers declared with `role: classifier` should use `type: fixed` or `type: sql` rather than `type: entity`. Emit a warning when a classifier is configured as a row-extraction entity.

**Difficulty:** Low. Single-pass check against entity type field.

### Schema-Aware Append Conformance

When a project uses append mode, validate that the appended columns conform to the target-model column spec for that entity. Currently append operations are not checked against the target model at all.

### Branch-Aware Semantic Validation

When a merged-parent entity has branch children, validate that each branch covers a non-overlapping slice. Depends on branch modeling being more concrete. Defer until branch proposals stabilize.

---

## Target Model YAML Editor Tab

The project-level YAML view currently shows only the `shapeshifter.yml` file. When a project references a `target_model:` file, add a second tab in that same view for editing the target model spec YAML directly.

**Status:** Tab implementation is complete. Monaco editor schema support for autocomplete is also complete.

**Completed:**
- ✅ Target model YAML editor tab with nested tabs UI
- ✅ Monaco editor schema integration for autocomplete and IntelliSense
- ✅ Automatic schema generation from Pydantic models via `scripts/generate_schemas.py`

**Constraints:**
- Raw YAML only — no structured form or entity-level UI.
- Tab visible only when the project has a `target_model:` reference that resolves to a **project-local file** (i.e. the `@include:` path lives inside the project's own directory). Shared/global spec files (e.g. `resources/target_models/sead_standard_model.yml`) are read-only in this view.
- API passes the YAML file content as raw text; the server validates syntax but **never re-serialises** it, so comments and formatting survive the round-trip.
- Save writes directly to the referenced target model YAML file.
- Changing the file triggers a re-run of conformance validation (same as editing the project YAML).

**Scope:**
- Frontend: add a second `<v-tab>` to the project YAML panel; reuse the existing Monaco YAML editor component. ✅ **COMPLETE**
- Backend: expose a `GET /api/v1/target-models/{name}` and `PUT /api/v1/target-models/{name}` endpoint pair for raw YAML read/write, mirroring the existing project file endpoints. ✅ **COMPLETE**
- Monaco schema support: Generate JSON Schema from `src/target_model/models.py` and wire into Monaco YAML editor for autocomplete. ✅ **COMPLETE**

### Monaco Editor Schema Support (Completed)

The Monaco YAML editor now provides autocomplete and IntelliSense for target model specification files.

**Implementation:**

1. **Schema Generation** (`scripts/generate_schemas.py`)
   - Extended to generate `targetModelSchema.json` from `src.target_model.models.TargetModel` Pydantic model
   - Outputs to `frontend/src/schemas/targetModelSchema.json` (5.6KB, JSON Schema Draft 7)
   - Includes all target model constructs: `EntitySpec`, `ColumnSpec`, `ForeignKeySpec`, `NamingConventions`, `ModelMetadata`, `GlobalConstraint`

2. **Monaco YAML Intelligence** (`frontend/src/composables/useMonacoYamlIntelligence.ts`)
   - Added `'target-model'` mode alongside `'project'` and `'entity'` modes
   - Imports and configures `targetModelSchema.json` for Monaco YAML autocomplete
   - Schema selected based on editor mode

3. **YAML Editor Component** (`frontend/src/components/common/YamlEditor.vue`)
   - Extended `mode` prop to accept `'target-model'`
   - Passes mode through to Monaco intelligence setup

4. **ProjectDetailView Integration** (`frontend/src/views/ProjectDetailView.vue`)
   - Target model YAML tab now uses `mode="target-model"` for schema-aware editing
   - Users get autocomplete for entity roles (`fact`, `lookup`, `classifier`, `bridge`), column specs, FK definitions, etc.

**Autocomplete Coverage:**
- Entity `role` options (fact, lookup, classifier, bridge)
- Entity specs: `required`, `description`, `domains`, `target_table`, `public_id`, `identity_columns`, `unique_sets`, `foreign_keys`
- Column specs: `required`, `type`, `nullable`, `description`
- Foreign key specs: `entity`, `required`
- Naming conventions: `public_id_suffix`
- Model metadata: `name`, `version`, `description`

**Remaining Work:**

Backend endpoints for read/write operations remain to be implemented (see sections below).

### Complexity Assessment

**Overall rating: Low–Medium. Estimated ~200–250 lines total across 4–5 files.**

---

#### Backend (Low) — TO DO

Two new endpoints modelled directly on the existing `GET/PUT /projects/{name}/raw-yaml` pattern (~60–80 lines):

Two new endpoints modelled directly on the existing `GET/PUT /projects/{name}/raw-yaml` pattern (~60–80 lines):

```
GET /api/v1/target-models/{name}   → { yaml_content: str }
PUT /api/v1/target-models/{name}   ← { yaml_content: str }  → Project (after reload)
```

Work items:
1. **Path resolution + locality check** — extract the file path from the `@include: ...` string in `project.metadata.target_model`. Resolve it relative to the project directory and confirm it is *inside* that directory (simple `Path.is_relative_to()` check). Return 403 if the path escapes the project directory (shared/global spec).
2. **Inline-dict guard** — return 422 when `target_model` is an inline dict (no backing file to edit).
3. **File read/write (text passthrough)** — read and write the file as raw text (`Path.read_text` / `Path.write_text`). On PUT: validate YAML syntax with `yaml.safe_load()` to catch parse errors, then write the *original* submitted string unchanged — never re-serialise through PyYAML, so comments and blank lines are preserved.
4. **Cache invalidation** — call `project_service.load_project(name, force_reload=True)` (or the existing `refresh` path) after write so subsequent conformance runs see the updated spec.

No new models, no new services, no router changes beyond adding the two route functions and registering them in `api.py`.

---

#### Frontend (Low–Medium) — PARTIALLY COMPLETE

**Completed:**
1. ✅ **Monaco schema integration** — `targetModelSchema.json` generated and wired into Monaco YAML editor with `mode="target-model"`
2. ✅ **Editor mode support** — `YamlEditor` component accepts `mode="target-model"` and configures autocomplete accordingly
3. ✅ **Target model tab UI** — nested tabs structure in place with target model YAML editor
4. ✅ **State management** — `targetModelYaml`, `targetModelYamlHasChanges`, `targetModelYamlLoading`, `targetModelYamlSaving` refs exist in `ProjectDetailView.vue`

**Remaining work:**
1. **API methods** — add `getTargetModelYaml(projectName)` and `updateTargetModelYaml(projectName, yaml)` to `frontend/src/api/projects.ts` (~15 lines, identical shape to `getRawYaml`/`updateRawYaml`).
2. **Backend integration** — wire load/save handlers to actual API endpoints once backend routes are implemented (~20 lines).
3. **Conditional visibility** — refine tab visibility logic to check `isProjectLocal` flag from backend response.

The core Monaco editing experience with autocomplete is fully functional. Only API integration remains.

---

#### Risk / Complications

| Item                                | Risk       | Notes                                                                                                     |
|-------------------------------------|------------|-----------------------------------------------------------------------------------------------------------|
| `@include:` path root resolution    | Low        | One existing precedent in `Config.resolve_includes()`; target model path is always repo-root-relative     |
| Project-local check                 | Low        | `Path.is_relative_to(project_dir)` — one line; non-local paths return 403                                 |
| Comment-preserving write            | Low        | Never call `yaml.dump()` on PUT; validate with `yaml.safe_load()` then write the submitted bytes verbatim |
| Inline-dict guard                   | Low        | One `isinstance` check; clear 422 response                                                                |
| Cache invalidation                  | Low        | `project_service.refresh()` already exists and is called by the reload button                             |
| Nested `<v-tabs>` inside YAML panel | Low–Medium | Vuetify nested tabs work fine; just more template boilerplate                                             |

---

## Target-Model-Aware Data Conformance

### Problem

Current conformance validates what the project **promises to produce** — configuration-level facts evaluated without running the pipeline. It cannot catch cases where the project is structurally valid but the produced data violates target-model contracts such as:

- A `required: true, nullable: false` column containing null values in the output
- An integer column containing string values
- A FK value that has no corresponding row in the parent entity's output

These require executing or previewing the normalization pipeline to evaluate.

### Design Decision: Keep Structural and Data Conformance Separate

|                 | Structural conformance (current)  | Data conformance (proposed)                      |
|-----------------|-----------------------------------|--------------------------------------------------|
| Input           | `ShapeShiftProject` config        | `DataFrame` output                               |
| When to run     | Every save / YAML edit            | On demand (preview or full run)                  |
| Speed           | Milliseconds                      | Seconds–minutes                                  |
| Failure meaning | Project cannot produce valid data | Pipeline ran but output violates target contract |
| Fix action      | Edit YAML configuration           | Fix source data or mapping logic                 |

Mixing them would break the fast-feedback loop: structural conformance fires on every save; data checks cannot.

**Data conformance is an extension of data validation, not of structural conformance.**

### Architecture

Data conformance validators follow the existing pure-domain pattern: static methods receiving a `DataFrame` and an `EntitySpec`, returning `list[ValidationIssue]`. No infrastructure dependencies.

```python
# src/validators/target_model_data_validators.py

class NullabilityConformanceValidator:
    @staticmethod
    def validate(df: pd.DataFrame, entity_spec: EntitySpec, entity_name: str) -> list[ValidationIssue]:
        """Check required-not-null columns have no nulls in produced data."""
        issues = []
        for col_name, col_spec in (entity_spec.columns or {}).items():
            if col_name not in df.columns:
                continue  # structural validator's job
            if col_spec.nullable is False and df[col_name].isna().any():
                null_count = int(df[col_name].isna().sum())
                issues.append(ValidationIssue(
                    severity="error",
                    entity=entity_name,
                    field=col_name,
                    message=f"Column '{col_name}' has {null_count} null value(s) but target model requires non-null",
                    code="TARGET_NULL_VIOLATION",
                    suggestion="Check source data or mapping for missing values",
                ))
        return issues

class TypeCompatibilityConformanceValidator:
    @staticmethod
    def validate(df: pd.DataFrame, entity_spec: EntitySpec, entity_name: str) -> list[ValidationIssue]:
        """Check column dtypes are compatible with declared logical types (warnings only)."""
        ...

class FKReferentialIntegrityConformanceValidator:
    @staticmethod
    def validate(
        child_df: pd.DataFrame,
        parent_df: pd.DataFrame,
        fk_spec: ForeignKeySpec,
        entity_name: str,
    ) -> list[ValidationIssue]:
        """Check FK values in child DataFrame exist in parent DataFrame (post-link)."""
        ...
```

### Orchestration

The `DataValidationOrchestrator` already fetches DataFrames via an injected `DataFetchStrategy`. Extend the orchestrator to also call target-model data validators when the resolved `core_project` has a `target_model`:

```python
async def validate_all_entities(...) -> list[ValidationIssue]:
    # ... existing data validators ...

    # Additional: target-model data conformance (if project has a target model)
    target_model = getattr(core_project.cfg.get("metadata", {}), "target_model", None)
    if target_model and isinstance(target_model, dict):
        for entity_name, entity_spec in target_model.get("entities", {}).items():
            df = await self.fetch_strategy.fetch(project_name, entity_name)
            issues += NullabilityConformanceValidator.validate(df, entity_spec, entity_name)
            issues += TypeCompatibilityConformanceValidator.validate(df, entity_spec, entity_name)
```

No new UI trigger is needed. Data conformance fires as part of the existing **Validate Data** run. The results appear in the same data validation panel under the entity's section.

### FK Referential Integrity

FK checks run best post-normalization (all entities linked). They fit into the `FullDataFetchStrategy` path where `table_store` is available. For preview-based runs, skip FK integrity checks (preview data is a sample, not the full output).

### Type Compatibility

The `ColumnSpec.type` field uses logical types (`integer`, `string`, `boolean`, `date`, `datetime`, `decimal`, `enum`). Emit **warnings**, not errors — type coercions happen legitimately during normalization. Only emit an error if the dtype is clearly incompatible (e.g. object column containing mixed non-numeric values where `integer` is declared).

### Deferred

- `allowed_values` / enum value checks — depends on `allowed_values` field in `ColumnSpec` (not yet in format)
- Row-count constraints — out of scope (the format deliberately does not express cardinality requirements)

---

## Alias and Normalization Heuristics

These were documented in `TARGET_MODEL_CONFORMANCE_REFINEMENT.md` as "not yet safe for integration because they generate too many false positives."

### Alias Matching

A project may use `sample_type_name` where the target model declares `type_name`. The names differ but refer to the same concept. A soft validator could detect likely aliases and suggest re-mapping rather than reporting a hard error.

**Why deferred:** Requires a similarity metric or curated alias table. No clean false-positive threshold yet.

### Semantic Normalization

Some column names include a redundant entity prefix. For example, `sead_method_group_id` could be normalized to `method_group_id`. Target models canonicalize to the short form, but projects often emit the long form.

**Approach when ready:** Add a `name_normalization` block to the target model spec listing known equivalences. Use only for warnings, never errors.

### Transitive FK Satisfaction

A project may satisfy a required FK transitively through an intermediate entity not named in the target model. The current FK conformance validator only does direct matching.

**Example:** Target model requires `sample → site`. Project has `sample → sample_group → site`. The requirement is satisfied transitively but would currently fail.

**Approach when ready:** Add a BFS/DFS walk through the project FK graph to find transitive paths to required FK targets.

### Value-Level Checks

Any conformance check requiring knowledge of actual column values (e.g., `allowed_values` verification, `@value:` expression interpretation) must wait until after pipeline execution. These cannot be done at configuration time.

**Placement when ready:** These belong in the data validation orchestrator, not the conformance engine.

---

## Format Extensions

These open questions were deferred from `TARGET_MODEL_SPECIFICATION_FORMAT.md`.

### Schema-Qualified Target Table Names

Should `target_table` support `public.tbl_locations` style names?

**Recommendation:** No in v1. The conformance engine validates entity names, not physical table locations. If schema qualification becomes important for ingestion checks, introduce it as an optional `schema` field alongside `target_table` rather than embedding it in the table name string.

### Entity Spec Inheritance / Mixins

Should target models support `extends:` to share column sets across entity specs?

**Assessment:** YAGNI for v1. The current SEAD model has enough repetition to feel painful but not enough to justify the parser complexity. Revisit after 5+ target models exist.

### `format_version` Field

A `format_version` field alongside `model.version` would allow the parser to reject incompatible target model files cleanly.

**Recommendation:** Add `format_version: "1"` to the top-level `model:` block in a minor update. No behavior change in v1 — treat missing as `"1"`. Start enforcing with any breaking format change.

### Richer Foreign Key Semantics

The current FK spec (`entity`, `required`, `columns`) does not express join-column overrides. A target model cannot currently say "entity A must have an FK to entity B *on column X*".

**Defer until:** A real project requires this level of FK specification. The current spec is sufficient for required-entity-level checks.

### Allowed Values / Enum Support

Add `allowed_values` or `type: enum` to `ColumnSpec` for validating classifier content without running the pipeline.

**Prerequisite:** Align with any value-level validation design (see value-level checks above).

### Database Defaults and Generated Values

Should the target model spec record which columns have database defaults or are auto-generated?

**Recommendation:** Advisory only. Add an optional `generated: true` flag that validators can use to suppress "column not present in source" warnings. Not normative.

### Inheritance / Mixins for Entity Templates

Reusable entity templates would reduce repetition across target models that share common SEAD spine entities.

**Approach when ready:** Introduce a top-level `templates:` block. Entities use `extends: templates.base_lookup`. Expand at parse time before passing to validators.

---

## Test Coverage Gaps

These test areas were identified in the implementation sketch but not yet covered.

### Target Model Spec Parsing

- Parse valid YAML into `TargetModel` — all fields, optional fields omitted
- Parse invalid YAML — missing required `model.name`, unknown `role` value, malformed `columns`
- Round-trip: parse → serialize → re-parse produces equivalent object

### `@include:` Resolution (Backend Boundary)

- Inline `target_model: {...}` dict passes through mapper unchanged
- `target_model: "@include: resources/target_models/sead_standard_model.yml"` resolves to dict at mapper boundary
- Missing include file produces a clear error, not a cryptic KeyError
- Relative path resolution from project file location

### Projects Without Target Model

- Structural validation runs normally when `metadata.target_model` is absent
- Conformance endpoint returns empty result (not error) when no target model is set
- Adding `target_model: null` clears the reference cleanly

### Warning vs Error Severity (Phase 4)

- Semantic mismatch checks emit warnings, not errors
- Orphan-fact check is configurable (warning by default, error when `required: strict`)
- Severity can be overridden via `options.validation.severity_overrides`

### Missing Target Model File

- Graceful error (not uncaught exception) when referenced file does not exist
- Error message includes the file path that was not found
- Backend endpoint returns 422 with clear message, not 500

### Backend Adapter Integration

- `TargetModelValidator` wraps all `ConformanceIssue` codes into `ValidationError` correctly
- `validate_target_model()` endpoint returns 200 with issues array
- Conformance issues appear under `ValidationCategory.CONFORMANCE` in merged results

---

## Open Technical Questions

### 1. Target Model Loading Location

Should `ValidationService` load and parse the target model directly, or should there be a dedicated `TargetModelLoader` service?

**Current behaviour:** `ValidationService.validate_target_model()` extracts the resolved `target_model` dict from the mapped core project and passes it to `TargetModelConformanceValidator`.

**Question:** As target model loading gains complexity (caching, remote refs, registry lookups), should this be extracted to a `TargetModelService`?

**Recommendation:** Extract to `TargetModelService` when remote references or caching become real requirements. For now, keep it in `ValidationService`.

### 2. Validation Code Naming

Should conformance issue codes be prefixed with `TARGET_` (e.g., `TARGET_MISSING_REQUIRED_ENTITY`, `TARGET_PUBLIC_ID_NAMING_VIOLATION`)?

**Current state:** Codes like `MISSING_REQUIRED_ENTITY`, `PUBLIC_ID_NAMING_VIOLATION` have no prefix. With a `ValidationCategory.CONFORMANCE` category, the prefix may be redundant.

**Recommendation:** Add prefix when expanding to Phase 4. It makes log messages and issue exports unambiguous.

### 3. Rule Disabling

Should projects be able to suppress specific conformance rules?

**Proposal:** Via `options.validation.disabled_rules: ["naming_convention", "no_orphan_facts"]` in the project YAML.

**Current state:** No rule suppression exists. The conformance engine runs all registered validators unconditionally.

**Recommendation:** Implement when false-positive feedback from real projects accumulates. Design as an allow-list that strips matching validators from the registry copy used for that project.

---

## Future Enhancements

### Target Model Diff Tooling

When a target model version changes, provide a diff report showing which conformance checks are new, changed, or removed. Useful for upgrade planning.

**Approach:** Compare two `TargetModel` instances field-by-field. Output a structured diff as YAML or markdown.

### Remote Target Model References

Allow `target_model: "https://registry.example.com/sead/v2.yml"` in addition to `@include:` file references.

**Prerequisites:**
- SSRF prevention (allowlist of permitted domains or a local proxy)
- Caching with TTL to avoid network calls on every validation
- Version pinning to prevent silent breakage on upstream changes

**Recommendation:** Only implement if a shared community registry becomes real. Local file references cover all current use cases.

### Curated Target Model Registry

A registry of community-contributed target models distributed alongside Shape Shifter or via a companion package.

**Candidates:**
- `sead_standard_model` — SEAD Clearinghouse v2 (already exists in `resources/target_models/`)
- Generic archaeological site model
- Museum specimen model

**Approach:** Bundled YAML files in `resources/target_models/`, referenced by short name without a path. The mapper resolves short names to the bundled file before resolving `@include:`.

### Target Model Documentation Downloads

**Status:** ✅ **COMPLETE** (January 2025)

Generate human-readable documentation for target models in HTML, Markdown, or Excel formats, with optional project context showing which entities are actually used vs. just defined in the specification.

**Implementation:**

1. **Core Generator** (`src/target_model/documentation.py`)
   - `TargetModelDocumentGenerator` class accepting `target_model: TargetModel` and optional `project: ShapeShiftProject`
   - Project-aware mode: marks entities as "used" or "unused", displays usage statistics, warns about missing required entities
   - Standalone mode (project=None): generates spec-only documentation without usage context
   - Format support: HTML (interactive with CSS), Markdown (readable), Excel (tabular with sheets per entity)

2. **Templates** (`src/target_model/templates/`)
   - Jinja2 templates for HTML and Markdown with conditional project context blocks
   - HTML: Project header, usage badges (green "✓ Used", gray "Unused"), stats cards, responsive layout
   - Markdown: Project Context section with warnings for missing required entities

3. **Backend Service** (`backend/app/services/documentation_service.py`)
   - `DocumentationService.generate_target_model_docs(project_name, format)` → bytes
   - Loads project, resolves target model, creates generator with project context
   - Error handling: NotFoundError if no target model, BadRequestError if malformed

4. **API Endpoint** (`GET /api/v1/projects/{name}/target-model-docs?format={html|markdown|excel}`)
   - Returns binary blob with appropriate content-type and Content-Disposition header
   - Format query parameter validated against DocumentFormat enum

5. **Frontend Integration** (`frontend/src/views/ProjectDetailView.vue`)
   - Download button in Target Model tab header with format selector dropdown
   - Three format options: HTML Interactive, Markdown, Excel Spreadsheet
   - Blob download pattern with temporary URL creation and cleanup

6. **CLI Script** (`scripts/generate_target_model_docs.py`)
   - Refactored to use Core generator class (removed ~280 lines of inline templates)
   - Supports standalone usage: `python scripts/generate_target_model_docs.py <yaml> --format all`
   - Works without project context for spec-only documentation

**Use Cases:**
- **Stakeholder documentation**: Download readable guides for non-technical users
- **Project planning**: See which entities are used vs. unused in current configuration
- **Quality assurance**: Identify missing required entities before data submission
- **Version comparison**: Generate docs for different target model versions to compare

**Benefits:**
- First-class UX feature accessible from Target Model tab (no terminal required)
- Project-aware insights show configuration gaps
- Multiple formats support different consumer needs (interactive HTML, portable Markdown, Excel for analysis)
- Reusable Core class enables both API and CLI usage

---

## SEAD Coverage Backlog

Lower-frequency SEAD tables not yet represented in `resources/target_models/sead_standard_model.yml`:

- Abundance chain entities (`abundance`, `abundance_element`, `abundance_modification`)
- Dating entities (`relative_dating`, `relative_age`, `radiocarbon_dating`)
- Method-group and contact entities (`method_group`, `biblio`, `contact`)
- Taxonomy-focused entities (`taxon`, `taxonomic_order`, `ecocodes`)
- Specialized tables appearing only in specific data types (ceramics, dendrochronology, insects)

**Note:** These are SEAD spec coverage gaps, not framework gaps. The conformance engine supports them — the spec YAML just has not been written yet.

**Approach:** Add entity blocks to `sead_standard_model.yml` incrementally as real projects exercise those entity types. Prefer driven-by-need over speculative coverage.

---

## Suggested Work Order

When resuming work on this backlog, a sensible order is:

1. **Source-type appropriateness** — low complexity, high value, zero false-positives
2. **`format_version` field** — trivial parser change, prevents future breakage
3. **Test coverage gaps** — fill the backend adapter and missing-file tests
4. **Rule disabling** — needed before shipping Phase 4 checks widely
5. **Semantic mismatch detection** — requires tuning; start with a conservative threshold
6. **Transitive FK satisfaction** — well-defined algorithm, removes real false-positives
7. **`no_orphan_facts`** check — depends on FK graph walk being tested first
8. **Alias matching / normalization** — only after alias table or metric is agreed on

Items in the "Future Enhancements" section (remote refs, registry, diff tooling) are speculative — implement only if a concrete need arises.
