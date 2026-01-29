
# Finally cleanup step

### Bugs

 - [] FIXME: Right preview pane doesn't clear values between entities
 - [] FIXME: Update documentation, archive non-relevent documents

### Tech debts:

 - [] FIXME: #169 Initialize Playwright setup (UX E2E tests)
 - [] FIXME: #171 Increade manual testing guide feature coverage
 - [] FIXME: #188 Syncing issue between entity state (changes not shown when entity re-opened)

### New features

 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: Add additional frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: #68 Add a "finally" step that removes intermediate tables and columns.
 - [] TODO: #66 Introduce a "transformations" section with more advance columnar transforms (e.g. toWSG84).
 - [] TODO: #69 Add "parent" property to entity definitions.
 - [] TODO: #67 Introduce support for string concatenation in "extra_columns".
 - [] TODO: Add capability to duplicate an existing configuration.
 - [] TODO: #108 Add tiny DSL Expression Support in extra_columns
 - [] TODO: Introduce optional support for types for entity fields
          (e.g., string, integer, date) and support type conversions in extra_columns.
 - [] TODO: Improve multiuser support (working on same project)
 - [] TODO: Add more reconciliation entity types, and non-SEAD types (e.g. Geonames, RAÄ-lämningsnummer)
 - [] TODO: NOT WORTH THE EFFORT! Improve user experience (Add new edge/relationship in dependency graph)
 - [] TODO: Improve in-system help (full User Guide, more context sensitive help)
 - [] TODO: Improve UX suggestions when editing entity (awareness of availiable tables, columns etc)
 - [] TODO: Improve Reconcile user experience
 - [] TODO: Auto-save feature in YAML editing mode (trigger after 2 seconds of inactivity)
 - [] TODO: #189 Simplify server side caching (remove!) of parsed YAML projects


APPENDIX

# TODO: #108 Tiny DSL Expression Support in extra_columns DETAILS

The "extra_colums" key in an entity's specification provides a way of adding new columns to the resulting DataFrame. The extra_columns value is a dict, where each key is the name of the new column, and the value is the initial value of the new column. The value can be a constant, or anoother column in the source or DataFrame.

It would be useful to support simple expressions in the key's value, e.g. create a fullname column for two first/last name columns. The expressions could translate to Pandas operations, or a python function that transforms the Pandas DataFrame.

Please suggest a YAML-notation for the expression in the extra-columns section for this feature, and how it could be implemented.. Try to make this feature simple but useful.


## Feature Idea

Add expressions under extra_columns using a tiny DSL in YAML, e.g.
```yml
extra_columns:
  fullname: "{row.first_name} + ' ' + {row.last_name}"
  initials: "concat(initials, first_name[:1], last_name[:1])"
```
where {row.X} refers to source/df fields and helpers (like concat or slicing) map to Pandas-friendly Python.

## Implementation path:
 - Interpret the string by formatting it inside a sandboxed helper that injects the current pandas.Series (row) or even the whole DataFrame.
 - For column-wise expressions, leverage df.eval/df.assign after prepping a safe namespace with allowed functions (concat, upper, etc.).
 - For more complex transformations, allow users to specify "lambda df: df['a'] + df['b']" (evaluated via eval with a restricted globals containing only helpers and pd).
- Keep simple by defaulting to expressions evaluated per-row via df.eval or df.assign, with ability to refer to any existing column.

## Next steps:

1. Decide whether expressions should be evaluated row-by-row (via df.assign(extra=...)) or on the whole DataFrame.
2. Implement parsing/evaluation in the pipeline step where extra_columns currently get applied (likely near the Filter/Link stage).
3. Add tests covering constant, direct column reference, and expression cases.
Expression Detection

Treat every extra_columns value as a string; interpret it as an expression only if it uses a special marker (e.g., starts with expr: or contains {/} tokens). Anything else stays literal.
Recommended rule: if the string matches expr:<python> (e.g., fullname: "expr:df['first_name'] + ' ' + df['last_name']"), run it through the expression evaluator; otherwise just assign the string directly.
This keeps defaults simple (constants work out of the box) while giving a clear hint when evaluation is intended.

