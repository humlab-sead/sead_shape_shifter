# Reconciliation improvement backlog

**Status:** Active reconciliation backlog; completed items are indexed below

**Last updated:** 2026-11-22

**Scope:** The human review workflow in the Reconciliation view, and the matching options that workflow depends on.

## Completed items (reference only)

This compact index preserves the original R numbers used by dependencies. The closed tracking issue and merged pull request are the implementation record when assigned; the linked proposal identifies the Interactive Search/Browse scope. Keep completed requirements out of this backlog.

| ID | Completed item | Scope reference |
|---|---|---|
| R2 | Patch a saved decision without reloading the preview | [Interactive Search/Browse](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) |
| R16 | Atomic batch save for Interactive Search/Browse drafts | [Interactive Search/Browse](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) |
| R21 | Keep the review pane open between rows | [Interactive Search/Browse](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) |
| R24 | Open Interactive Search/Browse independently of Find Candidates | [Interactive Search/Browse](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) |
| R26 | Interactive Search/Browse workspace | [Interactive Search/Browse](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) |
| R27 | Responsive, reliable typed search | [Interactive Search/Browse](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) |
| R28 | Keyboard search, decision, and advance | [Interactive Search/Browse](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) |
| R29 | Independent text search with optional context | [Interactive Search/Browse](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) |
| R30 | Save a searched match or New before batch matching | [Interactive Search/Browse](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md) |

## Reconciliation ID flow

See [RECONCILIATION_DIAGRAMS.md](./RECONCILIATION_DIAGRAMS.md) for separate sequence diagrams of candidate search, review decisions, export, manual links, targeted removal (R32), and normalization.

Each active item below is intended for its own GitHub issue. The `Tracking issue` line gives a suggested title; replace `TBD` with the number when the issue is created. Where one item unblocks another, the dependency is listed and the issue should reference it. R19 and R20 also need issues in the Authority Service repository for their service changes. When an item is complete, close its tracking issue with links to the merged pull request and validation, remove its detailed entry from this backlog, and retain its R number in the completed-items index. Rewrite partially delivered items to describe only the remaining work.

The entries below describe open, partial, or deferred work. This is a working backlog under `docs/proposals/`, not an approved phase plan.

## How to read an item

- **Area**: `frontend`, `backend`, or `authority service` (the reconciliation service behind `RECONCILIATION_SERVICE_URL`).

- **Effort**, recorded in the summary table: S is a small local change, M is a few days, L is a larger feature or crosses two services. These are estimates, not commitments.

- **Status**, recorded in the summary table: Open means no part of the item is complete; Partial means the remaining scope is described in the item; Deferred means the work is intentionally postponed.

- **Priority**: Early is in the first recommended improvement set; Next follows that foundation or its listed dependencies; Later is deferred until evidence supports the change; Opportunistic is small work that can fit alongside related changes.

- **Depends on**: an item that must ship first.

- The acceptance criteria are observable checks for the remaining work. Validate them with straightforward, ambiguous, empty-result, and failed-save cases where relevant.

## Workflow foundations

1. Reviewer decisions live in the reconciliation catalog (`shapeshifter.reconciliation.yml`). Normalized output does not change until accepted decisions are exported to the mapping sidecar (`shapeshifter.mapping.yml`). The preview endpoint returns decisions together with their candidates; the mapping endpoint returns the sidecar links. Most "the IDs did not change" confusion comes from this split, so several items below make it visible rather than removing it.

2. **Ranked candidate matching** (short: candidate matching) uses source-row labels and supported properties with the OpenRefine-compatible service at `RECONCILIATION_SERVICE_URL`, normally `sead_authority_service`. It returns scored candidates for review in the candidate grid. A type's matching strategy may use specialized logic, including LLM-based matching where configured. SIMS allocates identities and tracks bindings; it does not take part in candidate matching.

3. **Interactive Search/Browse** is reviewer-directed: Search uses text and supported context entered by the reviewer, while Browse loads a complete list within advertised limits. Search may also return ranked candidates; the distinction is how the query is started, not the result-ranking algorithm or protocol. Interactive Search/Browse complements ranked candidate matching and does not replace the candidate grid.

