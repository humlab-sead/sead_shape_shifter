# Proposal: Derived-Value Ergonomics Follow-Through

## Summary

This proposal covers the remaining work needed to make derived values easy to author, validate, preview, and maintain in Shape Shifter.

It does not propose a new derived-value primitive. It assumes the current baseline already exists through `extra_columns`, interpolation, and formula expressions, and focuses on the remaining ergonomics work around that baseline.

The practical question is not "how do we compute a derived value at all?" It is "how do we make the existing capability predictable, visible, and hard to misuse?"

## Problem

Derived values can already be expressed, but the remaining user experience is still uneven.

The main gaps are:

- authors do not always know when to use a direct copy, interpolation, constant, or formula
- validation feedback is still not strong enough for missing references, bad formulas, or stage-order confusion
- preview does not always make derived columns obvious enough during authoring
- the editor does not yet provide enough inline guidance or assistance for complex `extra_columns` usage
- the current guidance is spread across multiple documents and examples instead of presented as one clear recommended pattern

In practice this means the core mechanism exists, but the authoring experience is still more fragile than it should be.

## Goals

- Make `extra_columns` the clearly documented default place for lightweight derived values
- Make the choice between direct copy, constant, interpolation, and formula obvious
- Surface broken references and invalid formulas early
- Make derived columns easy to inspect in preview and editor flows
- Improve confidence that derived-value behavior matches what the YAML appears to say
- Avoid introducing a second overlapping feature unless a real gap remains after the ergonomics work is complete

## Non-Goals

- Add a second general-purpose derived-value feature alongside `extra_columns`
- Replace the current interpolation or formula support
- Reframe this as a new SQL-oriented computation system by default
- Solve branch topology, merged-parent semantics, or fact-versus-lookup intent in this proposal

Those broader modeling concerns remain in [COMPLEX_ENTITY_MODELING_ERGONOMICS.md](COMPLEX_ENTITY_MODELING_ERGONOMICS.md).

## Expected Outcome

When this proposal is complete:

- authors can reliably reach for `extra_columns` first
- users can tell which style to use for a given derived-value problem
- broken derived-value configurations fail early and clearly
- preview makes derived columns visible enough that authors do not need to infer behavior indirectly
- the team can make an informed decision about whether any further feature is still needed

## Phased Implementation Checklist

### Phase 1: Documentation Baseline

Goal: make the recommended path explicit and consistent before adding more behavior.

- [ ] Add one canonical derived-value section to `docs/CONFIGURATION_GUIDE.md`
- [ ] Add a short "which mechanism should I use?" decision guide covering copy, constant, interpolation, and formula usage
- [ ] Add one interpolation-heavy example based on a synthetic identifier or label
- [ ] Add one formula-heavy example based on lightweight transformation logic
- [ ] Update relevant UI help text so it matches the canonical terminology and examples

### Phase 2: Validation Follow-Through

Goal: catch the common authoring mistakes early and explain them clearly.

- [ ] Review current `extra_columns` validation coverage and document the gaps
- [ ] Add validation for missing interpolation placeholders
- [ ] Add validation for invalid or unsupported formula usage
- [ ] Distinguish syntax errors from likely stage-order or missing-column errors where practical
- [ ] Improve error messages so they include entity, field, and failing expression context
- [ ] Add tests for missing references, invalid formulas, and mixed `extra_columns` blocks

### Phase 3: Preview Visibility

Goal: make derived columns and their failures obvious during normal authoring.

- [ ] Decide how derived columns should be marked in preview output
- [ ] Surface derived-column evaluation errors in preview-related responses
- [ ] Verify preview behavior for derived columns added after other transformations
- [ ] Make it clear which preview values come from the raw source and which come from `extra_columns`
- [ ] Add or refine UI affordances so users can recognize derived columns quickly

### Phase 4: Editor Support

Goal: reduce guesswork in `ExtraColumnsEditor` before save or execute time.

- [ ] Review `ExtraColumnsEditor` for missing guidance and ambiguity
- [ ] Add concise inline help for copy vs interpolation vs formula usage
- [ ] Add examples or quick patterns directly in the editor flow or linked context help
- [ ] Add editor-side hints or suggestions for interpolation placeholders and formula arguments where low-risk and useful
- [ ] Add inline or near-inline validation where practical
- [ ] Add frontend coverage for the main guidance and validation behaviors if UI changes are introduced

### Phase 5: Decision Gate

Goal: decide whether any further feature is actually needed.

- [ ] Re-evaluate whether recurring real-world cases still remain awkward after Phases 1 to 4
- [ ] Document any remaining gap concretely, with examples, before proposing a separate `computed_columns` feature
- [ ] If no strong recurring gap remains, close this proposal without introducing a second derived-value system

## Completion Criteria

This proposal should be considered complete when:

- the recommended derived-value path is documented clearly and consistently
- validation catches the common failure modes early
- preview makes derived columns understandable during authoring
- editor help reduces guesswork for common patterns
- there is a clear written decision on whether any follow-on feature is still justified

## Relationship To Other Proposals

- This proposal is a supporting ergonomics proposal for [COMPLEX_ENTITY_MODELING_ERGONOMICS.md](COMPLEX_ENTITY_MODELING_ERGONOMICS.md).
- It should land before or alongside branch-aware modeling improvements where those improvements depend on authors creating branch markers or synthetic identifiers cleanly.
- It does not replace the broader complex-entity proposal; it narrows one part of that work into a more actionable follow-through track.