Using "expr: python-pandas-row-expression" sounds great. It might be a bit complicated for non-technical users, thoght. Can you suggest a layer/notation above these expressions that exposes the most common e.g. string expressions,a nd that "ompiles" into these pandas expressions? E.g. "= <user-friendly-expression>" by the backend compiles to "expr:<corresponding-python-expression>". In such a case, non-tech user can add simple expressions, but we still have a super-user option.

Expression DSL

Introduce a mini DSL for extra_columns like:

extra_columns:
  fullname: "=concat(first_name, ' ', last_name)"
  initials: "=upper(substr(first_name, 0, 1)) + upper(substr(last_name, 0, 1))"
  source_note: "expr:df['city'] + ' (' + df['code'] + ')'"
Strings starting with = are treated as friendly expressions; strings starting with expr: are raw pandas expressions for power users. Anything else stays constant.

Backend implementation: parse the string when it’s added to the DataFrame. If the value starts with expr:, strip the prefix and run it through df.assign(**{name: eval(expr, safe_globals, {"df": df})}). If it starts with =, feed it to a small compiler that replaces helper names with pandas operations (e.g., concat(a, b) → df['a'].astype(str) + df['b'].astype(str), upper(x) → df['x'].str.upper(), substr(x, start, length) → df['x'].str[start:start+length], ifnull(x, default) etc.), then evaluate the resulting pandas expression in the same safe context. Constants remain untouched.

Keep helper mappings simple so non-technical users can combine columns with string functions; expose more via extending the compiler (e.g., additional helpers for dates or math).

---

# AI Assessment of TODO Items (Generated 2026-01-16)

---

## 🔥 HIGH PRIORITY - Quick Wins

### #124 Reconciliation editor extra_columns complaint - **Easy Fix**
- The reconciliation editor validation is likely too strict
- Simple fix: Update schema/validation to allow `extra_columns` property
- **Effort: 1-2 hours** | **Value: High** (removes user friction)

### Right preview pane doesn't clear values - **Simple Bug**
- Likely missing reactive reset in EntityPreviewPanel.vue
- Pattern: Add `watch(() => props.entityName, () => clearState())`
- **Effort: 30 minutes** | **Value: Medium** (polish)

---

## 💡 MEDIUM PRIORITY - Moderate Value

### #116 Intermittent navigation error - **Needs Investigation**
- Could be race condition in router or store
- **Effort: 2-4 hours** | **Value: High IF frequent** (stability)
- Check browser console logs and navigation guards

### Edit data source in dual-mode editor (Form/YAML) - **Good UX Pattern**
- Already have this pattern for entities
- Reuse EntityFormDialog.vue architecture
- **Effort: 4-6 hours** | **Value: Medium** (consistency)

### Generate default reconciliation YAML from manifest - **Smart Feature**
- Calls `/reconcile` endpoint and scaffolds YAML
- **Effort: 6-8 hours** | **Value: High** (user productivity)
- Reconciliation system already exists with full implementation

### #68 Add "finally" cleanup step - **Pipeline Feature**
- Drops intermediate tables/columns after processing
- **Effort: 8-12 hours** | **Value: Medium** (clean output)
- Fits naturally after Store phase

---

## 🎯 WORTH CONSIDERING - Strategic Features

### #108 Tiny DSL for extra_columns - **HIGH VALUE but Complex**
- Detailed spec already exists in TODO.md
- Two-tier approach is smart: `=concat(...)` for users, `expr:...` for power users
- **Effort: 2-3 weeks** | **Value: Very High** (major feature)
- **Recommendation: Phase 1 = Just `expr:` support (1 week), Phase 2 = DSL compiler (2 weeks)**

