# Reconciliation improvement backlog

**Status:** Working backlog, not yet approved for implementation

**Last updated:** 2026-11-20

**Scope:** The human review workflow in the Reconciliation view, and the matching options that workflow depends on.

## Reconciliation ID flow

See [RECONCILIATION_DIAGRAMS.md](./RECONCILIATION_DIAGRAMS.md) for separate sequence diagrams of candidate search, review decisions, export, manual links, targeted removal (R32), and normalization.

Each item below is intended for its own GitHub issue. The `Tracking issue` line gives a suggested title; replace `TBD` with the number when the issue is created. Where one item unblocks another, the dependency is listed and the issue should reference it. R19 and R20 also need issues in the Authority Service repository for their service changes. R29 needs a companion service issue only if interactive-search fixtures demonstrate a retrieval gap.

This is a working backlog under `docs/proposals/`, not an approved phase plan or a description of shipped behavior. Decide its long-term location when the items are accepted.

## How to read an item

- **Area**: `frontend`, `backend`, or `authority service` (the reconciliation service behind `RECONCILIATION_SERVICE_URL`).

- **Effort**, recorded in the summary table: S is a small local change, M is a few days, L is a larger feature or crosses two services. These are estimates, not commitments.

- **Priority**: Early is in the first recommended improvement set; Next follows that foundation or its listed dependencies; Later is deferred until evidence supports the change; Opportunistic is small work that can fit alongside related changes.

- **Depends on**: an item that must ship first.

- The acceptance criteria are observable checks for closing the issue. Validate them with straightforward, ambiguous, empty-result, and failed-save cases where relevant.

## Workflow foundations

1. Reviewer decisions live in the reconciliation catalog (`shapeshifter.reconciliation.yml`). Normalized output does not change until accepted decisions are exported to the mapping sidecar (`shapeshifter.mapping.yml`). The preview endpoint returns decisions together with their candidates; the mapping endpoint returns the sidecar links. Most "the IDs did not change" confusion comes from this split, so several items below make it visible rather than removing it.

2. Candidate matching is an OpenRefine-protocol call to the service at `RECONCILIATION_SERVICE_URL`, normally `sead_authority_service`. SIMS is a different subsystem: it allocates identities and tracks bindings, and takes no part in candidate search. Matching options therefore belong to the authority service and its manifest, not to Shape Shifter core. The two SIMS items in the original draft are retitled accordingly.

3. For many entities, most rows describe new records. Other rows have abbreviated or non-English labels that require an operator-entered expansion or translation. Search-first review is a primary workflow and does not require batch Find Candidates. Group F owns this improvement area.

4. Search text is separate from source data and row identity. Accepting a manually searched result saves a review decision for export. It is different from R6's trusted manual link, which writes directly to the mapping sidecar.

## Non-goals

- Automatic acceptance of candidates. `auto_accept_threshold` is displayed and never accepts a candidate, and `docs/other/RECONCILIATION_GUIDE.md` states that matching never accepts a candidate. Every item below keeps the operator as the decision maker. A bulk action the operator starts is acceptable; silent acceptance is not.
- Automatic New decisions from empty results, failed searches, or a dataset's expected proportion of new records. New always requires an explicit operator action; a search miss is not proof that the record is absent.

---

## Group A — Faster review workflow

R4 needs API support to restore an undecided proposal. R9 and R10 need backend export rules, not browser-only estimates.

### R1. Show the top candidate in the review grid and accept it in one click

**Tracking issue:** `TBD` — "Reconciliation: show top candidate in the grid and accept it in one click" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** To accept a candidate from the grid, a reviewer must open the `Review (n)` dialog and choose a candidate. The grid renders `Selected target ID` (`target_id`), which stays empty until acceptance, even though the preview payload already includes each row's `candidates`.

**Change.**

- Add a `Top candidate` column showing name, numeric ID, and score (or "no score"). Define the ordering for ties and missing scores; mark alternatives as ambiguous when they are close enough to make a one-click choice unclear.

- Add an explicit one-click accept using the existing decision action and candidate URI ID extraction. Never accept automatically.

- Disable acceptance when the URI cannot yield a valid target ID; keep comparison of alternatives available.

**Acceptance criteria.**

- A proposed row with candidates can be accepted without opening a dialog.

- The displayed candidate follows the defined ordering, ties and missing scores are handled consistently, and close alternatives are identified as ambiguous.

- A candidate with a non-numeric URI cannot be accepted from the grid; a save failure remains visible.

### R2. Update the row from a saved decision without reloading the preview

**Tracking issue:** `TBD` — "Reconciliation: update saved decisions without reloading the preview" (labels: `reconciliation`, `frontend`, `performance`)

**Problem.** `updateMapping` in `frontend/src/stores/reconciliation.ts` awaits `loadEntityResolutionCatalog` and `loadPreviewData` after every decision. `loadPreviewData` calls the preview endpoint, which resolves the source rows and re-runs normalization for the whole entity. On a large entity, this can make each decision wait on work across all preview rows.

**Change.**

- Save the decision, then patch only the decided row in the stored preview from the server response and request. This is an acknowledged update, not an optimistic one; add optimism only if save latency still warrants it.

- Use the returned catalog to update decision state without an entity-wide preview reload. Keep other rows usable and preserve focus, scroll, filter, and sort.

- Add an explicit `Refresh` control; reload on a detected conflict or inconsistent state and after export or a selection change. Keep the saved catalog authoritative for export, not the patched preview.

**Acceptance criteria.**

- The saved status appears without an entity-wide preview request; other rows remain usable during the save.

- A failed save leaves the previous row unchanged and shows the error; focus and scroll remain in place.

- Export results are unchanged compared with the current behaviour.

### R3. Add a keyboard review loop

**Tracking issue:** `TBD` — "Reconciliation: keyboard review loop for accept, reject, new, and search" (labels: `reconciliation`, `frontend`, `ux`, `accessibility`)

**Problem.** Every row action is a mouse target inside a cell renderer, and the grid sets `suppressRowClickSelection`. A reviewer working through hundreds of rows cannot keep their hands on the keyboard, which is the main cost of a long session.

**Change.**

- Bind `Enter` to open review, `A` to accept the displayed candidate explicitly, `R` to reject, `N` to mark New, `S` to search alternatives, and `J` / `K` to move through visible rows.

- Advance to the next row needing review only after a successful save, following the visible filter and sort.

- Ignore the bindings while focus is in a text field, a dialog input, or the quick-search box, and list the bindings in the existing help dialog.