4. For many entities, most rows describe new records. Other rows have abbreviated or non-English labels that require an operator-entered expansion or translation. Interactive Search/Browse does not require ranked candidate matching. Search text is separate from source data and row identity: accepting a manually searched result saves a review decision for export. This differs from R6's trusted manual link, which writes directly to the mapping sidecar.

## Non-goals

- Automatic acceptance of candidates. `auto_accept_threshold` is displayed and never accepts a candidate, and `docs/other/RECONCILIATION_GUIDE.md` states that matching never accepts a candidate. Every item below keeps the operator as the decision maker. A bulk action the operator starts is acceptable; silent acceptance is not.
- Automatic New decisions from empty results, failed searches, or a dataset's expected proportion of new records. New always requires an explicit operator action; a search miss is not proof that the record is absent.

---

## Group A — Faster review workflow

R4 needs API support to restore an undecided proposal. R9 and R10 need backend export rules, not browser-only estimates.

### R1. Show the top ranked candidate in the candidate grid and accept it explicitly

**Tracking issue:** `TBD` — "Reconciliation: show top ranked candidate in the candidate grid" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** To accept a candidate from the grid, a reviewer must open the `Review (n)` dialog and choose a candidate. The grid renders `Selected target ID` (`target_id`), which stays empty until acceptance, even though the preview payload already includes each row's `candidates`.

**Change.**

- Add a `Top candidate` column showing name, numeric ID, and score (or "no score"). Define the ordering for ties and missing scores; mark alternatives as ambiguous when they are close enough to make a one-click choice unclear.

- Add an explicit one-click accept using the existing decision action and candidate URI ID extraction. Never accept automatically.

- Disable acceptance when the URI cannot yield a valid target ID; keep comparison of alternatives available.

**Acceptance criteria.**

- A proposed row with candidates can be accepted without opening a dialog.

- The displayed candidate follows the defined ordering, ties and missing scores are handled consistently, and close alternatives are identified as ambiguous.

- A candidate with a non-numeric URI cannot be accepted from the grid; a save failure remains visible.

### R3. Add keyboard shortcuts to the candidate grid

**Tracking issue:** `TBD` — "Reconciliation: keyboard shortcuts for the candidate grid" (labels: `reconciliation`, `frontend`, `ux`, `accessibility`)

**Remaining scope.** Interactive Search/Browse's keyboard search-and-decision loop is complete under R28. Add focus-scoped shortcuts to the candidate grid for opening a row, explicit decisions, search, and moving through visible rows. Do not trigger grid actions while the reviewer types in a field or dialog.

**Acceptance criteria.**

- A reviewer can complete a grid decision-and-advance cycle without the mouse; a failed save does not advance.
- Typing in search or a dialog does not trigger grid actions, and the help dialog lists the shortcuts.

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

### R5. Add advanced Needs review filters and sorting

**Tracking issue:** `TBD` — "Reconciliation: add advanced Needs review filters and sorting" (labels: `reconciliation`, `frontend`, `ux`)

**Remaining scope.** Interactive Search/Browse provides the basic Needs review queue, navigation, and counts. Add candidate-score sorting, category views, threshold filtering, and persistent filter/sort state for the broader review workflow.

**Acceptance criteria.**

- Candidate sorting uses candidate scores, handles missing scores and ties consistently, and does not use saved decision confidence.
- Category and threshold filters show counts that match their rows, including rows without candidate scores where required.
- Filter and sort choices persist across the relevant review navigation.

**Depends on:** R1 for candidate-score display and R8 for broader context persistence.

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

The completed Interactive Search/Browse workspace provides a picker that R6 can reuse, while R6 keeps the trusted manual-link save action separate.

### R7. Add preset reasons and broader note editing

**Tracking issue:** `TBD` — "Reconciliation: add preset reasons and edit notes across review surfaces" (labels: `reconciliation`, `frontend`, `audit`)

**Remaining scope.** Interactive Search/Browse supports optional inline notes. Add action-appropriate preset reasons and allow reviewers to view and edit saved notes across the other decision surfaces.

**Acceptance criteria.**

