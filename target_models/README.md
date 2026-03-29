# Target Models

Standalone workspace for iterating on target model specifications and their validation.

This area is intentionally separate from `src/`, `backend/`, and `data/` while the format and validator are still evolving.

## Structure

- `examples/` — standalone Shape Shifter project fixtures for conformance iteration
- `specs/` — YAML target model specifications such as `sead_v2.yml`
- `src/target_model_spec/` — Python source for parsing and validating target model specs
- `scripts/` — standalone helper scripts such as the template generator proof of concept
- `tests/` — tests for the parser and validator
- `schemas/json/` — optional JSON Schema representation of the format

## Intended Workflow

1. Evolve the YAML format in `specs/`
2. Keep parser and validator code in `src/target_model_spec/` aligned with the format
3. Add standalone example projects in `examples/` for conformance experiments
4. Add standalone conformance checks against those examples before backend integration
5. Add tests for both happy-path and invalid specifications
6. Add or refine JSON Schema only if it proves useful for external tooling

## Template Generator Proof of Concept

The Milestone 2 proof of concept lives in:

- `src/target_model_spec/template_generator.py`
- `scripts/generate_project_template.py`

Example usage:

```bash
PYTHONPATH=target_models/src /home/roger/source/sead_shape_shifter/.venv/bin/python \
	target_models/scripts/generate_project_template.py \
	--spec target_models/specs/sead_v2.yml \
	--domain dating
```

This generates a non-runnable `shapeshifter.yml` starter scaffold to stdout. It is intended as an authoring aid, not a complete executable project configuration.

## Notes

- This is a staging area for parallel iteration on the format and its implementation.
- Once the format stabilizes, pieces can be moved into the main application structure if needed.