### #66 Transformations section (toWGS84, etc.) - **Data Quality Feature**
- Coordinate transformations, case normalization, etc.
- **Effort: 2-3 weeks** | **Value: High for geo data**
- Consider using existing libraries (pyproj for coords)

### #69 Add "parent" property to entities - **Hierarchical Data**
- Useful for nested structures (site → feature → sample)
- **Effort: 1-2 weeks** | **Value: Medium** (depends on use cases)

### #67 String concatenation in extra_columns - **Subset of #108**
- **Recommendation: Skip if doing #108 DSL, otherwise quick win**
- **Effort: 2-3 days** | **Value: Medium**

### Duplicate existing configuration - **User Convenience**
- Copy project with new name
- **Effort: 2-3 hours** | **Value: Medium**

### Add optional types for entity fields - **Type Safety**
- Schema validation + conversions in extra_columns
- **Effort: 1-2 weeks** | **Value: Medium** (better error messages)

---

## ⚠️ LOW PRIORITY / DEFER

### Update documentation - **Continuous Task**
- Current docs are comprehensive (CONFIGURATION_GUIDE.md is 2,500+ lines!)
- Archive old docs as you find them
- **Recommendation: Do incrementally, not as big task**

### Improve multiuser support - **Complex Feature**
- Requires conflict resolution, locking, real-time sync
- **Effort: 4-6 weeks** | **Value: Low** (unless multiple concurrent users)
- **Recommendation: Defer unless actual need arises**

### Add more reconciliation entity types - **Domain-Specific**
- Geonames, RAÄ, etc.
- **Effort: Varies** | **Value: Depends on user base**
- **Recommendation: Add on demand, not preemptively**

### Improve UX suggestions when editing entity - **Context-Aware Editor**
- Show available tables/columns from data source
- **Effort: 2-3 weeks** | **Value: High for new users**
- Could integrate with existing YAML intelligence

### Improve in-system help - **User Guide Integration**
- Context-sensitive help tooltips
- **Effort: 2-4 weeks** | **Value: Medium**
- **Recommendation: You have good tooltips already; defer full guide**

### Improve Reconcile UX - **Vague Item**
- **Recommendation: Clarify specific pain points before tackling**

---

## ❌ NOT WORTH IT

### Improve UX for adding edges in dependency graph - **Marked as "NOT WORTH THE EFFORT"**
- Agreed - dependency graph is visualization, not primary editor
- YAML or form editing is sufficient

---

## Recommended Priority Order

### Phase 1: Quick Wins (1-2 days total)
1. ✅ Check off #166 YAML intelligence (DONE)
2. ✅ Check off "Review test coverage" (91% is excellent)
3. Fix #124 reconciliation editor extra_columns
4. Fix right preview pane clearing bug
5. Fix active route highlighting

### Phase 2: High-Value Features (2-3 weeks)
1. #108 DSL for extra_columns (Phase 1: `expr:` support only)
2. Generate default reconciliation YAML
3. Edit data source in dual-mode

### Phase 3: Strategic Additions (4-6 weeks)
1. #108 DSL (Phase 2: user-friendly compiler)
2. #68 Finally cleanup step
3. #66 Transformations section
4. Improve UX suggestions (context-aware editing)

### Deferred
- Multiuser support (until proven need)
- Additional reconciliation types (on demand)
- Full in-system help (incremental improvement better)

---

## New Tech Debt Identified

1. **Frontend type safety** - Some `any` types in stores could be stricter
2. **Error boundaries** - Add Vue error boundaries for production robustness
3. **API retry logic** - Add exponential backoff for transient failures
4. **Stale data indicator** - Show when cached data might be stale

None of these are critical given your 91% test coverage.

---

**Bottom line:** Focus on Phase 1 (bugs), then tackle #108 DSL in two phases. The extra_columns DSL is your highest-value unimplemented feature based on the detailed spec you've already written.

# TODO: #174 Upload Excel files to data source directory

