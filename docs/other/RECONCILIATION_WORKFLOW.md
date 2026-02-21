# Reconciliation Workflow - User Guide

This guide walks you through the complete process of reconciling your data against the SEAD authority database.

## What is Reconciliation?

Reconciliation matches your local data (e.g., site names, taxon names) against authoritative records in the SEAD database to ensure consistency and enable proper linking. For example, you might have a site called "Ageröd" in your data that needs to be matched to the official SEAD site record.

## Prerequisites

Before starting reconciliation:

1. **Project Configuration**: Have a valid Shape Shifter project configuration (YAML file)
2. **Entity Configuration**: Entity must be configured with data source and columns
3. **Reconciliation Service**: SEAD reconciliation service must be running and accessible
4. **Reconciliation Spec**: Entity must have a reconciliation specification configured

## Workflow Overview

```
1. Configure Reconciliation → 2. Run Auto-Reconcile → 3. Review Results → 4. Manual Review → 5. Save & Export
```

---

## Step 1: Configure Reconciliation Specification

### 1.1 Define Reconciliation Settings

Create or edit the reconciliation configuration for your entity in the project YAML file:

```yaml
reconciliation:
  entities:
    site:
      # Remote service configuration
      remote:
        service_type: "site"           # SEAD entity type (site, taxon, location, etc.)
        auto_accept_threshold: 0.95    # Auto-accept matches with ≥95% confidence
      
      # Field mappings
      mapping:
        query_name: "site_name"        # Your column with the name to match
        query_id: "site_id"            # Your column for storing matched IDs (optional)
        
      # Optional: Use different data source for reconciliation
      source: "site"                   # Entity name to use (defaults to entity itself)
```

### 1.2 Key Configuration Fields

- **`service_type`**: The SEAD authority type to match against
  - `site`: Archaeological sites
  - `taxon`: Species/taxa
  - `location`: Geographic locations
  - `method`: Analysis methods
  - `sample_type`: Sample types

- **`auto_accept_threshold`**: Confidence score (0.0-1.0) above which matches are automatically accepted
  - `0.95` (95%): Very strict - only exact/near-exact matches
  - `0.85` (85%): Moderate - good matches with minor variations
  - `0.75` (75%): Permissive - accepts fuzzy matches

- **`query_name`**: Column containing the text to match (e.g., site names)
- **`query_id`**: Column where matched SEAD IDs will be stored

### 1.3 Verify Configuration

**Via UI:**
1. Open the project in Shape Shifter editor
2. Navigate to the Reconciliation view
3. Review the **Specifications List** table
4. Check the **Status** column (first column):
   - ✅ **Green check**: Valid configuration - no issues detected
   - ⚠️ **Yellow warning**: Configuration warnings (e.g., missing remote service type)
   - 🔴 **Red alert**: Configuration errors - must be fixed before reconciliation
5. Hover over the status icon to see detailed validation messages

**Validation Checks:**
The system automatically validates each specification against the actual entity structure, including:
- **Entity existence**: Verifies the entity exists in the project
- **Target field availability**: Checks that the target field exists in the entity's output columns
- **Column availability**: Validates all column types are considered:
  1. **Keys** - Entity primary key columns
  2. **Columns** - Regular data columns (excluding value_vars if unnest configured)
  3. **Extra columns** - Dynamically added columns
  4. **FK join columns** - Columns added through foreign key relationships
  5. **Unnest columns** - `var_name` and `value_name` from unnest operations
- **Property mappings**: Ensures mapped source columns exist in entity output
- **Remote service type**: Warns if no service type is configured

**Common Configuration Errors:**
- **Entity not found**: The specified entity has been removed or renamed
- **Target field not found**: The column doesn't exist in the entity's final output
- **Missing columns in mappings**: Property mappings reference non-existent columns
- Check the tooltip on error icons for specific details

**Via CLI:**
```bash
# View reconciliation configuration
cat projects/my_project.yml | grep -A 20 "reconciliation:"
```

---

## Step 2: Run Auto-Reconciliation

Auto-reconciliation queries the SEAD service for all unique values in your data and automatically categorizes matches.

### 2.1 Check Service Health

**Via CLI:**
```bash
# Check if reconciliation service is online
curl http://localhost:8000/reconcile
```

**Via UI:**
1. Navigate to Settings → Reconciliation
2. Check service status indicator (should show green/online)

### 2.2 Run Auto-Reconciliation

**Option A: Using the CLI (Recommended for large datasets)**

```bash
# Basic usage - use configured threshold
python scripts/auto_reconcile.py my_project site

# Custom threshold for stricter matching
python scripts/auto_reconcile.py my_project site --threshold 0.98

# More candidates per query for better options
python scripts/auto_reconcile.py my_project site --max-candidates 10

# Verbose output for debugging
python scripts/auto_reconcile.py my_project site --verbose

# Using Make shortcut
make reconcile ARGS="my_project site --verbose"
```