**Acceptance criteria.**

- A full accept-and-advance cycle works without the mouse.

- Enter alone never accepts a candidate, and a failed save does not advance.

- Typing in search or in a dialog does not trigger row actions.

- The help dialog lists the bindings.

### R4. Undo the last decision

**Tracking issue:** `TBD` — "Reconciliation: undo the last review decision" (labels: `reconciliation`, `frontend`, `backend`)

**Problem.** Each decision is written to the catalog immediately, and nothing reverses an accidental click. A fast review loop increases the chance of one.

**Change.**

- Extend the decision API to restore a previous proposal (`proposed` is not currently accepted by `DecisionUpdateRequest`) as well as a previous decided state. Preserve the previous status, target ID, candidate URI, notes, and proposal data; do not turn an undecided proposal into a hidden or empty catalog entry.

- Keep a bounded in-memory undo stack per project, entity, and target field. Show Undo next to decision feedback; clear it on reload or conflicting external changes.

- If the undone decision was already exported, mark its sidecar effect as unapplied (R9). Undo changes the catalog, not the sidecar.

**Acceptance criteria.**

- Undo restores status, target, URI, notes, and original proposal candidates for both a previous decision and a previously proposed row.

- Undo is unavailable when the stack is empty, after reload, or when the saved state has changed externally; errors are shown.

- Undo after export does not claim that the sidecar changed; R9 shows the outstanding update.

**Depends on:** R2 and R9, so the restored row updates without a full preview reload and post-export undo is reported accurately.

### R5. Use a Needs review queue

**Tracking issue:** `TBD` — "Reconciliation: show rows needing review, including proposed matches" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** `statusFilter` starts at `all`; the existing `Unresolved` filter excludes proposed rows with candidates. Defaulting to it would hide the rows where one-click acceptance is most useful. The displayed decision confidence is not a suitable score for sorting undecided proposals.

**Change.**

- Default to `Needs review`: undecided rows and proposed rows, with or without candidates. Retain access to all decided rows.

- Add `Ready to decide`, `Ambiguous`, `No candidates`, and `Errors` views; show counts and explain which rows have no usable business key.

- Sort by top candidate score (not saved decision confidence). Offer `Best matches first` and `Needs investigation first`, with stable order and a defined place for missing scores; do not impose ascending score by default.

- Add a `Below review threshold` filter driven by `entitySpec.review_threshold`, including rows with no candidate score. Share filter/sort persistence with R8.

**Acceptance criteria.**

- Opening review includes proposed rows with candidates and undecided rows; category counts agree with the rows shown.

- Threshold filtering uses candidate scores (not decision confidence) and includes missing scores.

- The selected sort and filter survive a tab switch; ties and missing scores remain in a predictable order.

**Depends on:** R1 for top-candidate score display and sorting only; basic Needs review membership and search-first navigation do not require it. R8 extends the local filter/sort state across visits.

### R6. Choose a manual link target by search instead of typing an ID

**Tracking issue:** `TBD` — "Reconciliation: pick the manual link target from a search" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** The manual link form requires the reviewer to type an encoded business key and a numeric target ID by hand. Both are looked up manually today, and a wrong ID is written as a trusted link that is never checked. The suggest endpoint and a working search dialog already exist.

**Change.**

- Reuse a search picker for the manual link form and alternative candidate review, with the destination explicit: `Accept candidate` saves a review decision for later export; `Save trusted manual link` writes to the sidecar immediately.

- Fill the target ID from a selected result and prefill the encoded business key from the row.

- Keep direct ID entry as a secondary option, and keep the existing messages that state the link is trusted and unchecked.

**Acceptance criteria.**

- A manual link can be created by searching and selecting a result.

- Candidate acceptance and a trusted manual link have distinct labels, destinations, and side effects; the stored manual link keeps its existing source and notes.

- The unchecked-link warning remains visible before saving.

Group F extends free-text search as a primary review workflow. R6 shares its picker, but keeps the trusted manual-link save action separate.

### R7. Record notes and preset reasons on every decision type

**Tracking issue:** `TBD` — "Reconciliation: record notes and preset reasons on all review decisions" (labels: `reconciliation`, `frontend`, `audit`)

**Problem.** Notes can only be entered in the manual link and New dialogs. `persistDecision` passes no notes when rejecting, so the reason for a rejection is lost even though the request model supports notes. Reviewers who want to record a reason must add a manual link or nothing.

**Change.**

- Accept optional notes for all decisions, including rejection, and allow editing them after a fast decision.

- Offer action-appropriate reasons as text; for example, "record missing from SEAD" belongs with New, not rejection.

- Show existing notes on hover or in an expanded row, without opening a dialog.

**Acceptance criteria.**

- A rejection can carry a note that survives a reload.

- Preset reasons are stored as readable text; edits preserve existing notes unless deliberately cleared.

- Rows with notes are identifiable in the grid.

### R8. Keep the reviewer's place between visits

**Tracking issue:** `TBD` — "Reconciliation: remember review context between visits" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** `ReconciliationView` resets state on mount and selects the first reconcilable entity, and the grid's filter and search are local refs. Returning to a half-reviewed entity means finding the same specification, filter, and search text again.

**Change.** Store the active tab, selected entity and target, queue/filter, sort, search text, focused business key, and scroll position per project and specification using the store and `localStorage`. Restore a key only if it still exists; fall back to Needs review when stored selections or filters are invalid. Share the filter/sort mechanism with R5.

**Acceptance criteria.**

- Reloading restores the tab, entity, target, filter, sort, search, focused key, and approximate scroll position.

- A removed specification falls back to the first reconcilable entity without an error.

- Switching project does not carry the previous project's selection.

**Depends on:** R5 for the Needs review filter to restore.

### R9. Show unapplied changes and verification status

**Tracking issue:** `TBD` — "Reconciliation: show unapplied changes per specification" (labels: `reconciliation`, `frontend`, `backend`, `ux`)

**Problem.** Catalog decisions do not change normalized output until Export to Mapping runs. Counting accepted rows not yet exported misses changed targets, rejected former acceptances, New approvals, and removals. A successful export can still leave skipped, unverified, or failed rows requiring attention.

**Change.**

- Compute the difference on the backend between saved decisions and links/approvals owned by that specification in the sidecar: new and changed targets, links to remove, New approvals to add or remove, and notes that export would update. Do not treat a manual or other protected link as an exported reconciliation link.