- Preset reasons are stored as readable notes and match the decision action.
- Notes can be edited without losing existing text unless the reviewer deliberately clears it.
- The candidate grid identifies rows with notes and makes their text available without opening a decision dialog.

### R8. Restore broader review context between visits

**Tracking issue:** `TBD` — "Reconciliation: restore candidate-grid review context between visits" (labels: `reconciliation`, `frontend`, `ux`)

**Remaining scope.** Interactive Search/Browse restores its own mode, row, queries, filters, and sort. Extend context restoration to the broader project and candidate-grid workflow, including the selected specification, target, filter, search, focused row, and scroll position.

**Acceptance criteria.**

- Returning to a project and specification restores valid candidate-grid selections and navigation state.
- Removed specifications or invalid filters fall back safely, and state from one project is not shown in another.

**Depends on:** R5 for shared filter and sort behavior.

### R9. Show unapplied changes and verification status

**Tracking issue:** `TBD` — "Reconciliation: show unapplied changes per specification" (labels: `reconciliation`, `frontend`, `backend`, `ux`)

**Remaining scope.** Interactive Search/Browse distinguishes Save decision from Export. Show whether saved decisions are applied to the mapping sidecar and report outstanding changes, verification state, and affected rows.

**Acceptance criteria.**

- New, changed, removed, and New-approval decisions produce accurate outstanding-change counts.
- Exported, skipped, blocked, failed, and unverified rows show their correct state and reason.
- Manual or protected links are not mistaken for exported reconciliation decisions.

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

**Remaining scope.** Interactive Search/Browse caps and Authority Service per-query limit forwarding are implemented. Add an optional candidate count for batch matching, defaulting to 3 and limited to 1–10, and pass it through both matching routes.

**Acceptance criteria.**

- A specification requesting six candidates can display six when they are available; specifications without the field retain the default.
- Values outside the allowed range are rejected with a clear validation message.

**Depends on:** Implemented Authority Service per-query limit support.

---

## Group C — Batch decisions

### R17. Add bulk actions to the candidate grid

**Tracking issue:** `TBD` — "Reconciliation: bulk accept, reject, and mark New" (labels: `reconciliation`, `frontend`, `ux`)

**Problem.** The candidate grid has no row selection. Reviewing many rows with the same clear outcome therefore requires one decision and one request per row.

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

### R19. Add partial matching to ranked candidate matching

**Tracking issue:** `TBD` — "Candidate matching: evaluate token and substring matches" (labels: `reconciliation`, `matching`, `configuration`)

**Remaining scope.** Interactive Search/Browse supports literal substring filtering of complete Browse lists. Reproduce remaining failed-search cases and add opt-in token or substring matching to ranked candidate matching only where fixtures show it is needed. Keep wildcard syntax as a separate decision.

**Acceptance criteria.**

- Partial matches include a score and explanation that identifies the matched text and match kind.
- The option is rejected when the service manifest does not declare support.
- Wildcard characters remain literal unless a separate wildcard contract is approved.

### R20. Add curated and automatic multilingual matching

**Tracking issue:** `TBD` — "Candidate matching: multilingual label matching" (labels: `reconciliation`, `matching`, `configuration`)

**Remaining scope.** Reviewers can enter translated terms in Interactive Search/Browse. This item covers service-side matching through curated, type-specific aliases and, only if needed, runtime translation or language detection. Keep language exceptions explicit for terms without a translation.

**Acceptance criteria.**

- A cross-language match identifies the alias and language used.
- Ranking fixtures distinguish an approved equivalent term with matching context from a misleading same-language label.
- Disabling multilingual matching restores current results.

---

## Group E — Review continuity and repair

### R22. Flag changed source inputs on previously reviewed rows

**Tracking issue:** `TBD` — "Reconciliation: flag reviewed decisions after source inputs change" (labels: `reconciliation`, `frontend`, `backend`, `audit`)

**Problem.** A prior accepted, rejected, or New decision can remain visible after the source label or mapped context changes. It may then look freshly reviewed even though its basis changed.

**Change.** After R13 establishes how input fingerprints are stored, compare each reviewed row's current matching inputs with the inputs used for its decision. Keep operator decisions unchanged, but flag affected keys and changed inputs for reassessment; clearing the flag requires an explicit review action.

