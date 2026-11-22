# Search and Browse Backlog Ownership and Replacement

This sidecar records the backlog disposition for the approved [Search and Browse proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md). It does not mark issues done or change the backlog automatically. “Absorb” means delivery and acceptance move under the proposal; “partial” leaves the named remainder independent.

| Backlog item | Disposition | Relationship |
|---|---|---|
| R1 Top candidate in grid | Independent | Suggested-candidate speed improvement; no prerequisite for Search/Browse. |
| R2 Saved-row patch | Absorb | Shared save/update mechanism for pane and existing grid. |
| R3 Keyboard review | Partial | Search/Browse focus and decision loop included; broader grid shortcuts remain a follow-up using the same navigation actions. |
| R4 Undo | Independent | Can consume conditional saves later; does not block this proposal. |
| R5 Needs review queue | Partial | Basic membership/counts/navigation included; score sorting, ambiguity categories, and threshold views remain. Remove R1 as a prerequisite for basic queue access. |
| R6 Trusted manual-link picker | Dependent follow-up | Reuse the new picker; immediate trusted sidecar writes remain a separate labelled action and are not introduced here. |
| R7 Notes/reasons | Partial | Optional inline notes included; presets and editing notes across every decision surface remain. |
| R8 Remember context | Partial | Workspace mode, query/filter/sort and focused row included; wider project/grid state restoration remains. |
| R9 Unapplied changes | Partial | Clear Save decision versus Export labels only; application-state calculation, detailed counts, and full diagnostics remain deferred. |
| R10 Pre-export check | Independent | Preserve its future reuse of export rules; no extra confirmation added to ordinary decisions here. |
| R11 Headers | Independent | Cosmetic grid change, unrelated to the service contract. |
| R12 Query deduplication | Independent | Batch optimization; manual lookup does not wait for it. |
| R13 Matching fingerprints | Independent | Batch candidate reuse; browser draft source values are not a persisted historical fingerprint model. |
| R14 Batch progress/cancel | Independent | Long-running matching work; interactive request cancellation is included here without adopting the batch job system. |
| R15 Candidate limit | Partial; service forwarding exists | Preserve the implemented per-query limit/default handling. Interactive caps and end-to-end checks belong here; per-specification batch candidate-count configuration remains. |
| R16 Batch decision endpoint | Absorb | One atomic save for independently chosen browser drafts is included; bulk assignment remains out of scope. |
| R17 Bulk actions | Independent | Not required for a fast one-row search/browse loop. |
| R18 Equivalent-query groups | Independent | No propagation of decisions from shared labels or reused query text. |
| R19 Partial/wildcard matching | Partial; classifier prefix lookup exists | Reuse existing prefix autocomplete and add literal substring Browse filtering. Reassess failed-search fixtures against `dev`; fuzzy match-kind ranking and wildcard syntax remain separate. |
| R20 Multilingual aliases | Follow-up extension | Operator-entered translated queries work now; curated aliases and automatic multilingual retrieval remain later service work. |
| R21 Persistent pane | Absorb | This proposal becomes the pane's design owner; legacy candidate review uses the same component/actions. |
| R22 Changed historical inputs | Independent | Must later reuse compatible snapshot/input descriptions, but does not gate first-time decisions or basic resume. |
| R23 Skip/resume | Absorb for this workspace | No new terminal decision status; shared navigation can be reused by grid review. |
| R24 Open saved review | Absorb remaining navigation work | Preserve the review tab’s independent preview loading; remove compatibility gating from review entry and give it a distinct Open/Resume review label. |
| R25 Retained export results | Independent | Reuse selection/navigation actions for repair later; no full export-result redesign here. |
| R26 Search-first workspace | Replace standalone design | Covered by this proposal's Search/Browse pane. |
| R27 Responsive search | Absorb | One request-state implementation also serves browsing and details. |
| R28 Keyboard search/decide/advance | Absorb | Included end to end, with explicit New and failure recovery. |
| R29 Independent text/context | Absorb | Standard search plus declared browse filters; no implicit automatic translation. |
| R30 First-time decisions | Absorb | Browser drafts, save-time source validation, catalog-hash checks, and no matching prerequisite. |
| R31 Search history | Deferred | Recent-query history is not part of the first release; per-row query drafts remain part of workspace resume. |
| Browsing, discussed as R32 | New scope here | Not yet a numbered item in the supplied backlog. Do not create a competing standalone design; track service/UI work under the proposal. |

Existing tracking issues can remain separate delivery units linked to the proposal. Cross-service service-contract work needs an Authority Service issue; frontend and review-decision work belongs in Shape Shifter. No issue numbers or implementation owners have been assigned.
