# Proposal: Target Model Conformance Enhancements

## Status

**Active — backlog.** Core conformance engine (Milestones 1–3) is complete. This proposal tracks the remaining deferred and future work gathered from five now-archived source documents.

## Source Documents

This proposal consolidates deferred and future items from:

- `docs/proposals/done/TARGET_SCHEMA_AWARE_VALIDATION.md` — original validation proposal
- `docs/proposals/done/TARGET_SCHEMA_AWARE_VALIDATION_IMPLEMENTATION_SKETCH.md` — implementation sketch and phase plan
- `docs/proposals/done/TARGET_MODEL_SPECIFICATION_FORMAT.md` — format specification proposal
- `docs/proposals/done/SEAD_V2_IMPLEMENTATION_PLAN.md` — phased SEAD rollout plan
- `docs/proposals/done/TARGET_MODEL_CONFORMANCE_REFINEMENT.md` — conformance refinement notes

## What Is Already Implemented

Five conformance validators are registered and active:

| Key | What it checks |
|-----|----------------|
| `required_entity` | Required entities present in the project |
| `public_id` | `public_id` present and not unexpected |
| `foreign_key` | Required FK targets present |
| `required_columns` | Required columns present |
| `naming_convention` | `public_id` values end with `naming.public_id_suffix` |

Backend wiring, frontend Check Conformance button, and Conformance panel in ValidationPanel are all live.

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

**Implementation note:** Requires walking the FK graph, which is already available via `ProcessState`. Add a `GlobalConformanceValidator` base type to the registry.

### Source-Type Appropriateness

Classifiers declared with `role: classifier` should use `type: fixed` or `type: sql` rather than `type: entity`. Emit a warning when a classifier is configured as a row-extraction entity.

**Difficulty:** Low. Single-pass check against entity type field.

### Schema-Aware Append Conformance

When a project uses append mode, validate that the appended columns conform to the target-model column spec for that entity. Currently append operations are not checked against the target model at all.

### Branch-Aware Semantic Validation

When a merged-parent entity has branch children, validate that each branch covers a non-overlapping slice. Depends on branch modeling being more concrete. Defer until branch proposals stabilize.

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
- `target_model: "@include: target_models/specs/sead_v2.yml"` resolves to dict at mapper boundary
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
- `sead_v2` — SEAD Clearinghouse v2 (already exists in `target_models/specs/`)
- Generic archaeological site model
- Museum specimen model

**Approach:** Bundled YAML files in `target_models/specs/`, referenced by short name without a path. The mapper resolves short names to the bundled file before resolving `@include:`.

---

## SEAD Coverage Backlog

Lower-frequency SEAD tables not yet represented in `target_models/specs/sead_v2.yml`:

- Abundance chain entities (`abundance`, `abundance_element`, `abundance_modification`)
- Dating entities (`relative_dating`, `relative_age`, `radiocarbon_dating`)
- Method-group and contact entities (`method_group`, `biblio`, `contact`)
- Taxonomy-focused entities (`taxon`, `taxonomic_order`, `ecocodes`)
- Specialized tables appearing only in specific data types (ceramics, dendrochronology, insects)

**Note:** These are SEAD spec coverage gaps, not framework gaps. The conformance engine supports them — the spec YAML just has not been written yet.

**Approach:** Add entity blocks to `sead_v2.yml` incrementally as real projects exercise those entity types. Prefer driven-by-need over speculative coverage.

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
