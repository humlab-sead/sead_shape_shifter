---
name: move-proposal
description: Move a proposal file or topic folder under docs/proposals to done/, future/, onhold/, or into its own subfolder, updating the index and relative links. Use when asked to move, archive, defer, shelve, or group a proposal. Do not use for creating, reviewing, or implementing proposals.
---

# Move A Proposal

Move one proposal file or topic folder to a new location under `docs/proposals/`, keep the index and links consistent, and verify the result.

Optimize for a small number of tool calls. A correct move takes roughly six to ten targeted calls, not a repository survey. Follow the Time Sinks To Avoid section.

## Targets

`<TOPIC>` is the source name without its `.md` extension.

| User says | Destination |
|---|---|
| `done` | `docs/proposals/done/<TOPIC>/` (or `docs/proposals/done/<TOPIC>.md`) |
| `future` | `docs/proposals/future/<TOPIC>/` (or `docs/proposals/future/<TOPIC>.md`) |
| `onhold` | `docs/proposals/onhold/<TOPIC>/` (or `docs/proposals/onhold/<TOPIC>.md`) |
| `subfolder` | `docs/proposals/<TOPIC>/<TOPIC>.md` — wrap the standalone file into its own new folder |

- A status destination keeps the source shape: a folder stays a folder, and a standalone file stays a standalone file.
- The `subfolder` destination requires `docs/proposals/<TOPIC>.md` to exist. If only a folder exists, report that the file is already grouped and stop.
- An explicit destination in the user's request wins. Ask one concise question only when the source cannot be identified.
- If both `<TOPIC>.md` and `<TOPIC>/` exist, treat the folder as the source and say so.

## Workflow

1. Resolve the source with one targeted command:

   ```bash
   ls -d docs/proposals/<TOPIC>.md docs/proposals/<TOPIC> 2>/dev/null
   ```

2. Read the moving document's `## Status` block, and find inbound references in one grep:

   ```bash
   rg -n "<TOPIC>" docs README.md --glob '!docs/proposals/<TOPIC>*'
   ```

3. Move with `git mv` so history is preserved:
   - folder: `git mv docs/proposals/<TOPIC> docs/proposals/<TARGET>/<TOPIC>`
   - file: `git mv docs/proposals/<TOPIC>.md docs/proposals/<TARGET>/<TOPIC>.md`
   - subfolder: `mkdir -p docs/proposals/<TOPIC> && git mv docs/proposals/<TOPIC>.md docs/proposals/<TOPIC>/`

4. Fix relative links in the moved documents and in the documents that reference them. See Outbound Links and Inbound References.

5. Update `docs/proposals/README.md`. See Index Rules.

6. Rewrite the moved proposal's `## Status` block. See Status Rewrite.

7. Verify with one command. See Verification.

8. Commit the move as one commit. See Commit.

## Outbound Links (Inside The Moved Document)

Relative links resolve against the containing directory. For a link written inside the document you are moving, count the directory depth before and after the move, then add one `../` per added level to every link that points outside the moved directory.

| Move | Depth change | Link fix |
|---|---|---|
| `docs/proposals/X/` to `docs/proposals/done/X/` | +1 | `../a.md` becomes `../../a.md` |
| `docs/proposals/X.md` to `docs/proposals/X/X.md` | +1 | `../a.md` becomes `../../a.md` |
| `docs/proposals/future/X.md` to `docs/proposals/done/X.md` | 0 | none |
| `docs/proposals/X/` to `docs/proposals/X/Y/` | +1 | `../a.md` becomes `../../a.md` |

- Leave same-folder targets unchanged; they move with the file or folder.
- Never change `#fragment`, `http(s)://`, `mailto:`, or `/`-rooted links.
- Find every link in one pass with `rg -n "\]\(" <moved files>`.
- `make check-doc-links` does not validate `docs/proposals/`. Do not run it for this move; use the bundled checker.

## Inbound References (Links Into The Moved Topic)

A link from another document into the moved topic takes one change: insert the status folder. The number of `../` stays exactly as it was, because the referring document did not move.

| Referring document | Before | After (topic moved into `future/`) |
|---|---|---|
| `docs/proposals/done/A/B.md` | `../../X/README.md` | `../../future/X/README.md` |
| `docs/proposals/done/A/done/C.md` | `../../../X/README.md` | `../../../future/X/README.md` |

