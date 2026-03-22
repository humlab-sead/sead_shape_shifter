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

Those broader modeling concerns remain in [../COMPLEX_ENTITY_MODELING_ERGONOMICS.md](../COMPLEX_ENTITY_MODELING_ERGONOMICS.md).

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

- [x] Add one canonical derived-value section to `docs/CONFIGURATION_GUIDE.md`
- [x] Add a short "which mechanism should I use?" decision guide covering copy, constant, interpolation, and formula usage
- [x] Add one interpolation-heavy example based on a synthetic identifier or label
- [x] Add one formula-heavy example based on lightweight transformation logic
- [x] Update relevant UI help text so it matches the canonical terminology and examples

### Phase 2: Validation Follow-Through

Goal: catch the common authoring mistakes early and explain them clearly.

- [x] Review current `extra_columns` validation coverage and document the gaps
- [x] Add a dedicated entity-level preflight validation pass for `extra_columns` expressions
- [x] Add validation for missing interpolation placeholders
- [x] Add validation for invalid or unsupported formula usage
- [x] Distinguish syntax errors from likely stage-order or missing-column errors where practical
- [x] Improve error messages so they include entity, field, and failing expression context
- [x] Add tests for missing references, invalid formulas, and mixed `extra_columns` blocks
- [x] Surface unresolved deferred `extra_columns` as structured validation results instead of final log-only warnings
- [x] Decide whether `extra_columns` name conflicts should remain warning-and-skip or become stronger validation feedback

#### Current Validation Coverage And Gaps

Current coverage is split between static project validation and runtime evaluation.

What is already covered:

- runtime evaluation supports copies, constants, interpolation, escaped leading `=`, and DSL formulas
- interpolation fails when referenced columns are missing, or defers cleanly when the pipeline is allowed to wait for FK or unnest-added columns
- formula evaluation already parses and validates DSL syntax, allowed functions, arity, referenced columns, and evaluator safety limits
- entity validation now fails when `extra_columns` names conflict with columns, keys, IDs, or unnest-generated names
- downstream validation already treats `extra_columns` outputs as available columns for later FK and unnest checks
- full-data validation now reports unresolved deferred `extra_columns` as structured validation errors with entity, field, expression, and missing-column context
- tests already cover mixed `extra_columns` blocks and a wide range of interpolation and DSL runtime behaviors

Main gaps still remaining:

- there is no dedicated entity-level preflight validation pass for `extra_columns` expressions themselves; most expression problems are still caught only during evaluation
- missing interpolation placeholders are primarily detected at runtime rather than surfaced as early structured validation results
- invalid or unsupported formulas are primarily detected during runtime compilation/evaluation rather than by project validation before preview or normalize
- current runtime errors do not consistently distinguish syntax problems from missing-column or stage-order problems in a user-facing way
- there is still no focused validation message shape that consistently includes entity, field, and failing expression for every derived-value failure mode

Implication for Phase 2:

The remaining work is now mostly about tightening message consistency across all failure modes. The core evaluator and the major author-facing validation paths are in place.

### Phase 3: Preview Visibility

Goal: make derived columns and their failures obvious during normal authoring.

- [x] Decide how derived columns should be marked in preview output
- [x] Surface derived-column evaluation errors in preview-related responses
- [x] Verify preview behavior for derived columns added after other transformations
- [x] Make it clear which preview values come from the raw source and which come from `extra_columns`
- [x] Add or refine UI affordances so users can recognize derived columns quickly

### Phase 4: Editor Support

Goal: reduce guesswork in `ExtraColumnsEditor` before save or execute time.

- [x] Review `ExtraColumnsEditor` for missing guidance and ambiguity
- [x] Add concise inline help for copy vs interpolation vs formula usage
- [x] Add examples or quick patterns directly in the editor flow or linked context help
- [x] Add editor-side hints or suggestions for interpolation placeholders and formula arguments where low-risk and useful
- [x] Add inline or near-inline validation where practical
- [x] Add frontend coverage for the main guidance and validation behaviors if UI changes are introduced

### Phase 5: Decision Gate

Goal: decide whether any further feature is actually needed.

- [x] Re-evaluate whether recurring real-world cases still remain awkward after Phases 1 to 4
- [x] Document any remaining gap concretely, with examples, before proposing a separate `computed_columns` feature
- [x] If no strong recurring gap remains, close this proposal without introducing a second derived-value system

#### Phase 5 Decision

Decision: close this proposal without introducing a separate `computed_columns` feature.

What was re-evaluated:

- current real-world `extra_columns` usage in Arbodat-style test projects
- current documentation and examples for copy, constant, interpolation, and formula patterns
- implemented validation, preview, and editor support added through Phases 1 to 4
- adjacent proposal work in [../COMPLEX_ENTITY_MODELING_ERGONOMICS.md](../COMPLEX_ENTITY_MODELING_ERGONOMICS.md)

What now appears sufficient:

- direct copies and lightweight renames
- constant columns and default flags
- synthetic labels and identifiers built from interpolation
- lightweight string cleanup, fallback handling, and formatting through DSL formulas
- deferred derived values that depend on FK-added or unnest-added columns, with structured feedback when they still fail

What does not currently justify a second derived-value feature:

- no recurring project pattern has been identified that needs a second general-purpose derivation primitive rather than better use of `extra_columns`
- the current `extra_columns` path now works across entity types, not just SQL-backed entities
- the remaining awkwardness seen in more complex examples is primarily about modeling intent, branch topology, merged-parent semantics, and fact-versus-lookup roles, not about the ability to compute a value

Documented remaining gap:

- a strong recurring gap for value derivation itself was not found
- where authoring still feels awkward, the problem belongs to broader modeling ergonomics tracked in [../COMPLEX_ENTITY_MODELING_ERGONOMICS.md](../COMPLEX_ENTITY_MODELING_ERGONOMICS.md), especially around explicit branch structure and branch-scoped consumers

Conclusion:

`extra_columns`, interpolation, and DSL formulas are now the recommended and sufficient derived-value path for lightweight entity-level computation in Shape Shifter. If a future SQL-specific computed-expression feature is ever considered, it should be treated as a separate problem with separate semantics, not as unfinished work from this proposal.

## Completion Criteria

This proposal should be considered complete when:

- the recommended derived-value path is documented clearly and consistently
- validation catches the common failure modes early
- preview makes derived columns understandable during authoring
- editor help reduces guesswork for common patterns
- there is a clear written decision on whether any follow-on feature is still justified

## Relationship To Other Proposals

- This proposal is a supporting ergonomics proposal for [../COMPLEX_ENTITY_MODELING_ERGONOMICS.md](../COMPLEX_ENTITY_MODELING_ERGONOMICS.md).
- It should land before or alongside branch-aware modeling improvements where those improvements depend on authors creating branch markers or synthetic identifiers cleanly.
- It does not replace the broader complex-entity proposal; it narrows one part of that work into a more actionable follow-through track.