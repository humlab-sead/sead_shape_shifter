I think the proposal is directionally very good, and it is substantially better than a narrow fix for #511. The diagnosis matches the issue: the current implementation mixes saved configuration, source headers, and several frontend unions rather than modelling when columns actually exist. The proposal captures that problem clearly. Inklistrad markdown

I would approve the overall architecture, but I would revise a few parts before turning it into an implementation plan.

### 1. The five-stage model is slightly too coarse

This is the main issue I see.

The proposal defines:

> `extract`, `before_unnest`, `after_link`, `after_unnest`, and `final`

That is useful, but some controls do **not map cleanly to exactly one of those stages**.

In particular:

- **Entity `Columns`** concerns available **source/input fields**, not the output of `extract`.
- **Drop Duplicates** can execute either before or after unnest.
- **FK Local Keys** can participate in the first linking pass or the post-unnest linking pass.
- **Extra-column expressions** can become evaluable at several different points.
- **Filters** explicitly select their stage.
- Linking multiple FKs introduces another wrinkle: a later FK can consume columns produced by an earlier FK.

So I would avoid making the public resolver contract primarily:

```text
stage -> columns
```

and instead make it primarily about **availability contexts/operations**, with stages as part of the underlying model.

For example conceptually:

```python
resolver.source_fields(...)
resolver.columns_for_replacements(...)
resolver.columns_for_deduplication(...)
resolver.columns_for_fk_local(fk_index=...)
resolver.columns_for_fk_remote(remote_entity=...)
resolver.columns_before_unnest(...)
resolver.columns_after_unnest(...)
resolver.columns_for_filter(stage=...)
resolver.columns_for_extra_column(stage=...)
```

Internally these can share a stage model.

This avoids forcing every editor control into an artificial five-stage mapping.

Your proposal itself hints at this complication when it says Drop Duplicates may move after unnest and extra columns may be deferred. Inklistrad markdown

### 2. Add an explicit **source/input** availability stage

Related to the above, I would add something like:

```text
source
```

or

```text
input
```

before `extract`.

Otherwise the resolver cannot cleanly answer the first question in your investigation:

> Entity `Columns`: Source fields that can be selected for the entity.

Those are not really "`extract` columns"; they are the inputs from which extraction is configured.

A more useful internal sequence might therefore be:

```text
source
extract
after_link
before_unnest
after_unnest
final
```

Though even then I would expose operation-oriented queries to the frontend rather than asking the frontend to understand these stages.

### 3. I would make the resolver return **control-specific candidates**

The proposal currently says the backend should return "stage-keyed candidate sets." Inklistrad markdown

I think that risks leaking pipeline semantics into the Vue application.

Instead of:

```json
{
  "extract": [...],
  "before_unnest": [...],
  "after_link": [...]
}
```

I would seriously consider something closer to:

```json
{
  "columns": [...],
  "business_keys": [...],
  "replacements": [...],
  "drop_duplicates": [...],
  "drop_empty_rows": [...],
  "unnest": {
    "id_vars": [...],
    "value_vars": [...]
  },
  "foreign_keys": {
    "local_keys": [...],
    "remote_keys": [...]
  }
}
```

Possibly with stage metadata attached to candidates where useful.

That preserves the important architectural property:

> **Python owns the pipeline semantics.**

The frontend shouldn't have to know that "`drop_duplicates` currently means `extract` except when XYZ, in which case use `after_unnest`."

That would otherwise reintroduce some of the duplication the proposal is trying to eliminate.

### 4. The parity-test requirement is too strong as currently phrased

This is the part I would definitely change.

The proposal says:

> "asserts the resolver's per-stage sets match the actual columns present at each stage." Inklistrad markdown

But elsewhere you correctly state that suggestions are **candidate sets**, not guarantees, because files/queries may drift. Inklistrad markdown

Those two concepts conflict somewhat.

A static resolver may intentionally produce:

```text
possible/configurationally valid columns
```

while runtime gives:

```text
columns actually present for this particular input
```

I would therefore phrase the test more narrowly:

> For deterministic fixture projects with known source metadata, verify that the resolver's candidates agree with the columns available at the corresponding pipeline operation.

And for the general contract test things such as:

```text
actual expected usable columns ⊆ resolver candidates
```

rather than unconditional exact equality.

Exact equality is excellent for carefully controlled fixtures, but I would not make it the abstract resolver contract.

### 5. Resolve the draft API question now: use POST

I wouldn't leave this as an open design question:

> POST full draft vs client-side merge.

