---
description: "Use when editing Vue 3, Pinia, or frontend API code in frontend/src. Covers script setup, stores, composables, and TypeScript conventions."
applyTo: "frontend/src/**/*.vue,frontend/src/**/*.ts"
---
# Frontend Conventions

- Use Vue 3 Composition API with `<script setup lang=\"ts\">`.
- Prefer composables over mixins for shared logic.
- Use typed `defineProps<T>()` and `defineEmits<T>()`.
- Use `storeToRefs()` when destructuring Pinia store state.
- Keep API access in `frontend/src/api/` and call backend endpoints under `/api/v1`.
- Handle `null` and `undefined` explicitly; keep strict null checks intact.
- Prefer `type` for unions and `interface` for object-shaped API contracts.
- Preserve the existing frontend patterns unless the task explicitly asks for a larger redesign.
