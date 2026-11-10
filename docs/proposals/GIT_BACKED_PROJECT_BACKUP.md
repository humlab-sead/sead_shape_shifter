# Git-Backed Project Backups

## Status

- Proposed feature
- Scope: backend backup layer, project write boundaries, backup/restore API, container runtime image
- Goal: add a selectable per-project git repository backup backend that records every project file state, while keeping the current file-copy backup as the default

Related: [Proposal index](README.md)

## Summary

Add a `BackupBackend` abstraction with two implementations: the current file-copy backend and a new git backend. Each project directory becomes its own local git repository. Mutating operations (config save, boundary save, entity add/update/delete, file upload/delete, materialization, restore) commit the resulting project state with generated commit metadata. The existing `backups/` file copy remains the default and is unchanged.

The gain is versioned project state: `shapeshifter.yml`, task and mapping sidecars, and uploaded source data files in one history, with configuration restore from any recorded revision and diffs available through standard git tooling. Derived `materialized/` output and the file backend's own `backups/` are excluded by default, so repository growth follows source changes rather than regenerated data.

## Problem

The current backup writes a copy of one file before it is overwritten.

- `YamlService.create_backup()` copies a single file into `<project_dir>/backups/` as `shapeshifter.backup.<timestamp>.yml`; `save()`, `save_commented()`, and `merge_boundary()` call it by default.
- Sidecar writes pass `create_backup=False` in `ProjectService.save_project()` and `save_entity_rename_boundary()`, so `shapeshifter.tasks.yml` is never backed up.
- Uploaded data files, `materialized/` output, and mapping/reconciliation sidecars are not backed up at all. They are written by other services without touching the backup path.
- A backup is an independent snapshot of one file. There is no link between the config state and the data files that existed at that moment, so a project cannot be reconstructed to a known point in time.

Operators therefore cannot answer "what did this project look like before this change?" for anything except the config YAML, and cannot diff or export project history.

## Scope

- A backup backend interface with a file-copy implementation and a git implementation.
- Backend selection through configuration, defaulting to the current behavior.
- Recording a commit at the mutating-operation boundary so one user action produces one commit.
- A default tracked set of project source files: config, sidecars, and uploaded source data. Derived `materialized/` output is opt-in.
- A configured repository size threshold that warns instead of silently pruning.
- Initializing a repository on first write and a fresh repository for a copied project.
- Serving revision listing and config restore from the active backend through the existing project backup endpoints.
- A runtime prerequisite check for the `git` executable.

## Non-Goals

- No remote git hosting, pushing, or synchronization with external repositories.
- No change to the root `backups/` directory used for authorization database backups.
- No automatic pruning, squashing, or history rewriting. History is append-only, and an operator applies the documented compaction step when a repository grows large.
- No new UI beyond adapting the existing Backups dialog to the active backend.
- No per-project mixing of backends in the first delivery.
- No full-tree restore through the UI in the first delivery.

## Current Behavior

Verified in the current code:

| Area | Current behavior |
| --- | --- |
| Backup creation | `YamlService.create_backup()` copies one file into `<project_dir>/backups/` with a microsecond timestamp name. |
| Save paths | `ProjectService.save_project()`, `save_metadata_boundary()`, `save_entity_boundary()`, and `save_options_boundary()` reach `YamlService` writes that back up the config file. |
| Sidecar | `save_project()` and `save_entity_rename_boundary()` save `shapeshifter.tasks.yml` with `create_backup=False`. |
| Other project files | Uploaded files are stored in the project directory itself; materialized files are written under `materialized/`. Neither is backed up. |
| Project delete | `ProjectOperations.delete_project()` zips the whole project directory into `PROJECTS_DIR/archived/<name>_<timestamp>.zip`, then removes the directory. |
| Project copy | `ProjectOperations.copy_project()` copies the whole project directory with `shutil.copytree`. |
| Listing API | `GET /api/v1/projects/{name}/backups` returns `BackupInfo{file_name, created_at}` for `shapeshifter.backup.*.yml` only. |
| Restore API | `POST /api/v1/projects/{name}/restore` takes a backup file name, validates the YAML, backs up the current file, and copies the backup over `shapeshifter.yml`. |
| Frontend | The Backups dialog lists `file_name` and `created_at` and restores by file name. |
| Concurrency | Mutating project operations hold a per-project `threading.Lock` in `ProjectService`. |
| Runtime image | The production stage of `deployment/container/Containerfile` installs `default-jre-headless` and `libpq5` only; `git` is not present. |

Delete and copy both operate on the whole directory. A project-local `.git` therefore already travels inside the delete archive, and it would be carried into a copied project unless the copy path handles it.

## Proposed Design