Add capability to upload Excel files (.xls, .xlsx) to the data source files directory defined by SHAPE_SHIFTER_DATA_SOURCE_FILES_DIR in the .env file. The uploaded Excel files should be accessible for use in entity configurations within the Shape Shifter application.



I have a bug which can be reproduced with these steps:

1. Click on projects
2. Open a project
3. Click YAML
```
metadata:
  name: strukke_test
  type: shapeshifter-project
  description: Project for strukke_test
  version: 1.0.0
  default_entity:
entities:
  strukke_data:
    type: xlsx
    keys: []
    options:
      filename: projects/AllaC14_230316_v4_clean (1).xlsx
options: {}
```
4. Close YAML
5. Click on entities


TODO: #181 Drop duplicates of "site" entity fails FD validation

| Fustel            | EVNr       | FustelTyp | KoordSys                            | rWert    | hWert     | üNN   | site_name         | national_site_identifier | coordinate_system                   | latitude_dd | longitude_dd | altitude |
|-------------------|------------|-----------|-------------------------------------|----------|-----------|-------|-------------------|--------------------------|-------------------------------------|-------------|--------------|----------|
| Bkaker            | 274939     | Siedl     | Geografische Länge/Breite (dezimal) | 23.2     | 61.2      |       | Bkaker            | 274939                   | Geografische Länge/Breite (dezimal) | 23.2        | 61.2         |          |
| Blaker kirkegård  | 224073     | Siedl     |                                     | 628472.0 | 6653720.0 | 143.0 | Blaker kirkegård  | 224073                   |                                     | 628472.0    | 6653720.0    | 143.0    |
| Blaker kirkegård  | 224073     | Siedl     | Geografische Länge/Breite (dezimal) |          |           |       | Blaker kirkegård  | 224073                   | Geografische Länge/Breite (dezimal) |             |              |          |
| Blaker kirkegård  | 224073     | Siedl     | Geografische Länge/Breite (dezimal) | 628472.0 | 6653720.0 | 143.0 | Blaker kirkegård  | 224073                   | Geografische Länge/Breite (dezimal) | 628472.0    | 6653720.0    | 143.0    |
| Göteborg 342      | L1960:2928 | Stadt     |                                     |          |           |       | Göteborg 342      | L1960:2928               |                                     |             |              |          |
| Kville 1502       |            | Rin       |                                     |          |           |       | Kville 1502       |                          |                                     |             |              |          |
| Sandarna Gbg 15:1 | L1969:1130 | FustelSo  |                                     |          |           |       | Sandarna Gbg 15:1 | L1969:1130               |                                     |             |              |          |
| Sandarna Gbg 15:1 | L1969:1130 | unbek     |                                     |          |           |       | Sandarna Gbg 15:1 | L1969:1130               |                                     |             |              |          |


determinent_columns:  ["Fustel", "EVNr"]

# TODO: Keep log of deferred links during normalization (performance optimization)
Add capability to keep track of entities with deferred foreign key links during the normalization process. This will allow the system to retry linking only those entities that have unresolved foreign key references after each entity is processed, rather than attempting to relink all entities with deferred links. This optimization aims to reduce the time complexity from O(n^2) to a more efficient approach, improving overall performance during the normalization phase.

