# Target Model Conformance Manual Test Checklist

## Overview

This checklist is for manually testing the completed target-model-conformance work described by the done proposals that match `TARGET_*`.

It is intentionally:

- extensive enough to cover the full user flow from spec reference to conformance results
- easy to follow by using one small custom fixture plus two existing SEAD example projects
- specific about expected issue codes, exact mutations, and what should still be treated as non-conformant

Use this together with [../TESTING.md](../TESTING.md), [../TARGET_MODEL_GUIDE.md](../TARGET_MODEL_GUIDE.md), and [TEST_RESULTS_TEMPLATE.md](TEST_RESULTS_TEMPLATE.md) if you need to record outcomes.

---

## Scope

This guide verifies:

- `metadata.target_model` support through both `@include:` and inline definitions
- Metadata Editor support for the **Target Model** field
- the **Check Conformance** workflow in the Validate tab
- conformance results appearing under the dedicated **Conformance** panel/category
- core issue families:
  - `MISSING_REQUIRED_ENTITY`
  - `MISSING_PUBLIC_ID`
  - `UNEXPECTED_PUBLIC_ID`
  - `MISSING_REQUIRED_FOREIGN_KEY_TARGET`
  - `MISSING_REQUIRED_COLUMN`
  - `PUBLIC_ID_NAMING_VIOLATION`
  - `INVALID_TARGET_MODEL`
- conservative target-facing column inference using explicit columns, foreign-key-induced columns, and SEAD-style fixture patterns
- strict behavior around alias-like names and direct target relationships

This guide does **not** attempt to manually verify:

- large-scale target-model completeness across every SEAD entity in `sead_standard_model.yml`
- deferred semantic-role heuristics and branch-aware conformance backlog
- automated unit-test coverage for `TargetModelSpecValidator`
- performance, browser compatibility, or accessibility

---

## Preconditions

- Backend running
- Frontend running
- You can create or edit disposable test projects
- You can create small YAML files next to a test project when needed

Recommended environment:

- latest stable Chrome or Firefox
- a disposable project folder under `data/projects/`

---

## Fixture Set

This guide uses three fixtures.

### Fixture A: Minimal Passing Custom Target Model

Create a disposable folder such as `data/projects/target_model_manual_test/`.

Create `mini_target_model.yml` in that folder with this content:

```yaml
model:
  name: Mini Museum
  version: 1.0.0
  description: Small manual test target model for conformance validation.

entities:
  collection:
    role: lookup
    required: true
    public_id: collection_id
    columns:
      collection_name:
        required: true
        type: string
        nullable: false

  artifact:
    role: fact
    required: true
    public_id: artifact_id
    columns:
      accession_number:
        required: true
        type: string
        nullable: false
      collection_id:
        required: true
        type: integer
        nullable: false
    foreign_keys:
      - entity: collection
        required: true

naming:
  public_id_suffix: _id
```

Create `shapeshifter.yml` in the same folder with this content:

```yaml
metadata:
  name: target-model-manual-test
  type: shapeshifter-project
  target_model: "@include: mini_target_model.yml"

entities:
  collection:
    type: fixed
    public_id: collection_id
    keys: [collection_name]
    columns: [collection_id, collection_name]
    values:
      - [null, General Collection]

  artifact:
    type: fixed
    public_id: artifact_id
    keys: [accession_number]
    columns: [artifact_id, accession_number, collection_name]
    values:
      - [null, A-001, General Collection]
    foreign_keys:
      - entity: collection
        local_keys: [collection_name]
        remote_keys: [collection_name]
```

Why this fixture matters:

- it is small enough to edit quickly
- it exercises `@include:` target-model references
- it verifies a required FK and a required target-facing column (`collection_id`) that is satisfied via the FK target's `public_id`, not by a literal `artifact.columns` entry

### Fixture B: Built-In SEAD Negative Fixture

Use the existing file [target_models/examples/sead_missing_sample_group.yml](../../target_models/examples/sead_missing_sample_group.yml).

Before testing, add this field to the `metadata` block:

```yaml
target_model: "@include: resources/target_models/sead_standard_model.yml"
```

Why this fixture matters:

- it intentionally violates the SEAD target model
- it covers required entity, public ID, required FK, and required column failures in one small project

### Fixture C: Built-In SEAD Conservative-Rule Fixture

Use the existing file [target_models/examples/sead_arbodat_core.yml](../../target_models/examples/sead_arbodat_core.yml).

