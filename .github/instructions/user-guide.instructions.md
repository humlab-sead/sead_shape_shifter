---
description: "Use for USER_GUIDE.md and related end-user documentation in sead_shape_shifter, including workflows, task-oriented guidance, and common user scenarios."
applyTo: "docs/USER_GUIDE.md"
---
# User Guide Documentation Instructions

## Purpose

Keep the guide focused on helping users complete Shape Shifter workflows. Optimize for workflow clarity, fast onboarding, and practical task completion.

Write for researchers, data managers, project editors, SEAD contributors, and technical users who are not necessarily developers. Do not assume users understand repository structure, internal architecture, or implementation details.

Prefer: "How do I complete a task?" over "How is it implemented internally?"

## Structure

When editing an existing document, preserve its structure unless reorganization is explicitly requested — apply the progressive principle *within* the existing sections rather than restructuring.

For new documents, organize progressively:

1. Short product orientation
2. Quick success workflow (early)
3. Common workflows
4. Advanced topics (YAML editing, CLI, dispatcher internals, target model details)
5. Troubleshooting and FAQ

Keep beginner workflows early. Move raw YAML editing, CLI usage, and implementation detail to advanced sections. The FAQ should clarify misunderstandings, not introduce core concepts for the first time.

## Writing rules

- Use task-oriented headings: "Create an Entity", "Run Validation", "Export Results".
- Explain each feature with: when to use it, why a user would use it, what outcome it produces.
- Introduce terminology only when the current workflow step requires it.
- Keep conceptual explanations short; prefer numbered workflows and concrete examples over abstract description.

## Content boundaries

Focus on: user workflows, UI behavior, task sequencing, validation, reconciliation, execution, common user decisions, and troubleshooting.

Do not include: architecture documentation, YAML schema reference, API reference, implementation walkthroughs, or operations content. Link to deeper technical documentation instead.

## Common failure modes

- Explaining implementation instead of user behavior
- Front-loading terminology or YAML before users understand workflows
- Inserting architecture explanations into task sections
- Mixing beginner and advanced workflows in the same section
- Describing entities abstractly without relating them to user goals

If a section does not help users complete a task, make a decision, or understand a workflow — shorten or remove it.

## Quality checks

Before finalizing edits, verify:

- A new user can find a successful workflow quickly
- The guide starts with practical orientation, not architecture
- Execute and Dispatch are clearly distinguished
- Validation is presented as a normal part of the workflow
- Advanced topics do not interrupt beginner workflows
- Terminology is consistent throughout

## Sources to trust

- `frontend/src/` — current UI behavior and component structure
- `backend/app/api/` — current API endpoints and capabilities
- `docs/CONFIGURATION_GUIDE.md` — configuration reference
- `docs/DESIGN.md` — architecture context
- `AGENTS.md` — canonical conventions

Verify workflow descriptions against the current implementation before documenting them.
