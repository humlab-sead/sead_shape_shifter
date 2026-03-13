# AI Notice To Devs

Date: 2026-03-13

As this project grows, AI-assisted code work is affected less by raw file count and more by how much ambiguity, duplication, and noise exists in the workspace.

## What Degrades AI Performance

- Multiple competing implementations of the same behavior.
- Stale or conflicting documentation.
- Large dirty diffs and broad unrelated local changes.
- Generated files, coverage output, logs, and build artifacts mixed into normal search paths.
- Deprecated or archived code that looks authoritative.
- Weak or inconsistent naming across layers.
- Features whose behavior is spread across many unrelated files.

## What Helps Most

1. Keep architectural boundaries clear.
2. Exclude generated and deprecated noise from normal search paths.
3. Maintain concise, current architecture and workflow docs.
4. Use strong, consistent naming for entities, stores, services, endpoints, and config.
5. Keep feature logic locally coherent instead of scattering it across layers without clear ownership.
6. Keep commits and pull requests small and scoped.
7. Add focused regression tests for bug-prone workflows.
8. Preserve one source of truth for schemas, mappings, and config structure.
9. Clearly separate active code from archived, deprecated, or experimental code.
10. When asking for AI help, include the affected workflow, expected behavior, actual behavior, and likely files.

## Practical Guidance For This Repo

- Keep deprecated and archived material visibly separated from active implementation.
- Keep docs in `docs/` current and concise, especially architecture and development workflow guidance.
- Avoid duplicate implementations of frontend state handling, backend mapping logic, and config transformation rules.
- Prefer focused fixes with tests over broad mixed-purpose changes.
- When possible, isolate generated output, logs, coverage, and temporary files from normal workspace search.

## Summary

The biggest performance cost for AI in a large repository is not size alone. It is uncertainty. Reducing ambiguity, duplication, and search noise usually improves AI effectiveness more than simply reducing line count.