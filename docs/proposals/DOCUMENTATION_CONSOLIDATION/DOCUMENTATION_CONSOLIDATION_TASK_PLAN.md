# Documentation Consolidation Task Plan

**Plan readiness:** Validated

**Source:** an ad hoc documentation review. No upstream proposal or phase plan exists. The review findings are reproduced in **Repository Findings** below, so this plan is self-contained; the scratch file that held them was removed on 2026-09-10. Acceptance criteria are derived from those findings and from one confirmed user decision.

**Related documents:** none yet. This file is the first document in `docs/proposals/DOCUMENTATION_CONSOLIDATION/`.

---

## Phase Summary

**Goal:** Bring the active documentation set back in line with its own scope rules and with the Podman deployment that replaced the Docker deployment.

**Focus**

- Fix broken and stale cross-references.
- Retire the `docker/` deployment path and repoint every reference to `container/`.
- Reduce root `README.md`, `docs/DIAGRAMS.md`, and `docs/README.md` to their documented responsibilities.
- Remove YAML reference material that `docs/CONFIGURATION_GUIDE.md` already owns.
- Add an automated check so link rot is caught rather than reviewed manually.

**Constraints**

- Do not change application code, tests, or runtime configuration. This phase changes documentation, agent instruction files, and the build/deploy entry points that reference the retired `docker/` path.
- `docker/` is retired. Podman under `container/` is the only supported deployment path. This decision was confirmed by the user on 2026-09-10.
- Delete `docker/` in a dedicated commit so it can be reverted independently of the documentation edits.
- Do not create `docs/TROUBLESHOOTING.md`. The review recommendation pointed at a file that does not exist. Link to the existing troubleshooting sections instead: `docker/README.md` is retired, so use `docs/DEVELOPMENT.md`, `docs/TESTING.md`, and `docs/CONFIGURATION_GUIDE.md`.
- Preserve the section structure of existing documents unless a task explicitly authorizes restructuring. `USER_GUIDE.md` and `DIAGRAMS.md` have their own instruction files that constrain reorganization.
- Record the review outcome of finding 3 (see `PH1-AC-3`) rather than acting on it; the finding was not reproducible.

**Dependencies**

- The `docker/` retirement decision is resolved, so Areas 2, 3, and 4 are unblocked.
- `container/` is tracked in git (37 files), so Area 2 can delete `docker/` without losing the Podman deployment path.

**Acceptance Criteria**

- [ ] `PH1-AC-1` Root `README.md` contains no developer setup walkthrough, no deployment procedure, no CLI or YAML reference, and no architecture deep-dive; it stays under 300 lines and links to the owning documents.
- [ ] `PH1-AC-2` `docs/OPERATIONS.md` documents the Podman deployment as the only deployment path, names no `docker/` path or `docker compose` command, and stays within the 800–1800 word target in `.github/instructions/operations.instructions.md`.
- [ ] `PH1-AC-3` Every relative link in `README.md`, `docs/README.md`, `docs/OPERATIONS.md`, `docs/USER_GUIDE.md`, and `docs/DIAGRAMS.md` resolves; finding 3 is recorded as not reproducible with the evidence that disproves it.
- [ ] `PH1-AC-4` `docs/USER_GUIDE.md` contains no YAML semantics owned by `docs/CONFIGURATION_GUIDE.md` and no broken links.
- [ ] `PH1-AC-5` `docs/DIAGRAMS.md` contains diagrams with short captions only; product narrative and the feature catalog live in `docs/DESIGN.md` or `docs/USER_GUIDE.md`.
- [ ] `PH1-AC-6` `docs/README.md` is a documentation map with one row per active document, lists every active document, and contains no duplicated proposal inventory.
- [ ] `PH1-AC-7` A `make` target runs the documentation link check, and the retired `docker/` path no longer appears in the root `Makefile`, `README.md`, `docs/OPERATIONS.md`, or `.github/instructions/`.

---

## Repository Findings

**Repository basis:** branch `security-regression-and-release-verification`, commit `6b3ea6dd`, planned 2026-09-10. Uncommitted changes were considered at planning time: `container/` was untracked, and `TODO.md` and `scripts/README.md` were modified. The review findings lived in a scratch file, `TEMP.md`, which was removed on 2026-09-10.

