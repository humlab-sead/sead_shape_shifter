# Linked Art Export from Shape Shifter

## Status

- **Proposed change request — draft for review.**
- **Scope:** A small, narrowly scoped prototype that exports SEAD data as Linked Art, using Shape Shifter transformations and a registered output dispatcher (the pluggable component that writes results to a destination).
- **Goal:** Decide whether valid Linked Art output can be produced without changing Shape Shifter's relational transformation model — the rule that data is transformed table by table, with links expressed as foreign keys.
- **Decision requested:** Approve the prototype and its architectural constraints. Whether to support it in production is a separate decision, taken after the results are known.

## Summary

Use Shape Shifter to turn SEAD data into explicit target entities and the relationships between them. A dedicated exporter then assembles those tables into validated Linked Art JSON-LD (JSON for linked data), plugged into the existing dispatcher mechanism.

Keep decisions about what the data means in project configuration and target mapping definitions. Keep the rules for how the JSON is laid out in the exporter.

Start with one site, one sample and one analysis containing several results. Continue only if most of the work can be done with existing transformations and a small amount of adapter code. Needing substantial changes to Shape Shifter's core transformation engine, or a second mapping language inside the exporter, is a reason to narrow the scope or stop.

## Problem

SEAD is preparing to publish data using Linked Art. That requires rebuilding entities and relationships from relational tables, resolving controlled vocabulary terms to shared identifiers, preserving record identities, and expressing the result with Linked Art patterns.

A separate export script could repeat the mapping, linking and validation work that Shape Shifter already does. On the other hand, adding arbitrary graph processing or ontology reasoning (inferring facts from a formal model) would push Shape Shifter beyond its purpose: transforming one relational structure into another.

The decision is whether the chosen Linked Art target can be described as relational tables that Shape Shifter's existing workflow can produce, leaving the exporter with a small, explicit job: writing the JSON.

## Scope

- A representative, read-only export of SEAD data from published sources.
- An agreed Linked Art representation for the selected data, including what is deliberately left out.
- Target entities and relationships expressed as tabular transformation results; no intermediate database is needed.
- A target-specific exporter, a publication URI policy (how public identifiers are formed) and validation results.
- A feasibility assessment that names reused configuration, required adapter code and any remaining product changes.

## Non-Goals

- Full coverage of SEAD's scientific domains.
- A general RDF mapping engine, ontology editor, reasoning system or graph database.
- Changes to the Core pipeline order or to the foreign-key identity contract.
- Allocating institutional identities inside Shape Shifter.
- Hosting a Linked Art API, public deployment, harvesting, incremental publication or deletion handling.
- A graph-editing interface, or automatic inference of domain facts that are missing from the source.

## Current Behavior

Verified by read-only inspection of the repository's `main` branch on 2026-10-28:

- [ShapeShifter.store()](../../../src/normalizer.py) selects a registered dispatcher and passes it the project and the normalized `TableStore`.
- [Dispatchers](../../../src/dispatch.py) already supports CSV folders, zipped CSV, Excel and database output. Its `dispatch(target, data)` contract is a good candidate for Linked Art file output. The inspected registrations contain no Linked Art exporter.
- [TableStore](../../../src/table_store.py) holds named pandas DataFrames, one table per name. The proposed intermediate representation therefore fits the current result container.
- [TargetModel and EntitySpec](../../../src/target_model/models.py) describe entities, columns, uniqueness and foreign keys. They forbid undeclared fields, and they provide no way to declare Linked Art classes, properties or embedded structures.
- The [ingester protocol](../../../backend/app/ingesters/protocol.py) accepts normalized table input, but its base configuration requires database connection fields. The existing dispatcher is the closer fit for a file-only export.
- The [agent guide](../../../AGENTS.md) fixes the Core stage order and keeps three things separate: local `system_id` links, business keys and target ID columns. These contracts must be preserved.

**Not yet demonstrated:** Three things remain unproven. First, that the selected SEAD scientific mapping can be expressed with existing transformations. Second, that existing callers can expose a new dispatcher without extra integration changes. Third, that the prototype can handle production data volumes. These are feasibility questions, not claims about shipped behavior. The inspection did not run the pipeline or the tests.

**External model:** Linked Art is a CIDOC CRM application profile, that is, a shared cultural-heritage model, with an event-based structure and JSON-LD serialization [1, 2]. References between records and embedded structures follow specific representation rules [3]. Valid JSON alone therefore does not prove Linked Art conformance.

## Proposed Design

### Transform into a relational representation of the target

Define the required target entities before writing the exporter. Shape Shifter selects and transforms source data into the agreed places, actors, sample descriptions, activities, measurement descriptions and classifications. The exact classes and relationships depend on the approved SEAD mapping.