- Return counts and affected keys, including blocked/protected links, accepted decisions missing a candidate URI, and links awaiting verification. Expose them in the review header and specification list; distinguish unapplied changes from pending verification.

- Recompute after export and undo. Do not clear the badge merely because the export route returned success; retain skipped, unsuccessful, and unverified rows for follow-up.

**Acceptance criteria.**

- New acceptances, changed targets, rejection of an exported acceptance, and New approvals each produce the appropriate outstanding add, change, or removal count.

- An export that fully applies the saved decisions clears their unapplied counts; skipped, blocked, failed, and unverified rows remain visible with the correct reason.

- A manual link on the same key does not make an accepted decision look exported, and undo after export leaves an unapplied change until re-export.

### R10. Check export readiness before writing

**Tracking issue:** `TBD` — "Reconciliation: pre-export check for rows that cannot be exported" (labels: `reconciliation`, `frontend`, `backend`)

**Problem.** `export_to_mapping` validates local inputs before writing, but remote verification reports per-row `not_found`, `invalid_candidate`, and `unverified` outcomes during export. The UI shows the result afterward in a snackbar, and the reviewer has to find affected rows again by key.

**Change.**

- Reuse backend export preflight rules in a read-only check: show blocking conflicts and invalid accepted decisions separately from protected links that would be skipped and informational unfinished proposals.

- Show counts and keys with a path back to review. Do not force an extra confirmation on clean exports.

- Report remote candidate verification as pending until export runs; it can fail or become unavailable after a read-only check. Do not promise that preflight predicts remote results.

**Acceptance criteria.**

- Predictable blocking and skipped keys agree with export for an unchanged catalog and sidecar; later remote verification failures are reported separately.

- The check writes nothing.

- A clean check does not add a confirmation step, and continuing after a warning preserves export's existing rules.

### R11. Allow two-line column headers

**Tracking issue:** `TBD` — "Reconciliation: allow two-line column headers" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** Column widths are fixed and headers are single-line, so long headers are truncated. Several headers are long by construction: the search label column is built as `"<field> (Search label)"`, and the grid also carries `Selected target ID`, `Current ID`, and `Row errors`.

**Change.**

- Enable ag-Grid header text wrapping and let the header height follow its content, with a maximum of two lines and top-aligned text. Retain full names in tooltips.

- Shorten the labels before wrapping, for example `Search label`, `Selected ID`, `Current ID`, `Errors`. Wrapping alone will not fix a header that repeats the field name the column already shows.

- Keep the total grid width close to today's so no column is pushed off screen at the default window size.

**Acceptance criteria.**

- At the supported default window size, known headers are readable; arbitrary configured field names have a full-text tooltip when two lines do not suffice.

- Header text is top-aligned and occupies at most two lines.

- Row height and visible row count are unchanged.

Candidate headers, from the original draft:

| Review | Location Type | Selected |

| ------ | ------------- | -------- |

| Status | Label         | Target ID |

---

## Group B — Reduce matching work

### R12. Send each distinct query once

**Tracking issue:** `TBD` — "Reconciliation: deduplicate identical candidate queries" (labels: `reconciliation`, `backend`, `performance`)

**Problem.** `ReconciliationQueryService.create` builds one query per row, named `q{index}`. Repeated effective queries are sent again even when labels and mapped properties agree. A 500-row entity with 40 distinct matching inputs creates 500 query entries, sent in batches rather than as 500 separate HTTP requests.

**Change.**

- Key queries by the full effective request (service type, label, mapped properties, limit, and matching options), and map each query to the row indexes that use it.

- Fan the returned candidates back out to every row in that list.

- Keep the per-row error reporting and the duplicate business key handling unchanged.

**Acceptance criteria.**

- Identical effective queries issue one query each; differing properties, types, limits, or options are not merged.

- Every row still receives candidates, its own proposal, and its own business-key decision and error.

- Query counts fall for a repeated-input fixture without changing results.

### R13. Re-match only rows that need it

**Tracking issue:** `TBD` — "Reconciliation: reuse unchanged matching outcomes" (labels: `reconciliation`, `backend`, `performance`)

**Problem.** `create` already skips rows whose saved decision is not `proposed`, so accepted, rejected, and local-only rows are not re-sent. Every remaining proposed row is re-queried on each Find Candidates run, including rows that already hold candidates and whose source value has not changed.

**Change.**

- Persist a fingerprint of all effective query inputs and the outcome of each successful search, including an empty candidate list. Reuse an outcome only if inputs and matching configuration are unchanged.

- Report reused rows separately from queried rows; distinguish row counts from distinct queries.

- Add an explicit `Refresh all suggestions` control for remote changes. Preserve accepted, rejected, and New operator decisions; do not silently replace them.

**Acceptance criteria.**

- A second run issues no query for unchanged successful searches, including empty results; changed inputs and matching options cause a new search.

- Existing proposals, notes, and decided rows survive reuse and refresh.

- Refresh all suggestions re-queries eligible rows while preserving operator decisions.

### R14. Run matching through the progress endpoint

**Tracking issue:** `TBD` — "Reconciliation: use the async matching endpoint with progress and cancel" (labels: `reconciliation`, `frontend`, `backend`)

**Problem.** The view calls the synchronous route and shows no progress, so a slow entity looks hung. The asynchronous route, the progress routes, the SSE stream, the cancel route, `ReconciliationProgressDialog.vue`, and `autoReconcileAsync` in the store all exist and are unused by this view.

**Change.**

- Start matching through the async route, stream progress into the existing dialog, and offer cancel. Repair the dialog's cancellation path, which currently repeats `/api/v1` despite the client base URL including it.

- Define how a disconnected stream reconnects or retrieves the final result; retain operation status until the client can retrieve it rather than cleaning up on disconnect.

- Report rows processed and distinct queries separately. Keep the summary alert and reload the preview only after successful completion.

**Acceptance criteria.**

- Progress advances with identifiable row and query counts; completion yields a summary and refreshed preview.

- Cancel requests the correct endpoint, reaches a final cancelled state, and leaves saved catalog data readable.

- A disconnected stream can recover the final status/result; failures surface an error rather than appearing successful.

### R15. Make the candidate limit configurable

**Tracking issue:** `TBD` — "Reconciliation: make the candidate limit effective per specification" (labels: `reconciliation`, `backend`, `configuration`)

**Problem.** `auto_reconcile_entity` defaults `max_candidates` to 3 and the routes do not provide a per-specification value. The Authority Service may also use its own default rather than the requested query limit, so an effective end-to-end limit must be verified before promising a fixed number of candidates.

