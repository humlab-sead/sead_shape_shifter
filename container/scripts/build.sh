#!/usr/bin/env bash
# Build script for the SEAD Shape Shifter Podman image.
# Usage: ./build.sh [OPTIONS]
#
# Build modes:
#   Local:  ./build.sh --local                  (build from the repository checkout)
#   Branch: ./build.sh --git-ref main           (clone from GitHub, auto cache-bust)
#   Tag:    ./build.sh --git-ref v1.2.0         (clone a release tag, no cache-bust)
#
# GitHub builds always run in standalone mode: the build context is this script's
# directory, so the deployment host only needs Containerfile, build.sh and lib/.

set -euo pipefail

# Load container/.env values that the environment has not already set.
# shellcheck source=load-env.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/load-env.sh"
# shellcheck source=env-config.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/env-config.sh"

RED='\e[31m'
GREEN='\e[32m'
YELLOW='\e[33m'
BLUE='\e[34m'
CYAN='\e[36m'
RESET='\e[0m'

# Script location
g_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
g_script_file="$(basename "${BASH_SOURCE[0]}")"

# Defaults. GIT_REPO, GIT_REF and IMAGE_NAME come from container/.env when it
# sets them; the command-line options below still override those values.
g_git_repo="${GIT_REPO:-https://github.com/humlab-sead/sead_shape_shifter.git}"
g_git_ref="${GIT_REF:-}"
_shapeshifter_image="${IMAGE_NAME:-shape-shifter:latest}"
g_image_name="${_shapeshifter_image%%:*}"
if [ "$_shapeshifter_image" = "$g_image_name" ]; then
    g_image_tag="latest"
else
    g_image_tag="${_shapeshifter_image##*:}"
fi
unset _shapeshifter_image
g_containerfile="Containerfile"
g_source="github"
g_no_cache=""
g_standalone=false
g_build_context=".."
g_user_uid="$(id -u)"
g_user_gid="$(id -g)"

function print_usage() {
    if [ -n "${1:-}" ]; then
        echo "error: $1"
    fi
    cat <<EOF
Usage: $g_script_file [OPTIONS]

Build modes:
  --local               Build from the local repository checkout (development)
  --git-ref REF         Build from a GitHub branch or tag
  --standalone          Use the script directory as build context

Options:
  -t, --image-tag TAG   Image tag (default: derived from --git-ref)
  --image-name NAME     Image name (default: shape-shifter)
  --no-cache            Build without Podman cache
  --user-uid UID        Container user UID (default: current user's UID)
  --user-gid GID        Container user GID (default: current user's GID)
  --git-repo URL        Git repository URL (default: official repository)
  --containerfile PATH  Path to the Containerfile (default: Containerfile)
  --context PATH        Build context directory (default: .. or . in standalone)
  -h, --help            Show this help message

Examples:
  # Build from the local checkout (in the repository)
  $g_script_file --local

  # Build from GitHub main with cache invalidation
  $g_script_file --git-ref main

  # Build a release tag
  $g_script_file --git-ref v1.2.0

  # Deployment host: standalone build from GitHub
  $g_script_file --git-ref main

  # Force a rebuild without cache
  $g_script_file --git-ref main --no-cache
EOF
    if [ -n "${1:-}" ]; then
        exit 64
    fi
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            g_source="workdir"
            shift
            ;;
        --standalone)
            g_standalone=true
            g_build_context="."
            shift
            ;;
        --git-ref)
            g_git_ref="$2"
            g_source="github"
            shift 2
            ;;
        -t|--image-tag)
            g_image_tag="$2"
            shift 2
            ;;
        --image-name)
            g_image_name="$2"
            shift 2
            ;;
        --containerfile)
            g_containerfile="$2"
            shift 2
            ;;
        --context)
            g_build_context="$2"
            shift 2
            ;;
        --no-cache)
            g_no_cache="--no-cache"
            shift
            ;;
        --user-uid)
            g_user_uid="$2"
            shift 2
            ;;
        --user-gid)
            g_user_gid="$2"
            shift 2
            ;;
        --git-repo)
            g_git_repo="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            ;;
        *)
            print_usage "unknown option $1"
            ;;
    esac
done

# GitHub source always builds standalone with the script directory as context.
if [ "$g_source" = "github" ]; then
    g_standalone=true
    g_build_context="."
fi

if [ "$g_standalone" = true ]; then
    g_build_context="$g_script_dir"
fi

# Derive the image tag from the git ref when one was not supplied. The rule lives
# in scripts/env-config.sh so the deploy scripts cannot disagree with it.
if [ "$g_source" = "github" ] && [ "$g_image_tag" = "latest" ]; then
    g_image_tag="$(shapeshifter_tag_for_ref "$g_git_ref")"
fi

if [ "$g_source" = "github" ] && [ -z "$g_git_ref" ]; then
    print_usage "git-ref is required when building from GitHub"
