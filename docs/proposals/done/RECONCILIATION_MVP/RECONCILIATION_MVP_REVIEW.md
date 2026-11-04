# Review: Reconciliation MVP and Reconciliation Identity Contract

Review date: 2026-10-30. This is advice, not approval.

Reviewed proposals:

- [Reliable Reconciliation Links to Existing SEAD Entities](RECONCILIATION_MVP.md) (Shape Shifter)
- [Verify Reconciliation Candidates Against SEAD and SIMS](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md) (Authority Service)

## Overall assessment

The diagnosis is sound. The main current-behavior claims were checked against code:

- A sidecar `Link` has no owner field ([mapping_model.py](../../../../src/reconciliation/mapping_model.py)).
- Export keys links by `resolved_pair.source_value` and never removes stale links ([service.py](../../../../backend/app/services/reconciliation/service.py)).
- Entity resolvers are capped at `limit=1000` ([resolvers.py](../../../../backend/app/services/reconciliation/resolvers.py)).
- `_pick_best_candidate` falls back to the top score without requiring `match` ([ingester_runtime.py](../../../../backend/app/services/ingester_runtime.py)).
- The ID is extracted with a bare `/(\d+)/?$` regex.
- SIMS `resolve_identity` looks up an approved aggregate ID without checking lifecycle state (Authority Service `src/identity/service.py`).
- `default_query_limit` overrides the per-query limit (Authority Service `src/reconcile.py`).

The responsibility split is good: the Authority Service does read-only verification, SIMS does binding, and Shape Shifter owns approval and row keys. Rejecting `POST /identity/resolve` as a review-time lookup is correct because it writes state.

The main concerns are scope, a hard dependency on unplanned work, and a fail-closed design that has not been costed.

Not verified: the UI/backend contract mismatch, the HTTP 500 on `authority.fuzzy_site`, and whether `Link` tolerates new fields.

## Findings

### High

**1. The "narrow MVP" is not narrow, and one gating dependency has no plan.**

- **Where:** MVP Summary, Scope, Final Recommendation, Planning Handoff.
- **Issue:** Scope bundles about seven workstreams: full-coverage matching, a key-model change, a UI/backend decision contract, ownership plus legacy-link migration, four verification points, an ingester behavior change, and an Authority Service companion. Everything is gated on `materialized` SIMS identities for existing SEAD rows. The Authority Service's `SIMS_TARGET_ID_CONTRACT.md` says existing-data migration and cutover are outside its task and "separate operational work", and no plan for that work was found. Without it, every candidate is ineligible and the MVP produces zero links. It is only listed as a "blocking decision".
- **Recommendation:**
  - Make existing-data adoption of the pilot type an explicit prerequisite with a named owner or document.
  - Mark which `P-AC-*` criteria gate the first pilot and which can follow. Row-key alignment, coverage, UI contract, and ownership do not depend on the Authority Service and could ship first.
  - Reconsider the word "narrow" in the Final Recommendation.
- **Confidence:** High on the dependency gap. Medium on the best split.

**2. Fail-closed live verification at normalization is a major unexamined tradeoff.**

- **Where:** MVP "Eligibility at each use", P-AC-7.
- **Issue:** Normalization currently applies committed links from the sidecar deterministically ([normalizer.py](../../../../src/normalizer.py)). The proposal makes it depend on live Authority Service and SIMS availability, aborts the entity if the service is down, and aborts if no verifier is configured. Consequences:
  - Every existing project with exported reconciliation links stops normalizing until a verifier is configured.
  - Runs are no longer reproducible offline or in CI.
  - An abort "for the affected entity" can leave dependent entities and foreign keys undefined; the pipeline behavior is not stated.
  - Core `src/` cannot import backend code. The proposal does not say how the verifier is injected (a protocol passed at the mapper boundary would be consistent with repo rules).
  - Normalization is immediately followed by change-request generation, which rechecks the same facts, so the two checks largely duplicate each other.
  - Alternatives Considered does not weigh any cheaper option.
- **Recommendation:**
  - Choose the authoritative recheck points and justify each. For example, make the export check authoritative, store verification metadata on the link, and make the normalization preflight an explicit opt-in or per-project mode with a stated abort scope.
  - State the injection mechanism and the backward-compatibility behavior for existing sidecars.
  - Add the offline and CI tradeoff to Risks.
- **Confidence:** High that the tradeoff is unexamined. Medium on the better design.

### Medium

**3. The wire contract between the two proposals is not owned by either.**

