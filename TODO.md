
# Finally cleanup step

### Bugs

 - [] FIXME: Right preview pane doesn't clear values between entities
 - [] FIXME: #116 Intermittent navigation error when opening project
 - [] FIXME: #124 Reconciliation editor complains when "extra_columns" entered in property field

### Tech debts:

 - [] FIXME: Update documentation, archive non-relevent documents
 - [] FIXME: Review test code coverage
 - [] FIXME: #169 Initialize Playwright setup (UX E2E tests)
 - [] FIXME: #171 Increade manual testing guide feature coverage

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