Before testing, add this field to the `metadata` block:

```yaml
target_model: "@include: resources/target_models/sead_standard_model.yml"
```

Why this fixture matters:

- it demonstrates the shipped validator's conservative behavior against a more realistic SEAD-shaped project
- it confirms that some target-facing columns are inferred correctly from unnesting and foreign-key structure
- it also confirms that alias-like names are still treated strictly and are **not** silently accepted

---

## Quick Smoke Test

Use this when you only need a fast confidence check.

### Smoke Checklist

- [ ] Open Fixture A in the editor
- [ ] Confirm the Metadata Editor shows the **Target Model** field
- [ ] Run **Check Conformance** and confirm Fixture A returns zero conformance issues
- [ ] Change `artifact.public_id` from `artifact_id` to `artifact_pk`
- [ ] Re-run **Check Conformance** and confirm the conformance result now contains public-id related failures
- [ ] Open Fixture B and confirm the SEAD conformance result reports the expected missing-entity and wrong-public-id findings
- [ ] Open Fixture C and confirm the result stays limited to the known strictness findings instead of producing broad false positives

---

## Full Manual Checklist

### 1. Verify the Metadata Editor Target Model Workflow

### Steps

1. Open Fixture A.
2. Open the project metadata editor.
3. Locate the **Target Model** field.
4. Confirm it shows the current value as an `@include:` reference.
5. Clear the field, save, and reopen the metadata editor.
6. Re-enter `@include: mini_target_model.yml` using the UI.
7. Save again.

### Expected Results

- [ ] The **Target Model** field is visible in the metadata editor
- [ ] The field accepts an `@include:` value
- [ ] Clearing the field is allowed and persists
- [ ] Re-entering the value persists after save/reopen
- [ ] The editor treats the field as optional rather than required

---

### 2. Verify the Happy Path with an Included Custom Spec

### Steps

1. Ensure Fixture A has `target_model: "@include: mini_target_model.yml"`.
2. Open the **Validate** tab.
3. Click **Check Conformance**.
4. Inspect the result in the **Conformance** section.

### Expected Results

- [ ] The **Check Conformance** button is available
- [ ] The request completes successfully
- [ ] Conformance results appear in their own **Conformance** panel/category
- [ ] Fixture A returns zero conformance errors on the baseline setup
- [ ] The result is clearly separated from structural validation output

Why this should pass:

- `collection` and `artifact` both exist
- both entities use the expected `public_id`
- `artifact` declares a FK to `collection`
- `accession_number` is explicitly present
- `collection_id` is available to the validator through the artifact-to-collection FK target's `public_id`

---

### 3. Verify That Target Models Remain Optional

### Steps

1. In Fixture A, clear `metadata.target_model`.
2. Save the project.
3. Run **Check Conformance** again.
4. Run standard project validation as a control.

### Expected Results

- [ ] Removing `metadata.target_model` does not break the project editor
- [ ] **Check Conformance** completes without crashing
- [ ] The conformance result is empty/valid rather than producing unrelated errors
- [ ] Standard project validation still behaves normally

---

### 4. Verify Inline Target Model Definitions

### Steps

1. Replace Fixture A's `target_model` reference with this inline object:

```yaml
target_model:
  model:
    name: Mini Museum Inline
    version: 1.0.0
  entities:
    collection:
      role: lookup
      required: true
      public_id: collection_id
      columns:
        collection_name:
          required: true
          type: string
          nullable: false
    artifact:
      role: fact
      required: true
      public_id: artifact_id
      columns:
        accession_number:
          required: true
          type: string
          nullable: false
        collection_id:
          required: true
          type: integer
          nullable: false
      foreign_keys:
        - entity: collection
          required: true
  naming:
    public_id_suffix: _id
```

2. Save the project.
3. Run **Check Conformance**.

### Expected Results

- [ ] Inline target-model definitions are accepted
- [ ] Saving succeeds without converting the inline object into an invalid string
- [ ] Conformance still passes on the unchanged baseline entities
- [ ] Reopening the metadata editor preserves the inline structure

---

### 5. Verify Parse Errors for Invalid Target Model Content

### Steps

1. Create `bad_target_model.yml` next to Fixture A with this content:

```yaml
entities:
  broken:
    required: true
```

2. Set `metadata.target_model` to `"@include: bad_target_model.yml"`.
3. Save the project.
4. Run **Check Conformance**.

