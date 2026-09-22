# Release Cycle Evidence And Locking

## Status

- Proposed process change
- Scope: how a release is defined, verified, evidenced, stored, and compared across the SEAD application landscape
- Goal: make the release cycle explicit and motivated, and make verification evidence automatic, bound to the artifact it describes, and cheap to reproduce

## Summary

Recommend that every deployment change be tied to an explicit **release unit** — a frozen source commit, an immutable image identity, a manifest revision, and a configuration revision. Verification runs produce a **locked run record**: one self-describing directory that names the release unit, lists every check with its result, and carries a checksum over its own contents. A **delta** step compares two run records so re-verification after a rebuild reports only what actually changed.

The motivation is a rule already accepted in this repository: a result recorded for one image digest carries no weight for another. That rule is correct, but it makes results expire on every rebuild, and today nothing freezes the artifact, nothing binds evidence to it, and collecting evidence is manual. The result is that the same check families have been run three times against three images, and part of the evidence exists only as prose.

## Problem

**Results expire faster than they are produced.** The centralized-authorization cutover recorded deployment verification against `95c3d017` on 2026-09-15, against the same baseline on 2026-09-18, and against `dbff5ab9` on 2026-09-22. Each pass covered substantially the same controls. Because a result belongs to one image, every rebuild discards the previous pass, and no step ever declares an artifact frozen.

**Evidence collection is manual, and partly narrative.** `container/scripts/verify/run_deployment_verification.sh` captures firewall, container configuration, PostgreSQL grants, log, credential, and endpoint-containment checks into a timestamped directory. It does not capture the authorization evidence set — resource and grant inventories, audit events, the manifest checksum, integrity, and reconciliation — and it does not capture the image digest. `container/scripts/verify/verify_authenticated_access.sh` has no way to write its output to a file, so its transcript must be copied by hand. The Phase 4 record consequently states four access outcomes as a prose table, and the supporting raw transcript had to be recovered from a session log after the fact.

**Nothing binds evidence to the artifact.** No run records the image digest it belongs to, no checksum protects the captured files, and nothing distinguishes an edited result from a captured one.

**The cycle is implicit.** `docs/OPERATIONS.md` documents the operator steps and names the fields to record. `container/DEPLOYMENT.md` documents build, service, and health operations. `container/scripts/verify/README.md` lists the checks and asks the operator to record each result with the date and host. No document states when a verification run is required, what makes a candidate a release, the check set for a given release, who signs off, how long evidence is retained, or what the term "release disposition" — used across several plans — actually means.

**The cost is already visible.** The most recent phase closed with one acceptance criterion resting on a re-run that could not be performed, an accepted risk, and a transcript recovered from a chat log. That is the failure mode of a correct process that is too expensive to execute.

**The same problem applies to every SEAD application.** The reverse proxy on `humlabsead` already serves several sites — including `browser.sead.se`, `super.sead.se`, and `staging.sead.se` — and `container/DEPLOYMENT.md` already describes multiple Shape Shifter environments such as `test-shape-shifter.sead.se:8012` and `prod-shape-shifter.sead.se:8013`. Each has its own exposure, secrets, proxy, and grant concerns, and each will need the same evidence discipline.

## Scope

- Define a release unit and the identity fields that make it immutable.
- Define a locked run record that binds checks and evidence to one release unit.
- Define delta reporting between two run records.
- Define one documented release cycle: entry conditions, required checks, sign-off, retention, and disposition vocabulary.
- State, for each check, the risk it retires and the evidence that closes it.
- Keep the run record application-agnostic so other SEAD applications and other Shape Shifter environments can adopt it.

## Non-Goals

- Implementing the capture, locking, or delta tooling.
- Selecting a container registry or a CI/CD platform.
- Changing authorization policy, route classification, or the deployment layout.
- Repointing production DNS or the reverse proxy.
- Replacing proposals, phase plans, task plans, and handoffs; the run record is evidence, not planning.

## Current Behavior

Verified in this repository:

- `container/scripts/verify/run_deployment_verification.sh` writes `summary.txt`, per-check `<name>.log` files, and a copy of its options file into a timestamped directory under `<DATA_DIR>/deployment-verification/`. It searches for no digest, no authorization inventory, no manifest checksum, and no checksums over its own output.
- `container/scripts/verify/verify_authenticated_access.sh` accepts `--base-url`, `--principal-a`, `--principal-b`, `--project-a`, `--project-b`, and `-h`. It has no evidence-directory option; only `container/scripts/verify/rollback_exercise.sh` accepts `--evidence-dir`.
- `container/scripts/verify/verify_container_config.sh` inspects the running container's ports, mounts, environment variable names, and image labels and history. It does not read `RepoDigests`.
- `docs/OPERATIONS.md` section *Release, Verification, And Rollback* documents selecting a ref in `~/config/deployment.env`, `make build`, `make restart`, and the fields to record, plus firewall and container-configuration verification and the rollback steps.
- Authorization store operations are reached through `container/scripts/authorization.sh` (`backup`, `restore`, `import-manifest`, `export-manifest`, `list-resources`, `list-grants`, `list-audit-events`, `integrity-check`, `reconcile`).

