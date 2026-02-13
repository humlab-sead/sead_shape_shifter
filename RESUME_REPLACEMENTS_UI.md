# Resume Notes — Replacements UI (Entity Editor)

Date: 2026-02-12  
Branch: `improve-replacements`

## Goal
Add a **Replacements** tab to the entity editor (Vue/Vuetify) that edits `entity.replacements` and round-trips cleanly with the YAML editor and live preview payload.

Backend already supports:
- Legacy per-column forms: mapping object, and scalar/list blank-out + forward-fill
- Advanced per-column form: ordered list of rule dicts

## What’s implemented
### Frontend UI
- New **Replacements** tab in the entity form dialog.
- New editor component that edits per-column ordered rules.

Supported in the UI rule dropdown:
- `equals`, `contains`, `startswith`, `endswith`
- `regex`
- `in`
- `blank_out` (+ fill policy)
- `map` (key/value pairs)

Rule serialization produced by the UI:
- Match rules: `{ match: 'equals'|'not_equals'|..., from: <string|list>, to: <string>, flags?: ['ignorecase'], normalize?: [...], coerce?: 'string'|'int'|'float' }`
- Blank out: `{ blank_out: [...], fill: 'forward'|'backward'|'none'|{ constant: <string> }, normalize?: [...], coerce?: ... }`
- Map: `{ map: { <from>: <to>, ... }, normalize?: [...], coerce?: ... }`

Legacy column specs (mapping object, scalar/list blank-out) are **not** edited directly; if a legacy spec exists and you start editing rules, the UI converts that column to the ordered rule-list format.

### YAML + preview/save plumbing
- `buildEntityConfigFromFormData()` includes `replacements` in the payload, so both **save** and **live preview** see unsaved edits.
- `yamlToFormData()` pulls `replacements:` from YAML into the form state.

### YAML schema validation
- Updated entity JSON schema to accept:
  - legacy mapping
  - legacy blank-out scalar/list
  - advanced ordered rule list with common fields (`match/from/to/normalize/flags/coerce/blank_out/map`)

## Files changed
- frontend/src/components/entities/EntityFormDialog.vue
  - Adds the `Replacements` tab and window item
  - Adds `advanced.replacements` to form state
  - Includes `entityData.replacements` in config build
  - Parses `data.replacements` from YAML

- frontend/src/components/entities/ReplacementsEditor.vue
  - New component implementing the minimal replacements editor

- frontend/src/schemas/entitySchema.json
  - Expands `replacements` schema to match backend-supported formats

- frontend/src/components.d.ts
  - Auto-updated global components typing (generated)

## How to validate locally
Typecheck currently fails due to unrelated files under `deprecated/` and some frontend tests.

Useful commands:
- Build (skip typecheck): `pnpm -C frontend build:skip-check`
- Full build (includes vue-tsc): `pnpm -C frontend build` (currently fails due to unrelated TS issues)

## Known limitations / follow-ups
- The editor does not yet provide UX for:
  - `regex_sub` rule (exists in backend)
  - `report_replaced`, `report_unmatched`, `report_top` diagnostics toggles
- For `blank_out` fill `constant`, UI stores the constant as a string; backend will accept it but it may be desirable to support numeric/null types.
- Legacy formats are preserved unless edited; there is no “view-only” rendering of legacy mapping/blank-out specs.
- `frontend/src/components.d.ts` is generated; confirm the repo’s expected workflow (commit vs regenerate in CI).

## Quick start to resume
1. `git switch improve-replacements`
2. `pnpm -C frontend build:skip-check`
3. Run the frontend and open an entity editor:
   - `pnpm -C frontend dev`
4. In the entity dialog, open **Replacements** tab and verify:
   - Add rules; switch to YAML tab; ensure `replacements:` appears
   - Toggle back to form view; edits still visible
   - Preview uses the modified config (live preview refresh)

## Suggested next increments (optional)
- Add `regex_sub` support (pattern + replacement) to UI and schema.
- Add diagnostics toggles to rule cards (`report_replaced`, `report_unmatched`, `report_top`).
- Add a small “import legacy mapping → rule list” helper for smoother migrations.
