# Docker Build Script Guide

## Overview

The `build.sh` script provides a unified interface for building Shape Shifter Docker images from either local context or GitHub repository.

## Key Features

### 1. **Dual Build Modes**
- **Local context** (`--local`) - Development builds from working directory
- **GitHub repository** (`--git-ref`) - CI/CD builds from specific branches or tags

### 2. **Smart Cache Invalidation**
- **Branches**: Automatically fetches latest commit SHA for cache busting
- **Tags**: No cache invalidation (tags are immutable)
- Detects semver tags (`v1.2.3`) vs branch names

### 3. **Intelligent Multi-Tagging**
Automatically creates additional tags based on repository state:

**Scenario 1: Building from main when it matches latest tag**
```bash
./build.sh --git-ref main
# If main == v1.9.0 tag:
# → Tags: shape-shifter:latest + shape-shifter:v1.9.0
```

**Scenario 2: Building from tag when it matches main**
```bash
./build.sh --git-ref v1.9.0
# If v1.9.0 tag == main branch:
# → Tags: shape-shifter:v1.9.0 + shape-shifter:latest
```

**Benefits:**
- ✅ Production releases automatically get both version and latest tags
- ✅ Ensures latest always points to most recent stable release
- ✅ No manual tagging required

### 4. **User Permission Handling**
- Auto-detects `sead` user UID (defaults to 1002)
- Auto-detects `www-data` group GID (defaults to 33)
- Customizable via `--user-uid` and `--user-gid`

## Usage Examples

### Development Build (Local Context)
```bash
# Build from your working directory (repository mode)
cd /path/to/repo/docker
./build.sh --local

# Result: shape-shifter:latest
# Mode: normal
# Context: .. (parent directory)
```

### Deployment Server Build (Automatic Standalone)
```bash
# Deploy script to server
scp build.sh deploy-server:/opt/shape-shifter/
scp Dockerfile deploy-server:/opt/shape-shifter/
scp -r lib/ deploy-server:/opt/shape-shifter/

# On deployment server - run from anywhere
cd /tmp
/opt/shape-shifter/build.sh --git-ref main

# Mode: standalone (automatic)
# Context: /opt/shape-shifter (where build.sh is located)
```

### Standalone Build (Deployment Server)
```bash
# For deployment servers without full repository
# Copy Dockerfile, build.sh, and lib/ to deployment directory

cd /path/to/deployment
# Directory should contain:
#   - Dockerfile
#   - build.sh
#   - lib/ (UCanAccess library)

# Build from GitHub (automatically uses standalone mode)
./build.sh --git-ref main

# Result: shape-shifter:latest
# Build context: script directory (where build.sh is located)
# Standalone mode: AUTOMATIC for GitHub builds
```

**Important: GitHub source enforces standalone mode**
- When using `--git-ref`, standalone mode is **automatic**
- Build context is always the script directory
- No need to specify `--standalone` flag explicitly
- Works from any directory - context is always where build.sh lives

**Standalone mode features:**
- Uses script directory as build context
- Doesn't require repository directory structure
- Perfect for CI/CD or deployment servers
- Can specify custom Dockerfile path

### CI/CD Build (GitHub Main)
```bash
# Build from main branch with automatic cache invalidation
./build.sh --git-ref main

# Result: shape-shifter:latest
# Cache bust: Uses latest commit SHA from GitHub
```

### Production Build (Release Tag)
```bash
# Build from release tag (no cache invalidation needed)
./build.sh --git-ref v1.2.0

# Result: shape-shifter:v1.2.0
# Cache bust: Static (tags are immutable)
```

### Development Branch Build
```bash
# Build from feature branch
./build.sh --git-ref develop

# Result: shape-shifter:develop
# Cache bust: Uses latest commit SHA from develop branch

# Custom tag
./build.sh --git-ref develop --image-tag dev-latest

# Result: shape-shifter:dev-latest
```

### Force Rebuild
```bash
# Rebuild without Docker cache
./build.sh --git-ref main --no-cache
```

### Custom Configuration
```bash
# Custom user/group for container
./build.sh --git-ref main \
  --user-uid 1001 \
  --user-gid 1001

# Custom repository
./build.sh --git-ref main \
  --git-repo https://github.com/yourfork/sead_shape_shifter.git

# Standalone with custom Dockerfile location
./build.sh --standalone \
  --git-ref main \
  --dockerfile /custom/path/Dockerfile \
  --context /custom/build/context
```

## How Cache Invalidation Works

### Branch Builds
```bash
./build.sh --git-ref main
```

1. Script detects `main` is not a semver tag
2. Fetches latest commit SHA: `git ls-remote <repo> refs/heads/main`
3. Passes SHA to Docker: `--build-arg CACHE_BUST=<commit-sha>`
4. Every new commit triggers rebuild (Docker cache invalidated)

### Tag Builds
```bash
./build.sh --git-ref v1.2.0
```

1. Script detects `v1.2.0` matches semver pattern (`^v[0-9]+\.[0-9]+\.[0-9]+`)
2. Uses static cache bust: `--build-arg CACHE_BUST=1`
3. Tag never changes → Docker cache reused (faster builds)

## Smart Multi-Tagging Examples

### Example 1: Release Workflow
```bash
# Developer creates and pushes tag
git tag v1.10.0
git push origin v1.10.0

# On build server
./build.sh --git-ref v1.10.0

# Output:
# info: building from release tag v1.10.0 (no cache invalidation)
# info: tag v1.10.0 equals main branch, adding 'latest' tag
# Image Tag:      v1.10.0
# Additional Tags: shape-shifter:latest
#
# Result: Both tags created automatically!
# - shape-shifter:v1.10.0
# - shape-shifter:latest
```

