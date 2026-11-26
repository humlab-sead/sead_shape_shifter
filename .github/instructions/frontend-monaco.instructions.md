---
description: "Use when changing the Monaco YAML or SQL editors, YAML schemas, completions or editor validation in the Vue frontend."
applyTo: "frontend/src/monaco.ts,frontend/src/components/common/YamlEditor.vue,frontend/src/components/common/MonacoTextEditor.vue,frontend/src/components/common/SqlEditor.vue,frontend/src/components/query/QueryEditor.vue,frontend/src/composables/useMonacoYamlIntelligence.ts,frontend/src/utils/projectYaml*.ts,frontend/src/schemas/**"
---
# Monaco Editors

- Keep Monaco; do not replace it.
- Workers are bundled with the application. `configureMonacoWorkers()` (`src/monaco.ts`) is called once from `main.ts`. Do not load workers from a CDN.
- Use `components/common/YamlEditor.vue` for YAML instead of creating another Monaco YAML editor.

## YAML Schemas

- `setupYamlIntelligence()` configures `monaco-yaml` only once for the whole application. It therefore registers the schemas for all modes in one call: `project`, `entity`, `target-model` and `reconciliation`.
- A schema applies by model path. The path must have the form `inmemory://shapeshifter/<mode>-<id>.yaml`.
- A new mode needs a schema entry in `useMonacoYamlIntelligence.ts` and the mode added to the types there and in the `YamlEditor.vue` props.
- `monaco-yaml` validation and hover are turned off on purpose (hover caused errors). Do not turn them on without testing in a browser.
- The JSON files in `src/schemas/` are generated from backend Pydantic models. Do not edit them: change the model, then run `make generate-schemas`. `make check-schemas` reports differences. Schemas drive editor help only; the backend does the validation.

## Validation and Completions

- `YamlEditor.vue` reports YAML syntax errors from `js-yaml` below the editor.
- When `validationContext` is set, `validateProjectYaml()` adds editor markers under the owner `yaml-custom`.
- `registerProjectCompletions()` registers a completion provider for the YAML language, not for one editor, and nothing disposes it. `YamlEditor.vue` calls it when each editor mounts. Dispose any new provider you add.

## Tests

- Monaco does not run in jsdom. In component tests, replace `YamlEditor` or `MonacoTextEditor` with a stub (see `views/__tests__/ProjectDetailView.test.ts`).
- To test schema setup, mock `monaco-yaml` and call `vi.resetModules()` between tests, because the configured flag is stored in the module (see `composables/__tests__/useMonacoYamlIntelligence.test.ts`).