### Expected Results

- [ ] Conformance does not silently accept the malformed spec
- [ ] A conformance error is reported for `metadata.target_model`
- [ ] The issue code is `INVALID_TARGET_MODEL`
- [ ] The message explains that the target model specification could not be parsed

### Reset Step

Restore Fixture A to the valid target model before continuing.

- [ ] Valid target model restored

---

### 6. Verify Missing Required Entity Detection

### Steps

1. In Fixture A, remove the entire `collection` entity.
2. Save the project.
3. Run **Check Conformance**.

### Expected Results

- [ ] Conformance reports `MISSING_REQUIRED_ENTITY`
- [ ] The affected entity is `collection`
- [ ] The message clearly says the target model requires `collection`

### Reset Step

- [ ] Restore `collection`

---

### 7. Verify Missing and Wrong Public ID Detection

Run these as two separate mutations.

#### 7A. Wrong `public_id`

### Steps

1. Change `artifact.public_id` from `artifact_id` to `artifact_pk`.
2. Save the project.
3. Run **Check Conformance**.

### Expected Results

- [ ] Conformance reports `UNEXPECTED_PUBLIC_ID`
- [ ] The affected entity is `artifact`
- [ ] Conformance also reports `PUBLIC_ID_NAMING_VIOLATION` because `artifact_pk` does not end with `_id`

#### 7B. Missing `public_id`

### Steps

1. Remove `artifact.public_id` entirely.
2. Save the project.
3. Run **Check Conformance**.

### Expected Results

- [ ] Conformance reports `MISSING_PUBLIC_ID`
- [ ] The affected entity is `artifact`

### Reset Step

- [ ] Restore `artifact.public_id: artifact_id`

---

### 8. Verify Required Foreign Key and Required Column Detection

This section confirms both a missing direct target relationship and the loss of a target-facing column that had been satisfied through that relationship.

### Steps

1. In Fixture A, remove the `artifact.foreign_keys` entry to `collection`.
2. Leave the rest of the entity unchanged.
3. Save the project.
4. Run **Check Conformance**.

### Expected Results

- [ ] Conformance reports `MISSING_REQUIRED_FOREIGN_KEY_TARGET`
- [ ] The affected entity is `artifact`
- [ ] Conformance also reports `MISSING_REQUIRED_COLUMN` for `collection_id`
- [ ] This demonstrates that the required target-facing `collection_id` was previously satisfied via the FK target and is no longer inferable once the FK is removed

### Reset Step

- [ ] Restore the `artifact` foreign key to `collection`

---

### 9. Verify Required Column Detection for Explicit Project Columns

### Steps

1. In Fixture A, remove `accession_number` from `artifact.columns`.
2. Also remove it from `artifact.keys` if you added it there.
3. Save the project.
4. Run **Check Conformance**.

### Expected Results

- [ ] Conformance reports `MISSING_REQUIRED_COLUMN`
- [ ] The affected entity is `artifact`
- [ ] The missing column named in the message is `accession_number`

### Reset Step

- [ ] Restore `accession_number`

---

### 10. Verify SEAD Example Fixture with Broad Negative Coverage

### Steps

1. Open Fixture B: [target_models/examples/sead_missing_sample_group.yml](../../target_models/examples/sead_missing_sample_group.yml).
2. Ensure the metadata block includes `target_model: "@include: resources/target_models/sead_standard_model.yml"`.
3. Save the project under a disposable test name if you do not want to edit the example directly.
4. Run **Check Conformance**.
5. Review the **Conformance** results by code and by entity.

### Expected Results

- [ ] The result includes `MISSING_REQUIRED_ENTITY` for `sample_group`
- [ ] The result includes `UNEXPECTED_PUBLIC_ID` for `sample` because it uses `sample_id` instead of `physical_sample_id`
- [ ] The result includes `MISSING_REQUIRED_FOREIGN_KEY_TARGET` for `site` missing `location`
- [ ] The result includes `MISSING_REQUIRED_FOREIGN_KEY_TARGET` for `sample` missing `sample_group`
- [ ] The result includes `MISSING_REQUIRED_FOREIGN_KEY_TARGET` for `analysis_entity` missing `dataset`
- [ ] The result includes `MISSING_REQUIRED_COLUMN` for `sample.sample_group_id`
- [ ] The result includes `MISSING_REQUIRED_COLUMN` for `sample_type.type_name`
- [ ] The result includes `MISSING_REQUIRED_COLUMN` for `method.method_group_id`
- [ ] The result includes `MISSING_REQUIRED_COLUMN` for `analysis_entity.dataset_id`