### Example 2: Continuous Deployment
```bash
# CI/CD builds from main after merge
./build.sh --git-ref main

# If main HEAD matches v1.10.0 tag:
# Output:
# info: building from branch main (with cache invalidation)
# info: main branch equals tag v1.10.0, adding version tag
# Image Tag:      latest
# Additional Tags: shape-shifter:v1.10.0
#
# Result: Both tags point to same image
# - shape-shifter:latest
# - shape-shifter:v1.10.0
```

### Example 3: Development Branch
```bash
# Building feature branch
./build.sh --git-ref feature/new-ui

# Output:
# Image Tag:      feature-new-ui
# (no additional tags)
#
# Result: Single tag only
# - shape-shifter:feature-new-ui
```

## How Cache Invalidation Works (Legacy)

## Build Output

The script provides detailed configuration summary:

```
============================================================
Build Configuration
============================================================
Source:         github
Repository:     https://github.com/humlab-sead/sead_shape_shifter.git
Git Ref:        main
Cache Bust:     a1b2c3d4e5f6
Image Name:     shape-shifter
Image Tag:      latest
Dockerfile:     Dockerfile
User UID:       1002
User GID:       33
No Cache:       false
============================================================

Executing: docker build -f Dockerfile --build-arg SOURCE=github ...
```

## Integration with Makefile

The script is fully integrated with Makefile targets for convenience:

| Makefile Target | Equivalent Script Command | Description |
|----------------|---------------------------|-------------|
| `make docker-build` | `./build.sh --local` | Default: local development build |
| `make docker-build-github` | `./build.sh --git-ref main` | Build from GitHub main branch |
| `make docker-build-tag TAG=v1.2.0` | `./build.sh --git-ref v1.2.0` | Build from specific tag/branch |
| `make docker-build-local` | `./build.sh --local` | Explicit local build |

**Makefile advantages:**
- Concise commands (`make docker-build` vs `./build.sh --local`)
- Automatic variable passing (USER_UID, USER_GID, GIT_REPO)
- Consistent with project conventions

**Script advantages:**
- More flexible argument handling
- Better error messages and output formatting
- Standalone (no make dependency)
- Portable across environments
- Can be called from CI/CD directly

Both approaches use the same underlying script, so behavior is identical.

## Improvements Over Original

### Fixed Issues
1. ✅ **Removed unused variables** (`$g_registry`, `$g_use_uv`)
2. ✅ **Fixed Makefile syntax** (`$$` → `$` for bash variables)
3. ✅ **Function actually executes** (original defined but never called)
4. ✅ **Proper error handling** (validates required arguments)
5. ✅ **Complete implementation** (original was partial)

### New Features
1. ✅ **Local build support** (`--local` flag)
2. ✅ **Smart cache busting** (branch vs tag detection)
3. ✅ **Auto image tagging** (derives from git ref)
4. ✅ **User-friendly output** (configuration summary)
5. ✅ **Flexible arguments** (all settings customizable)
6. ✅ **Better documentation** (inline examples, help text)

### Code Quality
1. ✅ **Proper array handling** (`build_args` array vs string concatenation)
2. ✅ **Quoted variables** (prevents word splitting)
3. ✅ **Safe defaults** (fallbacks for missing users/groups)
4. ✅ **Clear structure** (logical flow, well-commented)

## Deployment Server Setup

For production deployments without the full repository:

### 1. Prepare Deployment Directory

```bash
# On deployment server
mkdir -p /opt/shape-shifter
cd /opt/shape-shifter

# Copy required files from repository or CI artifact
# - Dockerfile
# - build.sh
# - lib/ directory (UCanAccess)
```

### 2. Build Image

```bash
cd /opt/shape-shifter
chmod +x build.sh

# Build from latest main
./build.sh --standalone --git-ref main

# Or build from specific release
./build.sh --standalone --git-ref v1.2.0
```

### 3. Verify Build

```bash
docker images | grep shape-shifter
# Should show: shape-shifter:latest or shape-shifter:v1.2.0
```

### 4. Run Container

```bash
# Using docker compose (recommended)
docker compose up -d

# Or standalone
docker run -d -p 8012:8012 \
  -v /opt/shape-shifter/data/projects:/app/projects \
  -v /opt/shape-shifter/data/logs:/app/logs \
  shape-shifter:latest
```

## Troubleshooting

### "sead user not found"
Script falls back to UID 1002. Override with:
```bash
./build.sh --git-ref main --user-uid $(id -u)
```

### "could not fetch commit SHA"
Network issue or invalid branch. Script uses timestamp fallback:
```bash
warning: could not fetch commit SHA, using timestamp for cache bust
```

### "git-ref is required when building from GitHub"
Specify branch or tag:
```bash
./build.sh --git-ref main
```

### Build context too large
Use `--local` mode and ensure `.dockerignore` excludes unnecessary files.

## Best Practices

### Development Workflow
```bash
# Work locally, build frequently
./build.sh --local
```

### CI/CD Pipeline
```bash
# Automated builds from main
./build.sh --git-ref main
```

### Release Process
```bash
# Tag release first
git tag v1.2.0
git push origin v1.2.0

# Build from tag
./build.sh --git-ref v1.2.0

# Push to registry (if implemented)
docker push shape-shifter:v1.2.0
```

### Testing Multiple Branches
```bash
# Compare feature branch to main
./build.sh --git-ref feature/new-thing --image-tag feature-test
./build.sh --git-ref main --image-tag main-baseline
```

## Future Enhancements

Potential additions:
- [ ] `--push` flag for registry push
- [ ] `--platform` for multi-arch builds
- [ ] `--quiet` mode for CI logs
- [ ] Build time tracking
- [ ] Image size reporting
- [ ] Automatic tagging of both `:latest` and `:v1.2.0` for releases
- [ ] Integration with GitHub Actions
