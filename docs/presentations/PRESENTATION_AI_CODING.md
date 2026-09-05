---
marp: true
theme: default
paginate: true
backgroundColor: #fff
header: 'Shape Shifter — AI Coding Agent Setup'
# footer: 'SEAD Development Team | September 2026'
---

<!--
Deck: How the sead_shape_shifter repo is set up for AI coding agent work.
Audience: software developers. Assumes developer literacy and an interest in
AI-assisted engineering patterns; does NOT assume familiarity with this repo or
the SEAD domain. Domain terms are glossed on first use.

Export:
  marp docs/presentations/PRESENTATION_AI_CODING.md --html
  marp docs/presentations/PRESENTATION_AI_CODING.md --pdf
  marp docs/presentations/PRESENTATION_AI_CODING.md --pptx

Diagrams: the three diagrams in this deck are plain Markdown tables/layouts
(no Mermaid), so they render in the Marp VS Code extension preview as well as
in marp-cli exports. Earlier Mermaid versions were dropped because marp-vscode
3.6.1 has no Mermaid support and showed them as raw code.
-->

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter
## Engineering AI-Assisted Development — a Case Study

Layered agent instructions · skills & agents · `rtk` and `graphify` · proposal-driven delivery

A worked example of what a codebase looks like when you treat AI coding agents as something to engineer — with patterns any developer team can reuse.

**SEAD**
September 2026

---

## Agenda

1. Why we tune the AI coding layer at all
2. Layered agent instructions — size, intent, coverage, quality
3. Skills, agents, and reusable prompts
4. Tooling: `rtk` and `graphify`
5. The cross-agent instruction-parity problem and `rulesync`
6. Proposal → phase plan → task plan → implementation
7. Using and extending this system as a developer
8. Other things worth knowing
9. Takeaways and references

---

# Part 1
# Why This Matters

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## The Working Reality

**Shape Shifter in one line** (all you need for this talk): a data-integration service that reshapes heterogeneous source data — files, spreadsheets, legacy databases — into a target relational model, validating and reconciling as it goes. SEAD is the archaeology data platform it feeds.

It is a monorepo with four moving parts:

- **Core** (`src/`) — Python transformation engine, pipeline order is fixed
- **Backend** (`backend/app/`) — FastAPI, strict layer boundaries
- **Frontend** (`frontend/`) — Vue 3 + Pinia + TypeScript
- **Ingesters** (`ingesters/`) — pluggable, domain-specific importers

Work spans several AI coding agents:

- GitHub Copilot (VS Code) and Copilot CLI
- Codex (VS Code), Cline, Claude Code, Gemini

Each agent reads different instruction files and has a different context budget. The repo treats this as an **engineering problem to optimize**, not an afterthought.

---

## The Two Levers We Keep Pulling

**1. Quality of agent output**

An agent is only as good as the rules it sees. Wrong, stale, or missing rules cause repeated mistakes across the whole repo.

**2. Token budget**

Every agent loop is bounded by context. Long instruction dumps and raw command output crowd out the reasoning the agent can actually do.

Most of what follows is either *putting the right rules in front of the right agent at the right time*, or *cutting tokens*.

---

# Part 2
# Layered Agent Instructions

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Design: A Four-Level Instruction Hierarchy

A completed refactor (`AI_INSTRUCTIONS_REFACTORING.md`) moved from a few big files to a scoped, feature-oriented stack. Rules are **operational**, not encyclopedic — background knowledge lives in `docs/`, not in the always-on context.

| Level | Scope | Example files | Loaded when |
|---|---|---|---|
| 1 · Always-on | Whole repo | `.github/copilot-instructions.md` · root `AGENTS.md` | Every turn |
| 2 · Layer-scoped | Subtree | `AGENTS.md` per subtree (`src` · `backend` · `frontend` · `docs` · `tests` · `.github`) | Editing in that subtree |
| 3 · Path-scoped | Area of code | `.github/instructions/*.instructions.md` (`applyTo`) | Editing a matching path |
| 4 · Feature-scoped | Subsystem | `.github/instructions/features/*.instructions.md` | Editing that subsystem |

Each level layers on the one above: the always-on rules stay visible everywhere, and narrower rules are injected only when the agent touches relevant files.