fi

# Decide whether cache invalidation is needed, and collect additional tags.
g_cache_bust="1"
g_additional_tags=()

if [ "$g_source" = "github" ]; then
    if [[ "$g_git_ref" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
        echo "info: building from release tag $g_git_ref (no cache invalidation)"

        main_commit="$(git ls-remote "$g_git_repo" refs/heads/main 2>/dev/null | cut -f1)"
        tag_commit="$(git ls-remote "$g_git_repo" "refs/tags/$g_git_ref" 2>/dev/null | cut -f1)"
        if [ -n "$main_commit" ] && [ -n "$tag_commit" ] && [ "$main_commit" = "$tag_commit" ]; then
            echo "info: tag $g_git_ref equals main branch, adding 'latest' tag"
            g_additional_tags+=("$g_image_name:latest")
        fi
    else
        echo "info: building from non-version ref $g_git_ref (with cache invalidation)"

        ref_prefix="$(echo "$g_git_ref" | sed 's/[^a-zA-Z0-9._-]/-/g')"
        g_additional_tags+=("$g_image_name:${ref_prefix}-$(date +%Y%m%d)")

        # The ref can be a branch or a tag, matching the archive URL that the
        # bootstrap scripts download. Try the peeled tag, the tag, then a branch
        # so the record is right for any of them.
        g_cache_bust="$(git ls-remote "$g_git_repo" "refs/tags/$g_git_ref^{}" 2>/dev/null | head -n1 | cut -f1 || true)"
        if [ -z "$g_cache_bust" ]; then
            g_cache_bust="$(git ls-remote "$g_git_repo" "refs/tags/$g_git_ref" 2>/dev/null | head -n1 | cut -f1 || true)"
        fi
        if [ -z "$g_cache_bust" ]; then
            g_cache_bust="$(git ls-remote "$g_git_repo" "refs/heads/$g_git_ref" 2>/dev/null | head -n1 | cut -f1 || true)"
        fi
        if [ -z "$g_cache_bust" ]; then
            echo "warning: could not fetch commit SHA, using timestamp for cache bust"
            g_cache_bust="$(date +%s)"
        fi
    fi
fi

# Resolve the exact source commit so the image records the commit it was built
# from, next to its immutable content digest. The build context excludes .git,
# so the commit cannot be determined inside the build itself.
if [[ "$g_build_context" = /* ]]; then
    g_context_abs="$g_build_context"
else
    g_context_abs="$(cd "$g_script_dir/$g_build_context" 2>/dev/null && pwd || echo "$g_script_dir/$g_build_context")"
fi

g_build_ref="$g_git_ref"
g_source_commit=""

if [ "$g_source" = "github" ]; then
    if [[ "$g_git_ref" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
        # An annotated tag points at a tag object, so peel it down to the commit.
        g_source_commit="$(git ls-remote "$g_git_repo" "refs/tags/$g_git_ref^{}" 2>/dev/null | head -n1 | cut -f1 || true)"
        if [ -z "$g_source_commit" ]; then
            g_source_commit="$(git ls-remote "$g_git_repo" "refs/tags/$g_git_ref" 2>/dev/null | head -n1 | cut -f1 || true)"
        fi
    elif [[ "$g_cache_bust" =~ ^[0-9a-f]{40}$ || "$g_cache_bust" =~ ^[0-9a-f]{64}$ ]]; then
        # The cache-bust value is the branch commit, unless the lookup failed and
        # it fell back to a timestamp, which is a length that cannot be a commit.
        g_source_commit="$g_cache_bust"
    fi
else
    # A checkout build reads the commit from the checkout being built. A GitHub
    # build must not fall back to this, because the local repository is not the
    # source that gets cloned into the image.
    g_source_commit="$(git -C "$g_context_abs" rev-parse HEAD 2>/dev/null || true)"

    if [ -n "$g_source_commit" ] && [ -n "$(git -C "$g_context_abs" status --porcelain 2>/dev/null | head -n1)" ]; then
        # Uncommitted changes mean the image contents are not fully described by the commit.
        g_source_commit="${g_source_commit}-dirty"
        echo "warning: build context has uncommitted changes; labelling the image '${g_source_commit}'"
    fi
fi

if [ -z "$g_build_ref" ]; then
    g_build_ref="$(git -C "$g_context_abs" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
fi

if [ -z "$g_source_commit" ]; then
    echo "warning: could not determine the source commit; labelling it as 'unknown'"
    g_source_commit="unknown"
fi
if [ -z "$g_build_ref" ]; then
    g_build_ref="unknown"
fi

g_build_date="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# The Containerfile copies lib/ from the build context. Create an empty lib/ when
# the UCanAccess JARs are absent so the build still succeeds (MS Access data
# sources will be unavailable until scripts/install-ucanaccess.sh has been run).
if [ ! -d "$g_build_context/lib" ]; then
    echo "warning: no lib/ directory in build context; creating an empty one"
    echo "warning: MS Access support needs lib/ucanaccess - run scripts/install-ucanaccess.sh"
    mkdir -p "$g_build_context/lib"
fi
if [ ! -d "$g_build_context/lib/ucanaccess" ]; then
    echo "warning: lib/ucanaccess not found - MS Access data sources will not load"
fi

echo ""
echo "============================================================"
echo "Build Configuration"
echo "============================================================"
echo "Mode:            $([ "$g_standalone" = true ] && echo "standalone" || echo "normal")"
echo "Source:          $g_source"
if [ "$g_source" = "github" ]; then
    echo "Repository:      $g_git_repo"
    echo "Git Ref:         $g_git_ref"
    echo "Cache Bust:      ${g_cache_bust:0:12}"
fi
echo "Source Commit:   $g_source_commit"
echo "Build Date:      $g_build_date"
echo "Image Name:      $g_image_name"
echo "Image Tag:       $g_image_tag"
if [ ${#g_additional_tags[@]} -gt 0 ]; then
    echo "Additional Tags: ${g_additional_tags[*]}"
fi
echo "Containerfile:   $g_containerfile"
echo "Build Context:   $g_build_context"
echo "User UID:        $g_user_uid"
echo "User GID:        $g_user_gid"
echo "No Cache:        ${g_no_cache:-false}"
echo "============================================================"
echo ""

cd "$g_script_dir"

if [[ "$g_containerfile" = /* ]]; then
    g_containerfile_abs="$g_containerfile"
else
    g_containerfile_abs="$g_script_dir/$g_containerfile"
fi

build_args=(
    -f "$g_containerfile_abs"
    # Build in Docker image format so the Containerfile HEALTHCHECK is kept.
    # Podman's default OCI format silently drops HEALTHCHECK instructions.
    --format docker
    --build-arg "SOURCE=$g_source"
    --build-arg "SOURCE_COMMIT=$g_source_commit"
    --build-arg "BUILD_DATE=$g_build_date"
    --build-arg "GIT_REPO=$g_git_repo"
    --build-arg "GIT_REF=$g_build_ref"
    --build-arg "USER_UID=$g_user_uid"
    --build-arg "USER_GID=$g_user_gid"
    -t "$g_image_name:$g_image_tag"
)

if [ "$g_source" = "github" ]; then
    build_args+=(
        --build-arg "CACHE_BUST=$g_cache_bust"
    )
fi

if [ -n "$g_no_cache" ]; then
    build_args+=("$g_no_cache")
fi

for tag in "${g_additional_tags[@]}"; do
    build_args+=(-t "$tag")
done

build_args+=("$g_build_context")

echo "Executing: podman build ${build_args[*]}"
echo ""

podman build "${build_args[@]}"

echo ""
echo -e "${GREEN}============================================================${RESET}"
echo -e "${GREEN}Build complete${RESET}"
echo -e "${GREEN}============================================================${RESET}"
echo -e "${GREEN}Image:${RESET} $g_image_name:$g_image_tag"

# Record the two values that identify the release: the source commit recorded in
# the image label, and the immutable content digest.
g_image_revision="$(podman image inspect "$g_image_name:$g_image_tag" --format '{{index .Labels "org.opencontainers.image.revision"}}' 2>/dev/null || true)"
g_image_digest="$(podman image inspect "$g_image_name:$g_image_tag" --format '{{.Digest}}' 2>/dev/null || true)"
echo -e "${GREEN}Source commit:${RESET} ${g_image_revision:-unknown}"
echo -e "${GREEN}Digest:${RESET} ${g_image_digest:-unknown}"

# `make up` starts IMAGE_NAME, which is not necessarily the tag this build
# produced. Report the difference instead of letting the next start quietly run
# the previous image.
if [ -n "${IMAGE_NAME:-}" ] && [ "$IMAGE_NAME" != "$g_image_name:$g_image_tag" ]; then
    echo ""
    echo -e "${YELLOW}!${RESET} Built ${g_image_name}:${g_image_tag}, but IMAGE_NAME is '${IMAGE_NAME}'."
    echo -e "${YELLOW}!${RESET} 'make up' starts IMAGE_NAME. Set that value in container/.env to match, or run:"
    echo -e "${YELLOW}!${RESET}   IMAGE_NAME=${g_image_name}:${g_image_tag} make up"
fi

if [ ${#g_additional_tags[@]} -gt 0 ]; then
    echo -e "${GREEN}Additional tags:${RESET}"
    for tag in "${g_additional_tags[@]}"; do
        echo -e "  - $tag"
    done
fi
echo ""
echo -e "${BLUE}Start the container:${RESET}"
echo -e "  make up"