| Evidence | Finding | Planning implication |
|---|---|---|
| `README.md` (502 lines, 1951 words) | Contains Docker quick start, full developer installation, CLI reference, YAML example, FK constraint reference, architecture summary, test commands, and contributing rules. `.github/instructions/readme.instructions.md` excludes all of these. | Area 4 replaces content with links. Instruction target is 100–250 lines, hard ceiling 300. |
| `docs/OPERATIONS.md` (564 lines, 3766 words) | 60 `docker` mentions, 0 `podman` mentions. Paths, commands, and image names all describe the Docker path. | Area 3 rewrites it. Instruction target is 800–1800 words. |
| `container/README.md`, `container/DEPLOYMENT.md`, `container/Makefile`, `container/scripts/setup.sh`, `container/podman-compose.yml` | Podman deployment with data at `../container-data/`. Makefile targets: `setup`, `build`, `up`, `down`, `restart`, `logs`, `status`, `ps`, `shell`, `healthcheck`, `backup`, `clean`, `prune`, `service-*`. Container name is `shape-shifter`. | These are the authoritative sources for Area 3 and Area 4 content. |
| `container/podman-compose.yml` | `env_file` reads `${CONTAINER_DATA_DIR:-../container-data}/backend.env`, matching `setup.sh`, `container/README.md` and the volume mounts. An earlier revision of this row recorded a `./data/backend.env` mismatch that no longer exists. | Out of scope and already resolved, so it no longer blocks writing an accurate path in Area 3. |
| `container/resources/backend.env.example` | Uses `SHAPE_SHIFTER_*` prefixed names for all 14 settings. An earlier revision of this row described `container/.env.example` as holding unprefixed names; that file did not exist at the time, and the template that does exist is prefixed. A separate, newer `container/.env.example` holds deployment defaults (image, git ref, host port, `VITE_*`), not backend settings. | Out of scope, but the `SHAPE_SHIFTER_*` table in `docs/OPERATIONS.md` must be verified against `backend/app/core/config.py`, not against the env template. |
| `Makefile:337-349` | Root `Makefile` does `include docker/Makefile`, exports `DOCKER_DIR`, and defines `docker-patch-frontend` using `docker cp`. | Removing `docker/` breaks the root `Makefile` unless these lines are removed first. |
| `.github/instructions/readme.instructions.md:21,30,46`; `.github/instructions/operations.instructions.md:72,73,79` | Agent instruction files name `docker/README.md` and `docker/docker-compose.yml` as trusted sources. | These must be updated in Area 2 or the instructions keep sending agents to deleted files. |
| `docs/README.md` (302 lines) | Omits `DIAGRAMS.md`, `GLOSSARY.md`, `SQL_SAFETY_POLICY.md`, `TARGET_MODEL_GUIDE.md`, `TARGET_MODEL_SCHEMA_REFERENCE.md`, and the deployment docs. Repeats navigation at lines 228–255 and duplicates the proposal inventory at lines 118–204. | Area 1 rebuilds it as a complete map. |
| `docs/DIAGRAMS.md` (1397 lines) | Section numbers present: 1–9, 11, 12, 14–26. Sections 10 and 13 do not exist. Sections 1–3 and 11–12 are narrative, not diagrams. Section 12 spans lines 643–799. | Area 5 moves narrative out and renumbers. |
| `docs/USER_GUIDE.md:533` | `[docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md)` resolves to `docs/docs/CONFIGURATION_GUIDE.md`. | Area 1 fixes it; Area 5 audits the rest of the guide. |
| Link scan of five documents | Broken: `docs/README.md` → `proposals/future/AI_PROJECT_ADVISOR_PROPOSAL.md`, `proposals/future/COMMENT_PRESERVING_SAVE_PATH.md`, `proposals/future/COMMENT_PRESERVING_SAVE_PATH_IMPLEMENTATION_SKETCH.md`; `docs/USER_GUIDE.md` → `docs/CONFIGURATION_GUIDE.md`. `docs/proposals/future/` contains eight other files; the AI advisor material is now under `docs/proposals/SHAPESHIFTER_PROJECT_AI_ADVISOR/`. | These four links are the full verified broken set. This is new evidence; the original review listed only the `USER_GUIDE.md` link. |
| `git log --all --diff-filter=D` and `git ls-files` | No `DOCKER_TO_PODMAN_MIGRATION.md` was ever tracked or deleted. No `SUMMARY.md`, `INDEX.md`, or `QUICK_REFERENCE.md` is tracked in any branch. | Finding 3 is not reproducible. Do not spend edits on it. |
| `.github/workflows/` | Contains only `release.yml` (semantic-release). No push or PR test workflow exists. | A CI link check would require a new workflow. Makefile integration is the in-scope guard. |
| `Makefile:77` | `lint: tidy ruff pylint check-target-model-schema-reference`. | The link check joins this dependency list. |
| `container/Containerfile` | Builds the frontend from `frontend/` itself. | `frontend/Dockerfile` is not part of this phase; see Open Questions. |

---

## Scope

**In scope**

- `README.md`, `docs/README.md`, `docs/OPERATIONS.md`, `docs/USER_GUIDE.md`, `docs/DIAGRAMS.md`
- Removal of `docker/`
- Root `Makefile` docker hooks
- `.github/instructions/readme.instructions.md`, `.github/instructions/operations.instructions.md`
- `scripts/check_doc_links.sh` (new) and its `Makefile` wiring
- A short note in `docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md` marking its `docker/` line references as historical, so they are not read as current

**Out of scope**

- Application code, tests, runtime configuration, `backend/app/core/config.py`
- `container/` implementation defects; both recorded here are resolved in the current tree: `podman-compose.yml` derives `env_file` from `CONTAINER_DATA_DIR`, and `resources/backend.env.example` uses `SHAPE_SHIFTER_*` names
- `frontend/Dockerfile` and `docker/`-era security findings; `docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md` owns those
- `docs/archive/` and `docs/features/`
- Any restructuring of `docs/CONFIGURATION_GUIDE.md`, `docs/DESIGN.md`, `docs/DEVELOPMENT.md`, or `docs/TESTING.md` beyond link repair