Registry availability: no image registry is in use. GitHub Container Registry use is paused pending a billing review, so images are built locally. A locally built image can still carry a `RepoDigests` entry computed by the local store — the Shape Shifter deployment reports `localhost/shape-shifter@sha256:7ff51b2b…` — but the `localhost/` repository prefix shows nothing was pushed, so the digest has no external provenance. The identity is decided in *Proposed Design*.

## Proposed Design

### 1. The release unit

A release unit is the thing a verification run describes. It must be immutable and it must be identified by values that cannot change underneath a recorded result:

- source commit
- image identity: the OCI `revision` label, the image ID, and the manifest digest the local store computes when no registry digest is available
- authorization manifest revision and checksum
- configuration revision (`GIT_REF`, `IMAGE_NAME`, and the configuration file identity)
- the deployment target: host, deployment user, container name, published port, and proxy hostname

A run belongs to exactly one release unit. Nothing in a run may be reused for a different one.

**Image identity decision.** No image registry is available for this work: GitHub Container Registry use is paused while a billing change is reviewed, and a locally hosted registry with CI/CD builds is under consideration. The release unit therefore records the OCI `revision` label as the identity that travels across hosts, together with the image ID and the manifest digest the local store computes. The `localhost/` repository prefix shows the image was never pushed, so the digest is local evidence rather than something a registry vouches for, and a manifest digest computed on another host is not guaranteed to match. Every result that cites the digest says it was computed locally.

### 2. Automatic evidence capture

One entry point runs the check set for a release unit and writes a structured run record rather than requiring an operator to collect evidence piece by piece:

- `run.json` — release unit identity, check list, per-check result, start and end timestamps, actor, and host
- one log per check, exactly as the run produced it
- `checksums.txt` — a checksum over every other artifact in the run
- `summary.txt` — the human-readable roll-up

The check set is data, not code: adding a check to a release type must not require editing the capture logic. Checks that cannot run are recorded as `not run` with a reason. They must never be recorded as passed.

### 3. Result locking

Locking means a captured run is not editable:

- the run directory is created once and is immutable afterwards
- `checksums.txt` covers every artifact, so an altered file is detectable
- a correction produces a **new** run that explicitly supersedes the earlier one, with the reason stated
- the run is retrievable by release unit identity, so "what did we verify about this image" has one answer

### 4. Deltas between runs

A compare step reads two run records and reports:

- the release-unit differences between them
- checks added, removed, or whose result changed
- pass-to-fail and fail-to-pass transitions
- checks that were not run in either

This is what makes a rebuild cheap: after re-verification, the delta shows which results actually invalidated rather than requiring a full pass to be re-read.

### 5. A documented cycle

One document — a `docs/RELEASING.md`, or a section in `docs/OPERATIONS.md` if that is preferred — states:

- what constitutes a release for this application
- when a run is required and when a previous run may be cited
- the check set per release type
- who signs off and who owns an exception
- evidence naming, retention, and location
- the disposition vocabulary: `passed`, `approved exception`, `blocked`, and what each requires

### 6. Motivated criteria

Each check states the risk it retires and the evidence that closes it. A criterion without a stated risk is either unjustified or mis-stated, and both are failures of the process rather than of the check.

### 7. Ecosystem reuse

The run record envelope — release unit, checks, results, checksums, summary — is application-agnostic. A SEAD application supplies its own release-unit fields and check set; the envelope, the locking rule, and the delta reporting stay the same. Adoption order should follow exposure: the shared reverse proxy and its other sites carry the same class of risk as the deployment examined here.

## Alternatives Considered

- **Keep the manual process.** Rejected: its cost is measurable and its evidence is not bound to an artifact.
- **Record evidence only in proposal and handoff documents.** Rejected: those documents are narrative, are not machine-comparable, and do not carry digests or checksums. They should cite a run record, not be one.
- **Identify releases by image tag.** Rejected: tags are mutable, so a recorded result could silently describe a different artifact.
- **Build a full CI/CD pipeline first.** Deferred: the release unit and run record are prerequisites for any pipeline, and they are useful without one. A pipeline can produce the same record later.
- **Lock only by convention.** Rejected: without checksums, an edited artifact is indistinguishable from a captured one.

## Risks And Tradeoffs