- **Where:** Both Proposed Design sections, Authority Planning Handoff.
- **Issue:** Both call the endpoint names "provisional". The outcome categories are described in prose but have no fixed names or semantics. The ID base and type path are to be "published", but not where, such as the manifest or the verification response. Shape Shifter parses and validates the URI and maps strategy to SIMS type, then sends the typed pair back to the service that minted the URI. That duplicates logic across repositories. Current code builds `id` from `options:id_base` resolved `or ""` (Authority Service `src/strategies/strategy.py`), so a misconfigured base yields a relative ID. Both proposals use `P-AC-1`..`P-AC-7`, which will collide in phase planning.
- **Recommendation:**
  - Make the Authority proposal the single normative contract. Fix the request and response shape, a closed set of outcome codes, batch limits, and where the ID base is published.
  - Link the Shape Shifter proposal to it instead of restating the URI rules.
  - Consider letting the service accept the candidate `id` plus strategy and return the canonical `(type, id)`.
  - Say how the two sets of AC IDs are told apart, for example by repository prefix.
  - Also consider placing the endpoint beside `/identity/*`, which already carries the access controls and policy, rather than under the OpenRefine `/reconcile` namespace.
- **Confidence:** High on the gaps. Low to Medium on the endpoint placement.

**4. Ownership cleanup has an undefined trigger, and the key change implies a catalog migration.**

- **Where:** MVP "Review, persistence, and export", P-AC-2, P-AC-4.
- **Issue:**
  - **Removed specifications.** Export runs per `(entity, target_field)`. A removed specification has nothing to export, so the stated rule "remove stale links, including when a specification is removed" has no mechanism.
  - **Existing catalogs.** The proposal says today's catalog identifies results by search-field value and the new design identifies decisions by `local_key`. How existing catalog data is migrated or invalidated is not stated.
  - **Owner field.** An `owner` field on a persisted `Link` changes the sidecar schema. The proposal does not mention reader compatibility. Whether `Link` rejects unknown fields was not verified.
  - **Unowned-link volume.** No `source: reconciliation` links were found under `data/projects`, so the number of unowned links, and so the size of the review flow, is unknown. A full operator review flow may be over-scoped for the actual volume.
- **Recommendation:**
  - State when stale-owner cleanup runs, for example on specification delete or via an explicit reconcile-sidecar action.
  - State the catalog migration or reset rule and the sidecar schema compatibility rule.
  - Size the legacy links, and if few, replace the review flow with a report-and-block check.
- **Confidence:** Medium.

**5. Several acceptance criteria and key rules are not yet testable.**

- **Where:** MVP P-AC-1, P-AC-3, P-AC-5, "Review, persistence, and export".
- **Issue:**
  - P-AC-1 requires "one named type", but the type is undecided and `site` is only a candidate.
  - "Accurate confidence" and an auto-accept rule that "must account for ambiguity" have no threshold or margin. The ingester rule in P-AC-5 depends on the open question about pre-linked `public_id` values.
  - SIMS must recheck state "between resolution and binding", but the design does not say how, for example a row lock or a same-transaction check. This matters because the proposal itself notes the check cannot be atomic across SEAD and SIMS.
- **Recommendation:**
  - Fix the pilot type before approval.
  - State the minimum acceptance rule, such as `match=true` plus a score margin over the second candidate.
  - Resolve or tightly bound the `public_id` question.
  - Name the concurrency mechanism for the SIMS rebind check.
- **Confidence:** Medium.

### Low

**6. Bundled and overlapping scope in the Authority proposal.** The per-query `limit` and HTTP 4xx fixes are valid but independent of the identity contract. They are small, but keeping them in the same acceptance set (P-AC-5) adds noise. Keep them as a separate low-risk item or confirm they are cheap. Confidence: Medium.

**7. Document-structure nits.** Neither proposal has an Open Questions section, though both have real ones (pilot type, `public_id` rule, cross-process sidecar locking). These sit in Planning Handoff instead. Confidence: High, low impact.

## Planning readiness

**Shape Shifter MVP: Decision required.** Scope, the existing-data adoption dependency, and the cost of live verification at normalization must be decided before phase planning. These are material to the delivery sequence. The pilot type is also unresolved.

**Authority Service Identity Contract: Ready with minor revisions.** The design is coherent and correctly separated. It needs a fixed, normative contract (names, response shape, ID base location) and a rebind concurrency note. Its phase planning is blocked until the pilot type and the existing-data adoption plan are confirmed, which its own Planning Handoff already lists.