**Acceptance criteria.**

- Changing a reviewed row's mapped country, coordinate, or label flags the row without silently removing its decision.

- Unchanged inputs do not flag the row; reopening the review makes the change visible.

- The operator can re-review and clear the flag after comparing the saved and current matching inputs.

**Depends on:** R13.

### R23. Reuse skip and resume in candidate-grid review

**Tracking issue:** `TBD` — "Reconciliation: reuse skip and resume in candidate-grid review" (labels: `reconciliation`, `frontend`, `ux`)

**Remaining scope.** Interactive Search/Browse already lets reviewers skip a row without saving a decision and return to it later. Reuse that navigation in candidate-grid review without adding a catalog status.

**Acceptance criteria.**

- Skipping a row leaves its catalog decision and mapping sidecar unchanged and keeps it available in Needs review.
- Deferred rows can be revisited, and the UI distinguishes Skip from Reject and New.

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

## Group F — Interactive Search/Browse history

The Interactive Search/Browse workspace and per-row query drafts are complete; see the completed-items index. This group tracks only bounded recent-query history. Reviewers can already enter expanded or translated search terms without automatic multilingual matching.

### R31. Remember and reuse recent search terms

**Tracking issue:** `TBD` — "Reconciliation: remember and reuse recent search terms" (labels: `reconciliation`, `frontend`, `ux`)

**Remaining scope.** Offer bounded recent-query history scoped to a project and specification, with explicit reuse and Clear history. Reusing a term triggers a new search for the current row and never copies a decision. Keep query history separate from per-row drafts, catalog decisions, source labels, and curated aliases.

**Acceptance criteria.**

- A recent query can be reused for another row, but results and decisions remain scoped to that row and its current context.
- History is bounded, can be cleared, and does not leak across projects or specifications.

**Depends on:** R26 (complete; see the completed-items index). Share storage conventions with R8 where practical; R22 is not a prerequisite.

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

### R34. Inspect saved decisions in the Interactive Search/Browse workspace

**Tracking issue:** `TBD` — "Reconciliation: inspect saved decisions in the Interactive Search/Browse workspace" (labels: `reconciliation`, `frontend`, `ux`)

**Area:** frontend. **Effort:** M. **Priority:** Next.

**Problem.** The Interactive Search/Browse workspace's Needs review queue excludes rows with saved decisions. Reviewers can inspect those decisions in the candidate grid, but must switch workflows to do so.

**Change.**

- Add a **Saved decisions** view to the workspace, separate from the Needs review queue.
- Populate it from saved decision states already loaded for the specification, and update it from each successful batch response.
- Show the saved status and available decision details, such as target ID or URI and notes. Do not call Authority to render the saved decision.
- Keep saved rows out of Needs review so its membership and count do not change.

**Acceptance criteria.**

- After opening the workspace while Authority is available, a reviewer can inspect previously saved decisions and decisions saved during the session after Authority becomes unavailable, without switching to the candidate grid.
- Inspection uses saved state already loaded or returned by the batch save; it makes no Authority request.
- The view shows the saved status and available decision details without changing the catalog or mapping sidecar.
- Saved rows do not appear in Needs review or change its count.

**Depends on:** R2 and R24, both completed by the Interactive Search/Browse implementation.

**Scope note.** This remains deferred from the shipped [Interactive Search/Browse proposal](./done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md); saved-decision inspection was not part of its completed scope.

---

## Summary