Narrower layers load only when the agent edits matching files → **relevance up, noise down**.

---

## Level 1 — Always-On: Kept Deliberately Small

| File                              | Lines | Role                                                           |
|-----------------------------------|------:|----------------------------------------------------------------|
| root `AGENTS.md`                  |   ~98 | Shared, always-on guide for every agent that reads `AGENTS.md` |
| `.github/copilot-instructions.md` |   ~83 | Copilot's always-on file                                       |

Design intent:

- **Small on purpose.** The refactor cut the Copilot file from ~120 to ~53 lines; later additions such as the `rtk` block brought it to ~83.
- Contains only cross-cutting rules that must never be wrong: architecture, the API↔Core boundary, mapper and directive rules, registry pattern, async rules, workflow expectations.
- Explicitly *points* to deeper layers instead of restating them.

---

## Level 2 — Subtree `AGENTS.md` Files

Nearest-`AGENTS.md` lookup is how Codex (and Cline/Gemini) get local rules:

- `src/AGENTS.md`, `backend/AGENTS.md`, `frontend/AGENTS.md`, `ingesters/AGENTS.md`
- Added to close Codex's biggest gaps: `.github/AGENTS.md`, `docs/AGENTS.md`, `tests/AGENTS.md`

Each file is an index plus the few rules that matter locally. For example `.github/AGENTS.md` is a table mapping every instruction file to *when to read it*.

> Intent: one lookup path — "what applies here?" — answered close to the code being edited.

---

## Level 3 — Path-Scoped Instructions (`.github/instructions/`)

19 files, ~1,400 lines, each gated by an `applyTo` glob so Copilot injects it **only** when a matching path is edited.

| Theme            | Files                                                                                | Covers                                                   |
|------------------|--------------------------------------------------------------------------------------|----------------------------------------------------------|
| Code conventions | `python`, `frontend`                                                                 | API/Core boundary, DI, registries, Vue/Pinia conventions |
| Configuration    | `shapeshifter-configuration`                                                         | Entity/identity/FK rules — the largest file (224 lines)  |
| Documentation    | `design`, `development`, `operations`, `user-guide`, `readme`, `glossary`, `testing` | Per-doc scope and rules                                  |
| Planning         | `proposal-writing-guide`, `proposal-document-structure`, `phase-plan`, `task-plan`   | How we plan before we build                              |
| Cross-cutting    | `writing-style`, `diagrams`, `github-workflow`, `coding-practices`, `semantic-rules` | Style, process, and evidence rules                       |

`coding-practices.instructions.md` (applyTo `**/*`) is the universal floor: targeted changes, root-cause fixes, and *no success claim without fresh verification*.

---

## Level 4 — Feature-Scoped Instructions

11 files, ~700 lines, one per subsystem so domain rules sit next to the code that implements them:

- `features/entities`, `features/target-model`, `features/specifications`
- `features/loaders`, `features/transforms`, `features/execution`
- `features/validation`, `features/materialization` (emitting target tables), `features/reconciliation` (matching incoming values to reference data)
- `features/ingesters` (pluggable importers), `features/graph` (frontend dependency graph)

Example rule style (from `features/ingesters`): a new ingester is a directory under `ingesters/<name>/`, implements the `Ingester` protocol, and registers with `@Ingesters.register(key=...)`.

> These encode the *hard-won* subsystem contracts so an agent does not re-derive or silently break them.

---

## Size Discipline — Small Files, Scoped Load

Total instruction corpus: **~30 files, ~2,120 lines**.

Distribution is deliberately skewed small:

```text
Most files:           13 – 122 lines
features/:            18 –  92 lines
phase-plan:           187 lines
shapeshifter-config:  224 lines   (only outlier, by design)
```

Why this matters for agents:

- A small, always-on file keeps every turn cheap.
- Deep rules are injected only when relevant — Copilot does this automatically through `applyTo`.
- Small files are easy to review, update, and keep accurate as the code changes.

---

## Quality: Instructions Are Treated as a Deliverable

Several mechanisms keep the instructions themselves accurate and readable:

