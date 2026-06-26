---
description: "Use when creating or editing proposal-tree Markdown files in docs/proposals. Enforces document-type selection, required structure, and separation between proposals, phase plans, task plans, handoffs, and archive notes."
applyTo: "docs/proposals/**/*.md"
---

# Proposal Document Structure

Use this for Markdown files under `docs/proposals/`. It keeps proposals, phase plans, task plans, handoffs, and archive notes in separate roles. Detailed style lives in the proposal, phase-plan, task-plan, and writing-style instructions.

## Document Type

Classify each file as one primary type before writing. Create separate files when a request needs more than one type unless the user explicitly asks for one combined document.

| Type | Use For | Do Not Include |
|---|---|---|
| Proposal | Deciding or recommending a change | Progress trackers or detailed execution sequencing |
| Phase plan | Sequencing a larger implementation or migration | Task-level checklists |
| Task plan | Breaking one phase into work items and definition of done | Multi-phase strategy |
| Handoff | Recording current state, next actions, risks, references, and open decisions | New decisions unless clearly labeled as recommendations |
| Archive note | Recording completed work | New active scope |

## Structures

Use these section orders unless an existing file has a stronger local pattern.

| Type | Required Shape |
|---|---|
| Proposal | Title; Status; Summary; Problem; Scope; Non-Goals; Current Behavior when needed; Proposed Design; Alternatives Considered when useful; Risks And Tradeoffs; Testing And Validation; Acceptance Criteria; compact Recommended Delivery Order when useful; Open Questions when real; Final Recommendation |
| Phase plan | Title; Summary; Problem; Scope; Current Position; Phase Plan; Cross-Phase Rules; Validation Strategy; Final Recommendation when useful |
| Task plan | Phase Summary; Work Breakdown; Progress Tracker; Definition Of Done; Validation And Testing; Deliverables; Scope when needed; Risks And Mitigations when meaningful; Open Questions when real; Assumptions when needed |
| Handoff | Title; Purpose; Current State; Completed Work; Key References; Next Actions; Risks; Open Decisions; Suggested Follow-Up Documents |
| Archive note | Title; Status; Summary; Completed Scope; Validation Performed; Remaining Follow-Up when real |

## Phase Shape

Each phase-plan phase must use this shape:

```markdown
### Phase N: <Phase Title>

**Goal**

<one concise goal>

**Focus**

- <focus item>
- <focus item>

**Acceptance Criteria**

- <checkable outcome>
- <checkable outcome>
```

Prefer 3-7 phases. Use parity as an explicit measure when replacing legacy behavior. Include fallback, exception, or cutover phases for migrations when relevant.

## Cross-Document Rules

- Use relative links for repository documents.
- Prefer one clear file per decision or plan.
- Do not duplicate long background sections across related documents.
- Link related proposals, phase plans, task plans, or handoffs near the top.
- Make current state and planned state explicit.
- Treat unknown owners, dates, commands, and rollout details as `TBD` instead of guessing.
- Do not describe planned behavior as shipped behavior.
- For task plans, every acceptance criterion must map to at least one work area and one definition-of-done item.
- For archive notes, mark work complete only when validation is stated.

## Before Finishing

Check that:

- the document type is clear from the title and first section
- required sections for that document type are present or intentionally omitted
- planned work is not described as completed work
- acceptance criteria are checkable
- open questions are real decisions, not filler
- related phase plans, task plans, or handoff documents are linked when they already exist