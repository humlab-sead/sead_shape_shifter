# Merged Entity Manual Test Checklist

## Overview

This checklist is for manually testing the first-class `type: merged` entity workflow in the project editor.

It is intentionally:

- **extensive** enough to cover creation, editing, preview, validation, and downstream usage
- **easy to follow** by using a small fixed-data fixture instead of external databases or files
- **specific** about expected rows, branch names, sparse FK columns, and validation outcomes

Use this together with [../TESTING_GUIDE.md](../TESTING_GUIDE.md) and record outcomes in [TEST_RESULTS_TEMPLATE.md](TEST_RESULTS_TEMPLATE.md) if needed.

---

## Scope

This guide verifies:

- merged entity creation in the visual editor
- branch editing and persistence
- merged parent preview behavior
- branch-source preview behavior
- post-merge `columns` restriction behavior
- validation grouping and merged-specific errors
- dependency graph visibility for merged inputs
- downstream FK usage via propagated sparse branch FK columns

This guide does **not** cover:

- performance testing
- cross-browser accessibility testing
- reconciliation against live SEAD IDs
- large real-world project data

---

## Preconditions

- Backend running
- Frontend running
- You can create or edit a disposable test project
- You are comfortable switching between the visual form editor and YAML editor when needed

Recommended environment:

- Chrome or Firefox latest stable
- Empty or disposable project named `merged_manual_test`

---

## Test Fixture

### Fixture Goal

Build a merged parent called `analysis_entity` from two fixed branch sources:

- `abundance_source`
- `relative_dating_source`

Then add one downstream consumer entity:

- `abundance_note`

This gives you one compact fixture that can exercise:

- branch union behavior
- sparse branch FK propagation
- null-fill behavior
- merged column restriction
- downstream joins using a propagated branch FK column

Important note for the downstream consumer fixture:

- `abundance_note.abundance_id` uses `1` and `2` because merged branch FK columns point to the source branch row's local `system_id`, not to the source branch entity's unresolved `public_id` values.

### Baseline Project Setup

Create the project with the following setup. You can either to this manually via the visual editor or by pasting the entitre YAML into a new project's YAML editor.
``

```yaml
metadata:
  name: merged_manual_test
  type: shapeshifter-project
  description: Project for merged_manual_test
  version: 1.0.0
  default_entity:
entities:
  abundance_source:
    type: fixed
    public_id: abundance_id
    keys: [sample_code, taxon_name]
    columns: [abundance_id, sample_code, taxon_name, abundance, unit]
    values:
      - [null, "S1", "Oak", 12, "count"]
      - [null, "S2", "Pine", 8, "count"]
  relative_dating_source:
    type: fixed
    public_id: relative_dating_id
    keys: [sample_code, dating_label]
    columns: [relative_dating_id, sample_code, dating_label, older_than_bp]
    values:
      - [null, "S1", "Early Iron Age", 2450]
      - [null, "S3", "Roman Period", 1800]
  analysis_entity:
    type: merged
    public_id: analysis_entity_id
    keys: [sample_code]
    branches:
      - name: abundance
        source: abundance_source
        keys: [sample_code, taxon_name]
      - name: relative_dating
        source: relative_dating_source
        keys: [sample_code, dating_label]
  abundance_note:
    type: fixed
    public_id: abundance_note_id
    keys: [note_code]
    columns: [abundance_note_id, note_code, abundance_id, note_text]
    values:
      - [null, "NOTE-1", 1, "Linked to first abundance branch row"]
      - [null, "NOTE-2", 2, "Linked to second abundance branch row"]
    foreign_keys:
      - entity: analysis_entity
        local_keys: [abundance_id]
        remote_keys: [abundance_id]
        how: left
options: {}

```

#### Copy-Pastable Data

**abundance_source**

```tsv
S1	Oak	12	count
S2	Pine	8	count
```

**relative_dating_source**

```
sample_code	dating_label	older_than_bp
S1	Early Iron Age	2450
S3	Roman Period	1800
```

**abundance_note**

```
note_code	abundance_id	note_text
NOTE-1	1	Linked to first abundance branch row
NOTE-2	2	Linked to second abundance branch row
```

### Expected Behavior of the Fixture

For the two branch sources above, Shape Shifter should auto-generate local `system_id` values independently per source entity.

Expected source-local identities:

- `abundance_source.system_id` = `1`, `2`
- `relative_dating_source.system_id` = `1`, `2`

Expected merged output characteristics:

- 4 rows total in `analysis_entity`
- `analysis_entity_branch` values:
  - `abundance`
  - `relative_dating`
- Sparse FK columns in merged parent:
  - `abundance_id`
  - `relative_dating_id`
- Expected sparse FK pattern:
  - abundance rows: `abundance_id = 1/2`, `relative_dating_id = null`
  - relative_dating rows: `abundance_id = null`, `relative_dating_id = 1/2`

Expected merged preview row outline:

| Row | analysis_entity_branch | abundance_id | relative_dating_id | sample_code | taxon_name | abundance | unit  | dating_label   | older_than_bp |
|-----|------------------------|-------------:|-------------------:|-------------|------------|----------:|-------|----------------|--------------:|
| 1   | abundance              |            1 |               null | S1          | Oak        |        12 | count | null           |          null |
| 2   | abundance              |            2 |               null | S2          | Pine       |         8 | count | null           |          null |
| 3   | relative_dating        |         null |                  1 | S1          | null       |      null | null  | Early Iron Age |          2450 |
| 4   | relative_dating        |         null |                  2 | S3          | null       |      null | null  | Roman Period   |          1800 |

---

## Quick Smoke Test

Use this when you only need a fast confidence check.

### Smoke Checklist

- [ ] Create `abundance_source` and `relative_dating_source`
- [ ] Create `analysis_entity` as `type: merged`
- [ ] Confirm **Branches** tab is visible and **Append** tab is hidden
- [ ] Confirm the **Columns** field is visible in the **Basic** tab
- [ ] Preview `analysis_entity` and confirm 4 merged rows
- [ ] Confirm merged preview shows `analysis_entity_branch`
- [ ] Confirm merged preview shows sparse FK columns `abundance_id` and `relative_dating_id`
- [ ] Switch preview to **Branch Source** and inspect each branch source directly
- [ ] Run YAML validation and confirm no merged-specific errors for the baseline fixture
- [ ] Save, close, reopen `analysis_entity`, and confirm branches persist

---

## Full Manual Checklist

### 1. Create the Branch Source Entities

### Steps

1. Open the project.
2. Create `abundance_source` using the fixture above.
3. Create `relative_dating_source` using the fixture above.
4. Save both entities.
5. Preview each source entity once.

### Expected Results

- [ ] Both entities save without schema errors
- [ ] Each entity preview loads successfully
- [ ] `abundance_source` shows 2 rows
- [ ] `relative_dating_source` shows 2 rows
- [ ] `abundance_source` columns include `sample_code`, `taxon_name`, `abundance`, `unit`
- [ ] `relative_dating_source` columns include `sample_code`, `dating_label`, `older_than_bp`

---

### 2. Create the Merged Parent in the Form Editor

### Steps

1. Create a new entity named `analysis_entity`.
2. Set **Type** to `Merged (Multi-Branch)`.
3. Set **Public ID** to `analysis_entity_id`.
4. Set **Business Keys** to `sample_code`.
5. Open the **Branches** tab.
6. Add branch 1:
   - name: `abundance`
   - source: `abundance_source`
   - keys: `sample_code`, `taxon_name`
7. Add branch 2:
   - name: `relative_dating`
   - source: `relative_dating_source`
   - keys: `sample_code`, `dating_label`
8. Save the entity.

### Expected Results

- [ ] Merged type can be selected without errors
- [ ] **Branches** tab is shown prominently
- [ ] **Append** tab is not shown for merged entities
- [ ] Source-loading fields are hidden for merged entities
- [ ] Saving succeeds
- [ ] Reopening the entity shows both branches intact

---

### 3. Verify Basic Tab Behavior for Merged Entities

This section explicitly tests the recently fixed merged-entity `Columns` field behavior.

### Steps

1. Reopen `analysis_entity`.
2. Go to the **Basic** tab.
3. Inspect the available controls.
4. Open the **Columns** picker.

### Expected Results

