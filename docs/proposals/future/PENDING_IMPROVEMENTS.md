# Pending Improvements

## Purpose

Track non-blocking follow-up work for completed proposals that have already shipped their intended feature set.

## First-Class Merged Parent Entities

Completed proposal: [../done/FIRST_CLASS_MERGED_PARENT_ENTITIES.md](../done/FIRST_CLASS_MERGED_PARENT_ENTITIES.md)

The merged-entity feature is implemented and documented. The items below are follow-up polish, extra coverage, or optional ergonomics work and are not blockers for treating the proposal as done.

### UI and UX follow-up

- Restore or redesign dependency-graph selection highlighting for merged branch sources.
- Add an optional read-only merged branch summary in the entity detail view.
- Consider an expanded dependency-graph view showing branch structure and discriminator/FK derivation.
- Add screenshots or a short walkthrough for the merged branch editor.

### Testing follow-up

- Add backend preview-service tests for merged branch toggle behavior.
- Add dependency-graph visualization tests beyond current rendering coverage.
- Add frontend validation display tests for per-branch merged errors.
- Add end-to-end UI coverage for merged entity creation, preview, and validation.
- Add a real Arbodat `analysis_entity` scenario test.
- Add preview, validation, and normalization consistency coverage.
- Add cache invalidation coverage when branch sources change.
- Add circular-dependency coverage specific to merged entities.

### Optional product enhancements

- Support optional `branch_discriminator_column` override.
- Add explicit warnings for column type upcasting across branches, with dedicated test coverage.
- Consider enhanced topological-sort display for merged dependencies.
- Add append-to-merged migration guidance or a worked conversion example if adoption makes that worthwhile.

### Operational follow-up

- Semantic-release tagging happens on merge to `main`.
- Release-note publication remains a post-merge operational step, not a proposal blocker.