- **Freezing a release delays urgent fixes.** Mitigate with a documented exception path that changes the release unit openly instead of verifying a moving target.
- **Locking can obstruct a legitimate correction.** Mitigate by making supersession explicit: a new run replaces a wrong one, and the wrong one stays visible.
- **Automation can create false confidence.** Mitigate by treating a missing check as `not run`, never as `passed`, and by making every check fail loudly.
- **The manifest digest has no external provenance, and that is accepted for now.** With no registry available, the digest is computed by the local store and the image was never pushed, so nothing outside the host vouches for it and an equivalent build on another host may produce a different value. Record the source revision alongside it as the cross-host identity, and state where the digest came from. Standing up a local registry with CI/CD builds would add provenance and make the digest comparable across hosts.
- **Scope can creep across the ecosystem.** Mitigate by piloting on one application and keeping the envelope generic until a second application adopts it.
- **Evidence volume grows with every run.** Mitigate with retention rules that keep locked runs and checksum files longer than bulky logs.

## Testing And Validation

- Capture a run for a known release unit and confirm `run.json`, the per-check logs, `checksums.txt`, and `summary.txt` are complete and internally consistent.
- Alter one artifact and confirm the checksum check detects it.
- Compare two runs of the same release unit and confirm the delta reports no change.
- Compare runs of two different release units and confirm the delta reports only the checks whose results actually changed.
- Confirm a check that cannot run is recorded as `not run` with a reason, and that an overall run containing a `not run` check cannot report `passed` for the criterion that check covers.
- Confirm no credential value appears in any captured artifact.

## Acceptance Criteria

- `P-AC-1` A release unit is defined with immutable identity fields, and a verification result is unusable for any other release unit.
- `P-AC-2` One command produces a complete run record for a release unit without manual transcription of any check output.
- `P-AC-3` Every artifact in a run record is covered by a checksum, and a modified artifact is detected.
- `P-AC-4` A run record cannot be edited after capture; a correction creates a new run that names the run it supersedes.
- `P-AC-5` A delta between two run records reports release-unit differences, added and removed checks, changed results, and pass/fail transitions.
- `P-AC-6` A check that cannot run is recorded as `not run` with a reason, and never counted as passed.
- `P-AC-7` The release cycle is documented in one place: entry conditions, required checks, sign-off, retention, disposition vocabulary, and the risk each check retires.
- `P-AC-8` No captured artifact contains a credential value.
- `P-AC-9` The run record envelope is application-agnostic, and a second SEAD application or deployment environment can supply its own check set without changing the envelope, the locking rule, or delta reporting.

## Planning Handoff

Confirmed decisions:

- The release unit is the boundary for verification results. This follows from the accepted rule that a result for one image carries no weight for another.
- Identity is a frozen commit plus an immutable image identity, a manifest revision and checksum, a configuration revision, and the deployment target.
- No image registry is available, so the identity is the OCI `revision` label plus the image ID and the locally computed manifest digest, and each result that cites the digest states that it was computed locally and is not registry-served.
- Locking is additive: corrections supersede, they never overwrite.
- A missing check is `not run`, never `passed`.
- The run record is application-agnostic; check sets are per application.

Constraints and behavior to preserve:

- Do not change authorization policy, route classification, or deployment layout.
- Do not require credentials to be recorded or passed on a command line.
- Keep `container/scripts/verify/` scripts read-only except for the deliberate rollback exercise.
- Keep existing handoffs valid; a run record supplements the documents that cite it.

Expected validation outcomes: a captured run is complete and checksum-protected; a tampered artifact is detected; a same-unit delta is empty; a cross-unit delta is accurate; a `not run` check cannot be reported as passed.

Open questions, with the phase that must resolve each:

- Whether to stand up a locally hosted registry with CI/CD builds, and whether that is the successor to GitHub Container Registry or a temporary measure. Resolve before the evidence format is declared stable.
- Which document owns the cycle: a new `docs/RELEASING.md`, or a section in `docs/OPERATIONS.md`? Resolve in the same phase as the documentation work.
- Who signs off a release and who may approve an exception? Resolve before the cycle is declared in force.
- Which application pilots the envelope, and which adopts second? Resolve before the ecosystem adoption phase.
- How long are locked runs and bulky logs retained? Resolve before adoption widens.

## Recommended Delivery Order

1. Fix the release-unit fields around the source revision, the image ID, and the locally computed manifest digest, and state the digest's provenance in the format itself.
2. Implement capture and the run record envelope, with checksums.
3. Implement locking and supersession.
4. Implement delta reporting.
5. Document the cycle and the motivated check set.
6. Adopt on a second SEAD application or deployment environment.

## Open Questions

- Whether the release cycle is enforced by review convention or by tooling gates.
- Whether the check set is defined in one shared file per application or assembled per release type.
- Whether an existing evidence directory layout is migrated or left in place and superseded going forward.

## Final Recommendation

Adopt the release unit, the locked run record, and delta reporting, then document the cycle with a stated risk for every check. Start with one application, keep the envelope generic, and record the source revision plus the image ID and the locally computed manifest digest as the identity while no registry is available, stating the digest's provenance in every result that cites it.
