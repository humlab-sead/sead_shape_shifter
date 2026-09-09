---
marp: true
theme: default
paginate: true
backgroundColor: #fff
header: 'Shape Shifter — AI Coding Agent Setup (Abridged)'
# footer: 'SEAD Development Team | September 2026'
---

<!--
Deck: Abridged (~10 pages) companion to PRESENTATION_AI_CODING.md.
Audience: software developers. No repo/SEAD knowledge assumed; domain terms
glossed inline. Diagrams are plain Markdown (tables/layouts) so they render in
the Marp VS Code preview and in marp-cli exports.

Export:
  marp docs/presentations/PRESENTATION_AI_CODING_ABRIDGED.md --html|--pdf|--pptx
-->

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter
## Engineering AI-Assisted Development — a Case Study (Abridged)

Layered instructions · skills & agents · `rtk` and `graphify` · proposal-driven delivery

What a codebase looks like when you treat AI coding agents as something to engineer — patterns any developer team can reuse.

**SEAD**
September 2026

---

## Why We Tune the AI Coding Layer

**Shape Shifter in one line:** a data-integration service that reshapes heterogeneous source data (files, spreadsheets, legacy databases) into a target relational model. A monorepo: Python core · FastAPI backend · Vue frontend · pluggable ingesters.

**Reality:** several agents work here — Copilot, Codex, Cline, Claude Code, Gemini. Each reads different instruction files and has a different context budget.

Two levers drive everything:

1. **Rule quality** — an agent is only as good as the rules it sees; wrong or missing rules cause repo-wide mistakes.
2. **Token budget** — agent loops are context-bound; long dumps crowd out reasoning.

So: put the right rules in front of the right agent at the right time, and cut tokens.

---

## Layered Agent Instructions

A completed refactor replaced a few big files with a scoped, feature-oriented stack. Rules stay **operational**; knowledge lives in `docs/`.

| Level | Scope | Loaded when |
|---|---|---|
| 1 · Always-on | `.github/copilot-instructions.md` · root `AGENTS.md` | Every turn |
| 2 · Layer-scoped | `AGENTS.md` per subtree (`src` · `backend` · `frontend` · …) | Editing in that subtree |
| 3 · Path-scoped | `.github/instructions/*.instructions.md` (`applyTo`) | Editing a matching path |
| 4 · Feature-scoped | `.github/instructions/features/*.instructions.md` | Editing that subsystem |

Numbers that matter: ~30 files, ~2,120 lines total, but only relevant layers are injected (`applyTo`) — the always-on core is ~50–100 lines. **Relevance up, noise down.**

---

## Skills, Agents, and Prompts

**Skills** — load-on-demand expert knowledge kept out of context until needed (each with trigger + `references/`):
- `shapeshifter-configuration` — deep project-YAML validate/repair/author
- `technical-clarity-editor` — light clarity edits to docs/proposals

**Custom agents** — scoped specialists with restricted tools and explicit validation expectations:
- **Developer** (orchestrator) · **Backend** · **Frontend** · **Configuration Engineer** (+ a read-only **Explore** agent)

**~20 reusable prompts** — implementation generators (`add-endpoint`, `add-loader`, `add-validator`, test writers), review/routing agents (`token-router`, `boundary-guard`, `ci-gatekeeper`, …), and ultra-concise domain reference cards.

Effect: conventions are encoded once; agents never improvise the architecture.

---

## Tooling: rtk and graphify

Two tools attack the biggest token sinks, and both are enforced by hooks so agents don't have to remember:

**`rtk` — a token-optimized CLI proxy** compresses shell-command output, saving **60–90%** of tokens.
```bash
git status               rtk git status
uv run pytest tests -q   rtk uv run pytest tests -q
```
A `PreToolUse` hook (`.github/hooks/rtk-rewrite.json`) rewrites agent tool calls through `rtk` automatically.

**`graphify` — a persistent knowledge graph** of the repo. Agents prefer scoped queries over raw greps:
```bash
graphify query "<question>"   # scoped subgraph answer
graphify path "<A>" "<B>"     # relationship
```
Hooks inject a "run graphify first" hint before grep/read calls; `make update-graphify` keeps it current.

Pattern: **rtk** compresses command output, **graphify** compresses codebase exploration — both automatic.

