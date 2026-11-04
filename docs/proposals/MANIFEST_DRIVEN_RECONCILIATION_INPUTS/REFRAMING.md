So let's take a step back, and let's change the prerequisites:
- nothing is written in stone
- we can change reqs in #attachment:MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md if need be
- Shape Shifter is the primary, and currently only, consumer of SEAD Authority Service
- We can change SEAD Authority Service to be a better fit to Shape Shifter's needs
- On the other hand, it would be awsome if the use of SEAD Authority Service would be as configurable as possible, using the OpenRefine manifest to dynamically understand what types and properties are avaliable. This would almost mute #attachment:MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md
- The foremost important thing is to get an as reliable and useful reconciliation feature in Shape Shifter
- The use of SEAD Authority Service from e.g. OpenRefine is secondary.
- The `taxon`isn't implemented in SEAD Authority Service so we can't use `taxon` in #attachment:MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md
- We can use `feature_type` instead (a simple classifier)

How would you change #attachment:MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md given this? It feels like "adding a new entity type" should be more "how to consume openrefine manifest when creating a reconciliation specification" shouldn't it?



## Yes — you've identified the right reframe

The old document asked *"which two types do we add?"* The real question is *"why is adding a type a code change at all?"* I rewrote it around that, and your constraints made it much smaller.

### Facts I verified first

| Type           | Live result                                                             | Serves             |
|----------------|-------------------------------------------------------------------------|--------------------|
| `feature_type` | **works** — `Trench`→25 (100%), `Post hole`→26 (100%), `Roof`→29 (100%) | no properties      |
| `location`     | **works** — `Sweden`→205, `Uppsala`→4233                                | `place_name`       |
| `taxon`        | `{"result":[]}` for `Acer platanoides`                                  | no function exists |

The grants fix landed, so `site`/`location` no longer 500. And `abundance` — which the editor's fallback list offers — isn't in the manifest's 13 types at all. That fallback is provably stale.

### The new central decision

**The manifest is the reconciliation input contract.** Types from `defaultTypes`, properties from `extend.property_settings` filtered by type. Adding an entity type becomes: pick an advertised type → map served properties → declare the local business key → verify one real match. No Shape Shifter edit.

Because Shape Shifter is the only consumer, the division is now explicit: when the manifest can't express something, **change Authority Service**, not the client. That got its own section, with the constraint that manifest changes stay additive so the OpenRefine contract keeps working for anyone else.

### Concrete changes from the old draft

| Was | Now |
| --- | --- |
| `taxa` + `location` | `feature_type` + `location` |
| "add dynamic property discovery" as one bullet | The whole point of the proposal |
| Type fallback kept | **Removed** — an unavailable manifest is an explicit empty state |
| Acceptance: "configurable through existing behaviour" | `P-AC-6`: adding a further advertised type requires **no code change**, demonstrated by configuring one |
| Guide: "add an entity type" | Guide: "consume the manifest when creating a specification" |

### Three things the live checks turned up that change the plan

**`feature_type` serves no properties.** That's a genuine strength — it proves a label-only classifier works — but it also means it can't validate property mapping. So `site` stays the property-mapping regression reference, and `location` covers the one-property case.

**Both pilot entities declare `keys: []`.** `mapping_service._default_local_key` raises `Entity '...' has no entity.keys configuration for mapping operations`. Declaring a business key is real work, not a footnote, and for a classifier the natural key is the label or a code column.

**A manifest server without a database looks healthy.** The manifest never touches the schema, which is exactly how the grant gap hid. That's now a Risks bullet: only a real match request proves a type works.

### Also updated

- `docs/proposals/README.md` index row now describes the manifest-driven decision
- The MVP's "remaining follow-up" link no longer says "extend beyond `site`" but "consume the manifest"
- 8 acceptance criteria (`P-AC-1`–`P-AC-8`); `P-AC-1` keeps the site gate as satisfied-and-unregressed
- `check_doc_links.sh` passes; the two `VALUE_REFERENCE_COLUMN_*` README breaks are pre-existing at `HEAD` (those folders moved to `done/` earlier)

### Two things to decide

**Housekeeping completed.** The proposal folder and file are now named `MANIFEST_DRIVEN_RECONCILIATION_INPUTS`, and the stale review file has been removed.

One housekeeping note: while working I found two byte-identical stale copies at the old `docs/proposals/{RECONCILIATION_MVP,FOREIGN_KEY_LINK_TROUBLESHOOTER}/` paths — your editor apparently re-saved buffers after my `git mv`. I removed them (verified identical to the `done/` copies first).

Made changes.