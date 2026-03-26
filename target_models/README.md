# Target Models

Standalone workspace for iterating on target model specifications and their validation.

This area is intentionally separate from `src/`, `backend/`, and `data/` while the format and validator are still evolving.

## Structure

- `specs/` — YAML target model specifications such as `sead_v2.yml`
- `src/target_model_spec/` — Python source for parsing and validating target model specs
- `tests/` — tests for the parser and validator
- `schemas/json/` — optional JSON Schema representation of the format

## Intended Workflow

1. Evolve the YAML format in `specs/`
2. Keep parser and validator code in `src/target_model_spec/` aligned with the format
3. Add tests for both happy-path and invalid specifications
4. Add or refine JSON Schema only if it proves useful for external tooling

## Notes

- This is a staging area for parallel iteration on the format and its implementation.
- Once the format stabilizes, pieces can be moved into the main application structure if needed.