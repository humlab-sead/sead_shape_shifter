---
marp: true
theme: default
paginate: true
backgroundColor: #fff
header: 'Shape Shifter — AI-Assisted Development (Abridged)'
# footer: 'SEAD Development Team | September 2026'
---

<!--
Deck: Abridged companion to PRESENTATION_AI_CODING.md.
Audience: software developers. No prior knowledge of Shape Shifter or SEAD assumed.

Export:
  marp docs/presentations/PRESENTATION_AI_ASSISTED_DEVELOPMENT_ABRIDGED.md --html|--pdf|--pptx
-->

<!-- _class: lead -->
<!-- _paginate: false -->

# Shape Shifter

## AI-assisted development setup
- repository instructions
- reusable guidance
- tooling  `rtk` and `graphify`
- proposal-driven delivery


---

## Why bother

**Shape Shifter** is an ETL service that transforms heterogeneous source data—files, spreadsheets, and legacy databases—into a target relational model. It is a monorepo with a Python core, FastAPI backend, Vue frontend, and pluggable ingesters.

The project is used with several coding assistants, including GitHub Copilot, Codex, Cline, Claude Code, and Gemini. They differ in which instruction files they read and how much context they can use.

Two practical concerns follow:

1. **Relevant guidance** — repository conventions need to be available when they apply.
2. **Efficient context use** — large command outputs and broad code searches can displace more useful context.

The aim is therefore straightforward: provide focused guidance and reduce unnecessary context.

---

## Instructions are organised by scope

Large general-purpose instruction files have been replaced with smaller, feature-oriented files. Operational rules stay close to the code; background knowledge stays in `docs/`.

| Level                | Scope                                                   | Used when                       |
|----------------------|---------------------------------------------------------|---------------------------------|
| 1 · Repository-wide  | `.github/copilot-instructions.md` · root `AGENTS.md`    | In every relevant session       |
| 2 · Code area        | `AGENTS.md` in `src/`, `backend/`, `frontend/`, etc.    | Work concerns that subtree      |
| 3 · Path-specific    | `.github/instructions/*.instructions.md` with `applyTo` | Files match the configured path |
| 4 · Feature-specific | `.github/instructions/features/*.instructions.md`       | Work concerns that subsystem    |

The repository contains about 30 instruction files and 2,120 lines in total. Only a small core—roughly 50–100 lines—is intended to be present throughout a session.

**The useful measure is not the total amount of guidance, but how much relevant guidance is available for the current task.**

---

## Reusable guidance serves different purposes

**Skills** provide detailed, task-specific guidance that can be loaded when needed:

- `shapeshifter-configuration` — validate, repair, and author project YAML
- `technical-clarity-editor` — improve the clarity of documentation and proposals

**Custom roles** define a narrower scope, suitable tools, and expected validation:

- Developer · Backend · Frontend · Configuration Engineer
- Explore provides a read-only option for investigation

**Reusable prompts** support recurring work such as adding endpoints, loaders, validators, and tests. Others support review, routing, and concise domain reference.

Together, these resources make project conventions easier to apply consistently without placing all supporting material in every session.

---

## `rtk` and `graphify` reduce routine context use

Two tools address common sources of unnecessary context.

**`rtk`** is a command-line proxy that condenses command output. Depending on the command, it can substantially reduce the amount of text returned to the coding assistant.

```bash
git status               rtk git status
uv run pytest tests -q   rtk uv run pytest tests -q
```

A `PreToolUse` hook can rewrite supported commands automatically.

**`graphify`** maintains a knowledge graph of the repository. It supports focused questions about code structure and relationships:

```bash
graphify query "<question>"   # query a relevant subgraph
graphify path "<A>" "<B>"    # inspect a relationship
```

`make update-graphify` refreshes the graph. Hooks can suggest a graph query before a broad text search or sequence of file reads.

In short: `rtk` condenses tool output; `graphify` can narrow codebase exploration.

---

## Shared rules need a reliable source

Different coding tools read different configuration files:

- Codex, Cline, and Gemini use the `AGENTS.md` hierarchy.
- GitHub Copilot also uses `.github/instructions/**` through `applyTo` rules.
- Claude Code and Gemini can use tool-specific entry-point files.

At present, `CLAUDE.md` and `GEMINI.md` are symbolic links to `AGENTS.md`. This avoids copying content, but symbolic links can be inconvenient on some Windows checkouts and are not handled uniformly by every tool.

**Proposed improvement:** use `rulesync` to generate shared instruction files from one source.

```text
.rulesync/rules/*.md ──► AGENTS.md and nested files
                    ├─► CLAUDE.md
                    └─► other supported entry points
```

Tool-specific instructions, roles, prompts, skills, and hooks would remain hand-authored. A `make rules-sync-check` command in pre-commit or CI could detect generated files that are out of date.

**Status: proposed, not yet adopted.**

---

## Development starts with an agreed description of the change

The project separates decisions, planning, and implementation:

| Step | Artifact                                | Purpose                                           |
|------|-----------------------------------------|---------------------------------------------------|
| 1    | GitHub issue or change request          | Describe the need                                 |
| 2    | Proposal                                | Record the intended solution and decisions        |
| 3    | Phase plan                              | Divide a larger change into stages                |
| 4    | Task plan                               | Define work and completion criteria for one phase |
| 5    | Implementation branch                   | Build the change                                  |
| 6    | Review, tests, issue update, and commit | Verify and integrate it                           |

For substantial changes, the task plan is reviewed before implementation begins. This gives both developers and coding assistants a shared interpretation of the scope and acceptance criteria.

---

## Task plans make progress verifiable

A task plan normally contains:

- **Phase summary** — acceptance criteria restated as a checklist
- **Work breakdown** — three to six areas, each with completion criteria
- **Progress tracker** — `Not started`, `In progress`, `Blocked`, or `Done`
- **Definition of done** — links acceptance criteria to verification
- **Validation and testing** — concrete commands, using `rtk` where appropriate

Plans are based on an initial review of the actual code. Unknown paths, commands, owners, or APIs are recorded as `TBD` rather than assumed.

An item is marked complete only after the specified review or test has passed. Blocked work remains visible together with the reason.

For example, the current submission-metadata refactor records one area as blocked because a disposable migrated-database test environment is not yet available.

---

## The setup is maintained as repository configuration

The supporting material is ordinary Markdown and YAML, stored and reviewed with the code.

| Need                     | Location                                           | Main consideration                        |
|--------------------------|----------------------------------------------------|-------------------------------------------|
| Add a path-specific rule | `.github/instructions/<area>.instructions.md`      | Keep the `applyTo` scope narrow           |
| Add detailed guidance    | `.github/skills/<name>/SKILL.md` and `references/` | Define when it should be used             |
| Add a specialist role    | `.github/agents/<name>.agent.md`                   | State scope, tools, and validation        |
| Add a reusable prompt    | `.github/prompts/<name>.prompt.md`                 | Distinguish delegated work from questions |
| Change shared rules      | `AGENTS.md` and subtree files                      | Keep tool entry points consistent         |

The most reusable ideas are modest ones: a small repository-wide core, path-specific guidance, detailed material loaded when needed, automated output reduction, reviewable plans, and a check against configuration drift.

---

## What we have learned

1. **Scope matters more than volume.** Instructions are most useful when they match the code being changed.
2. **Keep the common core small.** Detailed guidance can be loaded for tasks that need it.
3. **Encode recurring project conventions.** Reusable roles and prompts reduce repeated explanation.
4. **Automate routine context reduction.** `rtk` condenses output; `graphify` narrows exploration.
5. **Treat cross-tool consistency as a maintenance problem.** A generated shared layer and drift check may be preferable to symbolic links.
6. **Separate decisions from implementation.** Proposals and task plans make scope and verification explicit.
7. **Review the setup as part of the codebase.** These files affect development work and should evolve with the project.

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Discussion

Which parts of this setup would be useful in your own projects—and which would add unnecessary overhead?