### Backend abstraction

Introduce a small interface under `backend/app/services/project/`:

```python
class BackupBackend(Protocol):
    def ensure_repository(self, project_dir: Path) -> None: ...
    def record(self, project_dir: Path, event: BackupEvent) -> None: ...
    def list_revisions(self, project_dir: Path) -> list[BackupRecord]: ...
    def restore_config(self, project_dir: Path, revision: str) -> None: ...
```

- `ensure_repository()` runs before a mutating operation and captures a baseline commit of the current on-disk state when a backend needs one.
- `record()` runs after the operation's writes succeed and commits the resulting state.
- `FileCopyBackupBackend` keeps today's copy-on-write behavior and treats each backup file name as the revision identifier.
- `GitBackupBackend` implements all four methods against a repository rooted at the project directory.

The backend is selected once in settings and resolved by a factory. `YamlService` keeps its current responsibility for single-file backup; the backend is called from the operation boundary instead, so multi-file operations produce one consistent commit.

Implementation uses the `git` executable through `subprocess.run([...], check=True)` against `git -C <project_dir>`. This avoids a new Python dependency.

### Project repository layout

- Repository root: `PROJECTS_DIR/<project_path>/`.
- Tracked by default: `shapeshifter.yml`, `shapeshifter.tasks.yml`, the mapping/reconciliation sidecar, and uploaded source data files.
- Excluded by default: `backups/`, which holds the file backend's output, and `materialized/`, which holds derived data that the project can regenerate.
- Tracking materialized output is opt-in through `PROJECT_BACKUP_GIT_TRACK_MATERIALIZED`. Enabling it commits derived data and accepts the matching growth cost.
- A `.gitignore` is created only when absent and contains the configured ignore patterns. An existing file is never rewritten.
- Repository-local configuration sets `user.name`, `user.email`, and `core.autocrlf=false`, so commits do not depend on host git configuration.
- A repository is initialized on the first mutating operation, not on project load, so reading a project still does not modify it.

### Recording changes

- `ensure_repository()` and `record()` are called inside the existing per-project lock, around the write, at these boundaries: `ProjectOperations` save/create/copy/delete, `EntityOperations` add/update/delete/rename, `ProjectService` metadata/options/entity boundary saves, file upload/delete/promote paths, and materialization persistence when materialized tracking is enabled.
- `record()` stages with `git add -A -- .` and skips the commit when `git status --porcelain` is empty, so no-op operations create no commit.
- One operation produces one commit. The commit message uses a fixed two-part shape:

```text
<operation>: <subject>

Operation: entity.update
Principal: <principal id>
Correlation-Id: <request correlation id>
```

- Operation keys are stable identifiers such as `project.save`, `project.restore`, `entity.add`, `entity.update`, `entity.delete`, `entity.rename`, `files.upload`, `files.delete`, `materialize.sync`.
- Restore writes the restored config file and then records a `project.restore` commit, so restoring never rewrites or discards history.

### Delete, copy, and archive

- Delete keeps the repository inside the archive zip that the delete path already creates. The archive is the retention mechanism for project history, so `.git` must not be added to any archive exclusion pattern.
- Copy removes the copied `.git` directory and initializes a fresh repository for the target project, then records an initial commit that names the source project. A copy therefore starts its own history instead of inheriting the source history.
- Recovery of a deleted project means extracting its archive and reopening the extracted directory as a project.

### Revision listing and restore

- Both endpoints keep their paths and behavior contract.
- `GET /projects/{name}/backups` returns revisions newest first from the active backend. `BackupInfo` gains three optional fields: `revision`, `author`, and `message`. `file_name` carries the backend revision identifier: the backup file name for the file backend and the full commit SHA for the git backend. The field name is retained for API and frontend compatibility.
- `POST /projects/{name}/restore` accepts a revision identifier in the existing request field, resolves it through the active backend, and restores only `shapeshifter.yml`. Metadata validation and the pre-restore backup stay as they are today.
- File-level and full-tree recovery for data files stays outside the application: an operator uses `git log`, `git diff`, and `git checkout` in the project directory.

### Configuration

New settings in `backend/app/core/config.py`:

| Setting | Default | Purpose |
| --- | --- | --- |
| `PROJECT_BACKUP_BACKEND` | `file` | Selects `file` or `git`. |
| `PROJECT_BACKUP_GIT_AUTHOR_NAME` | `Shape Shifter` | Repository-local `user.name`. |
| `PROJECT_BACKUP_GIT_AUTHOR_EMAIL` | `shape-shifter@localhost` | Repository-local `user.email`. |
| `PROJECT_BACKUP_GIT_IGNORE` | `backups/` | Additional ignore patterns written to a new `.gitignore`. |
| `PROJECT_BACKUP_GIT_TRACK_MATERIALIZED` | `false` | Includes `materialized/` in the tracked set. |
| `PROJECT_BACKUP_GIT_MAX_REPOSITORY_MB` | `512` | Size above which a warning is logged for each recorded operation. |

