# Pending Release

This snapshot is separate from versioned release notes and must not be published as a release body.

- [PR #649](https://github.com/humlab-sead/sead_shape_shifter/pull/649) Release 2\.6\.0: fix validation message layout, add push\-fix\-pr target (merged 2026-11-03).
  - User-facing release note:
    Validation messages now display in a properly laid-out table, with long messages truncated with an
    ellipsis instead of breaking the layout.
- [PR #650](https://github.com/humlab-sead/sead_shape_shifter/pull/650) chore: promote dev into staging (merged 2026-11-03).
  - Promotes: #649.
- [PR #653](https://github.com/humlab-sead/sead_shape_shifter/pull/653) fix\(paths\): keep directive resolution and materialization portable (merged 2026-11-03).
  - User-facing release note:
    Configuration directives such as @include: ${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml now expand
    correctly when the directory is configured only in .env, and file paths that resolve through a
    symlink now log a warning naming the symlink and its target, making path-containment rejections
    easier to diagnose.
- [PR #656](https://github.com/humlab-sead/sead_shape_shifter/pull/656) Speed up string concat and interpolation; add normalization profiler (merged 2026-11-03).
  - User-facing release note:
    Text interpolation and concatenation in extra-column formulas are now computed column-wise instead
    of row-by-row, which should make normalization of text-heavy projects faster. A new
    scripts/profile_normalization.py tool reports per-entity times and the most expensive functions so
    slow normalization runs can be diagnosed.
- [PR #657](https://github.com/humlab-sead/sead_shape_shifter/pull/657) chore: promote dev into staging (merged 2026-11-03).
  - Promotes: #653, #656.
- [PR #658](https://github.com/humlab-sead/sead_shape_shifter/pull/658) Add FK Link Troubleshooter experiments proposal and fix proposal paths (merged 2026-11-03).
- [PR #659](https://github.com/humlab-sead/sead_shape_shifter/pull/659) Add dev\-to\-staging promotion script (merged 2026-11-03).
  - User-facing release note:
    Maintainers can now prepare and publish a dev-to-staging promotion pull request with
    scripts/promote_dev_to_staging.sh prepare and publish <pull-request-number>, which handles
    provenance verification, draft PR creation, and description generation.
- [PR #660](https://github.com/humlab-sead/sead_shape_shifter/pull/660) Show remote entity from warning metadata in troubleshooter header (merged 2026-11-03).
  - User-facing release note:
    The link troubleshooter dialog now shows the correct entity pair (e.g. "orders → customers")
    immediately when opened, instead of briefly displaying "Unknown entity" while data loads.
- [PR #666](https://github.com/humlab-sead/sead_shape_shifter/pull/666) Scope warm cache by project and entities; purge failed entity data (merged 2026-11-04).
  - User-facing release note:
    Preview and validation results are no longer reused from the wrong project or from a partial run,
    and an entity that fails during normalization no longer appears with half-built data. Results that
    were previously cached incorrectly are now recomputed.
- [PR #667](https://github.com/humlab-sead/sead_shape_shifter/pull/667) chore: promote dev into staging (merged 2026-11-04).
  - Promotes: #658, #659, #660, #666.
- [PR #668](https://github.com/humlab-sead/sead_shape_shifter/pull/668) Derive reconciliation types and properties from the service manifest (merged 2026-11-05).
  - User-facing release note:
    Reconciliation types and their properties are now read from the reconciliation service manifest, so
    a new entity type can be configured without a Shape Shifter code change. Saved specifications that
    use a type or property the service no longer declares stay visible but are clearly marked
    unsupported and blocked from candidate matching until removed or remapped, instead of silently
    attempting matching.
  - Upgrade notes:
    - Existing specifications whose property_mappings reference properties no longer declared for the
    selected remote type remain saved but block candidate matching until the operator removes or remaps
    them in the editor.
     - API consumers: the matching and suggestion endpoints can now return 400 (unsupported type or
    property mapping) and 503 (manifest unavailable or invalid, error code
    RECONCILIATION_MANIFEST_ERROR) where requests previously proceeded to the service.
     - The reconciliation service must publish reconciliation.supportedTypes and a valid
    extend.property_settings array; the Authority Service-side contract change is tracked separately and
    is not part of this repository's diff. No data migrations are included.
- [PR #669](https://github.com/humlab-sead/sead_shape_shifter/pull/669) chore: promote dev into staging (merged 2026-11-05).
  - Promotes: #668.
- [PR #672](https://github.com/humlab-sead/sead_shape_shifter/pull/672) Register SIMS business\-key contracts and fix reconciliation UI (merged 2026-11-06).
  - User-facing release note:
    Change Request runs now confirm the project's business-key declarations with SIMS before sending
    identity work, and a conflicting key list stops the run with a readable conflict message instead of
    silently mismatching identities; project saves no longer block key edits on bound projects. The
    reconciliation review grid scrolls large result sets faster, preview rows load only when the review
    tab is opened, and the editor now uses the clearer "Search Field" and "Another Entity" terminology.
  - Upgrade notes:
    - To enable contract registration, set SHAPE_SHIFTER_SIMS_CONTRACT_CALLER (defaults to
    shape-shifter) and SHAPE_SHIFTER_SIMS_CONTRACT_REGISTRATION_TOKEN to a token matching the SIMS
    caller entry. An unset token keeps registration closed, so Change Request runs stop before any
    identity work.
     - Business-key edits on a bound project now save without a warning and are enforced by the next
    Change Request run. On an HTTP 409 conflict, either restore the registered key list and order or
    move the project to a new metadata.provider_schema value; SIMS exposes no update or retire call for
    a registered contract (see docs/OPERATIONS.md#provider-scope-key-contract-conflicts).
     - Update links to the removed docs/other/RECONCILIATION_SETUP_GUIDE.md and
    docs/other/RECONCILIATION_WORKFLOW.md; both were replaced by docs/other/RECONCILIATION_GUIDE.md.
- [PR #673](https://github.com/humlab-sead/sead_shape_shifter/pull/673) chore: promote dev into staging (merged 2026-11-06).
  - Promotes: #672.
- [PR #674](https://github.com/humlab-sead/sead_shape_shifter/pull/674) Add Foreign\-Key Integrity Troubleshooter phases 1\-3 (merged 2026-11-06).
  - User-facing release note:
    Users can now click "Troubleshoot link" on a foreign-key integrity warning to see the current
    unmatched values behind it, how many local rows each value affects, and a bounded sample of the
    local rows for a selected value, without any risk of changing the project. Warnings that cannot be
    inspected (for example, older warnings without saved-link identity) explain why instead of offering
    the action.
- [PR #675](https://github.com/humlab-sead/sead_shape_shifter/pull/675) chore: promote dev into staging (merged 2026-11-06).
  - Promotes: #674.
- [PR #676](https://github.com/humlab-sead/sead_shape_shifter/pull/676) Default data validation to complete mode and refine link troubleshooter (merged 2026-11-07).
  - User-facing release note:
    Data validation now runs in complete mode by default, so foreign-key warnings are checked against
    full data instead of a 1000-row sample, and link troubleshooting is unavailable for sample results
    with guidance to re-run complete validation. Troubleshooter dialogs open on unmatched rows and no
    longer show a success banner when the warning reproduces as expected.
  - Upgrade notes:
    The default validation_mode on the data-validation endpoint changed from sample to complete. API
    callers that relied on the previous default should pass validation_mode=sample explicitly to retain
    the old behavior. The task-status gate continues to use sample mode internally and requires no
    caller change.
- [PR #677](https://github.com/humlab-sead/sead_shape_shifter/pull/677) chore: promote dev into staging (merged 2026-11-07).
  - Promotes: #676.
- [PR #678](https://github.com/humlab-sead/sead_shape_shifter/pull/678) Use retained snapshots for link troubleshooting experiments (merged 2026-11-07).
  - User-facing release note:
    Link troubleshooting keeps a 15-minute snapshot of the reproduced link. Opening the dialog, or
    refreshing after the snapshot expires, reads current data, while changing the exception group,
    snapshot side, page, or page size reads nothing new. Run trial, Reset, and Close are explicit
    actions, and Reset restores the latest baseline without recomputing it.
  - Upgrade notes:
    The stateless POST /api/v1/projects/{project_name}/link-troubleshooter route and its request and
    response models are removed. API consumers must migrate to POST
    /api/v1/projects/{project_name}/link-experiment-contexts (open), POST .../{context_id}/trials
    (trial), GET .../{context_id} (read the retained baseline), and DELETE .../{context_id} (release).
    
     - Paging fields (page, page_size, row_filter) now return 422 on open and trial requests because the
    request models reject unknown fields.
     - An expired context returns 410 with detail.reason=context_expired and must be reopened from the
    original warning request; unknown or foreign identifiers return a concealed 404.
     - Optional environment overrides: SHAPE_SHIFTER_LINK_EXPERIMENT_MAX_MEMORY_MB (default 100) and
    SHAPE_SHIFTER_LINK_EXPERIMENT_GROUP_ROW_CAP (default 100, max 1000).
     - Retained contexts live in process memory, so the backend still requires a single Uvicorn worker,
    as now recorded in docs/DESIGN.md.
- [PR #679](https://github.com/humlab-sead/sead_shape_shifter/pull/679) test\(api\): expect 405 for removed link troubleshooter route (merged 2026-11-07).
- [PR #680](https://github.com/humlab-sead/sead_shape_shifter/pull/680) chore: promote dev into staging (merged 2026-11-07).
  - Promotes: #678, #679.
- [PR #683](https://github.com/humlab-sead/sead_shape_shifter/pull/683) Restructure Link Troubleshooter as responsive workspace (merged 2026-11-07).
  - User-facing release note:
    The Link Troubleshooter now leads with a plain-language summary of the link problem and arranges
    settings and results side by side on wide screens, with row inspection reachable in one click. After
    running a trial, changing settings keeps the previous comparison visible and clearly marks it as
    stale until the trial is rerun.
- [PR #684](https://github.com/humlab-sead/sead_shape_shifter/pull/684) chore: promote dev into staging (merged 2026-11-07).
  - Promotes: #683.
- [PR #685](https://github.com/humlab-sead/sead_shape_shifter/pull/685) Rework link troubleshooter summary and saved\-relationship display (merged 2026-11-07).
  - User-facing release note:
    The Link Troubleshooter now states up front how many source rows have no match and explains in one
    sentence what the saved join does with them, with the saved-link details condensed to a single line
    and null-key options explained in help tooltips.
- [PR #686](https://github.com/humlab-sead/sead_shape_shifter/pull/686) chore: promote dev into staging (merged 2026-11-07).
  - Promotes: #685.
- [PR #687](https://github.com/humlab-sead/sead_shape_shifter/pull/687) Replace comparison table with single\-result toggle view (merged 2026-11-07).
  - User-facing release note:
    The link troubleshooter results pane now shows one result at a time, with "Saved link" and "Last
    trial" buttons to switch between them instead of a side-by-side comparison table. Count cards show
    source and output row totals at a glance, with a delta against the saved link when viewing trial
    results.
- [PR #688](https://github.com/humlab-sead/sead_shape_shifter/pull/688) chore: promote dev into staging (merged 2026-11-07).
  - Promotes: #687.
- [PR #689](https://github.com/humlab-sead/sead_shape_shifter/pull/689) Add bounded row paging and AG Grid browsing to troubleshooters (merged 2026-11-08).
  - User-facing release note:
    Affected-row lists in the link troubleshooter and the integrity troubleshooter can now be paged
    through up to 10,000 rows instead of stopping at the first 100 (20 for integrity rows), with a
    message when a result set is larger than the browsable window. The troubleshooter dialog can be
    resized by dragging its edge or corner or with the arrow keys, integrity counts appear as
    at-a-glance stat cards with an explanatory tooltip, and the wording now says "configured link"
    instead of "saved link".
  - Upgrade notes:
    Deployers must rename the environment variable SHAPE_SHIFTER_LINK_EXPERIMENT_GROUP_ROW_CAP to
    SHAPE_SHIFTER_LINK_TROUBLESHOOT_BROWSE_ROW_CAP; its default rises from 100 to 10,000 and its allowed
    maximum from 1,000 to 10,000. API consumers calling the integrity troubleshooter may send
    row_offset and row_limit (default 100, max 500) and will see the new offset, limit, browse_cap, and
    browse_cap_reached fields in its rows response; baseline/trial responses now include only the first
    100 rows per exception group, with remaining rows read from the new exception-rows endpoint, which
    requires project:read authorization.
- [PR #690](https://github.com/humlab-sead/sead_shape_shifter/pull/690) chore: promote dev into staging (merged 2026-11-08).
  - Promotes: #689.
- [PR #696](https://github.com/humlab-sead/sead_shape_shifter/pull/696) fix: link troubleshooter UX, validation check selection, and stale (merged 2026-11-08).
  - User-facing release note:
    The row-count troubleshooter now offers an "All" page-size option, a 25,000-row browse cap, and
    tab-style affected-row categories, and the integrity troubleshooter can export all unmatched keys to
    CSV. Data-validation runs now honour which checks are selected, and a stale troubleshooter context
    shows a reopen prompt instead of a "Resource not found" error.
  - Upgrade notes:
    - The default SHAPE_SHIFTER_LINK_TROUBLESHOOT_BROWSE_ROW_CAP changed from 10,000 to 25,000 (maximum
    allowed value also 25,000). Operators who set this variable explicitly should verify the value
    still suits their environment.
     - The integrity troubleshooter API contract changed: the page, row_offset, and row_limit request
    fields were removed, and clients must use the new context-based flow via POST
    …/integrity-troubleshooter/{context_id}/page and DELETE …/integrity-troubleshooter/{context_id}.
     - Context routes that previously returned 404 for unknown identifiers now return HTTP 410 with a
    recoverable stale-context detail; API consumers keying on that status should account for it.
- [PR #697](https://github.com/humlab-sead/sead_shape_shifter/pull/697) Evaluate deferred extra columns before post\-unnest FK linking (merged 2026-11-08).
  - User-facing release note:
    Foreign keys whose local key is a computed extra column based on an unnested column now link
    correctly during normalization instead of failing with a missing-column error, so values such as
    lookup keys and labels derived from unnested data resolve as expected.
- [PR #699](https://github.com/humlab-sead/sead_shape_shifter/pull/699) Add map\_value DSL function for exact categorical value mapping (merged 2026-11-08).
  - User-facing release note:
    A new map_value DSL function lets you map exact input values to typed literals (e.g. 'artificial' →
    1, 'natural' → 2), with an optional fallback for unmapped values. Null inputs pass through
    unchanged.
- [PR #701](https://github.com/humlab-sead/sead_shape_shifter/pull/701) Add DSL functions: split\_part, concat\_ws, regex\_replace, named groups (merged 2026-11-08).
  - User-facing release note:
    Formula expressions can now split delimited strings by index, join optional parts while skipping nulls, perform regex-based replacement, and extract named capture groups—replacing hand-built prefix regexes and deeply nested `replace`/`coalesce` chains.
- [PR #702](https://github.com/humlab-sead/sead_shape_shifter/pull/702) Add direct target\-ID foreign key selector to entity editor (merged 2026-11-10).
  - User-facing release note:
    Project authors can now select direct target model IDs in the entity editor's Basic tab instead of editing YAML by hand. Selecting or clearing a target updates only that value source, existing `system_id` and stale entries are preserved, and validation offers a shortcut to the column settings when a required ID column is missing.
- [PR #703](https://github.com/humlab-sead/sead_shape_shifter/pull/703) docs\(proposals\): add backup proposal and advisor phase plan (merged 2026-11-10).
- [PR #704](https://github.com/humlab-sead/sead_shape_shifter/pull/704) Add copy action to project\.sh for duplicating and adopting projects (merged 2026-11-10).
  - User-facing release note:
    Administrators can now duplicate a project and transfer its ownership in a single command: `project.sh copy --project X --to X-copy --owner B`. The command confirms before acting, supports dry-run, and preserves the copied files unchanged.
  - Upgrade notes:
    `sync-to-deploy` now compares files by checksum rather than modification time and no longer preserves source ownership or timestamps. Deployments relying on timestamp-based incremental sync will see a full content comparison on the first run after this change. No configuration changes are required.
- [PR #705](https://github.com/humlab-sead/sead_shape_shifter/pull/705) Add disposable PostgreSQL container management for integration tests (merged 2026-11-11).
  - User-facing release note:
    Users can now run integration tests that require a PostgreSQL database without needing a persistent instance, as a disposable container can be spun up and torn down automatically.
- [PR #706](https://github.com/humlab-sead/sead_shape_shifter/pull/706) Implement conditional direct\-ID foreign key validation (merged 2026-11-11).
  - User-facing release note:
    Users can now utilize conditional direct-ID foreign keys without triggering reconciliation for valid declarations, improving efficiency in data handling.
- [PR #707](https://github.com/humlab-sead/sead_shape_shifter/pull/707) style\(frontend\): increase fixed values grid header gap to 8px (merged 2026-11-11).
  - User-facing release note:
    The elements in the fixed values grid header are now spaced further apart (8px instead of 4px),
    giving the header a slightly more open layout.
- [PR #708](https://github.com/humlab-sead/sead_shape_shifter/pull/708) build\(make\): add promote\-dev\-to\-staging target (merged 2026-11-11).
- [PR #709](https://github.com/humlab-sead/sead_shape_shifter/pull/709) chore: promote dev into staging (merged 2026-11-11).
  - Promotes: #696, #697, #699, #701, #702, #703, #704, #705, #706, #707, #708.