---

## Work Breakdown

### Area 1: Repair documentation navigation

**Objective:** Every relative link in the reviewed documents resolves, and `docs/README.md` is a complete documentation map.

**Affected files:** `docs/README.md`, `docs/USER_GUIDE.md`, `docs/proposals/future/`, `docs/proposals/SHAPESHIFTER_PROJECT_AI_ADVISOR/`

**Dependencies:** None. Independent of Areas 2–6, except `T1.6`, which runs last.

**Tasks**

- [ ] `T1.1` **Fix:** Correct the broken link at `docs/USER_GUIDE.md:533`.
  - **Target:** `docs/USER_GUIDE.md`, section 7 (fixed entities).
  - **Current → required:** `[docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md)` → `[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)`, because the page lives in `docs/`.
  - **Implementation:** Single-link edit. Do not change surrounding prose.
  - **Validation:** `V-1`; the scan reports no `docs/USER_GUIDE.md` entries.

- [ ] `T1.2` **Fix:** Correct the three broken proposal links in `docs/README.md`.
  - **Target:** `docs/README.md`, "Future proposals" list.
  - **Current → required:** links to `proposals/future/AI_PROJECT_ADVISOR_PROPOSAL.md`, `proposals/future/COMMENT_PRESERVING_SAVE_PATH.md`, and `proposals/future/COMMENT_PRESERVING_SAVE_PATH_IMPLEMENTATION_SKETCH.md` → existing targets under `docs/proposals/`, or removal of the rows.
  - **Implementation:** For the AI advisor, point at the existing `proposals/SHAPESHIFTER_PROJECT_AI_ADVISOR/` directory. For the two comment-preserving entries, confirm the current location under `docs/proposals/` and repoint; if no file exists, remove the rows instead of leaving dangling references. `T6.1` replaces the whole inventory, so keep this edit minimal.
  - **Validation:** `V-1` reports zero broken links in `docs/README.md`.

- [ ] `T1.3` **Document:** Record finding 3 as not reproducible.
  - **Target:** this task plan, `Acceptance-Criteria Coverage` and `Risks And Open Questions`.
  - **Current → required:** finding 3 is unreviewed → finding 3 is closed with evidence.
  - **Implementation:** No further action. The evidence is in `Repository Findings`. Do not create a `DOCKER_TO_PODMAN_MIGRATION.md` link fix task.
  - **Validation:** `V-8`.

- [ ] `T1.4` **Decide:** Classify `docs/REQUIREMENTS.md`.
  - **Target:** `docs/REQUIREMENTS.md`, `docs/README.md`, `docs/archive/`.
  - **Current → required:** listed in `docs/README.md` with a scope claim that overlaps `DESIGN.md` and `USER_GUIDE.md` → either retained and listed accurately, or moved to `docs/archive/` with an archive note.
  - **Implementation:** Choose one outcome and apply it. Retain it if it is still maintained; otherwise move it and add an archive note using the shape required by `.github/instructions/proposal-document-structure.instructions.md`. Record the chosen outcome in the Progress Tracker notes.
  - **Validation:** `V-1`, `V-8`.

- [ ] `T1.5` **Rewrite:** `docs/README.md` as a documentation map.
  - **Target:** `docs/README.md` (302 lines).
  - **Current → required:** a catalog with a duplicated proposal inventory, repeated navigation, version history, and missing documents → a map with one row per active document and no duplicated inventory.
  - **Implementation:** Delete the proposal inventory at lines 118–204 and replace it with links to `proposals/`, `proposals/future/`, `proposals/done/`, `proposals/onhold/`. Merge `Quick Navigation` (228–255) into the map. Delete `Version History` (278–290) and the `Last Updated` footer. Add the missing documents: `DIAGRAMS.md`, `GLOSSARY.md`, `SQL_SAFETY_POLICY.md`, `TARGET_MODEL_GUIDE.md`, `TARGET_MODEL_SCHEMA_REFERENCE.md`, `container/README.md`, `container/DEPLOYMENT.md`. Target under 150 lines.
  - **Constraints:** Keep `docs/README.md` in the same location with the same title. Do not move other documents.
  - **Validation:** `V-1`, `V-2`, `V-8`.

- [ ] `T1.6` **Add:** Documentation link check as a repeatable command.
  - **Target:** `scripts/check_doc_links.sh` (`NEW`), root `Makefile:77` lint dependency list, `docs/DEVELOPMENT.md`.
  - **Current → required:** no automated link check exists; four broken links reached `main`-bound documentation → the scan runs from `make lint`.
  - **Implementation:** Add `NEW scripts/check_doc_links.sh` containing the verified scan used for `V-1`, excluding `docs/archive/` and `graphify-out/`, and exiting non-zero on a broken link. Add a `check-doc-links` target to the root `Makefile` and append it to the `lint` dependency list at line 77. Add one line to `docs/DEVELOPMENT.md` under its code-quality section. Do not add a new GitHub workflow; `release.yml` is release-only.
  - **Constraints:** Shell only, no new Python or Node dependency. Must be runnable from the repository root.
  - **Validation:** `V-1`, `V-7`.
  - **Dependencies:** Run after Areas 2–6, so the guard starts from a clean baseline.