**Change.**

- Add an optional candidate count to the specification, with a documented default of 3, a permitted range of 1 to 10, and validation that rejects values outside it.

- Pass the value through both matching routes and the query limit. Coordinate with the Authority Service to honor that limit end to end; consider `Load more candidates for this row` separately.

**Acceptance criteria.**

- With at least six available matches, a specification requesting six can display six candidates; default behavior is preserved and the service does not silently cap the result below the requested limit.

- A value outside the permitted range is rejected by validation with a clear message.

- Existing specifications without the field keep the current behaviour.

**Depends on:** Authority Service support for honoring the requested query limit.

---

## Group C — Batch decisions

### R16. Add a batch decision endpoint

**Tracking issue:** `TBD` — "Reconciliation: batch decision endpoint" (labels: `reconciliation`, `backend`, `api`)

**Problem.** `update_mapping` takes the project lock, loads the catalog, applies one decision, and saves the catalog. The client also reloads the catalog and the preview after each decision. Any bulk action built on the current route is a loop that is slower than clicking.

**Change.**

- Add a route that accepts a list of decisions for one entity and target field, takes the lock once, loads the catalog once, applies every valid decision, and saves once.

- Reject duplicate keys in a request before writing. Validate remaining entries independently: report unknown keys and invalid accepted-candidate decisions per entry while saving valid entries together. If the catalog write fails, fail the whole write rather than reporting success for unsaved entries.

- Return saved decision data so the UI can patch rows. Detecting a decision changed since selection belongs to R33.

- Keep the single-decision route for compatibility.

**Acceptance criteria.**

- A request with N valid decisions produces one catalog write and returns N saved decisions.

- Duplicate keys reject the request without writing; independently invalid entries are reported per key while valid entries persist.

- A write failure reports no entries as saved; a stale edit is reported as a conflict once R33 adds the expected decision state.

### R17. Add bulk actions to the review grid

**Tracking issue:** `TBD` — "Reconciliation: bulk accept, reject, and mark New" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** The original draft proposed bulk actions, but the grid currently has no row selection. Reviewing many rows with the same clear outcome therefore requires one decision and one request per row.

**Change.**

- Add multi-row selection with checkboxes, following the pattern already used in `FixedValuesGrid.vue`. Make actions apply to explicitly selected visible rows only; do not silently act on hidden selections or all filtered rows.

- Offer three actions on the selection: accept top candidate, reject, and mark New. Show eligible and skipped counts and confirm before applying; explain that New approves new-record handling and may permit later ID allocation.

- Skip and count rows that cannot take the action, for example rows without a business key or without a candidate for accept.

- Send the decisions through R16 and refresh once.

**Acceptance criteria.**

- Only the visible selected rows are acted on; filter changes do not leave hidden selections to be applied accidentally.

- Rows that cannot accept are reported before submission; the number saved and skipped is shown afterward.

- One request is issued per bulk action.

**Depends on:** R16.

### R18. Review equivalent-query groups

**Tracking issue:** `TBD` — "Reconciliation: review rows with equivalent matching inputs together" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** A shared label does not establish a shared target: sites and locations can share names but differ in country, coordinates, or other mapped properties. Label-only propagation risks writing incorrect decisions across business keys.

**Change.**

- Offer an explicit group view for rows with the same effective matching inputs, including label and mapped properties. Show differences, candidate details, business keys, and existing decisions before any shared action.

- Offer application to eligible rows after confirmation. Never infer identity from the label alone; keep a separate decision for each key.

- Send changes through R16 and report rows with a different existing decision without overwriting them.

**Acceptance criteria.**

- Rows with the same label but different mapped properties are not grouped by default.

- An explicitly confirmed group action saves one decision per eligible business key; conflicting decisions remain unchanged and are listed.

- One request writes the selected eligible decisions.

**Depends on:** R16.

---

## Group D — Matching options (authority service)

These two items are owned by `sead_authority_service`, not by SIMS. They are listed here because they change what the review grid receives and how the specification configures it. Each needs a separate issue in that repository plus the Shape Shifter passthrough described below.

### R19. Partial matching; assess wildcard syntax separately

**Tracking issue:** `TBD` — "Candidate matching: evaluate token and substring matches" (labels: `reconciliation`, `matching`, `configuration`)

**Problem.** A reported search for `Sub-country administrative region` finds the target only when `administrative` is spelled out in full. Token or substring matching may help when the source supplies only part of a value.

**Change.**

- Reproduce the reported failed search with a small fixture; check whether interactive alternative search can solve it before changing matching for an entire specification.

- If partial matching is needed, add an opt-in token or substring strategy in the Authority Service and report the matched text and match kind alongside fuzzy matches. Pass the setting through Shape Shifter with an agreed query parameter/header and manifest capability.

- Treat wildcard patterns as a separate follow-up decision requiring syntax, escaping, and literal-character rules; do not conflate wildcards with partial matching in the first implementation.

**Constraint.** Partial hits must carry a score and match explanation so reviewers can distinguish them from full-label hits.

**Acceptance criteria.**

- A representative failing search finds the expected target through interactive search or, if needed, opt-in partial matching; disabled matching preserves current results.

- Each candidate from a partial match states its score, matched text, and match kind.

- The option is rejected by validation when the service manifest does not list support.

### R20. Multilingual matching

**Tracking issue:** `TBD` — "Candidate matching: multilingual label matching" (labels: `reconciliation`, `matching`, `configuration`)

**Problem.** Matching reportedly fails when the source and stored values express the same concept in different languages.

**Change.**

- Prefer curated, type-specific aliases with a recorded language, because reviewers can inspect the equivalent term that produced a candidate.

- Only then consider runtime translation or language detection. Rank using context and identifiers as well as label similarity; an approved equivalent term need not always rank below an unrelated same-language exact label.

- Keep exceptions explicit: a scientific or archaeological term may have no translation.

**Acceptance criteria.**

- A value in language A matches a stored value in language B, and the candidate names the alias and language used.

- Ranking fixtures distinguish an approved equivalent term with matching context from a misleading exact-label match.

- Disabling the option restores current results.

---

## Group E — Review continuity and repair

### R21. Keep the review pane open while moving between rows

**Tracking issue:** `TBD` — "Reconciliation: persistent pane for sequential review" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** The current dialog requires repeated open/close steps to inspect candidates, source context, notes, and alternative search across consecutive rows. One-click acceptance helps obvious matches but not ambiguous ones.

