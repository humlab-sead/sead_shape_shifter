# Reconciliation Guide

This guide covers the full reconciliation workflow in Shape Shifter: configuring a specification, finding candidates, reviewing decisions, and exporting accepted links so that normalized output carries SEAD IDs.

Reconciliation matches local source values (site names, taxon names, method names) to records in SEAD through an OpenRefine-compatible reconciliation service. The service proposes candidates; a reviewer accepts, rejects, or marks each row local-only. Accepted decisions are exported into the mapping sidecar, and normalization applies them.

Candidate scores and thresholds help a reviewer prioritize rows. They never accept a candidate.

## What Reconciliation Does to Identity

Shape Shifter uses a three-tier identity system. Reconciliation fills the third tier only:

| Tier | Field | Purpose | Affected by reconciliation |
|------|-------|---------|----------------------------|
| Local | `system_id` | Sequential ID used by all foreign keys | No |
| Business | `keys` | Source identifiers used to identify and deduplicate rows | No |
| Global | `public_id` | Target SEAD column; holds the matched SEAD ID | Yes |

Foreign keys always link on local `system_id` values. Reconciliation writes the selected SEAD ID into the entity's `public_id` column by way of the mapping sidecar.

```text
Source rows            Reconciliation service      Mapping sidecar        Exported output
────────────           ──────────────────────      ───────────────        ───────────────
"Norway"        →      candidate, score 0.98  →    "Norway" → 162    →    162
"Sweden"        →      candidate, score 1.00  →    "Sweden" → 205    →    205
```

The `public_id` column is the only column reconciliation writes. A specification's target field selects what is searched; it is not where the result is stored. An entity without `public_id` cannot receive links at all, and a sidecar entry that names a different column is rejected.

## Prerequisites

1. **Project** — a saved project that contains the entity you want to reconcile.
2. **Entity rows** — the entity, or the source named in the specification, must produce rows.
3. **Entity identity** — the entity declares `public_id`, which is the column that receives the matched ID, and declares `keys`, which identify each row.
4. **Backend** — Shape Shifter backend running (default `http://localhost:8012`).
5. **Reconciliation service** — running and reachable from the backend (default `http://localhost:8000`).
6. **Specification** — a specification exists for the entity and target field you want to fill.

## Workflow Overview

```text
Configure specification
        ↓
Find candidates
        ↓
Review decisions
        ↓
Export to mapping
        ↓
Execute or dispatch
```

---

## 1. Configure a Specification

### 1.1 Confirm the Service

Check the service directly, then check the backend's view of it:

```bash
# The service answers with its OpenRefine manifest
curl http://localhost:8000/reconcile

# The backend reports whether it can reach the service
curl http://localhost:8012/api/v1/reconciliation/health
```

The Reconciliation tab shows **Online** with a supported-type count when the backend can reach the service.

### 1.2 Create the Specification

Reconciliation data lives in a separate catalog file. Shape Shifter looks for it in the project folder:

```text
data/projects/<project>/<project>-reconciliation.yml
```

There is no `@include` entry and no `reconciliation:` block in `shapeshifter.yml`. When the file is missing, Shape Shifter starts with an empty catalog.

Open the project's **Reconciliation** tab, then **Configuration**, and select **Add Specification**. Choose the entity and the target field, or edit the raw YAML in the **YAML** tab.

A specification is keyed by entity name, then by target field:

```yaml
service_url: "http://localhost:8000"   # base URL of the reconciliation service

entities:
  site:
    site_name:                          # target field
      source: null                      # null = the entity's own rows
      property_mappings:
        latitude: lat
        longitude: lon
      remote:
        service_type: "site"            # must appear in the service manifest
        columns: []
      auto_accept_threshold: 0.95
      review_threshold: 0.70
      mapping: []
```

