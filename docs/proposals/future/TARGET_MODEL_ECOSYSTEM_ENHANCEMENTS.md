# Proposal: Target Model Ecosystem Enhancements

## Status

- Proposed future change
- Scope: target-model tooling, reference resolution, registry/distribution workflow
- Goal: separate speculative ecosystem work from the active conformance CR while keeping the options documented

## Summary

Keep the active conformance proposal focused on implemented and near-term validator work. Move speculative ecosystem features into a separate future proposal covering target-model diff tooling, remote references, and a curated registry.

## Problem

The current conformance proposal had started to accumulate two different kinds of work:

- concrete conformance and format changes that were being implemented in the current CR
- broader ecosystem ideas that depend on product decisions, operational constraints, or a future distribution model

That mix makes the active proposal harder to read and makes the remaining backlog look more implementation-ready than it really is.

## Scope

- target-model diff tooling for upgrade planning
- remote target-model references beyond local `@include:` files
- a curated target-model registry with short-name resolution

## Non-Goals

- changing the current local-file target-model workflow
- replacing the already implemented target-model documentation downloads
- implementing any of these features in the current conformance CR

## Current Behavior

Today, Shape Shifter supports project-local or repository-local target-model files resolved through the existing `@include:` workflow. This covers current use cases and avoids network, registry, and version-resolution concerns.

Target-model documentation downloads are already implemented and remain part of the active proposal as shipped functionality.

## Proposed Design

### Target Model Diff Tooling

When a target model version changes, provide a diff report showing which conformance checks, entities, or fields are new, changed, or removed.

**Approach:** Compare two `TargetModel` instances field-by-field and render a structured diff as Markdown or YAML.

### Remote Target Model References

Allow target models to be referenced by URL in addition to local `@include:` files.

```yaml
metadata:
  target_model: "https://registry.example.com/sead/v2.yml"
```

**Prerequisites:**

- SSRF prevention through an allowlist or controlled proxy
- caching with TTL so validation does not trigger network fetches on every run
- version pinning or equivalent safeguards so upstream changes do not silently alter validation behavior

**Recommendation:** Only implement this if a shared registry becomes a real operational need. Local file references cover current use cases.

### Curated Target Model Registry

A registry of community-contributed target models distributed with Shape Shifter or via a companion package.

**Candidate bundled models:**

- `sead_standard_model` — SEAD Clearinghouse v2
- a generic archaeological site model
- a museum specimen model

**Approach:** Store curated YAML files under a bundled resource path and resolve short names to those files before normal `@include:` resolution.

## Risks and Tradeoffs

- remote references add operational and security requirements that do not exist with local files
- a registry introduces versioning, support, and governance questions beyond pure code changes
- diff tooling is useful, but it only becomes valuable once target-model version churn is common enough to justify its maintenance cost

## Testing And Validation

- diff tooling: fixture models with expected structured diffs
- remote references: resolution, caching, pinning, and SSRF guard coverage
- registry: short-name resolution, invalid model names, and bundled-resource version coverage

## Acceptance Criteria

- each feature has a concrete product need and delivery owner before implementation starts
- no remote or registry feature ships without explicit security and caching rules
- the active conformance proposal remains free of speculative ecosystem scope

## Open Questions

- should remote references ever be allowed directly, or only through a local mirror/proxy?
- should a curated registry ship in the main repository or in a companion package?
- what level of semantic change should target-model diff tooling highlight by default?

## Final Recommendation

Treat these as undecided future enhancements, not as remaining work in the current conformance backlog. Revisit them only when a concrete operational or product need appears.