---

## Keeping Instructions on Par Across Agents

Different agents read different files, so the same repo looks different to each:

- Codex / Cline / Gemini read the **`AGENTS.md`** tree; Copilot also gets the rich `.github/instructions/**` layer via `applyTo`.
- `CLAUDE.md` and `GEMINI.md` are **symlinks to `AGENTS.md`** — no copy drift, but fragile (Windows checkouts, tools that don't follow symlinks) and nothing detects divergence.

**Proposed fix — `rulesync`** (open-source CLI): generate the shared layer from one source of truth.
```text
.rulesync/rules/*.md ──► AGENTS.md (+ nested) ──► Codex · Cline · Gemini · Copilot
                     └─► CLAUDE.md        ──► Claude Code
```
- Agent-specific surfaces (`.github/instructions`, agents, prompts, skills, hooks) stay **hand-authored**.
- A `make rules-sync-check` drift gate (pre-commit/CI) stops silent divergence.

Status: **proposed**, not yet adopted.

---

## Proposal-Driven Development

Decide, sequence, then execute — one role per document:

| Step | Artifact | Role |
|---|---|---|
| 1 | GitHub issue / change request | Trigger |
| 2 | Proposal | Decision document |
| 3 | Phase plan | Sequencing of a larger effort |
| 4 | Task plan per phase | Checklist + definition of done |
| 5 | Implementation on a branch | Building the change |
| 6 | Review · tests · issue + commit | Landing the work |

**A task plan is written and confirmed before implementation starts** — acceptance criteria are agreed up front, then ticked off as work lands.

---

## Task Plans — Contracts, Not Vibes

A task plan turns one phase into independently checkable work:

- **Phase Summary** — acceptance criteria restated as a checklist
- **Work Breakdown** — 3–6 areas, each with tasks and completion criteria
- **Progress Tracker** — honest status (`Not started / In progress / Blocked / Done`)
- **Definition of Done** — ties acceptance criteria to validation
- **Validation And Testing** — concrete `rtk`-prefixed commands

Why it works for agents:

- Plans are written only after exploring real code — **grounded**.
- Agents may **not invent** file paths, commands, owners, or APIs (`TBD` instead).
- Every item is **checkable**; a box is ticked only when a test/review passes.
- Blocked work stays **Blocked** with the reason recorded.
- No success claim without fresh verification (`coding-practices`).

Example: the current branch's submission-metadata refactor tracks checked acceptance criteria and records one work area as Blocked — no disposable migrated-database harness exists yet.

---

## Make It Yours: Config-as-Code + Patterns to Steal

The whole AI layer is plain Markdown/YAML with frontmatter — versioned like code:

| I want to… | Create | Key fields |
|---|---|---|
| Add a rule | `.github/instructions/<area>.instructions.md` | `applyTo` glob; small |
| Add deep knowledge | `.github/skills/<name>/SKILL.md` + `references/` | trigger description |
| Add a specialist | `.github/agents/<name>.agent.md` | scope · rules · validation · tools |
| Add a prompt | `.github/prompts/<name>.prompt.md` | `agent:` vs `ask:` |
| Change shared rules | `AGENTS.md` (+ subtrees) | sync or adopt `rulesync` |

**Patterns to steal:** path-scoped context injection · tiny always-on core · on-demand knowledge · hooks that enforce cost automatically · contracts before implementation · reviewer prompts as a pre-merge gate · single source + drift check for shared rules.

---

## Takeaways

1. **Right rules, right time** — layered, path-scoped instructions load only what's relevant.
2. **Small always-on, deep on-demand** — cheap every turn; skills/reference prompts for depth.
3. **Agents and prompts encode the architecture** — consistent output without improvising.
4. **Hooks, not habits** — `rtk` compresses command output, `graphify` compresses exploration, enforced automatically.
5. **Multi-agent parity is a real drift risk** — `AGENTS.md` tree now; `rulesync` (generate + drift-check) proposed.
6. **Plan before code** — proposal → phase plan → task plan (confirmed) → implement; verify before claiming done.
7. **Engineer your agent setup like your product** — it's configuration-as-code, and it compounds.

<!-- _class: lead -->
<!-- _paginate: false -->

# Thank You

Questions and discussion