**Option B: Using the Web UI**

1. Open your project in the editor
2. Navigate to the entity (e.g., "site")
3. Click the **Reconciliation** tab
4. Click **Auto-Reconcile** button
5. Adjust threshold if needed (default: 0.95)
6. Click **Run Reconciliation**
7. Wait for results (progress indicator will show)

### 2.3 Understanding Auto-Reconcile Results

The system categorizes each match into three groups:

| Category | Description | User Action Required |
|----------|-------------|---------------------|
| **Auto-Accepted** ✓ | Score ≥ threshold (e.g., ≥95%) | None - already matched |
| **Needs Review** ⚠️ | Score 80-95% (likely matches) | Manual review recommended |
| **Unmatched** ✗ | No candidates or score <80% | Manual search or create new |

**Example Output:**
```
=== Reconciliation Results ===
  Total queries:      150
  Auto-accepted:      95   (63%)
  Needs review:       42   (28%)
  Unmatched:          13   (9%)
```

---

## Step 3: Review Auto-Accepted Matches

Even auto-accepted matches should be spot-checked for accuracy.

### 3.1 View Auto-Accepted Matches

**Via UI:**
1. In the Reconciliation tab, filter by **Status: Accepted**
2. Review the matches in the grid
3. Each row shows:
   - Your original value
   - Matched SEAD record name
   - Confidence score
   - SEAD ID

### 3.2 Verify Sample Matches

Check a random sample of auto-accepted matches:

```bash
# View sample in verbose CLI output
python scripts/auto_reconcile.py my_project site -v | head -n 50
```

**Red Flags to Look For:**
- Match name doesn't semantically match your data (wrong entity entirely)
- Score is exactly at threshold (95%) - borderline case
- Multiple similar SEAD records exist (check if correct one was chosen)

### 3.3 Reject Incorrect Auto-Accepts

**Via UI:**
1. Click the row in the reconciliation grid
2. Click **Reject Match** button
3. The entry moves to "Needs Review" status
4. Manually select correct match or mark as unmatched

---

## Step 4: Manual Review of "Needs Review" Items

Items with scores between 80-95% require human judgment.

### 4.1 Review Each Candidate

**Via UI:**
1. Filter by **Status: Needs Review**
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
- Click the candidate row
- Click **Accept** button
- The match is confirmed and ID is recorded

**Reject and Search:**
- Click **Search Alternatives** button
- Enter different search terms
- Review new candidates
- Accept if found

**Mark as Unmatched:**
- If no suitable match exists
- Click **Mark Unmatched** button
- Optionally add notes explaining why

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
Action:       MARK UNMATCHED - new site not yet in SEAD
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
1. Go back to Entity Data tab
2. Edit the problematic value
3. Re-run reconciliation for that entity

**Option B: Manual Search with Broader Terms**
```yaml
# Your data has: "Ageröd I:H Site Complex, Trench 3, Layer 2a"
# Search with: "Ageröd"
```
1. Use the manual search feature
2. Try broader or simplified search terms
3. Check parent/child relationships

**Option C: Create New SEAD Record**
For genuinely new entities:
1. Document the unmatched item
2. Contact SEAD administrators
3. Submit new record request
4. Re-reconcile after record is added

**Option D: Accept as Unmatched**
For local-only identifiers that shouldn't be in SEAD:
1. Mark as "Will Not Match"
2. Add notes for documentation
3. These will be excluded from SEAD linking

---

## Step 6: Save Reconciliation Results

### 6.1 Save Configuration

**Via UI:**
1. Click **Save** button in reconciliation tab
2. Reconciliation state is saved to project file
3. Matched IDs are stored in your entity data

**Via CLI:**
The auto-reconcile script automatically saves:
- Updated reconciliation configuration
- Match decisions (accepted/rejected)
- Matched SEAD IDs in designated column

### 6.2 Verify Saved Results

Check that reconciliation data is persisted:

```bash
# View reconciliation state in project file
cat projects/my_project.yml | grep -A 50 "reconciliation:"

# Check that IDs are populated
python scripts/auto_reconcile.py my_project site --verbose
```

### 6.3 Export Final Data

**Export with Matched IDs:**
1. Navigate to Execute tab
2. Select output format (CSV, Excel, Database)
3. Click **Execute Workflow**
4. Your data now includes SEAD IDs in the designated column

**Example Output:**
```csv
site_name,site_id,latitude,longitude
"Ageröd",1234,56.1234,13.5678
"Tågerup",5678,55.9876,13.1234
```

---

## Step 7: Quality Assurance

### 7.1 Review Statistics

**Via CLI:**
```bash
python scripts/auto_reconcile.py my_project site --verbose
```