For me the answer is fairly clear: **send the draft to the backend**.

Client-side merging into a saved representation undermines the "single source of truth" objective and forces the frontend to understand backend project semantics.

I would add a sibling endpoint, e.g. conceptually:

```http
POST /projects/{project}/entities/{entity}/column-availability
```

with:

```json
{
  "entity": { ...current draft... }
}
```

rather than trying to put an entity body on the existing GET endpoint.

The current endpoint is indeed a GET against the saved project, which confirms the proposal's diagnosis.

### 6. Don't do a backend round-trip "per control"

This risk statement could be tightened:

> "Every control would now consult the resolver." Inklistrad markdown

That needn't mean every control makes a request.

Prefer:

```text
draft changes
      ↓
debounced resolver request
      ↓
ColumnAvailability result
      ↓
all controls consume it
```

So there is one availability calculation for a particular draft revision, not N API requests for N controls.

That also makes caching much simpler: cache by effective draft/config hash rather than by control.

### 7. I would remove the suggestion that some stage logic can be locally computed

This sentence weakens an otherwise strong design:

> "cheap stages whose inputs the frontend already holds can still be computed locally if the resolver is the shared reference for the stage logic." Inklistrad markdown

I would remove it.

You already correctly rejected:

> "Per-control stage logic in the frontend"

because it duplicates the pipeline semantics. Inklistrad markdown

Computing some stages locally creates essentially the same architectural risk.

Frontend filtering such as sorting, grouping, hiding invalid choices, etc. is fine. But **column-availability semantics should stay in Python**.

### 8. There's a small scope inconsistency around FK extra columns

Your investigation includes:

> `FK Remote Keys` **and FK extra columns**

but the proposal scope lists only:

> FK `Local Keys` and `Remote Keys` Inklistrad markdown

I would explicitly include the FK extra-column remote-source selector in scope and acceptance criteria.

Otherwise #511 can be fixed while another part of the same FK editor continues using the old availability logic.

### 9. Filter fields may not belong in this change yet

The proposal says:

> Filter column fields

but also notes the current editor uses text fields rather than suggestions.

If you intend to convert those to comboboxes, that's an additional UX change rather than strictly part of fixing incorrect suggestions.

I'd choose one of two approaches:

- include filter availability in the **resolver API**, but defer frontend use; or
- explicitly include converting filter fields to comboboxes in scope.

I prefer the first. It keeps the resolver complete without expanding #511 unnecessarily.

### 10. The `system_id` acceptance criterion may be slightly too categorical

`P-AC-5` says:

> `system_id` is suggested only as an FK remote match key and is excluded from business keys and other non-FK controls. Inklistrad markdown

That matches the intended normal workflow because `system_id` is generated late.

But I would word this in terms of **stage availability** rather than a global special-case blacklist:

> Automatically generated `system_id` must not be suggested for operations that execute before identity assignment; it is available as an FK remote match key for processed parent entities.

That makes the rule derive from pipeline semantics instead of hard-coding UI policy.

It will age better if identity handling changes later.

---

## The architecture I would recommend

The central design can be reduced to three layers:

```text
ColumnAvailabilityResolver
        │
        │ owns pipeline/stage semantics
        ▼
Backend draft-aware endpoint
        │
        │ one debounced request per draft state
        ▼
useColumnAvailability()
        │
        ├── columns
        ├── businessKeys
        ├── replacements
        ├── dropDuplicates
        ├── dropEmpty
        ├── fkLocalKeys
        ├── fkRemoteKeys
        ├── unnestInputs
        └── extraColumnInputs
```

The important distinction is:

> **The resolver should model stages internally; the frontend should consume operation-specific availability.**

That gives you the single source of truth you want without making the UI understand Shape Shifter's normalization pipeline.

## Overall assessment

I would rate the proposal **strong, but needing one conceptual refinement before implementation**.

The core recommendation is right, and the documented current-state problems are well supported: the backend still exposes flat config-derived categories, uses the legacy unnest interpretation, and the proposal accurately identifies the multiple independent suggestion sources. Inklistrad markdown

The main change I'd make is this:

> Replace **"one stage-aware resolver returning stage-keyed sets"** with **"one operation-aware resolver backed by an explicit pipeline-stage model."**

That sounds like a minor wording change, but I think it will materially simplify the API, frontend, tests, and future maintenance.

I would also resolve **POST draft → resolver** now rather than leave it to the implementation phase, remove client-side availability calculation as an option, and weaken exact runtime parity from a universal contract to a controlled-fixture test.
