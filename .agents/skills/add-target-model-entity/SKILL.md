---
name: add-target-model-entity
description: Add, extend, or repair an entity in the SEAD standard target model (resources/target_models/sead_standard_model.yml) from a live source table, including columns, unique sets, and required or conditional foreign keys. Use when asked to add a table or entity to the standard/superset target model, or to fix a model column or foreign key that disagrees with the live schema. Do not use for project configuration (shapeshifter.yml), for writing proposals, or for re-triaging which tables are gaps.
---

# Add a Target-Model Entity

Add one entity to `resources/target_models/sead_standard_model.yml` from the live
SEAD surface, wire the foreign keys that reference it, and update the dependent
tests and counts.

The user's instructions take precedence over this skill. Two rules that save the
most time:

- **Read the source table once, in one script call.** Do not explore the model by
  hand; the inspection script prints the columns, constraints, coverage state, and
  every referring table at once.
- **Edit the model once.** Collect the entity block and every dependent foreign
  key, then apply them together.

## Facts that decide the edit

- **Schema source of truth:** `docs/investigations/sead-target-model-completeness/columns.csv`
  (a run of `exported-columns.sql` against `sead_staging`). `docs/sead/01_tables.sql`
  is a stale historical dump; do not use it to decide columns.
- **One editable model file.** `tests/test_data/target_models/sead_standard_model.yml`
  and `resources/target_models/sead_superset_model.yml` are symlinks to
  `resources/target_models/sead_standard_model.yml`. Never copy; edit the target.
- **Entities are a top-level `entities:` key**, not nested under `model:`.
- **Do not declare the entity's own primary-key/public-id column** in `columns:`
  unless it is a generated bridge key (see `site_location`). `public_id` names it.
- **`public_id` must end with `naming.public_id_suffix`** (`_id`).
- **`unique_sets`** are business keys used for matching and deduplication, so they are
  not limited to declared database constraints. Prefer the table's real unique
  constraints when it declares them (`docs/sead/05_constraints.sql`); otherwise use
  the natural business key, as `taxa` does with `[genus_id, species]` on a table
  whose only constraint is its primary key. Every column named must exist in
  `columns:`, or `TargetModelSpecValidator` reports `UNKNOWN_UNIQUE_SET_COLUMN`.
- **Foreign keys name an entity, not a table or column.** Declare the FK *column*
  in `columns:` (for example `record_type_id`) and the *entity* in `foreign_keys:`.
  A declared column with no matching FK is a dangling reference — that is exactly
  what this skill fixes.
- **`required_when.has_new_rows` names the owning entity itself**, never the target:

  ```yaml
  foreign_keys:
    - entity: record_type
      required_when:
        has_new_rows: method      # the entity that owns this foreign key
  ```

  Never combine `required` with `required_when` on the same FK
  (`CONFLICTING_FOREIGN_KEY_REQUIREMENTS`). Use `required: true` only when the
  relationship must exist for every row; use `required_when` when the parent is
  only needed because this entity gains new rows.

## Workflow

Run these from the repository root. Use `.venv/bin/python`; `uv run` is unreliable
for ad-hoc scripts in this repository.

1. **Confirm the table and pick a role.** `columns.csv` column `table_name` is the
   table; the gap triage in `resources/target_models/TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md`
   usually suggests the entity name, role, and tier.

2. **Inspect the source table in one call:**

   ```bash
   .venv/bin/python .agents/skills/add-target-model-entity/scripts/inspect_source_table.py tbl_record_types \
     --entity record_type --role classifier --domain core \
     --description "Controlled vocabulary describing the kind of record a classifier row represents." --skeleton
   ```

   Read four sections: source columns and types, declared primary-key and unique
   constraints, current model coverage (including source columns the entity does
   not declare, and declared columns absent from the source), and the source tables
   that reference this table with their FK state.

3. **Place the entity next to its neighbours.** Insert it near related entities
   rather than at the end of the file, so the file stays readable. Keep the
   repository's two-space indent, `domains: [a, b]` inline form, and `unique_sets`
   / `foreign_keys` order.

4. **Wire every referring entity.** For each `FK NOT declared` line, add the FK
   column to that entity's `columns:` if missing, then add the entity FK with
   `required_when.has_new_rows` set to the owning entity. Prefer one edit batch that
   adds the entity and all dependent FKs.

5. **Bump `model.version`** for a semantic change to the standard model
   (minor for a new entity: `2.1.0` → `2.2.0`).