- [ ] The **Columns** field is visible for merged entities
- [ ] The merged info alert mentions `columns` as a valid post-merge configuration key
- [ ] The **Columns** picker contains union-style options from both branches
- [ ] The **Columns** picker includes `sample_code`
- [ ] The **Columns** picker includes `taxon_name`
- [ ] The **Columns** picker includes `abundance`
- [ ] The **Columns** picker includes `dating_label`
- [ ] The **Columns** picker includes `older_than_bp`
- [ ] The **Columns** picker includes `analysis_entity_branch`
- [ ] The **Columns** picker includes `abundance_id`
- [ ] The **Columns** picker includes `relative_dating_id`

---

### 4. Verify Branch Editing Ergonomics

### Steps

1. In `analysis_entity`, open the **Branches** tab.
2. Move `relative_dating` above `abundance`.
3. Save and preview.
4. Move the branches back to the original order.
5. Save again.

### Expected Results

- [ ] Branch reordering works
- [ ] Branch order persists after save
- [ ] Merged preview row order follows branch declaration order
- [ ] Returning branch order to the original sequence restores the original merged row order

---

### 5. Verify Merged Preview Output

### Steps

1. Open `analysis_entity`.
2. Open the preview panel.
3. Keep preview mode on **Merged result**.
4. Inspect the 4 rows.

### Expected Results

- [ ] Preview loads without errors
- [ ] Preview row count is 4
- [ ] `analysis_entity_branch` is visible
- [ ] `analysis_entity_branch` contains both `abundance` and `relative_dating`
- [ ] `abundance_id` is populated only for abundance rows
- [ ] `relative_dating_id` is populated only for relative-dating rows
- [ ] `taxon_name`, `abundance`, `unit` are null-filled for relative-dating rows
- [ ] `dating_label`, `older_than_bp` are null-filled for abundance rows
- [ ] Preview styling highlights the discriminator column
- [ ] Preview styling highlights branch lineage FK columns

---

### 6. Verify Branch Source Preview Mode

### Steps

1. In `analysis_entity`, switch preview mode from **Merged result** to **Branch source rows**.
2. Choose `abundance`.
3. Inspect the rows.
4. Switch to `relative_dating`.
5. Inspect the rows.

### Expected Results

- [ ] Branch-source preview mode is available for merged entities
- [ ] Selecting `abundance` previews `abundance_source` rows only
- [ ] Selecting `relative_dating` previews `relative_dating_source` rows only
- [ ] Branch-source preview is helpful for isolating branch-specific issues
- [ ] Switching back to **Merged result** restores the merged parent preview

---

### 7. Verify Post-Merge `Columns` Restriction

### Steps

1. Edit `analysis_entity`.
2. In the **Basic** tab, set **Columns** to:
   - `analysis_entity_branch`
   - `sample_code`
   - `abundance_id`
   - `relative_dating_id`
3. Save the entity.
4. Refresh preview.

### Expected Results

- [ ] Save succeeds with a non-empty merged `columns` selection
- [ ] Preview still shows all 4 rows
- [ ] Selected output columns remain visible
- [ ] Non-selected branch-only data columns such as `taxon_name`, `abundance`, `dating_label`, and `older_than_bp` are removed from the merged output
- [ ] Identity behavior remains stable after the column restriction

### Reset Step

After this test, clear the `columns` selection again so later tests use the full merged union.

- [ ] `columns` cleared
- [ ] Full merged union returns in preview after save

---

### 8. Verify Validation on the Happy Path

### Steps

1. Run YAML validation on the baseline fixture.
2. Open the validation results.
3. Check **By Entity**.

### Expected Results

- [ ] YAML validation passes or only returns unrelated warnings
- [ ] No merged-specific error is reported for `analysis_entity`
- [ ] `analysis_entity` appears in **By Entity** results cleanly
- [ ] No branch-scoped validation problem appears for the baseline fixture

---

### 9. Verify Downstream FK Usage Through Sparse Branch FKs

### Steps

1. Create `abundance_note` using the fixture above.
2. Save the entity.
3. Preview `abundance_note`.
4. Inspect any linked FK output columns added by the merge relationship.

### Expected Results

- [ ] `abundance_note` saves without FK configuration errors
- [ ] The join through `local_keys: [abundance_id]` to `analysis_entity.remote_keys: [abundance_id]` works
- [ ] The two note rows still exist after linking
- [ ] Each note resolves to the correct abundance branch row in `analysis_entity`

---

### 10. Verify Save/Reopen/YAML Round-Trip

### Steps