- Do not add a `../`. The `+1` rule above applies only to links inside the document being moved. Adding a level here is the common mistake, and it breaks every inbound reference at once.
- When unsure, recompute from the referring file's own directory to the new target. The bundled checker is the authority: it reports each link that does not resolve, with the file and target.
- Update backticked paths too, such as a `docs/proposals/X/README.md` cell in a table, so the prose still names a real location.
- A referring document inside the moved folder is outbound, not inbound; handle it with the table above.

## Index Rules

`docs/proposals/README.md` holds four tables: Open Proposals, Current Initiatives, Future Proposals, and On Hold.

| Destination | Index change |
|---|---|
| `done` | Remove the Open Proposals row. Add no row; `done/` is linked from the footer. |
| `future` | Move the row from Open Proposals to the Future Proposals table (Proposal, Topic). |
| `onhold` | Move the row from Open Proposals to the On Hold table (Record, Status, Topic). |
| `subfolder` | Keep the row in Open Proposals and update its target to `docs/proposals/<TOPIC>/<TOPIC>.md`. |

- Leave all other rows and every column shape unchanged.

## Status Rewrite

Replace the `## Status` bullets with the shape that matches the destination:

- `done`: `- **Implemented** (branch \`<branch>\`; merged in [PR #N](https://github.com/owner/repo/pull/N)).` followed by Scope, Goal, Validation, and any real remaining follow-up.
- `future`: `- Proposed future change` followed by Scope and Goal.
- `onhold`: `- On hold; <one-line reason>` followed by Scope and Goal.

State only validation that actually happened. Do not invent branch names, PR numbers, or validation results. Do not hunt for a linked issue with git history or the GitHub API; keep an issue line only when the source document already names one.

## Verification

Run the bundled relative-link checker over the moved documents:

```bash
bash .agents/skills/move-proposal/scripts/check_relative_links.sh docs/proposals/<TARGET>/<TOPIC>/*.md
```

Then confirm the old path is gone and the move is rename-tracked:

```bash
rg -n "docs/proposals/<TOPIC>" docs README.md ; git status --short --find-renames
```

The grep should return only references that intentionally point at the new location.

External `http(s)` links are out of scope for a move, and no checker in this repository validates them. `scripts/check_doc_links.sh` and the bundled checker both skip them, and VS Code validation never leaves the workspace. Do not add an external-link check to a move; it needs network access and cannot detect what a move breaks.

## Commit

Commit the move, the inbound reference fixes, and the index change together as one commit. Use the archive message shape already used in this repository:

| Destination | Commit message |
|---|---|
| `done` | `chore: moved <TOPIC> to done` |
| `future` | `chore: moved <TOPIC> to future` |
| `onhold` | `chore: moved <TOPIC> to onhold` |
| `subfolder` | `chore: moved <TOPIC> into a subfolder` |

- Stage only the moved files, their inbound references, and `docs/proposals/README.md`.
- Add no issue reference; repository archive commits do not use one and the move usually has no tracked issue.
- Report the commit hash in the completion message.

## Time Sinks To Avoid

These steps made a manual move take over four minutes. Skip them.

- `file_search docs/proposals/**` — it returns the whole proposal tree. Use `ls` on the one topic.
- Reading `.github/instructions/proposal-document-structure.instructions.md` or other instruction files — they are already injected for `docs/proposals/**/*.md`.
- Reading archived proposals or listing `done/` to learn the Status shape — it is in Status Rewrite above.
- Hunting for an issue number with `git log --grep`, `git show`, `gh issue list`, or `gh pr view`. One grep of the source document is the limit.
- Reviewing phase-task-plan checkboxes and validation milestones to confirm completion before moving. The user orders the move; do not re-verify finished work.
- Running `make check-doc-links` — it does not cover `docs/proposals/` and fails on a pre-existing unrelated break.
- Assuming VS Code's `markdown.updateLinksOnFileMove.enabled` will fix a `git mv` the agent ran. It is wired to `onDidRenameFiles`, which a terminal move never fires, so the links are left untouched.
- Applying the Outbound Links `+1` rule to inbound references. Inbound links keep their `../` prefix and only gain the status folder; adding a level breaks all of them.

## Limits

- Move one proposal per invocation.
- Change only the moved files, their inbound references, and `docs/proposals/README.md`.
- Do not rewrite proposal content beyond the Status block and link paths.
- Do not create `done/`, `future/`, or `onhold/`; they already exist.
- If an instruction conflict prevents the move, report it instead of guessing.
- Commit the move before reporting completion.
- Report the destination path, the links fixed, the verification output, and the commit hash.
