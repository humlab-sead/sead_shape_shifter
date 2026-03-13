# Docker Build Time Review

Date: 2026-03-13
Scope: `docker/Dockerfile`, `docker/.dockerignore`, `docker/build.sh`

## Findings

### 1. Dependency layers are invalidated by normal source edits

This is the largest build-time issue.

- In `docker/Dockerfile`, the frontend stage copies the entire source tree before `pnpm install`.
- In the Python builder stage, the Dockerfile copies the entire repo before `uv pip install -e ".[api]"`.

Impact:

- Any change to application source invalidates the dependency install layers.
- Docker then reruns both `pnpm install` and Python dependency installation even when lockfiles and dependency metadata have not changed.

Recommended change:

- Copy only frontend dependency manifests first, then run `pnpm install`, then copy the rest of the frontend source.
- Copy only Python dependency metadata first, then install Python dependencies, then copy the rest of the application source.

Typical pattern:

```dockerfile
# Frontend
COPY frontend/package.json frontend/pnpm-lock.yaml /app/frontend/
RUN pnpm install --frozen-lockfile
COPY frontend /app/frontend

# Python
COPY pyproject.toml uv.lock README.md /app/
RUN uv pip install --system --no-cache -e ".[api]"
COPY src backend ingesters scripts /app/
```

### 2. GitHub-mode builds still pay for full local context upload

The Dockerfile always executes `COPY . /source-context/`, even when `SOURCE=github`.

Impact:

- Docker still has to archive and send the full local build context before the build starts.
- The later shell branch that says it is ignoring the context only ignores it inside the image. It does not avoid transfer time.

This is especially relevant because `docker/build.sh` forces standalone mode for GitHub builds, so the Docker build context becomes the `docker/` directory. That reduces the penalty, but the unconditional `COPY .` is still structurally misleading and still unnecessary work.

Recommended change:

- Avoid unconditional context copy for GitHub-mode builds.
- If remote-source builds are important, use a minimal context and a Dockerfile structure that does not require `COPY .` in that path.

### 3. Runtime stage does expensive recursive ownership and permission changes

The runtime stage runs recursive `chown` and `chmod` across `/app` after all content is copied.

Impact:

- Extra filesystem walk across the application tree.
- Extra layer cost.
- Noticeable overhead when the image contains a full Python environment and built frontend assets.

Recommended change:

- Use `COPY --chown=` where possible.
- Restrict ownership and write-permission changes to the actual writable directories such as `projects`, `logs`, `output`, `backups`, and `tmp`.

### 4. Local source resolution duplicates copy work

For local builds, the source-resolver stage copies the full context into `/source-context` and then copies it again into `/source`.

Impact:

- Extra I/O and extra image layer work on every local build.

Recommended change:

- Simplify the local path so source files are copied directly where needed.
- If the source-resolver abstraction is kept, avoid the double-copy pattern.

## Priority Order

If optimizing incrementally, apply changes in this order:

1. Split dependency-manifest copy from application-source copy in the frontend and Python stages.
2. Remove or redesign the unconditional `COPY .` path for GitHub-mode builds.
3. Replace recursive `chown -R` and `chmod -R` with targeted ownership/perms handling.
4. Simplify the local source-resolver copy flow.

## Summary

The primary problem is cache structure rather than the package managers themselves. The current Dockerfile forces expensive dependency reinstalls after ordinary source edits and performs extra file-copy and metadata work that is avoidable. The fastest meaningful improvement is to reorganize the dependency installation layers so they depend only on manifest files, not the full source tree.