**Change.**

- Selecting a row opens a side pane with available source context, candidate names/IDs/scores, alternative search, notes, and decision controls. Keep the pane open while moving to another row.

- Start with fields already returned in the preview; richer remote previews are separate work. Reuse the same decision actions as the grid so pane and row stay synchronized.

- Alternative search should discard late responses from older searches, clear an obsolete selection when the query changes, and keep the pane/dialog open if a save fails. R26–R31 define the dedicated search-first workflow within this pane; reuse one search component and request-state mechanism.

**Acceptance criteria.**

- Ten consecutive rows can be reviewed without repeatedly opening and closing a dialog.

- Candidate selection and notes follow the active row; a failed save shows an error without discarding the selection.

- Rapid successive alternative searches cannot show or accept a stale result.

### R22. Flag changed source inputs on previously reviewed rows

**Tracking issue:** `TBD` — "Reconciliation: flag reviewed decisions after source inputs change" (labels: `reconciliation`, `frontend`, `backend`, `audit`)

**Problem.** A prior accepted, rejected, or New decision can remain visible after the source label or mapped context changes. It may then look freshly reviewed even though its basis changed.

**Change.** After R13 establishes how input fingerprints are stored, compare each reviewed row's current matching inputs with the inputs used for its decision. Keep operator decisions unchanged, but flag affected keys and changed inputs for reassessment; clearing the flag requires an explicit review action.

**Acceptance criteria.**

- Changing a reviewed row's mapped country, coordinate, or label flags the row without silently removing its decision.

- Unchanged inputs do not flag the row; reopening the review makes the change visible.

- The operator can re-review and clear the flag after comparing the saved and current matching inputs.

**Depends on:** R13.

### R23. Defer difficult rows without making a decision

**Tracking issue:** `TBD` — "Reconciliation: skip and resume difficult review rows" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** Rejecting candidates does not approve creating a new record, and marking New is not a suitable way to set a difficult row aside. Reviewers need to continue through easy rows without recording a false decision.

**Change.** Add `Skip for now` as review-session navigation rather than a new catalog decision. Keep skipped rows in Needs review and provide a way to return to them; explain the difference between Reject and New next to those actions.

**Acceptance criteria.**

- Skipping advances the review without changing the catalog or sidecar; the row remains available in Needs review.

- Deferred rows can be resumed later in the session, and no skipped row is shown as accepted, rejected, or New.

- The UI explains that Reject does not approve new-record handling, while New does.

### R24. Open saved review independently of Find Candidates

**Tracking issue:** `TBD` — "Reconciliation: open saved review without starting matching" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** A navigation action labelled `Find Candidates` can be confused with actually running a search, and compatibility checks may disable it when the remote service is offline. Existing saved decisions should still be inspectable.

**Change.** Provide `Open review` or `Resume review` separately from `Find Candidates`. Only disable the remote search when matching is unavailable; load saved catalog and preview for review independently and show any preview-load error explicitly.

**Acceptance criteria.**

- Saved review opens without issuing a candidate-search request, including when the Authority Service is unavailable.

- A disabled Find Candidates action does not block access to saved decisions.

- Opening review and starting a search have distinct labels and outcomes.

### R25. Keep export results available with repair actions

**Tracking issue:** `TBD` — "Reconciliation: retained export results and repair links" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** A short-lived snackbar is not enough to find skipped links, failed verification, or a specific key after exporting.

**Change.** Show the most recent export result in a compact panel with counts and affected keys for changed links, removals, New approvals, protected links skipped, and verification outcomes. Offer actions to filter or jump to affected rows (R5/R9). Keep the panel available after the snackbar disappears, until dismissed or replaced by a later result; it need not survive a page reload.

**Acceptance criteria.**

- After a mixed-result export, an operator can reopen the result and navigate to a skipped or failed key after the snackbar disappears.

- Unverified links are identified separately from verified links and from links that were not exported.

- A later export replaces the result deliberately; the panel does not claim that an unapplied change was resolved without checking current state.

**Depends on:** R5 and R9.

---

## Group F — Fast manual free-text search

For many entities, most source rows describe new records, so reviewing precomputed candidates is not the main task. Other rows use abbreviations or labels in another language, and the reviewer must search using an expanded or translated term. Free-text search is therefore a primary reconciliation workflow, alongside reviewing suggested candidates.

The intended loop is: select a source row → type or revise a search term → inspect results → explicitly accept an existing record, mark New, or skip → continue to the next row. Batch Find Candidates is optional. Source labels and business keys remain unchanged when the reviewer edits the search query. “Manual search” means operator-entered search text; accepting its result remains a catalog decision for export, not a trusted manual sidecar link.

R21 provides the persistent pane; R26–R31 add search-specific behaviour. R6 reuses the picker for trusted manual links but retains its separate save action. R19 and R20 may improve retrieval later; expanding abbreviations and typing translated terms must work without waiting for them.

### R26. Add a search-first workspace for rows needing review

**Tracking issue:** `TBD` — "Reconciliation: search-first workspace for manual free-text review" (labels: `reconciliation`, `frontend`, `ux`)

**Area:** frontend. **Effort:** M. **Priority:** Early.

**Problem.** Opening an alternative-search dialog separately for each row treats manual search as an exception. This is slow when most rows are new or their source labels are unsuitable search terms.

**Change.**

- Offer a Search-first review mode in the persistent pane, available for rows with valid business keys even when no batch candidate search has run. Keep source context visible beside the search field and results.
- Focus the editable search field when entering a row. Offer Use source label as a convenience; allow replacement by an expanded abbreviation, translation, identifier, or arbitrary text without editing project data.
- Keep results and decision controls in the same pane. Offer Accept selected record, Mark New, and Skip for now, with Previous/Next navigation and remaining-row counts. An ordinary review session must not require repeated dialog opening.
- In this mode, show the text search prominently and keep batch candidate matching optional. Do not require R1's top-candidate display or score sorting to navigate the queue.

**Acceptance criteria.**

- Ten consecutive rows can be searched and reviewed in one pane without opening individual search dialogs or running Find Candidates.
- Typing an English expansion for a non-English abbreviation leaves the source label and encoded business key unchanged.
- Entering another row updates the visible context, clears obsolete results and selection, and places focus in its search field.

**Depends on:** R21 for the persistent pane. R30 enables saving decisions before batch matching; R28 provides the complete keyboard loop.