**Completion evidence:** `scripts/check_doc_links.sh` exits 0, and `docs/README.md` lists every active document with one row each.

---

### Area 2: Retire the `docker/` deployment path

**Objective:** `docker/` is removed and no tracked file points at it.

**Affected files:** `docker/**`, `Makefile`, `.dockerignore`, `.github/instructions/`, `docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md`

**Dependencies:** `container/` must be committed first. Area 3 rewrites `docs/OPERATIONS.md`, which is the last inbound reference.

**Tasks**

- [ ] `T2.1` **Commit:** Add `container/` to version control.
  - **Target:** `container/` (currently untracked).
  - **Current → required:** the Podman deployment exists only in the working tree → it is tracked, so deleting `docker/` does not reduce deployment coverage.
  - **Implementation:** Commit `container/` as its own change before any deletion. Do not fold it into the documentation commit.
  - **Validation:** `V-3`; `git ls-files container/` returns the deployment files.
  - **Dependencies:** Blocks `T2.2`.

- [ ] `T2.2` **Remove:** Root `Makefile` docker hooks.
  - **Target:** `Makefile:337-349`.
  - **Current → required:** `DOCKER_DIR := ./docker`, `export DOCKER_DIR`, `include docker/Makefile`, and the `docker-patch-frontend` target (which calls `docker cp`) → the `Docker` section removed, with its replacement Podman recipes sourced from `container/Makefile` if any recipe is still needed.
  - **Implementation:** Delete lines 337–349. Confirm no other target depends on the removed recipes before deleting. If a frontend patch recipe is still useful, reimplement it against Podman rather than keeping the `docker cp` version.
  - **Constraints:** The root `Makefile` must still parse. `make help` is the cheapest parse check.
  - **Validation:** `V-2`, `V-5`.

- [ ] `T2.3` **Remove:** The `docker/` directory.
  - **Target:** `docker/.dockerignore`, `docker/BUILD_SCRIPT_GUIDE.md`, `docker/Dockerfile`, `docker/Makefile`, `docker/README.md`, `docker/build.sh`, `docker/deploy-to-sead-tools`, `docker/docker-compose.yml`, `docker/rsync-to-sead-tools`.
  - **Current → required:** present and linked → removed.
  - **Implementation:** Delete in a dedicated commit after `T2.1`, `T2.2`, `T2.4`, `T2.5`, and Area 3 and Area 4 have removed the inbound links. Use the terminal, not an editor tool, for file removal.
  - **Constraints:** Do not delete `frontend/Dockerfile`, `.dockerignore`, `Containerfile`, or `container/`.
  - **Validation:** `V-3`, `V-4`.

- [ ] `T2.4` **Update:** Agent instruction files that name `docker/` as a trusted source.
  - **Target:** `.github/instructions/operations.instructions.md:72,73,79`; `.github/instructions/readme.instructions.md:21,30,46`.
  - **Current → required:** trusted sources `docker/docker-compose.yml`, `docker/Dockerfile`, `docker/Makefile`, `docker/build.sh` and the README link list entry `docker/README.md` → `container/podman-compose.yml`, `container/Containerfile`, `container/Makefile`, `container/build.sh`, `container/README.md`.
  - **Implementation:** Update each path reference and the surrounding sentence. Keep the documents' purpose and structure unchanged.
  - **Validation:** `V-3`, `V-7`.

- [ ] `T2.5` **Annotate:** Historical `docker/` references in the security proposal.
  - **Target:** `docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md` (15 `docker` mentions, including lines 257, 257–263, 544, 553, 620, 639–640, 662–684, 708).
  - **Current → required:** path references read as current → a single note at the top of the file states that `docker/` paths record the state at review time and that `container/` is now the deployment path.
  - **Implementation:** Add one note. Do not rewrite the findings; they are a record of a review.
  - **Constraints:** Do not change any security finding, severity, or recommendation.
  - **Validation:** `V-8`; a reviewer confirms the note does not alter findings.

**Completion evidence:** `git grep -n 'docker/'` outside `docs/archive/`, `graphify-out/`, and `CHANGELOG.md` returns only the annotation added by `T2.5`.

---

### Area 3: Rewrite `docs/OPERATIONS.md` for the Podman deployment

**Objective:** `docs/OPERATIONS.md` describes the Podman deployment as the only supported path and stays inside its word budget.

**Affected files:** `docs/OPERATIONS.md`

**Dependencies:** Area 2 (`T2.1`–`T2.2`) for the final path and command names.

**Tasks**

- [ ] `T3.1` **Verify:** Confirm the current deployment topology.
  - **Target:** `container/DEPLOYMENT.md`, `container/README.md`, `container/Makefile`, `container/scripts/setup.sh`, `container/podman-compose.yml`.
  - **Current → required:** `docs/OPERATIONS.md:18` says production runs on the `sead-tools` host under the `sead` user at `/home/sead/sead-tools/sead_shape_shifter`; `container/DEPLOYMENT.md` documents per-environment users, `loginctl enable-linger`, systemd user services, and `container/scripts/deploy/` → one verified statement of the current topology.
  - **Implementation:** Read the `container/` sources and state only what they support. Delete the `sead-tools` description if it is superseded. Do not carry over `docker/data/` paths.
  - **Validation:** `V-4`; every named command exists in `container/Makefile`.

