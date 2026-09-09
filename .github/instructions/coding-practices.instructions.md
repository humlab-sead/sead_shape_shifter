---
description: "General coding practices for all work: targeted changes, root-cause fixes, and verification before claiming completion."
applyTo: "**/*"
---
# General Coding Practices

- Start with the smallest targeted search or read required to locate the likely edit site.
- Prefer direct, repo-aware fixes over broad cleanup or speculative refactors.
- Keep changes narrow, understandable, and aligned with the existing code style.
- If a fix is uncertain, investigate the root cause before patching.
- Prefer targeted changes over broad incidental changes.
- Validate with the smallest relevant command or targeted test before claiming completion.
- Do not claim success without fresh verification output.