### R27. Make typed search responsive and reliable

**Tracking issue:** `TBD` — "Reconciliation: responsive text search with stale-result protection" (labels: `reconciliation`, `frontend`, `performance`, `ux`)

**Area:** frontend. **Effort:** M. **Priority:** Early.

**Problem.** Reviewers try several terms for the same row. Waiting for obsolete requests, selecting an old result, or mistaking a failed request for no matches adds time and can produce an incorrect decision.

**Change.**

- Debounce typing with an initial target of 250–400 ms; Enter submits immediately without a second duplicate request. Support composition input so unfinished IME text is not submitted.
- Cancel superseded requests when possible and always discard responses for an older query, row, specification, or project. Clear candidate selection immediately when text or search context changes.
- Show distinct states for not searched, searching, results, no results, and search failed. A failed request offers Retry and never appears as an empty successful search.
- Keep the pane usable while searching. Acceptance is available only for a selected result belonging to the current completed search. Prevent duplicate decision submissions.

**Acceptance criteria.**

- If responses arrive in reverse order, only the current row's latest search can be displayed or accepted.
- Enter submits immediately, pending debounce does not duplicate it, and changing a query invalidates its former selection before the next response arrives.
- A failed search preserves the query, reports the error, and supports Retry; it does not claim that no existing record was found.

**Depends on:** R26. Consolidate R21's search request handling here rather than implementing a second mechanism.

### R28. Search, decide, and advance without leaving the keyboard

**Tracking issue:** `TBD` — "Reconciliation: keyboard search, accept or New, and advance" (labels: `reconciliation`, `frontend`, `ux`, `accessibility`)

**Area:** frontend. **Effort:** M. **Priority:** Early.

**Problem.** In datasets dominated by new records, repeatedly searching, closing a dialog, opening New, and finding the next row costs more than candidate selection itself.

**Change.**

- Define a focus-scoped loop: type a query; Enter searches; navigate results with the keyboard; explicitly Accept selected record and next, Mark New and next, or Skip for now. Show the shortcuts beside their controls and coordinate them with R3.
- Plain typing in the search field must never invoke bare-letter grid actions, and Enter in that field must never accept or mark New. Offer explicit modified shortcuts for decisions and equivalent labelled buttons.
- Make Mark New a deliberate action that explains new-record approval and possible later ID allocation. Permit optional notes inline; do not require an empty search or mandatory repeated confirmation for every row. An empty result never marks New automatically.
- Advance after a confirmed save only. On failure, retain the active row, query, selected result, and notes for retry. Skip changes neither catalog nor sidecar. Undo uses R4 when available.

**Acceptance criteria.**

- A keyboard-only fixture with 20 rows, including 18 known-new rows and two existing records, can be completed with explicit decisions and no repeated dialog opening.
- A no-results response alone makes no decision; Mark New remains an operator choice even when candidates exist or no search was run.
- A failed acceptance or New save does not advance or discard the work; successful saves update the queue without entity-wide preview reloads.

**Depends on:** R26, R27, R30, and R2. Share navigation with R3 and skip semantics with R23 without requiring batch-candidate shortcuts first.

### R29. Search using independent text and optional row context

**Tracking issue:** `TBD` — "Reconciliation: free-text record search with optional source context" (labels: `reconciliation`, `backend`, `matching`, `ux`)

**Area:** frontend, backend; authority service only where retrieval capability needs extending. **Effort:** L. **Priority:** Early.

**Problem.** A reviewer may know an expanded name or translated term that differs completely from the source label. Useful interactive search must accept that text and, when helpful, use context to distinguish similarly named records. Prefix suggestions alone should not be assumed to meet this need.

**Change.**

- Define an interactive search request with operator-entered text, the specification's target service type, optional supported row properties, and a bounded result limit. Keep query text separate from source label and business key.
- Allow reviewers to inspect and remove context restrictions for a broader retry. Preserve the target type, and distinguish true filters from properties used only to rank matches.
- First assess the existing suggestion/search route against abbreviated-label and translated-query fixtures. Reuse it where sufficient; extend backend or Authority Service retrieval only for demonstrated gaps. Return the actual query, context used, and whether more results are available when the service can report that.
- Show names, IDs, and available distinguishing details. Full abbreviation expansion or automatic translation is not required: the operator supplies the alternative text. Explicit wildcard syntax and automatic multilingual matching remain R19/R20 work.

**Acceptance criteria.**

- A source label such as `Sthlm` can be searched as `Stockholm`, and a Swedish source label can be searched using the target's English label, without changing project data.
- A same-name fixture demonstrates the effect of supported context and allows an explicit broader retry; context not supported by the service is not silently presented as applied.
- Search results retain exact candidate URIs for normal acceptance and export; truncation or unavailable pagination is described honestly rather than implying an exhaustive search.

**Depends on:** No dependency on R19 or R20. Add an Authority Service issue only if the fixture identifies a required service change.

### R30. Save a searched match or New decision before batch matching

**Tracking issue:** `TBD` — "Reconciliation: save row decisions without prior batch matching" (labels: `reconciliation`, `backend`, `api`)

**Area:** backend. **Effort:** M. **Priority:** Early.

**Problem.** The current decision service rejects keys absent from the reconciliation catalog with “run matching first”. This prevents a complete search-first workflow even when the source row is already visible and the operator has found an existing record or knows it is new.

**Change.**

- Allow an authorized decision for an actual source row with a valid unique business key to create its catalog entry directly. Validate the project, specification, current row, and key on the server; do not trust arbitrary keys or client-supplied source context.
- Preserve accepted-candidate URI/ID rules, notes, operator provenance, and available selected-result metadata. A manually searched match uses the same accepted-decision/export path as a batch-suggested match; it does not write a trusted manual link.
- Permit explicit New without a prior candidate search. Keep service reachability requirements specific to actions that need remote search: choosing New does not require the Authority Service to be online.
- Return enough saved state for R2 to patch the row and R9 to report unapplied changes. Avoid forcing a whole-entity normalization on every save; define reuse and invalidation of validated review-row data, and reject stale or no-longer-valid keys explicitly.

**Acceptance criteria.**

- On a specification with no prior matching entries, an existing searched record can be accepted and another row marked New without running batch matching.
- Unknown, missing, duplicate, stale, or unauthorized keys do not create decisions; concurrent edits return an actionable conflict.
- Decisions survive reload and batch reruns, appear as unapplied until export, and affect normalized output or new-record approval only through the existing export rules. Saving New still works while the remote search service is offline.