- [ ] `T3.2` **Update:** Paths, commands, and image handling.
  - **Target:** `docs/OPERATIONS.md:34, 101, 159, 161, 176, 200–296, 320–342, 367–398, 433–440, 463–472, 488–491, 534, 550, 559–560`.
  - **Current → required:** `docker/data/*`, `docker-compose.yml`, `docker compose exec shape-shifter …`, `make docker-build|docker-restart|docker-health|docker-ps|docker-logs` → `container-data/*`, `container/podman-compose.yml`, `podman exec shape-shifter …` or `make shell`, and the `container/Makefile` targets `build`, `restart`, `healthcheck`, `ps`, `logs`.
  - **Implementation:** Replace each path and command with the verified `container/` equivalent. `container/scripts/setup.sh` creates `../container-data/{projects,shared,logs,output,backups,tmp,.pgpass}` and `backend.env`; use that layout in the volume table. The container name remains `shape-shifter`, so `backend/app/scripts/authorization.py` commands keep the same module path and change only the `docker compose exec` prefix.
  - **Constraints:** Both `ops` and the container Makefile must agree; if they disagree, the Makefile and `setup.sh` win.
  - **Validation:** `V-3`, `V-4`.

- [ ] `T3.3` **Verify:** Rebuild the runtime environment variable table against `backend/app/core/config.py`.
  - **Target:** `docs/OPERATIONS.md` variable table (lines 36–60).
  - **Current → required:** variable names taken as given → each row confirmed against `backend/app/core/config.py:29-99`, including `SHAPE_SHIFTER_PROJECTS_DIR`, `SHAPE_SHIFTER_LOG_DIR`, `SHAPE_SHIFTER_GLOBAL_DATA_DIR`, `SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR`, and the `AUTHORIZATION_*` settings.
  - **Implementation:** Correct names and defaults to match `config.py`. Do not treat an env template as the definition: `container/resources/backend.env.example` uses `SHAPE_SHIFTER_*` names but is a starting point only. The `.env.example` name disagreement recorded earlier no longer applies.
  - **Validation:** `V-4`; a spot check of five rows against `config.py`.

- [ ] `T3.4` **Update:** Deployment flow, rollback, and references.
  - **Target:** `docs/OPERATIONS.md:367–472` and the references block at 555–564.
  - **Current → required:** `rsync-to-sead-tools`, `make build-and-deploy`, `GIT_REF=… make docker-build`, and the `docker/README.md` / `docker/BUILD_SCRIPT_GUIDE.md` reference rows → the `container/` equivalents, or removal where no equivalent exists.
  - **Implementation:** Replace rollback steps with the `container/Makefile` mechanism. Replace the reference rows with `container/README.md` and `container/DEPLOYMENT.md`. Keep `docs/DEVELOPMENT.md`, `docs/DESIGN.md`, and `AGENTS.md` rows.
  - **Constraints:** `.github/instructions/operations.instructions.md` requires the document to work as a concise overview with detail pushed to companion runbooks. Link to `container/DEPLOYMENT.md` rather than restating it.
  - **Validation:** `V-3`, `V-4`.

- [ ] `T3.5` **Reduce:** Trim to the 800–1800 word target.
  - **Target:** `docs/OPERATIONS.md` (3766 words).
  - **Current → required:** detail duplicated from companion runbooks → an overview plus pointers, per `.github/instructions/operations.instructions.md`.
  - **Implementation:** Move exceptional procedures into `container/DEPLOYMENT.md` or delete duplication. Keep deployment-agnostic content intact: the single-worker invariant, non-root container user, nginx authentication boundary, health-endpoint exception, file-backed project state, and no built-in TLS.
  - **Validation:** `V-2`.

**Completion evidence:** `docs/OPERATIONS.md` contains no `docker` or `docker compose` reference, stays between 800 and 1800 words, and every command it names exists in `container/Makefile`.

---

### Area 4: Trim root `README.md` to a front door

**Objective:** `README.md` orients a new visitor and links onward, inside the 100–250 line target.

**Affected files:** `README.md`

**Dependencies:** Area 2 and Area 3, for the deployment link target and the quick start wording.

**Tasks**

- [ ] `T4.1` **Rewrite:** Replace the Docker quick start with a Podman quick start.
  - **Target:** `README.md:67-88`.
  - **Current → required:** `cd sead_shape_shifter/docker`, `make setup`, `make docker-build`, `make docker-up`, and a link to `docker/README.md` → the `container/` directory, `make setup`, `make build`, `make up`, `make healthcheck`, and a link to `container/README.md`.
  - **Implementation:** Keep the section to five commands plus one URL, per `.github/instructions/readme.instructions.md`. State the default URL `http://localhost:8012/` and the health endpoint.
  - **Validation:** `V-3`, `V-4`.