- **Written to a standard.** `writing-style.instructions.md` governs prose for docs, docstrings, PRs, issues — and AI agent instructions. Concrete, behavior-first language; no vague overloaded terms.
- **Verified against the code.** Instructions describe implemented behavior; `docs/` is the source of truth; `docs/features/` is explicitly a backlog, not authority.
- **Changed through the same pipeline.** Instruction overhauls go through proposals and GitHub issues (e.g. issue #422 tracked the instruction refactor) and land with task plans.
- **Plain docstrings.** Repo guidance is itself an example: *"Reads sample rows from a CSV file."*, never *"Ingests artifacts across the import boundary."*

---

# Part 3
# Skills, Agents, and Prompts

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Skills — Load-on-Demand Expert Knowledge

Two repo skills live in `.github/skills/`, each with a `SKILL.md` plus a `references/` folder:

| Skill                        | Purpose                                                                                               |
|------------------------------|-------------------------------------------------------------------------------------------------------|
| `shapeshifter-configuration` | Deep validate, repair, and author project YAML — loads an authoritative reference file before judging |
| `technical-clarity-editor`   | Light, conservative clarity edits to proposals and docs — preserves tone and intent                   |

Why skills (not always-on instructions):

- Kept out of context until the task actually needs them.
- Each skill front-matter states precisely when to trigger, so routing is deterministic.
- Authoritative detail lives in the skill's `references/`, not in the description.

---

## Custom Agents — Scoped, Delegated Specialists

Four repo-defined agents in `.github/agents/*.agent.md`, each with **scope, working rules, and validation expectations**, plus restricted tools:

| Agent                      | Scope                                                        | Validation focus                            |
|----------------------------|--------------------------------------------------------------|---------------------------------------------|
| **Developer**              | Generalist orchestrator; delegates when specialization helps | Smallest relevant test before claiming done |
| **Backend Developer**      | `backend/app/api|services|models|clients|validators`         | API contract matches domain behavior        |
| **Frontend Developer**     | `frontend/src` components, stores, composables               | State/API flows still match UX              |
| **Configuration Engineer** | `shapeshifter.yml`, project YAML, validators                 | Config matches rules before claiming done   |

A built-in **Explore** agent does read-only research cheaply, keeping the main thread's context clean.

> Effect: the right specialist sees the right subtree rules; the orchestrator keeps cross-layer work coherent.

---

## A Library of Reusable Prompts (~20 templates)

Two complementary families in `.github/prompts/`:

**Implementation generators** (`agent`) — encode layer conventions so agents follow them every time:
- `add-endpoint`, `add-loader`, `add-validator`
- `core-test`, `backend-test`, `frontend-test`
- `proposal-implementation-plan`

**Review and routing agents** (`ask`) — turn the rule set into reviewers:
- `token-router` (route to the smallest useful context first)
- `boundary-guard`, `pipeline-invariant-reviewer`, `backend/frontend-contract-reviewer`
- `ci-gatekeeper`, `graph-steward`, `hotspot-refactor-scout`

**Domain reference cards** — ultra-concise: `sead-database`, `sead-quick-ref`.

> The prompts codify "how we add an endpoint/loader/validator here" so the agent never improvises the architecture.

---

# Part 4
# Tooling: rtk and graphify

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## rtk — A Token-Optimized CLI Proxy

**What it is:** `rtk` (Rust Token Killer) wraps shell commands and filters/compresses their output, saving **60–90% of tokens**.

```bash
# Instead of:                 Use:
git status                    rtk git status
git log -10                   rtk git log -10
uv run pytest tests -q        rtk uv run pytest tests -q
```

**Meta and verification:** `rtk gain` shows savings; `rtk gain --history` per command; `rtk proxy <cmd>` runs raw.

**Why it is beneficial:**

- Command output is where agent loops burn tokens fastest.
- Compressed output keeps more budget for reasoning → longer autonomous runs.
- `make rtk-install` sets it up for both Copilot and Codex.

---

## rtk Is Wired Into the Hooks, Not Just Habit

`.github/hooks/rtk-rewrite.json` rewrites agent tool calls so shell commands pass through `rtk` automatically.

- Uses VS Code/Claude/Copilot `PreToolUse` hook format (`rtk hook copilot`).
- Applies to both Copilot-style and Codex-style hook schemas in one file.
- Re-injects the repo's `.venv/bin` and brew paths before checking for `rtk`.

**Why this is a big deal:** agents do not have to *remember* to prefix every command. The environment rewrites the command for them — the token saving is structural, not optional.

---

## graphify — A Persistent Knowledge Graph of the Repo

**What it is:** a tool that turns code and docs into a queryable knowledge graph.

Outputs live in `graphify-out/`: `graph.json`, `GRAPH_REPORT.md`, `graph.html`, a call-flow HTML, and an agent-crawlable `wiki/index.md`.

**Commands agents are told to prefer:**

```bash
.venv/bin/graphify query "<question>"     # scoped subgraph answer
.venv/bin/graphify path "<A>" "<B>"       # relationship between two things
.venv/bin/graphify explain "<concept>"    # focused explanation
.venv/bin/graphify update .               # refresh graph after code changes
```

---

## Why graphify Pays Off

- **Smaller answers.** `query`/`path`/`explain` return a scoped subgraph, usually far smaller than `GRAPH_REPORT.md` or raw `grep` output — the same token-saving logic as `rtk`.
- **Better architecture questions.** Community detection and cross-file edges surface relationships a linear read misses.
- **A navigation layer that stays current.** Hooks and `make update-graphify` refresh the graph as code changes, so agents trust it.

The repo's guidance is blunt about ordering: *for codebase questions, run a graphify query first; read raw files to modify or debug*.

---

## graphify Is Also Injected Automatically

Agent configs carry graphify context hooks:

- `.codex/hooks.json` — runs `graphify hook-check` before Bash.
- `.claude/settings.json` — injects a graphify hint when the agent greps or reads code files: "run `graphify query …` instead of reading files to answer."
- `make install-graphify` installs hooks for the editor and Codex.

Pattern across the tooling:

> **rtk** compresses *command output*; **graphify** compresses *codebase exploration*. Both are enforced by hooks so the saving is automatic, and both are documented in `AGENTS.md` so every agent knows to use them.

---

# Part 5
# Keeping Instructions on Par Across Agents

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## The Parity Problem

Different agents read different files, so the same repo can look very different to each agent:

| Agent | Reads | Coverage |
|---|---|---|
| Copilot (VS Code) | `copilot-instructions.md` + `.github/instructions/**` via `applyTo` | Richest: docs, features, planning |
| Codex / Cline / Gemini | `AGENTS.md` tree (nearest-file lookup) | Core rules only, unless duplicated |
| Claude Code | `CLAUDE.md` — today a symlink to `AGENTS.md` | Same shared rules as Codex today (via symlink) |
| Copilot CLI | `AGENTS.md` | Same as Codex |

> **Today's nuance:** because `CLAUDE.md` (and `GEMINI.md`) are symlinks to `AGENTS.md`, Claude Code and Gemini currently see the *same shared content* as Codex — the parity gap below is about **fragility and drift**, not missing content. "Generation" only enters the picture if the `rulesync` proposal is adopted.

A comparison doc (`docs/ai/copilot-codex-instruction-comparison.md`) measured the remaining gaps for Codex: docs guidance, feature-specific rules, and planning rules were the biggest mismatches.

---

## Fragility of the Current Single-Source Trick

Today `CLAUDE.md` and `GEMINI.md` are **symlinks to `AGENTS.md`**:

- Avoids copy drift — one file is authoritative.
- But is fragile:
  - Windows checkouts (`core.symlinks=false`) materialize them as plain text containing the path, not the content.
  - Tools that do not follow symlinks silently see nothing.
  - `GEMINI.md` is redundant anyway — Gemini discovers `AGENTS.md` first.
- `.clinerules/project.md` points Cline at a *Copilot-named* file.

There is duplication, no modular source for shared rules, and **nothing detects drift**.

---

## The rulesync Proposal: One Source, Generated Outputs

`RULESYNC_AGENT_INSTRUCTIONS_UNIFICATION.md` proposes the open-source `rulesync` CLI (`dyoshikawa/rulesync`) to generate the **shared rules layer** from a single source of truth:

```text
Source of truth                 Generated by rulesync         Read by
.rulesync/rules/*.md  ──────►   AGENTS.md (+ nested)  ─────►  Codex · Cline · Gemini · Copilot
                        └────►  CLAUDE.md             ─────►  Claude Code
```

**Hand-authored — never written by `rulesync`:**

- Copilot's scoped layer: `.github/instructions/`, `.github/agents/`, `.github/prompts/`, `.github/skills/`
- Cline/Claude/Codex config: `.clinerules/`, hooks and settings
- `GEMINI.md` is removed (redundant); `.clinerules/project.md` is repointed at `AGENTS.md`

Result: every agent that reads `AGENTS.md` stays in sync automatically, while agent-specific capability files are untouched.

---

## rulesync — Scope Discipline

Deliberately **narrow** (this is what makes it safe):

- Generates only `AGENTS.md` (+ nested subtree files) and `CLAUDE.md`.
- `GEMINI.md` is removed as redundant; `.clinerules/project.md` repointed at `AGENTS.md`.
- **Non-goals:** generating Copilot's scoped `.github/instructions/`, `.github/agents/`, `.github/prompts/`, `.github/skills/`, `.clinerules`, hooks, permissions, or skills. Those agent-specific surfaces stay hand-authored.

**The guard rail:** a `make rules-sync-check` drift check (pre-commit + CI) fails when generated files diverge from `.rulesync/rules/` — so instructions can no longer silently drift apart.

> Status: **proposed**, not yet adopted — an open decision, tracked exactly like any other change.

---

# Part 6
# Proposal-Driven Development

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## Decide, Sequence, Then Execute

The core workflow is a strict document pipeline, with one role per document type:

| Step | Artifact | Role |
|---|---|---|
| 1 | GitHub issue / change request | Trigger for the work |
| 2 | Proposal | Decision document |
| 3 | Phase plan | Sequencing of a larger effort |
| 4 | Task plan per phase | Checklist + definition of done |
| 5 | Implementation on a branch | Building the change |
| 6 | Review · tests · issue + commit | Landing the work |

A task plan is **written and confirmed before implementation starts** — acceptance criteria are agreed up front, then ticked off as work lands.

---

## Proposals — The Decision Documents

Proposals live under `docs/proposals/` (with `done/`, `future/`, `onhold/`), and each file must declare **one primary type**:

| Type              | Job                                   | Must not contain      |
|-------------------|---------------------------------------|-----------------------|
| Proposal          | Decide/recommend a change             | Progress trackers     |
| Phase plan        | Sequence a larger effort              | Task-level checklists |
| Task plan         | Break one phase into work items + DoD | Multi-phase strategy  |
| Handoff / Archive | Record state / completed work         | New active scope      |

Proposal shape is enforced (`proposal-document-structure` + `proposal-writing-guide`): **problem-first, lean, KISS**, a clear recommendation, explicit non-goals, and acceptance criteria. *Stop when the decision is clear* — proposals are not docs by accretion.

---

## Phase Plans — Sequencing the Larger Effort

A phase plan is the bridge from decision to delivery and is broader than a task plan. Shape per phase:

```text
### Phase N: <Title>
Goal            ← one concise goal
Focus           ← focus items
Acceptance Criteria  ← checkable outcomes
```

Rules that matter for agents:

- Prefer **3–7 ordered phases**; dependency drives ordering.
- **Current state vs target state** must be explicit.
- Acceptance criteria are **checkable**, not vibes.
- Replacing legacy behavior uses **parity** as the delivery measure.
- Never describe planned work as shipped; use `TBD` for unknowns.

Real example: the AI Advisor (a grounded AI feature) is sequenced as Phases 0–6 with evaluation gates — the methodology is used to build AI features too.

---

## Task Plans — The Implementation Checklist

One task plan per phase, turned into independently checkable work:

- **Phase Summary** — the acceptance criteria restated as a checklist.
- **Work Breakdown** — 3–6 areas, each with an objective, `[ ]` task checklist, and completion criteria.
- **Progress Tracker** — compact status table (`Not started / In progress / Blocked / Done`).
- **Definition of Done** — final checklist tying acceptance criteria to validation.
- **Validation And Testing** — concrete commands (prefixed with `rtk`).
- Optional: Deliverables, Scope, Risks, Open Questions, Assumptions.

Every acceptance criterion must map to ≥1 work area and ≥1 DoD item.

---

## A Live Example: SEAD Submission Metadata Refactor

The current branch's task plan (`REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md`) shows the discipline in action:

- Proposal `REFACTOR_SEAD_SUBMISSION_METADATA.md` → task plan → work areas (5).
- Acceptance criteria tracked with real state:
  - `[x]` stable defaults round-trip; `[x]` one Pending submission emitted; …
  - `[ ]` "upstream PostgreSQL contract is validated against a disposable migrated database".
- Progress Tracker is honest: work area **Blocked** with the reason recorded — *no disposable migrated PostgreSQL harness exists in the repository yet*.
- Validation lists exact `rtk`-prefixed test commands per area.

Even the upstream SQL migration ships as forward + revert Sqitch artifacts alongside the proposal — plan-first applies to schema work too.

> **Gloss for non-SEAD devs:** a *target model* is the destination schema the data is shaped into; *Sqitch* is database change-management (each migration has deploy/revert/verify scripts); a *disposable migrated database harness* is simply a throwaway PostgreSQL instance for testing migrations. You do not need these details — the point is the checklist discipline.

---

## Why This Works for AI Agents

The planning documents are written *for humans and agents alike* and read like a contract:

- **Grounding.** Plans are produced only after exploring real code (`proposal-implementation-plan` prompt forces this).
- **No invention.** Rules say: do not invent file paths, commands, owners, or APIs. Unknowns are `TBD` or open questions.
- **Checkable units.** Every task and acceptance criterion is independently verifiable — an agent can tick a box only when a test or review confirms it.
- **Honest status.** Blocked work stays blocked and recorded instead of being silently "done".
- **Verification before completion.** `coding-practices.instructions.md`: no success claim without fresh output.

The result: agents produce code that matches the plan, and the plan shows *why* each piece exists.

---

# Part 7
# Using and Extending This System as a Developer

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## A Developer's Typical Session

Everything above composes into a normal working day:

1. **You open a task on a branch** — its task plan was confirmed before implementation started.
2. **The agent auto-loads context** — root `AGENTS.md` always; subtree `AGENTS.md` by folder; and in Copilot, only the `.github/instructions/*.md` files whose `applyTo` matches the files you touch.
3. **You pick the right tool** — invoke a specialist (`/backend-developer`) or a generator prompt (`/add-endpoint`, `/core-test`) instead of prompting from scratch.
4. **Exploration is already cheap** — the agent runs `graphify query …` before grep, and shell output is compressed through `rtk` by a hook.
5. **Tests decide "done"** — each task maps to concrete `rtk`-prefixed commands; a box is ticked only when they pass.
6. **Merge has a gate** — you run the review prompts (`/boundary-guard`, `/ci-gatekeeper`) and commit per `github-workflow.instructions.md`.

> The instructions do the explaining once; you and the agent spend effort on the code, not on re-deriving conventions.

---

## Extending the System: It's Just Files, Versioned Like Code

The whole AI layer is plain Markdown/YAML with frontmatter — treat it as **configuration-as-code**:

| I want to…                      | Create                                           | Key fields                                                   |
|---------------------------------|--------------------------------------------------|--------------------------------------------------------------|
| Add a rule for an area          | `.github/instructions/<area>.instructions.md`    | `applyTo` path glob; small & single-purpose                  |
| Add deep domain knowledge       | `.github/skills/<name>/SKILL.md` + `references/` | trigger description, argument hint                           |
| Add a specialist                | `.github/agents/<name>.agent.md`                 | scope, working rules, validation expectations, allowed tools |
| Add a reusable prompt           | `.github/prompts/<name>.prompt.md`               | `agent:` (generator) vs `ask:` (reviewer)                    |
| Change shared cross-agent rules | `AGENTS.md` (+ subtree files)                    | keep `CLAUDE.md`/`GEMINI.md` in sync — or adopt `rulesync`   |

Rules of thumb: keep files small, make them operational not encyclopedic, follow `writing-style`, and land changes through the same proposal → review pipeline as code.

---

## Patterns You Can Steal for Any Repo

1. **Path-scoped context injection** — bind rules to code paths (`applyTo` / subtree `AGENTS.md`) so only relevant rules load.
2. **Keep always-on tiny** — a small core file every agent reads on every turn.
3. **On-demand knowledge** — skills and reference prompts load only when a task needs them.
4. **Enforce cost with hooks** — rewrite/compress command output and inject cheap-retrieval hints automatically, so agents do not have to remember.
5. **Give agents contracts, not vibes** — acceptance criteria before implementation; forbid inventing paths, commands, or APIs; require verification before "done".
6. **Review agents as a second pair of eyes** — reviewer prompts encode your invariants as pre-merge checks.
7. **Single source + drift check** for shared rules when you run several agents — generate `AGENTS.md`/`CLAUDE.md` from one tree, or at least test that they have not diverged.

---

# Part 8
# Other Things Worth Knowing

<!-- _class: lead -->
<!-- _backgroundColor: #1e3a8a -->
<!-- _color: white -->

---

## More of the AI-Coding Layer

- **Semantic rules catalog** (`docs/rules/`, `semantic-rules.instructions.md`): AI-readable YAML rules (`id`, `severity`, `when`, `require`, `fix`) that complement JSON Schema for project YAML — so agents can explain and repair configs.
- **`docs/` is authoritative; `docs/features/` is backlog.** This single rule stops agents from implementing roadmap prose as if it were shipped behavior.
- **Instruction docs are reference, not policy**: comparison and agent notes live in `docs/ai/` (e.g. `copilot-codex-instruction-comparison.md`) as reference notes, not authoritative rules.
- **Makefile as the agent control surface** — `make lint`, `make tidy`, `make test`, plus `rtk-install`, `install-graphify`, `update-graphify`, `commit-graphify` — one command set every agent is pointed at.

---

## What We Optimized, Summarized

| Lever                   | Mechanism                                 | Effect                                  |
|-------------------------|-------------------------------------------|-----------------------------------------|
| Right rules, right time | 4-level scoped instructions (`applyTo`)   | Relevance up, noise down                |
| Small always-on         | ~50–80 line core files                    | Cheap every turn                        |
| Domain experts on tap   | skills + custom agents + ~20 prompts      | Consistent specialist output            |
| Output compression      | `rtk` (and hook rewrite)                  | 60–90% fewer output tokens              |
| Cheap exploration       | `graphify` query/path/explain (+ hooks)   | Small answers to architecture questions |
| Cross-agent parity      | `AGENTS.md` tree now; `rulesync` proposed | Stop instructions drifting apart        |
| Plan before code        | proposal → phase plan → task plan         | Grounded, verifiable implementation     |

---

## Takeaways

1. **Instructions are layered and path-scoped** so agents get the right rules without paying for all of them every turn.
2. **Knowledge stays in `docs/`; instructions stay operational** — small, concrete, and reviewable.
3. **Agents and prompts encode the architecture**, so adding an endpoint, loader, or validator follows the same shape every time.
4. **`rtk` and `graphify` attack the two biggest token sinks** — command output and codebase exploration — and are enforced through hooks.
5. **Cross-agent parity is a real drift risk**; the `AGENTS.md` tree is the shared baseline today, with `rulesync` proposed to generate and drift-check it.
6. **Proposal → phase plan → task plan → implementation** keeps agents grounded: decide, sequence, confirm the checklist, then build — and verify before claiming done.
7. **The whole AI layer is configuration-as-code** — versioned, reviewed, and easy to extend. That is the most transferable idea here: engineer your agent setup like you engineer your product, and it compounds.

---

## Key References

- `AGENTS.md` (root + subtree), `.github/copilot-instructions.md`
- `.github/instructions/` (+ `features/`), `.github/instructions/phase-plan.instructions.md`, `task-plan.instructions.md`
- `.github/agents/*.agent.md`, `.github/prompts/`, `.github/skills/`
- `RTK.md`, `Makefile` (`rtk-install`, `install-graphify`, `update-graphify`)
- `docs/proposals/RULESYNC_AGENT_INSTRUCTIONS_UNIFICATION.md`
- `docs/ai/copilot-codex-instruction-comparison.md`
- `docs/proposals/` — e.g. `CHANGE_REQUEST_INGESTER/`, `SHAPESHIFTER_PROJECT_AI_ADVISOR/`
- `graphify-out/` — knowledge graph + wiki

<!-- _class: lead -->
<!-- _paginate: false -->

# Thank You

Questions and discussion