**Depends on:** None. R26/R28 consume this support; R2/R9 provide the UI update and unapplied-state presentation.

### R31. Remember and reuse operator-entered search terms

**Tracking issue:** `TBD` — "Reconciliation: retain row search terms and reuse recent queries" (labels: `reconciliation`, `frontend`, `ux`)

**Area:** frontend. **Effort:** M. **Priority:** Next.

**Problem.** Reviewers repeatedly expand the same abbreviation, translate a term, or revisit a row after interruption. Reconstructing the useful query each time wastes work.

**Change.**

- Retain the latest query and context settings per project, specification, and business key. Restore the query on return and focus it for editing; never restore an old result as a newly verified match.
- Offer bounded recent-query history scoped to the specification, with explicit reuse and Clear history. Reusing a term triggers or prepares a new search and never copies a decision across keys.
- Coordinate persistence with R8. If current source inputs differ, indicate that a restored term came from earlier inputs and offer Reset to source label; use R22's richer comparison when available.
- Keep drafts and history separate from catalog decisions, source labels, matching fingerprints, and curated aliases. Promoting repeated terms into R20 aliases is separate work.

**Acceptance criteria.**

- Leaving and returning to a row restores its typed expansion or translation without changing source data or submitting a decision.
- A recent query can be reused for another row, but results and acceptance are scoped to that row and its current context.
- History is bounded, can be cleared, and does not leak across projects or specifications; a changed source row does not present an old query as newly reviewed input.

**Depends on:** R26. Share state persistence with R8; R22 is an optional enhancement, not a prerequisite for retaining queries.

---

## Group G — Targeted removal

### R32. Clear a review decision, a sidecar mapping, or both

