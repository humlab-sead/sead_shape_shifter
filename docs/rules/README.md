# Shape Shifter Semantic Rules

This directory contains machine-readable semantic validation rules for Shape Shifter project YAML files.

## Files

| File                 | Description                                                                           |
|----------------------|---------------------------------------------------------------------------------------|
| `semantic_rules.yml` | Initial rule catalog covering entity type contracts and cross-entity reference checks |

## Purpose

The generated JSON Schema (`frontend/src/schemas/entitySchema.json`) supports editor autocomplete and basic structural validation. It cannot express conditional or contextual rules such as:

- "an `xlsx` entity must define `options.filename`"
- "a `duckdb` entity must define both `query` and `depends_on`"
- "every entity referenced in `source` or `foreign_keys[].entity` must exist in `entities`"

The rule files in this directory capture those constraints in a stable, AI-readable format. AI coding agents load these rules via the `shapeshifter-configuration` skill to validate, explain, and repair project YAML.

## Rule format

Rules follow the format defined in `docs/ai/semantic-rules-agent.md`. Each rule has:

- `id` — stable identifier (`<area>.<context>.<rule_name>`)
- `title` — short description
- `severity` — `error`, `warning`, or `info`
- `category` — `conditional`, `structural`, `project_resource`, or `consistency`
- `applies_to` — YAML path pattern
- `when` — condition (discriminator match)
- `require` or `check` — what to validate
- `message` — diagnostic message
- `fix` — suggested repair
- `source` — code or documentation references

## Adding rules

1. Follow the format in `docs/ai/semantic-rules-agent.md`.
2. Use stable rule IDs. Do not reuse or rename existing IDs.
3. Add `confidence: medium` for rules inferred from examples rather than explicit code or schema.
4. Verify the file parses cleanly after editing:

```bash
python -c "import yaml; yaml.safe_load(open('docs/rules/semantic_rules.yml'))"
```
