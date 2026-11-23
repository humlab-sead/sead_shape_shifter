# KISS & YAGNI REVIEW of Search and Browse Target Records During Reconciliation

## Overall assessment

**Decision required.** The proposal addresses a real workflow problem, but commits to more infrastructure than the initial use case establishes. A smaller release could preserve explicit decisions and safe export while deferring session machinery and advanced browsing.

This reviews the locally modified `proposal`, not a PR diff. It is not part of the current branch’s PR.

## Findings

### F1 — High: Stop exports rather than support unverified exports during outages

`Proposal:143` retains the existing fallback that writes unverified links when Authority is unavailable. That creates verification-state and recovery work and permits invalid existing catalog entries to reach the sidecar.

**Simpler:** Block exports containing accepted candidates until verification succeeds. New-only exports could remain available. Require Authority availability when opening a new workspace rather than designing cold-start offline capability discovery.

This changes existing behavior: `an outage-export test` explicitly expects unverified export. Already-exported unverified links also need a separate policy. **Confidence: High.**

### F2 — High: Optimistic locking must cover existing writers

`Proposal:151` version-checks new row saves, but `whole-catalog replacement` can still overwrite them with stale JSON or YAML.

**Simpler:** Use a catalog content hash and conditional writes, following the existing `mapping-sidecar pattern`. Include legacy replacement and decision writers, or explicitly restrict them. A catalog-wide version causes occasional conflicts between unrelated edits, but avoids introducing per-row version storage. **Confidence: High.**

### F3 — Medium: Reconsider server-owned review snapshots

`Proposal:149` introduces tokens, server-side session storage, expiration, invalidation and source-revision providers before measuring whether they are necessary.

**Simpler alternative:** Keep individually chosen decisions as browser drafts and save them together. At save, resolve and validate source rows once, then conditionally update the catalog. Known source changes still need detection; unversioned external data remains point-in-time. This trades immediate durable saves for fewer normalizations and no server snapshot lifecycle. If per-row durability is essential, measure first before selecting a snapshot design. **Confidence: Medium.**

### F4 — Medium: Start with bounded complete lists

`Proposal:119` and `proposal:129` require typed filters, global sorting, exact counts and cursor management for every type, although actual sizes are unmeasured.

**Simpler:** Fetch a complete list under explicit row **and byte** limits; filter and sort it locally. Return an explicit “too large to browse” result rather than displaying a partial list as complete. Keep ranked Search available and add server paging only where measurements justify it. This intentionally relaxes universal Browse coverage. **Confidence: Medium.**

### F5 — Medium: Avoid two mandatory target-existence checks

`Proposal:123` requires a details lookup at acceptance, followed by candidate verification at export.

**Simpler:** Extend the existing verification protocol for classifiers and make successful verification mandatory at export. Treat saved selections as decisions, not proof of target existence. Return display fields with browse results and fetch additional details only when needed. This delays reporting a deleted target until export but removes a mandatory request and a separate acceptance contract. **Confidence: Medium.**

### F6 — Medium: Reduce first-release scope

`Proposal:7` makes all marked classifiers an all-or-nothing delivery requirement; the current registry contains `45 types`. One generic implementation is sensible, but every type still adds validation and rollout obligations.

**Simpler:** Validate representative types first, advertise only capabilities that work, and expand coverage as needed. Defer recent-query history and the derived application-state calculation; clearly label **Save decision** versus **Export** instead. **Confidence: Medium.**

## Remaining safeguards

The earlier `review` remains relevant, especially shared-source authorization and identifier-search semantics. Simpler persistence must not bypass either source authorization or business-key validation.

**Validation:** Static review only. Existing tests were located but not run; classifier sizes and performance were not measured. No GitHub review was posted.