6. **Verify in one call:**

   ```bash
   .venv/bin/python .agents/skills/add-target-model-entity/scripts/verify_model_change.py --conformance
   .venv/bin/python .agents/skills/add-target-model-entity/scripts/audit_foreign_keys.py
   ```

   `verify_model_change.py` must print `result: OK`, `out-of-source: 0`, no
   duplicate `target_table`, and the conformance counts per example project. Use
   `--unmapped` when you need the current gap list.

   `audit_foreign_keys.py` must print `foreign-key problems: 0`. It compares every
   foreign key in `columns.csv` against the model in both directions, so it catches
   relationships no tier or issue has listed yet. Run it after any entity work, not
   only when you suspect a mismatch.

7. **Update the pinned expectations the counts feed.** Only the ones that changed:

   | Location | What to update |
   |---|---|
   | `tests/target_model/test_spec_files.py` | `assert len(target_model.entities) == N` |
   | `tests/model/test_target_model_conformance.py` | the `sead_missing_sample_group` baseline dict: `CONDITIONAL_FK_AWAITING_RECONCILIATION` rises by one per new conditional FK owned by an entity the fixture declares |
   | `resources/target_models/README.md` | entity count, mapped/unmapped, model version, and the gap-triage row |
   | `resources/target_models/TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md` | strike the completed candidate, adjust the gap total, and the "remaining Tier 1" wording |

   Take the numbers from the verification output, never from memory or from the
   previous document text.

8. **Run the tests:**

   ```bash
   .venv/bin/python -m pytest tests/model tests/target_model -n 0 --tb=short > /tmp/tm.log 2>&1; echo "exit=$?"
   ```

   Judge the run by the exit status. Terminal output wrappers in this environment
   can suppress pytest's final `N passed` line, so do not spend time hunting for a
   summary line or re-running with different flags; `exit=0` plus `--tb=short` is
   enough. Use `-n 0` because xdist is configured by default.

   **Do not run `graphify update` for a target-model entity change.** The graph
   indexes source code and documentation structure, not YAML entity contents, so
   the refresh costs time without recording the edit. Leave graph maintenance to
   the workflow that changes Python or Markdown files.

## Verification meaning

- `CONDITIONAL_FK_AWAITING_RECONCILIATION` is an **info** finding, not an error.
  Conformance cannot know whether rows will be inserted before reconciliation.
  A rise in that count is expected when you add a conditional FK whose owner is in
  a fixture, and it is the baseline to update.
- `MISSING_REQUIRED_COLUMN` / `MISSING_REQUIRED_FOREIGN_KEY_TARGET` count existing
  fixture gaps. Do not "fix" them by weakening the model.
- Insert ordering follows the FKs automatically: `src/target_model/insert_dependencies.py`
  treats a `required_when` FK as an edge, so a selected `method` pulls `record_type`
  in first. No ordering code needs changing.
- Project YAML that hard-codes the FK value (for example arbodat's
  `record_type_id: '2'`) keeps working; the model FK does not break existing
  projects.

## Pitfalls

- Adding a column to an entity without adding the FK entity leaves a dangling
  reference; adding the FK entity without the column leaves a column-less
  relationship. Do both, and confirm with the inspection script's referring-table
  section.
- When the new entity's own foreign-key target is still unmapped (for example
  `taxa_tree_genus.family_id` points at the unmapped `taxa_tree_family`), declare
  the column and leave the FK out. Naming an entity that does not exist produces
  `UNKNOWN_FOREIGN_KEY_ENTITY`. Record the deferred FK in
  `TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md` so the next pass picks it up, and
  re-add the FK once the target is modelled.
- A nullable FK column means an optional FK (`required: false`), which creates no
  insert-order edge. Use that for self-references and for back-references such as
  `site.site_preservation_status_id`, where the target row is an aggregate child of
  the same entity. A conditional FK there would create a dependency cycle.
- Do not invent types. Map from `columns.csv`: `character varying`/`text` →
  `string`, `numeric` → `decimal`, `integer`/`bigint`/`smallint` → `integer`,
  `boolean` → `boolean`, `date` → `date`, `uuid` → `uuid`, `numrange` → `numrange`.
  Timestamps have no dedicated model type; use `string` and note it.
- Do not re-derive the completeness surface. The declared exclusions are tables
  ending `colours` or `images`, plus the export-query filters that never appear in
  `columns.csv`. Neither is a gap.
- `value_qualifier_symbol.public_id: qualifier_symbol_id` is correct; do not
  "fix" it while auditing nearby entities.