Target entities may combine information from several source tables, or split one source record into several target entities. Derived entities must represent facts the source supports. Missing analyst names, methods or event dates must stay unknown.

Define a separate relational target model for the export project where the existing format is sufficient. Its entities describe the intermediate output, not physical tables that must be created in SEAD. Do not add Linked Art properties to the existing SEAD ingestion model, and do not treat the current target-model format as validating JSON-LD. Rules specific to the export — classes, properties and embedded structures — belong in a small, separately defined adapter profile. Its configuration location is resolved during design verification.

Keep target results inspectable through the existing result facilities where they support it. Use ordinary entity relationships instead of building large JSON strings in transformation expressions. Preserve one-to-many relationships without duplicate rows (Cartesian multiplication) or repeated measurements.

### Separate semantic mapping from serialization

| Responsibility | Proposed location |
|---|---|
| Source selection, joins, reshaping and deduplication | Existing transformation pipeline |
| Target entity construction, classifications and relationship meaning | Project configuration and explicit target mapping definitions |
| Vocabulary URI lookup and reconciliation | Existing mapping/reconciliation facilities where supported |
| Resolve publication identity from approved stable identifiers | Target identity policy |
| Assemble arrays, embedded structures, references and JSON-LD context | Linked Art exporter |
| Check document structure and cross-record consistency | Target-specific validation |
| Serve records and manage publication lifecycle | Separate publication service |

The exporter consumes already mapped target results. It must not inspect SEAD tables independently, and it must not decide undocumented semantic mappings. Any target mapping definition needed beyond existing configuration must be small, explicit and reviewed as part of the feasibility decision.

Use a registered output dispatcher as the proposed integration point. It consumes the completed `TableStore` from the existing Store step. Keep serialization and validation separate from file writing, and treat the input tables as read-only. Do not add a parallel generic output framework, and do not require database or SIMS ingestion settings for this file-only operation.

Verify caller support before choosing how the prototype is invoked. Registering a dispatcher does not prove that existing API or UI format selectors accept a new mode. A dedicated graph UI is outside scope.

### Preserve Core identity and apply a publication URI policy

Keep Core `system_id` values and foreign-key resolution unchanged. Publication URIs are separate output values: they do not replace local link IDs, and they do not redefine `public_id`. In short, internal links stay as they are, and public identifiers are added on top.

Reuse approved stable SEAD identities where they exist. Respect the existing authority/SIMS responsibility for the identities it manages; the exporter must not become a second identity authority. For untracked entities or derived supporting structures, agree on a deterministic identity rule that suits their publication role. Supporting structures do not all need to become independently published records.

Repeated exports of the same entities must keep the same URIs, even if source rows are reordered or local `system_id` allocation changes. Reject identity collisions and ambiguous mappings. An unresolved institutional identity policy blocks production use, even if test fixtures can use illustrative URIs.

### Agree on Linked Art semantics before generalizing

Review the intended output for the prototype with SEAD domain experts. Keep these separate: the physical sample, the sampling or analytical activity, the measured value, the classification, and the information describing the result.

Linked Art provides measurement-context patterns using `Dimension` and `AttributeAssignment` [4]. Whether they fit a specific SEAD analysis must be decided explicitly. Do not assume that all numerical results are dimensions, or that every biological sample belongs in an artwork-oriented object class.

Record unsupported concepts and any proposed extensions. Linked Art's cultural heritage focus does not by itself cover taxonomy, analytical methods or scientific uncertainty [1]. A valid broader CIDOC CRM representation must not be reported as conforming to a standard, unextended Linked Art profile unless that has been checked.

### Validate before making an export available

Validate against the agreed Linked Art version and target mapping. The exporter is responsible for the required context, property cardinality (how many values a property may hold), literal types, omission of absent values, and the difference between embedded structures and references.

Report errors with the source entity or key and the affected target property where available. Check local reference identities and types, URI uniqueness and required vocabulary mappings. External vocabulary references are allowed, and must be distinguished from missing records that the export was expected to contain.

A failed export must not be reported as successful, and it must not leave a partial result presented as complete. The prototype produces files for inspection; it does not publish them to a public service.

## Alternatives Considered

| Alternative | Assessment |
|---|---|
| Dedicated SEAD-to-Linked Art exporter outside Shape Shifter | Lowest coupling. The preferred fallback if the experiment needs substantial custom transformations or Core changes. |
| Shape Shifter prepares tables for a separate Linked Art assembly tool | A useful narrower role if transformation reuse is strong but export integration turns out awkward. |
| General relational-to-RDF mapping support in Shape Shifter | Broader than this change request justifies; deferred. |
| Intermediate Linked Art-oriented database | Adds schema management and persistence with no demonstrated prototype need; deferred. |

## Risks and Tradeoffs