```
class _Linker(Protocol):
    """Minimal protocol for ForeignKeyLinker (keeps this class decoupled)."""

    def link_entity(self, *, entity_name: str, config: ShapeShiftProject) -> bool:
        """Return True if linking is still deferred for this entity."""


@dataclass
class DeferredLinkingTracker:
    """
    Tracks entities whose foreign key linking is deferred and retries linking efficiently.

    Usage pattern:
      - After each link_entity call: tracker.note(entity, deferred)
      - After processing entity: tracker.retry()
      - At end: unresolved = tracker.finalize()
    """

    project: ShapeShiftProject
    linker: _Linker

    deferred: set[str] = field(default_factory=set)

    def note(self, *, entity_name: str, deferred: bool) -> None:
        """Record the deferred status of a just-linked entity."""
        if deferred:
            self.deferred.add(entity_name)
        else:
            self.deferred.discard(entity_name)

    def retry(self) -> None:
        """Retry linking only for entities currently in deferred set."""
        if not self.deferred:
            return

        still_deferred: set[str] = set()
        for entity_name in self.deferred:
            if self.linker.link_entity(entity_name=entity_name, config=self.project):
                still_deferred.add(entity_name)

        self.deferred = still_deferred

    def finalize(self, *, include_entities: set[str] | None = None) -> set[str]:
        """
        Final retry sweep.

        If include_entities is provided and we haven't tracked anything yet,
        initialize deferred set from include_entities to force a last attempt.
        Returns the remaining unresolved deferred entities.
        """
        if include_entities is not None and not self.deferred:
            self.deferred = set(include_entities)

        self.retry()
        return set(self.deferred)
```

# TODO: Local vs remote identity fields

This system shapeshifts incoming data to a form that conforms to a target's system requirements.
Some entity instances (e.g. lookups etc) of the incoming data already exists in the target system, and
we need to reconcile these entities by assigning the target system's identity to these instances.

An example:
Income data has a site "Xyz" which exists in SEAD with identity 99. The user must be able to assign
target system's identity 99 to this incoming site "Xyz".

We do have the reconciliation workflow in a later step where we can search for identities in the
remote system. But user's need to be able to assign values to "fixed value" entities already 
in the entity editor.

## Current System Model

All foreign keys in the system refer to local identities within the shape shifting project.
Normally, this is a sequence number starting from 1.

Currently, this local id is assumed to be given the same name as the target system's identity.
For instance, entity "site" corresponds to SEAD table "tbl_sites" that has PK "site_id", and
entity "site" is then given the surrogate id "site_id".

A later step in the workflow copies this local surrogate id column to a "system_id" column, and
clears all values in the surrogate id column. This cleared column is then assumed to be the
public id (i.e. SEAD PK). Later on, if a row has a value in this column, that is an indication
that the row is an existing entity, and row with local "system_id" maps to this remote/public id.

For "tbl_sites" we can have "system_id" 2 maps to "sead_id" 6745.

This mapping/linking which is implemented in the reconciliation workflow is a fundamental feature
of this system.

## Proposed Enhancement: Three Explicit Identity Types

Make the three types of identities explicit and separate:

1. **Local Identity** (`system_id`): Project-scoped, auto-populated sequence
   - **Always named "system_id"** (standardized column name)
   - Auto-assigned starting from 1
   - Project-local scope (each project has its own sequence)
   - Used for internal foreign key relationships
   - For fixed-value entities: read-only, auto-renumbered on row add/delete
   - Config field can be omitted (defaults to "system_id")

2. **Source Business Keys** (`keys`): Natural/business keys from source data
   - Example: `keys: ["bygd", "raa_nummer"]` for Swedish archaeological sites
   - Uniquely identify entities within the source domain
   - Used for duplicate detection and source data reconciliation
   - Can span multiple columns
   - **Uses existing `keys` field** (already in the model)

3. **Target System Identity** (`public_id`): Remote system's primary key name
   - **Required field** - specifies FK column name (e.g., `public_id: site_id`)
   - Defines what FK columns are named in child tables
   - When child joins parent, FK column = parent's public_id, values = parent's system_id
   - Maps to target system's PK name (e.g., SEAD's tbl_sites.site_id)
   - Can be assigned values directly in entity editor for fixed-value entities

## Entity Configuration Model

