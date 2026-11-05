# Reconciliation Workflow - User Guide

This guide walks you through reconciling project data against the SEAD reconciliation service: finding candidates, reviewing decisions, and exporting accepted results into the mapping sidecar.

For the steps that create a specification, see [Create a Reconciliation Specification](../USER_GUIDE.md#create-a-reconciliation-specification). This guide covers everything after that point.

## What is Reconciliation?

Reconciliation matches local source values (site names, taxon names, method names) to records in SEAD, then stores the selected target IDs in the mapping sidecar. Normalization applies those stored links, so exported data carries the SEAD ID instead of the local text.

Reconciliation does not change `system_id` values. Foreign keys always link on local `system_id` values; reconciliation fills the entity's `public_id` column.

## Prerequisites

Before starting reconciliation:

1. **Project Configuration**: A saved project that contains the entity you want to reconcile
2. **Entity Configuration**: The entity has a data source and the columns needed for matching
3. **Reconciliation Service**: The service is reachable from the backend; the Reconciliation tab shows **Online** with a supported-type count when it answers
4. **Reconciliation Spec**: A specification exists for the entity and target field you want to fill

## Workflow Overview

```text
Configure Specification
   ↓
Find Candidates
   ↓
Review Decisions
   ↓
Export to Mapping
   ↓
Execute / Dispatch
```

---

## Step 1: Configure Reconciliation Specification

### 1.1 Create the Specification

Use **Add Specification** in the project's **Reconciliation → Configuration** tab, or edit the raw YAML. The field-by-field reference is in [RECONCILIATION_SETUP_GUIDE.md](RECONCILIATION_SETUP_GUIDE.md).

A specification is keyed by entity name and target field. The saved catalog looks like this:

```yaml
version: '3.0'
service_url: http://127.0.0.1:8000
entities:
  site:
    site_name:                    # target field
      property_mappings: {}
      remote:
        service_type: site
        columns: []
      auto_accept_threshold: 0.95
      review_threshold: 0.7
      mapping: []
```

The catalog is stored in the project folder as `<project>-reconciliation.yml`. For the default layout that path is `data/projects/<project>/<project>-reconciliation.yml`. Older formats used a `keys` list and an `@include` in the project file; neither is used now.

### 1.2 Fields That Control Matching

- **`remote.service_type`**: The type matched against, for example `site`, `taxon`, or `location`. The usable values come from the service manifest. When it is empty, matching is disabled for that specification.
- **`property_mappings`**: Maps a property the service serves to a local column, which adds context to each query.
- **`review_threshold`**: Marks low-scoring rows for attention in the review grid.
- **`auto_accept_threshold`**: Kept for format compatibility. The grid displays it, and it never accepts a candidate on its own.

### 1.3 Check the Specification Status

The specification row shows a status icon. A red alert means matching cannot run until the problem is fixed.

| Icon | Meaning |
|------|---------|
| Green check | No problems detected |
| Yellow warning | Configuration warning, such as a missing remote type |
| Red alert | Configuration error, such as a missing target field or an unsupported remote type |

Hover the icon to read the details. The checks cover entity existence, target field availability, mapped column availability, and current remote type and property support. See [Specification Validation](RECONCILIATION_SETUP_GUIDE.md#specification-validation) for the full list.

The catalog file can be inspected directly:

```bash
cat data/projects/my_project/my_project-reconciliation.yml
```

## Step 2: Find Candidates

### 2.1 Run the Search

1. Open the project's **Reconciliation** tab and confirm the service chip shows **Online**.
2. Select **Find Candidates** on the specification row.
3. Wait for the progress dialog to finish, then open **Reconcile & Review**.

The search reads the source selected in the specification: the entity's own rows, another entity's rows, or a custom SQL query.

### 2.2 What the Search Reports

| Result | Meaning |
|--------|---------|
| Candidate rows | The row has an encoded business key and candidates to review |
| Missing key | The row has no business key value and cannot be reviewed |
| Duplicate key | Two rows share an encoded business key; the run reports them |
| Missing label | The row has a key but no search label |
| Row error | The row could not be prepared for matching |

Preview failures and matching failures are reported separately from an empty result, so an empty grid does not always mean the service returned nothing.

### 2.3 About Scores and Thresholds

Candidate scores and the thresholds are shown for guidance only. **Matching never accepts a candidate.** Every accepted row requires a reviewer decision, and the threshold values do not change that.

---

## Step 3: Review Decisions

### 3.1 Row Statuses

| Status | Meaning |
|--------|---------|
| Proposed | Candidates exist and nothing is decided yet |
| Accepted | A reviewer selected a candidate; the target ID and candidate URI are recorded |
| Rejected | A reviewer rejected the row |
| Local-only | A reviewer marked the row as intentionally local, with no SEAD ID |

Rows without a decision or candidates are unresolved. Rows without a business key cannot be reviewed.

### 3.2 Decide a Row

1. Filter the grid by status to work through one group at a time.
2. Open the candidate list for a row and check the returned records.
3. Select a candidate, then select **Accept selected candidate**. Use **Reject** or **Local-only** when no candidate applies.
4. Add notes when the decision needs explanation.

Decisions are saved by encoded business key, and running **Find Candidates** again preserves them.

### 3.3 Re-accept Older Decisions

An accepted row that has only a numeric target ID and no candidate URI shows `Accepted · re-accept candidate`. Select the candidate URI again before exporting, because export needs the URI to check the record against SEAD.

### 3.4 Add a Manual Link

Use **Add Manual Link** when you already know the target ID.

1. Enter the encoded business key and an integer target ID.
2. Optionally add notes.

This writes a committed `source: manual` link to the mapping sidecar and does not check the ID against SEAD. During the next normalization that link takes precedence over the fixed row's saved `public_id`, reconciliation links, and imported links.

---

## Step 4: Work Through Candidate Rows

Most rows reach this step with candidates but no decision. Work through them in the grid.

### 4.1 Review Each Candidate

**Via UI:**
1. Filter by **Status: Proposed**
2. For each row:
   - Review your original value in left column
   - Review candidate matches in right panel
   - Each candidate shows:
     - Name
     - Confidence score
     - Additional metadata (if available)

### 4.2 Decision Making Process

For each item, decide:

**Accept a Candidate:**
- Select the candidate row
- Click **Accept selected candidate**
- The decision is recorded with its target ID and candidate URI

**Reject and Search Again:**
- Open the alternative search for the row
- Enter different search terms and run the search
- Review the new candidates
- Accept a candidate if one is correct

**Mark Local-only:**
- Use this when the value must not match a SEAD record
- Click **Local-only**
- Optionally add a reason explaining why

### 4.3 Common Review Scenarios

**Scenario 1: Spelling Variations**
```
Your data:    "Ageröd"
Candidate:    "Ageröd" (score: 0.92)
Action:       ACCEPT - exact match with diacritic variation
```

**Scenario 2: Historical Name Change**
```
Your data:    "Leningrad"
Candidate:    "St. Petersburg" (score: 0.88)
Action:       VERIFY - check if same location, then accept
```

**Scenario 3: Ambiguous Match**
```
Your data:    "Springfield"
Candidates:   "Springfield, MA" (0.85)
              "Springfield, IL" (0.85)
Action:       Check your data for context clues (coordinates, etc.)
```

**Scenario 4: No Good Match**
```
Your data:    "My Local Site XYZ-2024"
Candidates:   None above 0.50
Action:       LOCAL-ONLY - new site not yet in SEAD
```

---

## Step 5: Handle Unmatched Items

Items with no candidates or very low scores need special attention.

### 5.1 Investigate Unmatched

**Common Reasons:**
- New records not yet in SEAD database
- Misspellings or data entry errors in your data
- Different naming conventions
- Very specific local identifiers

### 5.2 Options for Unmatched Items

**Option A: Fix Your Data**
If the problem is a typo or data quality issue:
1. Open the entity and correct the source value
2. Save the project
3. Run **Find Candidates** again; existing decisions are preserved

**Option B: Search With Broader Terms**

The stored value may carry more detail than the SEAD record:

```text
Your data has: "Ageröd I:H Site Complex, Trench 3, Layer 2a"
Search with:   "Ageröd"
```

1. Open the alternative search for the row
2. Try broader or simplified search terms
3. Check parent/child relationships between records

**Option C: Create New SEAD Record**
For genuinely new entities:
1. Document the unmatched item
2. Contact SEAD administrators
3. Submit new record request
4. Re-reconcile after record is added

**Option D: Mark Local-only**
For local-only identifiers that should not be in SEAD:
1. Select the row and click **Local-only**
2. Add a reason for documentation
3. The decision is exported as a committed approval and does not set `public_id`

---

## Step 6: Export to Mapping

Select **Export to Mapping** to copy accepted decisions into the mapping sidecar.

What the export does:

- Checks each accepted candidate URI against SEAD.
- Copies valid decisions into `<project>-mapping.yml` with `source: reconciliation`, `committed_at`, and an owner recorded.
- Does not export a candidate reported as absent or invalid, and removes any older link owned by that specification for the same key. The result lists the key and the reason.
- Exports the link with an empty `verified_at` when the Authority Service is unavailable, and shows it as unverified. Export again after recovery to retry the check.
- Updates only links owned by that specification and removes its stale owned links. Manual links and unowned links are protected.
- Stops without changing the sidecar when a key has a conflicting owner, or when the sidecar metadata does not match.
- Exports local-only decisions as committed, owner-tagged approvals. It does not set `public_id`.

An accepted decision in the catalog does not change normalized IDs until it is exported.

### 6.1 Read the Export Result

| Value | Meaning |
|-------|---------|
| `exported` | Links written to the sidecar |
| `removed` | Stale owned links removed |
| `exported_local_only_approvals` | Local-only approvals written |
| `skipped_manual` | Links skipped because a manual link already exists |
| `outcomes` | Per-key result, with the reason for any key that was not exported |

---

## Step 7: Apply the Links

Normalization applies committed sidecar links in this order, first match wins:

1. Manual links (`source: manual`)
2. Reconciliation links (`source: reconciliation`)
3. Imported links (`source: import`)
4. Draft links with an empty `committed_at` are skipped

Normalization reads the sidecar offline and does not check IDs against SEAD. Run **Execute** or the project's dispatch flow to produce output that carries the applied IDs.

**Example Output:**
```csv
site_name,site_id,latitude,longitude
"Ageröd",1234,56.1234,13.5678
"Tågerup",5678,55.9876,13.1234
```

---

## Step 8: Quality Checks

### 8.1 Check the Decisions

1. Re-run **Find Candidates** and confirm previously reviewed rows still show their decisions.
2. Confirm no rows remain `Proposed` unless you intend to leave them unresolved.
3. Confirm rows you marked local-only show no unexpected `public_id` value.

### 8.2 Check the Export Result

1. Read the export result for keys reported absent or invalid.
2. Confirm `skipped_manual` is expected for the entity.
3. Export again after the Authority Service recovers if any link is shown as unverified.

### 8.3 Spot Check the Output

Check a sample of exported rows in the entity preview or the produced output:

- Applied IDs belong to the record you reviewed.
- Rejected and unresolved rows have no applied ID.
- Local-only rows have no applied ID.

---

## Reconciliation Best Practices

### DO:
- ✅ **Decide every row yourself** - matching never accepts a candidate
- ✅ **Check accepted rows carry a candidate URI** - a numeric ID alone cannot be verified on export
- ✅ **Export to Mapping before expecting output to change** - accepted catalog decisions are not applied links
- ✅ **Record why a row is local-only** - the reason documents the decision
- ✅ **Re-run Find Candidates after changing source data** - existing decisions are preserved

### DON'T:
- ❌ **Treat a high score as a decision** - scores and thresholds are guidance only
- ❌ **Assume an accepted decision is already applied** - only an export writes a committed link
- ❌ **Add a manual link for an ID you have not checked** - manual links are trusted and never verified against SEAD
- ❌ **Expect a local-only decision to set `public_id`** - it records an approval instead

---

## Troubleshooting

### Problem: No Candidates Returned

**Solutions:**
1. Confirm the specification status is not a red alert
2. Confirm `remote.service_type` appears in the service manifest
3. Confirm the source entity has preview rows
4. Confirm the search label column is populated
5. Confirm the backend can reach the service (`GET /api/v1/reconciliation/health`)

### Problem: Service Offline

**Symptoms:** "Connection failed" or "Service unavailable"

**Solutions:**
```bash
# Check the service answers directly
curl http://localhost:8000/reconcile

# Check the backend view of the service
curl http://localhost:8012/api/v1/reconciliation/health

# Check the configured service URL
cat data/projects/my_project/my_project-reconciliation.yml | grep service_url
```

### Problem: Every Row Is Unreviewable

The grid reports missing or duplicate business keys. Check that the entity's configured keys exist, are not blank, and are unique per delivery.

### Problem: Accepted Decisions Do Not Change the Output

Accepted catalog decisions must be exported first. Run **Export to Mapping**, then normalize again.

### Problem: Export Reports a Key as Absent

The candidate URI was not found in SEAD. Re-run **Find Candidates** for that row and select a current candidate.

### Problem: Export Stops on a Conflict

A key is already owned by another specification, or the sidecar metadata does not match. Review the reported key and its current link, then export again.

### Problem: Decisions Do Not Persist

**Solutions:**
1. Check the browser console and the network tab for failed requests
2. Confirm the catalog file at `data/projects/<project>/<project>-reconciliation.yml` is writable
3. Reload the project and check that the decisions are listed again

---

## Advanced Workflows

### Match Several Entities

Each specification is matched separately. Run **Find Candidates** on one specification row at a time, and review it in **Reconcile & Review** before moving to the next.

### Reconciliation API Routes

All routes are under the `/api/v1` prefix.

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/reconciliation/health` | Service status |
| `GET` | `/reconciliation/manifest` | Supported types and properties |
| `GET` | `/projects/{project}/reconciliation` | Read the catalog |
| `PUT` | `/projects/{project}/reconciliation/raw` | Replace the catalog as raw YAML |
| `GET` | `/projects/{project}/reconciliation/available-fields/{entity}` | Columns available for mappings |
| `GET` | `/projects/{project}/reconciliation/{entity}/{field}/preview` | Rows with decisions applied |
| `POST` | `/projects/{project}/reconciliation/{entity}/{field}/auto-reconcile` | Start candidate search |
| `POST` | `/projects/{project}/reconciliation/{entity}/{field}/auto-reconcile-sync` | Run candidate search and wait |
| `GET` | `/operations/{operation_id}/progress` | Progress for a running search |
| `POST` | `/projects/{project}/reconciliation/{entity}/{field}/mapping` | Record a decision |
| `DELETE` | `/projects/{project}/reconciliation/{entity}/{field}/mapping` | Delete a decision |
| `PUT` | `/projects/{project}/reconciliation/mapping-registry/{entity}/{field}` | Update a specification |

### Command-Line Matching Currently Fails

`scripts/auto_reconcile.py` and the `make reconcile` target fail on import because the script uses model names that no longer exist (`EntityMapping`, `EntityMappingRegistry`). Use the web interface or the API routes above until the script is repaired.

---

## Workflow Checklist

- [ ] Specification created for the entity and target field
- [ ] Specification status is not a red alert
- [ ] Service shown as online
- [ ] Candidate search completed
- [ ] Every needed row has a decision
- [ ] Accepted rows carry a candidate URI, not only a numeric ID
- [ ] Export to Mapping completed
- [ ] Export result reviewed for skipped or invalid keys
- [ ] Local-only decisions confirmed
- [ ] Output produced and spot-checked
- [ ] Project backed up

---

## Related Documentation

- [RECONCILIATION_SETUP_GUIDE.md](RECONCILIATION_SETUP_GUIDE.md) - Catalog format, fields, and validation reference
- [Create a Reconciliation Specification](../USER_GUIDE.md#create-a-reconciliation-specification) - First-time setup steps
- [CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md) - Full YAML configuration reference
- [DEVELOPMENT.md](../DEVELOPMENT.md) - Backend development and API details

---

## Getting Help

1. **Service status**: Check the Reconciliation tab chip and `GET /api/v1/reconciliation/health`
2. **Specification status**: Hover the status icon on the specification row
3. **Network tab**: Check browser DevTools for failed requests
4. **Logs**: Check the backend log for reconciliation errors
5. **GitHub Issues**: Report bugs with the specification, the row key, and the full error text

---

**Last Updated:** November 5, 2026  
**Version:** 2.0