You can create several specifications for one entity, one per target field, and specifications for as many entities as the project has. [Catalog Reference](#catalog-reference) shows a complete example.

### 1.3 Choose the Source

`source` selects the rows sent to the service:

| Option | Value | Behaviour |
|--------|-------|-----------|
| Entity preview | `null` or omitted | Uses the entity's own rows. This is the default. |
| Another entity | `"taxon_enriched"` | Uses rows from another entity in the same project. Column checks run against that entity. |
| Custom query | `{data_source, type: sql, query}` | Uses the rows returned by the query. Column checks are skipped because the query defines its own columns. |

Use another entity when a helper entity carries fields the reconciled entity lacks. Use a custom query when you need columns that no entity produces.

### 1.4 Select the Remote Type and Properties

**Remote type.** `remote.service_type` names the type the service matches against. It must appear in the manifest's `reconciliation.supportedTypes` list. That list is the set of types the service actually implements; `defaultTypes` only supplies OpenRefine display names and may include types without matching support.

```bash
curl http://localhost:8000/reconcile | jq '.reconciliation.supportedTypes'
```

When `service_type` is empty, matching is disabled for that specification. A type the service no longer serves is shown as `(unsupported)` or `(cannot be verified)` in the editor and cannot be used.

**Properties.** The manifest's `extend.property_settings` entries declare properties. A property applies to a type when that type appears in the entry's `entity_types` list, and the entry `name` is the key used in `property_mappings`.

```bash
curl http://localhost:8000/reconcile | jq '.extend.property_settings'
```

A type with no property entries is still usable: it matches on the search label alone.

Common patterns:

- **Sites** — coordinates (`latitude`, `longitude`), `country` or `place_name`, and `national_id` when available.
- **Taxa** — `genus`, `family`, and `scientific_name` give the service more to compare.
- **References** — structured identifiers (`doi`, `isbn`) discriminate best, with `year` and `authors` as support.

Do not map a property the manifest does not declare for the selected type. Do not copy property names from a fixed per-type list.

### 1.5 Set the Thresholds

- **`review_threshold`** marks low-scoring rows for attention in the review grid.
- **`auto_accept_threshold`** is kept for format compatibility. The grid displays it, and it never accepts a candidate.

## Specification Validation

The **Configuration** tab shows a status icon on each specification row. Hover the icon to read the details.

| Icon | Meaning |
|------|---------|
| Green check | Valid configuration |
| Yellow warning | Warning, such as a missing remote type |
| Red alert | Error that blocks matching, such as a missing target field or an unsupported remote type |

The checks confirm that the entity still exists, that the target field exists after all transformations, that every mapped source column exists in the output, and that the remote type and its properties are still served.

Column checks read `GET /api/v1/reconciliation/available-fields/{entity_name}`, so they include keys, regular columns, extra columns, foreign-key join columns, and unnest columns. Results are rechecked when a specification changes or the view refreshes.

A red alert names the affected entity, field, or column. Fix the specification, or add the missing column to the entity, then recheck.

---

## 2. Find Candidates

1. Confirm the service chip shows **Online**.
2. Select **Find Candidates** on the specification row.
3. Wait for the progress dialog to finish, then open **Reconcile & Review**.

The search reads the source named in the specification and queries the service once per encoded business key.

The run reports these results separately from an empty match:

| Result | Meaning |
|--------|---------|
| Candidate rows | The row has an encoded business key and candidates to review |
| Missing key | The row has no business key value and cannot be reviewed |
| Duplicate key | Two rows share an encoded business key |
| Missing label | The row has a key but no search label |
| Row error | The row could not be prepared for matching |

Preview failures and matching failures are shown apart from an empty result, so an empty grid does not always mean the service returned nothing.

---

## 3. Review Decisions

### 3.1 Row Statuses

| Status | Meaning |
|--------|---------|
| Proposed | Candidates exist and nothing is decided yet |
| Accepted | A reviewer selected a candidate; the target ID and, usually, the candidate URI are recorded |
| Rejected | A reviewer rejected the row |
| Local-only | A reviewer marked the row as intentionally local, with no SEAD ID |

Rows without a decision or candidates are unresolved. Rows without a business key cannot be reviewed.

### 3.2 Decide a Row

1. Filter the grid by status to work through one group at a time.
2. Open the candidate list for a row and check the returned records.
3. Select a candidate, then select **Accept selected candidate**. Use **Reject** or **Local-only** when no candidate applies.
4. Add notes when the decision needs explanation.

Decisions are saved by encoded business key. Running **Find Candidates** again preserves them.

### 3.3 Re-accept Older Decisions

An accepted row that carries only a numeric target ID and no candidate URI shows `Accepted · re-accept candidate`. Select the candidate again before exporting: export needs the URI to confirm the record exists in SEAD.

### 3.4 Add a Manual Link

Use **Add Manual Link** when you already know the target ID.

1. Enter the encoded business key and an integer target ID.
2. Optionally add notes.

This writes a committed `source: manual` link to the mapping sidecar without checking the ID against SEAD. During the next normalization that link outranks the fixed row's saved `public_id`, reconciliation links, and imported links.

### 3.5 Common Situations

```text
Spelling variation
  Source:     "Ageröd"
  Candidate:  "Ageröd" (0.92)
  Action:     accept — same name, different diacritics

Historical name
  Source:     "Leningrad"
  Candidate:  "St. Petersburg" (0.88)
  Action:     confirm the record is the same place, then accept

Ambiguous name
  Source:     "Springfield"
  Candidates: "Springfield, MA" (0.85), "Springfield, IL" (0.85)
  Action:     use coordinates or other context to choose, or reject

No suitable match
  Source:     "My Local Site XYZ-2024"
  Candidates: none above 0.50
  Action:     mark local-only when the value should not map to SEAD
```

## Handling Unmatched Rows

A row with no candidate, or only low-scoring candidates, needs a reviewer decision:

1. Check the source value for spelling and formatting. Correct it in the entity, save, then search again; existing decisions are preserved.
2. Add property mappings to give the service more to compare.
3. Confirm `service_type` appears in `reconciliation.supportedTypes`.
4. Search again with broader terms from the review grid when the stored value carries more detail than the SEAD record.
5. Mark the row local-only when it should not map to SEAD, or reject it.
6. Coordinate with SEAD administrators when the record belongs in SEAD but does not exist yet.

---

## 4. Export to Mapping

Select **Export to Mapping** to copy accepted decisions into the mapping sidecar.

- Each accepted candidate URI is checked against SEAD.
- Valid decisions are written to `<project>-mapping.yml` with `source: reconciliation`, `committed_at`, and an owner recorded.
- A candidate reported as absent or invalid is not exported, and any older link owned by that specification for the same key is removed. The result names the key and the reason.
- When the Authority Service is unavailable, the link is written with an empty `verified_at` and shown as unverified. Export again after recovery to retry the check.
- Only links owned by that specification are updated; its stale owned links are removed. Manual links and unowned links are protected.
- A key with a conflicting owner, or a sidecar whose metadata does not match, stops the export without changing the sidecar.
- Local-only decisions are written as committed, owner-tagged approvals. They do not set `public_id`.

An accepted decision in the catalog does not change normalized IDs until it is exported.

### 4.1 Read the Result

| Value | Meaning |
|-------|---------|
| `exported` | Links written to the sidecar |
| `removed` | Stale owned links removed |
| `exported_local_only_approvals` | Local-only approvals written |
| `skipped_manual` | Links skipped because a manual link already exists |
| `outcomes` | Per-key result, with the reason for any key that was not exported |

---

## 5. Apply the Links

Normalization applies committed sidecar links in this order, first match wins:

1. Manual links (`source: manual`)
2. Reconciliation links (`source: reconciliation`)
3. Imported links (`source: import`)
4. Draft links with an empty `committed_at`, which are skipped

Normalization reads the sidecar offline and does not check IDs against SEAD. Run **Execute**, or the project's dispatch flow, to produce output that carries the applied IDs.

Applied links always replace the value in the entity's `public_id` column. Four conditions stop the application:

| Condition | Effect |
|-----------|--------|
| The entity has no `public_id` configured | Nothing is applied. This is silent, so check the entity configuration first when exported IDs stay empty. |
| The sidecar has no entry for the entity | Nothing is applied |
| A `local_key` column is missing from the table | A warning is logged and the entity is skipped |
| The link is not committed (`committed_at` is empty) | The row keeps its existing value |

Rows without a matching committed link keep their current `public_id` value, so a fixed row's saved ID, an imported ID, or an ID from an earlier run is not cleared.

```csv
site_name,site_id,latitude,longitude
"Ageröd",1234,56.1234,13.5678
"Tågerup",5678,55.9876,13.1234
```

### 5.1 Quality Checks

- Re-run **Find Candidates** and confirm reviewed rows still show their decisions.
- Confirm no rows remain `Proposed` unless you mean to leave them unresolved.
- Read the export result for keys reported absent or invalid, and confirm `skipped_manual` is expected.
- Spot check exported rows: applied IDs belong to the record you reviewed; rejected, unresolved, and local-only rows have no applied ID.

## Best Practices

- **Decide every row yourself.** Matching never accepts a candidate.
- **Give accepted rows a candidate URI.** A numeric ID alone cannot be verified on export.
- **Export before expecting output to change.** Accepted catalog decisions are not applied links.
- **Record why a row is local-only.** The reason documents the decision.
- **Re-run the search after changing source data.** Decisions keyed by business key survive.
- **Add notes** for manual decisions, uncertainty, and known data problems, for example `"Typo in source: 'Qurcus' → Quercus"`.
- **Materialize slow sources first.** A frozen entity keeps the search input stable. See [Materialized Entities](../USER_GUIDE.md#materialized-entities).
- **Do not add a manual link for an unchecked ID.** Manual links are trusted and never verified against SEAD.
- **Do not treat a high score as a decision.** Scores and thresholds are guidance only.

## Troubleshooting

### No Candidates Returned

1. Confirm the specification status is not a red alert.
2. Confirm `remote.service_type` appears in the service manifest.
3. Confirm the selected source has rows and the target field is populated in them.
4. Confirm the backend can reach the service (`GET /api/v1/reconciliation/health`).
5. Confirm the mapped property names appear in `extend.property_settings` for the selected type.

### Service Offline

```bash
# The service answers directly
curl http://localhost:8000/reconcile

# The backend view of the service
curl http://localhost:8012/api/v1/reconciliation/health

# The configured service URL
grep service_url data/projects/my_project/my_project-reconciliation.yml
```

### Every Row Is Unreviewable

The grid reports missing or duplicate business keys. Check that the entity's configured keys exist, are not blank, and are unique per delivery.

### Accepted Decisions Do Not Change the Output

Accepted catalog decisions must be exported first. Run **Export to Mapping**, then normalize again.

### Exported Links Do Not Reach the Output

The entity has no `public_id` configured, so normalization skips link application without an error. Confirm the entity declares `public_id`, and confirm the sidecar entry names that same column. A sidecar entry naming a different column is rejected during validation.

### Export Reports a Key as Absent

The candidate URI was not found in SEAD. Search again for that row and select a current candidate.

### Export Stops on a Conflict

A key is already owned by another specification, or the sidecar metadata does not match. Review the reported key and its current link, then export again.

### Decisions Do Not Persist

1. Check the browser console and the network tab for failed requests.
2. Confirm `data/projects/<project>/<project>-reconciliation.yml` is writable.
3. Reload the project and check that the decisions are listed again.

### Matching Looks Out of Date

A type or property was removed from the service, or the specification still names one. Open the specification, check the status icon and the remote type list, and pick a type and properties the manifest currently serves.

---

## Catalog Reference

Each specification is stored under `entities.<entity_name>.<target_field>`. The entity name and target field are the key; the remaining fields configure matching.

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `source` | No | Rows used for matching | `null`, `"taxon_enriched"`, or `{data_source: "...", type: "sql", query: "..."}` |
| `property_mappings` | No | Maps a service property to a source column | `{"latitude": "lat", "genus": "genus_name"}` |
| `remote.service_type` | No | Type matched against; must appear in the manifest's `supportedTypes` | `"site"`, `"feature_type"`, `"location"` |
| `remote.columns` | No | Additional columns requested from the service | `[]` |
| `auto_accept_threshold` | No | Retained for compatibility; displayed but never accepts a candidate | `0.95` |
| `review_threshold` | No | Flags low-scoring rows for attention | `0.70` |
| `mapping` | No | Review decisions for this specification | `[]` |

`service_url` is required at the top of the catalog. Each catalog holds one value, so a project matches against one service; use a separate project to match against a different service.

There is no `keys` field in a specification. The search value comes from the target field, and the row is identified by its encoded business key, built from the entity's configured `keys`.

### Decision Records

Each entry in `mapping` records one review decision. The catalog holds decisions; the mapping sidecar holds the links that normalization applies.

```yaml
mapping:
  - local_key_value: undecided        # encoded ordered business key
    source_value: "Slöinge Raä 114"   # search label, not row identity
    status: proposed                  # proposed | accepted | rejected | local-only
    candidates:
      - id: https://w3id.org/sead/id/site/1
        name: Slöinge Raä 114
        score: 100.0
        match: true

  - local_key_value: undecided
    source_value: "Slöinge Raä 114"
    status: accepted
    target_id: 1
    candidate_id: https://w3id.org/sead/id/site/1
    confidence: 1.0
    notes: "Confirmed against the excavation report"
```

An accepted decision requires `target_id`, and only an accepted decision may carry it. `candidate_id` is optional in the file, but export needs it to confirm the record exists in SEAD.

### Example Catalog

One catalog can hold several entity and target field pairs, using all three source options.

```yaml
service_url: "http://localhost:8000"

entities:
  country:
    country_name:                  # own rows
      source: null
      remote:
        service_type: "country"
        columns: []
      mapping: []

  taxon:
    species:                       # rows from another entity
      source: "taxon_with_authors"
      property_mappings:
        genus: genus_col
        family: family_col
      remote:
        service_type: "taxon"
        columns: []
      mapping: []

  bibliographic_reference:
    citation:                      # rows from a custom query
      source:
        data_source: "bibliography_db"
        type: sql
        query: |
          SELECT citation, doi, title, authors
          FROM references
          WHERE doi IS NOT NULL OR isbn IS NOT NULL
      property_mappings:
        doi: doi
        title: title
        authors: authors
      remote:
        service_type: "bibliographic_reference"
        columns: []
      mapping: []
```

When `source` names another entity, that entity must exist in the project file. The catalog stores only its name.

## API Routes

All routes are under the `/api/v1` prefix. `{field}` is the target field name.

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/reconciliation/health` | Service status |
| `GET` | `/reconciliation/manifest` | Supported types and the properties each serves |
| `GET` | `/projects/{project}/reconciliation` | Read the catalog |
| `PUT` | `/projects/{project}/reconciliation/raw` | Replace the catalog as raw YAML |
| `GET` | `/projects/{project}/reconciliation/available-fields/{entity}` | Columns available for mappings |
| `GET` | `/projects/{project}/reconciliation/{entity}/{field}/preview` | Rows with decisions applied |
| `POST` | `/projects/{project}/reconciliation/{entity}/{field}/auto-reconcile` | Start candidate search; returns an `operation_id` |
| `POST` | `/projects/{project}/reconciliation/{entity}/{field}/auto-reconcile-sync` | Run candidate search and wait |
| `GET` | `/operations/{operation_id}/progress` | Progress for a running search |
| `POST` | `/projects/{project}/reconciliation/{entity}/{field}/mapping` | Record a decision |
| `DELETE` | `/projects/{project}/reconciliation/{entity}/{field}/mapping` | Delete a decision |
| `PUT` | `/projects/{project}/reconciliation/mapping-registry/{entity}/{field}` | Update a specification |

Neither candidate-search route accepts a candidate.

### Command-Line Matching Currently Fails

`scripts/auto_reconcile.py` and the `make reconcile` target fail on import because the script uses model names that no longer exist (`EntityMapping`, `EntityMappingRegistry`). Use the web interface or the API routes above until the script is repaired.

## Workflow Checklist

- [ ] Specification created for the entity and target field
- [ ] Entity declares `public_id`, and the sidecar entry names the same column
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

## Related Documentation

- [Create a Reconciliation Specification](../USER_GUIDE.md#create-a-reconciliation-specification) — the same first step, in the shorter user-guide form
- [CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md) — project and entity configuration reference
- [DEVELOPMENT.md](../DEVELOPMENT.md) — backend development and API details
- [OpenRefine Reconciliation API Specification](https://reconciliation-api.github.io/specs/latest/)

## Getting Help

1. **Service status** — the Reconciliation tab chip, or `GET /api/v1/reconciliation/health`
2. **Specification status** — hover the status icon on the specification row
3. **Network tab** — check browser DevTools for failed requests
4. **Logs** — check the backend log for reconciliation errors
5. **GitHub Issues** — report bugs with the specification, the row key, and the full error text

---

**Last Updated:** November 5, 2026