```yaml
entities:
  site:
    type: fixed
    # Local identity (auto-managed, always named "system_id")
    # system_id: system_id  # Optional - defaults to "system_id" if omitted
    
    # Target system identity - defines FK column name in child tables
    public_id: site_id
    
    # Source business keys (for reconciliation and duplicate detection)
    keys: [bygd, raa_nummer]
    
    # Regular data columns
    columns: [site_name, coordinate_system, latitude_dd, longitude_dd]
    
    values:
      - system_id: 1           # Auto-managed (always this column name)
        bygd: "Bkaker"
        raa_nummer: "274939"
        site_id: 6745          # Target system ID (column name = public_id)
        site_name: "Bkaker"
        coordinate_system: "WGS84"
        latitude_dd: 23.2
        longitude_dd: 61.2

  location:
    type: fixed
    public_id: location_id
    keys: [location_type, location_name]
    columns: [location_type, location_name, latitude, longitude]
    
    values:
      - system_id: 1
        location_type: "settlement"
        location_name: "Main area"
        location_id: 4521
        latitude: 59.123
        longitude: 18.456

  site_location:
    type: entity
    source: source_data
    public_id: site_location_id
    columns: [bygd, raa_nummer, location_type, location_name, ...]
    
    foreign_keys:
      - entity: site
        local_keys: [bygd, raa_nummer]
        remote_keys: [bygd, raa_nummer]
      - entity: location
        local_keys: [location_type, location_name]
        remote_keys: [location_type, location_name]
```

**After normalization**, `site_location` will have:
- `system_id` (auto-numbered: 1, 2, 3...)
- `bygd`, `raa_nummer`, `location_type`, `location_name` (original columns)
- `site_id` (FK column, name from site.public_id, values from site.system_id)
- `location_id` (FK column, name from location.public_id, values from location.system_id)

## Benefits

- **Eliminates confusion**: Clearly distinguishes local project IDs from target system IDs
- **Standardized local IDs**: `system_id` is always named "system_id" (no configuration needed)
- **Clear FK naming**: Foreign key columns automatically named after parent's `public_id`
- **Enables early mapping**: Users can assign target system IDs in entity editor before reconciliation
- **Supports source reconciliation**: Business keys enable duplicate detection and source-to-source mapping
- **Flexible imports**: Incoming data may already have target system IDs; business keys allow matching
- **Better audit trail**: Three distinct identity types make data lineage transparent
- **Simpler model**: Uses existing `keys` field; `system_id` standardized; only `public_id` varies

## Implementation Changes

### Core Model (`src/model.py`)
- Rename `surrogate_id` → `system_id` (always "system_id" column, config field optional)
- Clarify `keys` field usage as source business keys
- Add required `public_id` field (defines FK column name in child tables)

### Entity Editor UI
- Show three sections:
  - Local identity: info text "Always named 'system_id' (auto-managed 1, 2, 3...)"
  - Business keys: multi-select for keys (source identifiers)
  - Public ID: **required** field for public_id (defines FK column name, e.g., "site_id")
- For fixed-value grids: show system_id column (read-only, auto-numbered) and {public_id} column (user-assignable target IDs)

### Validation
- Ensure `system_id` column is always auto-populated (standardized name)
- Validate `keys` are valid column names in the data
- Validate `public_id` is specified (required for FK naming)
- Validate `public_id` values are unique in fixed-value entities
- Warn if `public_id` column name conflicts with existing column names

### Reconciliation Integration
- Use `keys` (business keys) for matching incoming to existing target system entities
- Pre-populate `{public_id}` column from reconciliation service when identities are resolved
- Allow user override of suggested public IDs
- FK resolution: when joining child to parent, create column named `{parent.public_id}` with values from `parent.system_id`

## Phased Implementation

**Phase 1: Foundation (1-2 weeks)**
- Rename `surrogate_id` → `system_id` throughout codebase
- Clarify `keys` field as source business keys in documentation
- Update fixed-value grid to show and manage `system_id` column (auto-numbered)
- Update entity editor UI to clearly show three identity sections

**Phase 2: Public ID Support (1-2 weeks)**
- Add `public_id` field to entity model
- Update entity editor UI to show all three identity sections
- Implement validation for unique `public_id` values

