# Proposal: Sead Change Request Next Delivery Candidates

## Status

- Candidate scope
- Decision state: undecided
- Goal: carry forward the old Delivery 2 capabilities without implying that they are one committed delivery

## Summary

Delivery 1 is closed on the current MVP baseline.

The repository still has several capabilities that matter for a fuller operational replacement of the legacy SEAD path, but those capabilities should no longer be described as one accepted Delivery 2. They are candidates for the next delivery and still need prioritization, scoping, and acceptance decisions.

This proposal records that candidate set so the closed Delivery 1 baseline can stay closed without losing the backlog context.

Frontend workflow integration is tracked separately in [FRONTEND_UX_INTEGRATION_CR.md](./FRONTEND_UX_INTEGRATION_CR.md), with GitHub-ready issue drafts in [FRONTEND_UX_INTEGRATION_ISSUES.md](./FRONTEND_UX_INTEGRATION_ISSUES.md). The closed post-Delivery-1 follow-up record now lives in [archive/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md](./archive/closed_delivery_1/DELIVERY_1_FOLLOWUP_CR.md).

## Problem

The old Delivery 1 proposal carried a Delivery 2 section.

That was useful while the baseline was still open, but it is now misleading in two ways.

First, it makes the next step look more committed than it is. Second, it bundles several different capability areas into one implied delivery even though they may need separate proposals, separate sequencing, or separate acceptance gates.

The repository needs one place to record those remaining capability candidates without treating them as approved scope.

## Scope

This proposal covers:

- candidate capability areas that were previously grouped under Delivery 2
- the current decision state for those areas
- the rule that these items are not yet one accepted delivery plan

## Non-Goals

- committing to all candidate items as one release
- choosing the final next-delivery scope in this document
- reopening the closed Delivery 1 baseline
- covering frontend workflow integration, which is tracked separately

## Candidate Areas

| Candidate | Why it matters | Current state |
|-----------|----------------|---------------|
| Functional rollback support | Delivery 1 is explicitly non-revertible | Candidate, not accepted |
| Data-provider update scope and ownership rules | Needed before existing-row update behavior can be scoped safely | Proposed in [DATA_PROVIDER_UPDATE_SCOPING_CR.md](./DATA_PROVIDER_UPDATE_SCOPING_CR.md), not accepted |
| UPDATE handling for existing rows | Delivery 1 only handles forward inserts | Proposed in [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md), not accepted |
| Stronger idempotency and re-submission behavior | Current guarantees are intentionally narrow | Candidate, not accepted |
| Change detection | Useful for reruns and update planning | Candidate, not accepted |
| More precise ordering when deferred constraints are insufficient | Needed only if deferred FK assumptions fail in broader practice | Candidate, not accepted |
| Verification behavior beyond placeholders | Needed only if SCCS workflow requires stronger verification semantics | Candidate, not accepted |

## Decision Gates

Each candidate should be accepted only when these questions are answered for that slice:

1. Is this a real next-delivery requirement or just a desirable improvement?
2. Can it ship independently from the other candidate items?
3. Does it require frontend workflow changes, backend orchestration changes, or both?
4. Can it be validated with focused acceptance criteria rather than broad operational hopes?

## Recommended Use

Treat this document as a staging proposal, not as an implementation plan.

When one candidate becomes real scope, either:

- convert this document into a narrower accepted proposal for that chosen slice, or
- create a more focused follow-up proposal and remove the accepted item from this candidate list

That keeps the next delivery concrete and prevents the repository from silently carrying an omnibus Delivery 2 commitment.

## Validation And Acceptance Criteria

- the closed Delivery 1 baseline no longer carries committed later-delivery scope
- the remaining capability areas are visible without being treated as accepted scope
- this document makes the undecided state explicit
- the document points to separate proposals for artifact hardening, frontend UX integration, provider update scope, and update handling

## Final Recommendation

Do not treat the old Delivery 2 list as a committed delivery.

Keep these items as explicit candidates until the repository is ready to choose the next real decision boundary. When that choice is made, open a narrower proposal for the selected capability rather than reviving a broad omnibus Delivery 2.