1. Open `analysis_entity` in the visual editor.
2. Switch to the **YAML** tab.
3. Confirm `type: merged` and `branches:` are present.
4. Switch back to the **Basic** tab.
5. Save.
6. Close the dialog.
7. Reopen `analysis_entity`.

### Expected Results

- [ ] YAML shows `type: merged`
- [ ] YAML shows both branch entries
- [ ] The visual form still shows both branches after returning from YAML
- [ ] Reopening the entity preserves all merged settings
- [ ] No duplicate or malformed branch entries appear after round-trip edits

---

### 11. Verify Dependency Graph Behavior

### Steps

1. Open the project dependency graph.
2. Locate `analysis_entity`.
3. Inspect inbound dependency edges.
4. Select `analysis_entity`.

### Expected Results

- [ ] `analysis_entity` appears as a merged node
- [ ] `abundance_source` and `relative_dating_source` are shown as direct inputs
- [ ] Branch dependencies are visually distinct from ordinary edges
- [ ] Branch labels or equivalent branch-edge semantics are visible

Note:

- Active selection highlighting of branch-source nodes is currently follow-up work, not a blocker for feature acceptance.

---

### 12. Negative Validation Checks

Run these one at a time. Add the invalid entity, validate, confirm the expected error, then remove it before the next check.

### 12A. Missing `public_id`

```yaml
invalid_merged_missing_public_id:
  type: merged
  branches:
    - name: abundance
      source: abundance_source
      keys: [sample_code, taxon_name]
```

Expected results:

- [ ] Validation flags missing `public_id`
- [ ] Issue appears under the merged entity in **By Entity**

### 12B. Duplicate Branch Names

```yaml
invalid_merged_duplicate_names:
  type: merged
  public_id: invalid_merged_duplicate_names_id
  branches:
    - name: duplicate
      source: abundance_source
      keys: [sample_code, taxon_name]
    - name: duplicate
      source: relative_dating_source
      keys: [sample_code, dating_label]
```

Expected results:

- [ ] Validation flags duplicate branch names
- [ ] Error is clearly associated with the merged entity

### 12C. Missing Branch Source Entity

```yaml
invalid_merged_missing_source:
  type: merged
  public_id: invalid_merged_missing_source_id
  branches:
    - name: missing_source
      source: does_not_exist
      keys: [sample_code]
```

Expected results:

- [ ] Validation flags missing branch source entity
- [ ] The issue is branch-scoped
- [ ] **By Entity** shows branch/source metadata for the failing branch

### 12D. Invalid Branch Keys

```yaml
invalid_merged_bad_keys:
  type: merged
  public_id: invalid_merged_bad_keys_id
  branches:
    - name: abundance
      source: abundance_source
      keys: [sample_code, does_not_exist]
```

Expected results:

- [ ] Validation flags the missing key column
- [ ] The issue is branch-scoped
- [ ] The message mentions the invalid key name

---

### 13. Optional Advanced Checks

Run these if you want broader confidence beyond the core merged workflow.

### Optional A: Extra Columns After Merge

Add a post-merge `extra_columns` value to `analysis_entity`, for example a label that references merged output fields.

- [ ] Extra column can be added to a merged entity
- [ ] Extra column appears in preview
- [ ] Extra column is applied to all merged rows consistently

### Optional B: Drop Duplicates After Merge

Add a duplicate row to one branch and enable a post-merge deduplication configuration.

- [ ] Deduplication applies to the assembled merged result, not only to one branch
- [ ] Resulting row count matches expectations

### Optional C: Branch Order Persistence

- [ ] Branch order survives dialog close/reopen
- [ ] Branch order survives YAML round-trip

---

## Test Completion Criteria

Treat the merged feature as manually verified when all of the following are true:

- [ ] Baseline merged fixture saves successfully
- [ ] Merged preview shows correct row union and sparse FK behavior
- [ ] Branch-source preview works
- [ ] Merged `Columns` field is visible and functional
- [ ] Validation catches merged-specific structural mistakes
- [ ] Branch-scoped validation issues are understandable in the UI
- [ ] Downstream consumer can join through a propagated branch FK column
- [ ] Save/reopen/YAML round-trip preserves merged configuration

---

## Suggested Result Log

Record at minimum:

- browser and OS
- backend branch/commit
- frontend branch/commit
- whether the baseline fixture passed fully
- which negative validation cases passed or failed
- screenshots of merged preview and branch-source preview if behavior looks suspicious