**Acceptable Benchmarks:**
- **Auto-accept rate**: 60-80% (good data quality)
- **Needs review**: 15-30% (normal variation)
- **Unmatched**: <10% (mostly new records)

**Red Flags:**
- Auto-accept rate <40%: Check threshold, data quality, or service_type
- Unmatched >30%: Wrong service_type or serious data quality issues

### 7.2 Spot Check Final Data

Sample 5-10 random records and manually verify:
```bash
# Export sample and check
python -c "import pandas as pd; df = pd.read_csv('output/site.csv').sample(10); print(df)"
```

Verify:
- IDs are populated for matched records
- IDs correspond to correct SEAD records
- Unmatched records have NULL/empty IDs (as expected)

---

## Reconciliation Best Practices

### DO:
✅ **Start with high threshold (0.95)** - Be conservative initially
✅ **Review a sample of auto-accepts** - Catch systematic errors early
✅ **Document unmatched items** - Keep notes on why no match
✅ **Re-run after data corrections** - Iterate to improve match rate
✅ **Save frequently** - Don't lose manual review work

### DON'T:
❌ **Set threshold too low (<0.85)** - Increases false positives
❌ **Blindly accept all suggestions** - Always validate samples
❌ **Skip unmatched review** - May hide data quality issues
❌ **Modify SEAD IDs manually** - Let reconciliation manage IDs

---

## Troubleshooting

### Problem: Low Auto-Accept Rate

**Symptoms:** <40% auto-accepted

**Solutions:**
1. Check `service_type` matches your data type
2. Review data quality - fix obvious typos
3. Temporarily lower threshold to see if good matches exist at 0.90
4. Check if using correct source entity

### Problem: Service Offline

**Symptoms:** "Connection failed" or "Service unavailable"

**Solutions:**
```bash
# Check service is running
curl http://localhost:8000/reconcile

# Check service URL in configuration
cat projects/my_project.yml | grep service_url

# Verify network connectivity
ping reconciliation-service-host

# Check logs
tail -f logs/endpoint_errors.log | grep '\[RECON\]'
```

### Problem: All Items Unmatched

**Symptoms:** 100% unmatched, even for known good data

**Solutions:**
1. Wrong `service_type` - verify entity type exists in SEAD
2. Wrong `query_name` column - check column name spelling
3. Empty data - verify source entity has data
4. Service error - check service logs

### Problem: Manual Reviews Not Saving

**Symptoms:** Decisions lost after page refresh

**Solutions:**
1. Click **Save** button after each batch of reviews
2. Check browser console for errors
3. Verify project file permissions (should be writable)
4. Check for backend API errors in Network tab

---

## Advanced Workflows

### Multi-Entity Reconciliation

Reconcile multiple entities in sequence:

```bash
# Reconcile all entities in a project
for entity in site taxon location; do
  echo "Reconciling $entity..."
  python scripts/auto_reconcile.py my_project $entity --threshold 0.95
done
```

### Batch Processing

Process multiple projects:

```bash
# Reconcile same entity across projects
for project in project1 project2 project3; do
  python scripts/auto_reconcile.py $project site
done
```

### Custom Thresholds by Entity Type

Different entity types may need different thresholds:

```bash
# Sites - high precision required
python scripts/auto_reconcile.py arbodat site --threshold 0.98

# Taxa - allow more variation (spelling/synonyms)
python scripts/auto_reconcile.py arbodat taxon --threshold 0.90

# Methods - stricter matching
python scripts/auto_reconcile.py arbodat method --threshold 0.95
```

---

## Workflow Checklist

Use this checklist to ensure complete reconciliation:

- [ ] Reconciliation spec configured in project YAML
- [ ] Service health verified (online)
- [ ] Auto-reconciliation executed successfully
- [ ] Auto-accepted matches spot-checked (sample of 10-20)
- [ ] All "needs review" items manually reviewed
- [ ] Unmatched items investigated and documented
- [ ] Reconciliation results saved
- [ ] Final data exported with SEAD IDs
- [ ] Quality assurance checks completed
- [ ] Project backed up

---

## Related Documentation

- [TRACE_LOGGING_GUIDE.md](TRACE_LOGGING_GUIDE.md) - Debugging reconciliation issues
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) - Full YAML configuration reference
- [scripts/README.md](../scripts/README.md) - CLI script usage details
- [BACKEND_API.md](BACKEND_API.md) - Reconciliation API endpoints

---

## Getting Help

If you encounter issues:

1. **Check logs**: `tail -f logs/endpoint_errors.log | grep '\[RECON\]'`
2. **Verbose output**: Run CLI with `--verbose` flag
3. **Network tab**: Check browser DevTools for API errors
4. **Service status**: Verify reconciliation service health endpoint
5. **GitHub Issues**: Report bugs with full error logs

---

**Last Updated:** January 3, 2026  
**Version:** 1.0