**Tracking issue:** [#759](https://github.com/humlab-sead/sead_shape_shifter/issues/759) — "Reconciliation: clear a decision or delete its sidecar mapping by key" (labels: `reconciliation`, `frontend`, `backend`, `ux`)

**Problem.** Removing an incorrect decision from the reconciliation catalog and removing a link or New approval from the mapping sidecar are different operations. Undo (R4) only restores a recent decision in the current session; it does not remove a sidecar entry. Reviewers need a deliberate way to remove either saved record, or both, for one row without deleting other mappings.

**Change.**

- Offer separately labelled `Clear decision`, `Delete sidecar mapping`, and `Clear both` actions for the selected project, entity, target field, and encoded business key. Show the matching catalog decision and sidecar link or local-only approval before confirmation; disable actions whose target does not exist.

- Use the existing per-key decision and link deletion operations where applicable. Add per-key removal for sidecar local-only approvals and any coordination needed for `Clear both`. Never use the specification-wide delete or remove unrelated keys.

- State which file each action changes. Clearing only the decision leaves an exported sidecar entry in place; deleting only the sidecar entry leaves the decision in place, so a later export may recreate it. Do not silently delete a trusted manual or other protected link as part of clearing a decision; require an explicit sidecar-delete choice and confirmation for such links.

- Report partial failures without claiming both records were cleared. Refresh the row and outstanding-change state (R9 when available) after a successful operation.

**Acceptance criteria.**

- For a key with both a saved decision and an exported link or New approval, each single-target action removes only its selected record; `Clear both` removes both after confirmation.

- A manual or protected link is never removed by `Clear decision` alone, and any direct deletion of it requires explicit confirmation.

- A missing target disables its action; a failed or partial deletion shows which record remains, and other keys and specifications are unchanged.

---

## Group H — Decision write conflicts

### R33. Require per-row expected decision state on every decision write

**Tracking issue:** [#766](https://github.com/humlab-sead/sead_shape_shifter/issues/766) — "Reconciliation: per-row expected decision state on decision writes" (labels: `reconciliation`, `backend`, `api`)

**Area:** backend. **Effort:** L. **Priority:** Later.

**Problem.** Every decision write loads the catalog under the project lock, changes one business key, and saves, but none of them compares the decision it replaces. Two reviewers working the same project and specification therefore overwrite each other's decisions for the same key on a last-writer-wins basis. This applies to the batch route, the single decision route, the delete route, and mark-unmatched. The Phase 3 workspace warns before a draft replaces a decision that changed since it loaded, but that comparison is client-side and advisory: a decision changed between the comparison and the write is still replaced silently.

**Change.**

- Add an optional expected current state per business key to each decision write: absent, or the decision's status with its target ID, candidate URI, and last-modified marker.
- Under the project lock, reject a write whose expected state differs from the stored decision, and name the affected keys with their current state so the reviewer can reload and reapply.
- Keep the batch all-or-nothing: one conflicting key rejects the whole batch without writing.
- Leave the whole-catalog replacement route on its own rule. Do not give per-key routes a whole-catalog precondition, and do not add server-side review sessions or per-row version storage.
- Treat a missing expected state as today's last-writer-wins behavior, so legacy routes, clients, and the frozen Phase 2 payload keep working.

**Acceptance criteria.**

- Two writes for the same key, where the first changes the decision, make the second fail with a conflict naming that key; a conflicting batch writes nothing.
- A write whose expected state matches the stored decision succeeds, and a key with no decision is distinguishable from a key whose decision was deleted.
- A conflict on one key leaves writes to other keys and other specifications unaffected.
- A caller that sends no expected state keeps the current behavior.

**Depends on:** Nothing blocks it. It replaces the advisory check `PH3-AC-6` adds and decides the conflict clause R16 states.

---

## Group I — Inspect saved workspace decisions

### R34. Inspect saved decisions in the Search/Browse workspace

**Tracking issue:** `TBD` — "Reconciliation: inspect saved decisions in the Search/Browse workspace" (labels: `reconciliation`, `frontend`, `ux`)

**Area:** frontend. **Effort:** M. **Priority:** Next.

**Problem.** The Search/Browse workspace replaces the legacy grid, and its Needs review queue removes rows with saved decisions. If Authority becomes unavailable after the workspace opens, reviewers cannot inspect saved decisions in the workspace and must switch to the legacy grid.

**Change.**

- Add a **Saved decisions** view to the workspace, separate from the Needs review queue.
- Populate it from saved decision states already loaded for the specification, and update it from each successful batch response.
- Show the saved status and available decision details, such as target ID or URI and notes. Do not call Authority to render the saved decision.
- Keep saved rows out of Needs review so its membership and count do not change.

**Acceptance criteria.**

- After opening the workspace while Authority is available, a reviewer can inspect previously saved decisions and decisions saved during the session after Authority becomes unavailable, without switching to the legacy grid.
- Inspection uses saved state already loaded or returned by the batch save; it makes no Authority request.
- The view shows the saved status and available decision details without changing the catalog or mapping sidecar.
- Saved rows do not appear in Needs review or change its count.

**Depends on:** R2 and R24 for saved-row updates and independent saved review.

**Scope note.** This follow-up is deferred from the [Search and Browse proposal](./RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) and is not a Phase 3 acceptance gate.

---

## Summary

| Item | Area | Effort | Priority | Depends on |
|---------------------------------------------------|----------------------------|--------|---------------|-----------------------|
| R1 Top candidate and explicit one-click accept | frontend | M | Early | — |
| R2 Patch saved decision without preview reload | frontend | M | Early | — |
| R3 Keyboard review loop | frontend | M | Early | R1, R5 |
| R4 Undo last decision | frontend, backend | M | Early | R2, R9 |
| R5 Needs review queue and candidate-score sorting | frontend | M | Early | R1 (score features only) |
| R6 Manual link target by search | frontend | M | Next | — |
| R7 Notes and preset reasons | frontend | S | Next | — |
| R8 Remember review context | frontend | M | Early | R5 |
| R9 Unapplied changes and verification status | frontend, backend | L | Early | — |
| R10 Pre-export check | frontend, backend | M | Next | — |
| R11 Two-line column headers | frontend | S | Cosmetic | — |
| R12 Deduplicate effective queries | backend | M | Early | — |
| R13 Reuse unchanged matching outcomes | backend | L | Next | — |
| R14 Async progress and cancel | frontend, backend | L | Early | — |
| R15 Effective configurable candidate limit | backend, authority service | L | Next | Service limit support |
| R16 Batch decision endpoint (conflict check owned by R33) | backend | L | Next | — |
| R17 Bulk actions in the grid | frontend | M | Next | R16 |
| R18 Review equivalent-query groups | frontend | M | Next | R16 |
| R19 Partial matching, wildcard follow-up | authority service, backend | L | Later | — |
| R20 Multilingual matching | authority service | L | Later | — |
| R21 Review pane stays open | frontend | L | Early | — |
| R22 Flag changed source inputs | frontend, backend | M | Next | R13 |
| R23 Defer and resume difficult rows | frontend | S | Next | — |
| R24 Open saved review independently | frontend | S | Early | — |
| R25 Retained export results and repair | frontend | M | Next | R5, R9 |
| R26 Search-first workspace | frontend | M | Early | R21 |
| R27 Responsive and reliable typed search | frontend | M | Early | R26 |
| R28 Keyboard search, decision, and advance | frontend | M | Early | R26, R27, R30, R2 |
| R29 Independent text search with optional context | frontend, backend; authority service if needed | L | Early | — |
| R30 Decisions without prior batch matching | backend | M | Early | — |
| R31 Remember and reuse search terms | frontend | M | Next | R26 |
| R32 Clear decision and/or sidecar entry by key | frontend, backend | M | Next | — |
| R33 Per-row expected decision state on decision writes | backend | L | Later | — |
| R34 Saved decisions in Search/Browse workspace | frontend | M | Next | R2, R24 |

## Suggested order

1. Deliver search-first review for mostly-new datasets and labels requiring alternative terms: R30 and R2, then R21, R26, R27, and R28. Assess R29's search fixtures early and extend retrieval only where required. This route does not wait for batch candidates, top-candidate display, R19, or R20. Add R31 next. Bring R9 and R24 alongside it so saved decisions and review access remain clear.

   Add R34 after R2/R24 and the initial Search/Browse workspace; it does not block this proposal's Phase 3 acceptance.

2. Make candidate review fast and recoverable: R1, R5, R8, R3, and R4, supported by R2/R9/R24 above. Implement R5 and R8 together so their shared persistence has one owner; coordinate R3's grid shortcuts with R28's search-field shortcuts.

3. Reduce batch matching waits: R14 and R12, followed by R13 and R15. Keep batch Find Candidates optional for search-first sessions.

4. Enable deliberate batch decisions: R16, R17, then R18. Add R22 after R13 and before encouraging reuse of old decisions.

5. Fit R6, R7, R10, R23, R25, and R32 around the workflow they support. Reuse the search picker and skip behaviour rather than building parallel implementations. Make R11 opportunistic.

6. Improve automatic matching through R19 and R20 after representative failed-search fixtures show what needs to change. Decide wildcard syntax separately from partial matching; manual expanded or translated query text is already supported by the earlier search-first work.

Add R33 once the workspace ships. It turns the advisory pre-save warning into a server-enforced check, and it is the only item here that removes the last-writer-wins window rather than warning about it.

Assess improvements by measuring time and interactions per saved decision, preview requests per decision, time to resume review, and time to locate and repair an export problem. For Group F, also measure time per explicit New decision, time from entering a query to a usable result (median and 95th percentile), and query attempts per completed decision. Record the fixture size and environment before setting latency targets.

Validate Group F with a dataset dominated by known-new records (for example, 90 of 100 rows), abbreviated and non-English source labels searched with manually supplied expansions/translations, and a session with no prior batch matching. Include ambiguous results, successful empty searches, unavailable service, out-of-order responses, changed source rows, and failed saves. Empty results must never mark New automatically; unavailable search must not prevent a deliberate New decision when local row validation succeeds.

## Open decisions

- R9: define whether "pending verification" includes already committed unverified links independently of unapplied decision changes.

- R13/R22: decide where matching-input fingerprints and the previous reviewed-input snapshot are stored and how existing catalog entries without them are shown.

- R15: confirm how the Authority Service honors the requested candidate limit before selecting the configuration contract.

- R19: agree on the option channel between services; handle wildcard syntax in separate follow-up work if partial matching proves useful.

- R29: establish which interactive-search behaviours the existing route already provides, whether optional context filters or only ranks results, and how result truncation can be reported. Automatic translation and wildcard syntax are separate decisions.
- R30: choose how validated source-row data is reused and invalidated so a first-time decision is checked against current data without normalizing the whole entity per save. Define an actionable stale-row conflict.
- R28: choose explicit modified decision shortcuts that coexist with text editing, composition input, and R3; plain Enter in the query field runs search only.
- R33: decide whether an expected state becomes required once Shape Shifter sends it, and how a rejected batch is recovered by reapplying the preserved drafts.
