## Overall assessment

This is a strong change request. It has a clear problem statement, a plausible target architecture, a deliberately constrained MVP, and a useful handoff breakdown. The main proposal—generate SEAD Change Control System-ready SQL directly from normalized DataFrames after SIMS/reconciliation identity resolution—is coherent and well aligned with the stated goal of removing the Clearinghouse/Transport System path. 

My recommendation would be: **approve for Delivery 1 discovery/scaffolding, but not yet for full implementation until a few blocking decisions are closed**.

## What works well

The strongest part is the sequencing rule: **resolve all identities before generating SQL**. That is the right architectural anchor. It prevents the ingester from becoming another partial staging mechanism and makes the generated SQL auditable, deterministic, and closer to a true change-control artifact.

The Delivery 1/Delivery 2 split is also sensible. Keeping Delivery 1 forward-only, INSERT-only, and fail-fast avoids the trap of trying to solve rollback, update semantics, reconciliation gaps, and re-submission behavior all at once. The document is honest that Delivery 1 proves the direct path rather than fully replacing the operational legacy path. 

The implementation issue breakdown is useful and mostly in the right order: scaffold, define handoff contract, extract target metadata, orchestrate identities, materialize PK/FK values, run collision checks, generate artifacts, associate with SIMS, then pilot. 

## Main concerns

### 1. “Existing rows are excluded” may be too simple

The biggest design risk is the rule that rows with populated `public_id` are treated as existing and not inserted. That is probably correct for entity tables, but it may be wrong for relationship or bridge rows.

For example, an existing taxon, site, sample group, or method may still need a **new association row**. The open question about bridge-table inserts is therefore not minor; it is likely a Delivery 1 blocking issue. I would promote it from “Open Question” to “Decision required before Issue 3/5.”

Suggested rule:

> Delivery 1 should exclude existing entity rows from entity-table inserts, but must still evaluate derived bridge/association rows independently based on their own identity or composite uniqueness rule.

### 2. The source handoff contract is underspecified

The proposal says normalized DataFrames are the input, but also says the current ingester framework may be path-based. That interface decision affects almost every implementation issue. 

Before implementation, define one explicit contract, for example:

```text
SeadCrIngester.ingest(
    frames: Mapping[str, pandas.DataFrame],
    target_model: TargetModel,
    submission_context: SubmissionContext,
    config: IngesterConfig
) -> ChangePackage
```

or, if the existing interface must remain path-based, define a clear adapter boundary:

```text
Normalized artifact path -> loader -> DataFrame bundle -> sead_cr orchestration
```

The important thing is to avoid quietly depending on the old Excel/CSV dispatch flow while claiming the new path is DataFrame-first.

### 3. “Resolved SEAD integer ID” needs a stricter definition

The change request says every row must have a resolved SEAD integer ID before SQL generation. That is good, but Delivery 1 should distinguish at least four cases:

| Case                                  | Meaning                                               | SQL behavior                     |
| ------------------------------------- | ----------------------------------------------------- | -------------------------------- |
| Existing entity                       | `public_id` maps to current target row                | Reference only, no entity insert |
| Newly allocated provider-owned entity | SIMS allocated/bound a new target ID                  | Insert                           |
| Reconciled classifier                 | Reconciliation matched an existing target row         | Reference only, no insert        |
| Derived bridge row                    | Identity may be composite, not necessarily SIMS-owned | Insert only if absent            |

Without that distinction, the implementation may either over-insert or under-insert relationship rows.

### 4. Placeholder revert scripts may be operationally risky

The proposal allows placeholder `revert/...` and `verify/...` files if the Change Control workflow requires them.  That is acceptable for an MVP, but I would make the placeholder behavior stricter:

* The revert script should fail loudly, not silently no-op.
* The deploy metadata should mark the change as **non-revertible**.
* The pilot must confirm that a non-functional revert file is acceptable to SEAD release practice.

A silent placeholder revert would be dangerous because it could give operators false confidence.

### 5. Collision checks are necessary but not sufficient for idempotency

The proposed Delivery 1 collision check verifies whether the resolved target-facing ID already exists in the target table. That catches duplicate primary IDs, but it will not catch duplicates caused by natural/composite uniqueness constraints, especially for bridge tables and lookup-like rows.

For Delivery 1 this may be acceptable, but the limitation should be explicit:

> Delivery 1 idempotency is limited to target ID collision detection and does not guarantee semantic duplicate detection across natural keys or composite relationship keys.

Then add a test/pilot scenario that demonstrates what happens when a bridge row already exists.

## Recommended changes before approval

I would revise the change request in these areas:

1. **Move bridge-row handling from open question to Delivery 1 design decision.**
   Define how association rows are identified, checked, and inserted when parent entities already exist.

2. **Define the DataFrame handoff contract explicitly.**
   Decide whether `sead_cr` accepts in-memory DataFrames, serialized normalized artifacts, or both.

3. **Add a “row state model.”**
   Include states such as `existing_reference`, `new_insert`, `matched_reference`, `derived_insert`, and `blocked_unresolved`.

4. **Tighten revert/verify placeholder semantics.**
   Revert placeholders should fail explicitly and be labelled as non-functional.

5. **Expand collision checks for bridge tables.**
   At minimum, Delivery 1 should check primary ID collisions plus configured unique/composite keys where available from target metadata.

6. **Clarify Binding Set confirmation flow.**
   The proposal says to stop if confirmation cannot be completed, but the operator workflow is still unclear. Decide whether the ingester is synchronous-only, produces a pending report, or can resume after manual confirmation.

## Suggested revised acceptance criteria

I would add these to Delivery 1:

* [ ] Existing entity rows may be referenced by new bridge/association rows without re-inserting the existing entity rows.
* [ ] Bridge/association rows have an explicit identity or uniqueness rule used for insert/collision decisions.
* [ ] The ingester exposes a documented DataFrame handoff contract or adapter boundary.
* [ ] Generated revert placeholders fail explicitly and identify the change as non-revertible in Delivery 1.
* [ ] Collision diagnostics include primary-key collisions and, where metadata exists, composite/natural-key collisions.
* [ ] Binding Set confirmation behavior is documented for both automatic and manual-confirmation cases.
* [ ] The pilot includes at least one mixed submission containing existing references, new provider-owned entities, classifiers, and bridge rows.

## Delivery recommendation

I would approve **Issues 1–3 immediately** as low-risk preparatory work:

1. Scaffold the new ingester.
2. Define the source handoff contract.
3. Build target model extraction and row partitioning.

I would hold **Issues 4–7** until the bridge-row, Binding Set confirmation, and artifact-contract decisions are closed. Those issues encode the core correctness guarantees, and ambiguity there could lead to a misleading MVP.

## Bottom line

This is a good and implementable change request. The architecture is directionally sound, especially the “identity first, SQL second” rule. The main gap is that Delivery 1 still needs a sharper model for **existing references versus new inserts**, especially for bridge/association rows. Resolve that, define the DataFrame contract, and make placeholder rollback behavior explicit; then the proposal is ready to move into implementation.
