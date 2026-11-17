The backlog is strong, but I would revise several candidates and change their priority. The biggest gains should come from **keeping users in a continuous review loop, removing unnecessary waits, and making unapplied decisions visible**.

I reviewed the attachment against `main` at [4c55aa8](https://github.com/humlab-sead/sead_shape_shifter/commit/4c55aa8b1e9812bdf767bd9bab12314cf7b6f7b1), including the MVP review, revised MVP, components, store, and backend. This is a code-based review; I have not measured the running interface.

**Three changes matter most before implementing the backlog.**

1. **Replace “pending exports” with “unapplied changes.”** R9 currently misses important cases: an accepted target changes, an exported decision becomes rejected, or a row is marked New. All can require sidecar updates. A successful export must also leave unverified or unsuccessful rows visible.
2. **Replace shared-label propagation with explicit grouping by matching inputs.** R18 assumes identical labels usually identify the same target. That is unsafe for sites, locations, and other contextual entities. The existing query builder deliberately includes mapped properties alongside the label.
3. **Create one “Needs review” queue.** The current `Unresolved` filter excludes proposed rows with candidates. Defaulting to it would hide the rows where one-click acceptance helps most.

These follow directly from the current [export logic](https://github.com/humlab-sead/sead_shape_shifter/blob/4c55aa8b1e9812bdf767bd9bab12314cf7b6f7b1/backend/app/services/reconciliation/service.py#L434), [query construction](https://github.com/humlab-sead/sead_shape_shifter/blob/4c55aa8b1e9812bdf767bd9bab12314cf7b6f7b1/backend/app/services/reconciliation/service.py#L137), and [grid filtering](https://github.com/humlab-sead/sead_shape_shifter/blob/4c55aa8b1e9812bdf767bd9bab12314cf7b6f7b1/frontend/src/components/reconciliation/ReconciliationGrid.vue#L546). Confidence: **high**.

**I would amend the existing candidates as follows.** “Early” means part of the first useful improvement set; “Next” means valuable once that foundation works.

| Item | Recommendation | Priority |
|---|---|---|
| **R1 — Top candidate and one-click accept** | Keep. Show candidate **name, ID, and score**, with an ambiguity indicator when alternatives have similar scores. Define how “top” is ordered, including ties and missing scores. Acceptance must remain an explicit user action. | Early |
| **R2 — Optimistic decisions** | Prioritize removing the preview reload. The proposed implementation patches **after saving**, which is an acknowledged update rather than an optimistic one; that is a good first step. Use the returned catalog to update the row, keep other rows usable, and preserve focus and scroll. Add true optimism only if save latency still warrants it. | Early |
| **R3 — Keyboard loop** | Keep, alongside R1 and R4. Prefer **Enter to open review; an explicit shortcut to accept the displayed candidate**. Bare Enter accepting a match can conflict with grid navigation. Advance only after a successful save, following the visible sort and filter. | Early |
| **R4 — Undo** | Keep, but reclassify as frontend **and backend**. The decision API cannot restore `proposed`. Define restoration of status, target, URI, notes, and proposal data. Undo after export creates an unapplied change; it must not imply the sidecar was restored. | Early |
| **R5 — Work queue** | Replace the default with **Needs review**, covering undecided rows and proposals with or without candidates. Separate **Ready to decide**, **Ambiguous**, **No candidates**, and **Errors**. Offer “Best matches first” and “Needs investigation first” instead of imposing ascending score order. | Early |
| **R6 — Search for manual target** | Keep a shared search picker, but make its destination explicit. **Accept candidate** saves a review decision for later export; **Save trusted manual link** writes directly to the sidecar. Preserve that distinction and prefill the business key from the row. | Next |
| **R7 — Notes and reasons** | Keep notes optional and editable after a fast decision. Use action-appropriate presets: “record missing from SEAD” fits New better than rejection. Preserve existing notes and support deliberately clearing them. | Next |
| **R8 — Remember context** | Extend to active tab, focused business key, and scroll position. Otherwise restoring filters still leaves the user finding their place. Share the persistence mechanism with R5 and scope it by project, entity, and specification. | Early |
| **R9 — Pending exports** | Rename **Unapplied changes and verification status**. Compare decisions with owned sidecar links and New approvals. Include additions, changed targets, removals, protected links, and pending verification. Compute this on the backend. | Early |
| **R10 — Export readiness** | Reuse export rules and distinguish **blocking conflicts**, **skipped protected links**, **verification failures**, and **informational unfinished work**. Unresolved proposals are not currently an export failure. Avoid an extra confirmation dialog on every clean export. | Next |
| **R11 — Headers** | Keep as a small improvement. Shorten labels, allow wrapping, and retain full names in tooltips. “Never truncated within two lines” is unrealistic for arbitrary configured field names; define supported viewport and readable fallback behaviour. | Opportunistic |
| **R12 — Query deduplication** | Keep. Key by the complete effective query, including type, properties, limit, and matching options. Correct the wording: 500 rows currently generate 500 **queries**, batched into HTTP requests. Preserve separate decisions for separate business keys. | Early |
| **R13 — Incremental matching** | Store a query fingerprint and search outcome. An empty successful result should be reusable too; otherwise “no candidates” rows are repeatedly queried. Invalidate when inputs or matching configuration change. “Refresh all suggestions” must preserve operator decisions. | Next |
| **R14 — Progress and cancel** | Move earlier, but include repairs to the existing implementation. Define cancellation completion, disconnected-stream behaviour, result retrieval, and separate counts for rows and distinct queries. This needs more than connecting the existing dialog. | Early |
| **R15 — Candidate limit** | Keep, with an Authority Service dependency. Its current reconciliation handler uses the server default instead of the requested query limit, so the assertion that the grid can never exceed three candidates is unsupported. Consider **Load more candidates for this row** as a later companion. | Next |
| **R16 — Batch endpoint** | Keep. Define duplicate-key rejection, per-entry validation, and whole-write failure separately. Return the saved decisions so the UI can patch rows. If another review changed a decision after selection, report a conflict rather than silently replacing it. | Next |
| **R17 — Bulk decisions** | Keep after R16. Make **selected rows**, **all filtered rows**, and hidden selections unambiguous. Show eligible and skipped counts before applying. Bulk New must explain that it approves new-record handling and may permit ID allocation later. | Next |
| **R18 — Shared-label decisions** | Replace with **Review equivalent-query groups**. Default grouping should include label and mapped properties. Show differences and existing decisions, and retain separate per-key records. Never infer semantic identity from a shared label alone. | Next |
| **R19 — Partial and wildcard matching** | Separate token/substring search from wildcard syntax. Start with the observed search failure and a small fixture. Consider improving interactive alternative search before changing matching for an entire specification. Keep match explanations visible. | Later |
| **R20 — Multilingual matching** | Keep curated, type-specific aliases as the first approach. Record language and matched alias. An approved equivalent term should not automatically rank below every same-language exact label; context and identifiers must still discriminate. | Later |

Some effort estimates need increasing. R4 requires an API change; R9 needs more than accepted-link counts; R13 adds persisted matching metadata; R15 crosses services; and R18 becomes a substantive group-review feature.

A few implementation details particularly support these revisions:

- [`DecisionUpdateRequest`](https://github.com/humlab-sead/sead_shape_shifter/blob/4c55aa8b1e9812bdf767bd9bab12314cf7b6f7b1/backend/app/models/reconciliation.py#L183) excludes `proposed`, preventing the proposed undo mechanism.
- New proposals currently have no decision confidence. R5 must derive a **candidate score**, rather than sort the existing decision-confidence field.
- The [progress dialog](https://github.com/humlab-sead/sead_shape_shifter/blob/4c55aa8b1e9812bdf767bd9bab12314cf7b6f7b1/frontend/src/components/reconciliation/ReconciliationProgressDialog.vue#L174) repeats `/api/v1` in its cancellation request, while the client base already includes it. The [stream endpoint](https://github.com/humlab-sead/sead_shape_shifter/blob/4c55aa8b1e9812bdf767bd9bab12314cf7b6f7b1/backend/app/api/v1/endpoints/reconciliation.py#L260) also removes operation tracking when the stream ends, including disconnects.
- The [Authority Service handler](https://github.com/humlab-sead/sead_authority_service/blob/81614af2025515df14c79c946d6023851299858d/src/reconcile.py) passes its configured default limit to the strategy.

Confidence in these code findings: **high**. The resulting effort and usability recommendations remain estimates.

**I would add five improvements.**

| New item | Proposed improvement | Observable outcome |
|---|---|---|
| **R21 — Persistent review pane** | Selecting a row opens a side pane containing source context, candidates, alternative search, notes, and decision controls. Keep it open when advancing. Start with existing payload fields; richer remote previews can follow. | Review ten consecutive rows without repeatedly opening and closing dialogs. |
| **R22 — Flag changed source inputs** | Compare the current matching-input fingerprint with the inputs reviewed previously. Preserve accepted, rejected, and New decisions, but flag changed inputs for reassessment. Reuse R13’s fingerprint mechanism. | A changed country or coordinate cannot leave an old acceptance looking freshly reviewed. |
| **R23 — Defer and resume difficult rows** | Add **Skip for now**, initially as review-session navigation rather than a new terminal decision. Clarify Reject versus New: rejecting candidates does not approve creating a record. | Users can clear straightforward rows and return to difficult ones without recording a false decision. |
| **R24 — Direct access to saved review** | Provide **Open review / Resume review** separately from Find Candidates, including while the service is offline. Currently the specification action is labelled as finding candidates but only navigates to review, and service compatibility can disable it. | Existing proposals remain accessible without starting—or being eligible to start—a new search. |
| **R25 — Persistent results with repair actions** | Replace long export snackbars with a compact results panel. Show changed links, removals, New approvals, skipped links, and verification issues, with actions to filter or jump to affected rows. | An export problem can be located and repaired after the five-second snackbar has disappeared. |

R21 is the largest missing UX improvement. One-click acceptance helps obvious matches; a persistent pane helps everything else. It also gives keyboard navigation, notes, alternative search, and candidate comparison one consistent home.

The [current alternative-search dialog](https://github.com/humlab-sead/sead_shape_shifter/blob/4c55aa8b1e9812bdf767bd9bab12314cf7b6f7b1/frontend/src/components/reconciliation/AlternativeSearchDialog.vue#L153) should also ignore late responses from older searches, clear the selected candidate when the query changes, and remain open when saving fails. Its present accept action closes before persistence finishes.

**I would change the priority order.**

1. **Make ordinary review fast and recoverable:** R2, R1, revised R5, R4, R3, R8, and R24. Bring R9 into this set so faster decisions do not create more confusion about output.
2. **Reduce waiting and repeated navigation:** R14, R12, and R21, followed by R13 and R15.
3. **Enable deliberate batch work:** R16 and R17, then revised R18. Add R22 before encouraging extensive reuse of old decisions.
4. Improve matching through R19 and R20 after representative failed searches establish what would help.

Keep R11 opportunistic; fit R6, R7, R10, R23, and R25 around the related workflow changes.

To assess whether the experience improved, measure **time per saved decision, interactions per decision, preview requests per decision, time to resume a session, and time to repair an export problem**. Include straightforward, ambiguous, empty-result, and failed-save cases.

My readiness assessment is **revision required for the backlog as a whole**, chiefly around undo, queue semantics, export state, and shared-label propagation. The small interaction improvements can proceed once those contracts are corrected.