- **Semantic mismatch:** Mechanically correct output can still misrepresent scientific meaning. Review the expected model before treating schema validation as success.
- **Hidden transformation logic:** A large exporter could end up duplicating the transformation engine. Keep source interpretation in mappings, and assess adapter complexity explicitly.
- **Identity drift:** URIs based on row order or local IDs break links between exports. Validate that identities stay stable when input is reordered.
- **Scope expansion:** Full SEAD coverage and publishing operations could bury the fit assessment. Limit the prototype and record additional requirements separately.
- **Scale is still unproven:** A small prototype shows correctness and architectural fit, not production memory use or throughput. Report this limitation in the outcome.

## Testing and Validation

Use a reviewed fixture with one site, one sample and one analysis containing multiple results, units, method and analyst attribution where present. Include shared references, and include one optional value that is absent. Agree on the expected Linked Art documents before evaluating the transformation.

Validate the emitted JSON-LD against the applicable Linked Art schemas and the agreed semantic checks. Compare source and target result counts, values, units and relationships. Repeat with reordered input and changed local IDs to verify that publication identity is stable. Exercise missing required mappings, unresolved local references and identity collisions to check failure reporting.

Run the relevant existing regression checks for any extension points changed during implementation. Record the mappings used, adapter responsibilities, required Core changes and remaining publication requirements in a concise feasibility result. This document does not claim that those tests have already run.

## Acceptance Criteria

- **P-AC-1:** The selected SEAD data has a reviewed target mapping, a named Linked Art version, expected documents, and explicit exclusions or extensions.
- **P-AC-2:** The prototype builds the agreed target entities and relationships as transformation results that can be inspected. Source interpretation is documented in mappings rather than hidden in serialization code.
- **P-AC-3:** The exported documents pass the agreed structural and semantic checks. Result counts, values, units and relationships match the reviewed fixture, without duplication caused by joins.
- **P-AC-4:** Publication URIs and references stay stable when source rows are reordered or local IDs change. Duplicate identities are rejected. Core identity and pipeline contracts are preserved.
- **P-AC-5:** Missing required mappings, invalid values and unresolved required local references produce errors that name the problem. Failed output is not presented as complete.
- **P-AC-6:** Existing transformation and output workflows keep their behavior, shown by the relevant regression checks.
- **P-AC-7:** A written fit assessment names reused capabilities, adapter code and any required Core changes, and recommends one of three outcomes: integrate the adapter, limit Shape Shifter to preparation, or use an independent exporter. Production support is not inferred from prototype success.

## Planning Handoff

**Established constraints:** Keep Shape Shifter in its relational transformation role, with an unchanged Core processing order and local identity contract. Keep semantic mapping explicit. Do not add public hosting, identity authority behavior or general ontology processing.

**Proposed implementation direction, subject to review:** Tabular target entities, followed by a Linked Art exporter that uses the existing dispatcher contract. Keep relational conformance and Linked Art document validation separate. A phase plan may be prepared after the proposal is approved; this proposal does not define delivery phases or tasks.

**Expected validation outcomes:** A reviewed semantic mapping, conforming output, preserved source meaning, stable publication identity, useful failure reports, and a clear assessment against P-AC-1 through P-AC-7.

**Questions to resolve:** Confirm caller integration and adapter-profile configuration before an implementation task plan. Settle the analysis fixture and mapping before building the exporter. Define identity rules before identity validation. Resolve production identity ownership, scientific extensions and scale requirements before any production-support decision.

## Open Questions

1. Which SEAD analysis makes a representative first example without requiring broad scientific-model coverage?
2. Can existing transformations build the required entities and relationships without changing Core behavior?
3. Where should the adapter profile be configured, and which existing caller should invoke the prototype dispatcher?
4. Which stable SEAD identifiers are available, and how should derived supporting entities be identified?
5. Does the selected scientific data fit standard Linked Art patterns, need agreed extensions, or need links to a richer external representation?

## Final Recommendation

Approve a small, narrowly scoped feasibility prototype for a Linked Art target exporter. Adopt it only if the semantic mapping stays explicit and most transformation work fits existing Shape Shifter configuration. Otherwise, keep Shape Shifter for data preparation or use a separate exporter, and record the reasons against the acceptance criteria.

## References

1. [Linked Art Data Model](https://linked.art/model/): model purpose, CIDOC CRM basis and scope limitations.
2. [JSON-LD Serialization](https://linked.art/api/1.0/json-ld/): context and serialization requirements.
3. [Reference Structure](https://linked.art/api/1.0/shared/reference/): references between published resources.
4. [Objects: Physical Characteristics](https://linked.art/model/object/physical/): dimensions and measurement context.

Repository placement: `docs/proposals/LINKED_ART_EXPORT/LINKED_ART_EXPORT.md`. Its row in the proposals index at `docs/proposals/README.md` lists this change request under Open Proposals. This drafting work did not modify the remote branch.