| Item | Area | Effort | Status | Priority | Depends on |
|---------------------------------------------------|----------------------------|--------|----------|---------------|-----------------------|
| R1 Ranked candidate matching: top candidate and explicit accept | frontend | M | Open | Early | — |
| R3 Keyboard shortcuts for the candidate grid | frontend | M | Partial | Early | R1, R5 |
| R4 Undo last decision | frontend, backend | M | Open | Early | R2, R9 |
| R5 Advanced Needs review filters and sorting | frontend | M | Partial | Early | R1 (score features only), R8 |
| R6 Manual link target by search | frontend | M | Open | Next | — |
| R7 Preset reasons and broader note editing | frontend | S | Partial | Next | — |
| R8 Restore broader review context | frontend | M | Partial | Early | R5 |
| R9 Unapplied changes and verification status | frontend, backend | L | Partial | Early | — |
| R10 Pre-export check | frontend, backend | M | Open | Next | — |
| R11 Two-line column headers | frontend | S | Open | Opportunistic | — |
| R12 Deduplicate effective queries | backend | M | Open | Early | — |
| R13 Reuse unchanged matching outcomes | backend | L | Open | Next | — |
| R14 Async progress and cancel | frontend, backend | L | Open | Early | — |
| R15 Per-specification candidate limit | backend, authority service | L | Partial | Next | Authority Service per-query limit support |
| R17 Bulk actions in the candidate grid | frontend | M | Open | Next | R16 |
| R18 Review equivalent-query groups | frontend | M | Open | Next | R16 |
| R19 Partial matching in ranked candidate matching | authority service, backend | L | Partial | Later | — |
| R20 Curated and automatic multilingual matching | authority service | L | Open | Later | — |
| R22 Flag changed source inputs | frontend, backend | M | Open | Next | R13 |
| R23 Reuse skip and resume in candidate-grid review | frontend | S | Partial | Next | — |
| R25 Retained export results and repair | frontend | M | Open | Next | R5, R9 |
| R31 Recent search history | frontend | M | Partial | Next | R26 |
| R32 Clear decision and/or sidecar entry by key | frontend, backend | M | Open | Next | — |
| R33 Per-row expected decision state on decision writes | backend | L | Open | Later | — |
| R34 Saved decisions in Interactive Search/Browse workspace | frontend | M | Deferred | Next | R2, R24 |

## Suggested order

1. Make candidate review fast and recoverable: R1, R5, R8, R3, and R4. R2 is complete and R9 remains partial; implement R5 and R8 together so their shared persistence has one owner.

2. Reduce batch matching waits: R14 and R12, followed by R13 and R15. Keep ranked candidate matching optional for Interactive Search/Browse sessions.

3. Enable deliberate batch decisions: build R17 and R18 on the completed R16 atomic save endpoint where its contract fits. Add R22 after R13 and before encouraging reuse of old decisions.

4. Fit R6, the remaining R7 work, R10, R23, R25, and R32 around the workflow they support. Reuse the Interactive Search/Browse picker and skip behavior rather than building parallel implementations. Make R11 opportunistic.

5. Improve automatic matching through R19 and R20 after representative failed-search fixtures show what needs to change. Decide wildcard syntax separately from partial matching. R31's recent-query history is a separate frontend follow-up.

R34 remains deferred. R33 can proceed now that the workspace is shipped; it replaces the advisory pre-save warning with a server-enforced check and removes the last-writer-wins window.

The Interactive Search/Browse workspace is shipped. R33 remains a follow-up that replaces its advisory pre-save warning with a server-enforced check and removes the last-writer-wins window.

Assess the shipped Interactive Search/Browse workflow by measuring time and interactions per saved decision, preview requests per decision, time to resume review, and time to locate and repair an export problem. Also measure time per explicit New decision, time from entering a query to a usable result (median and 95th percentile), and query attempts per completed decision. Record the fixture size and environment before setting latency targets.

Keep regression coverage for Interactive Search/Browse with a dataset dominated by known-new records (for example, 90 of 100 rows), abbreviated and non-English source labels searched with manually supplied expansions/translations, and a session with no prior ranked candidate matching. Include ambiguous results, successful empty searches, unavailable service, out-of-order responses, changed source rows, and failed saves. Empty results must never mark New automatically; unavailable search must not prevent a deliberate New decision when local row validation succeeds.

## Open decisions

- R9: define whether "pending verification" includes already committed unverified links independently of unapplied decision changes.

- R13/R22: decide where matching-input fingerprints and the previous reviewed-input snapshot are stored and how existing catalog entries without them are shown.

- R15: decide whether to add per-specification batch candidate-count configuration and select its allowed range; Authority Service per-query limit forwarding is implemented.

- R19: agree on the option channel between services; handle wildcard syntax in separate follow-up work if partial matching proves useful.

- R33: decide whether an expected state becomes required once Shape Shifter sends it, and how a rejected batch is recovered by reapplying the preserved drafts.