- [ ] `T4.2` **Remove:** Developer installation and command sections.
  - **Target:** `README.md:90-220` (`Developer Installation`, `Installation Steps`, `Install UCanAccess`, `Running the Application`, `Development Commands`).
  - **Current → required:** a full setup walkthrough and a command catalog → a prerequisites list of four lines plus one link to `docs/DEVELOPMENT.md`.
  - **Implementation:** Keep Python version, Java/JRE for UCanAccess, `pnpm`, and the `.venv/` convention as prerequisites. Move the UCanAccess install script path and the Makefile command tables to `docs/DEVELOPMENT.md` if they are not already there; otherwise delete and link.
  - **Constraints:** `docs/DEVELOPMENT.md` is the owning document; do not duplicate its content.
  - **Validation:** `V-1`, `V-2`.

- [ ] `T4.3` **Remove:** CLI usage, YAML example, database integration, and FK constraint sections.
  - **Target:** `README.md:222-378` (`Usage`, `Command-Line Interface`, `Configuration Example`, `Database Integration`, `Foreign Key Constraints`).
  - **Current → required:** CLI option reference, entity YAML example, and constraint semantics → links to `docs/USER_GUIDE.md` and `docs/CONFIGURATION_GUIDE.md`.
  - **Implementation:** Confirm the CLI flags and the FK constraint reference already exist in those documents before deleting. If a flag is missing, add it there first. Note the malformed YAML example at lines 306–325: `options:` is followed by an `Identity note:` prose block that swallows the `data_sources:` block, and a second `options:` key follows at line 325. Do not carry this forward.
  - **Validation:** `V-1`; a diff review confirms nothing is deleted without an existing home.

- [ ] `T4.4` **Remove:** Architecture, testing, and contributing sections.
  - **Target:** `README.md:379-502` (`Architecture`, `Documentation`, `Testing`, `Contributing`, `Code Standards`, `Commit Message Format`).
  - **Current → required:** component deep-dive, test command catalog, and contributor rules → links to `docs/DESIGN.md`, `docs/TESTING.md`, `docs/DEVELOPMENT.md`, and `.github/instructions/`.
  - **Implementation:** Keep a short feature summary and one documentation table. Keep the license and acknowledgements sections. Reduce the documentation list to the entry points.
  - **Validation:** `V-1`, `V-2`.

**Completion evidence:** `README.md` is under 300 lines, begins with a one-paragraph description and prerequisites, contains a quick start of at most five commands, and links to every owning document.

---

### Area 5: Reduce duplication in `docs/DIAGRAMS.md` and `docs/USER_GUIDE.md`

**Objective:** Both documents contain only the material they own.

**Affected files:** `docs/DIAGRAMS.md`, `docs/USER_GUIDE.md`, `docs/DESIGN.md`

**Dependencies:** Area 1 (`T1.1`, `T1.5`); sequencing only.

**Tasks**

- [ ] `T5.1` **Move:** Narrative sections out of `docs/DIAGRAMS.md`.
  - **Target:** `docs/DIAGRAMS.md` sections 1–3 (lines 7–144) and 11–12 (lines 543–799).
  - **Current → required:** problem statement, solution overview, user workflow, key features, and use-case map presented as diagrams → product narrative in `docs/DESIGN.md` and workflow narrative in `docs/USER_GUIDE.md`, leaving short summary lines and links.
  - **Implementation:** Preserve every diagram that carries visual information. Move or delete prose only. Apply `.github/instructions/diagrams.instructions.md` while editing.
  - **Constraints:** Do not restructure `docs/DESIGN.md` beyond appending an owning section; preserve its existing structure.
  - **Validation:** `V-2`, `V-6`.

- [ ] `T5.2` **Renumber:** Fix the section sequence.
  - **Target:** `docs/DIAGRAMS.md` headings.
  - **Current → required:** sections 1–9, 11, 12, 14–26 with no sections 10 and 13 → a continuous sequence with no gaps.
  - **Implementation:** Renumber headings and any in-document cross-references after `T5.1` settles the final set. Confirm sections 10 and 13 were not lost content; `Repository Findings` reports no such headings, so treat them as never written.
  - **Validation:** `V-6`; heading extraction shows a continuous 1..N sequence.

- [ ] `T5.3` **Trim:** Captions and length.
  - **Target:** `docs/DIAGRAMS.md` (1397 lines, 3549 words).
  - **Current → required:** diagrams mixed with explanatory prose → diagrams with one- to two-sentence captions.
  - **Implementation:** Keep technical sequence and state diagrams (sections 14–26 in the current numbering): project load, entity preview, validation, execution, save, refresh, entity editing state, preview cache state, validation result state, technology stack, deployment architecture, registry pattern. Update the deployment architecture diagram to Podman.
  - **Constraints:** Do not remove a diagram that has no equivalent elsewhere.
  - **Validation:** `V-2`, `V-6`.

- [ ] `T5.4` **Audit:** `docs/USER_GUIDE.md` for YAML semantics owned by the configuration guide.
  - **Target:** `docs/USER_GUIDE.md` (1174 lines), starting with the fixed-entity section around line 493.
  - **Current → required:** exact YAML field semantics explained in the user guide → short workflow explanation plus a link.
  - **Implementation:** `.github/instructions/user-guide.instructions.md` says not to include a YAML schema reference. Keep the workflow framing and the reason a user edits the field; replace the field-by-field semantics with a link to the corresponding `docs/CONFIGURATION_GUIDE.md` section. Preserve the guide's existing structure; do not reorganize sections.
  - **Constraints:** Every removed YAML explanation must already exist in `docs/CONFIGURATION_GUIDE.md`. Verify before deleting; add it there first if missing.
  - **Validation:** `V-1`, `V-6`.