**Phase 3: Reconciliation Integration (1-2 weeks)**
- Update reconciliation workflow to use `keys` (business keys) for matching
- Auto-populate `public_id` column from reconciliation results
- Support user override of suggested mappings

**Phase 4: Data Ingestion (1 week)**
- Support incoming data with pre-existing target system IDs
- Use `keys` (business keys) to match and merge with existing entities
- Preserve incoming public IDs if valid

## Future: "Freeze" Feature

Later, implement entity materialization:
- Run a derived entity through normalization pipeline
- "Freeze" button converts derived → fixed-value entity
- Auto-populate with computed results + auto-assigned system_ids
- User can then assign public_ids for reconciliation

## Notes

- No migrations needed (system is pre-deployment, all projects are test)
- Backward-compatible: existing surrogate_id projects still work (Phase 1 handles rename)
- Simplifies reconciliation by making identity flow explicit from the start 


Regarding naming of system_id/public_id. An important thing, which we might have missed in the analysis, is that when we join/merge tables using foreign key's, the **resulting FK field name in the "child" table** should be named as the public id in the parent table. We are basically, most often, joining on domain keys (not necesserally those defined in keys), and we wan't to "pull in" the join target's "system_id" into the local entity, but the local field must be named to remote table's public id.

Example:
```
entities:
  site:
    system_id: system_id      # I think we always can use this name so this key-value could possibly be ignored
    public_id: site_id
    keys: [bygd, raa_nummer]
    columns: [bygd, raa_nummer, ...]
  location:
    system_id: system_id
    public_id: location_id
    keys: [location_type, location]
    columns: [location_type, location_name, latitude, longitude, ...]
  site_location:
    system_id: system_id
    public_id: site_location_id
    columns: [bygd, raa_nummer, location_type, location_name, ...]
    foreign_keys:
    - entity: site
      local_keys: [bygd, raa_nummer]
      remote_keys: [bygd, raa_nummer]
    - entity: location
      local_keys: [location_type, location]
      remote_keys: [location_type, location]
```
After normalizing "site_location", it would have the following columns:
   - bygd, raa_nummer, location_type, location_name, site_id, location_id
   - site_id would have value from "site.system_id" columns
   - location_id would have values from "location.system_id" columns
 
That would give a behaviour consistent with current use of "surrogate_id".



TODO: Materialized of entities

Please assess how an entity materialization feature could be defined and implemented. 

An materialized entity should be "frozen" to the output of a full normalization workflow, and hence in all respect act as a fixed valued entity.

For an entity to be materialized the following must be true:
1. It cannot be a fixed valued entity (obvisously)
2. It must be fully validated
3. It cannot be dependent on another "dynamic" non-materialized entity (sql, entity based, file based). This is a constraint. But in the future we might allow cascading materialization.
4.  The entity's columns should be the same as the materialized dataframes columns

I don't think 3. is a big constraint, since we most often want's to materialize and reconcile lookups and metadata.

We need to be able to un-freeze the entity i.e. make it "dynamic" again. This means that when we materialize an entity we need to store overridden key/values so that they can be restored.

Un-freezing an entity should unfreeze all other entities that depends on this entity. User must be informed of consequence of materialization and un-freezing, especially of they have manually  entered values in the public id values which will be lost.

It might be a good idea to disable editing of frozen entities for all columns except the public id.

The data should  be store outside of the project file. On the other hand it is nice with a contained package. Feel free to suggest alternatives. Storing it outside the project probably limit's what could be edited without a construct for updating the data. An option is perhaps to store materialized data in a single file. On the other hand it might be good to be able to edit materialized data.

A tentative YAML syntax:

```
entities:
  site:
    public_id: site_id
    type: fixed
    materialized: true
    saved_state:
      type: sql
      columns: [.... old columns ... ]
      unnest:
        ....
      foreign_keys:
        ...
      ... more?

    values: 
       filename: path-to-file-relative-project-with-deterministict-name
       public_id: system-id to SEAD id mapping for edited vales
    xyz: rest the same ?

    