When `PROJECT_BACKUP_BACKEND=file`, behavior is identical to today.

### Failure handling and growth

- A backup failure does not fail the user's write. The write already succeeded, so returning an error would misreport the project state. The failure is logged at error level with project, operation, and correlation id.
- There is no health-status surface for project backups in the first delivery. Operators read failures from the application log.
- Startup fails with a clear configuration error when `PROJECT_BACKUP_BACKEND=git` and `git` cannot be executed.
- Repository size above `PROJECT_BACKUP_GIT_MAX_REPOSITORY_MB` logs a warning on each recorded operation. Recording continues; no commit is dropped, squashed, or rewritten by the application.
- Operator maintenance uses standard git tooling, for example `git gc` inside the project directory. The application never rewrites history.

### Runtime prerequisites

- Add `git` to the production stage of `deployment/container/Containerfile`.
- Document that a host running the git backend needs `git` on `PATH`.
- Keep the single-process assumption: `ProjectService` locks and repository initialization assume one application process per project directory. The container command runs uvicorn with `--workers 1`; multiple workers or hosts over a shared project directory are not supported.

## Alternatives Considered

| Alternative | Why not chosen |
| --- | --- |
| Extend the current file copy to cover every file | Produces many timestamped copies with no shared point-in-time relationship, no diffs, and unbounded disk growth against large binary data files. |
| Call the git backend from `YamlService` writes | One user action performs several writes (config plus sidecar), so this yields multiple partial commits and a history that does not match user actions. |
| Use a library such as GitPython or dulwich | Adds a dependency for a narrow command set; the `git` CLI already has to exist for operational inspection. |
| Commit from a host cron job instead of the application | Covers most file churn with no application change, but produces anonymous commits on an arbitrary interval that split or merge user actions, and it duplicates project-path knowledge outside the application. It cannot record which principal and which operation produced a change. |
| Make the git backend the default | Changes disk layout and deployment prerequisites for existing installations that do not need history; the default must stay compatible. |
| Store history in a single repository outside the project directories | Loses the simple per-project ownership and containment rules, and complicates delete/copy/archive behavior. |
| Push to a remote repository | Introduces credentials, network failure modes, and cross-host state that are out of scope for a local backup backend. |

## Risks And Tradeoffs

- **Repository growth.** Committing binary source data files makes the project repository grow with every changed file version. Mitigation: source-only tracked set, `materialized/` opt-in, and a size threshold that warns. Large data-file churn remains a real cost and must be accepted deliberately, because history is append-only.
- **Incomplete history on failure.** A failed commit leaves the file saved but unrecorded. Mitigation: error log with correlation id, and the next successful operation records the accumulated difference in one commit.
- **History lives in a zip after deletion.** A deleted project's repository survives only inside `archived/<name>_<timestamp>.zip`. Mitigation: documented as the retention path; recovering history requires extracting the archive rather than reading a live directory.
- **Inherited history on copy.** Without the copy step, a copied project would carry the source history and invite confusion about which project a commit belongs to. Mitigation: the copy path starts a fresh repository.
- **Restore scope.** Restoring only `shapeshifter.yml` can leave data files newer than the restored config. This is stated in operator documentation; full-tree restore is deliberately manual.
- **Locking.** Git's `index.lock` and the application's per-project lock overlap but are not the same guard. A crashed process can leave `index.lock` behind and block later commits until it is removed.
- **Runtime dependency.** The git backend fails on hosts and images without `git`. The startup check converts this from a silent no-op into an explicit configuration error.
- **Backup of a backup.** `backups/` must be ignored, otherwise every git commit would embed a copy of the file backend's snapshots.

## Testing And Validation

- Unit tests for `GitBackupBackend` against a temporary project directory: initialization, baseline commit, no-op commit suppression, ignore handling, commit metadata, revision listing order, and config restore from a revision.
- Unit tests for `FileCopyBackupBackend` parity: the same interface calls produce today's file names, listing order, and restore behavior.
- Service tests asserting one commit per mutating operation, that the sidecar and uploaded file appear in that commit, and that `materialized/` stays untracked unless the setting enables it.
- Delete and copy tests: a deleted project's archive contains `.git`, and a copied project starts a repository with no inherited history.
- Endpoint tests for `GET /projects/{name}/backups` and `POST /projects/{name}/restore` with both backends, including unknown revision handling.
- Failure-path tests: `git` missing at startup, commit failure logged without failing the save, the size threshold warning, and restore validation rejecting invalid YAML.
- A container check that `git --version` succeeds in the production image.
- A manual check on one existing project: apply an entity edit, a task-list change, and a file upload, then confirm three commits and a working restore of `shapeshifter.yml`.