This fixture is the main manual regression check for the proposal's core rule families.

---

### 11. Verify Conservative Strictness with the Arbodat-Derived SEAD Fixture

### Steps

1. Open Fixture C: [target_models/examples/sead_arbodat_core.yml](../../target_models/examples/sead_arbodat_core.yml).
2. Ensure the metadata block includes `target_model: "@include: resources/target_models/sead_standard_model.yml"`.
3. Save the project under a disposable name if needed.
4. Run **Check Conformance**.
5. Compare the actual issues to the expected narrow set below.

### Expected Results

- [ ] The result includes `MISSING_REQUIRED_COLUMN` for `sample_type.type_name`
- [ ] The result includes `MISSING_REQUIRED_COLUMN` for `method.method_group_id`
- [ ] The result includes `MISSING_REQUIRED_FOREIGN_KEY_TARGET` for `analysis_entity` missing `dataset`
- [ ] The result includes `MISSING_REQUIRED_COLUMN` for `analysis_entity.dataset_id`

Just as important, confirm the validator stays conservative:

- [ ] `location` does **not** incorrectly fail for `location_name`
- [ ] `location` does **not** incorrectly fail for `location_type_id`
- [ ] `sample` does **not** incorrectly fail for `sample_name`
- [ ] Alias-like names remain strict: `sample_type_name` does **not** silently satisfy target column `type_name`
- [ ] Alias-like names remain strict: `sead_method_group_id` does **not** silently satisfy target column `method_group_id`

This scenario verifies the refinement proposal's core decision:

- keep the target model canonical
- keep the validator conservative
- do not invent alias equivalence heuristics

---

### 12. Verify Conformance Presentation in the Validate Tab

Run this on any failing fixture from sections 10 or 11.

### Steps

1. Open the **Validate** tab after a failed conformance run.
2. Inspect the **By Category** and **By Entity** groupings.
3. Open one or more conformance issues.

### Expected Results

- [ ] Conformance issues appear under a dedicated **Conformance** category
- [ ] Conformance issues are distinguishable from structural validation issues
- [ ] Each issue shows a useful message and points to the affected entity
- [ ] The grouping makes it easy to review failures by entity name

---

### 13. Optional Advanced Checks

Run these if you want broader confidence beyond the main acceptance path.

#### Optional A: Full Project Conservative Direct-FK Behavior

Use the full Arbodat project at [tests/test_data/projects/arbodat/shapeshifter.yml](../../tests/test_data/projects/arbodat/shapeshifter.yml), add a SEAD `target_model` reference, and run conformance.

- [ ] Missing direct FK targets are still reported even if some broader project structure might seem to imply them transitively
- [ ] The validator does not treat indirect project paths as proof of direct conformance

#### Optional B: CLI Cross-Check

Run the same project through the CLI conformance entry point:

```bash
python -m src.target_model.conformance \
  --spec resources/target_models/sead_standard_model.yml \
  --project target_models/examples/sead_missing_sample_group.yml
```

- [ ] CLI output matches the same broad issue families seen in the UI

#### Optional C: Developer-Level Spec Validator Check

If you want to directly exercise spec self-consistency checks that are implemented in `src/target_model/spec_validator.py`, run them separately from the normal UI conformance flow.

- [ ] Invalid spec references to unknown FK targets can be detected
- [ ] Invalid `identity_columns` entries can be detected
- [ ] Invalid `unique_sets` columns can be detected

---

## Completion Criteria

Treat the target-model-conformance work as manually verified when all of the following are true:

- [ ] Included target-model references work
- [ ] Inline target-model definitions work
- [ ] Missing or malformed target-model specs fail cleanly
- [ ] Required entity, public-id, FK, naming, and required-column rules are all observable in the UI
- [ ] The dedicated **Conformance** result grouping is usable
- [ ] The bundled SEAD spec produces the expected failures on intentionally broken example projects
- [ ] The validator remains conservative and strict on alias-like or indirect relationships

---

## Suggested Result Log

Record at minimum:

- browser and OS
- backend branch or commit
- frontend branch or commit
- which fixture was tested
- whether the issue codes matched expectations
- screenshots of the Conformance panel for any surprising result