**Completion evidence:** `docs/DIAGRAMS.md` has a continuous section sequence with captions only, and `docs/USER_GUIDE.md` links to the configuration guide instead of restating field semantics.

---

### Area 6: Confirm no behaviour changed

**Objective:** Provide evidence that the phase changed documentation and build entry points only.

**Affected files:** none

**Dependencies:** Areas 1–5.

**Tasks**

- [ ] `T6.1` **Confirm:** Review the complete diff for unintended changes.
  - **Target:** the full phase diff.
  - **Current → required:** unknown → confirmed that no file under `src/`, `backend/app/`, `frontend/src/`, `ingesters/`, or `tests/` changed, and that no runtime setting changed.
  - **Implementation:** Inspect `git diff --name-only` against the expected file list in Scope. Confirm `container/` and `docker/` changes are limited to the planned edits.
  - **Validation:** `V-8`.

- [ ] `T6.2` **Confirm:** Verify the Makefile still parses after `T2.2`.
  - **Target:** root `Makefile`.
  - **Current → required:** an include of a deleted file → a self-contained `Makefile`.
  - **Implementation:** Run `make help` and confirm exit code 0.
  - **Validation:** `V-5`.

**Completion evidence:** `git diff --name-only` matches Scope, and `make help` exits 0.

---

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` | `T4.1`, `T4.2`, `T4.3`, `T4.4` | `V-1`, `V-2` | `README.md` under 300 lines, no setup, deployment, CLI, YAML, or architecture content |
| `PH1-AC-2` | `T3.1`, `T3.2`, `T3.3`, `T3.4`, `T3.5` | `V-2`, `V-3`, `V-4` | Zero `docker` matches in `docs/OPERATIONS.md`; word count within 800–1800 |
| `PH1-AC-3` | `T1.1`, `T1.2`, `T1.3`, `T1.5` | `V-1`, `V-8` | Link scan reports zero broken links; finding 3 recorded as not reproducible |
| `PH1-AC-4` | `T5.4`, `T1.1` | `V-1`, `V-6` | No YAML semantics retained in `docs/USER_GUIDE.md`; no broken links |
| `PH1-AC-5` | `T5.1`, `T5.2`, `T5.3` | `V-2`, `V-6` | Continuous section sequence; narrative removed; reduced line count |
| `PH1-AC-6` | `T1.5`, `T1.4` | `V-1`, `V-2`, `V-8` | One row per active document; no proposal inventory; all active documents listed |
| `PH1-AC-7` | `T1.6`, `T2.2`, `T2.3`, `T2.4` | `V-3`, `V-5`, `V-7` | `make check-doc-links` exists and passes; no `docker/` references outside `docs/archive/` and `CHANGELOG.md` |

---

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Relative link resolution across reviewed documents | `scripts/check_doc_links.sh` (`NEW`); before it exists, run the scan recorded in `Repository Findings` | `PH1-AC-1`, `PH1-AC-3`, `PH1-AC-4`, `PH1-AC-6` | Zero broken links | Fail: 4 broken links (`docs/README.md` ×3, `docs/USER_GUIDE.md` ×1) |
| `V-2` | Document size against instruction targets | `wc -l README.md docs/README.md docs/DIAGRAMS.md && wc -w docs/OPERATIONS.md` | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-5`, `PH1-AC-6` | `README.md` < 300 lines; `docs/README.md` < 150 lines; `docs/DIAGRAMS.md` reduced; `docs/OPERATIONS.md` 800–1800 words | Fail: 502 / 302 / 1397 lines; 3766 words |
| `V-3` | No retired `docker/` references | `git grep -n -iE 'docker/' -- ':!graphify-out' ':!CHANGELOG.md' ':!docs/archive' ':!docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md'` | `PH1-AC-2`, `PH1-AC-7` | No matches | Fail: 60 matches in `docs/OPERATIONS.md`, 6 in `README.md`, plus instruction files |
| `V-4` | Every named command and path exists | Cross-check each command in `docs/OPERATIONS.md` and `README.md` against `container/Makefile` and `container/scripts/` | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-7` | Every named target and path exists | Not run: no prior claim to verify |
| `V-5` | Root `Makefile` parses after include removal | `make help` | `PH1-AC-7` | Exit code 0, help text printed | Pass: `make help` currently works |
| `V-6` | Diagram and user-guide content ownership | Manual review against `.github/instructions/diagrams.instructions.md` and `.github/instructions/user-guide.instructions.md`; heading extraction for numbering | `PH1-AC-4`, `PH1-AC-5` | Continuous numbering; no narrative sections; no YAML semantics | Fail: sections 10 and 13 missing; sections 1–3 and 11–12 are narrative |
| `V-7` | Instruction files point at existing sources | Read `.github/instructions/operations.instructions.md` and `.github/instructions/readme.instructions.md`; confirm each named path exists | `PH1-AC-7` | Every named path resolves | Fail: 5 `docker/` path references across 2 instruction files |
| `V-8` | Scope containment | `git diff --name-only` compared against Scope | `PH1-AC-3`, `PH1-AC-6`, `PH1-AC-7` | Only documentation, instruction, and build-entry-point files changed | Not run: no changes yet |

No unit, integration, or contract test run is required. This phase changes no code path, contract, schema, or migration.

---

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Repaired links | Four verified broken relative links corrected | Not started | `README.md`, `docs/README.md`, `docs/USER_GUIDE.md` |
| Documentation map | `docs/README.md` rebuilt with one row per active document | Not started | `docs/README.md` |
| Link-check script | New shell script plus `make check-doc-links`, wired into `lint` | Not started | `scripts/check_doc_links.sh` (`NEW`), `Makefile` |
| Podman operations guide | `docs/OPERATIONS.md` rewritten for `container/` | Not started | `docs/OPERATIONS.md` |
| Trimmed front door | `README.md` reduced to overview, prerequisites, quick start, and links | Not started | `README.md` |
| Narrowed diagrams | Narrative moved out, numbering fixed, captions only | Not started | `docs/DIAGRAMS.md` |
| De-duplicated user guide | YAML semantics replaced by links to the configuration guide | Not started | `docs/USER_GUIDE.md` |
| Retired Docker path | `docker/` deleted with `Makefile` and instruction files updated | Not started | `docker/`, `Makefile`, `.github/instructions/` |

---

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| 1. Documentation navigation | Not started | `T1.4` outcome (retain or archive `REQUIREMENTS.md`) recorded here when decided |
| 2. `docker/` retirement | Not started | `T2.1` (commit `container/`) must complete before `T2.3` (delete `docker/`) |
| 3. `docs/OPERATIONS.md` rewrite | Not started | Depends on Area 2 for final path and command names |
| 4. Root `README.md` trim | Not started | Depends on Areas 2 and 3 for deployment wording |
| 5. Duplication reduction | Not started | Independent of Areas 2–4 |
| 6. Scope confirmation | Not started | Runs last |

---

## Definition Of Done

- [ ] Every `PH1-AC-*` criterion is satisfied and its evidence is recorded.
- [ ] `V-1` passes with zero broken links, and `scripts/check_doc_links.sh` is wired into `make lint`.
- [ ] `V-2` passes against the size targets for `README.md`, `docs/README.md`, `docs/DIAGRAMS.md`, and `docs/OPERATIONS.md`.
- [ ] `V-3` returns no `docker/` references outside `docs/archive/`, `CHANGELOG.md`, and the annotated security proposal.
- [ ] `V-4` confirms every command and path named in `README.md` and `docs/OPERATIONS.md` exists under `container/`.
- [ ] `V-5` confirms `make help` exits 0 after the `docker/Makefile` include is removed.
- [ ] `V-6` confirms diagram numbering is continuous and no document explains content owned by another document.
- [ ] `V-7` confirms both edited instruction files name only existing paths.
- [ ] `V-8` confirms the diff contains no application, test, or runtime configuration changes.
- [ ] Finding 3 is closed as not reproducible with the evidence recorded.
- [ ] New follow-up work created by this phase is recorded. The two items previously listed here are resolved in the current tree (`podman-compose.yml` `env_file` path, and `resources/backend.env.example` variable names), so no follow-up is needed for them.

---

## Risks And Open Questions

**Risks and mitigations**

| Risk | Mitigation |
|---|---|
| Deleting `docker/` removes the only deployment path if `container/` is incomplete or unverified. | Commit `container/` first (`T2.1`) and delete `docker/` in a dedicated commit (`T2.3`) so it can be reverted independently. |
| `container/podman-compose.yml:40` points `env_file` at `./data/backend.env`, but `setup.sh` and the volume mounts use `../container-data/backend.env`. | Out of scope for this phase. Record it as follow-up before `T3.2` documents the path, and document the path that `setup.sh` and the volume mounts use. |
| ~~`container/.env.example` uses unprefixed variable names~~ | Resolved: the runtime template is `container/resources/backend.env.example` and it uses `SHAPE_SHIFTER_*` names. `T3.3` still verifies the operations table against `backend/app/core/config.py`. |
| Moving narrative out of `docs/DIAGRAMS.md` loses information that exists nowhere else. | `T5.1` requires moving prose to its owning document, not deleting it. `V-6` verifies ownership rather than absence. |
| `docs/OPERATIONS.md` content is deleted without a home when trimming to the word target. | Move detail to `container/DEPLOYMENT.md`. Keep the deployment-agnostic invariants listed in `T3.5` in place. |

**Open questions**

1. Should a push or PR workflow be added for the link check? `.github/workflows/` contains only `release.yml`, which performs semantic release. `T1.6` wires the check into `make lint` only; CI enforcement needs a new workflow.
2. Is `frontend/Dockerfile` also retired? `container/Containerfile` builds the frontend itself, and `docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md:708` already records it as a stale standalone build. It is out of scope here, and that proposal owns the finding.
3. Should `docs/GLOSSARY.md`, `docs/SQL_SAFETY_POLICY.md`, and the target model guides be reviewed for the same scope and duplication problems? They were not part of the original review and are not in scope.