Tests that need the `git` executable are skipped with a clear marker when it is unavailable, rather than silently passing.

## Acceptance Criteria

- `P-AC-1` With `PROJECT_BACKUP_BACKEND=file`, backup creation, listing, restore, and file names are unchanged from current behavior.
- `P-AC-2` With `PROJECT_BACKUP_BACKEND=git`, the first mutating operation creates a repository rooted at the project directory and records `shapeshifter.yml`, `shapeshifter.tasks.yml`, the mapping sidecar, and uploaded source data files, while `backups/` and `materialized/` stay untracked by default.
- `P-AC-3` One mutating operation produces at most one commit, an operation that changes no tracked file produces no commit, and each commit identifies the operation, principal, and correlation id.
- `P-AC-4` `GET /api/v1/projects/{name}/backups` lists revisions newest first from the active backend, identifies each through `BackupInfo.file_name`, and fills `revision`, `author`, and `message` for git revisions.
- `P-AC-5` `POST /api/v1/projects/{name}/restore` restores `shapeshifter.yml` from a selected git revision after the same metadata validation used today, and the restore is itself recorded as a new commit.
- `P-AC-6` A backup failure is logged with project, operation, and correlation id and never fails a project write that already completed.
- `P-AC-7` Startup fails with a clear configuration error when the git backend is selected and the `git` executable is unavailable.
- `P-AC-8` The production image contains the `git` executable.
- `P-AC-9` Deleting a project leaves its repository inside the archive zip, and copying a project starts the copy with a fresh repository and no inherited history.
- `P-AC-10` A repository above `PROJECT_BACKUP_GIT_MAX_REPOSITORY_MB` produces a warning and continues recording; no commit is dropped, squashed, or rewritten.

## Planning Handoff

Confirmed decisions for phase planning:

- The default backend stays `file`; the git backend is opt-in through `PROJECT_BACKUP_BACKEND`.
- One repository per project directory; `backups/` is always ignored and `materialized/` is ignored by default.
- The default tracked set is project source files only: config, sidecars, and uploaded source data.
- Commits are recorded at the operation boundary inside the existing per-project lock, not inside `YamlService`.
- The git backend uses the `git` CLI, not a Python git library.
- The existing backup endpoints and `BackupInfo` shape are extended; no replacement endpoints.
- Restore covers `shapeshifter.yml` only and is itself committed.
- Delete retains history through the existing archive zip; copy starts a fresh repository.
- Growth is bounded by a warning threshold and documented operator maintenance, not by automatic pruning.
- Backup failure never fails a completed project write, and there is no project-backup health surface.
- History is append-only.

Constraints and behavior to preserve:

- Read-only project operations must not create `.git` or modify project files.
- Per-project lock ordering and current `create_backup` defaults must not change for the file backend.
- YAML validation and provider-binding validation must still run before any restore write.
- All project paths stay inside `PROJECTS_DIR` through `resolve_contained_path`.
- Existing frontend calls must keep working without a coordinated frontend release.

Expected validation outcomes:

- Parity tests prove the file backend behavior is unchanged.
- Git backend tests prove source-file coverage, one-commit-per-operation, and correct delete/copy behavior.
- Container validation proves `git` is present in the runtime image.

Open questions and the phase by which each must be resolved:

| Question | Resolve by |
| --- | --- |
| Should individual files be restorable through the API, or is operator `git checkout` sufficient for data files? | Before the restore phase |
| Should the git backend record writes outside the project directory, such as promoting a file to shared data? | Before the recording phase |
| Is a per-project backend override in project metadata needed? | Before the configuration phase |

## Open Questions

- Does any deployment keep `PROJECTS_DIR` on a network filesystem shared by more than one host? If so, git index locking must be addressed before the git backend is enabled there.
- Should a `.gitattributes` be generated for binary data files to keep diffs and text conversion predictable?
- Is an operator-facing wrapper needed around `git gc` for project repositories, or is the documented command sufficient?

## Final Recommendation

Implement the git backend behind a `BackupBackend` interface, keep the file-copy backend as the default, and record commits at the project operation boundary so each user action maps to one project state. Track project source files only, warn on repository growth instead of pruning, keep history in the existing delete archive, and start copied projects with a fresh repository. This delivers versioned project storage without changing current installations, and leaves remote hosting, per-file restore, and full-tree restore as deliberate follow-up decisions.
